from rest_framework import serializers
from .models import AuditoriaAccion, LogAcceso, AuditLog


class AuditoriaAccionSerializer(serializers.ModelSerializer):
    usuario_username = serializers.CharField(source='usuario.username', read_only=True)
    usuario_email = serializers.CharField(source='usuario.email', read_only=True)
    rol_display = serializers.CharField(source='get_accion_display', read_only=True)

    class Meta:
        model = AuditoriaAccion
        fields = [
            'id', 'usuario', 'usuario_username', 'usuario_email', 'accion', 'rol_display',
            'modulo', 'modelo', 'objeto_id', 'descripcion',
            'datos_anteriores', 'datos_nuevos',
            'ip_address', 'metodo_http', 'url',
            'fecha_hora', 'exitoso', 'mensaje_error', 'rol_usuario'
        ]
        read_only_fields = [
            'id', 'fecha_hora', 'usuario', 'rol_usuario'
        ]


class LogAccesoSerializer(serializers.ModelSerializer):
    usuario_username = serializers.CharField(source='usuario.username', read_only=True)

    class Meta:
        model = LogAcceso
        fields = [
            'id', 'usuario', 'usuario_username', 'ip_address', 'endpoint',
            'metodo', 'resultado', 'codigo_estado', 'mensaje',
            'user_agent', 'timestamp'
        ]
        read_only_fields = [
            'id', 'timestamp', 'usuario', 'ip_address', 'endpoint',
            'metodo', 'resultado', 'codigo_estado'
        ]


class AuditLogSerializer(serializers.ModelSerializer):
    usuario_username = serializers.CharField(source='usuario.username', read_only=True)
    accion_display = serializers.CharField(source='get_accion_display', read_only=True)

    class Meta:
        model = AuditLog
        fields = [
            'id', 'usuario', 'usuario_username', 'accion', 'accion_display',
            'descripcion', 'fecha_creacion', 'detalles'
        ]
        read_only_fields = ['id', 'fecha_creacion']

