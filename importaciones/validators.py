"""
Utilidades para validación estructural de archivos Excel
MÓDULO 2: PASO 2.3 — Validación estructural
"""

import pandas as pd
import openpyxl
from typing import Dict, List, Tuple, Any
import logging

logger = logging.getLogger(__name__)


class ValidadorExcel:
    """
    Valida la estructura de archivos Excel antes de procesarlos
    """
    
    # Columnas esperadas por tipo de carga
    COLUMNAS_ESPERADAS = {
        'polizas': [
            'numero_poliza', 'cliente', 'producto', 'fecha_inicio', 'fecha_vencimiento',
            'monto', 'estado', 'asegurado'
        ],
        'cobranzas': [
            'numero_poliza', 'cliente', 'monto', 'fecha_pago', 'estado', 'metodo_pago'
        ],
        'clientes': [
            'rut', 'nombre', 'email', 'telefono', 'direccion', 'ciudad'
        ],
    }
    
    # Tipos de datos esperados
    TIPOS_ESPERADOS = {
        'fecha_inicio': 'datetime',
        'fecha_vencimiento': 'datetime',
        'fecha_pago': 'datetime',
        'fecha_carga': 'datetime',
        'monto': 'float',
        'numero_poliza': 'string',
        'cliente': 'string',
        'estado': 'string',
    }
    
    def __init__(self, ruta_archivo: str):
        self.ruta_archivo = ruta_archivo
        self.errores = []
        self.advertencias = []
        self.columnas_detectadas = []
        self.filas_totales = 0
        self.filas_vacias = 0
    
    def validar(self) -> Tuple[bool, Dict[str, Any]]:
        """
        Valida el archivo completamente
        
        Retorna:
            (es_valido, detalles)
        """
        
        try:
            # 1. Verificar que el archivo existe y es válido
            self._validar_archivo()
            if self.errores:
                return False, self._generar_reporte()
            
            # 2. Cargar el archivo
            df = self._cargar_archivo()
            if df is None:
                return False, self._generar_reporte()
            
            # 3. Detectar columnas
            self.columnas_detectadas = df.columns.tolist()
            
            # 4. Validar estructura
            self._validar_columnas(df)
            self._validar_tipos(df)
            self._validar_valores(df)
            
            # 5. Generar reporte
            reporte = self._generar_reporte()
            
            # Válido si no hay errores (advertencias sí se permiten)
            es_valido = len(self.errores) == 0
            
            return es_valido, reporte
            
        except Exception as e:
            self.errores.append(f"Error durante validación: {str(e)}")
            logger.error(f"Error validando Excel: {str(e)}", exc_info=True)
            return False, self._generar_reporte()
    
    def _validar_archivo(self):
        """Valida que el archivo sea un Excel válido"""
        import os
        
        if not os.path.exists(self.ruta_archivo):
            self.errores.append(f"Archivo no encontrado: {self.ruta_archivo}")
            return
        
        # Verificar extensión
        if not self.ruta_archivo.lower().endswith(('.xlsx', '.xls', '.csv')):
            self.errores.append("El archivo debe ser .xlsx, .xls o .csv")
            return
        
        # Verificar tamaño (máximo 50 MB)
        tamanio = os.path.getsize(self.ruta_archivo)
        if tamanio > 50 * 1024 * 1024:
            self.errores.append("El archivo es muy grande (máximo 50 MB)")
            return
        
        logger.info(f"Archivo válido: {self.ruta_archivo} ({tamanio} bytes)")
    
    def _cargar_archivo(self) -> pd.DataFrame:
        """Carga el archivo con openpyxl o pandas"""
        try:
            if self.ruta_archivo.endswith('.csv'):
                df = pd.read_csv(self.ruta_archivo, encoding='utf-8')
            else:
                df = pd.read_excel(self.ruta_archivo)
            
            self.filas_totales = len(df)
            logger.info(f"Archivo cargado: {self.filas_totales} filas")
            return df
            
        except Exception as e:
            self.errores.append(f"No se pudo cargar el archivo: {str(e)}")
            return None
    
    def _validar_columnas(self, df: pd.DataFrame):
        """Valida que existan las columnas requeridas"""
        # Normalizar nombres de columnas (minúsculas, sin espacios)
        df.columns = df.columns.str.lower().str.strip().str.replace(' ', '_')
        
        # Obtener tipo de carga por columnas (heurística)
        tipo_carga = self._detectar_tipo_carga(df.columns.tolist())
        
        if tipo_carga and tipo_carga in self.COLUMNAS_ESPERADAS:
            columnas_esperadas = self.COLUMNAS_ESPERADAS[tipo_carga]
            columnas_faltantes = set(columnas_esperadas) - set(df.columns)
            
            if columnas_faltantes:
                self.advertencias.append(
                    f"Columnas esperadas faltantes: {', '.join(columnas_faltantes)}"
                )
    
    def _validar_tipos(self, df: pd.DataFrame):
        """Valida los tipos de datos"""
        for columna in df.columns:
            if columna not in self.TIPOS_ESPERADOS:
                continue
            
            tipo_esperado = self.TIPOS_ESPERADOS[columna]
            
            try:
                if tipo_esperado == 'datetime':
                    # Intentar convertir a datetime
                    pd.to_datetime(df[columna], errors='coerce')
                elif tipo_esperado == 'float':
                    pd.to_numeric(df[columna], errors='coerce')
            except Exception as e:
                self.advertencias.append(
                    f"Columna '{columna}' no puede convertirse a {tipo_esperado}"
                )
    
    def _validar_valores(self, df: pd.DataFrame):
        """Valida valores nulos y datos vacíos"""
        # Detectar filas completamente vacías
        self.filas_vacias = df.isna().all(axis=1).sum()
        
        if self.filas_vacias > 0:
            self.advertencias.append(f"Se encontraron {self.filas_vacias} filas completamente vacías")
        
        # Detectar valores nulos en columnas críticas
        columnas_criticas = ['numero_poliza', 'cliente', 'rut']
        for col in columnas_criticas:
            if col in df.columns:
                nulos = df[col].isna().sum()
                if nulos > 0:
                    porcentaje = (nulos / len(df)) * 100
                    if porcentaje > 10:
                        self.errores.append(
                            f"Columna '{col}' tiene {nulos} valores nulos ({porcentaje:.1f}%)"
                        )
    
    def _detectar_tipo_carga(self, columnas: List[str]) -> str:
        """Detecta el tipo de carga por las columnas presentes"""
        columnas_lower = [c.lower() for c in columnas]
        
        # Pólizas
        if any('poliza' in c for c in columnas_lower):
            return 'polizas'
        
        # Cobranzas
        if any('pago' in c or 'cobranza' in c for c in columnas_lower):
            return 'cobranzas'
        
        # Clientes
        if any('rut' in c or 'cliente' in c for c in columnas_lower):
            return 'clientes'
        
        return None
    
    def _generar_reporte(self) -> Dict[str, Any]:
        """Genera reporte de validación"""
        return {
            'columnas_detectadas': self.columnas_detectadas,
            'filas_totales': self.filas_totales,
            'filas_vacias': self.filas_vacias,
            'errores': self.errores,
            'advertencias': self.advertencias,
            'es_valido': len(self.errores) == 0,
        }


