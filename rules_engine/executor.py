"""
PASO 11: Executor del Motor de Reglas

Ejecuta las reglas de negocio registradas y captura resultados.
"""

import traceback
from datetime import timedelta
from django.utils import timezone
from django.db import transaction

from .models import Rule, RuleExecution
from .registry import register_rule, get_registered_rules
from polizas.models import Poliza
from clientes.models import Cliente
from alertas.utils import crear_alerta


# ==================== REGLAS DE NEGOCIO ====================

@register_rule("POLIZAS_POR_EXPIRAR")
def rule_polizas_por_expirar(rule_obj: Rule):
    """
    PASO 11.1: Alerta de Pólizas Próximas a Vencer
    
    Genera alertas para pólizas que vencen en el rango configurado.
    Parámetros:
    - dias: Número de días para considerar como "próximas a vencer" (default: 30)
    - severidad: Nivel de alerta (info/warning/critical) (default: warning)
    """
    dias = rule_obj.parametros.get("dias", 30)
    severidad = rule_obj.parametros.get("severidad", "warning")
    
    hoy = timezone.now().date()
    fecha_limite = hoy + timedelta(days=dias)
    
    # Buscar pólizas en rango
    polizas = Poliza.objects.filter(
        fecha_vencimiento__gte=hoy,
        fecha_vencimiento__lte=fecha_limite,
        estado__in=['VIGENTE', 'POR_RENOVAR']
    ).select_related('cliente')
    
    alertas_creadas = 0
    for poliza in polizas:
        dias_restantes = (poliza.fecha_vencimiento - hoy).days
        
        crear_alerta(
            tipo='vencimientos',
            titulo='PÓLIZA POR VENCER',
            mensaje=f'La póliza {poliza.numero} vence en {dias_restantes} días',
            severidad=severidad,
            poliza=poliza,
            cliente=poliza.cliente
        )
        alertas_creadas += 1
    
    return {
        "status": "exitosa",
        "alertas_creadas": alertas_creadas,
        "polizas_procesadas": polizas.count(),
        "rango_dias": f"0 a {dias}",
        "fecha_base": str(hoy),
        "fecha_limite": str(fecha_limite)
    }


@register_rule("CLIENTES_TOP_PRODUCCION")
def rule_clientes_top_produccion(rule_obj: Rule):
    """
    PASO 11.2: Detección de Clientes Top por Producción
    
    Identifica clientes con producción superior a un umbral.
    Parámetros:
    - min_uf: Mínimo en UF para considerar cliente top (default: 500)
    - generar_alerta: Si generar alerta o solo registrar (default: true)
    """
    min_uf = rule_obj.parametros.get("min_uf", 500)
    generar_alerta_flag = rule_obj.parametros.get("generar_alerta", True)
    
    # Agrupar por cliente
    clientes_data = {}
    polizas = Poliza.objects.filter(estado='VIGENTE').select_related('cliente')
    
    for poliza in polizas:
        if poliza.cliente and poliza.monto_uf:
            rut = poliza.cliente.rut
            if rut not in clientes_data:
                clientes_data[rut] = {
                    'cliente': poliza.cliente,
                    'total_uf': 0,
                    'polizas': 0
                }
            clientes_data[rut]['total_uf'] += poliza.monto_uf
            clientes_data[rut]['polizas'] += 1
    
    # Filtrar clientes top
    clientes_top = [
        data for data in clientes_data.values()
        if data['total_uf'] >= min_uf
    ]
    
    # Generar alertas si está configurado
    alertas_creadas = 0
    if generar_alerta_flag:
        for data in clientes_top:
            crear_alerta(
                tipo='cliente_top',
                titulo='CLIENTE TOP DETECTADO',
                mensaje=f"Cliente {data['cliente'].nombre} ({data['cliente'].rut}) con {data['total_uf']:.2f} UF en {data['polizas']} pólizas",
                severidad='info',
                cliente=data['cliente']
            )
            alertas_creadas += 1
    
    return {
        "status": "exitosa",
        "clientes_top_detectados": len(clientes_top),
        "alertas_creadas": alertas_creadas,
        "umbral_uf": min_uf,
        "detalles": [
            {
                "rut": data['cliente'].rut,
                "nombre": data['cliente'].nombre,
                "total_uf": data['total_uf'],
                "polizas_vigentes": data['polizas']
            }
            for data in clientes_top[:10]  # Top 10
        ]
    }


