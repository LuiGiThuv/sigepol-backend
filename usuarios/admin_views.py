"""
PASO 13: Vistas de Administración de Usuarios con Políticas de Seguridad Avanzadas

Gestión completa de usuarios con:
- Auditoría detallada
- Permisos avanzados por rol
- Control de seguridad
- Políticas de RBAC
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Q
import secrets

from .serializers import (
    UserSerializer, UserDetailSerializer, UserAdminListSerializer,
    UserCreateSerializer, UserUpdateSerializer, UserPasswordChangeSerializer
)
from .permissions import IsAdmin, CanAccessAdminPanel, CanDeleteUser, CanModifyUser
from .audita import AuditoriaManager
from auditorias.models import AuditoriaAccion

User = get_user_model()


class AdminUserManagementViewSet(viewsets.ModelViewSet):
    """
    PASO 12: ViewSet para administración completa de usuarios
    
    Endpoints:
    - GET /api/admin/users/ - Listar todos los usuarios
    - POST /api/admin/users/ - Crear nuevo usuario
    - GET /api/admin/users/{id}/ - Ver detalles de usuario
    - PUT /api/admin/users/{id}/ - Actualizar usuario
    - PATCH /api/admin/users/{id}/ - Actualizar parcialmente
    - DELETE /api/admin/users/{id}/ - Eliminar usuario
    - POST /api/admin/users/{id}/deactivate/ - Suspender usuario
    - POST /api/admin/users/{id}/activate/ - Activar usuario
    - POST /api/admin/users/{id}/reset_password/ - Resetear contraseña
    - POST /api/admin/users/{id}/change_role/ - Cambiar rol
    - GET /api/admin/users/{id}/audit_history/ - Ver historial de auditoría
    - GET /api/admin/users/search/ - Buscar usuario
    - GET /api/admin/users/by_role/{role}/ - Listar por rol
    - GET /api/admin/users/activity_report/ - Reporte de actividad
    """
    
    queryset = User.objects.all().order_by('-created_at')
    permission_classes = [IsAdmin]
    
    def get_serializer_class(self):
        """Retornar serializer según la acción"""
        if self.action == 'list':
            return UserAdminListSerializer
        elif self.action == 'retrieve':
            return UserDetailSerializer
        elif self.action == 'create':
            return UserCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return UserUpdateSerializer
        return UserSerializer
    
    def list(self, request, *args, **kwargs):
        """Listar todos los usuarios con paginación"""
        response = super().list(request, *args, **kwargs)
        
        # Registrar en auditoría
        AuditoriaAccion.objects.create(
            usuario=request.user,
            accion="READ",
            modulo="usuarios",
            modelo="User",
            descripcion=f"El administrador {request.user.username} listó usuarios"
        )
        
        return response
    
    def create(self, request, *args, **kwargs):
        """
        Crear nuevo usuario con auditoría avanzada.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Registrar auditoría usando AuditoriaManager
        AuditoriaManager.registrar_creacion_usuario(
            usuario_admin=request.user,
            usuario_creado=user,
            datos=request.data
        )
        
        return Response(
            UserDetailSerializer(user).data,
            status=status.HTTP_201_CREATED
        )
    
    def update(self, request, *args, **kwargs):
        """Actualizar usuario completo"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        # Guardar cambios anteriores para auditoría
        old_values = {
            'email': instance.email,
            'first_name': instance.first_name,
            'last_name': instance.last_name,
            'role': instance.role,
            'is_active': instance.is_active
        }
        
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Detectar cambios
        changes = []
        new_values = {
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'role': user.role,
            'is_active': user.is_active
        }
        
        for field, new_value in new_values.items():
            if old_values[field] != new_value:
                changes.append(f"{field}: {old_values[field]} → {new_value}")
        
        # Registrar en auditoría
        if changes:
            AuditoriaAccion.objects.create(
                usuario=request.user,
                accion="UPDATE",
                modulo="usuarios",
                modelo="User",
                objeto_id=str(user.id),
                descripcion=f"El administrador {request.user.username} actualizó a {user.username}",
                datos_anteriores=old_values,
                datos_nuevos=new_values
            )
        
        return Response(UserDetailSerializer(user).data)
    
    def destroy(self, request, *args, **kwargs):
        """
        Eliminar usuario (soft delete: desactivar).
        Con auditoría avanzada.
        """
        instance = self.get_object()
        
        # Admin no puede desactivar su propia cuenta
        if instance.id == request.user.id:
            return Response(
                {'error': 'No puedes desactivar tu propia cuenta'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Registrar auditoría
        AuditoriaManager.registrar_desactivacion(
            usuario_admin=request.user,
            usuario_desactivado=instance
        )
        
        instance.is_active = False
        instance.save()
        
        return Response(
            {'message': f'Usuario {instance.username} desactivado exitosamente'},
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """
        Suspender/desactivar usuario con auditoría.
        """
        user = self.get_object()
        
        if user.id == request.user.id:
            return Response(
                {'error': 'No puedes desactivar tu propia cuenta'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Registrar auditoría
        AuditoriaManager.registrar_desactivacion(
            usuario_admin=request.user,
            usuario_desactivado=user
        )
        
        user.is_active = False
        user.save()
        
        return Response(
            {
                'message': f'Usuario {user.username} desactivado',
                'user': UserDetailSerializer(user).data
            },
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """
        Activar usuario suspendido con auditoría.
        """
        user = self.get_object()
        
        # Registrar auditoría
        AuditoriaManager.registrar_reactivacion(
            usuario_admin=request.user,
            usuario_reactivado=user
        )
        
        user.is_active = True
        user.save()
        
        return Response(
            {
                'message': f'Usuario {user.username} activado',
                'user': UserDetailSerializer(user).data
            },
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=['post'])
    def reset_password(self, request, pk=None):
        """
        Resetear contraseña de usuario a una contraseña temporal.
        Con auditoría.
        """
        user = self.get_object()
        
        # Generar contraseña temporal
        temporary_password = secrets.token_urlsafe(12)
        
        user.set_password(temporary_password)
        user.save()
        
        # Registrar auditoría
        AuditoriaManager.registrar_reset_password(
            usuario_admin=request.user,
            usuario_modificado=user
        )
        
        return Response(
            {
                'message': f'Contraseña reseteada para {user.username}',
                'temporary_password': temporary_password,
                'note': 'El usuario debe cambiar esta contraseña en el próximo login'
            },
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=['post'])
    def change_role(self, request, pk=None):
        """
        Cambiar rol de usuario con auditoría.
        """
        user = self.get_object()
        new_role = request.data.get('role')
        
        if not new_role:
            return Response(
                {'error': 'Campo "role" requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validar que sea un rol válido
        valid_roles = [role[0] for role in User.ROLE_CHOICES]
        if new_role not in valid_roles:
            return Response(
                {'error': f'Rol inválido. Roles válidos: {", ".join(valid_roles)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        old_role = user.role
        user.role = new_role
        user.save()
        
        # Registrar auditoría
        AuditoriaManager.registrar_cambio_rol(
            usuario_admin=request.user,
            usuario_modificado=user,
            rol_anterior=old_role,
            rol_nuevo=new_role
        )
        
        return Response(
            {
                'message': f'Rol de {user.username} cambiado a {new_role}',
                'user': UserDetailSerializer(user).data
            },
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=['get'])
    def audit_history(self, request, pk=None):
        """Ver historial de auditoría de un usuario"""
        user = self.get_object()
        
        # Obtener acciones del usuario y acciones sobre el usuario
        audit_logs = AuditoriaAccion.objects.filter(
            Q(usuario=user) | Q(objeto_id=str(user.id))
        ).order_by('-fecha_hora')[:50]  # Últimas 50 acciones
        
        # Serializar
        from auditorias.serializers import AuditoriaAccionSerializer
        
        serializer = AuditoriaAccionSerializer(audit_logs, many=True)
        
        return Response({
            'user': user.username,
            'audit_count': audit_logs.count(),
            'audit_logs': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def by_role(self, request):
        """Listar usuarios por rol específico"""
        role = request.query_params.get('role')
        
        if not role:
            return Response(
                {'error': 'Parámetro "role" requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        users = self.queryset.filter(role=role)
        
        # Auditoría
        AuditoriaAccion.objects.create(
            usuario=request.user,
            accion="READ",
            modulo="usuarios",
            modelo="User",
            descripcion=f"El administrador {request.user.username} filtró usuarios por rol: {role}"
        )
        
        serializer = UserAdminListSerializer(users, many=True)
        return Response({
            'role': role,
            'count': users.count(),
            'users': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        """Buscar usuarios por username, email o nombre"""
        query = request.query_params.get('q', '')
        
        if len(query) < 2:
            return Response(
                {'error': 'La búsqueda debe tener al menos 2 caracteres'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        users = self.queryset.filter(
            Q(username__icontains=query) |
            Q(email__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query)
        )[:20]  # Limitar a 20 resultados
        
        # Auditoría
        AuditoriaAccion.objects.create(
            usuario=request.user,
            accion="READ",
            modulo="usuarios",
            modelo="Usuario",
            descripcion=f"El administrador {request.user.username} buscó usuarios: '{query}' (encontrados: {users.count()})"
        )
        
        serializer = UserAdminListSerializer(users, many=True)
        return Response({
            'query': query,
            'count': users.count(),
            'users': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def activity_report(self, request):
        """
        Reporte de actividad de usuarios:
        - Total de usuarios
        - Usuarios activos/inactivos
        - Distribución por rol
        - Últimos logins
        """
        from django.utils import timezone
        from datetime import timedelta
        
        total_users = User.objects.count()
        active_users = User.objects.filter(is_active=True).count()
        inactive_users = User.objects.filter(is_active=False).count()
        
        # Distribución por rol
        role_distribution = {}
        for role_choice in User.ROLE_CHOICES:
            role_code = role_choice[0]
            role_name = role_choice[1]
            count = User.objects.filter(role=role_code).count()
            role_distribution[role_name] = count
        
        # Usuarios activos en últimos 7 días
        last_week = timezone.now() - timedelta(days=7)
        active_last_week = User.objects.filter(last_login__gte=last_week).count()
        
        # Usuarios creados en últimos 30 días
        last_month = timezone.now() - timedelta(days=30)
        created_last_month = User.objects.filter(created_at__gte=last_month).count()
        
        # Auditoría
        AuditoriaAccion.objects.create(
            usuario=request.user,
            accion="READ",
            modulo="usuarios",
            modelo="Usuario",
            descripcion=f"El administrador {request.user.username} consultó el reporte de actividad de usuarios"
        )
        
        return Response({
            'total_users': total_users,
            'active_users': active_users,
            'inactive_users': inactive_users,
            'role_distribution': role_distribution,
            'active_last_week': active_last_week,
            'created_last_month': created_last_month,
            'report_generated': timezone.now().isoformat()
        })
