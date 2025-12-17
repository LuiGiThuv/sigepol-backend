from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """
    Custom User Model con soporte para roles y permisos (RBAC)
    """
    ROLE_CHOICES = [
        ('admin', 'Administrador'),
        ('comercial', 'Usuario Comercial'),
        ('auditor', 'Auditor / Viewer'),
    ]
    
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='comercial',
        help_text='Rol del usuario para control de permisos'
    )
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"
    
    def is_admin(self):
        return self.role == 'admin'
    
    def is_comercial(self):
        return self.role in ['admin', 'comercial']
    
    def is_auditor(self):
        return self.role == 'auditor'
