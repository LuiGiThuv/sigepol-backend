from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin customizado para el modelo User con roles RBAC"""
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Información Personal', {'fields': ('first_name', 'last_name', 'email')}),
        ('Permisos y Roles', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions', 'role')
        }),
        ('Fechas Importantes', {'fields': ('last_login', 'date_joined', 'created_at', 'updated_at')}),
    )
    
    readonly_fields = ('last_login', 'date_joined', 'created_at', 'updated_at')
    
    list_display = ('username', 'email', 'get_full_name', 'role', 'is_active', 'created_at')
    list_filter = ('role', 'is_active', 'is_staff', 'created_at')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('-created_at',)
    
    actions = ['make_admin', 'make_gestor', 'make_ejecutivo', 'activate_users', 'deactivate_users']
    
    def make_admin(self, request, queryset):
        """Acción: Cambiar rol a Administrador"""
        updated = queryset.update(role='admin')
        self.message_user(request, f'{updated} usuarios cambiados a Administrador')
    make_admin.short_description = 'Cambiar a Administrador'
    
    def make_gestor(self, request, queryset):
        """Acción: Cambiar rol a Gestor"""
        updated = queryset.update(role='gestor')
        self.message_user(request, f'{updated} usuarios cambiados a Gestor')
    make_gestor.short_description = 'Cambiar a Gestor de Cobranzas'
    
    def make_ejecutivo(self, request, queryset):
        """Acción: Cambiar rol a Ejecutivo"""
        updated = queryset.update(role='ejecutivo')
        self.message_user(request, f'{updated} usuarios cambiados a Ejecutivo')
    make_ejecutivo.short_description = 'Cambiar a Ejecutivo'
    
    def activate_users(self, request, queryset):
        """Acción: Activar usuarios"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} usuarios activados')
    activate_users.short_description = 'Activar usuarios seleccionados'
    
    def deactivate_users(self, request, queryset):
        """Acción: Desactivar usuarios"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} usuarios desactivados')
    deactivate_users.short_description = 'Desactivar usuarios seleccionados'
