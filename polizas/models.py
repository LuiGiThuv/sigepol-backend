from django.db import models
from clientes.models import Cliente
from django.utils import timezone
from datetime import timedelta


class Poliza(models.Model):
    ESTADO_CHOICES = [
        ('VIGENTE', 'Vigente'),
        ('VENCIDA', 'Vencida'),
        ('CANCELADA', 'Cancelada'),
    ]
    
    FRESHNESS_STATUS_CHOICES = [
        ('excelente', 'Excelente (0-7 días)'),
        ('bueno', 'Bueno (8-30 días)'),
        ('advertencia', 'Advertencia (31-60 días)'),
        ('critico', 'Crítico (>60 días)'),
    ]

    numero = models.CharField(max_length=50, unique=True)
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='polizas')
    fecha_inicio = models.DateField()
    fecha_vencimiento = models.DateField()
    monto_uf = models.DecimalField(max_digits=10, decimal_places=2)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='VIGENTE')
    cluster = models.IntegerField(blank=True, null=True, db_index=True, help_text="Cluster ML asignado")
    
    # DFVS — Data Freshness Validation Status
    ultima_actualizacion = models.DateField(auto_now=True, help_text="Última fecha de importación/actualización")
    frescura_estado = models.CharField(
        max_length=20, 
        choices=FRESHNESS_STATUS_CHOICES, 
        default='excelente',
        help_text="Indicador de confianza de datos"
    )
    datos_confiables = models.BooleanField(default=True, help_text="False si > 30 días sin actualizar")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.numero} - {self.cliente.nombre}"
    
    def actualizar_frescura(self):
        """
        Calcula y actualiza el estado de frescura de datos.
        Se ejecuta en señales post_save y en tareas batch.
        """
        from datetime import date
        dias_antiguedad = (date.today() - self.ultima_actualizacion).days
        
        if dias_antiguedad <= 7:
            self.frescura_estado = 'excelente'
            self.datos_confiables = True
        elif dias_antiguedad <= 30:
            self.frescura_estado = 'bueno'
            self.datos_confiables = True
        elif dias_antiguedad <= 60:
            self.frescura_estado = 'advertencia'
            self.datos_confiables = False
        else:
            self.frescura_estado = 'critico'
            self.datos_confiables = False
        
        self.save(update_fields=['frescura_estado', 'datos_confiables'])

    class Meta:
        verbose_name = "Póliza"
        verbose_name_plural = "Pólizas"
        ordering = ['-fecha_vencimiento']
        indexes = [
            models.Index(fields=['-ultima_actualizacion']),
            models.Index(fields=['frescura_estado']),
        ]
