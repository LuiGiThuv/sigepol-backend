from rest_framework import serializers
from .models import HistorialImportacion, DataUpload, ImportErrorRow, DataFreshness


class ImportErrorRowSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImportErrorRow
        fields = ['id', 'row_number', 'error', 'raw_data', 'created_at']
        read_only_fields = fields


class DataUploadSerializer(serializers.ModelSerializer):
    archivo_name = serializers.SerializerMethodField()
    cargado_por_username = serializers.CharField(source='cargado_por.username', read_only=True)
    error_rows = ImportErrorRowSerializer(many=True, read_only=True, source='error_rows.all')
    
    class Meta:
        model = DataUpload
        fields = [
            'id',
            'archivo',
            'archivo_name',
            'cargado_por',
            'cargado_por_username',
            'fecha_carga',
            'estado',
            'mensaje_error',
            'detalles_procesamiento',
            'error_file',
            'processed_rows',
            'inserted_rows',
            'updated_rows',
            'error_rows'
        ]
        read_only_fields = ['id', 'fecha_carga', 'estado', 'mensaje_error', 'error_file', 'processed_rows', 'inserted_rows', 'updated_rows', 'cargado_por']
    
    def get_archivo_name(self, obj):
        return obj.archivo.name.split('/')[-1] if obj.archivo else None


class HistorialImportacionSerializer(serializers.ModelSerializer):
    usuario = serializers.StringRelatedField(read_only=True)
    archivo = serializers.CharField(read_only=True)

    class Meta:
        model = HistorialImportacion
        fields = [
            'id',
            'usuario',
            'archivo',
            'fecha_carga',
            'clientes_ingresados',
            'filas_insertadas',
            'filas_actualizadas',
            'filas_erroneas',
            'mensaje',
        ]
        read_only_fields = fields


class DataFreshnessSerializer(serializers.ModelSerializer):
    """Serializer para el estado de frescura de datos de clientes"""
    
    usuario_ultima_carga_username = serializers.CharField(
        source='usuario_ultima_carga.username',
        read_only=True,
        allow_null=True
    )
    estado_frescura = serializers.SerializerMethodField()
    
    class Meta:
        model = DataFreshness
        fields = [
            'id',
            'cliente',
            'ultima_actualizacion',
            'dias_sin_actualizacion',
            'alerta_frescura',
            'fecha_ultima_carga',
            'usuario_ultima_carga',
            'usuario_ultima_carga_username',
            'registros_actualizados',
            'estado_frescura',
        ]
        read_only_fields = [
            'id',
            'ultima_actualizacion',
            'dias_sin_actualizacion',
            'usuario_ultima_carga',
            'estado_frescura',
        ]
    
    def get_estado_frescura(self, obj):
        """Obtiene el estado de frescura detallado del cliente"""
        return obj.obtener_estado_frescura()


class DataFreshnessEstadisticasSerializer(serializers.Serializer):
    """Serializer para las estadísticas globales de frescura de datos"""
    
    total_clientes = serializers.IntegerField()
    clientes_frescos = serializers.IntegerField()
    clientes_con_advertencia = serializers.IntegerField()
    clientes_criticos = serializers.IntegerField()
    porcentaje_fresco = serializers.FloatField()
    porcentaje_advertencia = serializers.FloatField()
    porcentaje_critico = serializers.FloatField()
    clientes_desactualizados = serializers.ListField(
        child=serializers.CharField(),
        help_text="Lista de clientes con datos desactualizados >30 días"
    )


