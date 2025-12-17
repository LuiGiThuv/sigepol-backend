from rest_framework import serializers
from .models import Cobranza
from polizas.models import Poliza


class CobranzaSerializer(serializers.ModelSerializer):
    poliza_numero = serializers.CharField(source='poliza.numero', read_only=True)
    cliente_rut = serializers.CharField(source='poliza.cliente.rut', read_only=True)
    cliente_nombre = serializers.CharField(source='poliza.cliente.nombre', read_only=True)
    dias_vencimiento = serializers.ReadOnlyField()
    esta_vencida = serializers.ReadOnlyField()
    es_de_riesgo = serializers.ReadOnlyField()
    
    class Meta:
        model = Cobranza
        fields = [
            'id', 'poliza', 'poliza_numero', 'cliente_rut', 'cliente_nombre',
            'monto_uf', 'monto_pesos', 'valor_uf',
            'fecha_emision', 'fecha_vencimiento', 'fecha_pago', 'dias_atraso',
            'estado', 'tipo_cobranza', 'metodo_pago', 'numero_documento',
            'fuente_etl', 'campo_pago_pendiente',
            'tiene_alerta_financiera', 'razon_alerta',
            'observaciones', 'usuario_registro',
            'dias_vencimiento', 'esta_vencida', 'es_de_riesgo',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'created_at', 'updated_at', 'usuario_registro', 
            'dias_vencimiento', 'esta_vencida', 'es_de_riesgo',
            'fuente_etl', 'campo_pago_pendiente'
        ]


class CobranzaCreateSerializer(serializers.ModelSerializer):
    poliza_numero = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = Cobranza
        fields = [
            'poliza', 'poliza_numero', 'monto_uf', 'valor_uf',
            'fecha_emision', 'fecha_vencimiento', 'observaciones'
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
        
        # Validar que la fecha de vencimiento sea posterior a la emisión
        if data.get('fecha_vencimiento') and data.get('fecha_emision'):
            if data['fecha_vencimiento'] < data['fecha_emision']:
                raise serializers.ValidationError({
                    'fecha_vencimiento': 'La fecha de vencimiento debe ser posterior a la fecha de emisión'
                })
        
        return data
    
    def create(self, validated_data):
        validated_data.pop('poliza_numero', None)
        cobranza = Cobranza.objects.create(**validated_data)
        
        # Calcular monto en pesos si se proporcionó valor_uf
        if cobranza.valor_uf:
            cobranza.calcular_monto_pesos(cobranza.valor_uf)
            cobranza.save()
        
        return cobranza


class CobranzaPagoSerializer(serializers.ModelSerializer):
    """Serializer para registrar el pago de una cobranza"""
    
    class Meta:
        model = Cobranza
        fields = ['fecha_pago', 'metodo_pago', 'numero_documento', 'observaciones', 'valor_uf']
    
    def update(self, instance, validated_data):
        # Actualizar campos
        instance.fecha_pago = validated_data.get('fecha_pago', instance.fecha_pago)
        instance.metodo_pago = validated_data.get('metodo_pago', instance.metodo_pago)
        instance.numero_documento = validated_data.get('numero_documento', instance.numero_documento)
        instance.observaciones = validated_data.get('observaciones', instance.observaciones)
        
        # Si se proporciona valor_uf, recalcular monto en pesos
        if 'valor_uf' in validated_data:
            instance.calcular_monto_pesos(validated_data['valor_uf'])
        
        # Cambiar estado a PAGADA
        instance.estado = 'PAGADA'
        instance.save()
        
        return instance
