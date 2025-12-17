from rest_framework import viewsets, status, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import Cobranza
from .serializers import CobranzaSerializer, CobranzaCreateSerializer, CobranzaPagoSerializer
from datetime import date, datetime, timedelta
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


class CobranzaViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar cobranzas con RBAC
    - Admin: acceso completo
    - Gestor: crear, editar, ver cobranzas
    - Ejecutivo: solo lectura
    """
    queryset = Cobranza.objects.select_related('poliza', 'poliza__cliente').all()
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['estado', 'poliza', 'metodo_pago']
    search_fields = ['poliza__numero', 'poliza__cliente__rut', 'poliza__cliente__nombre', 'numero_documento']
    ordering_fields = ['fecha_emision', 'fecha_vencimiento', 'fecha_pago', 'monto_uf', 'estado']
    ordering = ['-fecha_emision']

    def get_serializer_class(self):
        if self.action == 'create':
            return CobranzaCreateSerializer
        elif self.action == 'registrar_pago':
            return CobranzaPagoSerializer
        return CobranzaSerializer

    def get_permissions(self):
        """Permisos dinámicos por acción"""
        if self.action in ['create', 'update', 'partial_update', 'registrar_pago', 'cancelar']:
            permission_classes = [permissions.IsAuthenticated]
        else:
            permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]
        return [permission() for permission in permission_classes]

    def perform_create(self, serializer):
        """Crear cobranza y registrar en auditoría"""
        cobranza = serializer.save(usuario_registro=self.request.user)
        
        # Registrar en auditoría
        AuditoriaAccion.registrar(
            usuario=self.request.user,
            accion='CREATE',
            modulo='cobranzas',
            modelo='Cobranza',
            descripcion=f'Se creó cobranza para póliza {cobranza.poliza.numero}',
            objeto_id=cobranza.id,
            datos_nuevos={'numero': cobranza.numero, 'estado': cobranza.estado, 'monto_uf': float(cobranza.monto_uf)},
            ip_address=get_client_ip(self.request),
            user_agent=self.request.META.get('HTTP_USER_AGENT', ''),
            metodo_http=self.request.method,
            url=self.request.path
        )

    @action(detail=False, methods=['get'])
    def pendientes(self, request):
        """Retorna solo las cobranzas pendientes"""
        cobranzas = self.queryset.filter(estado='PENDIENTE')
        serializer = self.get_serializer(cobranzas, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def vencidas(self, request):
        """Retorna cobranzas vencidas (fecha_vencimiento < hoy y estado != PAGADA)"""
        hoy = date.today()
        cobranzas = self.queryset.filter(
            fecha_vencimiento__lt=hoy
        ).exclude(estado__in=['PAGADA', 'CANCELADA'])
        serializer = self.get_serializer(cobranzas, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def por_vencer(self, request):
        """Retorna cobranzas que vencen en los próximos 7 días"""
        hoy = date.today()
        dias = int(request.query_params.get('dias', 7))
        fecha_limite = hoy + datetime.timedelta(days=dias)
        
        cobranzas = self.queryset.filter(
            fecha_vencimiento__gte=hoy,
            fecha_vencimiento__lte=fecha_limite,
            estado='PENDIENTE'
        )
        serializer = self.get_serializer(cobranzas, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def registrar_pago(self, request, pk=None):
        """Registra el pago de una cobranza"""
        cobranza = self.get_object()
        
        if cobranza.estado == 'PAGADA':
            # Registrar intento fallido
            AuditoriaAccion.registrar(
                usuario=request.user,
                accion='UPDATE',
                modulo='cobranzas',
                modelo='Cobranza',
                descripcion=f'Intento fallido: cobranza {cobranza.numero} ya estaba pagada',
                objeto_id=cobranza.id,
                exitoso=False,
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                metodo_http=request.method,
                url=request.path
            )
            return Response(
                {'error': 'Esta cobranza ya fue pagada'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        estado_anterior = cobranza.estado
        serializer = self.get_serializer(cobranza, data=request.data)
        if serializer.is_valid():
            serializer.save()
            
            # Registrar pago en auditoría
            AuditoriaAccion.registrar(
                usuario=request.user,
                accion='UPDATE',
                modulo='cobranzas',
                modelo='Cobranza',
                descripcion=f'Se registró pago para cobranza {cobranza.numero}',
                objeto_id=cobranza.id,
                datos_anteriores={'estado': estado_anterior},
                datos_nuevos={'estado': cobranza.estado, 'fecha_pago': str(cobranza.fecha_pago)},
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                metodo_http=request.method,
                url=request.path
            )
            
            return Response(
                CobranzaSerializer(cobranza).data,
                status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def cancelar(self, request, pk=None):
        """Cancela una cobranza"""
        cobranza = self.get_object()
        
        if cobranza.estado == 'PAGADA':
            AuditoriaAccion.registrar(
                usuario=request.user,
                accion='UPDATE',
                modulo='cobranzas',
                modelo='Cobranza',
                descripcion=f'Intento fallido: no se puede cancelar cobranza pagada {cobranza.numero}',
                objeto_id=cobranza.id,
                exitoso=False,
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                metodo_http=request.method,
                url=request.path
            )
            return Response(
                {'error': 'No se puede cancelar una cobranza pagada'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        estado_anterior = cobranza.estado
        motivo = request.data.get('motivo', 'Sin motivo')
        cobranza.estado = 'CANCELADA'
        cobranza.observaciones += f"\nCancelada el {date.today()}: {motivo}"
        cobranza.save()
        
        # Registrar cancelación en auditoría
        AuditoriaAccion.registrar(
            usuario=request.user,
            accion='UPDATE',
            modulo='cobranzas',
            modelo='Cobranza',
            descripcion=f'Se canceló cobranza {cobranza.numero}. Motivo: {motivo}',
            objeto_id=cobranza.id,
            datos_anteriores={'estado': estado_anterior},
            datos_nuevos={'estado': 'CANCELADA'},
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            metodo_http=request.method,
            url=request.path
        )
        
        return Response(
            CobranzaSerializer(cobranza).data,
            status=status.HTTP_200_OK
        )

    @action(detail=False, methods=['get'])
    def estadisticas(self, request):
        """Retorna estadísticas generales de cobranzas"""
        total = self.queryset.count()
        pendientes = self.queryset.filter(estado='PENDIENTE').count()
        pagadas = self.queryset.filter(estado='PAGADA').count()
        vencidas = self.queryset.filter(
            fecha_vencimiento__lt=date.today()
        ).exclude(estado__in=['PAGADA', 'CANCELADA']).count()
        
        # Montos
        from django.db.models import Sum
        monto_pendiente = self.queryset.filter(estado='PENDIENTE').aggregate(
            total=Sum('monto_uf')
        )['total'] or 0
        
        monto_pagado = self.queryset.filter(estado='PAGADA').aggregate(
            total=Sum('monto_uf')
        )['total'] or 0
        
        return Response({
            'total_cobranzas': total,
            'pendientes': pendientes,
            'pagadas': pagadas,
            'vencidas': vencidas,
            'canceladas': self.queryset.filter(estado='CANCELADA').count(),
            'monto_pendiente_uf': float(monto_pendiente),
            'monto_pagado_uf': float(monto_pagado),
            'tasa_cobro': round((pagadas / total * 100) if total > 0 else 0, 2)
        })
