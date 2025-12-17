"""
PASO 13: Tests para Gestión Avanzada de Usuarios + Roles + Políticas de Seguridad

Prueba:
- Permisos por rol (admin, comercial, auditor)
- Auditoría avanzada
- Control de seguridad
- Validaciones
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from auditorias.models import AuditoriaAccion
from usuarios.audita import AuditoriaManager
import json

User = get_user_model()


class RoleBasedPermissionTests(APITestCase):
    """
    Tests para validar permisos basados en roles.
    """
    
    def setUp(self):
        """Crear usuarios de prueba con diferentes roles"""
        self.admin_user = User.objects.create_user(
            username='admin_user',
            email='admin@test.com',
            password='testpass123',
            role='admin'
        )
        
        self.comercial_user = User.objects.create_user(
            username='comercial_user',
            email='comercial@test.com',
            password='testpass123',
            role='comercial'
        )
        
        self.auditor_user = User.objects.create_user(
            username='auditor_user',
            email='auditor@test.com',
            password='testpass123',
            role='auditor'
        )
        
        self.client = APIClient()
    
    def test_admin_can_access_admin_panel(self):
        """Admin puede acceder al panel de administración"""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get('/api/usuarios/admin/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_comercial_cannot_access_admin_panel(self):
        """Comercial NO puede acceder al panel de administración"""
        self.client.force_authenticate(user=self.comercial_user)
        response = self.client.get('/api/usuarios/admin/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_auditor_cannot_access_admin_panel(self):
        """Auditor NO puede acceder al panel de administración"""
        self.client.force_authenticate(user=self.auditor_user)
        response = self.client.get('/api/usuarios/admin/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_unauthenticated_cannot_access_admin_panel(self):
        """Usuario no autenticado NO puede acceder al panel"""
        response = self.client.get('/api/usuarios/admin/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class UserCreationWithAuditTests(APITestCase):
    """
    Tests para creación de usuarios con auditoría.
    """
    
    def setUp(self):
        """Crear admin de prueba"""
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            role='admin'
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin_user)
    
    def test_create_user_generates_audit_log(self):
        """Crear usuario genera entrada en auditoría"""
        user_data = {
            'username': 'newuser',
            'email': 'new@test.com',
            'password': 'testpass123',
            'password2': 'testpass123',
            'role': 'comercial'
        }
        
        # Contar auditorías antes
        audit_count_before = AuditoriaAccion.objects.filter(
            accion='CREATE',
            modelo='Usuario'
        ).count()
        
        response = self.client.post('/api/usuarios/admin/', user_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Contar auditorías después
        audit_count_after = AuditoriaAccion.objects.filter(
            accion='CREATE',
            modelo='Usuario'
        ).count()
        
        self.assertEqual(audit_count_after, audit_count_before + 1)
    
    def test_audit_log_contains_user_data(self):
        """Auditoría contiene datos del usuario creado"""
        user_data = {
            'username': 'testuser',
            'email': 'test@test.com',
            'password': 'testpass123',
            'password2': 'testpass123',
            'role': 'comercial'
        }
        
        response = self.client.post('/api/usuarios/admin/', user_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verificar auditoría
        audit = AuditoriaAccion.objects.filter(
            accion='CREATE',
            modelo='Usuario'
        ).latest('fecha_hora')
        
        self.assertIsNotNone(audit.datos_nuevos)
        datos = json.loads(audit.datos_nuevos)
        self.assertEqual(datos['username'], 'testuser')
        self.assertEqual(datos['email'], 'test@test.com')


class RoleChangeAuditTests(APITestCase):
    """
    Tests para cambio de rol con auditoría.
    """
    
    def setUp(self):
        """Crear usuarios de prueba"""
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            role='admin'
        )
        
        self.target_user = User.objects.create_user(
            username='targetuser',
            email='target@test.com',
            password='testpass123',
            role='comercial'
        )
        
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin_user)
    
    def test_change_role_generates_audit_log(self):
        """Cambiar rol genera entrada de auditoría"""
        response = self.client.post(
            f'/api/usuarios/admin/{self.target_user.id}/change_role/',
            {'role': 'comercial'}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verificar auditoría
        audit = AuditoriaAccion.objects.filter(
            accion='ROLE_CHANGE',
            objeto_id=str(self.target_user.id)
        ).latest('fecha_hora')
        
        self.assertIsNotNone(audit)
        datos_anteriores = json.loads(audit.datos_anteriores)
        datos_nuevos = json.loads(audit.datos_nuevos)
        
        self.assertEqual(datos_anteriores['role'], 'comercial')
        self.assertEqual(datos_nuevos['role'], 'comercial')
    
    def test_invalid_role_rejected(self):
        """Rol inválido es rechazado"""
        response = self.client.post(
            f'/api/usuarios/admin/{self.target_user.id}/change_role/',
            {'role': 'invalid_role'}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class UserDeactivationAuditTests(APITestCase):
    """
    Tests para desactivación de usuario con auditoría.
    """
    
    def setUp(self):
        """Crear usuarios de prueba"""
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            role='admin'
        )
        
        self.target_user = User.objects.create_user(
            username='targetuser',
            email='target@test.com',
            password='testpass123',
            role='ejecutivo'
        )
        
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin_user)
    
    def test_deactivate_user_generates_audit_log(self):
        """Desactivar usuario genera entrada de auditoría"""
        response = self.client.post(
            f'/api/usuarios/admin/{self.target_user.id}/deactivate/'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verificar auditoría
        audit = AuditoriaAccion.objects.filter(
            accion='DEACTIVATE',
            objeto_id=str(self.target_user.id)
        ).latest('fecha_hora')
        
        self.assertIsNotNone(audit)
        
        # Verificar que usuario está desactivado
        self.target_user.refresh_from_db()
        self.assertFalse(self.target_user.is_active)
    
    def test_admin_cannot_deactivate_self(self):
        """Admin NO puede desactivar su propia cuenta"""
        response = self.client.post(
            f'/api/usuarios/admin/{self.admin_user.id}/deactivate/'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_activate_deactivated_user(self):
        """Reactivar usuario desactivado genera auditoría"""
        # Desactivar primero
        self.target_user.is_active = False
        self.target_user.save()
        
        # Reactivar
        response = self.client.post(
            f'/api/usuarios/admin/{self.target_user.id}/activate/'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verificar auditoría de reactivación
        audit = AuditoriaAccion.objects.filter(
            accion='ACTIVATE',
            objeto_id=str(self.target_user.id)
        ).latest('fecha_hora')
        
        self.assertIsNotNone(audit)
        
        # Verificar que usuario está activo
        self.target_user.refresh_from_db()
        self.assertTrue(self.target_user.is_active)


class PasswordResetAuditTests(APITestCase):
    """
    Tests para reset de contraseña con auditoría.
    """
    
    def setUp(self):
        """Crear usuarios de prueba"""
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            role='admin'
        )
        
        self.target_user = User.objects.create_user(
            username='targetuser',
            email='target@test.com',
            password='testpass123',
            role='ejecutivo'
        )
        
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin_user)
    
    def test_reset_password_generates_audit_log(self):
        """Reset de contraseña genera entrada de auditoría"""
        response = self.client.post(
            f'/api/usuarios/admin/{self.target_user.id}/reset_password/'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verificar auditoría
        audit = AuditoriaAccion.objects.filter(
            accion='PASSWORD_CHANGE',
            objeto_id=str(self.target_user.id)
        ).latest('fecha_hora')
        
        self.assertIsNotNone(audit)
        
        # Verificar que contraseña cambió
        self.target_user.refresh_from_db()
        # Si los hashes son diferentes, la contraseña fue cambiada
        self.assertNotEqual(
            self.target_user.password,
            'testpass123'
        )


class AuditoriaManagerTests(TestCase):
    """
    Tests para el AuditoriaManager.
    """
    
    def setUp(self):
        """Crear usuarios de prueba"""
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            role='admin'
        )
        
        self.target_user = User.objects.create_user(
            username='targetuser',
            email='target@test.com',
            password='testpass123',
            role='ejecutivo'
        )
    
    def test_registrar_creacion_usuario(self):
        """Registrar creación de usuario"""
        audit = AuditoriaManager.registrar_creacion_usuario(
            usuario_admin=self.admin_user,
            usuario_creado=self.target_user,
            datos={'username': self.target_user.username}
        )
        
        self.assertIsNotNone(audit)
        self.assertEqual(audit.accion, 'CREATE')
        self.assertEqual(audit.usuario, self.admin_user)
    
    def test_registrar_cambio_rol(self):
        """Registrar cambio de rol"""
        audit = AuditoriaManager.registrar_cambio_rol(
            usuario_admin=self.admin_user,
            usuario_modificado=self.target_user,
            rol_anterior='ejecutivo',
            rol_nuevo='gestor'
        )
        
        self.assertIsNotNone(audit)
        self.assertEqual(audit.accion, 'ROLE_CHANGE')
    
    def test_obtener_historial_usuario(self):
        """Obtener historial de usuario"""
        # Crear varias acciones
        for _ in range(3):
            AuditoriaManager.registrar_creacion_usuario(
                usuario_admin=self.admin_user,
                usuario_creado=self.target_user,
                datos={}
            )
        
        historial = AuditoriaManager.obtener_historial_usuario(
            self.target_user.id
        )
        
        self.assertGreater(len(historial), 0)
    
    def test_obtener_acciones_admin(self):
        """Obtener acciones realizadas por admin"""
        # Crear varias acciones
        AuditoriaManager.registrar_creacion_usuario(
            usuario_admin=self.admin_user,
            usuario_creado=self.target_user,
            datos={}
        )
        
        AuditoriaManager.registrar_cambio_rol(
            usuario_admin=self.admin_user,
            usuario_modificado=self.target_user,
            rol_anterior='ejecutivo',
            rol_nuevo='gestor'
        )
        
        acciones = AuditoriaManager.obtener_acciones_admin(
            self.admin_user
        )
        
        self.assertGreater(len(acciones), 0)
    
    def test_obtener_estadisticas_auditoria(self):
        """Obtener estadísticas de auditoría"""
        # Crear varias acciones
        AuditoriaManager.registrar_creacion_usuario(
            usuario_admin=self.admin_user,
            usuario_creado=self.target_user,
            datos={}
        )
        
        AuditoriaManager.registrar_cambio_rol(
            usuario_admin=self.admin_user,
            usuario_modificado=self.target_user,
            rol_anterior='ejecutivo',
            rol_nuevo='gestor'
        )
        
        estadisticas = AuditoriaManager.obtener_estadisticas_auditoria(dias=30)
        
        self.assertIsNotNone(estadisticas)
        self.assertGreater(estadisticas['total_acciones'], 0)
        self.assertGreater(estadisticas['creaciones'], 0)


class SecurityPoliciesTests(APITestCase):
    """
    Tests para políticas de seguridad avanzadas.
    """
    
    def setUp(self):
        """Crear usuarios de prueba"""
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            role='admin'
        )
        
        self.gestor_user = User.objects.create_user(
            username='gestor',
            email='gestor@test.com',
            password='testpass123',
            role='gestor'
        )
        
        self.ejecutivo_user = User.objects.create_user(
            username='ejecutivo',
            email='ejecutivo@test.com',
            password='testpass123',
            role='ejecutivo'
        )
        
        self.client = APIClient()
    
    def test_user_cannot_change_own_role(self):
        """Usuario NO puede cambiar su propio rol"""
        self.client.force_authenticate(user=self.ejecutivo_user)
        
        # Intentar cambiar su propio rol
        response = self.client.patch(
            f'/api/usuarios/{self.ejecutivo_user.id}/',
            {'role': 'admin'}
        )
        
        # El rol no debe haber cambiado
        self.ejecutivo_user.refresh_from_db()
        self.assertEqual(self.ejecutivo_user.role, 'ejecutivo')
    
    def test_non_admin_cannot_create_users(self):
        """No-admin NO puede crear usuarios"""
        self.client.force_authenticate(user=self.ejecutivo_user)
        
        user_data = {
            'username': 'newuser',
            'email': 'new@test.com',
            'password': 'testpass123',
            'password2': 'testpass123',
            'role': 'ejecutivo'
        }
        
        response = self.client.post('/api/usuarios/admin/', user_data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_soft_delete_preserves_data(self):
        """Soft delete preserva datos del usuario"""
        self.client.force_authenticate(user=self.admin_user)
        
        # Desactivar usuario
        response = self.client.post(
            f'/api/usuarios/admin/{self.ejecutivo_user.id}/deactivate/'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verificar que usuario existe pero está inactivo
        user = User.objects.get(id=self.ejecutivo_user.id)
        self.assertFalse(user.is_active)
        self.assertEqual(user.username, 'ejecutivo')
        self.assertEqual(user.email, 'ejecutivo@test.com')
