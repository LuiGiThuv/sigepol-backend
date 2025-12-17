"""
Pipeline ETL completo para procesamiento de importaciones
"""
import re
import pandas as pd
import io
import csv
import math
from datetime import datetime
from django.db import transaction
from django.core.files.base import ContentFile
from django.utils import timezone

from .models import DataUpload, ImportErrorRow
from clientes.models import Cliente
from polizas.models import Poliza
from auditorias.utils import create_audit_log
from .utils import update_upload_status

# Importar utilidades de alertas
try:
    from alertas.utils import crear_alerta, reglas_alertas_automaticas as ejecutar_reglas_alertas
except ImportError:
    def crear_alerta(*args, **kwargs):
        pass  # Fallback si alertas no está disponible
    def ejecutar_reglas_alertas(*args, **kwargs):
        pass

# Configuraciones
BATCH_SIZE = 500
RUT_REGEX = re.compile(r'^[0-9]{1,2}\.[0-9]{3}\.[0-9]{3}-[0-9Kk]$|^[0-9]{7,8}-[0-9Kk]$')


def normalize_rut(rut_str):
    """Normaliza RUT a formato NN.NNN.NNN-K"""
    if not isinstance(rut_str, str):
        return None
    
    s = str(rut_str).replace('.', '').replace(' ', '').replace('-', '').upper()
    if len(s) < 8:
        return None
    
    # Insertar puntos y guión
    body = s[:-1]
    dv = s[-1]
    
    # Formato: XX.XXX.XXX-K
    if len(body) <= 3:
        formatted = body + '-' + dv
    elif len(body) <= 6:
        formatted = body[:-3] + '.' + body[-3:] + '-' + dv
    else:
        formatted = body[:-6] + '.' + body[-6:-3] + '.' + body[-3:] + '-' + dv
    
    return formatted


def is_valid_rut(rut_str):
    """Valida RUT con regex simple"""
    if not rut_str:
        return False
    return bool(RUT_REGEX.match(str(rut_str)))


def parse_vigencia(vigencia_str):
    """
    Parsea vigencia de formato "DD/MM/YYYY AL DD/MM/YYYY"
    Retorna (fecha_inicio, fecha_fin) o (None, None)
    """
    if not vigencia_str or pd.isna(vigencia_str):
        raise ValueError(f"Vigencia inválida: {vigencia_str}")
    
    vigencia_str = str(vigencia_str).strip().upper()
    if 'AL' not in vigencia_str and 'A' not in vigencia_str:
        raise ValueError(f"Vigencia inválida (no contiene 'AL'): {vigencia_str}")
    
    # Dividir por "AL" o "A "
    if 'AL' in vigencia_str:
        parts = vigencia_str.split('AL')
    else:
        parts = vigencia_str.split('A')
    
    if len(parts) < 2:
        raise ValueError(f"Vigencia inválida (no tiene dos fechas): {vigencia_str}")
    
    try:
        inicio_str = parts[0].strip()
        fin_str = parts[1].strip()
        
        # Parsear fechas (asumiendo DD/MM/YYYY)
        inicio = pd.to_datetime(inicio_str, dayfirst=True).date()
        fin = pd.to_datetime(fin_str, dayfirst=True).date()
        
        return inicio, fin
    except Exception as e:
        raise ValueError(f"Error al parsear vigencia '{vigencia_str}': {str(e)}")


def float_from_str(s):
    """Convierte string a float, manejando formatos chilenos"""
    if s is None or pd.isna(s):
        raise ValueError(f"Monto inválido: {s}")
    
    try:
        s = str(s).strip()
        if not s:
            raise ValueError(f"Monto vacío")
        # Reemplazar punto (miles) y coma (decimales)
        s = s.replace('.', '').replace(',', '.')
        return float(s)
    except (ValueError, AttributeError) as e:
        raise ValueError(f"No se puede convertir '{s}' a float: {str(e)}")


def save_error_csv(upload, errors):
    """
    Guarda lista de errores en CSV y lo asigna a upload.error_file
    
    Args:
        upload: DataUpload instance
        errors: Lista de dicts con keys: row_number, raw_data (dict), error
    """
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_ALL)
    writer.writerow(['row_number', 'error', 'raw_data'])
    
    for e in errors:
        row_data = str(e.get('raw_data', {}))
        writer.writerow([
            e.get('row_number', ''),
            e.get('error', ''),
            row_data
        ])
    
    content = ContentFile(output.getvalue().encode('utf-8'))
    filename = f'errors_upload_{upload.id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    upload.error_file.save(filename, content, save=False)


