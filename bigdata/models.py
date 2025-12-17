"""
Modelos de Base de Datos para FASE 2: Big Data & ML

Los clústeres se aplican a las pólizas después de ejecutar PASO 6 en Colab.
"""

from django.db import models
from polizas.models import Poliza


class ClusterAsignacion(models.Model):
    """
    Registro de asignación de clusters a pólizas.
    
    Se llena después de ejecutar el modelo K-Means en PASO 6.
    """
    poliza = models.OneToOneField(Poliza, on_delete=models.CASCADE, related_name='cluster_asignacion')
    cluster_id = models.IntegerField(null=True, blank=True, help_text="ID del cluster (0-k)")
    probabilidad = models.FloatField(default=0.0, help_text="Confianza de asignación")
    fecha_asignacion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Asignación de Cluster"
        verbose_name_plural = "Asignaciones de Clusters"
        ordering = ['cluster_id']
    
    def __str__(self):
        return f"POL {self.poliza.numero} -> Cluster {self.cluster_id}"


class ModeloEntrenamiento(models.Model):
    """
    Registro de entrenamientos de modelos K-Means.
    """
    ESTADO_CHOICES = [
        ('en_progreso', 'En Progreso'),
        ('completado', 'Completado'),
        ('error', 'Error'),
    ]
    
    fecha_inicio = models.DateTimeField(auto_now_add=True)
    fecha_finalizacion = models.DateTimeField(null=True, blank=True)
    k_optimo = models.IntegerField(null=True, blank=True)
    silhouette_score = models.FloatField(null=True, blank=True)
    num_polizas = models.IntegerField()
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='en_progreso')
    notas = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "Entrenamiento de Modelo"
        verbose_name_plural = "Entrenamientos de Modelos"
        ordering = ['-fecha_inicio']
    
    def __str__(self):
        return f"Entrenamiento {self.pk} (k={self.k_optimo}, {self.estado})"
