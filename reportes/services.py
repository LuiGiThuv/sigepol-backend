"""
Services para reportes automáticos inteligentes
PASO 9: Módulo de Reportes Automáticos Inteligentes
PASO 10: Integración con Alertas Automáticas
"""

from datetime import timedelta
from django.utils import timezone
from django.db.models import Sum, Count, Q
from polizas.models import Poliza
from alertas.utils import crear_alerta


def reporte_polizas_vencidas():
    """
    PASO 9.1: Reporte de Pólizas Vencidas
    PASO 10: Genera alertas automáticas para pólizas vencidas
    
    Retorna lista de pólizas con fecha de vencimiento menor a hoy.
    Incluye:
    - cliente
    - RUT
    - número de póliza
    - fecha vencimiento
    - días de atraso
    """
    hoy = timezone.now().date()
    polizas = Poliza.objects.filter(
        fecha_vencimiento__lt=hoy
    ).select_related('cliente').order_by('fecha_vencimiento')
    
    data = []
    for p in polizas:
        dias = (hoy - p.fecha_vencimiento).days
        
        # PASO 10.1: Generar alerta automática para póliza vencida
        if p.cliente:
            crear_alerta(
                tipo='vencimientos',
                titulo='PÓLIZA VENCIDA',
                mensaje=f'La póliza {p.numero} venció hace {dias} días',
                severidad='critical',
                poliza=p,
                cliente=p.cliente
            )
        
        data.append({
            "id": p.id,
            "cliente": p.cliente.nombre if p.cliente else "N/A",
            "rut": p.cliente.rut if p.cliente else "N/A",
            "poliza": p.numero,
            "vencimiento": str(p.fecha_vencimiento),
            "dias_atraso": dias,
            "estado": p.estado,
            "prima_uf": float(p.monto_uf) if p.monto_uf else 0,
        })
    
    return {
        "total": len(data),
        "polizas": data,
        "generado": str(timezone.now()),
    }


def reporte_polizas_por_expirar():
    """
    PASO 9.2: Reporte de Pólizas por Expirar (30 días o menos)
    PASO 10: Genera alertas automáticas para pólizas próximas a vencer
    
    Retorna pólizas que vencerán en los próximos 30 días.
    Incluye:
    - cliente
    - RUT
    - número de póliza
    - fecha vencimiento
    - días restantes
    - recomendación
    """
    hoy = timezone.now().date()
    limite = hoy + timedelta(days=30)

    polizas = Poliza.objects.filter(
        fecha_vencimiento__range=[hoy, limite],
        estado__in=['vigente', 'VIGENTE']
    ).select_related('cliente').order_by('fecha_vencimiento')

    data = []
    for p in polizas:
        dias = (p.fecha_vencimiento - hoy).days
        
        # Lógica de recomendación por días restantes
        if dias <= 5:
            recomendacion = "URGENTE: Contactar cliente para renovación inmediata"
            severidad_alerta = "critical"
        elif dias <= 15:
            recomendacion = "Contactar cliente para renovación"
            severidad_alerta = "warning"
        else:
            recomendacion = "Preparar comunicación de renovación"
            severidad_alerta = "info"
        
        # PASO 10.2: Generar alerta automática para póliza próxima a vencer
        if p.cliente:
            crear_alerta(
                tipo='vencimientos',
                titulo='EXPIRACIÓN PRÓXIMA',
                mensaje=f'La póliza {p.numero} vence en {dias} días',
                severidad=severidad_alerta,
                poliza=p,
                cliente=p.cliente
            )
        
        data.append({
            "id": p.id,
            "cliente": p.cliente.nombre if p.cliente else "N/A",
            "rut": p.cliente.rut if p.cliente else "N/A",
            "poliza": p.numero,
            "vencimiento": str(p.fecha_vencimiento),
            "dias_restantes": dias,
            "recomendacion": recomendacion,
            "prima_uf": float(p.monto_uf) if p.monto_uf else 0,
            "estado": p.estado,
        })
    
    return {
        "total": len(data),
        "polizas": data,
        "generado": str(timezone.now()),
    }


