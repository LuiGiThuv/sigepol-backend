from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count, Q
from .models import Alerta


@admin.register(Alerta)
class AlertaAdmin(admin.ModelAdmin):
    list_display = ['id', 'tipo_badge', 'severidad_badge', 'titulo', 'estado_badge', 'confiable_badge', 'fecha_creacion', 'asignada_a']
    list_filter = ['tipo', 'severidad', 'estado', 'confiable', 'fecha_creacion']
    search_fields = ['titulo', 'mensaje', 'poliza__numero', 'cliente__nombre', 'cliente__rut', 'razon_no_confiable']
    readonly_fields = ['fecha_creacion', 'fecha_lectura', 'fecha_resolucion', 'esta_vencida', 'dias_pendiente', 'activa', 'estadisticas_panel']
    date_hierarchy = 'fecha_creacion'
    
    fieldsets = (
        ('Estadísticas Rápidas', {
            'fields': ('estadisticas_panel',),
            'classes': ('wide',)
        }),
        ('Información Principal', {
            'fields': ('tipo', 'severidad', 'titulo', 'mensaje', 'estado')
        }),
        ('Referencias', {
            'fields': ('poliza', 'cliente')
        }),
        ('Asignación', {
            'fields': ('creada_por', 'asignada_a')
        }),
        ('Fechas', {
            'fields': ('fecha_creacion', 'fecha_lectura', 'fecha_resolucion', 'fecha_limite')
        }),
        ('Confiabilidad (PASO 15)', {
            'fields': ('confiable', 'razon_no_confiable'),
            'classes': ('wide',)
        }),
        ('Estado Computed', {
            'fields': ('esta_vencida', 'dias_pendiente', 'activa')
        }),
        ('Metadatos', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['marcar_como_leidas', 'marcar_como_resueltas', 'marcar_como_no_confiables']
    
    def estadisticas_panel(self, obj):
        """Panel con estadísticas rápidas del sistema"""
        total = Alerta.objects.count()
        pendientes = Alerta.objects.filter(estado='PENDIENTE').count()
        criticas = Alerta.objects.filter(severidad='critical', estado__in=['PENDIENTE', 'LEIDA']).count()
        no_confiables = Alerta.objects.filter(confiable=False).count()
        vencimientos = Alerta.objects.filter(tipo='vencimientos').count()
        
        html = f"""
        <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; border-left: 4px solid #007bff;">
            <h3 style="margin-top: 0;">Resumen del Sistema</h3>
            <table style="width: 100%; font-size: 14px;">
                <tr>
                    <td style="padding: 5px;"><strong>Total Alertas:</strong></td>
                    <td style="padding: 5px; text-align: right; color: #007bff;"><strong>{total:,}</strong></td>
                    <td style="padding: 5px 15px;"><strong>Pendientes:</strong></td>
                    <td style="padding: 5px; text-align: right; color: #f39c12;"><strong>{pendientes:,}</strong></td>
                </tr>
                <tr>
                    <td style="padding: 5px;"><strong>Críticas Activas:</strong></td>
                    <td style="padding: 5px; text-align: right; color: #e74c3c;"><strong>{criticas:,}</strong></td>
                    <td style="padding: 5px 15px;"><strong>No Confiables:</strong></td>
                    <td style="padding: 5px; text-align: right; color: #c0392b;"><strong>{no_confiables:,}</strong></td>
                </tr>
                <tr>
                    <td style="padding: 5px;"><strong>Vencimientos:</strong></td>
                    <td style="padding: 5px; text-align: right; color: #9b59b6;"><strong>{vencimientos:,}</strong></td>
                    <td colspan="2" style="padding: 5px;"></td>
                </tr>
            </table>
        </div>
        """
        return format_html(html)
    estadisticas_panel.short_description = 'Estadísticas del Sistema'
    
    def tipo_badge(self, obj):
        """Muestra el tipo con color"""
        colores = {
            'produccion_baja': '#f39c12',
            'crecimiento_negativo': '#e74c3c',
            'cliente_riesgo': '#e67e22',
            'error_carga': '#c0392b',
            'manual': '#3498db',
            'vencimientos': '#9b59b6',
            'cobranzas': '#1abc9c',
            'importaciones': '#16a085',
            'sistema': '#34495e',
            'data_freshness_warning': '#e67e22',
            'ML_RIESGO_PRODUCCION': '#f39c12',
            'ML_VARIACION_NEGATIVA': '#e74c3c',
            'ML_ANOMALIA': '#c0392b',
        }
        color = colores.get(obj.tipo, '#95a5a6')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
            color, obj.get_tipo_display()
        )
    tipo_badge.short_description = 'Tipo'
    
    def severidad_badge(self, obj):
        """Muestra severidad con color"""
        colores = {
            'info': '#3498db',
            'warning': '#f39c12',
            'critical': '#e74c3c',
        }
        color = colores.get(obj.severidad, '#95a5a6')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
            color, obj.get_severidad_display()
        )
    severidad_badge.short_description = 'Severidad'
    
    def estado_badge(self, obj):
        """Muestra estado con color"""
        colores = {
            'PENDIENTE': '#f39c12',
            'LEIDA': '#3498db',
            'RESUELTA': '#2ecc71',
            'DESCARTADA': '#95a5a6',
        }
        color = colores.get(obj.estado, '#95a5a6')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
            color, obj.get_estado_display()
        )
    estado_badge.short_description = 'Estado'
    
    def confiable_badge(self, obj):
        """Muestra si la alerta es confiable (PASO 15)"""
        if obj.confiable:
            return format_html(
                '<span style="background-color: #2ecc71; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">OK</span>'
            )
        else:
            return format_html(
                '<span style="background-color: #e74c3c; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;" title="{}">NO CONF.</span>',
                obj.razon_no_confiable
            )
    confiable_badge.short_description = 'Confiable'
    
    def marcar_como_leidas(self, request, queryset):
        for alerta in queryset:
            alerta.marcar_como_leida(request.user)
        self.message_user(request, f'{queryset.count()} alertas marcadas como leídas')
    marcar_como_leidas.short_description = "Marcar como leídas"
    
    def marcar_como_resueltas(self, request, queryset):
        for alerta in queryset:
            alerta.marcar_como_resuelta(request.user)
        self.message_user(request, f'{queryset.count()} alertas marcadas como resueltas')
    marcar_como_resueltas.short_description = "Marcar como resueltas"
    
    def marcar_como_no_confiables(self, request, queryset):
        """Marcar alertas como no confiables (PASO 15)"""
        count = 0
        for alerta in queryset:
            if alerta.confiable:
                alerta.confiable = False
                alerta.razon_no_confiable = "Marcada manualmente como no confiable desde admin"
                alerta.save()
                count += 1
        self.message_user(request, f'{count} alertas marcadas como no confiables')
    marcar_como_no_confiables.short_description = "Marcar como NO confiables"

