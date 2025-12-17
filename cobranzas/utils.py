"""
Utilidades para detectar y gestionar cobranzas automáticamente
Integración entre ETL y módulo de Cobranzas
"""

from datetime import date, timedelta
from decimal import Decimal
from django.db.models import Q, Sum, Count, Avg
from polizas.models import Poliza
from .models import Cobranza


def detectar_pagos_pendientes(poliza=None, dias_desde_emision=30):
    """
    Detecta pólizas con pagos pendientes que no tienen cobranzas registradas.
    
    Retorna pólizas que:
    1. Están vigentes (fecha_inicio <= hoy <= fecha_vencimiento)
    2. Tienen monto_uf > 0
    3. No tienen cobranza registrada para el pago
    4. La póliza se emitió hace al menos X días (configurable)
    
    Args:
        poliza: Si se proporciona, solo verifica esta póliza
        dias_desde_emision: Días mínimos desde la emisión para crear cobranza
    
    Returns:
        QuerySet de Polizas con pagos pendientes
    """
    hoy = date.today()
    fecha_limite = hoy - timedelta(days=dias_desde_emision)
    
    # Base query: pólizas vigentes
    query = Poliza.objects.filter(
        fecha_inicio__lte=hoy,
        fecha_vencimiento__gte=hoy,
        monto_uf__gt=0
    )
    
    # Excluir pólizas que ya tienen cobranzas pagadas
    query = query.exclude(
        cobranzas__estado='PAGADA'
    )
    
    # Solo pólizas emitidas hace suficiente tiempo
    query = query.filter(
        fecha_inicio__lte=fecha_limite
    )
    
    # Si se proporciona una póliza específica, filtrar
    if poliza:
        query = query.filter(pk=poliza.pk)
    
    return query.distinct()


def detectar_pagos_vencidos():
    """
    Detecta pólizas vencidas sin pagar.
    
    Retorna pólizas que:
    1. Están vencidas (fecha_vencimiento < hoy)
    2. No tienen pago registrado
    3. No tienen cobranza pagada
    
    Returns:
        QuerySet de Polizas vencidas sin pagar
    """
    hoy = date.today()
    
    query = Poliza.objects.filter(
        fecha_vencimiento__lt=hoy,
        monto_uf__gt=0
    ).exclude(
        cobranzas__estado='PAGADA'
    )
    
    return query.distinct()


def detectar_cobranzas_en_riesgo():
    """
    Detecta cobranzas que requieren acción urgente.
    
    Retorna cobranzas que:
    1. Están vencidas hace más de 15 días
    2. No están pagadas
    3. Corresponden a clientes con histórico de atrasos
    
    Returns:
        QuerySet de Cobranzas en riesgo
    """
    hoy = date.today()
    fecha_riesgo = hoy - timedelta(days=15)
    
    # Cobranzas vencidas hace más de 15 días
    cobranzas_vencidas = Cobranza.objects.filter(
        fecha_vencimiento__lt=fecha_riesgo,
        estado__in=['PENDIENTE', 'EN_PROCESO']
    )
    
    # Con clientes con histórico de atrasos
    polizas_con_atrasos = Poliza.objects.filter(
        cobranzas__dias_atraso__gt=0
    ).values_list('cliente_id', flat=True).distinct()
    
    return cobranzas_vencidas.filter(
        poliza__cliente_id__in=polizas_con_atrasos
    ).distinct()


def crear_cobranza_desde_poliza(poliza, tipo_cobranza='PAGO_VIGENTE', campo_origen='', usuario=None):
    """
    Crea una cobranza para una póliza vigente con pago pendiente.
    
    Args:
        poliza: Instancia de Poliza
        tipo_cobranza: 'PAGO_VIGENTE', 'PAGO_VENCIDO', o 'RIESGO_FINANCIERO'
        campo_origen: Campo del Excel que indicó el pago pendiente
        usuario: Usuario que crea el registro
    
    Returns:
        Tupla (cobranza, created) - cobranza creada y flag de creación
    """
    hoy = date.today()
    
    # Fecha de vencimiento: 30 días después de la emisión (configurable según negocio)
    dias_plazo = 30
    fecha_vencimiento = poliza.fecha_inicio + timedelta(days=dias_plazo)
    
    # Crear cobranza
    cobranza, created = Cobranza.objects.get_or_create(
        poliza=poliza,
        tipo_cobranza=tipo_cobranza,
        estado='PENDIENTE',
        defaults={
            'monto_uf': poliza.monto_uf or Decimal('0'),
            'monto_pesos': None,  # Se calcula después con valor UF
            'fecha_emision': hoy,
            'fecha_vencimiento': fecha_vencimiento,
            'estado': 'PENDIENTE',
            'fuente_etl': True,
            'campo_pago_pendiente': campo_origen,
            'usuario_registro': usuario,
        }
    )
    
    return cobranza, created


