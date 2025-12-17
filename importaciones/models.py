from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

User = get_user_model()


class ImportErrorRow(models.Model):
    """
    Registra filas con errores durante la importación
    """
    upload = models.ForeignKey('DataUpload', on_delete=models.CASCADE, related_name='error_rows')
    row_number = models.IntegerField()
    raw_data = models.JSONField()
    error = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['row_number']
        verbose_name = 'Error de Importación'
        verbose_name_plural = 'Errores de Importación'

    def __str__(self):
        return f'Upload {self.upload.id} - Fila {self.row_number}: {self.error[:50]}'


class DataUpload(models.Model):
    """
    Modelo para registrar cargas de archivos con estados del pipeline
    MÓDULO 2: PASO 2.1 — Modelo CargaExcel mejorado
    """
    STATUS_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('validando', 'Validando'),
        ('limpiando', 'Limpiando'),
        ('procesando', 'Procesando'),
        ('ml', 'Aplicando ML'),
        ('completado', 'Completado'),
        ('error', 'Error'),
    ]

    archivo = models.FileField(upload_to="uploads/")
    nombre_archivo_original = models.CharField(
        max_length=255, 
        null=True, 
        blank=True,
        help_text="Nombre original del archivo cargado"
    )
    cargado_por = models.ForeignKey(User, on_delete=models.CASCADE, related_name='data_uploads')
    fecha_carga = models.DateTimeField(auto_now_add=True, db_index=True)
    estado = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendiente', db_index=True)
    mensaje_error = models.TextField(blank=True, null=True)
    detalles_procesamiento = models.JSONField(null=True, blank=True, help_text="Detalles del procesamiento")
    error_file = models.FileField(upload_to="upload_errors/", blank=True, null=True, help_text="CSV con filas de error")
    processed_rows = models.IntegerField(default=0, help_text="Total de filas procesadas")
    inserted_rows = models.IntegerField(default=0, help_text="Total de filas insertadas")
    updated_rows = models.IntegerField(default=0, help_text="Total de filas actualizadas")
    
    # VALIDACIÓN ESTRUCTURAL (PASO 2.3)
    columnas_detectadas = models.JSONField(null=True, blank=True, help_text="Lista de columnas detectadas en el Excel")
    columnas_validadas = models.BooleanField(default=False, help_text="¿Se validaron las columnas?")
    errores_validacion = models.JSONField(null=True, blank=True, help_text="Errores encontrados en validación")
    
    # PREVIEW (PASO 2.4)
    preview_filas = models.JSONField(null=True, blank=True, help_text="Primeras 5-10 filas para preview")
    
    # CONTROL
    descargado = models.BooleanField(default=False, help_text="¿Se descargó el archivo original?")
    fecha_descarga = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-fecha_carga']
        indexes = [
            models.Index(fields=['estado', '-fecha_carga']),
            models.Index(fields=['cargado_por', '-fecha_carga']),
            models.Index(fields=['fecha_carga']),
        ]
        verbose_name = 'Carga de Datos'
        verbose_name_plural = 'Cargas de Datos'

    def __str__(self):
        return f"Upload #{self.id} - {self.nombre_archivo_original} - {self.estado}"
    
    def marcar_descargado(self):
        """Registra cuando se descarga el archivo original"""
        from django.utils import timezone
        self.descargado = True
        self.fecha_descarga = timezone.now()
        self.save()
    
    def get_resumen(self):
        """Retorna resumen de la carga"""
        return {
            'id': self.id,
            'archivo': self.nombre_archivo_original,
            'estado': self.get_estado_display(),
            'fecha_carga': self.fecha_carga.isoformat(),
            'usuario': self.cargado_por.username,
            'procesadas': self.processed_rows,
            'insertadas': self.inserted_rows,
            'actualizadas': self.updated_rows,
            'errores': self.processed_rows - self.inserted_rows - self.updated_rows,
        }


class HistorialImportacion(models.Model):
    """
    Historial de importaciones (modelo anterior, mantenido para compatibilidad)
    """
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    archivo = models.FileField(upload_to="importaciones/")
    fecha_carga = models.DateTimeField(auto_now_add=True)
    filas_insertadas = models.IntegerField(default=0)
    filas_actualizadas = models.IntegerField(default=0)
    filas_erroneas = models.IntegerField(default=0)
    clientes_ingresados = models.IntegerField(default=0, help_text="Total de pólizas únicas procesadas en esta importación")
    mensaje = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Importación #{self.id} - {self.fecha_carga.strftime('%Y-%m-%d %H:%M')} ({self.clientes_ingresados} pólizas únicas)"


