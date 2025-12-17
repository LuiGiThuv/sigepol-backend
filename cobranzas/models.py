from django.db import models
from django.contrib.auth import get_user_model
from polizas.models import Poliza

User = get_user_model()


class Cobranza(models.Model):
    ESTADO_CHOICES = [
        ('PENDIENTE', 'Pendiente'),
        ('EN_PROCESO', 'En Proceso'),
        ('PAGADA', 'Pagada'),
        ('VENCIDA', 'Vencida'),
        ('CANCELADA', 'Cancelada'),
    ]

    METODO_PAGO_CHOICES = [
        ('TRANSFERENCIA', 'Transferencia Bancaria'),
        ('CHEQUE', 'Cheque'),
        ('EFECTIVO', 'Efectivo'),
        ('TARJETA', 'Tarjeta'),
        ('DEBITO_AUTOMATICO', 'Débito Automático'),
    ]
    
    TIPO_COBRANZA_CHOICES = [
        ('PAGO_VIGENTE', 'Pago Vigente/Pendiente'),
        ('PAGO_VENCIDO', 'Pago Vencido'),
        ('RIESGO_FINANCIERO', 'Riesgo Financiero'),
    ]

    # Relación principal
    poliza = models.ForeignKey(Poliza, on_delete=models.CASCADE, related_name='cobranzas')
    
    # Información de la cobranza
    monto_uf = models.DecimalField(max_digits=10, decimal_places=2)
    monto_pesos = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    valor_uf = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Valor UF al momento de la cobranza")
    
    # Fechas
    fecha_emision = models.DateField(help_text="Fecha de emisión de la cobranza")
    fecha_vencimiento = models.DateField(help_text="Fecha límite de pago")
    fecha_pago = models.DateField(null=True, blank=True, help_text="Fecha real de pago")
    dias_atraso = models.IntegerField(default=0, help_text="Días de atraso si está vencida sin pagar")
    
    # Estados y clasificación
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='PENDIENTE')
    tipo_cobranza = models.CharField(max_length=30, choices=TIPO_COBRANZA_CHOICES, default='PAGO_VIGENTE', help_text="Clasificación contable de la cobranza")
    metodo_pago = models.CharField(max_length=20, choices=METODO_PAGO_CHOICES, null=True, blank=True)
    numero_documento = models.CharField(max_length=100, blank=True, help_text="Número de cheque, transferencia, etc.")
    
    # Información de origen (ETL)
    fuente_etl = models.BooleanField(default=True, help_text="¿Se creó desde ETL/Upload?")
    campo_pago_pendiente = models.CharField(max_length=50, blank=True, help_text="Campo del Excel que indicó pago pendiente")
    
    # Alerta financiera
    tiene_alerta_financiera = models.BooleanField(default=False, help_text="¿Tiene alerta de riesgo financiero?")
    razon_alerta = models.CharField(max_length=255, blank=True, help_text="Razón de la alerta (atraso recurrente, caída de prima, etc.)")
    
    # Información adicional
    observaciones = models.TextField(blank=True)
    usuario_registro = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='cobranzas_registradas')
    
    # Auditoría
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cobranza {self.id} - {self.poliza.numero} - {self.estado}"

    @property
    def dias_vencimiento(self):
        """Retorna los días hasta el vencimiento (negativo si ya venció)"""
        from datetime import date
        delta = self.fecha_vencimiento - date.today()
        return delta.days

    @property
    def esta_vencida(self):
        """Retorna True si la cobranza está vencida"""
        from datetime import date
        return self.fecha_vencimiento < date.today() and self.estado not in ['PAGADA', 'CANCELADA']
    
    @property
    def es_de_riesgo(self):
        """Retorna True si es de riesgo (vencida sin pagar o con alerta)"""
        return self.esta_vencida or self.tiene_alerta_financiera

    def calcular_monto_pesos(self, valor_uf=None):
        """Calcula el monto en pesos según el valor UF proporcionado"""
        if valor_uf:
            self.valor_uf = valor_uf
            self.monto_pesos = self.monto_uf * valor_uf
            return self.monto_pesos
        return None
    
    def actualizar_dias_atraso(self):
        """Actualiza el campo dias_atraso basado en fecha_vencimiento"""
        from datetime import date
        if self.estado not in ['PAGADA', 'CANCELADA']:
            hoy = date.today()
            if self.fecha_vencimiento < hoy:
                self.dias_atraso = (hoy - self.fecha_vencimiento).days
            else:
                self.dias_atraso = 0
        return self.dias_atraso

    class Meta:
        verbose_name = "Cobranza"
        verbose_name_plural = "Cobranzas"
        ordering = ['-fecha_emision']
        indexes = [
            models.Index(fields=['estado', 'fecha_vencimiento']),
            models.Index(fields=['poliza', 'estado']),
            models.Index(fields=['tipo_cobranza', 'estado']),
            models.Index(fields=['tiene_alerta_financiera']),
        ]