def reporte_produccion_mensual():
    """
    PASO 9.3: Reporte de Producción Mensual
    
    Retorna estadísticas de producción del mes actual.
    Incluye:
    - total primas netas
    - total primas brutas
    - cantidad de pólizas vigentes
    - variación respecto al mes anterior
    """
    hoy = timezone.now().date()
    mes_inicio = hoy.replace(day=1)
    
    # Mes anterior
    if mes_inicio.month == 1:
        mes_anterior_inicio = mes_inicio.replace(year=mes_inicio.year - 1, month=12)
    else:
        mes_anterior_inicio = mes_inicio.replace(month=mes_inicio.month - 1)
    
    # Cálculo mes actual
    polizas_mes = Poliza.objects.filter(
        fecha_inicio__gte=mes_inicio,
        fecha_inicio__lt=hoy.replace(day=28) + timedelta(days=4)  # Próximo mes
    )
    
    total_prima_mes = polizas_mes.aggregate(
        total=Sum('monto_uf')
    )["total"] or 0
    
    total_polizas_mes = polizas_mes.count()
    
    # Cálculo mes anterior
    if mes_anterior_inicio.month == 12:
        mes_anterior_fin = mes_anterior_inicio.replace(year=mes_anterior_inicio.year + 1, month=1)
    else:
        mes_anterior_fin = mes_anterior_inicio.replace(month=mes_anterior_inicio.month + 1)
    
    polizas_mes_anterior = Poliza.objects.filter(
        fecha_inicio__gte=mes_anterior_inicio,
        fecha_inicio__lt=mes_anterior_fin
    )
    
    total_prima_mes_anterior = polizas_mes_anterior.aggregate(
        total=Sum('monto_uf')
    )["total"] or 0
    
    total_polizas_mes_anterior = polizas_mes_anterior.count()
    
    # Variación
    variacion_prima = total_prima_mes - total_prima_mes_anterior
    variacion_polizas = total_polizas_mes - total_polizas_mes_anterior
    
    # Pólizas vigentes totales
    total_vigentes = Poliza.objects.filter(
        estado__in=['vigente', 'VIGENTE']
    ).count()
    
    return {
        "mes": mes_inicio.strftime("%Y-%m"),
        "mes_anterior": mes_anterior_inicio.strftime("%Y-%m"),
        "produccion_actual": {
            "total_prima_uf": float(total_prima_mes),
            "cantidad_polizas": total_polizas_mes,
            "prima_promedio": float(total_prima_mes / total_polizas_mes) if total_polizas_mes > 0 else 0,
        },
        "produccion_anterior": {
            "total_prima_uf": float(total_prima_mes_anterior),
            "cantidad_polizas": total_polizas_mes_anterior,
        },
        "variacion": {
            "prima_uf": float(variacion_prima),
            "prima_porcentaje": round(
                (variacion_prima / total_prima_mes_anterior * 100) if total_prima_mes_anterior > 0 else 0,
                2
            ),
            "polizas": variacion_polizas,
            "polizas_porcentaje": round(
                (variacion_polizas / total_polizas_mes_anterior * 100) if total_polizas_mes_anterior > 0 else 0,
                2
            ),
        },
        "cartera": {
            "total_vigentes": total_vigentes,
        },
        "generado": str(timezone.now()),
    }


def reporte_top_clientes():
    """
    PASO 9.4: Top Clientes por Producción
    
    Ranking de clientes con mayor producción.
    Incluye:
    - cliente
    - RUT
    - total UF
    - cantidad pólizas
    - % participación mensual
    """
    hoy = timezone.now().date()
    mes_inicio = hoy.replace(day=1)
    
    # Total de primas del mes para calcular participación
    total_prima_mes = Poliza.objects.filter(
        fecha_inicio__gte=mes_inicio
    ).aggregate(total=Sum('monto_uf'))["total"] or 0
    
    # Ranking de clientes
    ranking = (Poliza.objects
        .filter(fecha_inicio__gte=mes_inicio)
        .values("cliente__id", "cliente__nombre", "cliente__rut")
        .annotate(
            total_uf=Sum("monto_uf"),
            cantidad_polizas=Count("id")
        )
        .order_by("-total_uf")[:10]
    )

    data = []
    posicion = 1
    for r in ranking:
        participacion = (r["total_uf"] / total_prima_mes * 100) if total_prima_mes > 0 else 0
        
        data.append({
            "posicion": posicion,
            "cliente_id": r["cliente__id"],
            "cliente": r["cliente__nombre"],
            "rut": r["cliente__rut"],
            "total_uf": float(r["total_uf"]),
            "cantidad_polizas": r["cantidad_polizas"],
            "participacion_porcentaje": round(participacion, 2),
            "prima_promedio": round(float(r["total_uf"] / r["cantidad_polizas"]), 2),
        })
        posicion += 1
    
    return {
        "mes": mes_inicio.strftime("%Y-%m"),
        "total_ranking": len(data),
        "total_prima_mes": float(total_prima_mes),
        "clientes": data,
        "generado": str(timezone.now()),
    }
