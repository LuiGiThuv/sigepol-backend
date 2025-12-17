"""
API Endpoints para carga y validación de Excel mejorados
MÓDULO 2: PASO 2.2, 2.3, 2.4, 2.5
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.core.files.storage import default_storage
from django.utils import timezone
from .models import DataUpload
from .validators import ValidadorExcel, GeneradorPreview
import logging
import os

logger = logging.getLogger(__name__)


class ExcelPreviewView(APIView):
    """
    Vista para obtener preview de un archivo Excel antes de procesarlo
    MÓDULO 2: PASO 2.4 — Vista previa del Excel
    
    POST /api/importaciones/preview/
    {
        "file": <file>
    }
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """Recibe un archivo y retorna preview"""
        file = request.FILES.get('file')
        
        if not file:
            return Response(
                {'error': 'No se envió archivo'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Guardar temporalmente
            temp_path = default_storage.save(f'temp/preview_{file.name}', file)
            full_path = default_storage.path(temp_path)
            
            # Generar preview
            preview = GeneradorPreview.generar(full_path)
            
            # Limpiar archivo temporal
            try:
                default_storage.delete(temp_path)
            except:
                pass
            
            return Response(preview, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error en preview: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class ExcelValidationView(APIView):
    """
    Vista para validar la estructura de un Excel
    MÓDULO 2: PASO 2.3 — Validación estructural
    
    POST /api/importaciones/validar/
    {
        "file": <file>
    }
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """Valida un archivo Excel y retorna errores/advertencias"""
        file = request.FILES.get('file')
        
        if not file:
            return Response(
                {'error': 'No se envió archivo'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Guardar temporalmente
            temp_path = default_storage.save(f'temp/validation_{file.name}', file)
            full_path = default_storage.path(temp_path)
            
            # Validar estructura
            validador = ValidadorExcel(full_path)
            es_valido, reporte = validador.validar()
            
            # Limpiar archivo temporal
            try:
                default_storage.delete(temp_path)
            except:
                pass
            
            response_data = {
                'valido': es_valido,
                **reporte
            }
            
            status_code = status.HTTP_200_OK if es_valido else status.HTTP_400_BAD_REQUEST
            return Response(response_data, status=status_code)
            
        except Exception as e:
            logger.error(f"Error en validación: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class ExcelUploadMejoradoView(APIView):
    """
    Vista mejorada para cargar Excel
    MÓDULO 2: PASO 2.1, 2.2 — Guardado y registro de Excel
    
    POST /api/importaciones/upload-mejorado/
    {
        "file": <file>,
        "tipo_carga": "polizas|cobranzas|clientes" (opcional, se detecta)
    }
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """Carga un Excel con validación y guardado mejorado"""
        file = request.FILES.get('file')
        
        if not file:
            return Response(
                {'error': 'No se envió archivo'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # 1. GUARDAR ARCHIVO ORIGINAL EN MEDIA (PASO 2.2)
            ruta_archivo = default_storage.save(
                f'excel_uploads/{timezone.now().strftime("%Y/%m/%d")}/{file.name}',
                file
            )
            full_path = default_storage.path(ruta_archivo)
            
            # 2. VALIDAR ESTRUCTURA (PASO 2.3)
            validador = ValidadorExcel(full_path)
            es_valido, reporte_validacion = validador.validar()
            
            # 3. GENERAR PREVIEW (PASO 2.4)
            preview = GeneradorPreview.generar(full_path)
            
            # 4. CREAR REGISTRO EN BD (PASO 2.1)
            data_upload = DataUpload.objects.create(
                archivo=ruta_archivo,
                nombre_archivo_original=file.name,
                cargado_por=request.user,
                estado='validando',
                columnas_detectadas=validador.columnas_detectadas,
                columnas_validadas=es_valido,
                errores_validacion=reporte_validacion.get('errores', []),
                preview_filas=preview.get('filas_preview', []),
            )
            
            logger.info(f"Excel cargado: {data_upload.id} - {file.name}")
            
            # 5. REGISTRAR EN AUDITORÍA
            try:
                from auditorias.models import AuditoriaAccion
                AuditoriaAccion.registrar(
                    usuario=request.user,
                    accion='CREATE',
                    modulo='importaciones',
                    modelo='DataUpload',
                    descripcion=f'Carga de archivo Excel: {file.name}',
                    objeto_id=data_upload.id,
                    ip_address=self._get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')[:255],
                    metodo_http='POST',
                    url=request.path,
                    exitoso=es_valido,
                )
            except Exception as e:
                logger.warning(f"No se registró auditoría: {str(e)}")
            
            # 6. RETORNAR RESPUESTA
            return Response({
                'id': data_upload.id,
                'archivo': file.name,
                'estado': 'validado' if es_valido else 'validacion_fallida',
                'valido': es_valido,
                'validacion': reporte_validacion,
                'preview': preview,
                'mensaje': 'Archivo listo para procesar' if es_valido else 'Revisa los errores de validación',
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Error en upload: {str(e)}", exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @staticmethod
    def _get_client_ip(request):
        """Obtiene IP del cliente"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class HistorialCargasView(APIView):
    """
    Vista para obtener historial de cargas de Excel
    MÓDULO 2: PASO 2.5 — Historial de cargas
    
    GET /api/importaciones/historial-cargas/
    Parámetros query:
        - limit: número de registros (default: 20)
        - estado: filtrar por estado
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Retorna historial de cargas"""
        # Filtrar por usuario (o todos si es admin)
        if request.user.role == 'admin':
            cargas = DataUpload.objects.all()
        else:
            cargas = DataUpload.objects.filter(cargado_por=request.user)
        
        # Filtrar por estado si se proporciona
        estado = request.query_params.get('estado')
        if estado:
            cargas = cargas.filter(estado=estado)
        
        # Limitar resultados
        limit = int(request.query_params.get('limit', 20))
        cargas = cargas[:limit]
        
        # Serializar
        datos = []
        for carga in cargas:
            datos.append({
                'id': carga.id,
                'archivo': carga.nombre_archivo_original,
                'estado': carga.get_estado_display(),
                'fecha_carga': carga.fecha_carga.isoformat(),
                'usuario': carga.cargado_por.username,
                'filas_procesadas': carga.processed_rows,
                'filas_insertadas': carga.inserted_rows,
                'filas_actualizadas': carga.updated_rows,
                'filas_error': carga.processed_rows - carga.inserted_rows - carga.updated_rows,
                'puede_descargar': True,
                'descargado': carga.descargado,
            })
        
        return Response({
            'total': len(datos),
            'cargas': datos,
        })


class DescargarExcelOriginalView(APIView):
    """
    Endpoint para descargar el archivo Excel original guardado
    MÓDULO 2: PASO 2.2 — Nunca borrar el original
    
    GET /api/importaciones/descargar/{id}/
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, pk):
        """Descarga el archivo original"""
        try:
            carga = DataUpload.objects.get(pk=pk)
            
            # Verificar permisos (solo el que lo cargó o admin)
            if request.user != carga.cargado_por and request.user.role != 'admin':
                return Response(
                    {'error': 'No tienes permiso para descargar este archivo'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Obtener archivo
            if not carga.archivo:
                return Response(
                    {'error': 'Archivo no encontrado'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Marcar como descargado
            carga.marcar_descargado()
            
            # Retornar archivo
            file_path = carga.archivo.path
            with open(file_path, 'rb') as f:
                from django.http import FileResponse
                response = FileResponse(f, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                response['Content-Disposition'] = f'attachment; filename="{carga.nombre_archivo_original}"'
                return response
                
        except DataUpload.DoesNotExist:
            return Response(
                {'error': 'Carga no encontrada'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error descargando archivo: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
