"""
URLs para API de análisis ML
"""

from django.urls import path
from .views import (
    StatusMLView,
    PredictarClustersView,
    ClusterStatsView,
    PredictarIndividualView,
    ReporteLimpiezaView,
    ClustersPredictosView
)

urlpatterns = [
    # Status y configuración
    path('status/', StatusMLView.as_view(), name='ml-status'),
    
    # PASO 4-6: Endpoint principal - Pólizas con clusters y riesgo
    path('clusters/', ClustersPredictosView.as_view(), name='clusters-predichos'),
    
    # Predicción de clusters
    path('predecir-clusters/', PredictarClustersView.as_view(), name='predecir-clusters'),
    path('predecir-individual/', PredictarIndividualView.as_view(), name='predecir-individual'),
    
    # Estadísticas
    path('cluster-stats/', ClusterStatsView.as_view(), name='cluster-stats'),
    path('reporte-limpieza/', ReporteLimpiezaView.as_view(), name='reporte-limpieza'),
]
