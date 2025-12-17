"""
API Views para reportes automáticos inteligentes
PASO 9: Módulo de Reportes Automáticos Inteligentes
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from usuarios.permissions import IsAdmin
from .services import (
    reporte_polizas_vencidas,
    reporte_polizas_por_expirar,
    reporte_produccion_mensual,
    reporte_top_clientes,
)


class ReportePolizasVencidasView(APIView):
    """
    PASO 9.1: Reporte de Pólizas Vencidas
    
    GET /api/reportes/polizas-vencidas/
    
    Retorna lista de pólizas con fecha de vencimiento menor a hoy.
    """
    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    
    def get(self, request):
        """Obtener reporte de pólizas vencidas"""
        try:
            data = reporte_polizas_vencidas()
            return Response(data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ReportePolizasPorExpirarView(APIView):
    """
    PASO 9.2: Reporte de Pólizas por Expirar
    
    GET /api/reportes/polizas-por-expirar/
    
    Retorna pólizas que vencerán en los próximos 30 días.
    """
    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    
    def get(self, request):
        """Obtener reporte de pólizas por expirar"""
        try:
            data = reporte_polizas_por_expirar()
            return Response(data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ReporteProduccionMensualView(APIView):
    """
    PASO 9.3: Reporte de Producción Mensual
    
    GET /api/reportes/produccion-mensual/
    
    Retorna estadísticas de producción del mes actual vs. mes anterior.
    """
    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    
    def get(self, request):
        """Obtener reporte de producción mensual"""
        try:
            data = reporte_produccion_mensual()
            return Response(data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ReporteTopClientesView(APIView):
    """
    PASO 9.4: Top Clientes por Producción
    
    GET /api/reportes/top-clientes/
    
    Retorna ranking de clientes por producción en el mes actual.
    Incluye participación porcentual.
    """
    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    
    def get(self, request):
        """Obtener reporte de top clientes"""
        try:
            data = reporte_top_clientes()
            return Response(data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
