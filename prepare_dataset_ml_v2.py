#!/usr/bin/env python
"""
Dataset Preparation for ML Training
=====================================
Prepara el dataset_ml.parquet desde SIGEPOL BD

Requisitos:
- NUMERO_POLIZA: ID único de póliza
- MONTO_UF: Monto en UF (reemplaza PRIMA_NETA y PRIMA_BRUTA)
- DIAS_VIGENCIA: Días entre fecha_inicio y fecha_vencimiento
"""

import os
import sys
import django
import pandas as pd
from datetime import date

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sigepol.settings')
django.setup()

from polizas.models import Poliza
from cobranzas.models import Cobranza
from alertas.models import Alerta
from clientes.models import Cliente

# Crear directorio
os.makedirs('ml_data', exist_ok=True)
DATASET_PATH = 'ml_data/dataset_ml.parquet'

print("""
=======================================================================
📊 PREPARACIÓN DE DATASET PARA ML
=======================================================================
""")

# ============================================================================
# PASO 1: Extraer datos de SIGEPOL
# ============================================================================
print("✅ PASO 1: Extraer datos de Pólizas")

try:
    polizas = Poliza.objects.select_related('cliente').all()
    print(f"   - Total pólizas: {polizas.count()}")
    
    if polizas.count() == 0:
        print("   ❌ No hay pólizas en la BD")
        sys.exit(1)
        
except Exception as e:
    print(f"   ❌ Error al consultar: {str(e)}")
    sys.exit(1)

# ============================================================================
# PASO 2: Construir DataFrame
# ============================================================================
print("\n✅ PASO 2: Construir DataFrame")

datos = []
for poliza in polizas:
    # Calcular días de vigencia
    dias_vigencia = 0
    if poliza.fecha_inicio and poliza.fecha_vencimiento:
        dias_vigencia = (poliza.fecha_vencimiento - poliza.fecha_inicio).days
    
    # Información de cobranzas
    cobranzas = Cobranza.objects.filter(poliza=poliza)
    
    # Información de alertas
    alertas = Alerta.objects.filter(poliza=poliza)
    
    # Crear fila
    fila = {
        # Columnas requeridas
        'NUMERO_POLIZA': poliza.numero,
        'MONTO_UF': float(poliza.monto_uf or 0),
        'DIAS_VIGENCIA': dias_vigencia,
        
        # Información de cliente
        'CLIENTE_ID': poliza.cliente.id if poliza.cliente else None,
        'CLIENTE_RUT': poliza.cliente.rut if poliza.cliente else None,
        
        # Información de póliza
        'ESTADO': poliza.estado or 'DESCONOCIDO',
        'FECHA_INICIO': poliza.fecha_inicio.isoformat() if poliza.fecha_inicio else None,
        'FECHA_VENCIMIENTO': poliza.fecha_vencimiento.isoformat() if poliza.fecha_vencimiento else None,
        
        # Información de cobranzas
        'TOTAL_COBRANZAS': cobranzas.count(),
        'COBRANZAS_PAGADAS': cobranzas.filter(estado='PAGADA').count(),
        'COBRANZAS_PENDIENTES': cobranzas.filter(estado='PENDIENTE').count(),
        
        # Información de alertas
        'TOTAL_ALERTAS': alertas.count(),
        'ALERTAS_CRITICAS': alertas.filter(estado='CRITICA').count(),
        
        # Data freshness
        'FRESCURA_ESTADO': poliza.frescura_estado if hasattr(poliza, 'frescura_estado') else 'desconocido',
    }
    
    datos.append(fila)

# Crear DataFrame
df = pd.DataFrame(datos)
print(f"   - Filas construidas: {len(df)}")
print(f"   - Columnas: {list(df.columns)}")

# ============================================================================
# PASO 3: Guardar dataset
# ============================================================================
print("\n✅ PASO 3: Guardar dataset")

try:
    df.to_parquet(DATASET_PATH, index=False)
    file_size = os.path.getsize(DATASET_PATH) / 1024 / 1024
    print(f"   ✅ Dataset guardado: {DATASET_PATH}")
    print(f"   - Tamaño: {file_size:.2f} MB")
    print(f"   - Filas: {len(df)}")
    
