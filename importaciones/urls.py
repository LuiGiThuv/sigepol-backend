from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ExcelUploadView,
    HistorialImportacionListView,
    HistorialImportacionDeleteView,
    ExportarPolizasView,
    ExportarHistorialView,
    UploadExcelETLView,
    DataUploadDetailView,
    UploadErrorsDownloadView,
    DataUploadViewSet,
    ImportErrorRowViewSet,
    DataFreshnessListView,
    DataFreshnessDetailView,
    DataFreshnessEstadisticasView,
    DataFreshnessCheckView,
    DataFreshnessClientesDesactualizadosView,
    HistorialEstadisticasView,
    VisualizarDatosImportacionView,
)
from .views_excel_mejorado import (
    ExcelPreviewView,
    ExcelValidationView,
    ExcelUploadMejoradoView,
    HistorialCargasView,
    DescargarExcelOriginalView,
)

# Router para ViewSets
router = DefaultRouter()
router.register(r'uploads', DataUploadViewSet, basename='dataupload')
router.register(r'upload-errors', ImportErrorRowViewSet, basename='importerrorrow')

urlpatterns = [
    # MÓDULO 2: ENDPOINTS MEJORADOS (PASO 2.1-2.5)
    path("preview/", ExcelPreviewView.as_view(), name="excel_preview"),
    path("validar/", ExcelValidationView.as_view(), name="excel_validation"),
    path("upload-mejorado/", ExcelUploadMejoradoView.as_view(), name="excel_upload_mejorado"),
    path("historial-cargas/", HistorialCargasView.as_view(), name="historial_cargas"),
    path("descargar/<int:pk>/", DescargarExcelOriginalView.as_view(), name="descargar_excel"),
    
    # Legacy endpoints
    path("upload-excel/", ExcelUploadView.as_view(), name="upload_excel"),
    path("historial/", HistorialImportacionListView.as_view(), name="historial_importaciones"),
    path("historial/<int:historial_id>/", HistorialImportacionDeleteView.as_view(), name="historial_delete"),
    path("visualizar/<int:historial_id>/", VisualizarDatosImportacionView.as_view(), name="visualizar_datos"),
    path("exportar-polizas/", ExportarPolizasView.as_view(), name="exportar_polizas"),
    path("exportar-historial/", ExportarHistorialView.as_view(), name="exportar_historial"),
    
    # ETL Pipeline endpoints (FASE 1 PASO 6)
    path("etl/upload-excel/", UploadExcelETLView.as_view(), name="etl_upload_excel"),
    path("etl/upload/<int:upload_id>/", DataUploadDetailView.as_view(), name="etl_upload_detail"),
    path("etl/upload/<int:upload_id>/download-errors/", UploadErrorsDownloadView.as_view(), name="etl_download_errors"),
    
    # Data Freshness endpoints (PASO 15)
    path("frescura/estadisticas/", DataFreshnessEstadisticasView.as_view(), name="frescura_estadisticas"),
    path("frescura/desactualizados/", DataFreshnessClientesDesactualizadosView.as_view(), name="frescura_desactualizados"),
    path("frescura/verificar/", DataFreshnessCheckView.as_view(), name="frescura_verificar"),
    path("frescura/", DataFreshnessListView.as_view(), name="frescura_list"),
    path("frescura/<str:cliente>/", DataFreshnessDetailView.as_view(), name="frescura_detail"),
    
    # Historial estadísticas
    path("historial-estadisticas/", HistorialEstadisticasView.as_view(), name="historial_estadisticas"),
    
    # Router
    path("", include(router.urls)),
]

