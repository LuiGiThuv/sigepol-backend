"""
URLs para reportes automáticos inteligentes
PASO 9: Módulo de Reportes Automáticos Inteligentes
"""

from django.urls import path
from .views import (
    ReportePolizasVencidasView,
    ReportePolizasPorExpirarView,
    ReporteProduccionMensualView,
    ReporteTopClientesView,
)

urlpatterns = [
    # PASO 9.1: Pólizas vencidas
    path('polizas-vencidas/', ReportePolizasVencidasView.as_view(), name='reporte-polizas-vencidas'),
    
    # PASO 9.2: Pólizas por expirar (30 días o menos)
    path('polizas-por-expirar/', ReportePolizasPorExpirarView.as_view(), name='reporte-polizas-por-expirar'),
    
    # PASO 9.3: Producción mensual
    path('produccion-mensual/', ReporteProduccionMensualView.as_view(), name='reporte-produccion-mensual'),
    
    # PASO 9.4: Top clientes
    path('top-clientes/', ReporteTopClientesView.as_view(), name='reporte-top-clientes'),
]
