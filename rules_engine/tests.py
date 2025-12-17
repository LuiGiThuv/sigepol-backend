import json
from datetime import timedelta
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from polizas.models import Poliza
from clientes.models import Cliente
from alertas.models import Alerta
from .models import Rule, RuleExecution
from .registry import register_rule, get_registered_rules
from .executor import (
    ejecutar_motor_reglas,
    ejecutar_regla_individual,
    rule_polizas_por_expirar,
    rule_clientes_top_produccion,
    rule_produccion_baja_detectada,
    rule_vigencia_irregular_detectada,
    rule_sanidad_datos
)

User = get_user_model()


class RuleModelTests(TestCase):
    """Tests para el modelo Rule"""
    
    def setUp(self):
        self.rule = Rule.objects.create(
            nombre='Regla Test',
            codigo='REGLA_TEST',
            descripcion='Regla de prueba',
            tipo='alerta',
            activa=True,
            parametros={'test': 'value'}
        )
    
    def test_crear_regla(self):
        """Test crear una regla"""
        self.assertEqual(Rule.objects.count(), 1)
        self.assertEqual(self.rule.codigo, 'REGLA_TEST')
        self.assertTrue(self.rule.activa)
    
    def test_regla_campos_requeridos(self):
        """Test que campos requeridos no sean vacíos"""
        self.assertIsNotNone(self.rule.nombre)
        self.assertIsNotNone(self.rule.codigo)
        self.assertIsNotNone(self.rule.parametros)
    
    def test_tasa_exito_sin_ejecuciones(self):
        """Test tasa de éxito cuando no hay ejecuciones"""
        self.assertEqual(self.rule.tasa_exito, 0)
    
    def test_tasa_exito_con_ejecuciones(self):
        """Test cálculo de tasa de éxito"""
        self.rule.total_ejecuciones = 10
        self.rule.ejecuciones_exitosas = 9
        self.rule.ejecuciones_fallidas = 1
        self.rule.save()
        
        self.assertEqual(self.rule.tasa_exito, 90.0)
    
    def test_habilitada_alias(self):
        """Test que habilitada sea alias de activa"""
        self.assertEqual(self.rule.habilitada, self.rule.activa)
        self.assertTrue(self.rule.habilitada)
    
    def test_codigo_unico(self):
        """Test que código sea único"""
        with self.assertRaises(Exception):
            Rule.objects.create(
                nombre='Otra Regla',
                codigo='REGLA_TEST',  # Código duplicado
                descripcion='Otra de prueba',
                tipo='alerta'
            )
    
    def test_actualizar_regla(self):
        """Test actualizar una regla"""
        self.rule.nombre = 'Nombre Actualizado'
        self.rule.activa = False
        self.rule.save()
        
        regla_actualizada = Rule.objects.get(codigo='REGLA_TEST')
        self.assertEqual(regla_actualizada.nombre, 'Nombre Actualizado')
        self.assertFalse(regla_actualizada.activa)


