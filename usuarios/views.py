from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.auth import get_user_model

from .serializers import (
    UserSerializer, UserCreateSerializer, UserUpdateSerializer,
    CustomTokenObtainPairSerializer
)
from .permissions import IsAdmin

User = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar usuarios con RBAC
    
    Endpoints:
    - GET /api/users/ - Listar usuarios (admins ver todos, otros solo su perfil)
    - POST /api/users/ - Crear usuario (solo admins)
    - GET /api/users/{id}/ - Detalle usuario
    - PUT /api/users/{id}/ - Actualizar usuario
    - DELETE /api/users/{id}/ - Eliminar usuario (solo admins)
    - GET /api/users/me/ - Ver perfil actual
    - PUT /api/users/me/ - Actualizar perfil
    - POST /api/users/change_password/ - Cambiar contraseña
    - GET /api/users/by_role/ - Listar por rol
    """
    
    queryset = User.objects.all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['role', 'is_active']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering_fields = ['created_at', 'username', 'role']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        """Retornar serializer según la acción"""
        if self.action == 'create':
            return UserCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return UserUpdateSerializer
        return UserSerializer
    
    def get_permissions(self):
        """Permisos dinámicos según la acción"""
        if self.action == 'create':
            permission_classes = [IsAdmin]
        elif self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [IsAdmin]
        elif self.action in ['me', 'update_me', 'change_password']:
            permission_classes = [IsAuthenticated]
        elif self.action in ['list', 'retrieve']:
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = [IsAdmin]
        
        return [permission() for permission in permission_classes]
    
    def list(self, request, *args, **kwargs):
        """
        Listar usuarios.
        - Admins ven todos
        - Otros ven solo su perfil
        """
        if request.user.is_admin():
            return super().list(request, *args, **kwargs)
        
        # No-admins solo ven su perfil
        self.queryset = User.objects.filter(id=request.user.id)
        return super().list(request, *args, **kwargs)
    
    @action(detail=False, methods=['get', 'put', 'patch'], permission_classes=[IsAuthenticated])
    def me(self, request):
        """
        GET: Obtener perfil del usuario actual
        PUT/PATCH: Actualizar perfil actual
        """
        user = request.user
        
        if request.method in ['PUT', 'PATCH']:
            serializer = UserUpdateSerializer(user, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(UserSerializer(user).data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = UserSerializer(user)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def change_password(self, request):
        """Cambiar contraseña del usuario autenticado"""
        user = request.user
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')
        new_password_confirm = request.data.get('new_password_confirm')
        
        # Validaciones
        if not old_password or not new_password or not new_password_confirm:
            return Response(
                {'error': 'Todos los campos son requeridos'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verificar contraseña actual
        if not user.check_password(old_password):
            return Response(
                {'error': 'Contraseña actual incorrecta'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verificar que nuevas contraseñas coincidan
        if new_password != new_password_confirm:
            return Response(
                {'error': 'Las nuevas contraseñas no coinciden'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Cambiar contraseña
        user.set_password(new_password)
        user.save()
        
        return Response({'success': 'Contraseña actualizada'}, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'])
    def by_role(self, request):
        """Listar usuarios por rol (solo admins)"""
        if not request.user.is_admin():
            return Response(
                {'error': 'Solo administradores pueden ver usuarios por rol'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        role = request.query_params.get('role')
        if not role:
            return Response(
                {'error': 'Parámetro "role" requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        users = User.objects.filter(role=role)
        serializer = self.get_serializer(users, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdmin])
    def activate(self, request, pk=None):
        """Activar usuario (solo admins)"""
        user = self.get_object()
        user.is_active = True
        user.save()
        
        return Response(
            {'success': f'Usuario {user.username} activado'},
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdmin])
    def deactivate(self, request, pk=None):
        """Desactivar usuario (solo admins)"""
        user = self.get_object()
        user.is_active = False
        user.save()
        
        return Response(
            {'success': f'Usuario {user.username} desactivado'},
            status=status.HTTP_200_OK
        )

