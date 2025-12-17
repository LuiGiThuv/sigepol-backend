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
from django.http import HttpResponse

def api_root(request):
    """API Root endpoint con página bonita"""
    html = """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>SIGEPOL Backend API</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            }
            .container {
                background: white;
                border-radius: 12px;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
                max-width: 900px;
                width: 100%;
                padding: 40px;
            }
            h1 {
                color: #333;
                margin-bottom: 10px;
                font-size: 2.5em;
            }
            .subtitle {
                color: #666;
                font-size: 1.1em;
                margin-bottom: 30px;
            }
            .status {
                display: inline-block;
                background: #10b981;
                color: white;
                padding: 8px 16px;
                border-radius: 20px;
                font-size: 0.9em;
                margin-bottom: 30px;
                font-weight: 600;
            }
            .endpoints {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 15px;
                margin-top: 30px;
            }
            .endpoint {
                background: #f3f4f6;
                padding: 15px;
                border-radius: 8px;
                border-left: 4px solid #667eea;
                transition: all 0.3s ease;
            }
            .endpoint:hover {
                background: #e5e7eb;
                transform: translateX(5px);
            }
            .endpoint a {
                color: #667eea;
                text-decoration: none;
                font-weight: 600;
            }
            .endpoint a:hover {
                text-decoration: underline;
            }
            .endpoint-label {
                color: #999;
                font-size: 0.85em;
                margin-bottom: 5px;
            }
            .docs-section {
                background: #f0f4ff;
                padding: 20px;
                border-radius: 8px;
                margin-top: 30px;
            }
            .docs-section h2 {
                color: #667eea;
                margin-bottom: 15px;
                font-size: 1.3em;
            }
            .docs-link {
                display: inline-block;
                background: #667eea;
                color: white;
                padding: 12px 24px;
                border-radius: 6px;
                text-decoration: none;
                margin-right: 10px;
                margin-bottom: 10px;
                transition: background 0.3s ease;
            }
            .docs-link:hover {
                background: #764ba2;
            }
            .api-info {
                color: #666;
                font-size: 0.95em;
                margin-top: 30px;
                padding-top: 30px;
                border-top: 1px solid #eee;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎉 SIGEPOL Backend API</h1>
            <p class="subtitle">Sistema Integral de Gestión de Pólizas</p>
            <div class="status">✓ Deployed Successfully</div>
            
            <div class="docs-section">
                <h2>📚 Documentación</h2>
                <a href="/api/schema/swagger/" class="docs-link">📖 Swagger UI (Interactivo)</a>
                <a href="/api/schema/redoc/" class="docs-link">📋 ReDoc (Referencia)</a>
                <a href="/admin/" class="docs-link">⚙️ Panel Admin</a>
            </div>
            
            <h2 style="margin-top: 30px; color: #333;">📡 Endpoints Disponibles</h2>
            <div class="endpoints">
                <div class="endpoint">
                    <div class="endpoint-label">Usuarios</div>
                    <a href="/api/usuarios/">/api/usuarios/</a>
                </div>
                <div class="endpoint">
                    <div class="endpoint-label">Importaciones</div>
                    <a href="/api/importaciones/">/api/importaciones/</a>
                </div>
                <div class="endpoint">
                    <div class="endpoint-label">Cobranzas</div>
                    <a href="/api/cobranzas/">/api/cobranzas/</a>
                </div>
                <div class="endpoint">
                    <div class="endpoint-label">Alertas</div>
                    <a href="/api/alertas/">/api/alertas/</a>
                </div>
                <div class="endpoint">
                    <div class="endpoint-label">Auditorías</div>
                    <a href="/api/auditorias/">/api/auditorias/</a>
                </div>
                <div class="endpoint">
                    <div class="endpoint-label">Dashboard</div>
                    <a href="/api/dashboard/">/api/dashboard/</a>
                </div>
                <div class="endpoint">
                    <div class="endpoint-label">Reportes</div>
                    <a href="/api/reportes/">/api/reportes/</a>
                </div>
                <div class="endpoint">
                    <div class="endpoint-label">Rules Engine</div>
                    <a href="/api/rules-engine/">/api/rules-engine/</a>
                </div>
                <div class="endpoint">
                    <div class="endpoint-label">Big Data</div>
                    <a href="/api/bigdata/">/api/bigdata/</a>
                </div>
                <div class="endpoint">
                    <div class="endpoint-label">Analytics</div>
                    <a href="/api/analytics/">/api/analytics/</a>
                </div>
            </div>
            
            <div class="api-info">
                <strong>Versión:</strong> 1.0.0 | 
                <strong>Status:</strong> Production | 
                <strong>Framework:</strong> Django REST Framework
            </div>
        </div>
    </body>
    </html>
    """
    return HttpResponse(html, content_type='text/html')

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
