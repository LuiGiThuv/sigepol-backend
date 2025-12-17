"""
PASO 14: Pruebas del Módulo de Alertas Predictivas (ML Integration)
Tests para verificar la integración de modelos de ML con el sistema de alertas.
"""

import json
import io
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.contrib.auth.models import Permission, Group
from usuarios.models import User
from clientes.models import Cliente
from alertas.models import Alerta
from auditorias.models import AuditoriaAccion


class MLImportResultsViewTests(APITestCase):
    """Tests para MLImportResultsView - Importación de resultados ML"""
    
    def setUp(self):
        """Configuración inicial para cada test"""
        # Crear usuario admin
        self.admin_user = User.objects.create_user(
            username='admin',
            password='admin123'
        )
        self.admin_user.role = 'admin'
        self.admin_user.is_staff = True
        self.admin_user.is_superuser = True
        self.admin_user.save()
        
        # Crear usuario no-admin
        self.regular_user = User.objects.create_user(
            username='user',
            password='user123'
        )
        self.regular_user.role = 'ejecutivo'
        self.regular_user.save()
        
        # Crear clientes de prueba
        self.cliente1 = Cliente.objects.create(
            rut='16543287-4',
            nombre='JUAN PÉREZ'
        )
        
        self.cliente2 = Cliente.objects.create(
            rut='12345678-9',
            nombre='MARÍA GARCÍA'
        )
        
        self.cliente3 = Cliente.objects.create(
            rut='87654321-1',
            nombre='CARLOS LÓPEZ'
        )
        
        self.client = APIClient()
    
    def create_csv_file(self, csv_data):
        """Crea un archivo CSV para pruebas"""
        csv_buffer = io.StringIO()
        csv_buffer.write(csv_data)
        csv_buffer.seek(0)
        
        csv_file = io.BytesIO(csv_buffer.getvalue().encode())
        csv_file.name = 'ml_results.csv'
        return csv_file
    
    def test_import_requires_authentication(self):
        """Test: Debe requerir autenticación"""
        csv_data = "cliente_rut,cliente_nombre,cluster,prima_total,variacion_mensual,anomalia\n"
        
        response = self.client.post(
            '/api/alertas/ml/import/',
            {'file': self.create_csv_file(csv_data)},
            format='multipart'
        )
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_import_requires_admin_permission(self):
        """Test: Solo admins pueden importar resultados ML"""
        self.client.force_authenticate(user=self.regular_user)
        
        csv_data = "cliente_rut,cliente_nombre,cluster,prima_total,variacion_mensual,anomalia\n"
        
        response = self.client.post(
            '/api/alertas/ml/import/',
            {'file': self.create_csv_file(csv_data)},
            format='multipart'
        )
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_import_cluster_0_creates_riesgo_produccion_alert(self):
        """Test: Cluster 0 debe crear alerta ML_RIESGO_PRODUCCION"""
        self.client.force_authenticate(user=self.admin_user)
        
        csv_data = """cliente_rut,cliente_nombre,cluster,prima_total,variacion_mensual,anomalia
16543287-4,JUAN PÉREZ,0,55.2,-32.1,false"""
        
        response = self.client.post(
            '/api/alertas/ml/import/',
            {'file': self.create_csv_file(csv_data)},
            format='multipart'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verificar que se creó la alerta
        alerta = Alerta.objects.filter(
            tipo='ML_RIESGO_PRODUCCION',
            cliente=self.cliente1
        ).first()
        
        self.assertIsNotNone(alerta)
        self.assertEqual(alerta.severidad, 'CRITICO')
    
    def test_import_negative_variation_creates_variacion_alert(self):
        """Test: Variación < -20% debe crear alerta ML_VARIACION_NEGATIVA"""
        self.client.force_authenticate(user=self.admin_user)
        
        csv_data = """cliente_rut,cliente_nombre,cluster,prima_total,variacion_mensual,anomalia
12345678-9,MARÍA GARCÍA,1,100.0,-25.5,false"""
        
        response = self.client.post(
            '/api/alertas/ml/import/',
            {'file': self.create_csv_file(csv_data)},
            format='multipart'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verificar que se creó la alerta
        alerta = Alerta.objects.filter(
            tipo='ML_VARIACION_NEGATIVA',
            cliente=self.cliente2
        ).first()
        
        self.assertIsNotNone(alerta)
        self.assertEqual(alerta.severidad, 'ADVERTENCIA')
    
    def test_import_anomalia_creates_anomalia_alert(self):
        """Test: Anomalia=true debe crear alerta ML_ANOMALIA"""
        self.client.force_authenticate(user=self.admin_user)
        
        csv_data = """cliente_rut,cliente_nombre,cluster,prima_total,variacion_mensual,anomalia
87654321-1,CARLOS LÓPEZ,2,200.0,-5.0,true"""
        
        response = self.client.post(
            '/api/alertas/ml/import/',
            {'file': self.create_csv_file(csv_data)},
            format='multipart'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verificar que se creó la alerta
        alerta = Alerta.objects.filter(
            tipo='ML_ANOMALIA',
            cliente=self.cliente3
        ).first()
        
        self.assertIsNotNone(alerta)
        self.assertEqual(alerta.severidad, 'CRITICO')
    
    def test_import_stores_metadata(self):
        """Test: Debe almacenar metadata del ML en la alerta"""
        self.client.force_authenticate(user=self.admin_user)
        
        csv_data = """cliente_rut,cliente_nombre,cluster,prima_total,variacion_mensual,anomalia
16543287-4,JUAN PÉREZ,0,55.2,-32.1,false"""
        
        response = self.client.post(
            '/api/alertas/ml/import/',
            {'file': self.create_csv_file(csv_data)},
            format='multipart'
        )
        
        alerta = Alerta.objects.filter(cliente=self.cliente1).first()
        
        # Verificar que metadata contiene datos ML
        self.assertIsNotNone(alerta)
        if alerta.metadata:
            self.assertIn('cluster', alerta.metadata)


class MLAlertsListViewTests(APITestCase):
    """Tests para MLAlertsListView - Listado de alertas ML"""
    
    def setUp(self):
        """Configuración inicial"""
        self.admin_user = User.objects.create_user(
            username='admin',
            password='admin123'
        )
        self.admin_user.is_staff = True
        self.admin_user.is_superuser = True
        self.admin_user.save()
        
        self.cliente = Cliente.objects.create(
            rut='16543287-4',
            nombre='JUAN PÉREZ'
        )
        
        # Crear alertas ML de prueba
        self.alerta_riesgo = Alerta.objects.create(
            tipo='ML_RIESGO_PRODUCCION',
            cliente=self.cliente,
            severidad='CRITICO',
            estado='PENDIENTE',
            metadata={'cluster': 0, 'prima_total': 55.2}
        )
        
        self.alerta_variacion = Alerta.objects.create(
            tipo='ML_VARIACION_NEGATIVA',
            cliente=self.cliente,
            severidad='ADVERTENCIA',
            estado='PENDIENTE',
            metadata={'variacion_mensual': -25.5}
        )
        
        self.alerta_anomalia = Alerta.objects.create(
            tipo='ML_ANOMALIA',
            cliente=self.cliente,
            severidad='CRITICO',
            estado='RESUELTA',
            metadata={'anomalia': True}
        )
        
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin_user)
    
    def test_list_all_ml_alerts(self):
        """Test: Debe listar todas las alertas ML"""
        response = self.client.get('/api/alertas/ml/alertas/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data['results']), 3)
    
    def test_filter_by_type(self):
        """Test: Debe filtrar alertas por tipo"""
        response = self.client.get('/api/alertas/ml/alertas/?tipo=ML_RIESGO_PRODUCCION')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for alerta in response.data['results']:
            self.assertEqual(alerta['tipo'], 'ML: Riesgo de Producción Baja')


class MLAlertsStatsViewTests(APITestCase):
    """Tests para MLAlertsStatsView - Estadísticas de alertas ML"""
    
    def setUp(self):
        """Configuración inicial"""
        self.admin_user = User.objects.create_user(
            username='admin',
            password='admin123'
        )
        self.admin_user.is_staff = True
        self.admin_user.is_superuser = True
        self.admin_user.save()
        
        self.cliente = Cliente.objects.create(
            rut='16543287-4',
            nombre='JUAN PÉREZ'
        )
        
        # Crear alertas variadas para estadísticas
        for i in range(3):
            Alerta.objects.create(
                tipo='ML_RIESGO_PRODUCCION',
                cliente=self.cliente,
                severidad='CRITICO',
                estado='PENDIENTE'
            )
        
        for i in range(2):
            Alerta.objects.create(
                tipo='ML_VARIACION_NEGATIVA',
                cliente=self.cliente,
                severidad='ADVERTENCIA',
                estado='LEIDA'
            )
        
        Alerta.objects.create(
            tipo='ML_ANOMALIA',
            cliente=self.cliente,
            severidad='CRITICO',
            estado='RESUELTA'
        )
        
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin_user)
    
    def test_stats_returns_total_count(self):
        """Test: Debe retornar conteo total de alertas"""
        response = self.client.get('/api/alertas/ml/stats/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total', response.data)
        self.assertGreaterEqual(response.data['total'], 6)
    
    def test_stats_breakdown_by_type(self):
        """Test: Debe retornar desglose por tipo de alerta"""
        response = self.client.get('/api/alertas/ml/stats/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('por_tipo', response.data)
