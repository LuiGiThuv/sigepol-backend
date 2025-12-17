"""
Servicio de notificaciones por correo para alertas
PASO 16: Sistema de notificaciones por email
"""
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib.auth import get_user_model
from .models import Alerta, PreferenciaNotificacionAlerta

User = get_user_model()


def enviar_notificacion_alerta(alerta):
    """
    Envía notificación por correo de una nueva alerta crítica
    
    Args:
        alerta: Instancia de Alerta a notificar
    
    Returns:
        bool: True si se envió exitosamente
    """
    if not settings.ALERTAS_EMAIL_CONFIG.get('enabled', False):
        return False
    
    # Verificar severidad
    config = settings.ALERTAS_EMAIL_CONFIG
    if alerta.severidad == 'critical' and not config.get('enviar_criticas', True):
        return False
    if alerta.severidad == 'warning' and not config.get('enviar_advertencias', True):
        return False
    if alerta.severidad == 'info' and not config.get('enviar_info', False):
        return False
    
    # Construir lista de destinatarios
    destinatarios = list(config.get('destinatarios_siempre', []))
    
    # Agregar usuarios con preferencias de notificación
    for prefs in PreferenciaNotificacionAlerta.objects.filter(recibir_emails=True):
        if prefs.debe_notificar(alerta.severidad, alerta.tipo):
            if prefs.usuario.email and prefs.usuario.email not in destinatarios:
                destinatarios.append(prefs.usuario.email)
    
    if not destinatarios:
        return False
    
    # Construir contenido del email
    contexto = {
        'alerta': alerta,
        'titulo': alerta.titulo,
        'mensaje': alerta.mensaje,
        'tipo': dict(Alerta.TIPO_CHOICES).get(alerta.tipo, alerta.tipo),
        'severidad': dict(Alerta.SEVERIDAD_CHOICES).get(alerta.severidad, alerta.severidad),
        'poliza': alerta.poliza,
        'cliente': alerta.cliente,
        'fecha_creacion': alerta.fecha_creacion.strftime('%d/%m/%Y %H:%M:%S'),
        'fecha_limite': alerta.fecha_limite.strftime('%d/%m/%Y %H:%M:%S') if alerta.fecha_limite else 'Sin límite',
        'url_dashboard': f'{settings.FRONTEND_URL}/alertas/{alerta.id}' if hasattr(settings, 'FRONTEND_URL') else '#',
    }
    
    # Determinar color según severidad
    color_severidad = {
        'critical': '#DC2626',  # Rojo
        'warning': '#F59E0B',   # Naranja
        'info': '#3B82F6',      # Azul
    }
    contexto['color_severidad'] = color_severidad.get(alerta.severidad, '#6B7280')
    
    # Renderizar template (usar template inline si no existe archivo)
    asunto = f"🚨 [{alerta.get_severidad_display()}] {alerta.titulo}"
    
    # HTML del email
    html_content = generar_html_email(contexto)
    texto_content = f"""
    {alerta.titulo}
    
    Tipo: {contexto['tipo']}
    Severidad: {contexto['severidad']}
    Fecha: {contexto['fecha_creacion']}
    
    {alerta.mensaje}
    
    {"Póliza: " + alerta.poliza.numero if alerta.poliza else ""}
    {"Cliente: " + str(alerta.cliente) if alerta.cliente else ""}
    """
    
    try:
        send_mail(
            subject=asunto,
            message=texto_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=destinatarios,
            html_message=html_content,
            fail_silently=False,
        )
        return True
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error enviando notificación de alerta {alerta.id}: {str(e)}")
        return False


