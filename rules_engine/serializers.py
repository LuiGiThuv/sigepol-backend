from rest_framework import serializers
from .models import Rule, RuleExecution


class RuleExecutionSerializer(serializers.ModelSerializer):
    """Serializer para las ejecuciones de reglas"""
    
    tiempo_ejecucion = serializers.CharField(read_only=True)
    exitosa = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = RuleExecution
        fields = (
            'id',
            'regla',
            'inicio',
            'fin',
            'duracion_segundos',
            'tiempo_ejecucion',
            'estado',
            'resultado',
            'error_mensaje',
            'exitosa',
            'parametros_utilizados'
        )
        read_only_fields = (
            'id',
            'inicio',
            'fin',
            'duracion_segundos',
            'estado',
            'resultado',
            'error_mensaje'
        )


class RuleDetailSerializer(serializers.ModelSerializer):
    """Serializer detallado para una regla con su historial"""
    
    tasa_exito = serializers.FloatField(read_only=True)
    habilitada = serializers.BooleanField(read_only=True)
    ejecuciones = RuleExecutionSerializer(
        source='ruleexecution_set',
        many=True,
        read_only=True
    )
    
    class Meta:
        model = Rule
        fields = (
            'id',
            'nombre',
            'descripcion',
            'codigo',
            'tipo',
            'activa',
            'habilitada',
            'orden_ejecucion',
            'parametros',
            'creada_en',
            'modificada_en',
            'ultima_ejecucion',
            'proxima_ejecucion',
            'ultimo_resultado',
            'ultimo_error',
            'total_ejecuciones',
            'ejecuciones_exitosas',
            'ejecuciones_fallidas',
            'tasa_exito',
            'ejecuciones'
        )
        read_only_fields = (
            'id',
            'creada_en',
            'modificada_en',
            'ultima_ejecucion',
            'ultimo_resultado',
            'ultimo_error',
            'total_ejecuciones',
            'ejecuciones_exitosas',
            'ejecuciones_fallidas',
            'ejecuciones'
        )


class RuleListSerializer(serializers.ModelSerializer):
    """Serializer simplificado para listado de reglas"""
    
    tasa_exito = serializers.FloatField(read_only=True)
    
    class Meta:
        model = Rule
        fields = (
            'id',
            'nombre',
            'codigo',
            'tipo',
            'activa',
            'ultima_ejecucion',
            'total_ejecuciones',
            'ejecuciones_exitosas',
            'ejecuciones_fallidas',
            'tasa_exito'
        )
        read_only_fields = (
            'id',
            'ultima_ejecucion',
            'total_ejecuciones',
            'ejecuciones_exitosas',
            'ejecuciones_fallidas'
        )


class RuleCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer para crear/editar reglas"""
    
    class Meta:
        model = Rule
        fields = (
            'nombre',
            'descripcion',
            'codigo',
            'tipo',
            'activa',
            'orden_ejecucion',
            'parametros'
        )
    
    def validate_codigo(self, value):
        """Validar que el código sea único"""
        if self.instance is None:
            if Rule.objects.filter(codigo=value).exists():
                raise serializers.ValidationError("El código de la regla ya existe")
        return value
    
    def validate_parametros(self, value):
        """Validar que parametros sea un dict válido"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Los parámetros deben ser un objeto JSON válido")
        return value