def process_upload(upload_id, run_ml=False):
    """
    Procesa upload ETL: validar → limpiar → procesar → (ml) → completado o error
    
    Args:
        upload_id: ID de DataUpload
        run_ml: Si True, marca status='ml' al final (para posterior procesamiento ML)
    
    Returns:
        Dict con resumen: {processed, inserted, updated, errors, error (si hay)}
    """
    try:
        upload = DataUpload.objects.get(id=upload_id)
    except DataUpload.DoesNotExist:
        return {'error': f'DataUpload {upload_id} no encontrado'}
    
    errors = []
    inserted = 0
    updated = 0
    processed = 0
    
    try:
        # PASO 1: Validación
        update_upload_status(upload, 'validando')
        
        # Leer Excel
        try:
            df = pd.read_excel(upload.archivo.path, engine='openpyxl')
        except Exception as e:
            raise Exception(f'Error leyendo Excel: {str(e)}')
        
        if len(df) == 0:
            raise Exception('Archivo Excel vacío')
        
        # Normalizar nombres de columnas
        df.columns = [c.strip().upper() for c in df.columns]
        
        # Mapeo de columnas (ajustar según tu estructura real)
        column_map = {
            'COMPAÑÍA': 'COMPANIA',
            'COMPANIA': 'COMPANIA',
            'RUT CONTRATANTE': 'RUT',
            'RUT': 'RUT',
            'NOMBRE CONTRATANTE': 'NOMBRE_CLIENTE',
            'NOMBRE': 'NOMBRE_CLIENTE',
            'PÓLIZA': 'NUMERO_POLIZA',
            'POLIZA': 'NUMERO_POLIZA',
            'VIGENCIA': 'VIGENCIA',
            'PRIMA NETA': 'PRIMA_NETA',
            'MONTO': 'PRIMA_NETA',
        }
        
        # Aplicar mapeo
        for real_col, std_col in column_map.items():
            if real_col in df.columns and std_col not in df.columns:
                df.rename(columns={real_col: std_col}, inplace=True)
        
        # Crear columnas de fechas desde VIGENCIA
        df['FECHA_INICIO'] = None
        df['FECHA_VENCIMIENTO'] = None
        
        for idx, vig in df.get('VIGENCIA', pd.Series()).fillna('').items():
            inicio, fin = parse_vigencia(str(vig))
            df.at[idx, 'FECHA_INICIO'] = inicio
            df.at[idx, 'FECHA_VENCIMIENTO'] = fin
        
        # Convertir montos
        df['MONTO_UF'] = df.get('PRIMA_NETA', pd.Series()).apply(float_from_str)
        
        # PASO 2: Limpieza (opcional: aquí podrías hacer más validaciones)
        update_upload_status(upload, 'limpiando')
        
        # PASO 3: Procesamiento por lotes
        update_upload_status(upload, 'procesando')
        
        total = len(df)
        
        for start in range(0, total, BATCH_SIZE):
            batch = df.iloc[start:start + BATCH_SIZE]
            
            with transaction.atomic():
                for row_idx, (i, row) in enumerate(batch.iterrows()):
                    row_number = start + row_idx + 2  # +2: header + 0-index
                    processed += 1
                    
                    try:
                        # Validar RUT
                        rut_raw = row.get('RUT')
                        rut = normalize_rut(rut_raw)
                        
                        if not is_valid_rut(rut):
                            raise ValueError(f'RUT inválido: {rut_raw}')
                        
                        # Obtener o crear Cliente
                        nombre_cliente = row.get('NOMBRE_CLIENTE') or 'SIN_NOMBRE'
                        cliente, _ = Cliente.objects.get_or_create(
                            rut=rut,
                            defaults={'nombre': str(nombre_cliente)[:200]}
                        )
                        
                        # Obtener número de póliza
                        numero = str(row.get('NUMERO_POLIZA')).strip()
                        if not numero or numero.lower() == 'nan':
                            raise ValueError('Número de póliza inválido o vacío')
                        
                        # Fechas
                        fecha_ini = row.get('FECHA_INICIO')
                        fecha_fin = row.get('FECHA_VENCIMIENTO')
                        
                        if not fecha_ini or not fecha_fin:
                            raise ValueError(f'Vigencia inválida: {row.get("VIGENCIA")}')
                        
                        # Monto
                        monto = row.get('MONTO_UF')
                        if monto is None or (isinstance(monto, float) and math.isnan(monto)):
                            monto = 0.0
                        
                        # Crear o actualizar Póliza
                        poliza, created = Poliza.objects.update_or_create(
                            numero=numero,
                            defaults={
                                'cliente': cliente,
                                'fecha_inicio': fecha_ini,
                                'fecha_vencimiento': fecha_fin,
                                'monto_uf': monto,
                                'estado': 'VIGENTE'
                            }
                        )
                        
                        if created:
                            inserted += 1
                        else:
                            updated += 1
                    
                    except Exception as row_error:
                        errors.append({
                            'row_number': row_number,
                            'raw_data': row.to_dict(),
                            'error': str(row_error)
                        })
                        
                        # Registrar en DB si hay espacio
                        try:
                            ImportErrorRow.objects.create(
                                upload=upload,
                                row_number=row_number,
                                raw_data=dict(row),
                                error=str(row_error)
                            )
                        except Exception:
                            pass  # Ignorar errores al guardar en DB
        
        # PASO 4: Guardar resumen
        upload.processed_rows = processed
        upload.inserted_rows = inserted
        upload.updated_rows = updated
        
        if errors:
            save_error_csv(upload, errors)
            update_upload_status(
                upload,
                'error',
                error_message=f'{len(errors)} filas con error de {processed} procesadas'
            )
            
            # Crear alerta por errores en carga (PASO 7.3)
            try:
                archivo_nombre = upload.archivo.name.split('/')[-1] if upload.archivo else 'archivo.xlsx'
                crear_alerta(
                    tipo='error_carga',
                    severidad='warning',
                    titulo=f'Errores en carga de {archivo_nombre}',
                    mensaje=f'El archivo {archivo_nombre} tiene {len(errors)} filas con error.',
                    usuario=upload.cargado_por
                )
            except Exception:
                pass  # Ignorar errores al crear alertas
        else:
            # Si no hay errores, ir a ML o completado
            if run_ml:
                update_upload_status(upload, 'ml')
            else:
                update_upload_status(upload, 'completado')
            
            # Crear alerta de éxito (PASO 7.3)
            try:
                archivo_nombre = upload.archivo.name.split('/')[-1] if upload.archivo else 'archivo.xlsx'
                crear_alerta(
                    tipo='importaciones',
                    severidad='info',
                    titulo=f'Carga exitosa: {archivo_nombre}',
                    mensaje=f'Archivo {archivo_nombre} procesado correctamente. '
                           f'{inserted} nuevas pólizas, {updated} actualizadas.',
                    usuario=upload.cargado_por
                )
            except Exception:
                pass  # Ignorar errores al crear alertas
            
            # Registrar frescura de datos (PASO 15: Data Freshness Validation)
            try:
                from .models import DataFreshness
                from clientes.models import Cliente
                
                if inserted > 0 or updated > 0:
                    # Registrar frescura para cada cliente actualizado
                    clientes_actualizados = Cliente.objects.filter(
                        polizas__isnull=False
                    ).distinct()
                    
                    registros_actualizados = inserted + updated
                    
                    for cliente in clientes_actualizados:
                        try:
                            # Registrar carga para este cliente
                            DataFreshness.registrar_carga(
                                cliente=cliente.rut,
                                usuario=upload.cargado_por,
                                registros_actualizados=registros_actualizados
                            )
                        except Exception as e:
                            logger.warning(f"No se pudo registrar frescura para {cliente.rut}: {str(e)}")
                    
                    logger.info(f"Frescura de datos registrada para {clientes_actualizados.count()} clientes")
            except Exception as e:
                logger.warning(f"No se pudo registrar frescura de datos: {str(e)}")
            
            # Ejecutar reglas automáticas de alertas (PASO 7.4)
            try:
                ejecutar_reglas_alertas(upload)
            except Exception:
                pass  # Ignorar errores en reglas automáticas
            
            # FASE 2: Generar dataset automáticamente para ML
            try:
                from bigdata.utils import enriquecer_dataset_ml, generar_archivos_dataset
                import os
                from django.conf import settings
                
                logger.info("Generando dataset ML automáticamente después de ETL exitoso...")
                df = enriquecer_dataset_ml()
                resultado = generar_archivos_dataset(
                    df,
                    upload_id=upload.id,
                    usuario=upload.cargado_por
                )
                logger.info(f"Dataset ML regenerado: {len(df)} registros. Archivos: {resultado.get('parquet', 'N/A')}")
            except Exception as e:
                logger.warning(f"No se pudo regenerar dataset ML automáticamente: {str(e)}")
                # No fallar el ETL si el dataset no se puede generar
        
        # Registrar en auditoría
        try:
            create_audit_log(
                usuario=upload.cargado_por,
                accion='process',
                descripcion=f'Procesó upload {upload.id}: {inserted} insertadas, {updated} actualizadas, {len(errors)} errores',
                detalles={
                    'upload_id': upload.id,
                    'processed': processed,
                    'inserted': inserted,
                    'updated': updated,
                    'errors': len(errors)
                }
            )
        except Exception:
            pass  # Ignorar errores de auditoría
        
        return {
            'processed': processed,
            'inserted': inserted,
            'updated': updated,
            'errors': len(errors)
        }
    
    except Exception as e:
        error_msg = str(e)
        update_upload_status(upload, 'error', error_message=error_msg)
        
        try:
            create_audit_log(
                usuario=upload.cargado_por,
                accion='error',
                descripcion=f'Error procesando upload {upload.id}: {error_msg}',
                detalles={'upload_id': upload.id, 'error': error_msg}
            )
        except Exception:
            pass
        
        return {'error': error_msg, 'processed': processed, 'inserted': inserted, 'updated': updated}
