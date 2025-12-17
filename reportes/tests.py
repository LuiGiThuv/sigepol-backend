"""
Tests para el módulo de Reportes Automáticos Inteligentes (PASO 9)
Prueba las 4 vistas de API y sus funciones de negocio
"""

from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient
from rest_framework import status

from usuarios.models import User
from clientes.models import Cliente
from polizas.models import Poliza


class ReportesServicesTestCase(TestCase):
    """Test suite para las funciones de servicio de reportes"""
    
    def setUp(self):
        """Configurar datos de prueba"""
        # Crear clientes
        self.cliente1 = Cliente.objects.create(
            nombre='Cliente Service Test',
            rut='11111111-1'
        )
        
        hoy = timezone.now().date()
        
        # Crear pólizas con diferentes fechas
        Poliza.objects.create(
            numero='SRV-001',
            cliente=self.cliente1,
            fecha_inicio=hoy - timedelta(days=30),
            fecha_vencimiento=hoy - timedelta(days=15),
            estado='VIGENTE',
            monto_uf=100.0
        )
    
    def test_servicios_importados(self):
        """Test que los servicios pueden importarse sin errores"""
        try:
            from reportes.services import (
                reporte_polizas_vencidas,
                reporte_polizas_por_expirar,
                reporte_produccion_mensual,
                reporte_top_clientes
            )
            self.assertTrue(True)
        except ImportError as e:
            self.fail(f"Error importando servicios: {e}")
    
    def test_servicio_polizas_vencidas_estructura(self):
        """Test que la estructura de datos de servicios es correcta"""
        from reportes.services import reporte_polizas_vencidas
        
        resultado = reporte_polizas_vencidas()
        
        self.assertIsInstance(resultado, dict)
        self.assertIn('total', resultado)
        self.assertIn('polizas', resultado)
        self.assertIn('generado', resultado)
        self.assertIsInstance(resultado['total'], int)
        self.assertIsInstance(resultado['polizas'], list)
    
    def test_servicio_produccion_mensual_estructura(self):
        """Test que la estructura de producción mensual es correcta"""
        from reportes.services import reporte_produccion_mensual
        
        resultado = reporte_produccion_mensual()
        
        self.assertIsInstance(resultado, dict)
        self.assertIn('mes', resultado)
        self.assertIn('produccion_actual', resultado)
        self.assertIn('variacion', resultado)
        self.assertIn('cartera', resultado)
        self.assertIn('generado', resultado)
    
    def test_servicio_top_clientes_estructura(self):
        """Test que la estructura de top clientes es correcta"""
        from reportes.services import reporte_top_clientes
        
        resultado = reporte_top_clientes()
        
        self.assertIsInstance(resultado, dict)
        self.assertIn('mes', resultado)
        self.assertIn('total_ranking', resultado)
        self.assertIn('total_prima_mes', resultado)
        self.assertIn('clientes', resultado)
        self.assertIn('generado', resultado)
        self.assertIsInstance(resultado['clientes'], list)


class ReportesPermissionsTestCase(TestCase):
    """Test suite para verificar permisos de acceso"""
    
    def setUp(self):
        """Configurar datos de prueba"""
        self.client = APIClient()
        
        # Crear usuario admin
        self.admin_user = User.objects.create_user(
            username='admin_test',
            email='admin@test.com',
            password='testpass123',
            role='admin'
        )
        
        # Crear usuario normal
        self.normal_user = User.objects.create_user(
            username='normal_user',
            email='user@test.com',
            password='testpass123',
            role='ejecutivo'
        )
        
        # Crear datos de prueba
        hoy = timezone.now().date()
        self.cliente = Cliente.objects.create(
            nombre='Test Client',
            rut='11111111-1'
        )
        
        Poliza.objects.create(
            numero='TEST-001',
            cliente=self.cliente,
            fecha_inicio=hoy - timedelta(days=30),
            fecha_vencimiento=hoy - timedelta(days=5),
            estado='VIGENTE',
            monto_uf=100.0
        )
        
        # Obtener tokens JWT
        from rest_framework_simplejwt.tokens import RefreshToken
        
        refresh = RefreshToken.for_user(self.admin_user)
        self.admin_token = str(refresh.access_token)
        
        refresh = RefreshToken.for_user(self.normal_user)
        self.normal_token = str(refresh.access_token)
    
    def test_polizas_vencidas_sin_autenticacion(self):
        """Test que sin token no se permite acceso"""
        response = self.client.get('/api/reportes/polizas-vencidas/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_polizas_vencidas_usuario_normal(self):
        """Test que usuario normal no puede acceder"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.normal_token}')
        response = self.client.get('/api/reportes/polizas-vencidas/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_polizas_vencidas_admin(self):
        """Test que admin puede acceder"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        response = self.client.get('/api/reportes/polizas-vencidas/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertIn('total', data)
        self.assertIn('polizas', data)
        self.assertIn('generado', data)
    
    def test_polizas_por_expirar_admin(self):
        """Test endpoint de polizas por expirar"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        response = self.client.get('/api/reportes/polizas-por-expirar/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertIn('total', data)
        self.assertIn('polizas', data)
    
    def test_produccion_mensual_admin(self):
        """Test endpoint de producción mensual"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        response = self.client.get('/api/reportes/produccion-mensual/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertIn('mes', data)
        self.assertIn('produccion_actual', data)
        self.assertIn('variacion', data)
    
    def test_top_clientes_admin(self):
        """Test endpoint de top clientes"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        response = self.client.get('/api/reportes/top-clientes/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertIn('mes', data)
        self.assertIn('total_ranking', data)
        self.assertIn('clientes', data)

