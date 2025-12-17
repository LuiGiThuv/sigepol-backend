from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AlertaViewSet,
    AlertasActivasView,
    AlertasHistorialView,
    ResolverAlertaView,
    AlertasEstadisticasView,
    EjecutarReglasAlertasView,  # PASO 10
    AlertaHistorialListView,  # PASO 11
    TestEmailAlertaView,  # PASO 16: Envío de emails
)
from .ml_views import (  # PASO 14: ML Integration
    MLImportResultsView,
    MLAlertsListView,
    MLAlertsStatsView,
)

router = DefaultRouter()
router.register(r'', AlertaViewSet, basename='alerta')

urlpatterns = [
    # Nuevos endpoints PASO 7 (deben estar primero para tener prioridad)
    path('activas/', AlertasActivasView.as_view(), name='alertas_activas'),
    path('historial/', AlertasHistorialView.as_view(), name='alertas_historial'),
    path('estadisticas/', AlertasEstadisticasView.as_view(), name='alertas_estadisticas'),
    path('resolver/<int:alerta_id>/', ResolverAlertaView.as_view(), name='resolver_alerta'),
    
    # PASO 10: Ejecutar reglas automáticas de alertas
    path('run/', EjecutarReglasAlertasView.as_view(), name='ejecutar_reglas_alertas'),
    
    # PASO 11: Historial completo de alertas para auditoría
    path('historial-list/', AlertaHistorialListView.as_view(), name='alerta_historial_list'),
    
    # PASO 14: ML Integration - Alertas Predictivas
    path('ml/import/', MLImportResultsView.as_view(), name='ml-import'),
    path('ml/alertas/', MLAlertsListView.as_view(), name='ml-alerts-list'),
    path('ml/stats/', MLAlertsStatsView.as_view(), name='ml-stats'),
    
    # PASO 16: Test de envío de emails
    path('test-email/<int:alerta_id>/', TestEmailAlertaView.as_view(), name='test-email-alerta'),
    
    # Routers del ViewSet (después para que las rutas específicas tengan prioridad)
    path('', include(router.urls)),
]
