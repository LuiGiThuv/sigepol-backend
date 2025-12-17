from django.contrib import admin
from .models import DataUpload, HistorialImportacion, ImportErrorRow
from django.utils.html import format_html
import json


@admin.register(ImportErrorRow)
class ImportErrorRowAdmin(admin.ModelAdmin):
    list_display = ['id', 'upload_id', 'row_number', 'error_short', 'created_at']
    list_filter = ['upload', 'created_at']
    search_fields = ['upload__id', 'error', 'raw_data']
    readonly_fields = ['upload', 'row_number', 'raw_data', 'error', 'created_at', 'raw_data_display']

    fieldsets = (
        ('Información del Error', {
            'fields': ('upload', 'row_number', 'error', 'created_at')
        }),
        ('Datos Raw', {
            'fields': ('raw_data_display',),
            'classes': ('collapse',)
        }),
    )

    def error_short(self, obj):
        return obj.error[:100] + '...' if len(obj.error) > 100 else obj.error
    error_short.short_description = 'Error'

    def raw_data_display(self, obj):
        if obj.raw_data:
            return format_html('<pre>{}</pre>', json.dumps(obj.raw_data, indent=2, ensure_ascii=False))
        return '-'
    raw_data_display.short_description = 'Datos Raw (JSON)'

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(DataUpload)
class DataUploadAdmin(admin.ModelAdmin):
    list_display = ['id', 'archivo_name', 'cargado_por', 'estado_badge', 'fecha_carga', 'processed_rows', 'inserted_rows', 'updated_rows']
    list_filter = ['estado', 'fecha_carga']
    search_fields = ['archivo', 'cargado_por__username']
    readonly_fields = ['archivo', 'cargado_por', 'fecha_carga', 'detalles_json', 'processed_rows', 'inserted_rows', 'updated_rows', 'error_file']
    
    fieldsets = (
        ('Información de Carga', {
            'fields': ('archivo', 'cargado_por', 'fecha_carga', 'estado')
        }),
        ('Estadísticas de Procesamiento', {
            'fields': ('processed_rows', 'inserted_rows', 'updated_rows'),
        }),
        ('Error', {
            'fields': ('mensaje_error', 'error_file'),
            'classes': ('collapse',)
        }),
        ('Detalles de Procesamiento', {
            'fields': ('detalles_json',),
            'classes': ('collapse',)
        }),
    )

    def archivo_name(self, obj):
        return obj.archivo.name.split('/')[-1]
    archivo_name.short_description = 'Archivo'

    def estado_badge(self, obj):
        color_map = {
            'pendiente': '#95a5a6',
            'validando': '#f39c12',
            'limpiando': '#3498db',
            'procesando': '#1abc9c',
            'ml': '#9b59b6',
            'completado': '#2ecc71',
            'error': '#e74c3c',
        }
        color = color_map.get(obj.estado, '#95a5a6')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            color, obj.get_estado_display()
        )
    estado_badge.short_description = 'Estado'

    def detalles_json(self, obj):
        if obj.detalles_procesamiento:
            return format_html('<pre>{}</pre>', json.dumps(obj.detalles_procesamiento, indent=2, ensure_ascii=False))
        return '-'
    detalles_json.short_description = 'Detalles'

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(HistorialImportacion)
class HistorialImportacionAdmin(admin.ModelAdmin):
    list_display = ['id', 'usuario', 'archivo_name', 'fecha_carga', 'clientes_ingresados', 'filas_insertadas', 'filas_actualizadas', 'filas_erroneas']
    list_filter = ['fecha_carga']
    search_fields = ['archivo', 'usuario__username']
    readonly_fields = ['usuario', 'archivo', 'fecha_carga', 'clientes_ingresados', 'filas_insertadas', 'filas_actualizadas', 'filas_erroneas', 'mensaje']

    def archivo_name(self, obj):
        return obj.archivo.name.split('/')[-1]
    archivo_name.short_description = 'Archivo'

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False
