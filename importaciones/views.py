import pandas as pd
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from django.core.files.storage import default_storage
from django.http import HttpResponse
from clientes.models import Cliente
from polizas.models import Poliza
from .models import HistorialImportacion, DataFreshness
from .serializers import (
    HistorialImportacionSerializer, 
    DataFreshnessSerializer,
    DataFreshnessEstadisticasSerializer
)
import unicodedata
from datetime import datetime
import logging
import math
from fuzzywuzzy import fuzz
from io import BytesIO

# Importar utilidades de cobranzas
try:
    from cobranzas.utils import crear_cobranza_automatica
except ImportError:
    def crear_cobranza_automatica(*args, **kwargs):
        pass  # Fallback si cobranzas no está disponible

logger = logging.getLogger(__name__)


class ExcelUploadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        file = request.FILES.get("file")
        if not file:
            return Response({"error": "No se envió archivo."}, status=status.HTTP_400_BAD_REQUEST)

        # Guardar temporalmente el archivo
        file_path = default_storage.save(f"temp/{file.name}", file)

        # Obtener la ruta completa del archivo
        full_path = default_storage.path(file_path)

        try:
            # Leer Excel - intentar detectar la fila de encabezados
            df_raw = pd.read_excel(full_path, header=None)
            
            # Encontrar la primera fila que contenga palabras clave de encabezados
            # o que tenga al menos 5 valores no-nulos y solo contenga texto
            header_row = 0
            keywords = ["RUT", "NOMBRE", "POLIZA", "VIGENCIA", "PRIMA", "CLIENTE", "CONTRATANTE", "NUMERO"]
            
            for idx, row in df_raw.iterrows():
                non_null_count = row.notna().sum()
                row_str = " ".join(str(val).upper() for val in row if pd.notna(val))
                
                # Si la fila tiene al menos 5 valores y contiene palabras clave, es probablemente el encabezado
                if non_null_count >= 5 and any(kw in row_str for kw in keywords):
                    header_row = idx
                    break
            
            # Releer el archivo usando la fila detectada como encabezado
            df = pd.read_excel(full_path, header=header_row)
            
            # Si aún tiene columnas "Unnamed", removerlas si están vacías
            df = df.dropna(axis=1, how='all')

            def normalize_column(col_name):
                # Elimina tildes, pasa a mayúsculas y recorta espacios
                normalized = unicodedata.normalize("NFKD", str(col_name))
                normalized = normalized.encode("ascii", "ignore").decode("ascii")
                return normalized.strip().upper()

            normalized_columns = {normalize_column(col): col for col in df.columns}

            # Definir columnas requeridas y sus posibles sinónimos
            column_requirements = {
                "RUT": ["RUT", "RUT_CLIENTE", "RUT_CONTRATANTE", "NUMERO_RUT"],
                "NOMBRE_CLIENTE": ["NOMBRE", "NOMBRE_CLIENTE", "NOMBRE_CONTRATANTE", "NOMBRE_ASEGURADO"],
                "NUMERO_POLIZA": ["POLIZA", "NUMERO_POLIZA", "NUMERO_DE_POLIZA", "POLIZA_NUM"],
                "VIGENCIA": ["VIGENCIA", "FECHA_VIGENCIA", "PERIODO_VIGENCIA"],
                "PRIMA_NETA": ["PRIMA_NETA", "PRIMA_NETA_UF", "PRIMA_UF", "PRIMA"],
            }

            # Mapeo inteligente usando fuzzy matching
            column_map = {}
            for target_col, synonyms in column_requirements.items():
                best_match = None
                best_score = 0
                best_original = None

                for normalized_name, original_name in normalized_columns.items():
                    # Probar cada sinónimo contra la columna normalizada
                    for synonym in synonyms:
                        synonym_normalized = normalize_column(synonym)
                        score = fuzz.ratio(normalized_name, synonym_normalized)
                        
                        if score > best_score:
                            best_score = score
                            best_match = normalized_name
                            best_original = original_name

                # Si el match es bueno (>70%), usar ese mapeo
                if best_score > 70 and best_match:
                    column_map[best_original] = target_col
                    logger.info(f"Mapeado '{best_original}' -> '{target_col}' (score: {best_score})")

            # Aplicar el mapeo
            for original_name, target_name in column_map.items():
                if original_name in df.columns:
                    df.rename(columns={original_name: target_name}, inplace=True)

            # Fallbacks y columnas por defecto
            # Si no existe NUMERO_POLIZA, intentar mapear desde 'NUMERO DOCUMENTO' u otras variantes
            if 'NUMERO_POLIZA' not in df.columns:
                mapped = False
                for norm_name, orig_name in normalized_columns.items():
                    if 'NUMERO' in norm_name and ('DOCUMENT' in norm_name or 'DOCUMENTO' in norm_name or 'NUMERODOCUMENTO' in norm_name):
                        if orig_name in df.columns:
                            df.rename(columns={orig_name: 'NUMERO_POLIZA'}, inplace=True)
                            logger.info(f"Fallback: mapeado '{orig_name}' -> 'NUMERO_POLIZA'")
                            mapped = True
                            break
                if not mapped:
                    # Intentar por coincidencia simple en los nombres actuales del DataFrame
                    for col in df.columns:
                        normcol = normalize_column(col)
                        if 'NUMERO' in normcol and ('DOCUMENT' in normcol or 'DOCUMENTO' in normcol):
                            df.rename(columns={col: 'NUMERO_POLIZA'}, inplace=True)
                            logger.info(f"Fallback: mapeado '{col}' -> 'NUMERO_POLIZA'")
                            mapped = True
                            break

            # La columna COMPANIA se ignora completamente; no se usará para crear/relacionar objetos

            # Añadir columnas adicionales importantes (si faltan) con valores vacíos para conservar la información
            extra_cols = ['Año', 'Mes', 'Número Documento', 'Tipo Documento', 'Ramo', 'Moneda', 'Cantidad Endosos', 'Estado Pago', 'Comisión Porcentaje', 'Es Co Corretaje', 'Porcentaje Participación', 'Convenio', 'Código']
            for col in extra_cols:
                if col not in df.columns:
                    df[col] = None

            # Log para depuración
            logger.info(f"Columnas después del mapeo y fallbacks: {list(df.columns)}")
            if "VIGENCIA" in df.columns:
                logger.info(f"Primeros valores de VIGENCIA: {df['VIGENCIA'].head(3).tolist()}")

            columnas_requeridas = [
                "RUT", "NOMBRE_CLIENTE",
                "NUMERO_POLIZA", "VIGENCIA", "PRIMA_NETA"
            ]

            # Validar columnas finales
            columnas_faltantes = [col for col in columnas_requeridas if col not in df.columns]
            if columnas_faltantes:
                return Response({
                    "error": "No se pudieron mapear todas las columnas requeridas.",
                    "requeridas": columnas_requeridas,
                    "encontradas": list(df.columns),
                    "faltantes": columnas_faltantes,
                    "consejo": "Las columnas del Excel deben ser similares a las requeridas (ej: 'RUT', 'POLIZA', 'VIGENCIA', 'PRIMA')"
                }, status=status.HTTP_400_BAD_REQUEST)

            # Separar el rango de fechas contenido en la columna "VIGENCIA"
            def separar_vigencia(valor):
                try:
                    # Manejar valores nulos
                    if pd.isna(valor):
                        return None, None
                    
                    # Si ya es datetime, retornar como es
                    if isinstance(valor, (pd.Timestamp, datetime)):
                        return valor.date(), valor.date()
                    
                    valor_str = str(valor).strip()
                    
                    # Intentar diferentes separadores (case-insensitive)
                    valor_upper = valor_str.upper()
                    partes = None
                    
                    if " AL " in valor_upper:
                        partes = valor_str.split(" AL ", 1)
                    elif " a " in valor_str and valor_str.count(" a ") == 1:
                        partes = valor_str.split(" a ", 1)
                    elif "-" in valor_str and valor_str.count("-") == 5:  # formato: 01-03-2023 - 10-03-2024 o similar
                        # Dividir manualmente: dd-mm-yyyy AL/a dd-mm-yyyy
                        partes = valor_str.split()
                        if len(partes) >= 3:
                            fecha_ini = partes[0]
                            fecha_fin = partes[-1]
                            partes = [fecha_ini, fecha_fin]
                        else:
                            partes = None
                    
                    if not partes or len(partes) != 2:
                        return None, None
                    
                    fecha_ini = partes[0].strip()
                    fecha_fin = partes[1].strip()
                    
                    # Intentar diferentes formatos de fecha
                    formatos = [
                        "%d/%m/%Y", "%d-%m-%Y",  # Con barras y guiones
                        "%Y-%m-%d", "%Y/%m/%d",  # Formato ISO
                        "%d/%m/%y", "%d-%m-%y",  # 2 dígitos de año
                        "%d.%m.%Y",              # Con puntos
                    ]
                    
                    inicio = None
                    fin = None
                    
                    # Intentar con formatos específicos
                    for fmt in formatos:
                        try:
                            inicio = pd.to_datetime(fecha_ini, format=fmt)
                            if pd.notna(inicio):
                                break
                        except:
                            pass
                    
                    for fmt in formatos:
                        try:
                            fin = pd.to_datetime(fecha_fin, format=fmt)
                            if pd.notna(fin):
                                break
                        except:
                            pass
                    
                    # Si fallan los formatos específicos, intentar con dayfirst=True
                    if pd.isna(inicio):
                        try:
                            inicio = pd.to_datetime(fecha_ini, dayfirst=True, errors='coerce')
                        except:
                            pass
                    
                    if pd.isna(fin):
                        try:
                            fin = pd.to_datetime(fecha_fin, dayfirst=True, errors='coerce')
                        except:
                            pass
                    
                    # Si aún hay problemas, intentar corregir fechas inválidas
                    # Por ejemplo: 31-11-2024 -> 30-11-2024
                    if pd.isna(inicio) and "-" in fecha_ini:
                        try:
                            partes_fecha = fecha_ini.split("-")
                            if len(partes_fecha) == 3:
                                dia, mes, ano = int(partes_fecha[0]), int(partes_fecha[1]), int(partes_fecha[2])
                                # Corregir días inválidos
                                if mes == 2:  # Febrero
                                    dia = min(dia, 29)
                                elif mes in [4, 6, 9, 11]:  # Meses con 30 días
                                    dia = min(dia, 30)
                                else:  # Meses con 31 días
                                    dia = min(dia, 31)
                                inicio = pd.to_datetime(f"{ano}-{mes:02d}-{dia:02d}")
                        except:
                            pass
                    
                    if pd.isna(fin) and "-" in fecha_fin:
                        try:
                            partes_fecha = fecha_fin.split("-")
                            if len(partes_fecha) == 3:
                                dia, mes, ano = int(partes_fecha[0]), int(partes_fecha[1]), int(partes_fecha[2])
                                # Corregir días inválidos
                                if mes == 2:  # Febrero
                                    dia = min(dia, 29)
                                elif mes in [4, 6, 9, 11]:  # Meses con 30 días
                                    dia = min(dia, 30)
                                else:  # Meses con 31 días
                                    dia = min(dia, 31)
                                fin = pd.to_datetime(f"{ano}-{mes:02d}-{dia:02d}")
                        except:
                            pass
                    
                    if pd.isna(inicio) or pd.isna(fin):
                        return None, None
                    
                    return inicio.date(), fin.date()
                except Exception as e:
                    return None, None

            df["FECHA_INICIO"], df["FECHA_VENCIMIENTO"] = zip(*df["VIGENCIA"].apply(separar_vigencia))

            if df["FECHA_INICIO"].isnull().any() or df["FECHA_VENCIMIENTO"].isnull().any():
                # Log para depuración
                filas_con_error = df[df["FECHA_INICIO"].isnull() | df["FECHA_VENCIMIENTO"].isnull()]
                logger.error(f"Filas con fechas inválidas: {filas_con_error['VIGENCIA'].tolist()}")
                return Response({
                    "error": "No se pudieron interpretar las fechas de la columna VIGENCIA. Formato esperado: 'dd/mm/yyyy AL dd/mm/yyyy'.",
                    "muestra": filas_con_error['VIGENCIA'].head(3).tolist()
                }, status=status.HTTP_400_BAD_REQUEST)

            # Convertir montos con comas a float
            for columna_monto in ["PRIMA_NETA", "PRIMA_BRUTA"]:
                if columna_monto in df.columns:
                    df[columna_monto] = (
                        df[columna_monto]
                        .astype(str)
                        .str.replace(".", "", regex=False)  # eliminar separador de miles si existe
                        .str.replace(",", ".", regex=False)
                        .str.strip()
                    )
                    df[columna_monto] = pd.to_numeric(df[columna_monto], errors="coerce")

            # Usar PRIMA_NETA como monto UF si existe
            if "PRIMA_NETA" in df.columns:
                df["MONTO_UF"] = df["PRIMA_NETA"]
            else:
                df["MONTO_UF"] = 0.0

            insertados = 0
            actualizados = 0
            errores = 0
            errores_detalle = []
            polizas_procesadas = set()  # Registrar pólizas únicas procesadas (por número)
            logger.info(f"DEBUG: Iniciando procesamiento de {len(df)} filas")

            for index, row in df.iterrows():
                try:
                    # Validar datos mínimos
                    if pd.isna(row["NUMERO_POLIZA"]) or pd.isna(row["RUT"]):
                        errores += 1
                        logger.debug(f"Fila {index+2}: SKIP - datos incompletos")
                        errores_detalle.append(f"Fila {index+2}: datos incompletos (RUT o NUMERO_POLIZA vacío).")
                        continue

                    # Validar fechas
                    if pd.isna(row["FECHA_INICIO"]) or pd.isna(row["FECHA_VENCIMIENTO"]):
                        errores += 1
                        logger.debug(f"Fila {index+2}: SKIP - fechas inválidas")
                        errores_detalle.append(f"Fila {index+2}: fechas inválidas en VIGENCIA.")
                        continue

                    # Normalizar RUT
                    rut_limpio = str(row["RUT"]).strip().upper()
                    nombre_cliente = str(row["NOMBRE_CLIENTE"]).strip() if pd.notna(row["NOMBRE_CLIENTE"]) else "Sin nombre"

                    cliente, cliente_created = Cliente.objects.get_or_create(
                        rut=rut_limpio,
                        defaults={"nombre": nombre_cliente}
                    )
                    
                    logger.debug(f"Fila {index+2}: Cliente {rut_limpio} (ID={cliente.id}, nuevo={cliente_created})")

                    # Normalizar número de póliza
                    numero_poliza = str(row["NUMERO_POLIZA"]).strip()
                    
                    # Registrar póliza única procesada
                    # IMPORTANTE: Se registra por número de póliza (única por contrato)
                    polizas_procesadas.add(numero_poliza)
                    logger.debug(f"  → polizas_procesadas.add({numero_poliza}), total ahora: {len(polizas_procesadas)}")

                    poliza, poliza_created = Poliza.objects.update_or_create(
                        numero=numero_poliza,
                        defaults={
                            "cliente": cliente,
                            "fecha_inicio": row["FECHA_INICIO"],
                            "fecha_vencimiento": row["FECHA_VENCIMIENTO"],
                            "monto_uf": float(row["MONTO_UF"]) if pd.notna(row["MONTO_UF"]) else 0.0,
                            "estado": "VIGENTE",
                        },
                    )

                    if poliza_created:
                        insertados += 1
                        logger.info(f"Póliza {numero_poliza} insertada correctamente")
                        
                        # Crear cobranza automática para la nueva póliza
                        try:
                            cobranza = crear_cobranza_automatica(poliza, request.user)
                            if cobranza:
                                logger.info(f"Cobranza creada automáticamente para póliza {numero_poliza}")
                        except Exception as e:
                            logger.warning(f"No se pudo crear cobranza para póliza {numero_poliza}: {str(e)}")
                    else:
                        actualizados += 1
                        logger.info(f"Póliza {numero_poliza} actualizada correctamente")

                except Exception as e:
                    errores += 1
                    error_msg = f"Fila {index+2}: {str(e)}"
                    errores_detalle.append(error_msg)
                    logger.error(error_msg)

            # Registrar historial
            logger.info(f"="*70)
            logger.info(f"RESUMEN DE IMPORTACIÓN:")
            logger.info(f"  - Filas procesadas: {len(df)}")
            logger.info(f"  - Pólizas únicas: {len(polizas_procesadas)}")
            logger.info(f"  - Pólizas procesadas: {sorted(polizas_procesadas)[:10]}")
            logger.info(f"  - Pólizas insertadas: {insertados}")
            logger.info(f"  - Pólizas actualizadas: {actualizados}")
            logger.info(f"  - Errores: {errores}")
            logger.info(f"="*70)
            
            historial = HistorialImportacion.objects.create(
                usuario=request.user,
                archivo=file,
                clientes_ingresados=len(polizas_procesadas),
                filas_insertadas=insertados,
                filas_actualizadas=actualizados,
                filas_erroneas=errores,
                mensaje="\n".join(errores_detalle)[:5000],
            )

            # Eliminar archivo temporal
            try:
                default_storage.delete(file_path)
            except:
                pass

            return Response({
                "mensaje": "Archivo procesado exitosamente.",
                "polizas_unicas": len(polizas_procesadas),
                "insertados": insertados,
                "actualizados": actualizados,
                "errores": errores,
                "historial_id": historial.id
            }, status=status.HTTP_200_OK)

        except Exception as e:
            # Eliminar archivo temporal en caso de error
            try:
                default_storage.delete(file_path)
            except:
                pass
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class HistorialImportacionListView(ListAPIView):
    """
    Vista para listar el historial de importaciones
    Accesible por: admin, comercial, auditor
    """
    queryset = HistorialImportacion.objects.all().order_by('-fecha_carga')
    serializer_class = HistorialImportacionSerializer
    permission_classes = [permissions.IsAuthenticated]