# PASO 16: Admin para Preferencias de Notificación
from .models import AlertaHistorial, PreferenciaNotificacionAlerta


@admin.register(PreferenciaNotificacionAlerta)
class PreferenciaNotificacionAlertaAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'recibir_emails_badge', 'frecuencia_badge', 'fecha_actualizacion']
    list_filter = ['recibir_emails', 'frecuencia', 'notificar_criticas', 'notificar_advertencias']
    search_fields = ['usuario__username', 'usuario__email']
    readonly_fields = ['fecha_creacion', 'fecha_actualizacion']
    
    fieldsets = (
        ('Usuario', {
            'fields': ('usuario',)
        }),
        ('Control General', {
            'fields': ('recibir_emails',)
        }),
        ('Notificaciones por Severidad', {
            'fields': ('notificar_criticas', 'notificar_advertencias', 'notificar_info')
        }),
        ('Filtro de Tipos', {
            'fields': ('tipos_interes',),
            'description': 'Dejar vacío para recibir todos los tipos'
        }),
        ('Frecuencia', {
            'fields': ('frecuencia', 'hora_notificacion')
        }),
        ('Auditoría', {
            'fields': ('fecha_creacion', 'fecha_actualizacion'),
            'classes': ('collapse',)
        }),
    )
    
    def recibir_emails_badge(self, obj):
        """Muestra si recibe emails"""
        color = '#27ae60' if obj.recibir_emails else '#e74c3c'
        emoji = '✅' if obj.recibir_emails else '❌'
        return format_html(
            f'<span style="color: {color}; font-weight: bold;">{emoji} {"Sí" if obj.recibir_emails else "No"}</span>'
        )
    recibir_emails_badge.short_description = 'Recibe Emails'
    
    def frecuencia_badge(self, obj):
        """Muestra la frecuencia con color"""
        colores = {'inmediata': '#e74c3c', 'diaria': '#f39c12', 'semanal': '#27ae60'}
        color = colores.get(obj.frecuencia, '#95a5a6')
        return format_html(
            f'<span style="background: {color}; color: white; padding: 3px 10px; border-radius: 3px;">{obj.get_frecuencia_display()}</span>'
        )
    frecuencia_badge.short_description = 'Frecuencia'


@admin.register(AlertaHistorial)
class AlertaHistorialAdmin(admin.ModelAdmin):
    list_display = ['alerta', 'tipo', 'severidad', 'estado_final', 'creada_en', 'resuelta_en']
    list_filter = ['tipo', 'severidad', 'estado_final', 'creada_en']
    search_fields = ['alerta__titulo', 'cliente__nombre', 'poliza__numero']
    readonly_fields = ['creada_en', 'resuelta_en', 'tiempo_resolucion', 'dias_pendiente']
    date_hierarchy = 'creada_en'
    
    fieldsets = (
        ('Referencia', {
            'fields': ('alerta', 'tipo', 'severidad')
        }),
        ('Contenido', {
            'fields': ('titulo', 'mensaje')
        }),
        ('Referencias', {
            'fields': ('cliente', 'poliza')
        }),
        ('Resolución', {
            'fields': ('estado_final', 'creada_en', 'resuelta_en', 'resuelta_por')
        }),
        ('Análisis', {
            'fields': ('tiempo_resolucion', 'dias_pendiente'),
            'classes': ('collapse',)
        }),
    )