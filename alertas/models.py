from django.db import models
from django.contrib.auth import get_user_model
from polizas.models import Poliza
from clientes.models import Cliente

User = get_user_model()


class Alerta(models.Model):
    # Tipos de alertas (automáticas, manuales y ML)
    TIPO_CHOICES = [
        # Alertas ML (PASO 14)
        ('ML_RIESGO_PRODUCCION', 'ML: Riesgo de Producción Baja'),
        ('ML_VARIACION_NEGATIVA', 'ML: Variación Negativa Detectada'),
        ('ML_ANOMALIA', 'ML: Anomalía en Datos'),
        
        # Alertas basadas en reglas
        ('produccion_baja', 'Producción Baja'),
        ('crecimiento_negativo', 'Crecimiento Negativo'),
        ('cliente_riesgo', 'Cliente en Cluster de Bajo Rendimiento'),
        ('error_carga', 'Error en Carga de Datos'),
        ('manual', 'Alerta Manual'),
        
        # Categorías adicionales existentes
        ('vencimientos', 'Vencimientos'),
        ('cobranzas', 'Cobranzas'),
        ('importaciones', 'Importaciones'),
        ('sistema', 'Sistema'),
    ]

    # Severidad de alertas
    SEVERIDAD_CHOICES = [
        ('info', 'Informativa'),
        ('warning', 'Advertencia'),
        ('critical', 'Crítica'),
    ]

    # Estados (retrocompatibilidad)
    ESTADO_CHOICES = [
        ('PENDIENTE', 'Pendiente'),
        ('LEIDA', 'Leída'),
        ('RESUELTA', 'Resuelta'),
        ('DESCARTADA', 'Descartada'),
    ]

    # Campos nuevos (PASO 7)
    tipo = models.CharField(max_length=50, choices=TIPO_CHOICES, default='manual')
    severidad = models.CharField(max_length=20, choices=SEVERIDAD_CHOICES, default='info')
    
    # Campos existentes renombrados para consistencia
    titulo = models.CharField(max_length=200)
    mensaje = models.TextField()
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='PENDIENTE')
    
    # PASO 15: Confiabilidad basada en frescura de datos
    confiable = models.BooleanField(
        default=True,
        help_text="False si la alerta se generó con datos desactualizados (>30 días)"
    )
    razon_no_confiable = models.CharField(
        max_length=255,
        blank=True,
        help_text="Razón por la cual la alerta no es confiable"
    )
    
    # Referencias opcionales
    poliza = models.ForeignKey(Poliza, on_delete=models.CASCADE, null=True, blank=True, related_name='alertas')
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, null=True, blank=True, related_name='alertas')
    
    # Auditoría
    creada_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='alertas_creadas')
    asignada_a = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='alertas_asignadas')
    
    # Fechas
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_lectura = models.DateTimeField(null=True, blank=True)
    fecha_resolucion = models.DateTimeField(null=True, blank=True)
    fecha_limite = models.DateTimeField(null=True, blank=True, help_text="Fecha límite para resolver la alerta")
    
    # Metadatos
    metadata = models.JSONField(null=True, blank=True, help_text="Datos adicionales en formato JSON")
    
    class Meta:
        verbose_name = "Alerta"
        verbose_name_plural = "Alertas"
        ordering = ['-fecha_creacion', '-severidad']
        indexes = [
            models.Index(fields=['tipo', 'estado']),
            models.Index(fields=['estado', 'severidad']),
            models.Index(fields=['-fecha_creacion']),
        ]

    def __str__(self):
        return f"[{self.get_tipo_display()}] {self.titulo} - {self.estado}"

    @property
    def esta_vencida(self):
        """Verifica si la alerta ha superado su fecha límite"""
        from django.utils import timezone
        if self.fecha_limite:
            return timezone.now() > self.fecha_limite and self.estado == 'PENDIENTE'
        return False

    @property
    def dias_pendiente(self):
        """Calcula cuántos días lleva pendiente la alerta"""
        from django.utils import timezone
        if self.estado == 'PENDIENTE':
            delta = timezone.now() - self.fecha_creacion
            return delta.days
        return 0

    @property
    def activa(self):
        """Propiedad calculada: alerta está activa si es PENDIENTE o LEIDA"""
        return self.estado in ['PENDIENTE', 'LEIDA']

    def marcar_como_leida(self, usuario=None):
        """Marca la alerta como leída"""
        from django.utils import timezone
        if self.estado == 'PENDIENTE':
            self.estado = 'LEIDA'
            self.fecha_lectura = timezone.now()
            if usuario:
                self.asignada_a = usuario
            self.save()
            return True
        return False

    def marcar_como_resuelta(self, usuario=None):
        """Marca la alerta como resuelta"""
        from django.utils import timezone
        if self.estado in ['PENDIENTE', 'LEIDA']:
            self.estado = 'RESUELTA'
            self.fecha_resolucion = timezone.now()
            if usuario:
                self.asignada_a = usuario
            self.save()
            return True
        return False

    def descartar(self):
        """Descarta la alerta"""
        if self.estado in ['PENDIENTE', 'LEIDA']:
            self.estado = 'DESCARTADA'
            self.save()
            return True
        return False


