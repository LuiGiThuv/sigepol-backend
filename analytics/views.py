"""
Views para API de análisis ML
Endpoints para predicción de clusters y estadísticas
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
import logging
from .services import AnalizadorPolizas, predictor, mapear_riesgo_individual
from .ml.predictor import FEATURES

logger = logging.getLogger(__name__)

class StatusMLView(APIView):
    """
    GET /api/analytics/status/
    Estado de disponibilidad de modelos ML
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Retorna estado de los modelos ML"""
        
        try:
            disponible = predictor.esta_disponible()
            
            return Response({
                'modelos_disponibles': disponible,
                'modelo_path': 'analytics/ml/kmeans_sigepol.pkl',
                'scaler_path': 'analytics/ml/scaler_sigepol.pkl',
                'features': FEATURES,
                'mensaje': 'Modelos listos para demo' if disponible else 'Modelos ML no disponibles en esta demo (requieren entrenamiento)'
            })
        except Exception as e:
            logger.error(f"Error verificando estado ML: {e}")
            return Response({
                'modelos_disponibles': False,
                'error': str(e),
                'mensaje': 'Error al cargar modelos ML'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PredictarClustersView(APIView):
    """
    POST /api/analytics/predecir-clusters/
    Predice clusters para todas las pólizas
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Ejecuta predicción de clusters"""
        
        if not predictor.esta_disponible():
            return Response({
                'error': 'Modelos ML no disponibles',
                'detalle': 'Debe entrenar primero los modelos en Google Colab'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            logger.info(f"Usuario {request.user} solicita predicción de clusters")
            
            # Construir DataFrame
            df = AnalizadorPolizas.construir_dataframe()
            logger.info(f"DataFrame construido: {len(df)} pólizas")
            
            # Predecir
            df_predicho = predictor.predecir(df)
            
            # Actualizar BD
            AnalizadorPolizas.actualizar_clusters_bd(df_predicho)
            
            # Obtener estadísticas
            stats = AnalizadorPolizas.obtener_estadisticas_clusters(df_predicho)
            
            return Response({
                'exito': True,
                'pólizas_procesadas': len(df_predicho),
                'clusters_identificados': int(df_predicho['cluster_predicho'].nunique()),
                'estadisticas_por_cluster': stats,
                'columnas_predichas': ['cluster_predicho', 'distancia_cluster']
            })
        
        except Exception as e:
            logger.error(f"Error en predicción: {e}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ClusterStatsView(APIView):
    """
    GET /api/analytics/cluster-stats/
    Obtiene estadísticas de clusters
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Retorna estadísticas de clusters"""
        
        try:
            # Construir DataFrame
            df = AnalizadorPolizas.construir_dataframe()
            
            # Si hay clusters predichos
            if predictor.esta_disponible():
                df_predicho = predictor.predecir(df)
                stats = AnalizadorPolizas.obtener_estadisticas_clusters(df_predicho)
                
                return Response({
                    'tipo': 'PREDICHO',
                    'clusters': stats,
                    'total_polizas': len(df_predicho)
                })
            
            else:
                # Usar clusters históricos si existen
                df['cluster'] = df['CLUSTER_ANTERIOR']
                
                stats = []
                for cluster_id in sorted(df[df['cluster'] >= 0]['cluster'].unique()):
                    cluster_data = df[df['cluster'] == cluster_id]
                    stats.append({
                        'cluster': int(cluster_id),
                        'cantidad_polizas': len(cluster_data),
                        'porcentaje': round(len(cluster_data) / len(df) * 100, 2)
                    })
                
                return Response({
                    'tipo': 'HISTÓRICO',
                    'clusters': stats,
                    'total_polizas': len(df),
                    'nota': 'Clusters históricos. Ejecutar predicción para actualizar.'
                })
        
        except Exception as e:
            logger.error(f"Error obteniendo stats: {e}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PredictarIndividualView(APIView):
    """
    POST /api/analytics/predecir-individual/
    Predice cluster para una póliza individual
    
    Body:
    {
        "numero_poliza": "X-P-125623",
        "monto_uf": 14.32,
        "dias_vigencia": 365,
        ...
    }
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Predice cluster para una póliza individual"""
        
        if not predictor.esta_disponible():
            return Response({
                'error': 'Modelos no disponibles'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            datos = request.data
            
            # Validar features mínimas
            features_requeridas = ['monto_uf', 'dias_vigencia', 'total_cobranzas']
            for feature in features_requeridas:
                if feature not in datos:
                    return Response({
                        'error': f'Falta feature: {feature}'
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            # Normalizar nombres a uppercase
            datos_normalized = {k.upper(): v for k, v in datos.items()}
            
            # Predecir
            resultado = predictor.predecir_individual(datos_normalized)
            
            return Response({
                'numero_poliza': datos.get('numero_poliza', 'N/A'),
                'cluster_predicho': resultado['cluster'],
                'distancia_cluster': round(resultado['distancia'], 4),
                'features_utilizadas': FEATURES
            })
        
        except Exception as e:
            logger.error(f"Error en predicción individual: {e}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ReporteLimpiezaView(APIView):
    """
    GET /api/analytics/reporte-limpieza/
    Reporta pólizas que necesitan limpieza
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Retorna reporte de pólizas con issues"""
        
        try:
            df = AnalizadorPolizas.construir_dataframe()
            
            issues = {
                'sin_cobranzas': len(df[df['TOTAL_COBRANZAS'] == 0]),
                'sin_vigencia': len(df[df['DIAS_VIGENCIA'] == 0]),
                'datos_no_confiables': len(df[df['DATOS_CONFIABLES'] == 0]),
                'sin_cliente': len(df[df['CLIENTE_NOMBRE'] == 'DESCONOCIDO']),
                'alertas_criticas': int(df['ALERTAS_CRITICAS'].sum()),
                'total_polizas': len(df)
            }
            
            return Response({
                'issues': issues,
                'porcentaje_limpios': round((issues['total_polizas'] - issues['datos_no_confiables']) / issues['total_polizas'] * 100, 2)
            })
        
        except Exception as e:
            logger.error(f"Error en reporte: {e}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ClustersPredictosView(APIView):
    """
    GET /api/analytics/clusters/
    Retorna lista de pólizas con clusters predichos y nivel de riesgo
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Retorna pólizas con clusters y riesgo (PASOS 4-6)"""
        
        try:
            logger.info(f"Usuario {request.user} solicita clusters")
            
            # PASO 1-2: Construir DataFrame
            df = AnalizadorPolizas.construir_dataframe()
            
            # PASO 3: Si modelos disponibles, predecir
            if predictor.esta_disponible():
                df_predicho = predictor.predecir(df)
                df['cluster'] = df_predicho['cluster_predicho'].astype(int)
                df['distancia_cluster'] = df_predicho['distancia_cluster'].round(3)
            else:
                df['cluster'] = df['CLUSTER_ANTERIOR'].astype(int)
                df['distancia_cluster'] = None
            
            # PASO 6: Mapear a nivel de riesgo (regla de negocio)
            df['nivel_riesgo'] = df.apply(
                lambda row: mapear_riesgo_individual(
                    int(row['cluster']),
                    row['TASA_MORA'],
                    row['TOTAL_ALERTAS'],
                    row['COBRANZAS_PENDIENTES']
                ),
                axis=1
            )
            
            # Seleccionar columnas importantes
            resultado = df[[
                'NUMERO_POLIZA',
                'CLIENTE_NOMBRE',
                'MONTO_UF',
                'ESTADO',
                'TOTAL_COBRANZAS',
                'TOTAL_ALERTAS',
                'cluster',
                'nivel_riesgo',
                'distancia_cluster',
                'TASA_MORA'
            ]].copy()
            
            resultado['MONTO_UF'] = resultado['MONTO_UF'].round(2)
            resultado['TASA_MORA'] = resultado['TASA_MORA'].round(3)
            
            # Normalizar nombres
            data_list = []
            for idx, row in resultado.iterrows():
                data_list.append({
                    'numero_poliza': row['NUMERO_POLIZA'],
                    'cliente_nombre': row['CLIENTE_NOMBRE'],
                    'monto_uf': float(row['MONTO_UF']),
                    'estado': row['ESTADO'],
                    'total_cobranzas': int(row['TOTAL_COBRANZAS']),
                    'total_alertas': int(row['TOTAL_ALERTAS']),
                    'cluster': int(row['cluster']),
                    'nivel_riesgo': row['nivel_riesgo'],
                    'distancia_cluster': float(row['distancia_cluster']) if row['distancia_cluster'] else None,
                    'tasa_mora': float(row['TASA_MORA'])
                })
            
            return Response({
                'total_polizas': len(resultado),
                'clusters_identificados': int(resultado['cluster'].nunique()),
                'data': data_list
            })
        
        except Exception as e:
            logger.error(f"Error obteniendo clusters: {e}")
            import traceback
            traceback.print_exc()
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
