"""
Middleware para registrar logs de acceso a la API
"""
from .models import LogAcceso
from django.utils.decorators import decorator_from_middleware
from django.utils import timezone


class LogAccesoMiddleware:
    """
    Middleware que registra todos los accesos a la API
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Iniciar timer
        inicio = timezone.now()
        
        # Hacer la request
        response = self.get_response(request)
        
        # No registrar requests a recursos estáticos o admin
        if request.path.startswith('/static/') or request.path.startswith('/media/'):
            return response
        
        # Obtener IP del cliente
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', 'unknown')
        
        # Determinar resultado
        codigo = response.status_code
        if codigo >= 400:
            resultado = 'FALLIDO'
        else:
            resultado = 'EXITOSO'
        
        # Registrar log
        try:
            LogAcceso.objects.create(
                usuario=request.user if request.user.is_authenticated else None,
                ip_address=ip,
                endpoint=request.path,
                metodo=request.method,
                resultado=resultado,
                codigo_estado=codigo,
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
            )
        except Exception as e:
            # Si falla el logging, no bloquear la request
            pass
        
        return response