@register_rule("PRODUCCION_BAJA_DETECTADA")
def rule_produccion_baja_detectada(rule_obj: Rule):
    """
    PASO 11.3: Alerta de Producción Baja
    
    Detecta cuándo la producción diaria/semanal cae por debajo de un umbral.
    Parámetros:
    - dias_comparar: Días atrás para comparar (default: 7)
    - porcentaje_caida: % mínimo de caída para alertar (default: 30)
    """
    dias_comparar = rule_obj.parametros.get("dias_comparar", 7)
    porcentaje_caida = rule_obj.parametros.get("porcentaje_caida", 30)
    
    hoy = timezone.now().date()
    fecha_anterior = hoy - timedelta(days=dias_comparar)
    
    # Contar pólizas en período anterior
    polizas_anterior = Poliza.objects.filter(
        fecha_inicio__gte=fecha_anterior,
        fecha_inicio__lt=hoy - timedelta(days=dias_comparar-1)
    ).count()
    
    # Contar pólizas en período actual
    polizas_actual = Poliza.objects.filter(
        fecha_inicio__gte=hoy - timedelta(days=dias_comparar-1),
        fecha_inicio__lte=hoy
    ).count()
    
    # Calcular caída
    if polizas_anterior > 0:
        caida_porcentual = ((polizas_anterior - polizas_actual) / polizas_anterior) * 100
    else:
        caida_porcentual = 0
    
    alerta_generada = False
    if caida_porcentual >= porcentaje_caida:
        crear_alerta(
            tipo='produccion_baja',
            titulo='CAÍDA DE PRODUCCIÓN DETECTADA',
            mensaje=f'La producción cayó {caida_porcentual:.1f}% en los últimos {dias_comparar} días',
            severidad='critical'
        )
        alerta_generada = True
    
    return {
        "status": "exitosa",
        "produccion_anterior": polizas_anterior,
        "produccion_actual": polizas_actual,
        "caida_porcentual": round(caida_porcentual, 2),
        "alerta_generada": alerta_generada,
        "periodo_dias": dias_comparar,
        "umbral_caida": porcentaje_caida
    }


@register_rule("VIGENCIA_IRREGULAR_DETECTADA")
def rule_vigencia_irregular_detectada(rule_obj: Rule):
    """
    PASO 11.4: Detección de Vigencia Irregular
    
    Detecta clientes con patrones de vigencia anómala
    (muchas renovaciones, vencimientos sin renovación, etc.)
    Parámetros:
    - dias_analisis: Días a analizar hacia atrás (default: 90)
    - min_renovaciones: Mínimo de renovaciones en período (default: 3)
    """
    dias_analisis = rule_obj.parametros.get("dias_analisis", 90)
    min_renovaciones = rule_obj.parametros.get("min_renovaciones", 3)
    
    fecha_limite = timezone.now().date() - timedelta(days=dias_analisis)
    
    # Contar renovaciones por cliente
    clientes_anómalos = {}
    
    polizas = Poliza.objects.filter(
        fecha_inicio__gte=fecha_limite,
        cliente__isnull=False
    ).select_related('cliente').values('cliente').distinct()
    
    for cliente_data in polizas:
        cliente_id = cliente_data['cliente']
        if cliente_id:
            renovaciones = Poliza.objects.filter(
                cliente_id=cliente_id,
                fecha_inicio__gte=fecha_limite
            ).count()
            
            if renovaciones >= min_renovaciones:
                cliente = Cliente.objects.get(id=cliente_id)
                clientes_anómalos[cliente.rut] = {
                    'cliente': cliente,
                    'renovaciones': renovaciones
                }
    
    # Generar alertas
    alertas_creadas = 0
    for rut, data in clientes_anómalos.items():
        crear_alerta(
            tipo='vigencia_irregular',
            titulo='VIGENCIA IRREGULAR DETECTADA',
            mensaje=f"Cliente {data['cliente'].nombre} tiene {data['renovaciones']} renovaciones en {dias_analisis} días",
            severidad='warning',
            cliente=data['cliente']
        )
        alertas_creadas += 1
    
    return {
        "status": "exitosa",
        "clientes_detectados": len(clientes_anómalos),
        "alertas_creadas": alertas_creadas,
        "dias_analisis": dias_analisis,
        "renovaciones_minimo": min_renovaciones
    }