def generar_html_email(contexto):
    """
    Genera el HTML del email de notificación
    
    Args:
        contexto: Dict con datos de la alerta
    
    Returns:
        str: HTML del email
    """
    alerta = contexto['alerta']
    
    emoji_severidad = {
        'critical': '🔴',
        'warning': '🟠',
        'info': '🔵',
    }
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                line-height: 1.6;
                color: #333;
            }}
            .container {{
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f9fafb;
            }}
            .header {{
                background: linear-gradient(135deg, {contexto['color_severidad']} 0%, #1f2937 100%);
                color: white;
                padding: 30px;
                border-radius: 8px 8px 0 0;
                text-align: center;
            }}
            .header h1 {{
                margin: 0;
                font-size: 24px;
                font-weight: bold;
            }}
            .content {{
                background: white;
                padding: 30px;
                border: 1px solid #e5e7eb;
                border-radius: 0 0 8px 8px;
            }}
            .alerta-box {{
                background-color: #f3f4f6;
                border-left: 4px solid {contexto['color_severidad']};
                padding: 15px;
                margin: 20px 0;
                border-radius: 4px;
            }}
            .field {{
                margin: 15px 0;
            }}
            .field-label {{
                font-weight: bold;
                color: {contexto['color_severidad']};
                margin-bottom: 5px;
            }}
            .field-value {{
                color: #374151;
            }}
            .mensaje {{
                background-color: #f9fafb;
                padding: 15px;
                border-radius: 4px;
                margin: 20px 0;
                border-left: 3px solid {contexto['color_severidad']};
            }}
            .footer {{
                text-align: center;
                padding: 20px;
                color: #6b7280;
                font-size: 12px;
                border-top: 1px solid #e5e7eb;
                margin-top: 20px;
            }}
            .button {{
                display: inline-block;
                background-color: {contexto['color_severidad']};
                color: white;
                padding: 12px 30px;
                text-decoration: none;
                border-radius: 4px;
                margin-top: 20px;
            }}
            .button:hover {{
                opacity: 0.9;
            }}
            .info-tabla {{
                width: 100%;
                border-collapse: collapse;
                margin: 15px 0;
            }}
            .info-tabla td {{
                padding: 10px;
                border-bottom: 1px solid #e5e7eb;
            }}
            .info-tabla td:first-child {{
                font-weight: bold;
                width: 150px;
                color: {contexto['color_severidad']};
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>{emoji_severidad.get(alerta.severidad, '⚠️')} {contexto['titulo']}</h1>
                <p style="margin: 10px 0 0 0;">{contexto['tipo']}</p>
            </div>
            
            <div class="content">
                <div class="alerta-box">
                    <table class="info-tabla">
                        <tr>
                            <td>Tipo de Alerta:</td>
                            <td>{contexto['tipo']}</td>
                        </tr>
                        <tr>
                            <td>Severidad:</td>
                            <td>{emoji_severidad.get(alerta.severidad, '⚠️')} {contexto['severidad']}</td>
                        </tr>
                        <tr>
                            <td>Fecha Creación:</td>
                            <td>{contexto['fecha_creacion']}</td>
                        </tr>
                        <tr>
                            <td>Fecha Límite:</td>
                            <td>{contexto['fecha_limite']}</td>
                        </tr>
                        {"<tr><td>Póliza:</td><td>" + str(contexto['poliza']) + "</td></tr>" if contexto['poliza'] else ""}
                        {"<tr><td>Cliente:</td><td>" + str(contexto['cliente']) + "</td></tr>" if contexto['cliente'] else ""}
                    </table>
                </div>
                
                <div class="mensaje">
                    <strong>Detalles:</strong><br><br>
                    {contexto['mensaje']}
                </div>
                
                <center>
                    <a href="{contexto['url_dashboard']}" class="button">Ver en SIGEPOL</a>
                </center>
            </div>
            
            <div class="footer">
                <p>Este es un correo automático de SIGEPOL.</p>
                <p>Por favor no responda a este correo.</p>
                <p>&copy; 2025 SIGEPOL - Sistema de Gestión de Pólizas</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html


def enviar_resumen_alertas_diario():
    """
    Envía un resumen diario de alertas a usuarios suscritos
    Útil para ejecutar con un task scheduler
    """
    from django.utils import timezone
    from datetime import timedelta
    
    hoy = timezone.now()
    hace_24h = hoy - timedelta(hours=24)
    
    # Alertas creadas en las últimas 24 horas
    alertas_hoy = Alerta.objects.filter(
        fecha_creacion__gte=hace_24h,
        estado__in=['PENDIENTE', 'LEIDA']
    ).order_by('-severidad', '-fecha_creacion')
    
    if not alertas_hoy.exists():
        return False
    
    # Enviar a usuarios con preferencia de resumen diario
    for prefs in PreferenciaNotificacionAlerta.objects.filter(
        recibir_emails=True,
        frecuencia='diaria'
    ):
        if not prefs.usuario.email:
            continue
        
        # Filtrar alertas según preferencias del usuario
        alertas_usuario = [a for a in alertas_hoy if prefs.debe_notificar(a.severidad, a.tipo)]
        
        if alertas_usuario:
            enviar_resumen_email(prefs.usuario, alertas_usuario)
    
    return True


def enviar_resumen_email(usuario, alertas):
    """
    Envía un email de resumen de alertas
    
    Args:
        usuario: Usuario que recibe el resumen
        alertas: List de alertas a incluir en resumen
    """
    asunto = f"📊 Resumen de Alertas SIGEPOL - {alertas[0].fecha_creacion.strftime('%d/%m/%Y')}"
    
    # Agrupar por severidad
    criticas = [a for a in alertas if a.severidad == 'critical']
    advertencias = [a for a in alertas if a.severidad == 'warning']
    info = [a for a in alertas if a.severidad == 'info']
    
    # Construir tabla
    filas_html = ""
    for alerta in alertas:
        emoji = {'critical': '🔴', 'warning': '🟠', 'info': '🔵'}.get(alerta.severidad, '⚠️')
        filas_html += f"""
        <tr style="border-bottom: 1px solid #e5e7eb;">
            <td style="padding: 10px;">{emoji}</td>
            <td style="padding: 10px;"><strong>{alerta.titulo}</strong></td>
            <td style="padding: 10px;">{alerta.get_tipo_display()}</td>
            <td style="padding: 10px; text-align: right;">{alerta.fecha_creacion.strftime('%H:%M:%S')}</td>
        </tr>
        """
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: #1f2937; color: white; padding: 20px; border-radius: 8px; text-align: center; }}
            .content {{ background: white; padding: 20px; margin-top: 20px; }}
            .stats {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin: 20px 0; }}
            .stat-box {{ background: #f3f4f6; padding: 15px; border-radius: 4px; text-align: center; }}
            .stat-box strong {{ color: #1f2937; font-size: 20px; }}
            table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
            th {{ background: #f9fafb; padding: 10px; text-align: left; border-bottom: 2px solid #e5e7eb; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>📊 Resumen de Alertas SIGEPOL</h2>
                <p>{alertas[0].fecha_creacion.strftime('%d de %B de %Y')}</p>
            </div>
            
            <div class="content">
                <p>Hola <strong>{usuario.first_name or usuario.username}</strong>,</p>
                <p>A continuación se muestra el resumen de alertas generadas en las últimas 24 horas:</p>
                
                <div class="stats">
                    <div class="stat-box">
                        <strong style="color: #DC2626;">{len(criticas)}</strong>
                        <p>Críticas</p>
                    </div>
                    <div class="stat-box">
                        <strong style="color: #F59E0B;">{len(advertencias)}</strong>
                        <p>Advertencias</p>
                    </div>
                    <div class="stat-box">
                        <strong style="color: #3B82F6;">{len(info)}</strong>
                        <p>Informativas</p>
                    </div>
                </div>
                
                <table>
                    <thead>
                        <tr>
                            <th>Severidad</th>
                            <th>Título</th>
                            <th>Tipo</th>
                            <th>Hora</th>
                        </tr>
                    </thead>
                    <tbody>
                        {filas_html}
                    </tbody>
                </table>
                
                <p style="color: #6b7280; font-size: 12px; margin-top: 30px;">
                    Este es un correo automático de SIGEPOL. Por favor no responda a este correo.
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    
    try:
        send_mail(
            subject=asunto,
            message="Ver en HTML",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[usuario.email],
            html_message=html_content,
            fail_silently=False,
        )
        return True
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error enviando resumen a {usuario.email}: {str(e)}")
        return False