class AlertaHistorial(models.Model):
    """
    PASO 11: Historial completo de alertas con trazabilidad
    
    Registra:
    - Cuando se creó la alerta
    - Cliente y póliza involucrados
    - Tipo y severidad
    - Quién la resolvió
    - Cuándo se resolvió
    - Estado final
    
    Usado para auditoría, trazabilidad y control interno
    """
    
    ESTADO_FINAL_CHOICES = [
        ('nueva', 'Nueva'),
        ('resuelta', 'Resuelta'),
        ('descartada', 'Descartada'),
        ('expirada', 'Expirada'),
    ]
    
    # Referencia a alerta (opcional, para compatibilidad)
    alerta = models.ForeignKey(
        Alerta,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='historial_registros'
    )
    
    # Información de la alerta
    tipo = models.CharField(max_length=100)
    severidad = models.CharField(max_length=20)
    titulo = models.CharField(max_length=200)
    mensaje = models.TextField()
    
    # Referencias a entidades
    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='historial_alertas'
    )
    poliza = models.ForeignKey(
        Poliza,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='historial_alertas'
    )
    
    # Timestamps
    creada_en = models.DateTimeField(auto_now_add=True, db_index=True)
    resuelta_en = models.DateTimeField(null=True, blank=True)
    
    # Usuario que resolvió
    resuelta_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='alertas_resueltas'
    )
    
    # Estado final
    estado_final = models.CharField(
        max_length=20,
        choices=ESTADO_FINAL_CHOICES,
        default='nueva',
        db_index=True
    )
    
    # Metadatos adicionales
    notas = models.TextField(blank=True, null=True)
    metadata = models.JSONField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Historial de Alerta"
        verbose_name_plural = "Historiales de Alertas"
        ordering = ['-creada_en']
        indexes = [
            models.Index(fields=['estado_final', 'severidad']),
            models.Index(fields=['cliente', 'creada_en']),
            models.Index(fields=['-creada_en']),
            models.Index(fields=['tipo', 'estado_final']),
        ]
    
    def __str__(self):
        return f"{self.tipo} - {self.cliente.nombre if self.cliente else 'N/A'} ({self.estado_final})"
    
    @property
    def tiempo_resolucion(self):
        """Calcula el tiempo entre creación y resolución"""
        if self.resuelta_en:
            return (self.resuelta_en - self.creada_en).total_seconds() / 3600  # en horas
        return None
    
    @property
    def dias_pendiente(self):
        """Calcula cuántos días lleva sin resolver"""
        from django.utils import timezone
        if self.estado_final == 'nueva':
            delta = timezone.now() - self.creada_en
            return delta.days
        return 0

class PreferenciaNotificacionAlerta(models.Model):
    """
    Preferencias de notificación por correo para cada usuario
    PASO 16: Sistema de notificaciones por email
    """
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='pref_notificacion_alerta')
    
    # Habilitación general
    recibir_emails = models.BooleanField(default=True, help_text="¿Recibir notificaciones por email?")
    
    # Por severidad
    notificar_criticas = models.BooleanField(default=True, help_text="Notificar alertas críticas")
    notificar_advertencias = models.BooleanField(default=True, help_text="Notificar alertas de advertencia")
    notificar_info = models.BooleanField(default=False, help_text="Notificar alertas informativas")
    
    # Por tipo
    tipos_interes = models.JSONField(
        default=list,
        blank=True,
        help_text="Tipos de alerta para notificar (vacío = todos)"
    )
    
    # Frecuencia
    FRECUENCIA_CHOICES = [
        ('inmediata', 'Inmediata'),
        ('diaria', 'Resumen Diario'),
        ('semanal', 'Resumen Semanal'),
    ]
    frecuencia = models.CharField(
        max_length=20,
        choices=FRECUENCIA_CHOICES,
        default='inmediata',
        help_text="Frecuencia de notificaciones"
    )
    
    # Horario
    hora_notificacion = models.TimeField(
        null=True,
        blank=True,
        help_text="Hora para enviar resumen (si usa resumen)"
    )
    
    # Auditoría
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Preferencia de Notificación de Alerta"
        verbose_name_plural = "Preferencias de Notificación de Alertas"
    
    def __str__(self):
        return f"Preferencias de {self.usuario.username}"
    
    def debe_notificar(self, severidad, tipo):
        """Verifica si debe notificar basada en preferencias"""
        if not self.recibir_emails:
            return False
        
        # Verificar severidad
        if severidad == 'critical' and not self.notificar_criticas:
            return False
        if severidad == 'warning' and not self.notificar_advertencias:
            return False
        if severidad == 'info' and not self.notificar_info:
            return False
        
        # Verificar tipo si hay filtro
        if self.tipos_interes and tipo not in self.tipos_interes:
            return False
        
        return True