@register_rule("SANIDAD_DATOS")
def rule_sanidad_datos(rule_obj: Rule):
    """
    PASO 11.5: Verificación de Sanidad de Datos
    
    Detecta registros incompletos o inconsistentes.
    Parámetros:
    - alertar_campos_vacios: Alertar por campos vacíos (default: true)
    - alertar_fechas_inconsistentes: Alertar por fechas inválidas (default: true)
    """
    alertar_vacios = rule_obj.parametros.get("alertar_campos_vacios", True)
    alertar_fechas = rule_obj.parametros.get("alertar_fechas_inconsistentes", True)
    
    problemas = []
    
    # Verificar campos vacíos en pólizas
    if alertar_vacios:
        polizas_sin_cliente = Poliza.objects.filter(cliente__isnull=True).count()
        polizas_sin_fecha_inicio = Poliza.objects.filter(fecha_inicio__isnull=True).count()
        
        if polizas_sin_cliente > 0:
            problemas.append(f"{polizas_sin_cliente} pólizas sin cliente")
        if polizas_sin_fecha_inicio > 0:
            problemas.append(f"{polizas_sin_fecha_inicio} pólizas sin fecha de inicio")
    
    # Verificar inconsistencias de fechas
    if alertar_fechas:
        polizas_inconsistentes = Poliza.objects.filter(
            fecha_vencimiento__lt=timezone.now().date()
        ).exclude(
            estado__in=['VENCIDA', 'CANCELADA']
        ).count()
        
        if polizas_inconsistentes > 0:
            problemas.append(f"{polizas_inconsistentes} pólizas con vencimiento pasado pero estado incorrecto")
    
    # Generar alerta si hay problemas
    if problemas:
        crear_alerta(
            tipo='sanidad_datos',
            titulo='PROBLEMAS DE SANIDAD DE DATOS',
            mensaje='; '.join(problemas),
            severidad='warning'
        )
    
    return {
        "status": "exitosa",
        "problemas_encontrados": len(problemas),
        "detalles": problemas,
        "accion": "Alerta generada" if problemas else "Sin problemas"
    }


# ==================== EJECUTOR ====================

