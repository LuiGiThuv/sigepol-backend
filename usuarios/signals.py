"""
PASO 12: Señales de Auditoría para Usuarios

Captura automática de eventos de usuarios y registra en AuditLog
"""

from django.db.models.signals import post_save, pre_delete, m2m_changed
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from auditorias.models import AuditoriaAccion
import json

User = get_user_model()


# Las señales pueden deshabilitarse por ahora ya que los views
# registran la auditoría manualmente para mayor control

def ready():
    """
    Conectar señales cuando la app está lista
    Llamar desde apps.py
    """
    pass

