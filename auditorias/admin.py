from django.contrib import admin
from django.utils import timezone
from datetime import timedelta
from .models import AuditoriaAccion, LogAcceso, AuditLog
from django.utils.html import format_html
from django.urls import reverse, path
from django.utils.safestring import mark_safe
from django.template.response import TemplateResponse
from django.db.models import Count, Q
import json


# ============================================================================
# VISTAS PERSONALIZADAS DEL ADMIN (MÓDULO 1: PASO 1.4)
# ============================================================================

class VistaSeguridadAdmin(admin.AdminSite):
    """
    Admin site personalizado con vistas de seguridad
    """
    site_header = "🔐 Panel de Seguridad - SIGEPOL"
    site_title = "Seguridad"
    index_title = "Centro de Seguridad"
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('seguridad/', self.admin_site.admin_view(self.vista_seguridad), name='vista_seguridad'),
        ]
        return custom_urls + urls
    
    def vista_seguridad(self, request):
        """Vista personalizada con dashboard de seguridad"""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        # Obtener estadísticas
        ahora = timezone.now()
        hace_24h = ahora - timedelta(hours=24)
        hace_7d = ahora - timedelta(days=7)
        
        # Accesos en últimas 24 horas
        accesos_24h = LogAcceso.objects.filter(timestamp__gte=hace_24h).count()
        accesos_fallidos_24h = LogAcceso.objects.filter(
            timestamp__gte=hace_24h,
            resultado__in=['FALLIDO', 'BLOQUEADO']
        ).count()
        
        # Auditorías en últimas 24 horas
        cambios_24h = AuditoriaAccion.objects.filter(fecha_hora__gte=hace_24h).count()
        
        # Usuarios activos en últimas 24 horas
        usuarios_activos = LogAcceso.objects.filter(
            timestamp__gte=hace_24h,
            resultado='EXITOSO'
        ).values('usuario').distinct().count()
        
        # IPs sospechosas (múltiples fallos)
        ips_sospechosas = LogAcceso.objects.filter(
            timestamp__gte=hace_24h,
            resultado__in=['FALLIDO', 'BLOQUEADO']
        ).values('ip_address').annotate(count=Count('id')).filter(count__gte=5)
        
        # Usuarios con cambios recientes
        usuarios_cambios = AuditoriaAccion.objects.filter(
            fecha_hora__gte=hace_7d
        ).values('usuario__username').annotate(count=Count('id')).order_by('-count')[:10]
        
        # Últimos logins
        ultimos_logins = LogAcceso.objects.filter(
            resultado='EXITOSO',
            endpoint__icontains='login'
        ).order_by('-timestamp')[:10]
        
        context = {
            'accesos_24h': accesos_24h,
            'accesos_fallidos_24h': accesos_fallidos_24h,
            'cambios_24h': cambios_24h,
            'usuarios_activos': usuarios_activos,
            'ips_sospechosas': ips_sospechosas,
            'usuarios_cambios': usuarios_cambios,
            'ultimos_logins': ultimos_logins,
            'title': 'Vista de Seguridad',
        }
        
        return TemplateResponse(
            request,
            'admin/seguridad/vista_seguridad.html',
            context
        )



