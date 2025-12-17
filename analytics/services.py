"""
Servicios de análisis ML para pólizas
Conecta los datos de SIGEPOL con los predictores ML
"""

import pandas as pd
import logging
from django.core.cache import cache
from polizas.models import Poliza
from cobranzas.models import Cobranza
from alertas.models import Alerta
from .ml.predictor import predictor, FEATURES

logger = logging.getLogger(__name__)

class AnalizadorPolizas:
    """Servicio para analizar pólizas con ML"""
    
    @staticmethod
    def construir_dataframe():
        """Construye DataFrame con todas las pólizas y features"""
        
        # Verificar si está en cache
        df_cache = cache.get('df_polizas_features')
        if df_cache is not None:
            logger.info("DataFrame obtenido del cache")
            return df_cache
        
        logger.info("Construyendo DataFrame desde BD...")
        
        polizas = Poliza.objects.select_related('cliente').all()
        datos = []
        
        for poliza in polizas:
            fila = {}
            
            # Datos básicos
            fila['NUMERO_POLIZA'] = str(poliza.numero) if poliza.numero else ''
            fila['CLIENTE_NOMBRE'] = str(poliza.cliente.nombre) if poliza.cliente else 'DESCONOCIDO'
            fila['MONTO_UF'] = float(poliza.monto_uf or 0)
            fila['ESTADO'] = poliza.estado or 'DESCONOCIDO'
            
            # Vigencia
            if poliza.fecha_inicio and poliza.fecha_vencimiento:
                fila['DIAS_VIGENCIA'] = (poliza.fecha_vencimiento - poliza.fecha_inicio).days
            else:
                fila['DIAS_VIGENCIA'] = 0
            
            # Cobranzas
            cobranzas = Cobranza.objects.filter(poliza=poliza)
            total_cob = cobranzas.count()
            pagadas = cobranzas.filter(estado='PAGADA').count()
            pendientes = cobranzas.filter(estado='PENDIENTE').count()
            
            fila['TOTAL_COBRANZAS'] = total_cob
            fila['COBRANZAS_PAGADAS'] = pagadas
            fila['COBRANZAS_PENDIENTES'] = pendientes
            fila['TASA_PAGO'] = round(pagadas / total_cob, 3) if total_cob > 0 else 0.0
            fila['TASA_MORA'] = round(pendientes / total_cob, 3) if total_cob > 0 else 0.0
            
            # Alertas
            alertas = Alerta.objects.filter(poliza=poliza)
            total_alert = alertas.count()
            criticas = alertas.filter(estado='CRITICA').count()
            
            fila['TOTAL_ALERTAS'] = total_alert
            fila['ALERTAS_CRITICAS'] = criticas
            
            dias = fila['DIAS_VIGENCIA']
            fila['DENSIDAD_ALERTAS'] = round(total_alert / dias, 4) if dias > 0 else 0.0
            
            fila['CLUSTER_ANTERIOR'] = poliza.cluster if poliza.cluster else -1
            fila['FRESCURA'] = poliza.frescura_estado if poliza.frescura_estado else 'DESCONOCIDO'
            fila['DATOS_CONFIABLES'] = 1 if poliza.datos_confiables else 0
            
            datos.append(fila)
        
        df = pd.DataFrame(datos)
        
        # Guardar en cache por 1 hora
        cache.set('df_polizas_features', df, 3600)
        logger.info(f"DataFrame construido: {len(df)} pólizas")
        
        return df
    
    @staticmethod
    def predecir_clusters():
        """Predice clusters para todas las pólizas"""
        
        if not predictor.esta_disponible():
            logger.warning("Modelos ML no disponibles")
            return None
        
        try:
            df = AnalizadorPolizas.construir_dataframe()
            df_predicho = predictor.predecir(df)
            
            logger.info(f"Predicción completada para {len(df_predicho)} pólizas")
            
            # Actualizar clusters en BD
            AnalizadorPolizas.actualizar_clusters_bd(df_predicho)
            
            return df_predicho
        
        except Exception as e:
            logger.error(f"Error en predicción: {e}")
            return None
    
    @staticmethod
    def actualizar_clusters_bd(df_predicho):
        """Actualiza los clusters predichos en la base de datos"""
        
        try:
            for idx, fila in df_predicho.iterrows():
                poliza = Poliza.objects.get(numero=fila['NUMERO_POLIZA'])
                poliza.cluster = int(fila['cluster_predicho'])
                poliza.save(update_fields=['cluster', 'ultima_actualizacion'])
            
            logger.info(f"Clusters actualizados para {len(df_predicho)} pólizas")
        
        except Exception as e:
            logger.error(f"Error actualizando clusters: {e}")
    
    @staticmethod
    def obtener_estadisticas_clusters(df_predicho):
        """Calcula estadísticas por cluster"""
        
        if df_predicho is None or 'cluster_predicho' not in df_predicho.columns:
            return None
        
        estadisticas = []
        
        for cluster_id in sorted(df_predicho['cluster_predicho'].unique()):
            cluster_data = df_predicho[df_predicho['cluster_predicho'] == cluster_id]
            
            stats = {
                'cluster': int(cluster_id),
                'cantidad_polizas': len(cluster_data),
                'porcentaje': round(len(cluster_data) / len(df_predicho) * 100, 2),
                'monto_uf_promedio': float(cluster_data['MONTO_UF'].mean()),
                'tasa_pago_promedio': float(cluster_data['TASA_PAGO'].mean()),
                'alertas_totales': int(cluster_data['TOTAL_ALERTAS'].sum()),
                'riesgo_nivel': determinar_riesgo(cluster_data)
            }
            
            estadisticas.append(stats)
        
        return estadisticas


def determinar_riesgo(cluster_data):
    """Determina nivel de riesgo basado en características del cluster"""
    
    tasa_mora = cluster_data['TASA_MORA'].mean()
    alertas_densidad = cluster_data['DENSIDAD_ALERTAS'].mean()
    cobranzas_pendientes = (cluster_data['COBRANZAS_PENDIENTES'] > 0).sum() / len(cluster_data)
    
    score_riesgo = (tasa_mora * 0.4) + (alertas_densidad * 0.3) + (cobranzas_pendientes * 0.3)
    
    if score_riesgo > 0.7:
        return 'CRÍTICO'
    elif score_riesgo > 0.5:
        return 'ALTO'
    elif score_riesgo > 0.3:
        return 'MEDIO'
    else:
        return 'BAJO'


def mapear_riesgo_individual(cluster_id, tasa_mora, alertas, cobranzas_pendientes):
    """
    Mapea un cluster individual a nivel de riesgo
    
    Regla de negocio:
    - CRÍTICO: Tasa mora > 50% O alertas > 5
    - ALTO: Tasa mora > 30% O alertas > 2
    - MEDIO: Tasa mora > 10% O alertas > 0
    - BAJO: Sin issues
    """
    
    if tasa_mora > 0.5 or alertas > 5:
        return 'CRÍTICO'
    elif tasa_mora > 0.3 or alertas > 2:
        return 'ALTO'
    elif tasa_mora > 0.1 or alertas > 0:
        return 'MEDIO'
    else:
        return 'BAJO'