class RuleExecutionModelTests(TestCase):
    """Tests para el modelo RuleExecution"""
    
    def setUp(self):
        self.rule = Rule.objects.create(
            nombre='Regla Test',
            codigo='REGLA_TEST',
            tipo='alerta'
        )
    
    def test_crear_ejecucion(self):
        """Test crear ejecución de regla"""
        ejecucion = RuleExecution.objects.create(
            regla=self.rule,
            estado='exitosa',
            resultado={'datos': 'test'},
            duracion_segundos=1.5
        )
        
        self.assertEqual(ejecucion.regla, self.rule)
        self.assertEqual(ejecucion.estado, 'exitosa')
        self.assertTrue(ejecucion.exitosa)
    
    def test_ejecucion_fallida(self):
        """Test ejecución fallida"""
        ejecucion = RuleExecution.objects.create(
            regla=self.rule,
            estado='error',
            error_mensaje='Test error',
            duracion_segundos=2.0
        )
        
        self.assertEqual(ejecucion.estado, 'error')
        self.assertFalse(ejecucion.exitosa)
        self.assertEqual(ejecucion.error_mensaje, 'Test error')
    
    def test_tiempo_ejecucion_formateado(self):
        """Test formato de tiempo de ejecución"""
        ejecucion = RuleExecution.objects.create(
            regla=self.rule,
            estado='exitosa',
            duracion_segundos=65.5
        )
        
        self.assertIn('m', ejecucion.tiempo_ejecucion)  # Debe incluir minutos
    
    def test_parametros_utilizados_snapshot(self):
        """Test que guarda snapshot de parámetros"""
        self.rule.parametros = {'dias': 30, 'severidad': 'alta'}
        self.rule.save()
        
        ejecucion = RuleExecution.objects.create(
            regla=self.rule,
            estado='exitosa',
            parametros_utilizados=self.rule.parametros
        )
        
        self.assertEqual(ejecucion.parametros_utilizados['dias'], 30)


class RegistryTests(TestCase):
    """Tests para el sistema de registro de reglas"""
    
    def test_registrar_regla(self):
        """Test registrar una regla con decorador"""
        @register_rule("TEST_RULE")
        def test_rule(rule_obj):
            return {"test": "result"}
        
        self.assertIn("TEST_RULE", get_registered_rules())
    
    def test_obtener_regla_registrada(self):
        """Test obtener función de regla registrada"""
        reglas = get_registered_rules()
        self.assertGreater(len(reglas), 0)
        self.assertIn("POLIZAS_POR_EXPIRAR", reglas)
    
    def test_reglas_principales_registradas(self):
        """Test que todas las reglas principales estén registradas"""
        reglas = get_registered_rules()
        
        esperadas = [
            'POLIZAS_POR_EXPIRAR',
            'CLIENTES_TOP_PRODUCCION',
            'PRODUCCION_BAJA_DETECTADA',
            'VIGENCIA_IRREGULAR_DETECTADA',
            'SANIDAD_DATOS'
        ]
        
        for regla in esperadas:
            self.assertIn(regla, reglas)


