"""
PASO 14: Módulo de ML - Integración de Modelos de Machine Learning

Conecta resultados del modelo K-Means con el sistema de alertas.
Genera alertas predictivas automáticamente basadas en clusters y anomalías.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
import pandas as pd
import io
import traceback

from clientes.models import Cliente
from alertas.models import Alerta, AlertaHistorial
from usuarios.permissions import IsAdmin
from auditorias.utils import create_detailed_audit


class MLImportResultsView(APIView):
    """
    Endpoint para importar resultados del modelo ML (K-Means)
    
    Genera alertas predictivas automáticamente:
    - ML_RIESGO_PRODUCCION: Cluster 0 (producción baja)
    - ML_VARIACION_NEGATIVA: Caída > 20% en UF mensual
    - ML_ANOMALIA: Outliers detectados por Spark
    
    Uso:
    POST /api/ml/import/
    Content-Type: multipart/form-data
    
    Data: {
        "file": <CSV con resultados del modelo>
    }
    
    CSV esperado:
    cliente_rut,cliente_nombre,cluster,prima_total,variacion_mensual,anomalia
    16543287-4,JUAN PÉREZ,0,55.2,-32.1,false
    """
    
    parser_classes = [MultiPartParser]
    permission_classes = [IsAdmin]
    
    def post(self, request):
        """
        Recibe CSV con resultados del modelo ML y crea alertas
        """
        try:
            # Obtener archivo
            file = request.data.get("file")
            if not file:
                return Response(
                    {"error": "Archivo no proporcionado"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Leer CSV
            try:
                df = pd.read_csv(io.BytesIO(file.read()))
            except Exception as e:
                return Response(
                    {"error": f"Error al leer CSV: {str(e)}"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Validar columnas requeridas
            columnas_requeridas = ['cliente_rut', 'cluster', 'prima_total']
            columnas_faltantes = [c for c in columnas_requeridas if c not in df.columns]
            if columnas_faltantes:
                return Response(
                    {"error": f"Columnas faltantes: {columnas_faltantes}"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Procesar filas
            alertas_creadas = 0
            clientes_procesados = 0
            clientes_no_encontrados = 0
            errores = []
            
            for idx, row in df.iterrows():
                try:
                    rut = str(row.get('cliente_rut', '')).strip()
                    cluster = int(row.get('cluster', -1))
                    prima_total = float(row.get('prima_total', 0))
                    variacion_mensual = float(row.get('variacion_mensual', 0))
                    anomalia = str(row.get('anomalia', 'false')).lower() == 'true'
                    
                    # Buscar cliente
                    cliente = Cliente.objects.filter(rut=rut).first()
                    if not cliente:
                        clientes_no_encontrados += 1
                        continue
                    
                    clientes_procesados += 1
                    
                    # ALERTA 1: CLUSTER DE RIESGO (Producción Baja)
                    if cluster == 0:
                        alerta = Alerta.objects.create(
                            tipo='ML_RIESGO_PRODUCCION',
                            severidad='CRITICO',
                            titulo=f'ML: Riesgo de Producción - {cliente.nombre}',
                            mensaje=(
                                f"Cliente {cliente.nombre} ({cliente.rut}) detectado en cluster "
                                f"de baja producción. Prima total: {prima_total:.2f} UF. "
                                f"Requiere revisión urgente."
                            ),
                            cliente=cliente,
                            creada_por=request.user,
                            estado='PENDIENTE',
                            metadata={
                                'cluster': cluster,
                                'prima_total': prima_total,
                                'tipo_alerta': 'ML',
                                'modelo': 'K-Means'
                            }
                        )
                        alertas_creadas += 1
                        
                        # Registrar en auditoría
                        create_detailed_audit(
                            usuario=request.user,
                            accion='CREATE',
                            modulo='alertas',
                            modelo='Alerta',
                            descripcion=f"Alerta ML de riesgo de producción creada para {cliente.nombre}",
                            objeto_id=str(alerta.id),
                            datos_nuevos={'tipo': alerta.tipo, 'cliente_id': cliente.id}
                        )
                    
                    # ALERTA 2: VARIACIÓN NEGATIVA (Caída > 20%)
                    if variacion_mensual < -20:
                        alerta = Alerta.objects.create(
                            tipo='ML_VARIACION_NEGATIVA',
                            severidad='ADVERTENCIA',
                            titulo=f'ML: Variación Negativa - {cliente.nombre}',
                            mensaje=(
                                f"Cliente {cliente.nombre} ({cliente.rut}) presenta caída del "
                                f"{abs(variacion_mensual):.1f}% en producción mensual. "
                                f"Variación detectada: {variacion_mensual:.2f}%. "
                                f"Requiere seguimiento comercial."
                            ),
                            cliente=cliente,
                            creada_por=request.user,
                            estado='PENDIENTE',
                            metadata={
                                'cluster': cluster,
                                'prima_total': prima_total,
                                'variacion_mensual': variacion_mensual,
                                'tipo_alerta': 'ML',
                                'modelo': 'K-Means'
                            }
                        )
                        alertas_creadas += 1
                        
                        # Registrar en auditoría
                        create_detailed_audit(
                            usuario=request.user,
                            accion='CREATE',
                            modulo='alertas',
                            modelo='Alerta',
                            descripcion=f"Alerta ML de variación negativa creada para {cliente.nombre}",
                            objeto_id=str(alerta.id),
                            datos_nuevos={'tipo': alerta.tipo, 'cliente_id': cliente.id}
                        )
                    
                    # ALERTA 3: ANOMALÍA (Outliers Spark)
                    if anomalia:
                        alerta = Alerta.objects.create(
                            tipo='ML_ANOMALIA',
                            severidad='CRITICO',
                            titulo=f'ML: Anomalía Detectada - {cliente.nombre}',
                            mensaje=(
                                f"Spark/Big Data detectó una anomalía en los datos del cliente "
                                f"{cliente.nombre} ({cliente.rut}). Monto fuera de rango histórico. "
                                f"Prima actual: {prima_total:.2f} UF. Requiere validación."
                            ),
                            cliente=cliente,
                            creada_por=request.user,
                            estado='PENDIENTE',
                            metadata={
                                'cluster': cluster,
                                'prima_total': prima_total,
                                'anomalia_spark': True,
                                'tipo_alerta': 'ML',
                                'modelo': 'Spark/Big Data'
                            }
                        )
                        alertas_creadas += 1
                        
                        # Registrar en auditoría
                        create_detailed_audit(
                            usuario=request.user,
                            accion='CREATE',
                            modulo='alertas',
                            modelo='Alerta',
                            descripcion=f"Alerta ML de anomalía creada para {cliente.nombre}",
                            objeto_id=str(alerta.id),
                            datos_nuevos={'tipo': alerta.tipo, 'cliente_id': cliente.id}
                        )
                
                except Exception as e:
                    errores.append(f"Fila {idx}: {str(e)}")
                    continue
            
            # Registrar acción principal en auditoría
            create_detailed_audit(
                usuario=request.user,
                accion='CREATE',
                modulo='alertas',
                modelo='ML_Import',
                descripcion=(
                    f"Importación de resultados ML: {alertas_creadas} alertas creadas, "
                    f"{clientes_procesados} clientes procesados, "
                    f"{clientes_no_encontrados} clientes no encontrados"
                ),
                datos_nuevos={
                    'alertas_creadas': alertas_creadas,
                    'clientes_procesados': clientes_procesados,
                    'clientes_no_encontrados': clientes_no_encontrados,
                    'errores': len(errores)
                }
            )
            
            return Response({
                'status': 'success',
                'alertas_creadas': alertas_creadas,
                'clientes_procesados': clientes_procesados,
                'clientes_no_encontrados': clientes_no_encontrados,
                'errores_procesamiento': errores if errores else None,
                'mensaje': f'{alertas_creadas} alertas predictivas generadas automáticamente'
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            error_msg = f"Error en importación ML: {str(e)}\n{traceback.format_exc()}"
            return Response(
                {"error": error_msg},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class MLAlertsListView(APIView):
    """
    Endpoint para listar alertas generadas por ML
    
    Uso:
    GET /api/ml/alertas/
    GET /api/ml/alertas/?tipo=riesgo_produccion
    GET /api/ml/alertas/?estado=PENDIENTE
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        Lista alertas generadas por ML con filtros opcionales
        """
        # Filtrar alertas de tipo ML
        alertas = Alerta.objects.filter(
            tipo__startswith='ML_'
        ).order_by('-fecha_creacion')
        
        # Filtros opcionales
        tipo = request.query_params.get('tipo')
        if tipo:
            alertas = alertas.filter(tipo__icontains=tipo)
        
        estado = request.query_params.get('estado')
        if estado:
            alertas = alertas.filter(estado=estado)
        
        severidad = request.query_params.get('severidad')
        if severidad:
            alertas = alertas.filter(severidad=severidad)
        
        cliente_id = request.query_params.get('cliente_id')
        if cliente_id:
            alertas = alertas.filter(cliente_id=cliente_id)
        
        # Paginación
        limit = int(request.query_params.get('limit', 50))
        offset = int(request.query_params.get('offset', 0))
        
        total = alertas.count()
        alertas = alertas[offset:offset+limit]
        
        # Serializar
        data = [{
            'id': a.id,
            'tipo': a.get_tipo_display(),
            'severidad': a.severidad,
            'titulo': a.titulo,
            'mensaje': a.mensaje,
            'estado': a.estado,
            'cliente': {
                'id': a.cliente.id,
                'nombre': a.cliente.nombre,
                'rut': a.cliente.rut
            } if a.cliente else None,
            'fecha_creacion': a.fecha_creacion,
            'creada_por': a.creada_por.username if a.creada_por else None,
            'metadata': a.metadata
        } for a in alertas]
        
        return Response({
            'total': total,
            'limit': limit,
            'offset': offset,
            'results': data
        })


class MLAlertsStatsView(APIView):
    """
    Endpoint para estadísticas de alertas ML
    
    Uso:
    GET /api/ml/stats/
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        Retorna estadísticas de alertas ML
        """
        alertas_ml = Alerta.objects.filter(tipo__startswith='ML_')
        
        stats = {
            'total': alertas_ml.count(),
            'por_tipo': {},
            'por_severidad': {
                'CRITICO': alertas_ml.filter(severidad='CRITICO').count(),
                'ADVERTENCIA': alertas_ml.filter(severidad='ADVERTENCIA').count(),
                'INFO': alertas_ml.filter(severidad='INFO').count(),
            },
            'por_estado': {
                'PENDIENTE': alertas_ml.filter(estado='PENDIENTE').count(),
                'LEIDA': alertas_ml.filter(estado='LEIDA').count(),
                'RESUELTA': alertas_ml.filter(estado='RESUELTA').count(),
                'DESCARTADA': alertas_ml.filter(estado='DESCARTADA').count(),
            },
            'ultimas_24h': alertas_ml.filter(
                fecha_creacion__gte=timezone.now() - timezone.timedelta(hours=24)
            ).count(),
        }
        
        # Desglose por tipo
        for tipo_choice in ['ML_RIESGO_PRODUCCION', 'ML_VARIACION_NEGATIVA', 'ML_ANOMALIA']:
            count = alertas_ml.filter(tipo=tipo_choice).count()
            stats['por_tipo'][tipo_choice] = count
        
        return Response(stats)