def ejecutar_motor_reglas(solo_activas=True):
    """
    PASO 11: Ejecuta todas las reglas registradas
    
    Retorna diccionario con resultados de cada regla.
    """
    
    if solo_activas:
        reglas = Rule.objects.filter(activa=True).order_by('orden_ejecucion')
    else:
        reglas = Rule.objects.all().order_by('orden_ejecucion')
    
    resultados = {
        "ejecutadas": 0,
        "exitosas": 0,
        "fallidas": 0,
        "reglas": {}
    }
    
    for regla in reglas:
        # Verificar si la regla está registrada
        if regla.codigo not in get_registered_rules():
            resultados["reglas"][regla.codigo] = {
                "status": "error",
                "mensaje": f"Regla {regla.codigo} no está registrada"
            }
            continue
        
        # Ejecutar regla
        try:
            with transaction.atomic():
                inicio = timezone.now()
                func_regla = get_registered_rules()[regla.codigo]
                
                # Ejecutar la función
                resultado = func_regla(regla)
                
                fin = timezone.now()
                duracion = (fin - inicio).total_seconds()
                
                # Guardar resultado
                regla.ultima_ejecucion = fin
                regla.proxima_ejecucion = fin + timedelta(days=1)
                regla.ultimo_resultado = resultado
                regla.ultimo_error = None
                regla.total_ejecuciones += 1
                regla.ejecuciones_exitosas += 1
                regla.save()
                
                # Registrar ejecución
                RuleExecution.objects.create(
                    regla=regla,
                    estado='exitosa',
                    resultado=resultado,
                    duracion_segundos=duracion,
                    parametros_utilizados=regla.parametros
                )
                
                resultados["exitosas"] += 1
                resultados["reglas"][regla.codigo] = {
                    "status": "exitosa",
                    "resultado": resultado,
                    "duracion_segundos": duracion
                }
        
        except Exception as e:
            fin = timezone.now()
            error_msg = str(e)
            error_tb = traceback.format_exc()
            
            # Guardar error
            regla.ultimo_error = error_msg
            regla.total_ejecuciones += 1
            regla.ejecuciones_fallidas += 1
            regla.save()
            
            # Registrar ejecución fallida
            RuleExecution.objects.create(
                regla=regla,
                estado='error',
                error_mensaje=error_msg,
                error_traceback=error_tb,
                duracion_segundos=(fin - inicio).total_seconds() if 'inicio' in locals() else None,
                parametros_utilizados=regla.parametros
            )
            
            resultados["fallidas"] += 1
            resultados["reglas"][regla.codigo] = {
                "status": "error",
                "error": error_msg
            }
        
        resultados["ejecutadas"] += 1
    
    return resultados


def ejecutar_regla_individual(codigo_regla):
    """
    Ejecuta una sola regla específica.
    """
    
    try:
        regla = Rule.objects.get(codigo=codigo_regla)
    except Rule.DoesNotExist:
        return {
            "status": "error",
            "mensaje": f"Regla {codigo_regla} no encontrada"
        }
    
    if codigo_regla not in get_registered_rules():
        return {
            "status": "error",
            "mensaje": f"Regla {codigo_regla} no está registrada"
        }
    
    try:
        with transaction.atomic():
            inicio = timezone.now()
            func_regla = get_registered_rules()[codigo_regla]
            resultado = func_regla(regla)
            fin = timezone.now()
            duracion = (fin - inicio).total_seconds()
            
            regla.ultima_ejecucion = fin
            regla.ultimo_resultado = resultado
            regla.ultimo_error = None
            regla.total_ejecuciones += 1
            regla.ejecuciones_exitosas += 1
            regla.save()
            
            RuleExecution.objects.create(
                regla=regla,
                estado='exitosa',
                resultado=resultado,
                duracion_segundos=duracion,
                parametros_utilizados=regla.parametros
            )
            
            return {
                "status": "exitosa",
                "regla": codigo_regla,
                "resultado": resultado,
                "duracion_segundos": duracion
            }
    
    except Exception as e:
        fin = timezone.now()
        error_msg = str(e)
        error_tb = traceback.format_exc()
        
        regla.ultimo_error = error_msg
        regla.total_ejecuciones += 1
        regla.ejecuciones_fallidas += 1
        regla.save()
        
        RuleExecution.objects.create(
            regla=regla,
            estado='error',
            error_mensaje=error_msg,
            error_traceback=error_tb,
            duracion_segundos=(fin - inicio).total_seconds(),
            parametros_utilizados=regla.parametros
        )
        
        return {
            "status": "error",
            "regla": codigo_regla,
            "error": error_msg
        }
