from rest_framework import serializers
from .models import Alerta
from polizas.models import Poliza
from clientes.models import Cliente


class AlertaSerializer(serializers.ModelSerializer):
    """Serializer completo para lecturas de alertas"""
    poliza_numero = serializers.CharField(source='poliza.numero', read_only=True)
    cliente_rut = serializers.CharField(source='cliente.rut', read_only=True)
    cliente_nombre = serializers.CharField(source='cliente.nombre', read_only=True)
    creada_por_username = serializers.CharField(source='creada_por.username', read_only=True)
    asignada_a_username = serializers.CharField(source='asignada_a.username', read_only=True)
    
    # Propiedades calculadas
    esta_vencida = serializers.ReadOnlyField()
    dias_pendiente = serializers.ReadOnlyField()
    activa = serializers.ReadOnlyField()
    
    tipo_display = serializers.SerializerMethodField()
    severidad_display = serializers.SerializerMethodField()
    estado_display = serializers.SerializerMethodField()
    
    class Meta:
        model = Alerta
        fields = [
            'id', 'tipo', 'tipo_display', 'severidad', 'severidad_display',
            'titulo', 'mensaje', 'estado', 'estado_display',
            'poliza', 'poliza_numero', 'cliente', 'cliente_rut', 'cliente_nombre',
            'creada_por', 'creada_por_username', 'asignada_a', 'asignada_a_username',
            'fecha_creacion', 'fecha_lectura', 'fecha_resolucion', 'fecha_limite',
            'esta_vencida', 'dias_pendiente', 'activa', 'metadata'
        ]
        read_only_fields = [
            'id', 'fecha_creacion', 'fecha_lectura', 'fecha_resolucion',
            'esta_vencida', 'dias_pendiente', 'activa'
        ]
    
    def get_tipo_display(self, obj):
        return obj.get_tipo_display()
    
    def get_severidad_display(self, obj):
        return obj.get_severidad_display()
    
    def get_estado_display(self, obj):
        return obj.get_estado_display()


class AlertaListSerializer(serializers.ModelSerializer):
    """Serializer simplificado para listados"""
    tipo_display = serializers.SerializerMethodField()
    severidad_display = serializers.SerializerMethodField()
    estado_display = serializers.SerializerMethodField()
    creada_por_username = serializers.CharField(source='creada_por.username', read_only=True)
    
    class Meta:
        model = Alerta
        fields = [
            'id', 'tipo', 'tipo_display', 'severidad', 'severidad_display',
            'titulo', 'estado', 'estado_display', 'creada_por_username',
            'fecha_creacion', 'dias_pendiente'
        ]
    
    def get_tipo_display(self, obj):
        return obj.get_tipo_display()
    
    def get_severidad_display(self, obj):
        return obj.get_severidad_display()
    
    def get_estado_display(self, obj):
        return obj.get_estado_display()


class AlertaCreateSerializer(serializers.ModelSerializer):
    """Serializer para crear alertas manuales"""
    poliza_numero = serializers.CharField(write_only=True, required=False)
    cliente_rut = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = Alerta
        fields = [
            'tipo', 'severidad', 'titulo', 'mensaje',
            'poliza', 'poliza_numero', 'cliente', 'cliente_rut',
            'asignada_a', 'fecha_limite', 'metadata'
        ]
    
    def validate(self, data):
        # Si se proporciona poliza_numero en lugar de poliza ID
        if 'poliza_numero' in data and data.get('poliza_numero'):
            try:
                poliza = Poliza.objects.get(numero=data['poliza_numero'])
                data['poliza'] = poliza
            except Poliza.DoesNotExist:
                raise serializers.ValidationError({
                    'poliza_numero': f"No existe póliza con número {data['poliza_numero']}"
                })
        
        # Si se proporciona cliente_rut en lugar de cliente ID
        if 'cliente_rut' in data and data.get('cliente_rut'):
            try:
                cliente = Cliente.objects.get(rut=data['cliente_rut'])
                data['cliente'] = cliente
            except Cliente.DoesNotExist:
                raise serializers.ValidationError({
                    'cliente_rut': f"No existe cliente con RUT {data['cliente_rut']}"
                })
        
        return data


class AlertaUpdateSerializer(serializers.ModelSerializer):
    """Serializer para actualizar estado de alertas"""
    class Meta:
        model = Alerta
        fields = ['estado', 'asignada_a', 'fecha_limite']
    
    def create(self, validated_data):
        # Limpiar campos temporales
        validated_data.pop('poliza_numero', None)
        validated_data.pop('cliente_rut', None)
        
        return Alerta.objects.create(**validated_data)


class AlertaUpdateSerializer(serializers.ModelSerializer):
    """Serializer para actualizar estado y asignación"""
    
    class Meta:
        model = Alerta
        fields = ['estado', 'asignada_a', 'mensaje']


class AlertaHistorialSerializer(serializers.ModelSerializer):
    """
    PASO 11: Serializer para historial de alertas
    Incluye información relacionada para auditoría y trazabilidad
    """
    cliente_nombre = serializers.CharField(source='cliente.nombre', read_only=True)
    cliente_rut = serializers.CharField(source='cliente.rut', read_only=True)
    poliza_numero = serializers.CharField(source='poliza.numero', read_only=True)
    resuelta_por_username = serializers.CharField(source='resuelta_por.username', read_only=True)
    
    class Meta:
        from .models import AlertaHistorial
        model = AlertaHistorial
        fields = [
            'id', 'alerta', 'tipo', 'severidad', 'titulo', 'mensaje',
            'cliente', 'cliente_nombre', 'cliente_rut',
            'poliza', 'poliza_numero',
            'creada_en', 'resuelta_en', 'resuelta_por', 'resuelta_por_username',
            'estado_final', 'notas', 'metadata'
        ]
        read_only_fields = ['id', 'creada_en']

