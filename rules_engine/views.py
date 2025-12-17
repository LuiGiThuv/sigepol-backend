from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from .models import Rule, RuleExecution
from .serializers import (
    RuleListSerializer,
    RuleDetailSerializer,
    RuleCreateUpdateSerializer,
    RuleExecutionSerializer
)
from .executor import ejecutar_motor_reglas, ejecutar_regla_individual
from .registry import get_registered_rules


class IsAdmin(permissions.BasePermission):
    """Permiso solo para administradores"""
    
    def has_permission(self, request, view):
        return request.user and request.user.is_staff


class RuleViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar reglas del motor
    
    Endpoints:
    - GET /api/rules/ - Listar todas las reglas
    - GET /api/rules/{id}/ - Ver detalles de una regla
    - POST /api/rules/ - Crear nueva regla
    - PUT /api/rules/{id}/ - Actualizar regla
    - DELETE /api/rules/{id}/ - Eliminar regla
    - POST /api/rules/{id}/execute/ - Ejecutar una regla
    - POST /api/rules/execute_all/ - Ejecutar todas las reglas
    - GET /api/rules/{id}/executions/ - Ver historial de ejecuciones
    - GET /api/rules/registered/ - Ver reglas registradas en código
    - GET /api/rules/health/ - Estado general del motor
    """
    
    queryset = Rule.objects.all()
    permission_classes = [IsAdmin]
    
    def get_serializer_class(self):
        """Retornar serializer según la acción"""
        if self.action == 'list':
            return RuleListSerializer
        elif self.action == 'create' or self.action == 'update' or self.action == 'partial_update':
            return RuleCreateUpdateSerializer
        else:
            return RuleDetailSerializer
    
    def get_queryset(self):
        """Filtrar por estado si se especifica"""
        queryset = Rule.objects.all()
        
        activa = self.request.query_params.get('activa', None)
        if activa is not None:
            activa = activa.lower() == 'true'
            queryset = queryset.filter(activa=activa)
        
        tipo = self.request.query_params.get('tipo', None)
        if tipo:
            queryset = queryset.filter(tipo=tipo)
        
        return queryset.order_by('orden_ejecucion')
    
    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        """
        Ejecutar una regla específica
        
        POST /api/rules/{id}/execute/
        """
        regla = self.get_object()
        
        resultado = ejecutar_regla_individual(regla.codigo)
        
        if resultado['status'] == 'exitosa':
            return Response(resultado, status=status.HTTP_200_OK)
        else:
            return Response(resultado, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def execute_all(self, request):
        """
        Ejecutar todas las reglas activas
        
        POST /api/rules/execute_all/
        """
        solo_activas = request.data.get('solo_activas', True)
        resultado = ejecutar_motor_reglas(solo_activas=solo_activas)
        return Response(resultado, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['get'])
    def executions(self, request, pk=None):
        """
        Ver historial de ejecuciones de una regla
        
        GET /api/rules/{id}/executions/
        """
        regla = self.get_object()
        
        # Parámetros de paginación
        limit = int(request.query_params.get('limit', 20))
        offset = int(request.query_params.get('offset', 0))
        
        ejecuciones = RuleExecution.objects.filter(
            regla=regla
        ).order_by('-inicio')[offset:offset+limit]
        
        serializer = RuleExecutionSerializer(ejecuciones, many=True)
        
        return Response({
            'count': RuleExecution.objects.filter(regla=regla).count(),
            'limit': limit,
            'offset': offset,
            'results': serializer.data
        }, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'])
    def registered(self, request):
        """
        Ver reglas registradas en el código (decoradores @register_rule)
        
        GET /api/rules/registered/
        """
        registered = get_registered_rules()
        return Response({
            'total': len(registered),
            'reglas': list(registered.keys())
        }, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'])
    def health(self, request):
        """
        Ver estado general del motor de reglas
        
        GET /api/rules/health/
        """
        total_reglas = Rule.objects.count()
        activas = Rule.objects.filter(activa=True).count()
        inactivas = Rule.objects.filter(activa=False).count()
        
        # Reglas registradas
        registered = get_registered_rules()
        reglas_no_registradas = Rule.objects.exclude(
            codigo__in=registered.keys()
        ).count()
        
        # Últimas ejecuciones
        ejecuciones_totales = RuleExecution.objects.count()
        ejecuciones_exitosas = RuleExecution.objects.filter(estado='exitosa').count()
        ejecuciones_fallidas = RuleExecution.objects.filter(estado='error').count()
        
        tasa_exito_general = (
            (ejecuciones_exitosas / ejecuciones_totales * 100) 
            if ejecuciones_totales > 0 else 0
        )
        
        # Regla más frecuente
        ejecutada_mas_frecuente = Rule.objects.order_by('-total_ejecuciones').first()
        
        return Response({
            'status': 'operacional',
            'reglas': {
                'total': total_reglas,
                'activas': activas,
                'inactivas': inactivas,
                'registradas': len(registered),
                'no_registradas': reglas_no_registradas
            },
            'ejecuciones': {
                'total': ejecuciones_totales,
                'exitosas': ejecuciones_exitosas,
                'fallidas': ejecuciones_fallidas,
                'tasa_exito_general': round(tasa_exito_general, 2)
            },
            'regla_mas_ejecutada': {
                'codigo': ejecutada_mas_frecuente.codigo if ejecutada_mas_frecuente else None,
                'nombre': ejecutada_mas_frecuente.nombre if ejecutada_mas_frecuente else None,
                'ejecuciones': ejecutada_mas_frecuente.total_ejecuciones if ejecutada_mas_frecuente else 0
            } if ejecutada_mas_frecuente else None
        }, status=status.HTTP_200_OK)


class RuleExecutionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para ver el historial de ejecuciones de reglas (solo lectura)
    
    Endpoints:
    - GET /api/rule-executions/ - Listar todas las ejecuciones
    - GET /api/rule-executions/{id}/ - Ver detalles de una ejecución
    - GET /api/rule-executions/by_rule/{codigo}/ - Ejecuciones de una regla
    - GET /api/rule-executions/failures/ - Ver solo ejecuciones fallidas
    """
    
    queryset = RuleExecution.objects.all()
    serializer_class = RuleExecutionSerializer
    permission_classes = [IsAdmin]
    
    def get_queryset(self):
        """Filtrar ejecuciones según parámetros"""
        queryset = RuleExecution.objects.all()
        
        # Filtrar por estado
        estado = self.request.query_params.get('estado', None)
        if estado:
            queryset = queryset.filter(estado=estado)
        
        # Filtrar por regla
        regla_id = self.request.query_params.get('regla_id', None)
        if regla_id:
            queryset = queryset.filter(regla_id=regla_id)
        
        regla_codigo = self.request.query_params.get('regla_codigo', None)
        if regla_codigo:
            queryset = queryset.filter(regla__codigo=regla_codigo)
        
        return queryset.order_by('-inicio')
    
    @action(detail=False, methods=['get'])
    def failures(self, request):
        """
        Ver solo ejecuciones fallidas
        
        GET /api/rule-executions/failures/
        """
        limit = int(request.query_params.get('limit', 20))
        offset = int(request.query_params.get('offset', 0))
        
        fallos = RuleExecution.objects.filter(
            estado='error'
        ).order_by('-inicio')[offset:offset+limit]
        
        serializer = RuleExecutionSerializer(fallos, many=True)
        
        return Response({
            'count': RuleExecution.objects.filter(estado='error').count(),
            'limit': limit,
            'offset': offset,
            'results': serializer.data
        }, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'])
    def by_rule(self, request):
        """
        Ver ejecuciones de una regla específica por código
        
        GET /api/rule-executions/by_rule/?codigo=POLIZAS_POR_EXPIRAR
        """
        codigo = request.query_params.get('codigo', None)
        
        if not codigo:
            return Response(
                {'error': 'Se requiere parámetro codigo'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        regla = get_object_or_404(Rule, codigo=codigo)
        
        limit = int(request.query_params.get('limit', 20))
        offset = int(request.query_params.get('offset', 0))
        
        ejecuciones = RuleExecution.objects.filter(
            regla=regla
        ).order_by('-inicio')[offset:offset+limit]
        
        serializer = RuleExecutionSerializer(ejecuciones, many=True)
        
        return Response({
            'regla': {
                'codigo': regla.codigo,
                'nombre': regla.nombre
            },
            'count': RuleExecution.objects.filter(regla=regla).count(),
            'limit': limit,
            'offset': offset,
            'results': serializer.data
        }, status=status.HTTP_200_OK)
