from rest_framework import viewsets, status, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.db import models
from .models import Alerta
from .serializers import (
    AlertaSerializer, AlertaListSerializer, AlertaCreateSerializer, AlertaUpdateSerializer
)
from .utils import (
    crear_alerta, reglas_alertas_automaticas, estadisticas_alertas, 
    obtener_alertas_activas, obtener_alertas_historial
)
from usuarios.permissions import IsAdmin, IsAdminOrReadOnly
from auditorias.models import AuditoriaAccion


def get_client_ip(request):
    """Obtiene la IP del cliente"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR', 'unknown')
    return ip


class AlertasActivasView(APIView):
    """API para obtener alertas activas (PASO 7.5)"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        filtro_severidad = request.query_params.get('severidad', None)
        alertas = obtener_alertas_activas(filtro_severidad=filtro_severidad)
        serializer = AlertaListSerializer(alertas, many=True)
        return Response(serializer.data)


class AlertasHistorialView(APIView):
    """API para obtener historial de alertas (PASO 7.5)"""
    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    
    def get(self, request):
        limite = int(request.query_params.get('limite', 200))
        filtro_tipo = request.query_params.get('tipo', None)
        alertas = obtener_alertas_historial(limite=limite, filtro_tipo=filtro_tipo)
        serializer = AlertaListSerializer(alertas, many=True)
        return Response(serializer.data)


class ResolverAlertaView(APIView):
    """API para marcar alerta como resuelta (PASO 7.8)
    PASO 11: Ahora también actualiza el historial de alertas"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, alerta_id):
        try:
            alerta = Alerta.objects.get(id=alerta_id)
            alerta.marcar_como_resuelta(request.user)
            
            # PASO 11: Actualizar historial cuando se resuelve
            from .models import AlertaHistorial
            historial = AlertaHistorial.objects.filter(alerta=alerta).last()
            if historial:
                from django.utils import timezone
                historial.resuelta_en = timezone.now()
                historial.resuelta_por = request.user
                historial.estado_final = 'resuelta'
                historial.save()
            
            serializer = AlertaSerializer(alerta)
            return Response(serializer.data)
        except Alerta.DoesNotExist:
            return Response(
                {'error': 'Alerta no encontrada'},
                status=status.HTTP_404_NOT_FOUND
            )


class AlertasEstadisticasView(APIView):
    """API para obtener estadísticas de alertas"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        stats = estadisticas_alertas()
        return Response(stats)


class AlertaViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar alertas con RBAC
    - Admin: acceso completo
    - Gestor: crear, editar alertas
    - Ejecutivo: solo lectura
    """
    queryset = Alerta.objects.select_related('poliza', 'cliente', 'creada_por', 'asignada_a').all()
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['tipo', 'severidad', 'estado', 'poliza', 'cliente']
    search_fields = ['titulo', 'mensaje', 'poliza__numero', 'cliente__nombre', 'cliente__rut']
    ordering_fields = ['fecha_creacion', 'severidad', 'estado', 'fecha_limite']
    ordering = ['-fecha_creacion']

    def get_serializer_class(self):
        if self.action == 'create':
            return AlertaCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return AlertaUpdateSerializer
        return AlertaSerializer

    def get_permissions(self):
        """Permisos dinámicos por acción"""
        if self.action in ['create', 'update', 'partial_update', 'resolver', 'asignar']:
            permission_classes = [permissions.IsAuthenticated]
        else:
            permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]
        return [permission() for permission in permission_classes]

    def perform_create(self, serializer):
        """Crear alerta y registrar en auditoría"""
        alerta = serializer.save(creada_por=self.request.user)
        
        # Registrar en auditoría
        AuditoriaAccion.registrar(
            usuario=self.request.user,
            accion='CREATE',
            modulo='alertas',
            modelo='Alerta',
            descripcion=f'Se creó alerta: {alerta.titulo}',
            objeto_id=alerta.id,
            datos_nuevos={'titulo': alerta.titulo, 'tipo': alerta.tipo, 'severidad': alerta.severidad},
            ip_address=get_client_ip(self.request),
            user_agent=self.request.META.get('HTTP_USER_AGENT', ''),
            metodo_http=self.request.method,
            url=self.request.path
        )

    @action(detail=False, methods=['get'])
    def pendientes(self, request):
        """Retorna alertas pendientes"""
        alertas = self.queryset.filter(estado='PENDIENTE')
        serializer = self.get_serializer(alertas, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def por_tipo(self, request):
        """Agrupa alertas por tipo"""
        from django.db.models import Count
        
        stats = self.queryset.values('tipo').annotate(
            total=Count('id'),
            pendientes=Count('id', filter=models.Q(estado='PENDIENTE')),
            resueltas=Count('id', filter=models.Q(estado='RESUELTA'))
        ).order_by('tipo')
        
        return Response(stats)

    @action(detail=False, methods=['get'])
    def mis_alertas(self, request):
        """Retorna alertas asignadas al usuario actual"""
        alertas = self.queryset.filter(asignada_a=request.user, estado__in=['PENDIENTE', 'LEIDA'])
        serializer = self.get_serializer(alertas, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def criticas(self, request):
        """Retorna alertas críticas pendientes"""
        alertas = self.queryset.filter(
            severidad='critical',
            estado__in=['PENDIENTE', 'LEIDA']
        )
        serializer = self.get_serializer(alertas, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def vencidas(self, request):
        """Retorna alertas que han superado su fecha límite"""
        ahora = timezone.now()
        alertas = self.queryset.filter(
            fecha_limite__lt=ahora,
            estado='PENDIENTE'
        )
        serializer = self.get_serializer(alertas, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def marcar_leida(self, request, pk=None):
        """Marca una alerta como leída"""
        alerta = self.get_object()
        
        if alerta.marcar_como_leida(request.user):
            return Response(
                AlertaSerializer(alerta).data,
                status=status.HTTP_200_OK
            )
        return Response(
            {'error': 'La alerta ya fue procesada'},
            status=status.HTTP_400_BAD_REQUEST
        )

    @action(detail=True, methods=['post'])
    def marcar_resuelta(self, request, pk=None):
        """Marca una alerta como resuelta"""
        alerta = self.get_object()
        
        if alerta.marcar_como_resuelta(request.user):
            return Response(
                AlertaSerializer(alerta).data,
                status=status.HTTP_200_OK
            )
        return Response(
            {'error': 'La alerta ya fue resuelta o descartada'},
            status=status.HTTP_400_BAD_REQUEST
        )

    @action(detail=True, methods=['post'])
    def descartar(self, request, pk=None):
        """Descarta una alerta"""
        alerta = self.get_object()
        
        if alerta.descartar():
            return Response(
                AlertaSerializer(alerta).data,
                status=status.HTTP_200_OK
            )
        return Response(
            {'error': 'La alerta ya fue procesada'},
            status=status.HTTP_400_BAD_REQUEST
        )

    @action(detail=False, methods=['get'])
    def estadisticas(self, request):
        """Retorna estadísticas generales de alertas"""
        from django.db.models import Count, Q
        
        stats = {
            'total': self.queryset.count(),
            'pendientes': self.queryset.filter(estado='PENDIENTE').count(),
            'leidas': self.queryset.filter(estado='LEIDA').count(),
            'resueltas': self.queryset.filter(estado='RESUELTA').count(),
            'criticas': self.queryset.filter(severidad='critical', estado__in=['PENDIENTE', 'LEIDA']).count(),
            'vencidas': self.queryset.filter(
                fecha_limite__lt=timezone.now(),
                estado='PENDIENTE'
            ).count(),
        }
        
        # Por tipo
        por_tipo = {}
        for tipo_code, tipo_name in Alerta.TIPO_CHOICES:
            por_tipo[tipo_code] = {
                'nombre': tipo_name,
                'total': self.queryset.filter(tipo=tipo_code).count(),
                'pendientes': self.queryset.filter(tipo=tipo_code, estado='PENDIENTE').count()
            }
        
        stats['por_tipo'] = por_tipo
        
        return Response(stats)

    @action(detail=False, methods=['post'])
    def crear_alerta_vencimiento(self, request):
        """Crea alertas automáticas para pólizas próximas a vencer"""
        from polizas.models import Poliza
        from datetime import date, timedelta
        
        dias_alerta = int(request.data.get('dias', 30))
        fecha_limite = date.today() + timedelta(days=dias_alerta)
        
        polizas_por_vencer = Poliza.objects.filter(
            fecha_vencimiento__lte=fecha_limite,
            fecha_vencimiento__gte=date.today(),
            estado='VIGENTE'
        )
        
        alertas_creadas = 0
        for poliza in polizas_por_vencer:
            # Verificar si ya existe una alerta para esta póliza
            existe = Alerta.objects.filter(
                tipo='vencimientos',
                poliza=poliza,
                estado__in=['PENDIENTE', 'LEIDA']
            ).exists()
            
            if not existe:
                dias_restantes = (poliza.fecha_vencimiento - date.today()).days
                severidad = 'critical' if dias_restantes <= 7 else 'warning' if dias_restantes <= 15 else 'info'
                
                Alerta.objects.create(
                    tipo='vencimientos',
                    severidad=severidad,
                    titulo=f'Póliza {poliza.numero} próxima a vencer',
                    mensaje=f'La póliza {poliza.numero} del cliente {poliza.cliente.nombre} vence en {dias_restantes} días ({poliza.fecha_vencimiento.strftime("%d/%m/%Y")})',
                    poliza=poliza,
                    cliente=poliza.cliente,
                    creada_por=request.user,
                    fecha_limite=timezone.make_aware(timezone.datetime.combine(poliza.fecha_vencimiento, timezone.datetime.min.time()))
                )
                alertas_creadas += 1
        
        return Response({
            'mensaje': f'{alertas_creadas} alertas de vencimiento creadas',
            'polizas_revisadas': polizas_por_vencer.count()
        }, status=status.HTTP_201_CREATED)


class EjecutarReglasAlertasView(APIView):
    """
    PASO 10: API para ejecutar reglas automáticas de alertas
    
    Ejecuta todas las reglas de alerta basadas en reportes inteligentes:
    1. Pólizas vencidas
    2. Pólizas próximas a vencer (≤30 días)
    3. Caída de producción en clientes de alto valor
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """Ejecuta todas las reglas de alertas y retorna estadísticas"""
        try:
            from reportes.services import (
                reporte_polizas_vencidas,
                reporte_polizas_por_expirar,
            )
            
            # Ejecutar reportes (que generan alertas automáticamente)
            vencidas = reporte_polizas_vencidas()
            por_expirar = reporte_polizas_por_expirar()
            
            # Obtener estadísticas de alertas después de la ejecución
            alertas_totales = Alerta.objects.count()
            alertas_pendientes = Alerta.objects.filter(estado='PENDIENTE').count()
            alertas_criticas = Alerta.objects.filter(
                severidad='critical',
                estado__in=['PENDIENTE', 'LEIDA']
            ).count()
            
            response_data = {
                "status": "ok",
                "mensaje": "Reglas de alertas ejecutadas exitosamente",
                "reportes": {
                    "polizas_vencidas": vencidas['total'],
                    "polizas_por_expirar": por_expirar['total'],
                },
                "alertas": {
                    "totales": alertas_totales,
                    "pendientes": alertas_pendientes,
                    "criticas": alertas_criticas,
                },
                "generado": str(timezone.now()),
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response(
                {
                    "status": "error",
                    "mensaje": f"Error al ejecutar reglas de alertas: {str(e)}",
                    "generado": str(timezone.now()),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AlertaHistorialListView(APIView):
    """
    PASO 11: API para ver el historial completo de alertas
    
    Retorna los últimos 200 registros del historial con información completa
    de quién resolvió cada alerta y cuándo.
    """
    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    
    def get(self, request):
        """
        Retorna historial de alertas con filtros opcionales
        
        Query parameters:
        - tipo: filtrar por tipo de alerta
        - estado: filtrar por estado_final
        - cliente_id: filtrar por cliente
        - dias: últimos N días (default: todos)
        """
        from .models import AlertaHistorial
        from clientes.models import Cliente
        from django.utils import timezone
        
        # Base query con select_related para optimizar
        historial = AlertaHistorial.objects.select_related(
            'alerta', 'cliente', 'poliza', 'resuelta_por'
        ).order_by('-creada_en')
        
        # Filtros opcionales
        tipo = request.query_params.get('tipo')
        if tipo:
            historial = historial.filter(tipo=tipo)
        
        estado = request.query_params.get('estado')
        if estado:
            historial = historial.filter(estado_final=estado)
        
        cliente_id = request.query_params.get('cliente_id')
        if cliente_id:
            historial = historial.filter(cliente_id=cliente_id)
        
        dias = request.query_params.get('dias')
        if dias:
            fecha_limite = timezone.now() - timezone.timedelta(days=int(dias))
            historial = historial.filter(creada_en__gte=fecha_limite)
        
        # Limitar a últimos 200 registros
        historial = historial[:200]
        
        # Serializar datos
        data = [{
            "id": h.id,
            "alerta_id": h.alerta_id,
            "tipo": h.tipo,
            "mensaje": h.mensaje,
            "titulo": h.titulo,
            "cliente": h.cliente.nombre if h.cliente else "N/A",
            "rut": h.cliente.rut if h.cliente else "N/A",
            "poliza": h.poliza.numero if h.poliza else "N/A",
            "severidad": h.severidad,
            "creada_en": h.creada_en.isoformat(),
            "resuelta_en": h.resuelta_en.isoformat() if h.resuelta_en else None,
            "resuelta_por": h.resuelta_por.username if h.resuelta_por else None,
            "estado_final": h.estado_final,
            "tiempo_resolucion_horas": h.tiempo_resolucion,
            "dias_pendiente": h.dias_pendiente,
        } for h in historial]
        
        return Response({
            "total": len(data),
            "historial": data,
            "timestamp": timezone.now().isoformat()
        }, status=status.HTTP_200_OK)


class TestEmailAlertaView(APIView):
    """
    PASO 16: Vista para testear envío de email de una alerta
    Solo para administradores
    """
    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    
    def post(self, request, alerta_id):
        """Envía un email de prueba para una alerta específica"""
        try:
            alerta = Alerta.objects.get(id=alerta_id)
            
            from .notificaciones import enviar_notificacion_alerta
            resultado = enviar_notificacion_alerta(alerta)
            
            if resultado:
                return Response(
                    {
                        'success': True,
                        'mensaje': f'Email de alerta enviado exitosamente',
                        'alerta_id': alerta.id,
                        'titulo': alerta.titulo,
                        'severidad': alerta.get_severidad_display(),
                    },
                    status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {
                        'success': False,
                        'error': 'No se pudo enviar el email (verifica configuración SMTP)'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
        except Alerta.DoesNotExist:
            return Response(
                {'error': 'Alerta no encontrada'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'Error: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
