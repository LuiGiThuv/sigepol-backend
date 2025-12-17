from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from datetime import timedelta, date
from django.db.models import Count, Q

from .models import AuditoriaAccion, LogAcceso, AuditLog
from .serializers import AuditoriaAccionSerializer, LogAccesoSerializer
from usuarios.permissions import IsAdmin, IsGestor, CanAccessAuditorias
from importaciones.models import DataUpload
from django.contrib.auth import get_user_model

User = get_user_model()


def get_client_ip(request):
    """Obtiene la IP del cliente desde la request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


class AuditoriaViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para auditoría (solo lectura)
    - Admins: ven todas las auditorías
    - Gestores: ven solo sus propias auditorías
    - Ejecutivos: no tienen acceso
    """
    queryset = AuditoriaAccion.objects.all()
    serializer_class = AuditoriaAccionSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['usuario', 'accion', 'modulo', 'modelo', 'exitoso', 'rol_usuario']
    search_fields = ['descripcion', 'usuario__username', 'usuario__email', 'objeto_id']
    ordering_fields = ['fecha_hora', 'accion', 'usuario']
    ordering = ['-fecha_hora']

    def get_permissions(self):
        """Admin y Auditor acceden a auditoría"""
        return [permissions.IsAuthenticated(), CanAccessAuditorias()]

    def get_queryset(self):
        """
        - Admins: ven todas
        - Gestores: ven solo sus acciones
        - Otros: no ven nada (filtrado por permiso)
        """
        user = self.request.user
        if user.role == 'admin':
            return AuditoriaAccion.objects.all()
        return AuditoriaAccion.objects.filter(usuario=user)

    @action(detail=False, methods=['get'])
    def mias(self, request):
        """Auditorías del usuario actual"""
        auditorias = AuditoriaAccion.objects.filter(usuario=request.user)
        serializer = self.get_serializer(auditorias, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def por_usuario(self, request):
        """Auditorías de un usuario específico (solo admin)"""
        if request.user.role != 'admin':
            return Response(
                {'detail': 'Solo administradores pueden ver auditorías de otros usuarios'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        usuario_id = request.query_params.get('usuario_id')
        if not usuario_id:
            return Response(
                {'detail': 'Parámetro usuario_id requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        auditorias = AuditoriaAccion.objects.filter(usuario_id=usuario_id)
        serializer = self.get_serializer(auditorias, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def por_modulo(self, request):
        """Auditorías filtradas por módulo"""
        modulo = request.query_params.get('modulo')
        if not modulo:
            return Response(
                {'detail': 'Parámetro modulo requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if request.user.role == 'admin':
            auditorias = AuditoriaAccion.objects.filter(modulo=modulo)
        else:
            auditorias = AuditoriaAccion.objects.filter(modulo=modulo, usuario=request.user)
        
        serializer = self.get_serializer(auditorias, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def cambios_recientes(self, request):
        """Cambios en las últimas 24 horas (solo admin)"""
        if request.user.role != 'admin':
            return Response(
                {'detail': 'Solo administradores pueden ver este reporte'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        hace_24h = timezone.now() - timedelta(hours=24)
        auditorias = AuditoriaAccion.objects.filter(
            fecha_hora__gte=hace_24h,
            accion__in=['CREATE', 'UPDATE', 'DELETE']
        )
        serializer = self.get_serializer(auditorias, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def accesos_denegados(self, request):
        """Intentos de acceso denegado (solo admin)"""
        if request.user.role != 'admin':
            return Response(
                {'detail': 'Solo administradores pueden ver este reporte'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        auditorias = AuditoriaAccion.objects.filter(accion='PERMISSION_DENIED')
        serializer = self.get_serializer(auditorias, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def estadisticas(self, request):
        """Estadísticas de auditoría (solo admin)"""
        if request.user.role != 'admin':
            return Response(
                {'detail': 'Solo administradores pueden ver estadísticas'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        total = AuditoriaAccion.objects.count()
        acciones = AuditoriaAccion.objects.values('accion').distinct().count()
        usuarios_activos = AuditoriaAccion.objects.values('usuario').distinct().count()
        hoy = timezone.now().date()
        acciones_hoy = AuditoriaAccion.objects.filter(fecha_hora__date=hoy).count()
        
        return Response({
            'total_auditorias': total,
            'tipos_acciones': acciones,
            'usuarios_activos': usuarios_activos,
            'acciones_hoy': acciones_hoy,
            'ultimas_24h': AuditoriaAccion.objects.filter(
                fecha_hora__gte=timezone.now() - timedelta(hours=24)
            ).count()
        })


class LogAccesoViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para logs de acceso (solo admin)
    """
    queryset = LogAcceso.objects.all()
    serializer_class = LogAccesoSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['usuario', 'ip_address', 'resultado', 'metodo']
    search_fields = ['endpoint', 'ip_address', 'usuario__username']
    ordering_fields = ['timestamp', 'resultado']
    ordering = ['-timestamp']

    def get_permissions(self):
        """Admin y Auditor acceden"""
        return [permissions.IsAuthenticated(), CanAccessAuditorias()]

    @action(detail=False, methods=['get'])
    def ips_sospechosas(self, request):
        """IPs con múltiples accesos fallidos"""
        if request.user.role != 'admin':
            return Response(
                {'detail': 'Solo administradores'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        from django.db.models import Count
        ips_fallidas = LogAcceso.objects.filter(
            resultado='FALLIDO'
        ).values('ip_address').annotate(
            intentos=Count('id')
        ).filter(intentos__gte=5).order_by('-intentos')
        
        return Response(ips_fallidas)

    @action(detail=False, methods=['get'])
    def ultimos_accesos(self, request):
        """Últimos 50 accesos"""
        logs = self.queryset[:50]
        serializer = self.get_serializer(logs, many=True)
        return Response(serializer.data)


class AdminStatsView(APIView):
    """
    Vista para obtener estadísticas del administrador
    Accesible por admin y auditor
    """
    permission_classes = [permissions.IsAuthenticated, CanAccessAuditorias]

    def get(self, request):
        """
        Retorna estadísticas del sistema:
        - Total de usuarios
        - Total de acciones auditadas
        - Total de accesos registrados
        - Total de cargas
        - Cargas hoy
        - Cargas con error
        """
        from django.db.models import Count
        
        total_users = User.objects.count()
        total_acciones = AuditoriaAccion.objects.count()
        total_accesos = LogAcceso.objects.count()
        total_uploads = DataUpload.objects.count()
        uploads_today = DataUpload.objects.filter(
            fecha_carga__date=date.today()
        ).count()
        uploads_error = DataUpload.objects.filter(estado='error').count()
        
        # Agrupar cargas por estado
        uploads_by_status = DataUpload.objects.values('estado').annotate(
            count=Count('id')
        ).order_by('-count')
        
        return Response({
            'total_usuarios': total_users,
            'total_acciones': total_acciones,
            'total_accesos': total_accesos,
            'total_cargas': total_uploads,
            'cargas_hoy': uploads_today,
            'cargas_con_error': uploads_error,
            'cargas_por_estado': list(uploads_by_status),
        })


class RecentUploadsView(APIView):
    """
    Vista para ver cargas recientes
    Accesible por todos los usuarios autenticados
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """
        Retorna últimas 50 cargas con detalles
        """
        uploads = DataUpload.objects.select_related('cargado_por').order_by(
            '-fecha_carga'
        )[:50]
        
        data = [{
            'id': u.id,
            'archivo': u.archivo.name,
            'estado': u.estado,
            'estado_display': u.get_estado_display(),
            'cargado_por': u.cargado_por.username if u.cargado_por else 'N/A',
            'fecha_carga': u.fecha_carga,
            'mensaje_error': u.mensaje_error,
            'detalles': u.detalles_procesamiento,
        } for u in uploads]
        
        return Response(data)


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para logs de auditoría simples
    - Admins: ven todos
    - Gestores: ven solo sus propios logs
    """
    queryset = AuditLog.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['usuario', 'accion']
    search_fields = ['descripcion', 'usuario__username']
    ordering_fields = ['fecha_creacion', 'accion']
    ordering = ['-fecha_creacion']

    def get_queryset(self):
        """
        Admins ven todos, gestores ven solo los suyos
        """
        user = self.request.user
        if user.role == 'admin':
            return AuditLog.objects.all()
        return AuditLog.objects.filter(usuario=user)

    def list(self, request, *args, **kwargs):
        """
        Override para retornar formato simples
        """
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            data = [{
                'id': log.id,
                'usuario': log.usuario.username if log.usuario else 'N/A',
                'accion': log.accion,
                'accion_display': log.get_accion_display(),
                'descripcion': log.descripcion,
                'fecha_creacion': log.fecha_creacion,
                'detalles': log.detalles,
            } for log in page]
            return self.get_paginated_response(data)

        data = [{
            'id': log.id,
            'usuario': log.usuario.username if log.usuario else 'N/A',
            'accion': log.accion,
            'accion_display': log.get_accion_display(),
            'descripcion': log.descripcion,
            'fecha_creacion': log.fecha_creacion,
            'detalles': log.detalles,
        } for log in queryset]
        return Response(data)
