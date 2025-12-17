"""
Dashboard Analytics - Admin System Statistics and Metrics
PASO 8: Dashboard Administrador Profesional

Provides comprehensive statistics for:
- System metrics (users, uploads, errors)
- Business metrics (policies, premiums)
- ETL performance
- Alerts summary
- Recent activity (audit logs)
- Preparation for ML metrics (FASE 2)
"""

from django.utils import timezone
from django.db.models import Count, Sum, Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from datetime import timedelta

from polizas.models import Poliza
from usuarios.models import User
from importaciones.models import DataUpload
from alertas.models import Alerta
from auditorias.models import AuditoriaAccion
from usuarios.permissions import IsAdmin


class AdminSystemStatsView(APIView):
    """
    PASO 8.1: System statistics API
    Returns overall system health metrics
    """
    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    def get(self, request):
        """Get system statistics"""
        try:
            total_usuarios = User.objects.count()
            total_alertas_activas = Alerta.objects.filter(
                estado__in=['PENDIENTE', 'LEIDA']
            ).count()

            total_cargas = DataUpload.objects.count()
            cargas_hoy = DataUpload.objects.filter(
                fecha_carga__date=timezone.now().date()
            ).count()

            errores_carga = DataUpload.objects.filter(
                estado__in=['error']
            ).count()

            cargas_exitosas = DataUpload.objects.filter(
                estado__in=['completado']
            ).count()

            # Calculate success rate
            if total_cargas > 0:
                tasa_exito = round((cargas_exitosas / total_cargas) * 100, 2)
            else:
                tasa_exito = 0

            return Response({
                "usuarios": total_usuarios,
                "alertas_activas": total_alertas_activas,
                "cargas_totales": total_cargas,
                "cargas_hoy": cargas_hoy,
                "errores_carga": errores_carga,
                "cargas_exitosas": cargas_exitosas,
                "tasa_exito": tasa_exito,
            })
        except Exception as e:
            return Response(
                {"error": str(e), "usuarios": 0, "alertas_activas": 0, "cargas_totales": 0, "tasa_exito": 0},
                status=500
            )


class AdminBusinessStatsView(APIView):
    """
    PASO 8.2: Business metrics API
    Returns business-related statistics
    """
    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    def get(self, request):
        """Get business statistics"""
        try:
            total_polizas = Poliza.objects.count()
            polizas_vigentes = Poliza.objects.filter(
                estado__in=['vigente', 'VIGENTE']
            ).count()

            cargas_exitosas = DataUpload.objects.filter(
                fecha_carga__date=timezone.now().date(),
                estado='completado'
            ).count()

            prima_total = Poliza.objects.aggregate(
                total=Sum('monto_uf')
            )['total'] or 0

            # Today's production
            polizas_hoy = Poliza.objects.filter(
                fecha_inicio=timezone.now().date()
            ).count()

            # Last 7 days
            fecha_7_dias_atras = timezone.now().date() - timedelta(days=7)
            polizas_7_dias = Poliza.objects.filter(
                fecha_inicio__gte=fecha_7_dias_atras
            ).count()

            # Last 30 days
            fecha_30_dias_atras = timezone.now().date() - timedelta(days=30)
            polizas_30_dias = Poliza.objects.filter(
                fecha_inicio__gte=fecha_30_dias_atras
            ).count()

            return Response({
                "polizas_totales": total_polizas,
                "polizas_vigentes": polizas_vigentes,
                "prima_total_uf": float(prima_total),
                "produccion_hoy": polizas_hoy,
                "produccion_7_dias": polizas_7_dias,
                "produccion_30_dias": polizas_30_dias,
            })
        except Exception as e:
            return Response(
                {"error": str(e), "polizas_totales": 0, "polizas_vigentes": 0, "prima_total_uf": 0},
                status=500
            )


class AdminRecentActivityView(APIView):
    """
    PASO 8.3: Recent activity/audit logs API
    Returns last 50 audit actions for system monitoring
    """
    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    def get(self, request):
        """Get recent audit activities"""
        try:
            limit = int(request.query_params.get('limit', 50))
            logs = AuditoriaAccion.objects.select_related('usuario').order_by("-fecha_hora")[:limit]

            data = [
                {
                    "id": log.id,
                    "usuario_nombre": log.usuario.get_full_name() or log.usuario.username if log.usuario else "Sistema",
                    "accion": log.accion,
                    "descripcion": log.descripcion,
                    "modulo": log.modulo,
                    "modelo": log.modelo,
                    "detalles": log.descripcion,
                    "fecha_accion": log.fecha_hora,
                    "exitoso": log.exitoso,
                    "ip_address": log.ip_address,
                    "metodo_http": log.metodo_http,
                }
                for log in logs
            ]
            return Response(data)
        except Exception as e:
            return Response({"error": str(e)}, status=500)


