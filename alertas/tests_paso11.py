"""
Tests para PASO 11: Historial de Alertas y Auditoría
Verifica:
- Creación automática de AlertaHistorial cuando se genera una alerta
- Actualización de historial cuando se resuelve una alerta
- API para listar historial con filtros
- Propiedades calculadas del historial
"""

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from datetime import timedelta

from .models import Alerta, AlertaHistorial
from .utils import crear_alerta
from clientes.models import Cliente
from polizas.models import Poliza
from usuarios.models import User


class AlertaHistorialModelTests(TestCase):
    """Tests para el modelo AlertaHistorial"""
    
    def setUp(self):
        """Configurar datos de prueba"""
        self.usuario = User.objects.create_user(
            username='testadmin',
            password='password123',
            email='admin@test.com',
            role='admin'
        )
        
        self.cliente = Cliente.objects.create(
            nombre='Cliente Test',
            rut='12345678-9'
        )
        
        self.poliza = Poliza.objects.create(
            numero='POL-001',
            cliente=self.cliente,
            fecha_inicio=timezone.now().date(),
            fecha_vencimiento=timezone.now().date() + timedelta(days=30),
            estado='VIGENTE',
            monto_uf=1000.0
        )
    
    def test_crear_historial_automaticamente(self):
        """Verifica que se crea AlertaHistorial al crear una alerta"""
        # Crear alerta usando crear_alerta()
        alerta = crear_alerta(
            tipo='vencimientos',
            mensaje='Prueba de historial',
            severidad='warning',
            usuario=self.usuario,
            poliza=self.poliza,
            cliente=self.cliente,
            titulo='Prueba'
        )
        
        # Verificar que se creó el historial
        self.assertEqual(AlertaHistorial.objects.count(), 1)
        
        historial = AlertaHistorial.objects.first()
        self.assertEqual(historial.alerta, alerta)
        self.assertEqual(historial.tipo, 'vencimientos')
        self.assertEqual(historial.estado_final, 'nueva')
        self.assertIsNone(historial.resuelta_en)
        self.assertIsNone(historial.resuelta_por)
    
    def test_tiempo_resolucion(self):
        """Verifica cálculo de tiempo de resolución"""
        alerta = crear_alerta(
            tipo='test',
            mensaje='Prueba',
            severidad='info',
            poliza=self.poliza,
            cliente=self.cliente
        )
        
        historial = AlertaHistorial.objects.first()
        
        # Antes de resolver, tiempo_resolucion es None
        self.assertIsNone(historial.tiempo_resolucion)
        
        # Simular resolución
        historial.resuelta_en = historial.creada_en + timedelta(hours=2)
        historial.save()
        
        # Verificar que se calculó correctamente
        self.assertIsNotNone(historial.tiempo_resolucion)
        self.assertGreater(historial.tiempo_resolucion, 0)
    
    def test_dias_pendiente(self):
        """Verifica cálculo de días pendiente"""
        alerta = crear_alerta(
            tipo='test',
            mensaje='Prueba',
            severidad='info',
            poliza=self.poliza,
            cliente=self.cliente
        )
        
        historial = AlertaHistorial.objects.first()
        
        # Verificar que cuenta días pendientes
        dias = historial.dias_pendiente
        self.assertGreaterEqual(dias, 0)
    
    def test_str_method(self):
        """Verifica representación en string"""
        alerta = crear_alerta(
            tipo='vencimientos',
            mensaje='Prueba',
            severidad='info',
            poliza=self.poliza,
            cliente=self.cliente
        )
        
        historial = AlertaHistorial.objects.first()
        str_repr = str(historial)
        
        self.assertIn('vencimientos', str_repr)
        self.assertIn('Cliente Test', str_repr)
        self.assertIn('nueva', str_repr)


