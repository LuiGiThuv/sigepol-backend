"""
URLs para el módulo de Big Data (FASE 2)

Nota: Los endpoints principales se ejecutan en Google Colab.
Este módulo mantiene los modelos y la configuración de Django.
"""

from django.urls import path
from . import views

app_name = 'bigdata'

urlpatterns = [
    # PASO ML.0 — Dataset para entrenamientoML
    path('dataset/', views.DatasetMLView.as_view(), name='dataset_ml'),
    
    # Endpoints de clustering
    path('clusters/', views.ClusterListView.as_view(), name='cluster_list'),
    path('modelo-status/', views.ModeloStatusView.as_view(), name='modelo_status'),
    
    # Los endpoints de PASO 6 se ejecutan en Colab
    # path('kmeans/train/', views.train_kmeans, name='train_kmeans'),
    # path('clusters/', views.get_clusters, name='get_clusters'),
]