class DataFreshness(models.Model):
    """
    Registra la última actualización de datos por cliente.
    
    Propósito: Evitar falsas alertas por datos desactualizados.
    
    Ejemplos:
    - Cliente "ABC Corp" actualizado hace 15 días ✅ (confiable)
    - Cliente "XYZ Ltd" sin carga hace 45 días ⚠️ (no confiable)
    """
    
    cliente = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        help_text="RUT o ID del cliente"
    )
    
    ultima_actualizacion = models.DateField(
        default=timezone.now,
        db_index=True,
        help_text="Última vez que se actualizó información"
    )
    
    dias_sin_actualizacion = models.IntegerField(
        default=0,
        help_text="Días desde última actualización"
    )
    
    alerta_frescura = models.BooleanField(
        default=False,
        help_text="¿Requiere alerta por falta de actualización?"
    )
    
    fecha_ultima_carga = models.DateField(
        null=True,
        blank=True,
        help_text="Última carga de archivo"
    )
    
    usuario_ultima_carga = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cargas_cliente_frescura'
    )
    
    registros_actualizados = models.IntegerField(
        default=0,
        help_text="Registros actualizados en última carga"
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
    
    def __str__(self):
        return f"{self.cliente} - Actualizado: {self.ultima_actualizacion} ({self.dias_sin_actualizacion} días)"
    
    def actualizar_dias(self):
        """Recalcula días sin actualización"""
        self.dias_sin_actualizacion = (timezone.now().date() - self.ultima_actualizacion).days
        
        if self.dias_sin_actualizacion >= 30:
            self.alerta_frescura = True
        else:
            self.alerta_frescura = False
        
        self.save(update_fields=['dias_sin_actualizacion', 'alerta_frescura'])
        return self.dias_sin_actualizacion
    
    def es_fresca(self, dias_limite=30):
        """Verifica si datos están actualizados"""
        self.actualizar_dias()
        return self.dias_sin_actualizacion < dias_limite
    
    def obtener_estado_frescura(self):
        """Retorna estado con descripción"""
        self.actualizar_dias()
        
        if self.dias_sin_actualizacion < 15:
            status = 'EXCELENTE'
            emoji = '✅'
            confiable = True
        elif self.dias_sin_actualizacion < 30:
            status = 'BUENO'
            emoji = '✔️'
            confiable = True
        elif self.dias_sin_actualizacion < 45:
            status = 'ADVERTENCIA'
            emoji = '⚠️'
            confiable = False
        else:
            status = 'CRITICO'
            emoji = '🔴'
            confiable = False
        
        return {
            'status': status,
            'emoji': emoji,
            'dias_sin_actualizar': self.dias_sin_actualizacion,
            'confiable': confiable,
            'cliente': self.cliente,
            'ultima_carga': self.ultima_actualizacion.isoformat(),
            'mensaje': f"{emoji} {status}: hace {self.dias_sin_actualizacion} días"
        }
    
    @staticmethod
    def registrar_carga(cliente, usuario, registros_actualizados=0):
        """Registra una nueva carga de datos"""
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
        """Obtiene clientes con datos desactualizados"""
        limite_fecha = timezone.now().date() - timedelta(days=dias_limite)
        return DataFreshness.objects.filter(ultima_actualizacion__lt=limite_fecha)
    
    @staticmethod
    def obtener_estadisticas_frescura():
        """Retorna estadísticas globales de frescura"""
        total_clientes = DataFreshness.objects.count()
        frescos = DataFreshness.objects.filter(dias_sin_actualizacion__lt=30).count()
        advertencia = DataFreshness.objects.filter(
            dias_sin_actualizacion__gte=30,
            dias_sin_actualizacion__lt=45
        ).count()
        criticos = DataFreshness.objects.filter(dias_sin_actualizacion__gte=45).count()
        
        # Obtener lista de clientes desactualizados
        clientes_desactualizados = list(
            DataFreshness.objects.filter(dias_sin_actualizacion__gte=30).values_list('cliente', flat=True)
        )
        
        if total_clientes > 0:
            porcentaje_fresco = round((frescos / total_clientes) * 100, 1)
            porcentaje_advertencia = round((advertencia / total_clientes) * 100, 1)
            porcentaje_critico = round((criticos / total_clientes) * 100, 1)
        else:
            porcentaje_fresco = porcentaje_advertencia = porcentaje_critico = 0.0
        
        return {
            'total_clientes': total_clientes,
            'clientes_frescos': frescos,
            'clientes_con_advertencia': advertencia,
            'clientes_criticos': criticos,
            'porcentaje_fresco': porcentaje_fresco,
            'porcentaje_advertencia': porcentaje_advertencia,
            'porcentaje_critico': porcentaje_critico,
            'clientes_desactualizados': clientes_desactualizados,
        }
