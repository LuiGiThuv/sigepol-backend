from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RuleViewSet, RuleExecutionViewSet

# Router para los ViewSets
router = DefaultRouter()
router.register(r'rules', RuleViewSet, basename='rule')
router.register(r'rule-executions', RuleExecutionViewSet, basename='rule-execution')

urlpatterns = [
    path('', include(router.urls)),
]
