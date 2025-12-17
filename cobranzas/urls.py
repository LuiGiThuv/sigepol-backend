from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CobranzaViewSet

router = DefaultRouter()
router.register(r'', CobranzaViewSet, basename='cobranza')

urlpatterns = [
    path('', include(router.urls)),
]
