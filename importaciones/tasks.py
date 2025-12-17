"""
Celery tasks para procesamiento asincrónico de imports
"""
from celery import shared_task
from .etl import process_upload


@shared_task(bind=True, max_retries=3)
def process_upload_task(self, upload_id):
    """
    Tarea Celery para procesar upload ETL
    
    Args:
        upload_id: ID de DataUpload a procesar
    
    Returns:
        Dict con resultado del procesamiento
    """
    try:
        return process_upload(upload_id, run_ml=False)
    except Exception as exc:
        # Reintentar con backoff exponencial
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
