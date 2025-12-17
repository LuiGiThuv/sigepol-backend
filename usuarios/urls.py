from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import UserViewSet
from .admin_views import AdminUserManagementViewSet

app_name = 'usuarios'

# Router para administración de usuarios (PASO 12) - registrar primero!
admin_router = DefaultRouter()
admin_router.register(r'admin', AdminUserManagementViewSet, basename='admin-user')

# Router para usuarios normales
user_router = DefaultRouter()
user_router.register(r'', UserViewSet, basename='user')

urlpatterns = [
    # JWT Token endpoints
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Admin User Management endpoints (PASO 12) - primero
    path('', include(admin_router.urls)),
    
    # User endpoints (usuarios normales)
    path('', include(user_router.urls)),
]