class AdminETLStatsView(APIView):
    """
    PASO 8.4: ETL performance metrics API
    Returns upload statistics and performance indicators
    """
    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    def get(self, request):
        """Get ETL statistics"""
        try:
            limit = int(request.query_params.get('limit', 10))
            uploads = DataUpload.objects.select_related('cargado_por').order_by("-fecha_carga")[:limit]

            data = [
                {
                    "id": u.id,
                    "archivo": u.archivo.name if u.archivo else "desconocido",
                    "tipo_carga": "General",
                    "estado": u.estado,
                    "procesadas": u.processed_rows or 0,
                    "filas_insertadas": u.inserted_rows or 0,
                    "filas_actualizadas": u.updated_rows or 0,
                    "filas_erroneas": 0,  # DataUpload no tiene error_rows, pero se puede calcular
                    "tasa_error": round(
                        ((u.processed_rows - u.inserted_rows - u.updated_rows) / u.processed_rows * 100) 
                        if u.processed_rows > 0 else 0,
                        2
                    ),
                    "mensaje_error": u.mensaje_error or "",
                    "fecha_carga": u.fecha_carga,
                    "cargado_por": u.cargado_por.get_full_name() or u.cargado_por.username if u.cargado_por else "N/A",
                }
                for u in uploads
            ]
            return Response(data)
        except Exception as e:
            return Response({"error": str(e)}, status=500)


class AdminAlertSummaryView(APIView):
    """
    PASO 8.5: Alerts summary API
    Returns alert status and distribution
    """
    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    def get(self, request):
        """Get alert statistics"""
        try:
            # Alerts by type
            alertas_por_tipo = list(
                Alerta.objects.filter(estado__in=['PENDIENTE', 'LEIDA'])
                .values('tipo')
                .annotate(total=Count('id'))
                .order_by('-total')
            )

            # Alerts by severity
            alertas_por_severidad = list(
                Alerta.objects.filter(estado__in=['PENDIENTE', 'LEIDA'])
                .values('severidad')
                .annotate(total=Count('id'))
                .order_by('-total')
            )

            alertas_activas = Alerta.objects.filter(
                estado__in=['PENDIENTE', 'LEIDA']
            ).count()

            alertas_vencidas = Alerta.objects.filter(
                fecha_limite__lt=timezone.now(),
                estado='PENDIENTE'
            ).count()

            return Response({
                "alertas_activas": alertas_activas,
                "alertas_vencidas": alertas_vencidas,
                "por_tipo": alertas_por_tipo,
                "por_severidad": alertas_por_severidad,
                "total_resuelta": Alerta.objects.filter(estado='RESUELTA').count(),
                "total_descartada": Alerta.objects.filter(estado='DESCARTADA').count(),
            })
        except Exception as e:
            return Response({"error": str(e)}, status=500)


class AdminDashboardOverviewView(APIView):
    """
    PASO 8.6: Complete dashboard overview
    Integrates all metrics into a single endpoint for initial load
    """
    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    def get(self, request):
        """Get complete dashboard overview"""
        try:
            # System stats
            total_usuarios = User.objects.count()
            total_alertas_activas = Alerta.objects.filter(
                estado__in=['PENDIENTE', 'LEIDA']
            ).count()
            total_cargas = DataUpload.objects.count()
            cargas_exitosas = DataUpload.objects.filter(
                estado='completado'
            ).count()

            if total_cargas > 0:
                tasa_exito = round((cargas_exitosas / total_cargas) * 100, 2)
            else:
                tasa_exito = 0

            # Business stats
            total_polizas = Poliza.objects.count()
            polizas_vigentes = Poliza.objects.filter(
                estado__in=['vigente', 'VIGENTE']
            ).count()
            prima_total = Poliza.objects.aggregate(
                total=Sum('monto_uf')
            )['total'] or 0

            # Recent logs (last 50)
            logs = AuditoriaAccion.objects.select_related('usuario').order_by("-fecha_hora")[:50]
            recent_activity = [
                {
                    "id": log.id,
                    "usuario_nombre": log.usuario.get_full_name() or log.usuario.username if log.usuario else "Sistema",
                    "accion": log.accion,
                    "descripcion": log.descripcion,
                    "modulo": log.modulo,
                    "detalles": log.descripcion,
                    "fecha_accion": log.fecha_hora,
                    "exitoso": log.exitoso,
                }
                for log in logs
            ]

            # Recent uploads (last 10)
            uploads = DataUpload.objects.select_related('cargado_por').order_by("-fecha_carga")[:10]
            recent_etl = [
                {
                    "id": u.id,
                    "archivo": u.archivo.name if u.archivo else "desconocido",
                    "tipo_carga": "General",
                    "estado": u.estado,
                    "filas_insertadas": u.inserted_rows or 0,
                    "filas_actualizadas": u.updated_rows or 0,
                    "filas_erroneas": 0,
                    "fecha_carga": u.fecha_carga,
                }
                for u in uploads
            ]

            return Response({
                "sistema": {
                    "usuarios": total_usuarios,
                    "alertas_activas": total_alertas_activas,
                    "cargas_totales": total_cargas,
                    "tasa_exito": tasa_exito,
                },
                "negocio": {
                    "polizas_totales": total_polizas,
                    "polizas_vigentes": polizas_vigentes,
                    "prima_total_uf": float(prima_total),
                },
                "actividad_reciente": recent_activity,
                "etl_reciente": recent_etl,
                "timestamp": timezone.now(),
            })
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({
                "error": str(e),
                "sistema": {"usuarios": 0, "alertas_activas": 0, "cargas_totales": 0, "tasa_exito": 0},
                "negocio": {"polizas_totales": 0, "polizas_vigentes": 0, "prima_total_uf": 0},
                "actividad_reciente": [],
                "etl_reciente": [],
            }, status=500)
