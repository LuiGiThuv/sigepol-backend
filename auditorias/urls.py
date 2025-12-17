from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AuditoriaViewSet, LogAccesoViewSet, AuditLogViewSet, AdminStatsView, RecentUploadsView

router = DefaultRouter()
router.register(r'acciones', AuditoriaViewSet, basename='auditoria-acciones')
router.register(r'logs', LogAccesoViewSet, basename='auditoria-logs')
router.register(r'audit-logs', AuditLogViewSet, basename='audit-logs')

urlpatterns = [
    path('', include(router.urls)),
    path('admin-stats/', AdminStatsView.as_view(), name='admin-stats'),
    path('recent-uploads/', RecentUploadsView.as_view(), name='recent-uploads'),
]
