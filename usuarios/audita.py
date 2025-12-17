"""
Módulo de Auditoría Avanzada para PASO 13

Registra todas las acciones de usuario:
- Creación de usuario
- Cambio de rol
- Eliminación/desactivación
- Login
- Password reset
- Cambios de datos
"""

from auditorias.models import AuditoriaAccion
from django.utils import timezone
import json


class AuditoriaManager:
    """
    Gestor centralizado de auditoría para todos los eventos de usuarios.
    """
    
    @staticmethod
    def registrar_accion(usuario, accion, descripcion, datos_anteriores=None, 
                        datos_nuevos=None, modelo='Usuario', objeto_id=None, modulo='usuarios'):
        """
        Registra una acción en la auditoría.
        
        Args:
            usuario: Usuario que realizó la acción
            accion: Tipo de acción (CREATE, UPDATE, DELETE, LOGIN, PASSWORD_CHANGE, ROLE_CHANGE)
            descripcion: Descripción legible de la acción
            datos_anteriores: Dict con datos antes del cambio
            datos_nuevos: Dict con datos después del cambio
            modelo: Modelo afectado
            objeto_id: ID del objeto modificado
            modulo: Módulo donde ocurrió la acción
        """
        try:
            audit_entry = AuditoriaAccion.objects.create(
                usuario=usuario,
                accion=accion,
                descripcion=descripcion,
                datos_anteriores=json.dumps(datos_anteriores) if datos_anteriores else None,
                datos_nuevos=json.dumps(datos_nuevos) if datos_nuevos else None,
                modelo=modelo,
                objeto_id=objeto_id,
                modulo=modulo,
                fecha_hora=timezone.now()
            )
            return audit_entry
        except Exception as e:
            print(f"Error registrando auditoría: {str(e)}")
            return None
    
    @staticmethod
    def registrar_creacion_usuario(usuario_admin, usuario_creado, datos):
        """
        Registra la creación de un nuevo usuario.
        """
        descripcion = f"Usuario {usuario_creado.username} creado por {usuario_admin.username}"
        datos_nuevos = {
            'username': usuario_creado.username,
            'email': usuario_creado.email,
            'role': usuario_creado.role,
            'is_active': usuario_creado.is_active,
            'first_name': usuario_creado.first_name,
            'last_name': usuario_creado.last_name,
        }
        
        return AuditoriaManager.registrar_accion(
            usuario=usuario_admin,
            accion='CREATE',
            descripcion=descripcion,
            datos_nuevos=datos_nuevos,
            objeto_id=usuario_creado.id,
            modelo='Usuario'
        )
    
    @staticmethod
    def registrar_cambio_rol(usuario_admin, usuario_modificado, rol_anterior, rol_nuevo):
        """
        Registra el cambio de rol de un usuario.
        """
        descripcion = (
            f"Rol de {usuario_modificado.username} cambió de "
            f"{usuario_modificado.get_role_display()} a {usuario_modificado.get_role_display()}"
        )
        
        datos_anteriores = {'role': rol_anterior}
        datos_nuevos = {'role': rol_nuevo}
        
        return AuditoriaManager.registrar_accion(
            usuario=usuario_admin,
            accion='ROLE_CHANGE',
            descripcion=descripcion,
            datos_anteriores=datos_anteriores,
            datos_nuevos=datos_nuevos,
            objeto_id=usuario_modificado.id,
            modelo='Usuario'
        )
    
    @staticmethod
    def registrar_desactivacion(usuario_admin, usuario_desactivado):
        """
        Registra la desactivación de un usuario.
        """
        descripcion = f"Usuario {usuario_desactivado.username} desactivado por {usuario_admin.username}"
        
        datos_anteriores = {'is_active': True}
        datos_nuevos = {'is_active': False}
        
        return AuditoriaManager.registrar_accion(
            usuario=usuario_admin,
            accion='DEACTIVATE',
            descripcion=descripcion,
            datos_anteriores=datos_anteriores,
            datos_nuevos=datos_nuevos,
            objeto_id=usuario_desactivado.id,
            modelo='Usuario'
        )
    
    @staticmethod
    def registrar_reactivacion(usuario_admin, usuario_reactivado):
        """
        Registra la reactivación de un usuario.
        """
        descripcion = f"Usuario {usuario_reactivado.username} reactivado por {usuario_admin.username}"
        
        datos_anteriores = {'is_active': False}
        datos_nuevos = {'is_active': True}
        
        return AuditoriaManager.registrar_accion(
            usuario=usuario_admin,
            accion='ACTIVATE',
            descripcion=descripcion,
            datos_anteriores=datos_anteriores,
            datos_nuevos=datos_nuevos,
            objeto_id=usuario_reactivado.id,
            modelo='Usuario'
        )
    
    @staticmethod
    def registrar_reset_password(usuario_admin, usuario_modificado):
        """
        Registra el reset de contraseña de un usuario.
        """
        descripcion = f"Contraseña reseteada para usuario {usuario_modificado.username} por {usuario_admin.username}"
        
        return AuditoriaManager.registrar_accion(
            usuario=usuario_admin,
            accion='PASSWORD_CHANGE',
            descripcion=descripcion,
            datos_nuevos={'password_reseteada': True},
            objeto_id=usuario_modificado.id,
            modelo='Usuario'
        )
    
    @staticmethod
    def registrar_login(usuario):
        """
        Registra el login de un usuario.
        """
        descripcion = f"Login del usuario {usuario.username}"
        
        return AuditoriaManager.registrar_accion(
            usuario=usuario,
            accion='LOGIN',
            descripcion=descripcion,
            datos_nuevos={'last_login': str(timezone.now())},
            objeto_id=usuario.id,
            modelo='Usuario'
        )
    
    @staticmethod
    def registrar_cambio_perfil(usuario, datos_antiguos, datos_nuevos):
        """
        Registra cambios en el perfil del usuario.
        """
        cambios = []
        for key in datos_nuevos:
            if key not in datos_antiguos or datos_antiguos[key] != datos_nuevos[key]:
                cambios.append(f"{key}: {datos_antiguos.get(key)} → {datos_nuevos[key]}")
        
        descripcion = f"Perfil actualizado: {', '.join(cambios)}" if cambios else "Perfil actualizado"
        
        return AuditoriaManager.registrar_accion(
            usuario=usuario,
            accion='UPDATE',
            descripcion=descripcion,
            datos_anteriores=datos_antiguos,
            datos_nuevos=datos_nuevos,
            objeto_id=usuario.id,
            modelo='Usuario'
        )
    
    @staticmethod
    def obtener_historial_usuario(usuario_id, limit=100):
        """
        Obtiene el historial de auditoría de un usuario.
        """
        return AuditoriaAccion.objects.filter(
            objeto_id=usuario_id,
            modelo='Usuario'
        ).order_by('-fecha_hora')[:limit]
    
    @staticmethod
    def obtener_acciones_admin(usuario_admin, limit=100):
        """
        Obtiene todas las acciones realizadas por un admin.
        """
        return AuditoriaAccion.objects.filter(
            usuario=usuario_admin,
            accion__in=['CREATE', 'UPDATE', 'DELETE', 'DEACTIVATE', 'ACTIVATE', 
                       'PASSWORD_CHANGE', 'ROLE_CHANGE']
        ).order_by('-fecha_hora')[:limit]
    
    @staticmethod
    def obtener_estadisticas_auditoria(dias=30):
        """
        Obtiene estadísticas de auditoría de los últimos N días.
        """
        from django.utils import timezone
        from datetime import timedelta
        
        fecha_inicio = timezone.now() - timedelta(days=dias)
        
        acciones = AuditoriaAccion.objects.filter(
            fecha_hora__gte=fecha_inicio,
            modelo='Usuario'
        )
        
        estadisticas = {
            'total_acciones': acciones.count(),
            'creaciones': acciones.filter(accion='CREATE').count(),
            'cambios_rol': acciones.filter(accion='ROLE_CHANGE').count(),
            'desactivaciones': acciones.filter(accion='DEACTIVATE').count(),
            'reactivaciones': acciones.filter(accion='ACTIVATE').count(),
            'resets_password': acciones.filter(accion='PASSWORD_CHANGE').count(),
            'logins': acciones.filter(accion='LOGIN').count(),
        }
        
        return estadisticas