except Exception as e:
    print(f"   ❌ Error al guardar: {str(e)}")
    sys.exit(1)

# ============================================================================
# PASO 4: Verificar columnas requeridas
# ============================================================================
print("\n✅ PASO 4: Verificar columnas requeridas")

COLUMNAS_REQUERIDAS = {
    'NUMERO_POLIZA': 'ID único de póliza',
    'MONTO_UF': 'Monto en UF (prima)',
    'DIAS_VIGENCIA': 'Días de vigencia',
}

todas_presentes = True
for col, desc in COLUMNAS_REQUERIDAS.items():
    if col in df.columns:
        print(f"   ✅ {col}: {desc}")
    else:
        print(f"   ❌ FALTA: {col}")
        todas_presentes = False

if not todas_presentes:
    print("\n   ❌ Faltan columnas requeridas")
    sys.exit(1)

# ============================================================================
# PASO 5: Análisis exploratorio
# ============================================================================
print("\n✅ PASO 5: Análisis exploratorio")

print("\n   📊 Estadísticas por columna:")
print(f"   - NUMERO_POLIZA: {df['NUMERO_POLIZA'].nunique()} valores únicos")
print(f"   - MONTO_UF: min={df['MONTO_UF'].min():.2f}, max={df['MONTO_UF'].max():.2f}, mean={df['MONTO_UF'].mean():.2f}")
print(f"   - DIAS_VIGENCIA: min={df['DIAS_VIGENCIA'].min()}, max={df['DIAS_VIGENCIA'].max()}, mean={df['DIAS_VIGENCIA'].mean():.1f}")

print("\n   📉 Valores nulos:")
for col in df.columns:
    nulls = df[col].isnull().sum()
    if nulls > 0:
        pct = (nulls / len(df)) * 100
        print(f"   - {col}: {nulls} ({pct:.1f}%)")

print("\n   📋 Muestra de datos:")
print(df[['NUMERO_POLIZA', 'MONTO_UF', 'DIAS_VIGENCIA', 'ESTADO']].head(5).to_string())

# ============================================================================
# PASO 6: Preparar metadata
# ============================================================================
print("\n✅ PASO 6: Preparar metadata")

metadata = {
    'total_rows': len(df),
    'total_columns': len(df.columns),
    'generated_at': pd.Timestamp.now().isoformat(),
    'columns': list(df.columns),
    'columnas_requeridas': list(COLUMNAS_REQUERIDAS.keys()),
    'dtype_mapping': {col: str(dtype) for col, dtype in df.dtypes.items()},
    'statistics': {
        'NUMERO_POLIZA': {'unique': int(df['NUMERO_POLIZA'].nunique())},
        'MONTO_UF': {
            'min': float(df['MONTO_UF'].min()),
            'max': float(df['MONTO_UF'].max()),
            'mean': float(df['MONTO_UF'].mean()),
            'std': float(df['MONTO_UF'].std()),
        },
        'DIAS_VIGENCIA': {
            'min': int(df['DIAS_VIGENCIA'].min()),
            'max': int(df['DIAS_VIGENCIA'].max()),
            'mean': float(df['DIAS_VIGENCIA'].mean()),
        },
    }
}

# Guardar metadata
import json
metadata_path = 'ml_data/dataset_ml.json'
with open(metadata_path, 'w') as f:
    json.dump(metadata, f, indent=2)

print(f"   ✅ Metadata guardada: {metadata_path}")

# ============================================================================
# RESUMEN FINAL
# ============================================================================
print("""
=======================================================================
✅ DATASET LISTO PARA ML
=======================================================================

📦 Archivos generados:
   - ml_data/dataset_ml.parquet (dataset para entrenamiento)
   - ml_data/dataset_ml.json (metadata y estadísticas)

📊 Resumen:
""")

print(f"   - Total registros: {len(df)}")
print(f"   - Total features: {len(df.columns)}")
print(f"   - Columnas requeridas: ✅ TODAS PRESENTES")
print(f"   - Nulos: {df.isnull().sum().sum()} valores")

print("\n🚀 Próximo paso: MÓDULO 3 (ML Training en AWS)")
print("   Comando: python train_ml_model.py --dataset ml_data/dataset_ml.parquet")

print("\n=======================================================================")