class GeneradorPreview:
    """
    Genera preview (primeras N filas) de un archivo Excel
    MÓDULO 2: PASO 2.4 — Vista previa del Excel
    """
    
    FILAS_PREVIEW = 10
    
    @staticmethod
    def generar(ruta_archivo: str) -> Dict[str, Any]:
        """
        Genera preview del archivo
        
        Retorna:
            {
                'columnas': [...],
                'filas': [...],
                'total_filas': 1000,
                'total_columnas': 15,
                'primeras_5': [...]
            }
        """
        
        try:
            if ruta_archivo.endswith('.csv'):
                df = pd.read_csv(ruta_archivo, encoding='utf-8', nrows=GeneradorPreview.FILAS_PREVIEW + 1)
                df_total = pd.read_csv(ruta_archivo, encoding='utf-8')
            else:
                df = pd.read_excel(ruta_archivo, nrows=GeneradorPreview.FILAS_PREVIEW + 1)
                df_total = pd.read_excel(ruta_archivo)
            
            # Normalizar nombres de columnas
            df.columns = df.columns.str.lower().str.strip()
            df_total.columns = df_total.columns.str.lower().str.strip()
            
            # Convertir a diccionarios
            filas_preview = df.head(GeneradorPreview.FILAS_PREVIEW).to_dict('records')
            
            # Convertir valores para JSON
            for fila in filas_preview:
                for key, value in fila.items():
                    if pd.isna(value):
                        fila[key] = None
                    elif isinstance(value, (pd.Timestamp, pd.datetime.datetime)):
                        fila[key] = str(value)
            
            return {
                'columnas': df.columns.tolist(),
                'filas_preview': filas_preview,
                'total_filas': len(df_total),
                'total_columnas': len(df.columns),
                'primera_fila_mostrando': min(GeneradorPreview.FILAS_PREVIEW, len(df)),
            }
            
        except Exception as e:
            logger.error(f"Error generando preview: {str(e)}")
            return {
                'error': str(e),
                'columnas': [],
                'filas_preview': [],
            }


def validar_excel_simple(ruta_archivo: str) -> bool:
    """
    Función simple para validar si un Excel es válido
    
    Retorna: True si es válido, False sino
    """
    validador = ValidadorExcel(ruta_archivo)
    es_valido, _ = validador.validar()
    return es_valido
