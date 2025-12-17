"""
Utilidades para gestionar cargas de datos
"""
from .models import DataUpload


def update_upload_status(upload, status, error_message=None, detalles=None):
    """
    Actualizar el estado de una carga
    
    Args:
        upload: Instancia de DataUpload
        status: Nuevo estado (pendiente, validando, limpiando, procesando, ml, completado, error)
        error_message: Mensaje de error si aplica
        detalles: Dict con detalles del procesamiento
    
    Ejemplo:
        update_upload_status(
            upload=data_upload,
            status='procesando',
            detalles={'registros_procesados': 100, 'errores': 0}
        )
    """
    upload.estado = status
    
    if error_message:
        upload.mensaje_error = error_message
    
    if detalles:
        upload.detalles_procesamiento = detalles
    
    upload.save()
    return upload


def mark_upload_error(upload, error_message):
    """
    Marcar una carga como error
    
    Args:
        upload: Instancia de DataUpload
        error_message: Mensaje de error
    """
    return update_upload_status(
        upload=upload,
        status='error',
        error_message=error_message
    )


def mark_upload_completed(upload, detalles=None):
    """
    Marcar una carga como completada
    
    Args:
        upload: Instancia de DataUpload
        detalles: Dict con detalles finales del procesamiento
    """
    return update_upload_status(
        upload=upload,
        status='completado',
        detalles=detalles
    )
