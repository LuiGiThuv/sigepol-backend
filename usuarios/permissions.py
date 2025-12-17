from rest_framework.permissions import BasePermission, SAFE_METHODS
from functools import wraps
from rest_framework.response import Response
from rest_framework import status


# ============================================================================
# CLASES DE PERMISOS DRF
# ============================================================================


class IsAdmin(BasePermission):
    """
    Permiso: Solo administradores
    """
    message = 'Solo administradores pueden acceder a este recurso'
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_admin()


class IsGestor(BasePermission):
    """
    Permiso: Administradores y usuarios comerciales (reemplaza a gestores)
    """
    message = 'Solo administradores y usuarios comerciales pueden acceder a este recurso'
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_comercial()


class IsEjecutivo(BasePermission):
    """
    Permiso: Todos los usuarios autenticados
    """
    message = 'Debes estar autenticado para acceder a este recurso'
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated


class CanAccessAuditorias(BasePermission):
    """
    Permiso: Admin y Auditor pueden acceder a auditorías
    """
    message = 'Solo administradores y auditores pueden acceder a auditorías'
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.role in ['admin', 'auditor']


class IsAdminOrReadOnly(BasePermission):
    """
    Permiso: Admins pueden crear/editar/eliminar, otros solo lectura
    """
    
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        
        return request.user and request.user.is_authenticated and request.user.is_admin()


class IsGestorOrReadOnly(BasePermission):
    """
    Permiso: Usuarios comerciales pueden crear/editar/eliminar, otros solo lectura
    """
    
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        
        return request.user and request.user.is_authenticated and request.user.is_comercial()


class CanViewAllUsers(BasePermission):
    """
    Permiso: Solo admins pueden ver todos los usuarios, otros solo se ven a sí mismos
    """
    
    def has_object_permission(self, request, view, obj):
        # Admins ven todo
        if request.user.is_admin():
            return True
        
        # Otros solo ven su propio perfil
        return obj == request.user


class RoleBasedPermission(BasePermission):
    """
    Permiso basado en roles dinámicos
    Uso: permission_classes = [RoleBasedPermission]
    En la vista: role_permissions = {'GET': ['admin', 'gestor'], 'POST': ['admin']}
    """
    message = 'No tienes permiso para realizar esta acción'
    
    def has_permission(self, request, view):
        # Si no está autenticado
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Si la vista define permisos de rol
        if hasattr(view, 'role_permissions'):
            allowed_roles = view.role_permissions.get(request.method, [])
            return request.user.role in allowed_roles
        
        # Si no está configurado, permitir autenticados
        return True


# ========== POLÍTICAS DE SEGURIDAD PASO 13 ==========

class CanAccessAdminPanel(BasePermission):
    """
    Solo admin puede acceder al panel administrativo.
    """
    message = "Acceso denegado. Solo administradores pueden acceder al panel."

    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role == 'admin'
        )


class CanAccessAnalytics(BasePermission):
    """
    Admin y Comercial pueden acceder a analytics.
    """
    message = "Se requiere rol de Usuario Comercial o superior para acceder a analytics."

    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role in ['admin', 'comercial']
        )


class CanUploadFiles(BasePermission):
    """
    Todos los usuarios autenticados pueden subir archivos.
    """
    message = "Se requiere autenticación para subir archivos."

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated


class CanAccessAlerts(BasePermission):
    """
    Admin y Comercial pueden acceder a alertas críticas.
    """
    message = "Se requiere rol de Usuario Comercial o superior para acceder a alertas."

    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role in ['admin', 'comercial']
        )


class CanAccessSystemLogs(BasePermission):
    """
    Solo admin puede acceder a logs del sistema.
    """
    message = "Solo administradores pueden acceder a logs."

    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role == 'admin'
        )


class CanModifyUser(BasePermission):
    """
    Permite modificar usuario solo si:
    - Es admin, O
    - Es el usuario modificando su propio perfil (sin cambiar rol)
    """
    message = "No tienes permisos para modificar este usuario."

    def has_object_permission(self, request, view, obj):
        # Admin puede modificar a cualquiera
        if request.user.role == 'admin':
            return True
        
        # Usuario puede modificar su propio perfil (excepto rol)
        if request.user == obj:
            # Si intenta cambiar rol, rechazar
            if 'role' in request.data and request.data['role'] != obj.role:
                return False
            return True
        
        return False


class CanDeleteUser(BasePermission):
    """
    Solo admin puede "eliminar" usuarios (soft delete).
    Admin no puede desactivar su propia cuenta.
    """
    message = "Solo administradores pueden desactivar usuarios."

    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role == 'admin'
        )
    
    def has_object_permission(self, request, view, obj):
        # Admin no puede desactivar a sí mismo
        if request.user == obj:
            return False
        return True


