"""
Utilidades para auditoría del sistema
"""
from .models import AuditLog, AuditoriaAccion


def create_audit_log(usuario, accion, descripcion, detalles=None):
    """
    Crear un registro de auditoría simple
    
    Args:
        usuario: Usuario que realiza la acción
        accion: Tipo de acción (login, upload, process, view, update, delete, ml_run, report_generate, export)
        descripcion: Descripción legible de la acción
        detalles: Dict opcional con detalles adicionales
    
    Ejemplo:
        create_audit_log(
            usuario=request.user,
            accion='upload',
            descripcion='Se subió archivo datos_mensual.xlsx',
            detalles={'filename': 'datos_mensual.xlsx', 'size': 1024000}
        )
    """
    return AuditLog.objects.create(
        usuario=usuario,
        accion=accion,
        descripcion=descripcion,
        detalles=detalles or {}
    )


def create_detailed_audit(usuario, accion, modulo, modelo, descripcion,
                         objeto_id=None, datos_anteriores=None, datos_nuevos=None,
                         ip_address=None, user_agent=None, metodo_http=None, url=None,
                         exitoso=True, mensaje_error=None):
    """
    Crear un registro de auditoría detallado (wrapper de AuditoriaAccion.registrar)
    
    Args:
        usuario: Usuario que realiza la acción
        accion: CREATE, UPDATE, DELETE, READ, LOGIN, etc
        modulo: Módulo del sistema (cobranzas, alertas, usuarios)
        modelo: Modelo de datos (Cobranza, Alerta, User)
        descripcion: Descripción legible
        objeto_id: ID del objeto modificado
        datos_anteriores: Valores antes (JSON)
        datos_nuevos: Valores después (JSON)
        ip_address: IP del cliente
        user_agent: User agent del navegador
        metodo_http: GET, POST, PUT, DELETE
        url: Endpoint accedido
        exitoso: Fue exitoso?
        mensaje_error: Mensaje de error si falló
    """
    return AuditoriaAccion.registrar(
        usuario=usuario,
        accion=accion,
        modulo=modulo,
        modelo=modelo,
        descripcion=descripcion,
        objeto_id=objeto_id,
        datos_anteriores=datos_anteriores,
        datos_nuevos=datos_nuevos,
        ip_address=ip_address,
        user_agent=user_agent,
        metodo_http=metodo_http,
        url=url,
        exitoso=exitoso,
        mensaje_error=mensaje_error
    )
