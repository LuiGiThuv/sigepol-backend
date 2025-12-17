"""
PASO 11: Modelos para el Motor de Reglas

Almacena reglas dinámicas que el sistema ejecuta automáticamente.
"""

from django.db import models
from django.utils import timezone


class Rule(models.Model):
    """
    PASO 11: Regla de negocio ejecutable

    Permite definir lógica inteligente sin modificar código.
    Cada regla tiene:
    - Código único para referencia
    - Parámetros configurables (JSON)
    - Historial de ejecuciones
    """
    
    RULE_TYPES = [
        ('vencimientos', 'Alerta de Vencimientos'),
        ('produccion', 'Análisis de Producción'),
        ('cliente_top', 'Clientes Top'),
        ('anomalia', 'Detección de Anomalías'),
        ('compliance', 'Cumplimiento Normativo'),
    ]
    
    # Identificación
    nombre = models.CharField(max_length=200, unique=True)
    descripcion = models.TextField()
    tipo = models.CharField(max_length=50, choices=RULE_TYPES)
    codigo = models.CharField(max_length=100, unique=True, db_index=True)
    
    # Control
    activa = models.BooleanField(default=True, db_index=True)
    orden_ejecucion = models.IntegerField(default=0, help_text="Orden en el que se ejecuta (0=primero)")
    
    # Configuración dinámica
    parametros = models.JSONField(
        default=dict,
        help_text="Parámetros configurables para la regla (ej: {\"dias\": 30, \"severidad\": \"critical\"})"
    )
    
    # Auditoría de ejecución
    creada_en = models.DateTimeField(auto_now_add=True)
    modificada_en = models.DateTimeField(auto_now=True)
    ultima_ejecucion = models.DateTimeField(null=True, blank=True, db_index=True)
    proxima_ejecucion = models.DateTimeField(null=True, blank=True)
    ultimo_resultado = models.JSONField(null=True, blank=True)
    ultimo_error = models.TextField(blank=True, null=True)
    
    # Estadísticas
    total_ejecuciones = models.IntegerField(default=0)
    ejecuciones_exitosas = models.IntegerField(default=0)
    ejecuciones_fallidas = models.IntegerField(default=0)
    
    class Meta:
        verbose_name = "Regla de Negocio"
        verbose_name_plural = "Reglas de Negocio"
        ordering = ['orden_ejecucion', 'nombre']
        indexes = [
            models.Index(fields=['activa', 'tipo']),
            models.Index(fields=['-ultima_ejecucion']),
            models.Index(fields=['codigo']),
        ]
    
    def __str__(self):
        return f"{self.nombre} ({self.codigo})"
    
    @property
    def tasa_exito(self):
        """Calcula porcentaje de ejecuciones exitosas"""
        if self.total_ejecuciones == 0:
            return 0
        return (self.ejecuciones_exitosas / self.total_ejecuciones) * 100
    
    @property
    def habilitada(self):
        """Alias para compatibilidad"""
        return self.activa


class RuleExecution(models.Model):
    """
    PASO 11: Historial detallado de ejecuciones

    Permite auditoría completa de qué hizo cada regla y cuándo.
    """
    
    STATUS_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('ejecutando', 'Ejecutando'),
        ('exitosa', 'Exitosa'),
        ('error', 'Error'),
        ('parcial', 'Ejecución Parcial'),
    ]
    
    regla = models.ForeignKey(Rule, on_delete=models.CASCADE, related_name='ejecuciones')
    
    # Timeline
    inicio = models.DateTimeField(auto_now_add=True, db_index=True)
    fin = models.DateTimeField(null=True, blank=True)
    duracion_segundos = models.FloatField(null=True, blank=True)
    
    # Resultado
    estado = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendiente')
    resultado = models.JSONField(default=dict)
    error_mensaje = models.TextField(blank=True)
    error_traceback = models.TextField(blank=True)
    
    # Contexto
    parametros_utilizados = models.JSONField(default=dict, help_text="Parámetros usados en esta ejecución")
    
    class Meta:
        verbose_name = "Ejecución de Regla"
        verbose_name_plural = "Ejecuciones de Reglas"
        ordering = ['-inicio']
        indexes = [
            models.Index(fields=['regla', '-inicio']),
            models.Index(fields=['estado']),
            models.Index(fields=['-inicio']),
        ]
    
    def __str__(self):
        return f"{self.regla.codigo} - {self.inicio.strftime('%Y-%m-%d %H:%M:%S')} - {self.estado}"
    
    @property
    def exitosa(self):
        return self.estado == 'exitosa'
    
    @property
    def tiempo_ejecucion(self):
        """Retorna duración en formato legible"""
        if self.duracion_segundos is None:
            return "N/A"
        if self.duracion_segundos < 60:
            return f"{self.duracion_segundos:.2f}s"
        return f"{self.duracion_segundos/60:.2f}m"
