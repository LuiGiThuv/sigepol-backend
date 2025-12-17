from django.contrib import admin
from .models import Cobranza


@admin.register(Cobranza)
class CobranzaAdmin(admin.ModelAdmin):
    list_display = ['id', 'poliza', 'monto_uf', 'fecha_emision', 'fecha_vencimiento', 'estado', 'dias_vencimiento']
    list_filter = ['estado', 'metodo_pago', 'fecha_emision', 'fecha_vencimiento']
    search_fields = ['poliza__numero', 'poliza__cliente__nombre', 'poliza__cliente__rut', 'numero_documento']
    readonly_fields = ['created_at', 'updated_at', 'usuario_registro', 'dias_vencimiento', 'esta_vencida']
    date_hierarchy = 'fecha_emision'
    
    fieldsets = (
        ('Información Principal', {
            'fields': ('poliza', 'monto_uf', 'monto_pesos', 'valor_uf')
        }),
        ('Fechas', {
            'fields': ('fecha_emision', 'fecha_vencimiento', 'fecha_pago')
        }),
        ('Estado y Pago', {
            'fields': ('estado', 'metodo_pago', 'numero_documento')
        }),
        ('Información Adicional', {
            'fields': ('observaciones', 'usuario_registro', 'dias_vencimiento', 'esta_vencida')
        }),
        ('Auditoría', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