class HistorialImportacionDeleteView(APIView):
    """
    Vista para eliminar un registro del historial de importaciones
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def delete(self, request, historial_id):
        # Solo admin puede eliminar
        if not (hasattr(request.user, 'role') and request.user.role == 'admin'):
            return Response(
                {'error': 'Solo administradores pueden eliminar importaciones'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            historial = HistorialImportacion.objects.get(id=historial_id)
            # Eliminar archivo si existe
            if historial.archivo:
                try:
                    default_storage.delete(historial.archivo.name)
                except:
                    pass
            historial.delete()
            return Response({'success': 'Importación eliminada correctamente'}, status=status.HTTP_200_OK)
        except HistorialImportacion.DoesNotExist:
            return Response({'error': 'Importación no encontrada'}, status=status.HTTP_404_NOT_FOUND)


class ExportarPolizasView(APIView):
    """
    Vista para exportar pólizas a Excel con filtros opcionales.
    Todos los usuarios autenticados pueden exportar para análisis.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        try:
            # Obtener parámetros de filtro
            estado = request.query_params.get('estado', None)
            fecha_inicio_desde = request.query_params.get('fecha_inicio_desde', None)
            fecha_inicio_hasta = request.query_params.get('fecha_inicio_hasta', None)
            fecha_venc_desde = request.query_params.get('fecha_venc_desde', None)
            fecha_venc_hasta = request.query_params.get('fecha_venc_hasta', None)
            cliente_rut = request.query_params.get('cliente_rut', None)
            formato = request.query_params.get('formato', 'excel')  # excel o csv

            # Construir query
            polizas = Poliza.objects.select_related('cliente').all()

            if estado:
                polizas = polizas.filter(estado=estado)
            if fecha_inicio_desde:
                polizas = polizas.filter(fecha_inicio__gte=fecha_inicio_desde)
            if fecha_inicio_hasta:
                polizas = polizas.filter(fecha_inicio__lte=fecha_inicio_hasta)
            if fecha_venc_desde:
                polizas = polizas.filter(fecha_vencimiento__gte=fecha_venc_desde)
            if fecha_venc_hasta:
                polizas = polizas.filter(fecha_vencimiento__lte=fecha_venc_hasta)
            if cliente_rut:
                polizas = polizas.filter(cliente__rut__icontains=cliente_rut)

            # Preparar datos para el DataFrame
            data = []
            for poliza in polizas:
                data.append({
                    'Número Póliza': poliza.numero,
                    'RUT Cliente': poliza.cliente.rut,
                    'Nombre Cliente': poliza.cliente.nombre,
                    'Fecha Inicio': poliza.fecha_inicio.strftime('%d-%m-%Y'),
                    'Fecha Vencimiento': poliza.fecha_vencimiento.strftime('%d-%m-%Y'),
                    'Monto UF': float(poliza.monto_uf),
                    'Estado': poliza.estado,
                    'Fecha Creación': poliza.created_at.strftime('%d-%m-%Y %H:%M'),
                    'Última Actualización': poliza.updated_at.strftime('%d-%m-%Y %H:%M'),
                })

            # Crear DataFrame
            df = pd.DataFrame(data)

            # Generar archivo según formato
            if formato == 'csv':
                # Exportar como CSV
                response = HttpResponse(content_type='text/csv; charset=utf-8')
                response['Content-Disposition'] = f'attachment; filename="polizas_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
                df.to_csv(response, index=False, encoding='utf-8-sig')
                return response
            else:
                # Exportar como Excel
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, sheet_name='Pólizas', index=False)
                    
                    # Ajustar ancho de columnas
                    worksheet = writer.sheets['Pólizas']
                    for idx, col in enumerate(df.columns):
                        max_length = max(df[col].astype(str).apply(len).max(), len(col)) + 2
                        worksheet.column_dimensions[chr(65 + idx)].width = min(max_length, 50)

                output.seek(0)
                response = HttpResponse(
                    output.read(),
                    content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
                response['Content-Disposition'] = f'attachment; filename="polizas_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx"'
                return response

        except Exception as e:
            logger.error(f"Error al exportar pólizas: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ExportarHistorialView(APIView):
    """
    Vista para exportar historial de importaciones.
    Todos los usuarios autenticados pueden exportar para análisis.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        try:
            # Obtener parámetros
            fecha_desde = request.query_params.get('fecha_desde', None)
            fecha_hasta = request.query_params.get('fecha_hasta', None)
            formato = request.query_params.get('formato', 'excel')

            # Construir query
            historial = HistorialImportacion.objects.all().order_by('-fecha_carga')

            if fecha_desde:
                historial = historial.filter(fecha_carga__gte=fecha_desde)
            if fecha_hasta:
                historial = historial.filter(fecha_carga__lte=fecha_hasta)

            # Preparar datos
            data = []
            for item in historial:
                data.append({
                    'ID': item.id,
                    'Fecha Carga': item.fecha_carga.strftime('%d-%m-%Y %H:%M:%S'),
                    'Nombre Archivo': item.nombre_archivo,
                    'Filas Insertadas': item.filas_insertadas,
                    'Filas Actualizadas': item.filas_actualizadas,
                    'Filas Erróneas': item.filas_erroneas,
                    'Total Filas': item.filas_insertadas + item.filas_actualizadas + item.filas_erroneas,
                    'Tasa Éxito': f"{round((item.filas_insertadas / (item.filas_insertadas + item.filas_erroneas) * 100) if (item.filas_insertadas + item.filas_erroneas) > 0 else 0, 2)}%",
                })

            df = pd.DataFrame(data)

            # Generar archivo
            if formato == 'csv':
                response = HttpResponse(content_type='text/csv; charset=utf-8')
                response['Content-Disposition'] = f'attachment; filename="historial_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
                df.to_csv(response, index=False, encoding='utf-8-sig')
                return response
            else:
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, sheet_name='Historial', index=False)
                    
                    worksheet = writer.sheets['Historial']
                    for idx, col in enumerate(df.columns):
                        max_length = max(df[col].astype(str).apply(len).max(), len(col)) + 2
                        worksheet.column_dimensions[chr(65 + idx)].width = min(max_length, 50)

                output.seek(0)
                response = HttpResponse(
                    output.read(),
                    content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
                response['Content-Disposition'] = f'attachment; filename="historial_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx"'
                return response

        except Exception as e:
            logger.error(f"Error al exportar historial: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    permission_classes = [permissions.IsAuthenticated]


# ============================================================================
# ENDPOINTS DEL PIPELINE ETL (FASE 1 PASO 6)
# ============================================================================

from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from .models import DataUpload, ImportErrorRow
from .serializers import DataUploadSerializer, ImportErrorRowSerializer
from .etl import process_upload


class UploadExcelETLView(APIView):
    """
    POST /api/etl/upload-excel/
    Sube archivo y crea DataUpload, inicia procesamiento ETL (sincrónico o Celery)
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        file = request.FILES.get('file')
        if not file:
            return Response(
                {'error': 'No file provided'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Crear DataUpload
            upload = DataUpload.objects.create(
                archivo=file,
                cargado_por=request.user,
                estado='pendiente'
            )

            # Opción 1: Procesamiento sincrónico (rápido para testing)
            # Comentar si quieres usar Celery
            result = process_upload(upload.id, run_ml=False)
            
            # Opción 2: Procesamiento asincrónico con Celery (descomenta si lo usas)
            # from importaciones.tasks import process_upload_task
            # process_upload_task.delay(upload.id)

            return Response({
                'upload_id': upload.id,
                'status': upload.estado,
                'result': result
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class DataUploadDetailView(APIView):
    """
    GET /api/etl/upload/<upload_id>/
    Obtiene estado detallado de un upload
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, upload_id):
        try:
            upload = DataUpload.objects.get(id=upload_id)
            serializer = DataUploadSerializer(upload)
            return Response(serializer.data)
        except DataUpload.DoesNotExist:
            return Response(
                {'error': 'Upload not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class UploadErrorsDownloadView(APIView):
    """
    GET /api/etl/upload/<upload_id>/download-errors/
    Descarga CSV con filas de error
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, upload_id):
        try:
            upload = DataUpload.objects.get(id=upload_id)
            
            if not upload.error_file:
                return Response(
                    {'error': 'No error file for this upload'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Retornar archivo
            response = HttpResponse(
                upload.error_file.read(),
                content_type='text/csv'
            )
            response['Content-Disposition'] = f'attachment; filename="{upload.error_file.name.split("/")[-1]}"'
            return response
        
        except DataUpload.DoesNotExist:
            return Response(
                {'error': 'Upload not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class DataUploadViewSet(ModelViewSet):
    """
    GET /api/etl/uploads/
    GET /api/etl/uploads/<id>/
    DELETE /api/etl/uploads/<id>/
    
    Lista todos los uploads con filtros opcionales
    Permite eliminar registros de importación (solo admin)
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DataUploadSerializer
    filterset_fields = ['estado', 'cargado_por']
    ordering_fields = ['fecha_carga', 'estado']
    ordering = ['-fecha_carga']

    def get_queryset(self):
        # Los usuarios ven solo sus uploads, admins ven todos
        user = self.request.user
        if hasattr(user, 'role') and user.role == 'admin':
            return DataUpload.objects.all()
        return DataUpload.objects.filter(cargado_por=user)
    
    def destroy(self, request, *args, **kwargs):
        """Eliminar un registro de importación (solo admin)"""
        # Verificar permiso: solo admin puede eliminar
        if not (hasattr(request.user, 'role') and request.user.role == 'admin'):
            return Response(
                {'error': 'Solo administradores pueden eliminar importaciones'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        return super().destroy(request, *args, **kwargs)


class ImportErrorRowViewSet(ReadOnlyModelViewSet):
    """
    GET /api/etl/upload-errors/
    GET /api/etl/upload-errors/<id>/
    
    Lista errores de importación de un upload
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ImportErrorRowSerializer
    filterset_fields = ['upload', 'row_number']
    ordering_fields = ['row_number', 'created_at']
    ordering = ['row_number']

    def get_queryset(self):
        upload_id = self.request.query_params.get('upload_id')
        if upload_id:
            return ImportErrorRow.objects.filter(upload_id=upload_id)
        return ImportErrorRow.objects.all()


# ========== ENDPOINTS PARA FRESCURA DE DATOS (PASO 15) ==========

class DataFreshnessListView(ListAPIView):
    """
    GET /api/importaciones/frescura/
    
    Lista el estado de frescura de datos para todos los clientes
    Permite filtros por estado de frescura
    Accesible por: admin, comercial, auditor
    
    Ejemplo respuesta:
    [
        {
            "id": 1,
            "cliente": "14123456-8",
            "ultima_actualizacion": "2025-12-01",
            "dias_sin_actualizacion": 15,
            "alerta_frescura": false,
            "fecha_ultima_carga": "2025-12-01",
            "usuario_ultima_carga_username": "admin1",
            "registros_actualizados": 25,
            "estado_frescura": {
                "status": "BUENO",
                "emoji": "✔️",
                "dias": 15,
                "confiable": true,
                "mensaje": "Datos actualizados hace 15 días - Buena calidad"
            }
        }
    ]
    """
    queryset = DataFreshness.objects.all().order_by('-dias_sin_actualizacion')
    serializer_class = DataFreshnessSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['cliente', 'alerta_frescura']
    ordering_fields = ['dias_sin_actualizacion', 'ultima_actualizacion']


class DataFreshnessDetailView(RetrieveAPIView):
    """
    GET /api/importaciones/frescura/<cliente>/
    
    Obtiene el estado de frescura para un cliente específico
    Accesible por: admin, comercial, auditor
    
    Ejemplo respuesta:
    {
        "id": 1,
        "cliente": "14123456-8",
        "ultima_actualizacion": "2025-12-01",
        "dias_sin_actualizacion": 15,
        "alerta_frescura": false,
        "fecha_ultima_carga": "2025-12-01",
        "usuario_ultima_carga_username": "admin1",
        "registros_actualizados": 25,
        "estado_frescura": {
            "status": "BUENO",
            "emoji": "✔️",
            "dias": 15,
            "confiable": true,
            "mensaje": "Datos actualizados hace 15 días - Buena calidad"
        }
    }
    """
    queryset = DataFreshness.objects.all()
    serializer_class = DataFreshnessSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'cliente'
    lookup_url_kwarg = 'cliente'


class DataFreshnessEstadisticasView(APIView):
    """
    GET /api/importaciones/frescura/estadisticas/
    
    Obtiene estadísticas globales de frescura de datos
    Accesible por: admin, comercial, auditor
    
    Retorna:
    {
        "total_clientes": 145,
        "clientes_frescos": 120,
        "clientes_con_advertencia": 18,
        "clientes_criticos": 7,
        "porcentaje_fresco": 82.76,
        "porcentaje_advertencia": 12.41,
        "porcentaje_critico": 4.83,
        "clientes_desactualizados": [
            "14123456-8",
            "15987654-3",
            "16123456-9"
        ]
    }
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        # Obtener estadísticas del modelo DataFreshness
        estadisticas = DataFreshness.obtener_estadisticas_frescura()
        
        # Usar el serializer para validar la respuesta
        serializer = DataFreshnessEstadisticasSerializer(estadisticas)
        return Response(serializer.data)


class DataFreshnessCheckView(APIView):
    """
    POST /api/importaciones/frescura/verificar/
    
    Verifica si los datos de un cliente están frescos
    Requiere un días_limite (default: 30 días)
    
    Ejemplo request:
    {
        "cliente": "14123456-8",
        "dias_limite": 30
    }
    
    Ejemplo respuesta:
    {
        "cliente": "14123456-8",
        "es_fresca": true,
        "dias_sin_actualizar": 15,
        "estado_frescura": {
            "status": "BUENO",
            "emoji": "✔️",
            "dias": 15,
            "confiable": true,
            "mensaje": "Datos actualizados hace 15 días - Buena calidad"
        }
    }
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        cliente = request.data.get('cliente')
        dias_limite = request.data.get('dias_limite', 30)
        
        if not cliente:
            return Response(
                {'error': 'Cliente es requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            data_freshness = DataFreshness.objects.get(cliente=cliente)
            es_fresca = data_freshness.es_fresca(dias_limite=dias_limite)
            estado = data_freshness.obtener_estado_frescura()
            
            return Response({
                'cliente': cliente,
                'es_fresca': es_fresca,
                'dias_sin_actualizar': data_freshness.dias_sin_actualizacion,
                'estado_frescura': estado
            })
        except DataFreshness.DoesNotExist:
            return Response(
                {'error': f'No se encontraron datos de frescura para cliente {cliente}'},
                status=status.HTTP_404_NOT_FOUND
            )


class DataFreshnessClientesDesactualizadosView(APIView):
    """
    GET /api/importaciones/frescura/desactualizados/
    
    Lista clientes con datos desactualizados (>30 días)
    Permite especificar días_limite como query param
    
    Ejemplo: GET /api/importaciones/frescura/desactualizados/?dias_limite=45
    
    Respuesta:
    {
        "total": 7,
        "dias_limite": 30,
        "clientes": [
            {
                "cliente": "14123456-8",
                "dias_sin_actualizar": 45,
                "ultima_actualizacion": "2025-10-17",
                "estado_frescura": {
                    "status": "CRITICO",
                    "emoji": "🔴",
                    "dias": 45,
                    "confiable": false,
                    "mensaje": "CRÍTICO: Datos no actualizados hace 45 días"
                }
            }
        ]
    }
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        dias_limite = int(request.query_params.get('dias_limite', 30))
        
        clientes_desactualizados = DataFreshness.obtener_clientes_desactualizados(
            dias_limite=dias_limite
        )
        
        clientes_data = []
        for data_freshness in clientes_desactualizados:
            clientes_data.append({
                'cliente': data_freshness.cliente,
                'dias_sin_actualizar': data_freshness.dias_sin_actualizacion,
                'ultima_actualizacion': data_freshness.ultima_actualizacion,
                'estado_frescura': data_freshness.obtener_estado_frescura()
            })
        
        return Response({
            'total': len(clientes_data),
            'dias_limite': dias_limite,
            'clientes': clientes_data
        })


class HistorialEstadisticasView(APIView):
    """
    Vista para obtener estadísticas generales del historial de importaciones
    Retorna: total de pólizas únicas, cantidad de importaciones, etc.
    
    GET /api/importaciones/historial-estadisticas/
    
    Respuesta:
    {
        "total_polizas_unicas": 1403,
        "total_importaciones": 14,
        "promedio_polizas_por_importacion": 233.83,
        "ultima_importacion": {
            "fecha": "2025-12-09T15:41:53.315473Z",
            "polizas": 1403,
            "archivo": "Produccion_11-11-2025_3_qMo4rx3.xlsx"
        }
    }
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        from django.db.models import Sum, Count, Q
        
        # Obtener estadísticas
        total_importaciones = HistorialImportacion.objects.count()
        
        # Total de pólizas únicas
        total_polizas_unicas = Poliza.objects.values('numero').distinct().count()
        
        # Promedio (solo de las que tienen contador)
        importaciones_con_datos = HistorialImportacion.objects.filter(
            clientes_ingresados__gt=0
        ).count()
        promedio = (
            total_polizas_unicas / importaciones_con_datos 
            if importaciones_con_datos > 0 
            else 0
        )
        
        # Última importación
        ultima_importacion = HistorialImportacion.objects.all().order_by('-fecha_carga').first()
        ultima_info = None
        if ultima_importacion:
            ultima_info = {
                'fecha': ultima_importacion.fecha_carga.isoformat(),
                'polizas': ultima_importacion.clientes_ingresados,
                'archivo': ultima_importacion.archivo.name if ultima_importacion.archivo else 'N/A'
            }
        
        return Response({
            'total_polizas_unicas': total_polizas_unicas,
            'total_importaciones': total_importaciones,
            'promedio_polizas_por_importacion': round(promedio, 2),
            'ultima_importacion': ultima_info
        }, status=status.HTTP_200_OK)


class VisualizarDatosImportacionView(APIView):
    """
    Vista para visualizar el Excel original de una importación
    Lee el archivo Excel y devuelve todas las hojas y datos en formato JSON
    
    GET /api/importaciones/visualizar/<int:historial_id>/
    
    Respuesta:
    {
        "importacion": {
            "id": 1,
            "fecha_carga": "2025-12-09T15:41:53",
            "archivo": "Produccion_11-11-2025.xlsx"
        },
        "excel_data": {
            "sheets": ["Hoja1", "Hoja2"],
            "data": {
                "Hoja1": {
                    "headers": ["RUT", "Nombre", "Póliza", ...],
                    "rows": [
                        ["12345678-9", "JUAN PEREZ", "X-P-125623", ...],
                        ...
                    ]
                }
            }
        },
        "total_hojas": 1,
        "total_filas": 1403
    }
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, historial_id):
        print(f"[DEBUG] VisualizarDatosImportacionView - historial_id: {historial_id}")
        try:
            historial = HistorialImportacion.objects.get(id=historial_id)
            print(f"[DEBUG] Historial encontrado: {historial.id}, archivo: {historial.archivo.name if historial.archivo else 'None'}")
            
            # Verificar que el archivo existe
            if not historial.archivo:
                return Response(
                    {'error': 'No hay archivo asociado a esta importación'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            try:
                # Leer el archivo Excel desde storage
                archivo_name = historial.archivo.name
                print(f"[DEBUG] Verificando archivo: {archivo_name}")
                
                if not default_storage.exists(archivo_name):
                    print(f"[DEBUG] Archivo NO existe: {archivo_name}")
                    return Response(
                        {'error': 'El archivo Excel no existe en el sistema'},
                        status=status.HTTP_404_NOT_FOUND
                    )
                
                print(f"[DEBUG] Archivo existe, abriendo...")
                with default_storage.open(archivo_name, 'rb') as f:
                    excel_file = pd.ExcelFile(f)
                    sheet_names = excel_file.sheet_names
                    print(f"[DEBUG] Hojas encontradas: {sheet_names}")
                    
                    excel_data = {
                        'sheets': sheet_names,
                        'data': {}
                    }
                    
                    total_filas = 0

                    def make_json_safe(value):
                        if value is None:
                            return None
                        if hasattr(value, 'item'):
                            value = value.item()
                        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
                            return None
                        if hasattr(value, 'isoformat'):
                            return value.isoformat()
                        return value
                    
                    # Leer cada hoja
                    for sheet_name in sheet_names:
                        # Reabrir el archivo para cada hoja
                        with default_storage.open(historial.archivo.name, 'rb') as f2:
                            df = pd.read_excel(f2, sheet_name=sheet_name)
                            
                            # Convertir NaN a None para JSON
                            df = df.where(pd.notnull(df), None)
                            
                            # Extraer headers (convertir a string)
                            headers = [str(h) for h in df.columns.tolist()]
                            
                            # Convertir filas asegurando tipos JSON serializables
                            rows = []
                            for idx, row in df.head(1000).iterrows():  # Limitar a 1000 filas
                                new_row = []
                                for val in row:
                                    new_row.append(make_json_safe(val))
                                rows.append(new_row)
                            
                            excel_data['data'][sheet_name] = {
                                'headers': headers,
                                'rows': rows
                            }
                            
                            total_filas += len(df)
                
                print(f"[DEBUG] Datos procesados: {len(sheet_names)} hojas, {total_filas} filas total")
                return Response({
                    'importacion': {
                        'id': historial.id,
                        'fecha_carga': historial.fecha_carga.isoformat(),
                        'archivo': historial.archivo.name.split('/')[-1],
                        'clientes_ingresados': historial.clientes_ingresados
                    },
                    'excel_data': excel_data,
                    'total_hojas': len(sheet_names),
                    'total_filas': total_filas
                }, status=status.HTTP_200_OK)
                
            except Exception as e:
                logger.error(f"Error leyendo Excel: {e}")
                return Response(
                    {'error': f'Error al leer el archivo Excel: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
        except HistorialImportacion.DoesNotExist:
            return Response(
                {'error': 'Importación no encontrada'},
                status=status.HTTP_404_NOT_FOUND
            )

