"""
Predictor ML para inferencia con modelos preentrenados
Carga modelos de K-Means y Scaler, hace predicciones de clusters
"""

import os
import joblib
import pandas as pd
import numpy as np
from pathlib import Path

# Rutas de modelos
BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "kmeans_sigepol.pkl"
SCALER_PATH = BASE_DIR / "scaler_sigepol.pkl"

# Features que usa el modelo (deben coincidir con las usadas en entrenamiento)
FEATURES = [
    "MONTO_UF",
    "DIAS_VIGENCIA",
    "TOTAL_COBRANZAS",
    "COBRANZAS_PAGADAS",
    "COBRANZAS_PENDIENTES"
]

class PredictorML:
    """Predictor de clusters para pólizas usando K-Means preentrenado"""
    
    def __init__(self):
        self.modelo = None
        self.scaler = None
        self.cargar_modelos()
    
    def cargar_modelos(self):
        """Carga los modelos preentrenados"""
        try:
            if MODEL_PATH.exists():
                self.modelo = joblib.load(str(MODEL_PATH))
                print(f"✅ Modelo K-Means cargado desde {MODEL_PATH}")
            else:
                print(f"⚠️  Modelo no encontrado en {MODEL_PATH}")
                self.modelo = None
            
            if SCALER_PATH.exists():
                self.scaler = joblib.load(str(SCALER_PATH))
                print(f"✅ Scaler cargado desde {SCALER_PATH}")
            else:
                print(f"⚠️  Scaler no encontrado en {SCALER_PATH}")
                self.scaler = None
        
        except Exception as e:
            print(f"❌ Error cargando modelos: {e}")
            self.modelo = None
            self.scaler = None
    
    def esta_disponible(self):
        """Verifica si los modelos están disponibles"""
        return self.modelo is not None and self.scaler is not None
    
    def predecir(self, df):
        """
        Predice clusters para un DataFrame
        
        Args:
            df (pd.DataFrame): DataFrame con columnas FEATURES
        
        Returns:
            pd.DataFrame: DataFrame original + columna 'cluster_predicho'
        """
        if not self.esta_disponible():
            raise ValueError("Modelos no disponibles. Entrena primero con Google Colab.")
        
        # Validar que existan las features necesarias
        features_faltantes = [f for f in FEATURES if f not in df.columns]
        if features_faltantes:
            raise ValueError(f"Faltan features: {features_faltantes}")
        
        # Seleccionar features y escalar
        X = df[FEATURES].copy()
        
        # Manejar valores faltantes
        X = X.fillna(X.mean())
        
        # Escalar
        X_scaled = self.scaler.transform(X)
        
        # Predecir clusters
        df['cluster_predicho'] = self.modelo.predict(X_scaled)
        
        # Agregar probabilidades (distancia a centros)
        distancias = self.modelo.transform(X_scaled)
        df['distancia_cluster'] = distancias.min(axis=1)
        
        return df
    
    def predecir_individual(self, datos):
        """
        Predice cluster para un individual registro
        
        Args:
            datos (dict): Diccionario con las features
        
        Returns:
            dict: {'cluster': int, 'distancia': float}
        """
        if not self.esta_disponible():
            raise ValueError("Modelos no disponibles")
        
        # Crear DataFrame con una fila
        df = pd.DataFrame([datos])
        
        # Validar features
        for feature in FEATURES:
            if feature not in df.columns:
                df[feature] = 0.0
        
        # Predecir
        resultado = self.predecir(df)
        
        return {
            'cluster': int(resultado['cluster_predicho'].iloc[0]),
            'distancia': float(resultado['distancia_cluster'].iloc[0])
        }


# Instancia global
predictor = PredictorML()
