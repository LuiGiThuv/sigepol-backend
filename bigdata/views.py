"""
Vistas API para el módulo de Big Data (FASE 2)

Nota: El entrenamiento del modelo (PASO 6) se ejecuta en Google Colab.
Estas vistas son para consultar resultados y aplicar clusters.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.http import FileResponse
from .models import ClusterAsignacion, ModeloEntrenamiento
import pandas as pd
from io import BytesIO
import logging

logger = logging.getLogger(__name__)


class DatasetMLView(APIView):
    """
    Endpoint para descargar el dataset oficial para entrenamientoML
    GET /api/bigdata/dataset/?formato=parquet|csv|json
    
    Retorna un dataset con todas las pólizas y features para ML
    """
    
    def get(self, request):
        """Descargar dataset para ML"""
        formato = request.query_params.get('formato', 'parquet').lower()
        
        try:
            # Importar modelos
            from polizas.models import Poliza
            from cobranzas.models import Cobranza
            from alertas.models import Alerta
            
            # Construir dataset desde pólizas
            polizas = Poliza.objects.select_related('cliente').all()
            
            if not polizas.exists():
                return Response(
                    {'error': 'No hay pólizas en la BD'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Crear DataFrame
            datos = []
            for poliza in polizas:
                # Datos básicos de póliza
                fila = {
                    'NUMERO_POLIZA': poliza.numero,
                    'CLIENTE_ID': poliza.cliente.id if poliza.cliente else None,
                    'CLIENTE_NOMBRE': poliza.cliente.nombre if poliza.cliente else 'DESCONOCIDO',
                    'MONTO_UF': float(poliza.monto_uf or 0),
                    'ESTADO': poliza.estado or 'DESCONOCIDO',
                    'FECHA_INICIO': poliza.fecha_inicio,
                    'FECHA_VENCIMIENTO': poliza.fecha_vencimiento,
                }
                
                # Calcular días de vigencia
                if poliza.fecha_inicio and poliza.fecha_vencimiento:
                    dias = (poliza.fecha_vencimiento - poliza.fecha_inicio).days
                    fila['DIAS_VIGENCIA'] = dias
                else:
                    fila['DIAS_VIGENCIA'] = 0
                
                # Información de cobranzas
                cobranzas = Cobranza.objects.filter(poliza=poliza)
                fila['TOTAL_COBRANZAS'] = cobranzas.count()
                fila['COBRANZAS_PAGADAS'] = cobranzas.filter(estado='PAGADA').count()
                fila['COBRANZAS_PENDIENTES'] = cobranzas.filter(estado='PENDIENTE').count()
                
                # Información de alertas
                alertas = Alerta.objects.filter(poliza=poliza)
                fila['TOTAL_ALERTAS'] = alertas.count()
                fila['ALERTAS_CRITICAS'] = alertas.filter(estado='CRITICA').count()
                
                datos.append(fila)
            
            # Convertir a DataFrame
            df = pd.DataFrame(datos)
            
            logger.info(f"Dataset creado: {len(df)} filas, {len(df.columns)} columnas")
            
            # Retornar según formato
            if formato == 'parquet':
                buffer = BytesIO()
                df.to_parquet(buffer, index=False)
                buffer.seek(0)
                return FileResponse(
                    buffer,
                    as_attachment=True,
                    filename='dataset_ml.parquet',
                    content_type='application/octet-stream'
                )
            
            elif formato == 'csv':
                buffer = BytesIO()
                df.to_csv(buffer, index=False, encoding='utf-8')
                buffer.seek(0)
                return FileResponse(
                    buffer,
                    as_attachment=True,
                    filename='dataset_ml.csv',
                    content_type='text/csv'
                )
            
            elif formato == 'json':
                return Response({
                    'total_filas': len(df),
                    'total_columnas': len(df.columns),
                    'columnas': df.columns.tolist(),
                    'datos': df.to_dict('records'),
                    'muestra_filas': len(df)
                })
            
            else:
                return Response(
                    {'error': 'Formato no soportado. Use: parquet, csv o json'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        except Exception as e:
            logger.error(f"Error en DatasetMLView: {str(e)}", exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )



class ClusterListView(APIView):
    """
    Lista las asignaciones de clusters de las pólizas.
    """
    
    def get(self, request):
        """Obtener clusters asignados"""
        clusters = ClusterAsignacion.objects.all().values('poliza__numero', 'cluster_id')
        return Response({
            'total': clusters.count(),
            'clusters': list(clusters)
        })


class ModeloStatusView(APIView):
    """
    Estado del último entrenamiento del modelo.
    """
    
    def get(self, request):
        """Obtener estado del modelo"""
        modelo = ModeloEntrenamiento.objects.order_by('-fecha_inicio').first()
        
        if not modelo:
            return Response({
                'estado': 'no_entrenado',
                'mensaje': 'Aún no se ha entrenado el modelo'
            }, status=status.HTTP_404_NOT_FOUND)
        
        return Response({
            'estado': modelo.estado,
            'k_optimo': modelo.k_optimo,
            'silhouette_score': modelo.silhouette_score,
            'num_polizas': modelo.num_polizas,
            'fecha_inicio': modelo.fecha_inicio,
            'fecha_finalizacion': modelo.fecha_finalizacion,
            'notas': modelo.notas
        })
