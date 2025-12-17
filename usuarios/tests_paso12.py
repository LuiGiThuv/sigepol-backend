"""
PASO 12: Tests para Administración de Usuarios

Pruebas para:
- Listar usuarios
- Crear usuarios
- Actualizar usuarios
- Desactivar/Activar usuarios
- Cambiar roles
- Auditoría de acciones
- Permisos (solo admin)
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from auditorias.models import AuditoriaAccion

User = get_user_model()


class AdminUserManagementTestCase(TestCase):
    """Tests para AdminUserManagementViewSet"""
    
    def setUp(self):
        """Configurar datos para las pruebas"""
        self.client = APIClient()
        
        # Crear usuario administrador
        self.admin_user = User.objects.create_user(
            username='admin_test',
            email='admin@test.com',
            password='admin123',
            role='admin',
            is_staff=True
        )
        
        # Crear usuario comercial
        self.comercial_user = User.objects.create_user(
            username='comercial_test',
            email='comercial@test.com',
            password='comercial123',
            role='comercial'
        )
        
        # Crear usuario auditor
        self.auditor_user = User.objects.create_user(
            username='auditor_test',
            email='auditor@test.com',
            password='auditor123',
            role='auditor'
        )
    
    def test_admin_list_users(self):
        """Test: Admin puede listar todos los usuarios"""
        self.client.force_authenticate(user=self.admin_user)
        
        response = self.client.get('/api/usuarios/admin/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_non_admin_cannot_list_admin_users(self):
        """Test: Usuario no-admin NO puede acceder a /api/usuarios/admin/"""
        self.client.force_authenticate(user=self.comercial_user)
        
        response = self.client.get('/api/usuarios/admin/')
        
        # Debe obtener 403 Forbidden
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_create_user_as_admin(self):
        """Test: Admin puede crear nuevo usuario"""
        self.client.force_authenticate(user=self.admin_user)
        
        data = {
            'username': 'nuevo_usuario',
            'email': 'nuevo@test.com',
            'password': 'password123',
            'password2': 'password123',
            'first_name': 'Juan',
            'last_name': 'Pérez',
            'role': 'comercial'
        }
        
        response = self.client.post('/api/usuarios/admin/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['username'], 'nuevo_usuario')
        self.assertEqual(response.data['role'], 'comercial')
        
        # Verificar que se creó en BD
        user = User.objects.get(username='nuevo_usuario')
        self.assertIsNotNone(user)
        self.assertEqual(user.email, 'nuevo@test.com')
        
        # Verificar auditoría
        audit_log = AuditoriaAccion.objects.filter(
            accion="CREATE",
            objeto_id=str(user.id)
        ).first()
        self.assertIsNotNone(audit_log)
    
    def test_create_user_non_admin_forbidden(self):
        """Test: Usuario no-admin NO puede crear usuarios"""
        self.client.force_authenticate(user=self.comercial_user)
        
        data = {
            'username': 'nuevo_usuario',
            'email': 'nuevo@test.com',
            'password': 'password123',
            'role': 'comercial'
        }
        
        response = self.client.post('/api/usuarios/admin/', data)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_update_user_as_admin(self):
        """Test: Admin puede actualizar usuario"""
        self.client.force_authenticate(user=self.admin_user)
        
        data = {
            'email': 'newemail@test.com',
            'first_name': 'Carlos',
            'role': 'auditor'
        }
        
        response = self.client.patch(
            f'/api/usuarios/admin/{self.comercial_user.id}/',
            data
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verificar cambios
        self.comercial_user.refresh_from_db()
        self.assertEqual(self.comercial_user.email, 'newemail@test.com')
        self.assertEqual(self.comercial_user.first_name, 'Carlos')
        self.assertEqual(self.comercial_user.role, 'auditor')
        
        # Verificar auditoría
        audit_log = AuditoriaAccion.objects.filter(
            accion="UPDATE",
            objeto_id=str(self.comercial_user.id)
        ).first()
        self.assertIsNotNone(audit_log)
    
    def test_deactivate_user(self):
        """Test: Admin puede desactivar usuario"""
        self.client.force_authenticate(user=self.admin_user)
        
        self.assertTrue(self.comercial_user.is_active)
        
        response = self.client.post(
            f'/api/usuarios/admin/{self.comercial_user.id}/deactivate/'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verificar que fue desactivado
        self.comercial_user.refresh_from_db()
        self.assertFalse(self.comercial_user.is_active)
        
        # Verificar auditoría
        audit_log = AuditoriaAccion.objects.filter(
            accion="UPDATE",
            objeto_id=str(self.comercial_user.id)
        ).first()
        self.assertIsNotNone(audit_log)
    
    def test_admin_cannot_deactivate_self(self):
        """Test: Admin NO puede desactivarse a sí mismo"""
        self.client.force_authenticate(user=self.admin_user)
        
        response = self.client.post(
            f'/api/usuarios/admin/{self.admin_user.id}/deactivate/'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Verificar que sigue activo
        self.admin_user.refresh_from_db()
        self.assertTrue(self.admin_user.is_active)
    
    def test_activate_user(self):
        """Test: Admin puede activar usuario desactivado"""
        self.client.force_authenticate(user=self.admin_user)
        
        # Primero desactivar
        self.comercial_user.is_active = False
        self.comercial_user.save()
        
        # Luego activar
        response = self.client.post(
            f'/api/usuarios/admin/{self.comercial_user.id}/activate/'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verificar que fue activado
        self.comercial_user.refresh_from_db()
        self.assertTrue(self.comercial_user.is_active)
        
        # Verificar auditoría
        audit_log = AuditoriaAccion.objects.filter(
            accion="UPDATE",
            objeto_id=str(self.comercial_user.id)
        ).first()
        self.assertIsNotNone(audit_log)
    
    def test_reset_password(self):
        """Test: Admin puede resetear contraseña"""
        self.client.force_authenticate(user=self.admin_user)
        
        old_password = self.gestor_user.password
        
        response = self.client.post(
            f'/api/usuarios/admin/{self.gestor_user.id}/reset_password/'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('temporary_password', response.data)
        
        # Verificar que la contraseña cambió
        self.gestor_user.refresh_from_db()
        self.assertNotEqual(self.gestor_user.password, old_password)
        
        # Verificar auditoría
        audit_log = AuditoriaAccion.objects.filter(
            accion="PASSWORD_CHANGE",
            objeto_id=str(self.gestor_user.id)
        ).first()
        self.assertIsNotNone(audit_log)
    
    def test_change_role(self):
        """Test: Admin puede cambiar rol de usuario"""
        self.client.force_authenticate(user=self.admin_user)
        
        self.assertEqual(self.comercial_user.role, 'comercial')
        
        data = {'role': 'auditor'}
        response = self.client.post(
            f'/api/usuarios/admin/{self.comercial_user.id}/change_role/',
            data
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verificar cambio
        self.comercial_user.refresh_from_db()
        self.assertEqual(self.comercial_user.role, 'auditor')
        
        # Verificar auditoría
        audit_log = AuditoriaAccion.objects.filter(
            accion="ROLE_CHANGE",
            objeto_id=str(self.comercial_user.id)
        ).first()
        self.assertIsNotNone(audit_log)
        self.assertIn('comercial', audit_log.descripcion)
        self.assertIn('auditor', audit_log.descripcion)
    
    def test_change_role_invalid(self):
        """Test: No permitir rol inválido"""
        self.client.force_authenticate(user=self.admin_user)
        
        data = {'role': 'rol_invalido'}
        response = self.client.post(
            f'/api/usuarios/admin/{self.comercial_user.id}/change_role/',
            data
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Verificar que el rol no cambió
        self.comercial_user.refresh_from_db()
        self.assertEqual(self.comercial_user.role, 'comercial')
    
    def test_filter_by_role(self):
        """Test: Filtrar usuarios por rol"""
        self.client.force_authenticate(user=self.admin_user)
        
        response = self.client.get('/api/usuarios/admin/by_role/?role=comercial')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['role'], 'comercial')
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['users'][0]['username'], 'comercial_test')
    
    def test_search_users(self):
        """Test: Buscar usuarios por username/email/nombre"""
        self.client.force_authenticate(user=self.admin_user)
        
        # Buscar por email
        response = self.client.get('/api/usuarios/admin/search/?q=comercial@test.com')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['users'][0]['username'], 'comercial_test')
    
    def test_search_minimum_length(self):
        """Test: Búsqueda debe tener mínimo 2 caracteres"""
        self.client.force_authenticate(user=self.admin_user)
        
        response = self.client.get('/api/usuarios/admin/search/?q=a')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_activity_report(self):
        """Test: Obtener reporte de actividad de usuarios"""
        self.client.force_authenticate(user=self.admin_user)
        
        response = self.client.get('/api/usuarios/admin/activity_report/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_users'], 3)
        self.assertEqual(response.data['active_users'], 3)
        self.assertEqual(response.data['inactive_users'], 0)
        self.assertIn('role_distribution', response.data)
        # Las keys son los nombres legibles, no los códigos
        self.assertTrue(any('Administrador' in str(k) or 'admin' in str(k).lower() for k in response.data['role_distribution'].keys()))
    
    def test_audit_history(self):
        """Test: Ver historial de auditoría de usuario"""
        self.client.force_authenticate(user=self.admin_user)
        
        # Hacer una acción que genere auditoría
        self.client.post(
            f'/api/usuarios/admin/{self.comercial_user.id}/deactivate/'
        )
        
        # Obtener historial
        response = self.client.get(
            f'/api/usuarios/admin/{self.comercial_user.id}/audit_history/'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['user'], 'comercial_test')
        self.assertGreater(response.data['audit_count'], 0)
        self.assertGreater(len(response.data['audit_logs']), 0)
    
    def test_soft_delete_user(self):
        """Test: Eliminar usuario (soft delete - desactivar)"""
        self.client.force_authenticate(user=self.admin_user)
        
        user_id = self.comercial_user.id
        user_count_before = User.objects.count()
        
        response = self.client.delete(
            f'/api/usuarios/admin/{self.comercial_user.id}/'
        )
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # Verificar que el usuario sigue en BD pero inactivo
        user = User.objects.get(id=user_id)
        self.assertFalse(user.is_active)
        
        # Verificar que el count es el mismo (soft delete)
        user_count_after = User.objects.count()
        self.assertEqual(user_count_before, user_count_after)
        
        # Verificar auditoría
        audit_log = AuditoriaAccion.objects.filter(
            accion="DELETE",
            objeto_id=str(user_id)
        ).first()
        self.assertIsNotNone(audit_log)
    
    def test_unauthenticated_access_denied(self):
        """Test: Usuario no autenticado NO puede acceder"""
        response = self.client.get('/api/usuarios/admin/')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_audit_log_created_on_list(self):
        """Test: Se registra auditoría cuando admin lista usuarios"""
        initial_count = AuditoriaAccion.objects.filter(accion='READ').count()
        
        self.client.force_authenticate(user=self.admin_user)
        self.client.get('/api/usuarios/admin/')
        
        final_count = AuditoriaAccion.objects.filter(accion='READ').count()
        self.assertEqual(final_count, initial_count + 1)
    
    def test_retrieve_user_detail(self):
        """Test: Admin puede ver detalles completos de usuario"""
        self.client.force_authenticate(user=self.admin_user)
        
        response = self.client.get(
            f'/api/usuarios/admin/{self.comercial_user.id}/'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'comercial_test')
        self.assertEqual(response.data['email'], 'comercial@test.com')
        self.assertIn('last_login_display', response.data)
        self.assertIn('role_display', response.data)
