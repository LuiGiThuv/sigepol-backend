"""
URL configuration for sigepol project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from django.http import JsonResponse, FileResponse
from django.views.decorators.cache import never_cache
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

@never_cache
def frontend_view(request):
    """Sirve el frontend React o JSON si no está disponible"""
    # Intenta múltiples rutas posibles
    possible_paths = [
        BASE_DIR / 'frontend' / 'dist' / 'index.html',
        BASE_DIR / 'staticfiles' / 'index.html',
        os.path.join(os.environ.get('BUILD_DIR', BASE_DIR), 'frontend', 'dist', 'index.html'),
    ]
    
    for index_path in possible_paths:
        if Path(index_path).exists():
            try:
                with open(index_path, 'rb') as f:
                    return FileResponse(f, content_type='text/html; charset=utf-8')
            except Exception as e:
                print(f"Error sirviendo {index_path}: {e}")
    
    # Fallback: JSON response si no existe el frontend
    return JsonResponse({
        'message': '🎉 SIGEPOL Backend API está funcionando correctamente',
        'version': '1.0.0',
        'endpoints': {
            'api_docs': '/api/schema/swagger/',
            'api_redoc': '/api/schema/redoc/',
            'admin': '/admin/',
            'usuarios': '/api/usuarios/',
            'importaciones': '/api/importaciones/',
            'cobranzas': '/api/cobranzas/',
            'alertas': '/api/alertas/',
            'auditorias': '/api/auditorias/',
            'dashboard': '/api/dashboard/',
            'reportes': '/api/reportes/',
            'rules_engine': '/api/rules-engine/',
            'bigdata': '/api/bigdata/',
            'analytics': '/api/analytics/'
        },
        'status': 'deployed_successfully',
        'note': 'Frontend no disponible. Accede a /api/schema/swagger/ para documentación.'
    })

# Alias para compatibilidad
api_root = frontend_view

urlpatterns = [
    path("", api_root, name='root'),  # API Root
    path("admin/", admin.site.urls),
    
    # API Schema / Swagger
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    
    # API endpoints
    path("api/usuarios/", include("usuarios.urls")),
    path("api/importaciones/", include("importaciones.urls")),
    path("api/cobranzas/", include("cobranzas.urls")),
    path("api/alertas/", include("alertas.urls")),
    path("api/auditorias/", include("auditorias.urls")),
    path("api/dashboard/", include("dashboard.urls")),
    path("api/reportes/", include("reportes.urls")),  # PASO 9: Reportes Automáticos
    path("api/", include("rules_engine.urls")),  # PASO 11: Motor de Reglas
    path("api/bigdata/", include("bigdata.urls")),  # FASE 2: Big Data & ML
    path("api/analytics/", include("analytics.urls")),  # MÓDULO 3: ML & Analytics
]