class BusinessRuleTests(TransactionTestCase):
    """Tests para las reglas de negocio"""
    
    def setUp(self):
        """Setup de datos de prueba"""
        # Crear cliente
        self.cliente = Cliente.objects.create(
            nombre='Cliente Test',
            rut='12345678-9'
        )
        
        # Crear pólizas de prueba
        hoy = timezone.now().date()
        
        # Póliza por vencer (en 15 días)
        self.poliza_vencimiento_proximo = Poliza.objects.create(
            numero='POL001',
            cliente=self.cliente,
            fecha_inicio=hoy - timedelta(days=365),
            fecha_vencimiento=hoy + timedelta(days=15),
            monto_uf=100,
            estado='VIGENTE'
        )
        
        # Póliza vigente normal
        self.poliza_vigente = Poliza.objects.create(
            numero='POL002',
            cliente=self.cliente,
            fecha_inicio=hoy - timedelta(days=180),
            fecha_vencimiento=hoy + timedelta(days=180),
            monto_uf=500,
            estado='VIGENTE'
        )
        
        # Regla para pruebas
        self.rule = Rule.objects.create(
            nombre='Test Rule',
            codigo='TEST_RULE',
            tipo='alerta',
            parametros={'dias': 30}
        )
    
    def test_rule_polizas_por_expirar(self):
        """Test regla de pólizas por expirar"""
        resultado = rule_polizas_por_expirar(self.rule)
        
        self.assertEqual(resultado['status'], 'exitosa')
        self.assertGreater(resultado['alertas_creadas'], 0)
        self.assertIn('dias_restantes', resultado.get('detalles', [{}])[0] if resultado.get('detalles') else {})
    
    def test_rule_clientes_top_produccion(self):
        """Test regla de clientes top"""
        self.rule.parametros = {'min_uf': 100, 'generar_alerta': True}
        self.rule.save()
        
        resultado = rule_clientes_top_produccion(self.rule)
        
        self.assertEqual(resultado['status'], 'exitosa')
        self.assertGreater(resultado['clientes_top_detectados'], 0)
    
    def test_rule_produccion_baja_detectada(self):
        """Test regla de producción baja"""
        self.rule.parametros = {'dias_comparar': 7, 'porcentaje_caida': 50}
        self.rule.save()
        
        resultado = rule_produccion_baja_detectada(self.rule)
        
        self.assertEqual(resultado['status'], 'exitosa')
        self.assertIn('caida_porcentual', resultado)
    
    def test_rule_vigencia_irregular_detectada(self):
        """Test regla de vigencia irregular"""
        # Crear múltiples pólizas para el mismo cliente
        hoy = timezone.now().date()
        for i in range(4):
            Poliza.objects.create(
                numero=f'POL_IRREGULAR_{i}',
                cliente=self.cliente,
                fecha_inicio=hoy - timedelta(days=i*30),
                fecha_vencimiento=hoy + timedelta(days=30),
                monto_uf=100,
                estado='VIGENTE'
            )
        
        self.rule.parametros = {'dias_analisis': 90, 'min_renovaciones': 3}
        self.rule.save()
        
        resultado = rule_vigencia_irregular_detectada(self.rule)
        
        self.assertEqual(resultado['status'], 'exitosa')
        self.assertIn('clientes_detectados', resultado)
    
    def test_rule_sanidad_datos(self):
        """Test regla de sanidad de datos"""
        self.rule.parametros = {'alertar_campos_vacios': True, 'alertar_fechas_inconsistentes': True}
        self.rule.save()
        
        resultado = rule_sanidad_datos(self.rule)
        
        self.assertEqual(resultado['status'], 'exitosa')
        self.assertIn('problemas_encontrados', resultado)


class ExecutorTests(TransactionTestCase):
    """Tests para el executor del motor"""
    
    def setUp(self):
        """Setup de datos y reglas"""
        self.cliente = Cliente.objects.create(
            nombre='Cliente Executor Test',
            rut='98765432-1'
        )
        
        hoy = timezone.now().date()
        self.poliza = Poliza.objects.create(
            numero='POL_EXEC001',
            cliente=self.cliente,
            fecha_inicio=hoy - timedelta(days=30),
            fecha_vencimiento=hoy + timedelta(days=10),
            monto_uf=100,
            estado='VIGENTE'
        )
        
        # Crear reglas activas
        self.rule1 = Rule.objects.create(
            nombre='Regla 1',
            codigo='POLIZAS_POR_EXPIRAR',
            tipo='alerta',
            activa=True,
            orden_ejecucion=1,
            parametros={'dias': 30}
        )
        
        self.rule2 = Rule.objects.create(
            nombre='Regla 2',
            codigo='SANIDAD_DATOS',
            tipo='validacion',
            activa=True,
            orden_ejecucion=2,
            parametros={}
        )
    
    def test_ejecutar_motor_todas_reglas(self):
        """Test ejecutar todas las reglas activas"""
        resultado = ejecutar_motor_reglas(solo_activas=True)
        
        self.assertIn('ejecutadas', resultado)
        self.assertIn('exitosas', resultado)
        self.assertIn('fallidas', resultado)
        self.assertGreater(resultado['ejecutadas'], 0)
    
    def test_ejecutar_regla_individual(self):
        """Test ejecutar una regla específica"""
        resultado = ejecutar_regla_individual('POLIZAS_POR_EXPIRAR')
        
        self.assertEqual(resultado['status'], 'exitosa')
        self.assertIn('resultado', resultado)
        self.assertIn('duracion_segundos', resultado)
    
    def test_actualizar_estadisticas_regla(self):
        """Test que se actualicen las estadísticas de la regla"""
        self.rule1.total_ejecuciones = 0
        self.rule1.ejecuciones_exitosas = 0
        self.rule1.save()
        
        ejecutar_regla_individual('POLIZAS_POR_EXPIRAR')
        
        self.rule1.refresh_from_db()
        self.assertGreater(self.rule1.total_ejecuciones, 0)
        self.assertGreater(self.rule1.ejecuciones_exitosas, 0)
    
    def test_crear_registro_ejecucion(self):
        """Test que se cree registro de ejecución"""
        ejecuciones_antes = RuleExecution.objects.count()
        
        ejecutar_regla_individual('POLIZAS_POR_EXPIRAR')
        
        ejecuciones_despues = RuleExecution.objects.count()
        self.assertGreater(ejecuciones_despues, ejecuciones_antes)
    
    def test_regla_no_registrada(self):
        """Test manejo de regla no registrada"""
        regla_inexistente = Rule.objects.create(
            nombre='Regla Inexistente',
            codigo='REGLA_NO_EXISTE',
            tipo='alerta',
            activa=True
        )
        
        resultado = ejecutar_regla_individual('REGLA_NO_EXISTE')
        
        self.assertEqual(resultado['status'], 'error')


