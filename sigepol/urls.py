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
from django.http import FileResponse, JsonResponse
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

def frontend_view(request):
    """Sirve index.html del frontend para SPA routing"""
    index_path = BASE_DIR / 'frontend' / 'dist' / 'index.html'
    
    if index_path.exists():
        return FileResponse(open(index_path, 'rb'), content_type='text/html')
    else:
        # Fallback si el frontend no está compilado
        return JsonResponse({
            'message': '🎉 SIGEPOL Backend API está funcionando correctamente',
            'version': '1.0.0',
            'endpoints': {
                'api_docs': '/api/schema/swagger/',
                'admin': '/admin/',
                'api': '/api/'
            },
            'status': 'deployed_successfully',
            'note': 'Frontend no compilado. Accede a /api/schema/swagger/ para documentación.'
        })

urlpatterns = [
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
    
    # Frontend SPA - catch all (debe ir al final)
    path("", frontend_view, name='frontend'),
]

# Serve static files in production
if not settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
