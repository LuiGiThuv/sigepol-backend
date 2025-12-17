"""
Utilidades para crear y gestionar alertas
PASO 11: Integración con historial de alertas
"""
from django.utils import timezone
from django.db.models import Sum, Count
from datetime import timedelta
from .models import Alerta, AlertaHistorial
from polizas.models import Poliza


def calcular_fecha_limite(severidad):
    """
    Calcula la fecha límite para resolver una alerta basada en su severidad
    
    Args:
        severidad: Nivel de severidad ('info', 'warning', 'critical')
    
    Returns:
        datetime con la fecha límite calculada
    """
    ahora = timezone.now()
    
    # Definir plazos según severidad
    plazos = {
        'critical': 1,      # 1 día para críticas
        'warning': 3,       # 3 días para advertencias
        'info': 7,          # 7 días para informativas
    }
    
    dias = plazos.get(severidad, 7)
    return ahora + timedelta(days=dias)


def crear_alerta(tipo, mensaje, severidad='info', usuario=None, poliza=None, cliente=None, titulo=None):
    """
    Crea una alerta en el sistema
    PASO 11: Ahora también crea un registro en AlertaHistorial
    PASO 15: Verifica frescura de datos antes de crear alerta
    
    Args:
        tipo: Tipo de alerta (ver choices en modelo)
        mensaje: Mensaje descriptivo
        severidad: 'info', 'warning', o 'critical'
        usuario: Usuario que crea/dispara la alerta
        poliza: Póliza relacionada (opcional)
        cliente: Cliente relacionado (opcional)
        titulo: Título personalizado (si no se proporciona, usa tipo)
    
    Returns:
        Alerta creada o existente con confiable establecido según frescura de datos
    """
    if titulo is None:
        titulo = dict(Alerta.TIPO_CHOICES).get(tipo, tipo)
    
    # VERIFICACIÓN DE DUPLICADOS: No crear si ya existe una alerta idéntica activa
    # para la misma póliza, tipo y estado
    if poliza:
        alerta_existente = Alerta.objects.filter(
            tipo=tipo,
            poliza=poliza,
            estado__in=['PENDIENTE', 'LEIDA']
        ).first()
        
        if alerta_existente:
            # Retornar la alerta existente en lugar de crear duplicado
            return alerta_existente
    
    # PASO 15: Verificar frescura de datos (DataFreshness Validation)
    confiable = True
    razon_no_confiable = ""
    
    try:
        from importaciones.models import DataFreshness
        
        # Obtener cliente para verificar frescura
        cliente_rut = None
        if cliente and hasattr(cliente, 'rut'):
            cliente_rut = cliente.rut
        elif poliza and poliza.cliente and hasattr(poliza.cliente, 'rut'):
            cliente_rut = poliza.cliente.rut
        
        # Verificar frescura si tenemos cliente
        if cliente_rut:
            try:
                data_freshness = DataFreshness.objects.get(cliente=cliente_rut)
                
                # Considerar no confiable si datos tienen >30 días
                if not data_freshness.es_fresca(dias_limite=30):
                    confiable = False
                    estado = data_freshness.obtener_estado_frescura()
                    razon_no_confiable = f"Datos desactualizados hace {estado['dias_sin_actualizar']} días"
            except DataFreshness.DoesNotExist:
                # Cliente no tiene registro de frescura aún (es normal en primeras cargas)
                pass
    except Exception as e:
        # No fallar la creación de alerta si hay error en validación de frescura
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Error verificando frescura para alerta: {str(e)}")
    
    alerta = Alerta.objects.create(
        tipo=tipo,
        severidad=severidad,
        titulo=titulo,
        mensaje=mensaje,
        creada_por=usuario,
        poliza=poliza,
        cliente=cliente,
        estado='PENDIENTE',
        confiable=confiable,
        razon_no_confiable=razon_no_confiable,
        fecha_limite=calcular_fecha_limite(severidad),  # Calcular fecha límite según severidad
    )
    
    # PASO 16: Enviar notificación por correo
    try:
        from .notificaciones import enviar_notificacion_alerta
        enviar_notificacion_alerta(alerta)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Error enviando notificación de alerta {alerta.id}: {str(e)}")
    
    # PASO 11: Crear registro de historial automáticamente
    AlertaHistorial.objects.create(
        alerta=alerta,
        tipo=tipo,
        severidad=severidad,
        titulo=titulo,
        mensaje=mensaje,
        cliente=cliente,
        poliza=poliza,
        estado_final='nueva'
    )
    
    return alerta