class APITests(APITestCase):
    """Tests para la API REST"""
    
    def setUp(self):
        """Setup para tests de API"""
        self.client = APIClient()
        
        # Crear usuario admin
        self.admin = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='admin123'
        )
        
        # Crear regla
        self.rule = Rule.objects.create(
            nombre='API Test Rule',
            codigo='API_TEST_RULE',
            tipo='alerta',
            activa=True,
            parametros={'test': 'value'}
        )
        
        # Autenticar
        self.client.force_authenticate(user=self.admin)
    
    def test_listar_reglas(self):
        """Test listar reglas via API"""
        response = self.client.get('/api/rules/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
    
    def test_crear_regla_via_api(self):
        """Test crear regla via API"""
        data = {
            'nombre': 'Nueva Regla API',
            'codigo': 'NUEVA_API_RULE',
            'descripcion': 'Regla creada via API',
            'tipo': 'alerta',
            'activa': True,
            'parametros': {'test': 'new'}
        }
        
        response = self.client.post('/api/rules/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Rule.objects.filter(codigo='NUEVA_API_RULE').exists())
    
    def test_obtener_detalles_regla(self):
        """Test obtener detalles de regla"""
        response = self.client.get(f'/api/rules/{self.rule.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['codigo'], 'API_TEST_RULE')
    
    def test_ejecutar_regla_via_api(self):
        """Test ejecutar regla via API"""
        response = self.client.post(f'/api/rules/{self.rule.id}/execute/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('status', response.data)
    
    def test_ejecutar_todas_reglas_via_api(self):
        """Test ejecutar todas las reglas via API"""
        response = self.client.post('/api/rules/execute_all/', {'solo_activas': True}, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('ejecutadas', response.data)
    
    def test_ver_reglas_registradas_via_api(self):
        """Test ver reglas registradas via API"""
        response = self.client.get('/api/rules/registered/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('reglas', response.data)
    
    def test_health_check_via_api(self):
        """Test health check del motor"""
        response = self.client.get('/api/rules/health/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'operacional')
        self.assertIn('reglas', response.data)
        self.assertIn('ejecuciones', response.data)
    
    def test_ver_ejecuciones_regla_via_api(self):
        """Test ver historial de ejecuciones via API"""
        # Ejecutar primero
        self.client.post(f'/api/rules/{self.rule.id}/execute/')
        
        # Luego listar ejecuciones
        response = self.client.get(f'/api/rules/{self.rule.id}/executions/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
    
    def test_permiso_admin_requerido(self):
        """Test que se requiera permisos de admin"""
        self.client.force_authenticate(user=None)
        
        response = self.client.get('/api/rules/')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