def crear_cobranzas_desde_etl(polizas_data=None, usuario=None):
    """
    Crea cobranzas automáticamente desde datos del ETL.
    
    Procesa:
    1. Pólizas vigentes con pagos pendientes detectados en Excel
    2. Calcula qué tipo de cobranza corresponde
    3. Crea registros sin duplicados
    
    Args:
        polizas_data: QuerySet de Polizas procesadas del ETL
        usuario: Usuario que ejecuta el proceso
    
    Returns:
        Dict con estadísticas: {creadas: int, duplicadas: int, errores: int}
    """
    stats = {'creadas': 0, 'duplicadas': 0, 'errores': 0}
    
    if polizas_data is None:
        polizas_data = detectar_pagos_pendientes()
    
    for poliza in polizas_data:
        try:
            # Determinar tipo de cobranza
            hoy = date.today()
            if poliza.fecha_vencimiento < hoy:
                tipo = 'PAGO_VENCIDO'
            else:
                tipo = 'PAGO_VIGENTE'
            
            cobranza, created = crear_cobranza_desde_poliza(
                poliza=poliza,
                tipo_cobranza=tipo,
                campo_origen='DETECCION_ETL',
                usuario=usuario
            )
            
            if created:
                stats['creadas'] += 1
            else:
                stats['duplicadas'] += 1
        except Exception as e:
            stats['errores'] += 1
            print(f"Error creando cobranza para póliza {poliza.numero}: {str(e)}")
    
    return stats


def obtener_estadisticas_cobranzas():
    """
    Retorna estadísticas generales de cobranzas.
    
    Returns:
        Dict con estadísticas
    """
    hoy = date.today()
    
    stats = {
        'total_cobranzas': Cobranza.objects.count(),
        'pendientes': Cobranza.objects.filter(estado='PENDIENTE').count(),
        'en_proceso': Cobranza.objects.filter(estado='EN_PROCESO').count(),
        'pagadas': Cobranza.objects.filter(estado='PAGADA').count(),
        'vencidas': Cobranza.objects.filter(
            fecha_vencimiento__lt=hoy,
            estado__in=['PENDIENTE', 'EN_PROCESO']
        ).count(),
        'en_riesgo': Cobranza.objects.filter(
            tiene_alerta_financiera=True,
            estado__in=['PENDIENTE', 'EN_PROCESO']
        ).count(),
        'monto_total_pendiente': Cobranza.objects.filter(
            estado__in=['PENDIENTE', 'EN_PROCESO']
        ).aggregate(Sum('monto_uf'))['monto_uf__sum'] or Decimal('0'),
        'promedio_dias_atraso': Cobranza.objects.filter(
            estado__in=['PENDIENTE', 'EN_PROCESO'],
            dias_atraso__gt=0
        ).aggregate(Avg('dias_atraso'))['dias_atraso__avg'] or 0,
    }
    
    return stats


def obtener_cobranzas_por_cliente(cliente_id):
    """
    Retorna todas las cobranzas para un cliente específico.
    
    Args:
        cliente_id: ID del cliente
    
    Returns:
        QuerySet filtrado
    """
    return Cobranza.objects.filter(
        poliza__cliente_id=cliente_id
    ).order_by('-fecha_emision')


def marcar_como_pagada(cobranza_id, metodo_pago='', numero_documento=''):
    """
    Marca una cobranza como pagada.
    
    Args:
        cobranza_id: ID de la cobranza
        metodo_pago: Método de pago utilizado
        numero_documento: Número de transacción/cheque/etc
    
    Returns:
        Cobranza actualizada
    """
    cobranza = Cobranza.objects.get(pk=cobranza_id)
    cobranza.estado = 'PAGADA'
    cobranza.fecha_pago = date.today()
    cobranza.metodo_pago = metodo_pago
    cobranza.numero_documento = numero_documento
    cobranza.dias_atraso = 0
    cobranza.save()
    
    return cobranza


def generar_alerta_financiera(cobranza_id, razon):
    """
    Agrega una alerta financiera a una cobranza.
    
    Args:
        cobranza_id: ID de la cobranza
        razon: Motivo de la alerta (atraso recurrente, caída prima, etc)
    
    Returns:
        Cobranza actualizada
    """
    cobranza = Cobranza.objects.get(pk=cobranza_id)
    cobranza.tiene_alerta_financiera = True
    cobranza.razon_alerta = razon
    cobranza.tipo_cobranza = 'RIESGO_FINANCIERO'
    cobranza.save()
    
    return cobranza


def crear_cobranzas_lote(polizas, usuario=None):
    """
    Crea cobranzas automáticas para un lote de pólizas.
    Útil cuando se sube un archivo Excel con múltiples pólizas.
    
    Args:
        polizas: QuerySet o lista de Poliza
        usuario: Usuario que registra las cobranzas (opcional)
    
    Returns:
        Diccionario con estadísticas de creación
    """
    stats = {
        'creadas': 0,
        'existentes': 0,
        'errores': 0
    }
    
    with transaction.atomic():
        for poliza in polizas:
            cobranza = crear_cobranza_automatica(poliza, usuario)
            
            if cobranza:
                # Verificar si es nueva o existente
                # Si fue creada ahora, sera una nueva instancia
                if cobranza.id is not None:
                    stats['creadas'] += 1
            else:
                stats['errores'] += 1
    
    return stats


def generar_cobranzas_faltantes(usuario=None):
    """
    Genera cobranzas para todas las pólizas que no tengan cobranzas.
    Útil para sincronización inicial.
    
    Args:
        usuario: Usuario que registra las cobranzas (opcional)
    
    Returns:
        Diccionario con estadísticas
    """
    # Encontrar pólizas sin cobranzas
    polizas_sin_cobranza = Poliza.objects.filter(
        cobranzas__isnull=True
    ).distinct()
    
    return crear_cobranzas_lote(polizas_sin_cobranza, usuario)
