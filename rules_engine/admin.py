from django.contrib import admin
from django.utils.html import format_html
from .models import Rule, RuleExecution


class RuleExecutionInline(admin.TabularInline):
    """Inline para ver historial de ejecuciones de una regla"""
    model = RuleExecution
    extra = 0
    readonly_fields = ('inicio', 'fin', 'duracion_segundos', 'estado', 'resultado', 'error_mensaje')
    fields = ('inicio', 'fin', 'duracion_segundos', 'estado')
    can_delete = False
    
    def get_queryset(self, request):
        # Mostrar solo las últimas 10 ejecuciones
        qs = super().get_queryset(request)
        return qs.order_by('-inicio')[:10]


@admin.register(Rule)
class RuleAdmin(admin.ModelAdmin):
    """Admin para gestionar reglas del motor"""
    
    list_display = (
        'codigo',
        'nombre',
        'estado_badge',
        'tipo',
        'ultima_ejecucion',
        'tasa_exito_badge',
        'total_ejecuciones'
    )
    
    list_filter = (
        'activa',
        'tipo',
        'creada_en',
        'ultima_ejecucion'
    )
    
    search_fields = ('codigo', 'nombre', 'descripcion')
    
    readonly_fields = (
        'creada_en',
        'modificada_en',
        'total_ejecuciones',
        'ejecuciones_exitosas',
        'ejecuciones_fallidas',
        'tasa_exito',
        'ultima_ejecucion',
        'proximo_resultado',
        'proximo_error'
    )
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('nombre', 'codigo', 'descripcion', 'tipo')
        }),
        ('Control', {
            'fields': ('activa', 'orden_ejecucion')
        }),
        ('Configuración', {
            'fields': ('parametros',),
            'description': 'Parámetros en formato JSON para configurar el comportamiento de la regla'
        }),
        ('Ejecución', {
            'fields': (
                'ultima_ejecucion',
                'proxima_ejecucion',
                'proximo_resultado',
                'proximo_error'
            ),
            'classes': ('collapse',)
        }),
        ('Estadísticas', {
            'fields': (
                'total_ejecuciones',
                'ejecuciones_exitosas',
                'ejecuciones_fallidas',
                'tasa_exito'
            ),
            'classes': ('collapse',)
        }),
        ('Auditoría', {
            'fields': ('creada_en', 'modificada_en'),
            'classes': ('collapse',)
        })
    )
    
    inlines = [RuleExecutionInline]
    
    def estado_badge(self, obj):
        """Mostrar estado con badge de color"""
        if obj.activa:
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 3px 8px; border-radius: 3px;">ACTIVA</span>'
            )
        else:
            return format_html(
                '<span style="background-color: #6c757d; color: white; padding: 3px 8px; border-radius: 3px;">INACTIVA</span>'
            )
    estado_badge.short_description = 'Estado'
    
    def tasa_exito_badge(self, obj):
        """Mostrar tasa de éxito con color basado en porcentaje"""
        tasa = obj.tasa_exito
        
        if tasa >= 95:
            color = '#28a745'  # Verde
        elif tasa >= 80:
            color = '#ffc107'  # Amarillo
        else:
            color = '#dc3545'  # Rojo
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{:.1f}%</span>',
            color, tasa
        )
    tasa_exito_badge.short_description = 'Tasa Éxito'
    
    def proximo_resultado(self, obj):
        """Mostrar último resultado de forma legible"""
        if obj.ultimo_resultado:
            return str(obj.ultimo_resultado)[:200] + "..." if len(str(obj.ultimo_resultado)) > 200 else str(obj.ultimo_resultado)
        return "-"
    proximo_resultado.short_description = 'Último Resultado'
    
    def proximo_error(self, obj):
        """Mostrar último error si existe"""
        if obj.ultimo_error:
            return format_html(
                '<span style="color: #dc3545;">{}</span>',
                str(obj.ultimo_error)[:200] + "..." if len(str(obj.ultimo_error)) > 200 else str(obj.ultimo_error)
            )
        return "-"
    proximo_error.short_description = 'Último Error'
    
    def get_readonly_fields(self, request, obj=None):
        """Si es nuevo, permitir editar todos los campos"""
        if obj is None:
            return ()
        return self.readonly_fields


@admin.register(RuleExecution)
class RuleExecutionAdmin(admin.ModelAdmin):
    """Admin para ver historial de ejecuciones"""
    
    list_display = (
        'regla',
        'inicio',
        'fin',
        'duracion_segundos',
        'estado_badge'
    )
    
    list_filter = (
        'estado',
        'regla',
        'inicio'
    )
    
    search_fields = ('regla__codigo', 'regla__nombre', 'error_mensaje')
    
    readonly_fields = (
        'regla',
        'inicio',
        'fin',
        'duracion_segundos',
        'estado',
        'resultado',
        'error_mensaje',
        'error_traceback',
        'parametros_utilizados'
    )
    
    fieldsets = (
        ('Regla', {
            'fields': ('regla',)
        }),
        ('Ejecución', {
            'fields': ('inicio', 'fin', 'duracion_segundos', 'estado')
        }),
        ('Resultado', {
            'fields': ('resultado', 'parametros_utilizados'),
            'classes': ('collapse',)
        }),
        ('Error', {
            'fields': ('error_mensaje', 'error_traceback'),
            'classes': ('collapse',)
        })
    )
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def estado_badge(self, obj):
        """Mostrar estado con badge de color"""
        colores = {
            'exitosa': '#28a745',
            'error': '#dc3545',
            'pendiente': '#ffc107',
            'ejecutando': '#17a2b8',
            'parcial': '#fd7e14'
        }
        
        color = colores.get(obj.estado, '#6c757d')
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; text-transform: uppercase;">{}</span>',
            color, obj.estado
        )
    estado_badge.short_description = 'Estado'