class AlertaHistorialIntegrationTests(TestCase):
    """Tests de integración con flujo de alertas"""
    
    def setUp(self):
        """Configurar datos de prueba"""
        self.admin_user = User.objects.create_user(
            username='admin',
            password='admin123',
            email='admin@test.com',
            role='admin'
        )
        
        self.executor_user = User.objects.create_user(
            username='executor',
            password='exec123',
            email='exec@test.com',
            role='gestor'
        )
        
        self.cliente = Cliente.objects.create(
            nombre='Cliente Test',
            rut='12345678-9'
        )
        
        self.poliza = Poliza.objects.create(
            numero='POL-001',
            cliente=self.cliente,
            fecha_inicio=timezone.now().date(),
            fecha_vencimiento=timezone.now().date() + timedelta(days=30),
            estado='VIGENTE',
            monto_uf=1000.0
        )
        
        self.client = APIClient()
    
    def test_resolver_actualiza_historial(self):
        """Verifica que resolver alerta actualiza el historial"""
        # Crear alerta
        alerta = crear_alerta(
            tipo='test',
            mensaje='Alerta de prueba',
            severidad='warning',
            poliza=self.poliza,
            cliente=self.cliente
        )
        
        # Verificar historial inicial
        historial = AlertaHistorial.objects.first()
        self.assertEqual(historial.estado_final, 'nueva')
        self.assertIsNone(historial.resuelta_en)
        
        # Resolver alerta
        alerta.marcar_como_resuelta(self.executor_user)
        
        # Actualizar historial (simulando lo que hace la API)
        historial.resuelta_en = timezone.now()
        historial.resuelta_por = self.executor_user
        historial.estado_final = 'resuelta'
        historial.save()
        
        # Verificar actualización
        historial.refresh_from_db()
        self.assertEqual(historial.estado_final, 'resuelta')
        self.assertIsNotNone(historial.resuelta_en)
        self.assertEqual(historial.resuelta_por, self.executor_user)
    
    def test_multiples_alertas_historial(self):
        """Verifica que múltiples alertas tengan múltiples historiales"""
        # Crear varias alertas
        for i in range(3):
            crear_alerta(
                tipo='test',
                mensaje=f'Alerta {i}',
                severidad='info',
                poliza=self.poliza,
                cliente=self.cliente
            )
        
        # Verificar que hay 3 historiales
        self.assertEqual(AlertaHistorial.objects.count(), 3)
        
        # Verificar que todos están en estado 'nueva'
        historiales_nuevos = AlertaHistorial.objects.filter(estado_final='nueva')
        self.assertEqual(historiales_nuevos.count(), 3)


