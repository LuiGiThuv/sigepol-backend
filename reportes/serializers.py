"""
Serializers para reportes automáticos inteligentes
PASO 9: Módulo de Reportes Automáticos Inteligentes
"""

from rest_framework import serializers


class ReportePolizaSerializer(serializers.Serializer):
    """Serializer para pólizas en reportes"""
    id = serializers.IntegerField()
    cliente = serializers.CharField()
    rut = serializers.CharField()
    poliza = serializers.CharField()
    vencimiento = serializers.CharField()
    dias_atraso = serializers.IntegerField(required=False)
    dias_restantes = serializers.IntegerField(required=False)
    prima_uf = serializers.FloatField()
    estado = serializers.CharField()


class ReporteClienteSerializer(serializers.Serializer):
    """Serializer para clientes en ranking"""
    posicion = serializers.IntegerField()
    cliente_id = serializers.IntegerField()
    cliente = serializers.CharField()
    rut = serializers.CharField()
    total_uf = serializers.FloatField()
    cantidad_polizas = serializers.IntegerField()
    participacion_porcentaje = serializers.FloatField()
    prima_promedio = serializers.FloatField()


class ReporteProduccionSerializer(serializers.Serializer):
    """Serializer para reporte de producción"""
    mes = serializers.CharField()
    mes_anterior = serializers.CharField()
    produccion_actual = serializers.DictField()
    produccion_anterior = serializers.DictField()
    variacion = serializers.DictField()
    cartera = serializers.DictField()
    generado = serializers.CharField()