def reglas_alertas_automaticas(upload=None):
    """
    Ejecuta reglas automáticas para detectar anomalías
    después del procesamiento de ETL
    
    Se ejecuta al final de process_upload() exitosamente
    """
    hoy = timezone.now().date()
    
    # 1. Producción del día muy baja (0 pólizas)
    produccion_hoy = Poliza.objects.filter(fecha_inicio=hoy).count()
    
    if produccion_hoy == 0:
        crear_alerta(
            tipo='produccion_baja',
            severidad='warning',
            titulo='Producción del día en cero',
            mensaje='La producción de pólizas del día es 0. Esto es inusual.'
        )
    
    # 2. Prima total anómala (total muy baja)
    total_polizas = Poliza.objects.count()
    
    if total_polizas == 0:
        crear_alerta(
            tipo='sistema',
            severidad='critical',
            titulo='Base de datos de pólizas vacía',
            mensaje='No hay pólizas registradas en el sistema.'
        )
    
    # 3. Detectar crecimiento negativo (comparar últimos 7 días vs 14 días)
    fecha_7_dias_atras = hoy - timezone.timedelta(days=7)
    fecha_14_dias_atras = hoy - timezone.timedelta(days=14)
    
    polizas_7_dias = Poliza.objects.filter(
        fecha_inicio__gte=fecha_7_dias_atras,
        fecha_inicio__lte=hoy
    ).count()
    
    polizas_14_dias = Poliza.objects.filter(
        fecha_inicio__gte=fecha_14_dias_atras,
        fecha_inicio__lt=fecha_7_dias_atras
    ).count()
    
    # Si hay decrecimiento mayor al 30%
    if polizas_14_dias > 0 and polizas_7_dias < (polizas_14_dias * 0.7):
        crear_alerta(
            tipo='crecimiento_negativo',
            severidad='warning',
            titulo='Decrecimiento de producción detectado',
            mensaje=f'Producción últimos 7 días: {polizas_7_dias} vs 14 días anteriores: {polizas_14_dias}. Decrecimiento > 30%.'
        )
    
    # 4. Clientes en riesgo (detectaría clusters de bajo rendimiento cuando ML esté activo)
    # Por ahora solo placeholder
    pass


def alertas_por_carga_etl(upload, errors, inserted_rows, updated_rows):
    """
    Genera alertas relacionadas a la carga ETL
    
    Args:
        upload: Objeto DataUpload
        errors: Lista/número de errores
        inserted_rows: Número de filas insertadas
        updated_rows: Número de filas actualizadas
    """
    archivo_nombre = upload.archivo.name.split('/')[-1] if upload.archivo else 'archivo.xlsx'
    usuario = upload.cargado_por
    
    # Si hay errores
    if errors and len(errors) > 0:
        crear_alerta(
            tipo='error_carga',
            severidad='warning',
            titulo=f'Errores en carga de {archivo_nombre}',
            mensaje=f'El archivo {archivo_nombre} tiene {len(errors)} filas con error.',
            usuario=usuario
        )
    
    # Si hay éxito (muchas filas procesadas)
    if inserted_rows > 0 or updated_rows > 0:
        crear_alerta(
            tipo='importaciones',
            severidad='info',
            titulo=f'Carga exitosa: {archivo_nombre}',
            mensaje=f'Archivo {archivo_nombre} procesado correctamente. '
                   f'{inserted_rows} nuevas pólizas, {updated_rows} actualizadas.',
            usuario=usuario
        )


def obtener_alertas_activas(filtro_severidad=None):
    """
    Obtiene alertas activas (PENDIENTE o LEIDA)
    
    Args:
        filtro_severidad: Filtrar por severidad ('info', 'warning', 'critical')
    
    Returns:
        QuerySet de alertas activas ordenadas por fecha
    """
    queryset = Alerta.objects.filter(
        estado__in=['PENDIENTE', 'LEIDA']
    ).order_by('-fecha_creacion')
    
    if filtro_severidad:
        queryset = queryset.filter(severidad=filtro_severidad)
    
    return queryset


def obtener_alertas_historial(limite=200, filtro_tipo=None):
    """
    Obtiene historial de alertas (todas)
    
    Args:
        limite: Número máximo de alertas a retornar
        filtro_tipo: Filtrar por tipo de alerta
    
    Returns:
        QuerySet de alertas ordenadas por fecha (descendente)
    """
    queryset = Alerta.objects.all().order_by('-fecha_creacion')
    
    if filtro_tipo:
        queryset = queryset.filter(tipo=filtro_tipo)
    
    return queryset[:limite]


def estadisticas_alertas():
    """
    Retorna estadísticas sobre alertas por estado
    
    Returns:
        Dict con conteos por estado (pendientes, leidas, resueltas, criticas, vencidas)
    """
    from django.utils import timezone
    from datetime import timedelta
    
    ahora = timezone.now()
    
    pendientes = Alerta.objects.filter(estado='PENDIENTE').count()
    leidas = Alerta.objects.filter(estado='LEIDA').count()
    resueltas = Alerta.objects.filter(estado='RESUELTA').count()
    
    return {
        'total': pendientes + leidas + resueltas,  # Solo alertas activas (excluye DESCARTADA)
        'pendientes': pendientes,
        'leidas': leidas,
        'resueltas': resueltas,
        'criticas': Alerta.objects.filter(severidad='critical', estado__in=['PENDIENTE', 'LEIDA']).count(),
        'vencidas': Alerta.objects.filter(fecha_limite__lt=ahora, estado__in=['PENDIENTE', 'LEIDA']).count(),
    }
