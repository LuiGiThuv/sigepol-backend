from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import json

User = get_user_model()


class AuditoriaAccion(models.Model):
    """
    Registro de auditoría para todas las acciones realizadas por usuarios
    """
    TIPO_ACCIONES = [
        ('CREATE', 'Crear'),
        ('UPDATE', 'Actualizar'),
        ('DELETE', 'Eliminar'),
        ('READ', 'Leer'),
        ('LOGIN', 'Iniciar sesión'),
        ('LOGOUT', 'Cerrar sesión'),
        ('PERMISSION_DENIED', 'Acceso denegado'),
        ('ROLE_CHANGE', 'Cambio de rol'),
        ('PASSWORD_CHANGE', 'Cambio de contraseña'),
    ]

    # Identificación
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='auditorias')
    accion = models.CharField(max_length=20, choices=TIPO_ACCIONES)
    
    # Contenido
    modulo = models.CharField(max_length=100, help_text="Ej: cobranzas, alertas, usuarios")
    modelo = models.CharField(max_length=100, help_text="Ej: Cobranza, Alerta, User")
    objeto_id = models.CharField(max_length=100, null=True, blank=True, help_text="ID del objeto modificado")
    descripcion = models.TextField(help_text="Descripción de lo que se hizo")
    
    # Datos
    datos_anteriores = models.JSONField(null=True, blank=True, help_text="Valores antes de la acción")
    datos_nuevos = models.JSONField(null=True, blank=True, help_text="Valores después de la acción")
    
    # Acceso
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    metodo_http = models.CharField(max_length=10, null=True, blank=True, help_text="GET, POST, PUT, DELETE, etc")
    url = models.URLField(null=True, blank=True)
    
    # Timestamps
    fecha_hora = models.DateTimeField(auto_now_add=True, db_index=True)
    
    # Estado
    exitoso = models.BooleanField(default=True)
    mensaje_error = models.TextField(null=True, blank=True)
    
    # Rol del usuario en el momento de la acción
    rol_usuario = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        ordering = ['-fecha_hora']
        indexes = [
            models.Index(fields=['usuario', '-fecha_hora']),
            models.Index(fields=['modulo', '-fecha_hora']),
            models.Index(fields=['accion', '-fecha_hora']),
        ]
        verbose_name = 'Auditoría'
        verbose_name_plural = 'Auditorías'

    def __str__(self):
        return f"{self.usuario} - {self.get_accion_display()} - {self.modelo} ({self.fecha_hora})"

    @classmethod
    def registrar(cls, usuario, accion, modulo, modelo, descripcion,
                  objeto_id=None, datos_anteriores=None, datos_nuevos=None,
                  ip_address=None, user_agent=None, metodo_http=None, url=None,
                  exitoso=True, mensaje_error=None):
        """
        Método helper para registrar acciones
        
        Uso:
        AuditoriaAccion.registrar(
            usuario=request.user,
            accion='UPDATE',
            modulo='cobranzas',
            modelo='Cobranza',
            descripcion='Se actualizó el estado de la cobranza',
            objeto_id=cobranza.id,
            datos_anteriores={'estado': 'PENDIENTE'},
            datos_nuevos={'estado': 'PAGADA'},
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT'),
            metodo_http=request.method,
            url=request.path
        )
        """
        return cls.objects.create(
            usuario=usuario,
            accion=accion,
            modulo=modulo,
            modelo=modelo,
            objeto_id=objeto_id,
            descripcion=descripcion,
            datos_anteriores=datos_anteriores,
            datos_nuevos=datos_nuevos,
            ip_address=ip_address,
            user_agent=user_agent,
            metodo_http=metodo_http,
            url=url,
            exitoso=exitoso,
            mensaje_error=mensaje_error,
            rol_usuario=usuario.role if usuario else None
        )


class LogAcceso(models.Model):
    """
    Log de intentos de acceso a la API
    """
    RESULTADO_CHOICES = [
        ('EXITOSO', 'Exitoso'),
        ('FALLIDO', 'Fallido'),
        ('BLOQUEADO', 'Bloqueado'),
    ]

    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='logs_acceso')
    ip_address = models.GenericIPAddressField()
    endpoint = models.CharField(max_length=255)
    metodo = models.CharField(max_length=10)
    
    resultado = models.CharField(max_length=20, choices=RESULTADO_CHOICES)
    codigo_estado = models.IntegerField(null=True, blank=True)
    
    mensaje = models.TextField(null=True, blank=True)
    
    user_agent = models.TextField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['usuario', '-timestamp']),
            models.Index(fields=['ip_address', '-timestamp']),
        ]
        verbose_name = 'Log de Acceso'
        verbose_name_plural = 'Logs de Acceso'

    def __str__(self):
        return f"{self.usuario or self.ip_address} - {self.resultado} - {self.endpoint} ({self.timestamp})"


class AuditLog(models.Model):
    """
    Modelo simple de auditoría para registro de acciones del sistema
    Complementa AuditoriaAccion con un modelo más básico
    """
    ACTIONS = [
        ('login', 'Inicio de sesión'),
        ('logout', 'Cierre de sesión'),
        ('upload', 'Carga de archivo'),
        ('process', 'Procesamiento de datos'),
        ('view', 'Visualización de datos'),
        ('update', 'Actualización de datos'),
        ('delete', 'Eliminación de datos'),
        ('ml_run', 'Ejecución de modelo ML'),
        ('report_generate', 'Generación de reporte'),
        ('export', 'Exportación de datos'),
    ]

    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='audit_logs')
    accion = models.CharField(max_length=50, choices=ACTIONS)
    descripcion = models.TextField()
    fecha_creacion = models.DateTimeField(auto_now_add=True, db_index=True)
    detalles = models.JSONField(null=True, blank=True, help_text="Detalles adicionales en JSON")

    class Meta:
        ordering = ['-fecha_creacion']
        indexes = [
            models.Index(fields=['usuario', '-fecha_creacion']),
            models.Index(fields=['accion', '-fecha_creacion']),
        ]
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'

    def __str__(self):
        return f"{self.usuario} - {self.get_accion_display()} - {self.fecha_creacion}"
