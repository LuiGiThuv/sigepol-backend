"""
Tests para el módulo de Dashboard (PASO 8)
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from datetime import timedelta
from django.utils import timezone

from polizas.models import Poliza
from importaciones.models import DataUpload
from alertas.models import Alerta
from auditorias.models import AuditoriaAccion

User = get_user_model()


class DashboardAPITestCase(APITestCase):
    """Tests para los endpoints del dashboard"""

    def setUp(self):
        """Preparar datos de prueba"""
        self.admin_user = User.objects.create_superuser(
            username='admin', 
            password='admin123',
            email='admin@test.com'
        )
        # Set role to admin for permission checks
        self.admin_user.role = 'admin'
        self.admin_user.is_staff = True
        self.admin_user.is_superuser = True
        self.admin_user.save()
        self.client.force_authenticate(user=self.admin_user)

    def test_system_stats_endpoint(self):
        """Test endpoint de estadísticas del sistema"""
        url = '/api/dashboard/stats/system/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('usuarios', response.data)
        self.assertIn('alertas_activas', response.data)
        self.assertIn('cargas_totales', response.data)

    def test_business_stats_endpoint(self):
        """Test endpoint de estadísticas comerciales"""
        url = '/api/dashboard/stats/business/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('polizas_totales', response.data)
        self.assertIn('prima_total_uf', response.data)
        self.assertIn('produccion_hoy', response.data)

    def test_activity_endpoint(self):
        """Test endpoint de actividad reciente"""
        url = '/api/dashboard/stats/activity/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)

    def test_etl_stats_endpoint(self):
        """Test endpoint de estadísticas ETL"""
        url = '/api/dashboard/stats/etl/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)

    def test_alert_summary_endpoint(self):
        """Test endpoint de resumen de alertas"""
        url = '/api/dashboard/stats/alertas/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('alertas_activas', response.data)
        self.assertIn('por_tipo', response.data)
        self.assertIn('por_severidad', response.data)

    def test_overview_endpoint(self):
        """Test endpoint de overview completo"""
        url = '/api/dashboard/overview/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('sistema', response.data)
        self.assertIn('negocio', response.data)
        self.assertIn('actividad_reciente', response.data)
        self.assertIn('etl_reciente', response.data)

    def test_system_stats_content(self):
        """Test que el contenido de system stats sea correcto"""
        url = '/api/dashboard/stats/system/'
        response = self.client.get(url)
        
        # Verificar estructura
        self.assertIn('usuarios', response.data)
        self.assertIn('alertas_activas', response.data)
        self.assertIn('cargas_totales', response.data)
        self.assertIn('tasa_exito', response.data)

    def test_business_stats_content(self):
        """Test que el contenido de business stats sea correcto"""
        url = '/api/dashboard/stats/business/'
        response = self.client.get(url)
        
        # Verificar estructura
        self.assertIn('polizas_totales', response.data)
        self.assertIn('polizas_vigentes', response.data)
        self.assertIn('prima_total_uf', response.data)
        self.assertIn('produccion_hoy', response.data)

    def test_permission_required(self):
        """Test que se requiera permisos de admin"""
        self.client.force_authenticate(user=None)
        url = '/api/dashboard/stats/system/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_limit_parameter(self):
        """Test parámetro limit en activity endpoint"""
        url = '/api/dashboard/stats/activity/?limit=10'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_etl_limit_parameter(self):
        """Test parámetro limit en ETL endpoint"""
        url = '/api/dashboard/stats/etl/?limit=5'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