class IsOwnerOrAdmin(BasePermission):
    """
    Propietario del objeto o admin pueden acceder.
    """
    message = "No tienes permiso para acceder a este recurso."

    def has_object_permission(self, request, view, obj):
        # Admin siempre tiene permiso
        if request.user.role == 'admin':
            return True
        
        # Usuario puede acceder a su propio objeto
        if hasattr(obj, 'user') and obj.user == request.user:
            return True
        
        if hasattr(obj, 'owner') and obj.owner == request.user:
            return True
        
        return False


# ============================================================================
# DECORADORES PARA VISTAS
# ============================================================================

def require_role(*allowed_roles):
    """
    Decorador para proteger vistas basado en roles
    
    Uso:
        @require_role('admin', 'comercial')
        def mi_vista(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not hasattr(request, 'user') or not request.user.is_authenticated:
                return Response(
                    {'error': 'Usuario no autenticado'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            if request.user.role not in allowed_roles:
                return Response(
                    {
                        'error': 'Permiso denegado',
                        'detalle': f'Se requiere uno de estos roles: {", ".join(allowed_roles)}'
                    },
                    status=status.HTTP_403_FORBIDDEN
                )
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def require_admin(view_func):
    """Decorador para requerir rol de admin"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return Response(
                {'error': 'Usuario no autenticado'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        if request.user.role != 'admin':
            return Response(
                {'error': 'Se requiere rol de administrador'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        return view_func(request, *args, **kwargs)
    return wrapper


# ============================================================================
# CLASE MIXIN PARA VIEWSETS
# ============================================================================

class RoleBasedAccessMixin:
    """
    Mixin para ViewSets que requieren control de rol.
    
    Ejemplo:
        class MiViewSet(RoleBasedAccessMixin, ModelViewSet):
            required_role_for_create = 'comercial'
            required_role_for_destroy = 'admin'
    """
    
    required_role_for_list = None
    required_role_for_retrieve = None
    required_role_for_create = None
    required_role_for_update = None
    required_role_for_partial_update = None
    required_role_for_destroy = None
    
    def check_role_permission(self, action):
        """Verifica si el usuario tiene permiso para la acción"""
        from rest_framework.exceptions import PermissionDenied
        
        role_required = getattr(self, f'required_role_for_{action}', None)
        
        if role_required is None:
            return True
        
        if not self.request.user.is_authenticated:
            raise PermissionDenied('Usuario no autenticado')
        
        user_role = self.request.user.role
        
        # Admin tiene acceso a todo
        if user_role == 'admin':
            return True
        
        # Verificar rol específico
        if isinstance(role_required, (list, tuple)):
            if user_role not in role_required:
                raise PermissionDenied(
                    f'Se requiere uno de estos roles: {", ".join(role_required)}'
                )
        else:
            if user_role != role_required:
                raise PermissionDenied(f'Se requiere rol: {role_required}')
        
        return True
    
    def list(self, request, *args, **kwargs):
        self.check_role_permission('list')
        return super().list(request, *args, **kwargs)
    
    def retrieve(self, request, *args, **kwargs):
        self.check_role_permission('retrieve')
        return super().retrieve(request, *args, **kwargs)
    
    def create(self, request, *args, **kwargs):
        self.check_role_permission('create')
        return super().create(request, *args, **kwargs)
    
    def update(self, request, *args, **kwargs):
        self.check_role_permission('update')
        return super().update(request, *args, **kwargs)
    
    def partial_update(self, request, *args, **kwargs):
        self.check_role_permission('partial_update')
        return super().partial_update(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        self.check_role_permission('destroy')
        return super().destroy(request, *args, **kwargs)

# ============================================================================
# FUNCIONES HELPER
# ============================================================================

def get_user_permissions(user):
    """
    Retorna un diccionario con los permisos disponibles para un usuario
    
    Retorna:
        {
            'puede_crear_uploads': True,
            'puede_procesar_ml': False,
            'puede_ver_auditorias': True,
            ...
        }
    """
    if user.role == 'admin':
        return {
            'puede_crear_uploads': True,
            'puede_procesar_ml': True,
            'puede_ver_auditorias': True,
            'puede_cambiar_roles': True,
            'puede_descargar_excel': True,
            'puede_ver_errores': True,
        }
    
    elif user.role == 'comercial':
        return {
            'puede_crear_uploads': True,
            'puede_procesar_ml': False,
            'puede_ver_auditorias': False,
            'puede_cambiar_roles': False,
            'puede_descargar_excel': True,
            'puede_ver_errores': True,
        }
    
    else:  # auditor
        return {
            'puede_crear_uploads': False,
            'puede_procesar_ml': False,
            'puede_ver_auditorias': True,
            'puede_cambiar_roles': False,
            'puede_descargar_excel': False,
            'puede_ver_errores': True,
        }