@admin.register(AuditoriaAccion)
class AuditoriaAccionAdmin(admin.ModelAdmin):
    list_display = ['usuario_link', 'accion_badge', 'modulo', 'modelo', 'objeto_id', 'exitoso_badge', 'fecha_hora']
    list_filter = ['accion', 'modulo', 'modelo', 'exitoso', 'rol_usuario', 'fecha_hora']
    search_fields = ['usuario__username', 'usuario__email', 'descripcion', 'objeto_id']
    readonly_fields = ['usuario', 'accion', 'modulo', 'modelo', 'objeto_id', 'descripcion',
                       'datos_anteriores_display', 'datos_nuevos_display', 'ip_address', 
                       'user_agent', 'metodo_http', 'url', 'fecha_hora', 'exitoso', 
                       'mensaje_error', 'rol_usuario']
    
    fieldsets = (
        ('Usuario & Acción', {
            'fields': ('usuario', 'accion', 'rol_usuario', 'fecha_hora')
        }),
        ('Detalles de la Acción', {
            'fields': ('modulo', 'modelo', 'objeto_id', 'descripcion')
        }),
        ('Datos Modificados', {
            'fields': ('datos_anteriores_display', 'datos_nuevos_display'),
            'classes': ('collapse',)
        }),
        ('Información Técnica', {
            'fields': ('ip_address', 'user_agent', 'metodo_http', 'url'),
            'classes': ('collapse',)
        }),
        ('Estado', {
            'fields': ('exitoso', 'mensaje_error')
        }),
    )

    def usuario_link(self, obj):
        if obj.usuario:
            url = reverse('admin:usuarios_user_change', args=[obj.usuario.id])
            return format_html('<a href="{}">{}</a>', url, obj.usuario.username)
        return '-'
    usuario_link.short_description = 'Usuario'

    def accion_badge(self, obj):
        color_map = {
            'CREATE': '#2ecc71',
            'UPDATE': '#3498db',
            'DELETE': '#e74c3c',
            'READ': '#95a5a6',
            'LOGIN': '#27ae60',
            'LOGOUT': '#34495e',
            'PERMISSION_DENIED': '#c0392b',
            'ROLE_CHANGE': '#f39c12',
            'PASSWORD_CHANGE': '#9b59b6',
        }
        color = color_map.get(obj.accion, '#95a5a6')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-weight: bold;">{}</span>',
            color, obj.get_accion_display()
        )
    accion_badge.short_description = 'Acción'

    def exitoso_badge(self, obj):
        if obj.exitoso:
            return format_html('<span style="color: green; font-weight: bold;">✓ Exitoso</span>')
        return format_html('<span style="color: red; font-weight: bold;">✗ Fallido</span>')
    exitoso_badge.short_description = 'Estado'

    def datos_anteriores_display(self, obj):
        if obj.datos_anteriores:
            return format_html('<pre>{}</pre>', json.dumps(obj.datos_anteriores, indent=2, ensure_ascii=False))
        return '-'
    datos_anteriores_display.short_description = 'Datos Anteriores'

    def datos_nuevos_display(self, obj):
        if obj.datos_nuevos:
            return format_html('<pre>{}</pre>', json.dumps(obj.datos_nuevos, indent=2, ensure_ascii=False))
        return '-'
    datos_nuevos_display.short_description = 'Datos Nuevos'

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(LogAcceso)
class LogAccesoAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'ip_address', 'endpoint', 'metodo', 'resultado_badge', 'codigo_estado', 'timestamp']
    list_filter = ['resultado', 'metodo', 'codigo_estado', 'timestamp']
    search_fields = ['usuario__username', 'ip_address', 'endpoint']
    readonly_fields = ['usuario', 'ip_address', 'endpoint', 'metodo', 'resultado', 'codigo_estado', 
                       'mensaje', 'user_agent', 'timestamp']

    fieldsets = (
        ('Información del Acceso', {
            'fields': ('usuario', 'timestamp', 'ip_address', 'endpoint', 'metodo')
        }),
        ('Resultado', {
            'fields': ('resultado', 'codigo_estado', 'mensaje')
        }),
        ('User Agent', {
            'fields': ('user_agent',),
            'classes': ('collapse',)
        }),
    )

    def resultado_badge(self, obj):
        color_map = {
            'EXITOSO': '#2ecc71',
            'FALLIDO': '#e74c3c',
            'BLOQUEADO': '#f39c12',
        }
        color = color_map.get(obj.resultado, '#95a5a6')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            color, obj.resultado
        )
    resultado_badge.short_description = 'Resultado'

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'accion_badge', 'descripcion_short', 'fecha_creacion']
    list_filter = ['accion', 'fecha_creacion']
    search_fields = ['descripcion', 'usuario__username']
    readonly_fields = ['usuario', 'accion', 'descripcion', 'fecha_creacion', 'detalles_json']
    
    fieldsets = (
        ('Información', {
            'fields': ('usuario', 'accion', 'fecha_creacion')
        }),
        ('Descripción', {
            'fields': ('descripcion',)
        }),
        ('Detalles', {
            'fields': ('detalles_json',),
            'classes': ('collapse',)
        }),
    )

    def descripcion_short(self, obj):
        return obj.descripcion[:50] + '...' if len(obj.descripcion) > 50 else obj.descripcion
    descripcion_short.short_description = 'Descripción'

    def accion_badge(self, obj):
        color_map = {
            'login': '#2ecc71',
            'upload': '#3498db',
            'process': '#f39c12',
            'view': '#95a5a6',
            'update': '#9b59b6',
            'delete': '#e74c3c',
            'ml_run': '#e67e22',
            'report_generate': '#1abc9c',
            'export': '#34495e',
        }
        color = color_map.get(obj.accion, '#95a5a6')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            color, obj.get_accion_display()
        )
    accion_badge.short_description = 'Acción'

    def detalles_json(self, obj):
        if obj.detalles:
            return format_html('<pre>{}</pre>', json.dumps(obj.detalles, indent=2, ensure_ascii=False))
        return '-'
    detalles_json.short_description = 'Detalles'

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False