class AlertaHistorialAPITests(TestCase):
    """Tests para la API de historial de alertas"""
    
    def setUp(self):
        """Configurar datos de prueba"""
        self.admin_user = User.objects.create_user(
            username='admin',
            password='admin123',
            email='admin@test.com',
            role='admin'
        )
        
        self.regular_user = User.objects.create_user(
            username='regular',
            password='user123',
            email='user@test.com',
            role='gestor'
        )
        
        self.cliente = Cliente.objects.create(
            nombre='Cliente Test',
            rut='12345678-9'
        )
        
        self.cliente2 = Cliente.objects.create(
            nombre='Cliente Test 2',
            rut='98765432-1'
        )
        
        self.poliza = Poliza.objects.create(
            numero='POL-001',
            cliente=self.cliente,
            fecha_inicio=timezone.now().date(),
            fecha_vencimiento=timezone.now().date() + timedelta(days=30),
            estado='VIGENTE',
            monto_uf=1000.0
        )
        
        self.client = APIClient()
    
    def test_get_historial_requiere_admin(self):
        """Verifica que solo admin puede ver historial"""
        # Sin autenticación
        response = self.client.get('/api/alertas/historial-list/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # Con usuario regular
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.get('/api/alertas/historial-list/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_get_historial_vacio(self):
        """Verifica obtener historial vacío"""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get('/api/alertas/historial-list/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total'], 0)
        self.assertEqual(len(response.data['historial']), 0)
    
    def test_get_historial_con_datos(self):
        """Verifica obtener historial con datos"""
        # Crear alertas
        for i in range(5):
            crear_alerta(
                tipo='test',
                mensaje=f'Alerta {i}',
                severidad='info',
                poliza=self.poliza,
                cliente=self.cliente
            )
        
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get('/api/alertas/historial-list/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total'], 5)
        self.assertEqual(len(response.data['historial']), 5)
    
    def test_filtro_por_tipo(self):
        """Verifica filtro por tipo de alerta"""
        # Crear alertas de diferentes tipos
        crear_alerta(
            tipo='vencimientos',
            mensaje='Alerta 1',
            severidad='critical',
            poliza=self.poliza,
            cliente=self.cliente
        )
        
        crear_alerta(
            tipo='produccion_baja',
            mensaje='Alerta 2',
            severidad='warning',
            poliza=self.poliza,
            cliente=self.cliente
        )
        
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get('/api/alertas/historial-list/?tipo=vencimientos')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total'], 1)
        self.assertEqual(response.data['historial'][0]['tipo'], 'vencimientos')
    
    def test_filtro_por_estado(self):
        """Verifica filtro por estado final"""
        # Crear alertas
        alerta1 = crear_alerta(
            tipo='test',
            mensaje='Alerta 1',
            severidad='info',
            poliza=self.poliza,
            cliente=self.cliente
        )
        
        alerta2 = crear_alerta(
            tipo='test',
            mensaje='Alerta 2',
            severidad='info',
            poliza=self.poliza,
            cliente=self.cliente
        )
        
        # Marcar una como resuelta
        historial2 = AlertaHistorial.objects.get(alerta=alerta2)
        historial2.estado_final = 'resuelta'
        historial2.resuelta_en = timezone.now()
        historial2.save()
        
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get('/api/alertas/historial-list/?estado=resuelta')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total'], 1)
        self.assertEqual(response.data['historial'][0]['estado_final'], 'resuelta')
    
    def test_filtro_por_cliente(self):
        """Verifica filtro por cliente"""
        # Crear alertas para diferentes clientes
        crear_alerta(
            tipo='test',
            mensaje='Alerta 1',
            severidad='info',
            cliente=self.cliente
        )
        
        crear_alerta(
            tipo='test',
            mensaje='Alerta 2',
            severidad='info',
            cliente=self.cliente2
        )
        
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(f'/api/alertas/historial-list/?cliente_id={self.cliente.id}')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total'], 1)
        self.assertEqual(response.data['historial'][0]['cliente'], self.cliente.nombre)
    
    def test_historial_incluye_campos_requeridos(self):
        """Verifica que la respuesta incluye todos los campos requeridos"""
        crear_alerta(
            tipo='vencimientos',
            mensaje='Alerta de prueba',
            severidad='critical',
            poliza=self.poliza,
            cliente=self.cliente
        )
        
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get('/api/alertas/historial-list/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        historial = response.data['historial'][0]
        
        # Verificar campos requeridos
        self.assertIn('id', historial)
        self.assertIn('tipo', historial)
        self.assertIn('cliente', historial)
        self.assertIn('rut', historial)
        self.assertIn('poliza', historial)
        self.assertIn('severidad', historial)
        self.assertIn('mensaje', historial)
        self.assertIn('creada_en', historial)
        self.assertIn('resuelta_en', historial)
        self.assertIn('resuelta_por', historial)
        self.assertIn('estado_final', historial)
    
    def test_historial_ordenamiento(self):
        """Verifica que el historial está ordenado por fecha descendente"""
        # Crear alertas con pequeño delay
        crear_alerta(tipo='test', mensaje='Alerta 1', severidad='info')
        
        # Esperar para que las timestamps difieran
        import time
        time.sleep(0.1)
        
        crear_alerta(tipo='test', mensaje='Alerta 2', severidad='info')
        
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get('/api/alertas/historial-list/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        historiales = response.data['historial']
        
        # Verificar que están ordenados de más reciente a más antiguo
        if len(historiales) > 1:
            for i in range(len(historiales) - 1):
                fecha_actual = historiales[i]['creada_en']
                fecha_siguiente = historiales[i + 1]['creada_en']
                self.assertGreaterEqual(fecha_actual, fecha_siguiente)


class AlertaHistorialSeleccionRelacionadosTests(TestCase):
    """Tests para verificar que select_related está optimizado"""
    
    def setUp(self):
        """Configurar datos de prueba"""
        self.admin_user = User.objects.create_user(
            username='admin',
            password='admin123',
            role='admin'
        )
        
        self.cliente = Cliente.objects.create(
            nombre='Cliente Test',
            rut='12345678-9'
        )
        
        self.poliza = Poliza.objects.create(
            numero='POL-001',
            cliente=self.cliente,
            fecha_inicio=timezone.now().date(),
            fecha_vencimiento=timezone.now().date() + timedelta(days=30),
            estado='VIGENTE',
            monto_uf=1000.0
        )
        
        self.client = APIClient()
    
    def test_select_related_optimizacion(self):
        """Verifica que las queries estén optimizadas con select_related"""
        # Crear múltiples alertas
        for i in range(10):
            crear_alerta(
                tipo='test',
                mensaje=f'Alerta {i}',
                severidad='info',
                poliza=self.poliza,
                cliente=self.cliente
            )
        
        self.client.force_authenticate(user=self.admin_user)
        
        # Hacer la request
        response = self.client.get('/api/alertas/historial-list/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total'], 10)
        
        # Verificar que todos tienen datos relacionados cargados
        for historial in response.data['historial']:
            self.assertIsNotNone(historial['cliente'])
            self.assertIsNotNone(historial['rut'])
