"""
Modelo para validar frescura de datos (Data Freshness Validation)

Solución profesional para evitar falsas alertas por datos desactualizados.
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

User = get_user_model()


class DataFreshness(models.Model):
    """
    Registra la última actualización de datos por cliente y a nivel sistema.
    
    Propósito:
    - Evitar falsas alertas por datos desactualizados
    - Detectar clientes sin carga reciente
    - Validar confiabilidad de alertas
    - Generar avisos de falta de actualización
    
    Ejemplo:
        - Cliente "ABC Corp" fue actualizado hace 15 días ✅ (confiable)
        - Cliente "XYZ Ltd" no tiene carga hace 45 días ⚠️ (no confiable)
    """
    
    # Referencia al cliente (RUT o ID)
    cliente = models.CharField(
        max_length=50,
        db_index=True,
        help_text="RUT, ID o identificador único del cliente"
    )
    
    # Última fecha cuando se subió un archivo con datos de este cliente
    ultima_actualizacion = models.DateField(
        auto_now=True,
        db_index=True,
        help_text="Última vez que se actualizó información de este cliente"
    )
    
    # Cuántos días han pasado sin actualización
    dias_sin_actualizacion = models.IntegerField(
        default=0,
        help_text="Días desde la última carga"
    )
    
    # Si debe generar alerta de falta de carga
    alerta_frescura = models.BooleanField(
        default=False,
        help_text="¿Se debe generar alerta por falta de actualización?"
    )
    
    # Cuándo se registró por primera vez
    fecha_registro = models.DateField(
        auto_now_add=True,
        help_text="Primera vez que se registró este cliente"
    )
    
    # Cuándo fue la última carga exitosa
    fecha_ultima_carga = models.DateField(
        null=True,
        blank=True,
        help_text="Última carga de archivo para este cliente"
    )
    
    # Usuario que realizó la última carga
    usuario_ultima_carga = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cargas_cliente'
    )
    
    # Cantidad de registros actualizados en la última carga
    registros_actualizados = models.IntegerField(
        default=0,
        help_text="Cuántos registros (pólizas/cobranzas) se actualizaron"
    )
    
    class Meta:
        ordering = ['-ultima_actualizacion']
        indexes = [
            models.Index(fields=['cliente', '-ultima_actualizacion']),
            models.Index(fields=['alerta_frescura']),
            models.Index(fields=['dias_sin_actualizacion']),
        ]
        verbose_name = 'Frescura de Datos'
        verbose_name_plural = 'Frescura de Datos'
        unique_together = [['cliente']]
    
    def __str__(self):
        return f"{self.cliente} - Actualizado: {self.ultima_actualizacion} ({self.dias_sin_actualizacion} días)"
    
    def actualizar_dias(self):
        """Recalcula cuántos días han pasado sin actualización"""
        self.dias_sin_actualizacion = (timezone.now().date() - self.ultima_actualizacion).days
        
        # Si pasan más de 30 días, marcar como requiere alerta
        if self.dias_sin_actualizacion >= 30:
            self.alerta_frescura = True
        else:
            self.alerta_frescura = False
        
        self.save(update_fields=['dias_sin_actualizacion', 'alerta_frescura'])
        return self.dias_sin_actualizacion
    
    def es_fresca(self, dias_limite=30):
        """
        Verifica si los datos están actualizados (frescura)
        
        Args:
            dias_limite: Máximo de días permitidos sin actualización
        
        Returns:
            True si la data fue actualizada hace menos de dias_limite días
        """
        self.actualizar_dias()
        return self.dias_sin_actualizacion < dias_limite
    
    def obtener_estado_frescura(self):
        """
        Retorna el estado de frescura con descripción
        
        Returns:
            dict: {status, dias, confiable, mensaje}
        """
        self.actualizar_dias()
        
        if self.dias_sin_actualizacion < 15:
            status = 'EXCELENTE'
            confiable = True
        elif self.dias_sin_actualizacion < 30:
            status = 'BUENO'
            confiable = True
        elif self.dias_sin_actualizacion < 45:
            status = 'ADVERTENCIA'
            confiable = False
        else:
            status = 'CRITICO'
            confiable = False
        
        return {
            'status': status,
            'dias_sin_actualizar': self.dias_sin_actualizacion,
            'confiable': confiable,
            'cliente': self.cliente,
            'ultima_carga': self.ultima_actualizacion.isoformat(),
            'mensaje': self._generar_mensaje(status)
        }
    
    def _generar_mensaje(self, status):
        """Genera mensaje según el estado"""
        if status == 'EXCELENTE':
            return f"✅ Datos muy actualizados (hace {self.dias_sin_actualizacion} días)"
        elif status == 'BUENO':
            return f"✔️ Datos actualizados (hace {self.dias_sin_actualizacion} días)"
        elif status == 'ADVERTENCIA':
            return f"⚠️ Datos desactualizados (hace {self.dias_sin_actualizacion} días)"
        else:
            return f"🔴 Datos muy desactualizados (hace {self.dias_sin_actualizacion} días) - SUBIR ARCHIVO URGENTEMENTE"
    
    @staticmethod
    def registrar_carga(cliente, usuario, registros_actualizados=0):
        """
        Registra una nueva carga de datos para un cliente
        
        Args:
            cliente: Identificador del cliente
            usuario: Usuario que realizó la carga
            registros_actualizados: Cuántos registros se actualizaron
        
        Returns:
            DataFreshness: Objeto actualizado
        """
        hoy = timezone.now().date()
        
        data_freshness, created = DataFreshness.objects.get_or_create(
            cliente=cliente,
            defaults={
                'ultima_actualizacion': hoy,
                'fecha_ultima_carga': hoy,
                'usuario_ultima_carga': usuario,
                'registros_actualizados': registros_actualizados,
                'dias_sin_actualizacion': 0,
                'alerta_frescura': False,
            }
        )
        
        if not created:
            data_freshness.ultima_actualizacion = hoy
            data_freshness.fecha_ultima_carga = hoy
            data_freshness.usuario_ultima_carga = usuario
            data_freshness.registros_actualizados = registros_actualizados
            data_freshness.dias_sin_actualizacion = 0
            data_freshness.alerta_frescura = False
            data_freshness.save()
        
        return data_freshness
    
    @staticmethod
    def obtener_clientes_desactualizados(dias_limite=30):
        """
        Obtiene todos los clientes con datos desactualizados
        
        Args:
            dias_limite: Días sin actualización que considera crítico
        
        Returns:
            QuerySet: Clientes con data > dias_limite días
        """
        limite_fecha = timezone.now().date() - timedelta(days=dias_limite)
        return DataFreshness.objects.filter(ultima_actualizacion__lt=limite_fecha)
    
    @staticmethod
    def obtener_estadisticas_frescura():
        """
        Retorna estadísticas de frescura global
        
        Returns:
            dict: Estadísticas de todo el sistema
        """
        total_clientes = DataFreshness.objects.count()
        frescos = DataFreshness.objects.filter(dias_sin_actualizacion__lt=30).count()
        desactualizados = DataFreshness.objects.filter(dias_sin_actualizacion__gte=30).count()
        criticos = DataFreshness.objects.filter(dias_sin_actualizacion__gte=45).count()
        
        dias_promedio = sum([df.dias_sin_actualizacion for df in DataFreshness.objects.all()]) / max(total_clientes, 1)
        
        return {
            'total_clientes': total_clientes,
            'clientes_frescos': frescos,
            'clientes_desactualizados': desactualizados,
            'clientes_criticos': criticos,
            'dias_promedio_sin_actualizar': round(dias_promedio, 1),
            'porcentaje_frescos': round((frescos / max(total_clientes, 1)) * 100, 1),
        }
