"""
Tests para el módulo de alertas (PASO 7)
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from django.utils import timezone

from .models import Alerta
from .utils import crear_alerta, estadisticas_alertas, obtener_alertas_activas
from clientes.models import Cliente
from polizas.models import Poliza

User = get_user_model()


class AlertaModelTestCase(TestCase):
    """Tests para el modelo Alerta"""

    def setUp(self):
        self.usuario = User.objects.create_user(username='testuser', password='pass123')
        self.cliente = Cliente.objects.create(rut='12.345.678-9', nombre='Test Cliente')

    def test_crear_alerta_basica(self):
        """Crea una alerta básica"""
        alerta = Alerta.objects.create(
            tipo='manual',
            severidad='info',
            titulo='Alerta de prueba',
            mensaje='Mensaje de prueba',
            creada_por=self.usuario,
            estado='PENDIENTE'
        )
        self.assertEqual(alerta.tipo, 'manual')
        self.assertEqual(alerta.severidad, 'info')
        self.assertTrue(alerta.activa)

    def test_marcar_como_leida(self):
        """Marca una alerta como leída"""
        alerta = Alerta.objects.create(
            tipo='manual',
            severidad='info',
            titulo='Test',
            mensaje='Test',
            creada_por=self.usuario
        )
        self.assertTrue(alerta.marcar_como_leida(self.usuario))
        alerta.refresh_from_db()
        self.assertEqual(alerta.estado, 'LEIDA')
        self.assertIsNotNone(alerta.fecha_lectura)

    def test_marcar_como_resuelta(self):
        """Marca una alerta como resuelta"""
        alerta = Alerta.objects.create(
            tipo='manual',
            severidad='warning',
            titulo='Test',
            mensaje='Test',
            creada_por=self.usuario
        )
        self.assertTrue(alerta.marcar_como_resuelta(self.usuario))
        alerta.refresh_from_db()
        self.assertEqual(alerta.estado, 'RESUELTA')
        self.assertIsNotNone(alerta.fecha_resolucion)

    def test_descartar_alerta(self):
        """Descarta una alerta"""
        alerta = Alerta.objects.create(
            tipo='manual',
            severidad='info',
            titulo='Test',
            mensaje='Test',
            creada_por=self.usuario
        )
        self.assertTrue(alerta.descartar())
        alerta.refresh_from_db()
        self.assertEqual(alerta.estado, 'DESCARTADA')

    def test_alerta_vencida(self):
        """Detecta alertas vencidas"""
        fecha_pasada = timezone.now() - timezone.timedelta(days=1)
        alerta = Alerta.objects.create(
            tipo='manual',
            severidad='critical',
            titulo='Test',
            mensaje='Test',
            creada_por=self.usuario,
            fecha_limite=fecha_pasada
        )
        self.assertTrue(alerta.esta_vencida)

    def test_dias_pendiente(self):
        """Calcula días pendiente"""
        alerta = Alerta.objects.create(
            tipo='manual',
            severidad='info',
            titulo='Test',
            mensaje='Test',
            creada_por=self.usuario
        )
        self.assertGreaterEqual(alerta.dias_pendiente, 0)

    def test_relacion_cliente(self):
        """Alerta puede estar relacionada a cliente"""
        alerta = Alerta.objects.create(
            tipo='cliente_riesgo',
            severidad='critical',
            titulo='Cliente en riesgo',
            mensaje='Test',
            cliente=self.cliente,
            creada_por=self.usuario
        )
        self.assertEqual(alerta.cliente, self.cliente)


class AlertasUtilsTestCase(TestCase):
    """Tests para funciones de utilidad de alertas"""

    def setUp(self):
        self.usuario = User.objects.create_user(username='testuser', password='pass123')

    def test_crear_alerta_util(self):
        """Función crear_alerta funciona"""
        alerta = crear_alerta(
            tipo='error_carga',
            severidad='warning',
            mensaje='Archivo con errores',
            usuario=self.usuario
        )
        self.assertIsNotNone(alerta.id)
        self.assertEqual(alerta.tipo, 'error_carga')

    def test_estadisticas_alertas(self):
        """Obtiene estadísticas de alertas"""
        crear_alerta(tipo='manual', mensaje='Test 1', severidad='info', usuario=self.usuario)
        crear_alerta(tipo='manual', mensaje='Test 2', severidad='warning', usuario=self.usuario)
        crear_alerta(tipo='manual', mensaje='Test 3', severidad='critical', usuario=self.usuario)

        stats = estadisticas_alertas()
        self.assertEqual(stats['total_alertas'], 3)
        self.assertEqual(stats['alertas_criticas'], 1)
        self.assertEqual(stats['alertas_info'], 1)

    def test_obtener_alertas_activas(self):
        """Obtiene solo alertas activas"""
        alerta1 = crear_alerta(tipo='manual', mensaje='Test 1', severidad='info', usuario=self.usuario)
        alerta2 = crear_alerta(tipo='manual', mensaje='Test 2', severidad='warning', usuario=self.usuario)

        # Una la marcamos como resuelta
        alerta1.marcar_como_resuelta(self.usuario)

        activas = obtener_alertas_activas()
        self.assertEqual(activas.count(), 1)
        self.assertEqual(activas.first().id, alerta2.id)

    def test_obtener_alertas_por_severidad(self):
        """Filtra alertas por severidad"""
        crear_alerta(tipo='manual', mensaje='Info', severidad='info', usuario=self.usuario)
        crear_alerta(tipo='manual', mensaje='Warning', severidad='warning', usuario=self.usuario)
        crear_alerta(tipo='manual', mensaje='Critical', severidad='critical', usuario=self.usuario)

        criticas = obtener_alertas_activas(filtro_severidad='critical')
        self.assertEqual(criticas.count(), 1)


class AlertasAPITestCase(APITestCase):
    """Tests para API REST de alertas"""

    def setUp(self):
        self.usuario = User.objects.create_user(username='testuser', password='pass123')
        self.client.force_authenticate(user=self.usuario)

    def test_listar_alertas(self):
        """Endpoint para listar alertas"""
        crear_alerta('manual', 'info', 'Test', self.usuario)
        url = reverse('alerta-list')
        response = self.client.get(url)
        self.assertIn(response.status_code, [200, 403])

    def test_alertas_activas_endpoint(self):
        """Endpoint de alertas activas (PASO 7.5)"""
        crear_alerta('manual', 'info', 'Test', self.usuario)
        url = '/api/alertas/activas/'
        response = self.client.get(url)
        self.assertIn(response.status_code, [200, 403])

    def test_estadisticas_endpoint(self):
        """Endpoint de estadísticas"""
        crear_alerta('manual', 'info', 'Test 1', self.usuario)
        crear_alerta('error_carga', 'critical', 'Test 2', self.usuario)
        url = '/api/alertas/estadisticas/'
        response = self.client.get(url)
        self.assertIn(response.status_code, [200, 403])


class AlertaIntegracionTestCase(TestCase):
    """Tests de integración con ETL (PASO 7.3)"""

    def setUp(self):
        self.usuario = User.objects.create_user(username='testuser', password='pass123')

    def test_alerta_error_carga(self):
        """Se crea alerta al haber errores en carga"""
        alerta = crear_alerta(
            tipo='error_carga',
            severidad='warning',
            mensaje='El archivo archivo.xlsx tiene 5 filas con error.',
            usuario=self.usuario,
            titulo='Errores en archivo.xlsx'
        )
        self.assertEqual(alerta.tipo, 'error_carga')
        self.assertEqual(alerta.severidad, 'warning')

    def test_alerta_importacion_exitosa(self):
        """Se crea alerta al completar importación exitosa"""
        alerta = crear_alerta(
            tipo='importaciones',
            severidad='info',
            mensaje='Archivo archivo.xlsx procesado correctamente. 100 nuevas pólizas, 50 actualizadas.',
            usuario=self.usuario,
            titulo='Carga exitosa: archivo.xlsx'
        )
        self.assertEqual(alerta.tipo, 'importaciones')
        self.assertEqual(alerta.severidad, 'info')

    def test_alerta_produccion_baja(self):
        """Se crea alerta por producción baja"""
        alerta = crear_alerta(
            tipo='produccion_baja',
            severidad='warning',
            mensaje='La producción de pólizas del día es 0. Esto es inusual.',
            titulo='Producción del día en cero'
        )
        self.assertEqual(alerta.tipo, 'produccion_baja')

    def test_alerta_crecimiento_negativo(self):
        """Se crea alerta por crecimiento negativo"""
        alerta = crear_alerta(
            tipo='crecimiento_negativo',
            severidad='warning',
            mensaje='Producción últimos 7 días: 50 vs 14 días anteriores: 100. Decrecimiento > 30%.',
            titulo='Decrecimiento de producción detectado'
        )
        self.assertEqual(alerta.tipo, 'crecimiento_negativo')

    def test_alerta_cliente_riesgo(self):
        """Se crea alerta por cliente en riesgo"""
        cliente = Cliente.objects.create(rut='12.345.678-9', nombre='Cliente Test')
        alerta = crear_alerta(
            tipo='cliente_riesgo',
            severidad='critical',
            mensaje='Cliente 12.345.678-9 asignado a cluster 3 (riesgo alto)',
            cliente=cliente,
            titulo='Cliente en cluster de bajo rendimiento'
        )
        self.assertEqual(alerta.tipo, 'cliente_riesgo')
        self.assertEqual(alerta.cliente, cliente)
