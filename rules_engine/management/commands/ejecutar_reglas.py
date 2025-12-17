"""
Management command para ejecutar el Motor de Reglas
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from rules_engine.executor import ejecutar_motor_reglas, ejecutar_regla_individual
from rules_engine.models import Rule
from rules_engine.registry import get_registered_rules


class Command(BaseCommand):
    help = 'Ejecuta el motor de reglas del sistema'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Ejecutar todas las reglas (incluyendo inactivas)',
        )
        
        parser.add_argument(
            '--regla',
            type=str,
            help='Ejecutar una regla específica por su código',
        )
        
        parser.add_argument(
            '--list',
            action='store_true',
            help='Listar todas las reglas disponibles',
        )
        
        parser.add_argument(
            '--stats',
            action='store_true',
            help='Ver estadísticas del motor',
        )
        
        parser.add_argument(
            '--init',
            action='store_true',
            help='Inicializar reglas por defecto',
        )
    
    def handle(self, *args, **options):
        if options['list']:
            self.listar_reglas()
        elif options['stats']:
            self.ver_estadisticas()
        elif options['init']:
            self.inicializar_reglas()
        elif options['regla']:
            self.ejecutar_regla_unica(options['regla'])
        else:
            self.ejecutar_todas_reglas(solo_activas=not options['all'])
    
    def ejecutar_todas_reglas(self, solo_activas=True):
        """Ejecutar todas las reglas activas"""
        self.stdout.write(self.style.SUCCESS('\n' + '='*60))
        self.stdout.write(self.style.SUCCESS('  Motor de Reglas - Ejecución General'))
        self.stdout.write(self.style.SUCCESS('='*60 + '\n'))
        
        self.stdout.write(f'Hora de inicio: {timezone.now().strftime("%Y-%m-%d %H:%M:%S")}\n')
        
        try:
            resultado = ejecutar_motor_reglas(solo_activas=solo_activas)
            
            self.stdout.write(self.style.SUCCESS(f'✓ Reglas ejecutadas: {resultado["ejecutadas"]}'))
            self.stdout.write(self.style.SUCCESS(f'✓ Exitosas: {resultado["exitosas"]}'))
            
            if resultado['fallidas'] > 0:
                self.stdout.write(self.style.WARNING(f'⚠ Fallidas: {resultado["fallidas"]}'))
            else:
                self.stdout.write(self.style.SUCCESS(f'✓ Fallidas: {resultado["fallidas"]}'))
            
            self.stdout.write('\nDetalles por regla:\n')
            
            for codigo, detalles in resultado['reglas'].items():
                if detalles['status'] == 'exitosa':
                    self.stdout.write(
                        self.style.SUCCESS(f"  ✓ {codigo}")
                    )
                    if 'duracion_segundos' in detalles:
                        self.stdout.write(f"    Duración: {detalles['duracion_segundos']:.2f}s")
                else:
                    self.stdout.write(
                        self.style.ERROR(f"  ✗ {codigo}")
                    )
                    if 'error' in detalles:
                        self.stdout.write(f"    Error: {detalles['error']}")
                    elif 'mensaje' in detalles:
                        self.stdout.write(f"    Mensaje: {detalles['mensaje']}")
            
            self.stdout.write('\n' + self.style.SUCCESS('='*60))
            self.stdout.write(f'Hora de fin: {timezone.now().strftime("%Y-%m-%d %H:%M:%S")}')
            self.stdout.write(self.style.SUCCESS('='*60 + '\n'))
        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Error: {str(e)}'))
            raise CommandError(f'Error al ejecutar motor: {str(e)}')
    
    def ejecutar_regla_unica(self, codigo):
        """Ejecutar una regla específica"""
        self.stdout.write(self.style.SUCCESS(f'\nEjecutando regla: {codigo}\n'))
        
        try:
            resultado = ejecutar_regla_individual(codigo)
            
            if resultado['status'] == 'exitosa':
                self.stdout.write(self.style.SUCCESS(f"✓ {codigo} ejecutada exitosamente"))
                self.stdout.write(f"  Duración: {resultado['duracion_segundos']:.2f}s")
                self.stdout.write(f"  Resultado: {resultado['resultado']}")
            else:
                self.stdout.write(self.style.ERROR(f"✗ {codigo} falló"))
                self.stdout.write(f"  Error: {resultado['error']}")
        
        except Exception as e:
            raise CommandError(f'Error al ejecutar regla: {str(e)}')
    
    def listar_reglas(self):
        """Listar todas las reglas configuradas"""
        self.stdout.write(self.style.SUCCESS('\n' + '='*80))
        self.stdout.write(self.style.SUCCESS('  Reglas Configuradas'))
        self.stdout.write(self.style.SUCCESS('='*80 + '\n'))
        
        reglas = Rule.objects.all().order_by('orden_ejecucion')
        
        if not reglas.exists():
            self.stdout.write(self.style.WARNING('No hay reglas configuradas'))
            return
        
        # Reglas registradas
        registradas = get_registered_rules()
        
        for regla in reglas:
            estado = '✓ ACTIVA' if regla.activa else '✗ INACTIVA'
            registrada = '✓ Registrada' if regla.codigo in registradas else '✗ No Registrada'
            
            self.stdout.write(f"\n{regla.codigo}")
            self.stdout.write(f"  Nombre: {regla.nombre}")
            self.stdout.write(f"  Estado: {estado}")
            self.stdout.write(f"  Código: {registrada}")
            self.stdout.write(f"  Orden: {regla.orden_ejecucion}")
            self.stdout.write(f"  Tipo: {regla.tipo}")
            self.stdout.write(f"  Ejecuciones: {regla.total_ejecuciones}")
            self.stdout.write(f"  Tasa Éxito: {regla.tasa_exito:.1f}%")
            self.stdout.write(f"  Descripción: {regla.descripcion}")
        
        self.stdout.write('\n' + self.style.SUCCESS('='*80 + '\n'))
    
    def ver_estadisticas(self):
        """Ver estadísticas del motor"""
        self.stdout.write(self.style.SUCCESS('\n' + '='*80))
        self.stdout.write(self.style.SUCCESS('  Estadísticas del Motor de Reglas'))
        self.stdout.write(self.style.SUCCESS('='*80 + '\n'))
        
        # Conteos
        total_reglas = Rule.objects.count()
        activas = Rule.objects.filter(activa=True).count()
        inactivas = Rule.objects.filter(activa=False).count()
        
        self.stdout.write(f"Total de reglas: {total_reglas}")
        self.stdout.write(f"  Activas: {activas}")
        self.stdout.write(f"  Inactivas: {inactivas}")
        
        # Reglas registradas
        registradas = get_registered_rules()
        no_registradas = Rule.objects.exclude(codigo__in=registradas.keys()).count()
        
        self.stdout.write(f"\nReglas registradas en código: {len(registradas)}")
        self.stdout.write(f"Reglas no registradas: {no_registradas}")
        
        # Estadísticas de ejecución
        from rules_engine.models import RuleExecution
        
        ejecuciones_totales = RuleExecution.objects.count()
        exitosas = RuleExecution.objects.filter(estado='exitosa').count()
        fallidas = RuleExecution.objects.filter(estado='error').count()
        
        self.stdout.write(f"\nEjecuciones totales: {ejecuciones_totales}")
        self.stdout.write(f"  Exitosas: {exitosas}")
        self.stdout.write(f"  Fallidas: {fallidas}")
        
        if ejecuciones_totales > 0:
            tasa_exito = (exitosas / ejecuciones_totales) * 100
            self.stdout.write(f"  Tasa de éxito: {tasa_exito:.1f}%")
        
        # Regla más ejecutada
        regla_frecuente = Rule.objects.order_by('-total_ejecuciones').first()
        if regla_frecuente:
            self.stdout.write(f"\nRegla más ejecutada:")
            self.stdout.write(f"  {regla_frecuente.codigo}: {regla_frecuente.total_ejecuciones} veces")
        
        self.stdout.write('\n' + self.style.SUCCESS('='*80 + '\n'))
    
    def inicializar_reglas(self):
        """Inicializar reglas por defecto"""
        self.stdout.write(self.style.SUCCESS('\n' + '='*80))
        self.stdout.write(self.style.SUCCESS('  Inicializando Reglas Por Defecto'))
        self.stdout.write(self.style.SUCCESS('='*80 + '\n'))
        
        rules_data = [
            {
                'nombre': 'Pólizas Próximas a Vencer',
                'codigo': 'POLIZAS_POR_EXPIRAR',
                'descripcion': 'Genera alertas para pólizas que vencen en los próximos días',
                'tipo': 'alerta',
                'parametros': {'dias': 30, 'severidad': 'warning'}
            },
            {
                'nombre': 'Clientes Top por Producción',
                'codigo': 'CLIENTES_TOP_PRODUCCION',
                'descripcion': 'Detecta clientes con producción superior a un umbral',
                'tipo': 'inteligencia',
                'parametros': {'min_uf': 500, 'generar_alerta': True}
            },
            {
                'nombre': 'Detección de Producción Baja',
                'codigo': 'PRODUCCION_BAJA_DETECTADA',
                'descripcion': 'Alerta cuando la producción cae por debajo de un umbral',
                'tipo': 'validacion',
                'parametros': {'dias_comparar': 7, 'porcentaje_caida': 30}
            },
            {
                'nombre': 'Vigencia Irregular Detectada',
                'codigo': 'VIGENCIA_IRREGULAR_DETECTADA',
                'descripcion': 'Detecta patrones anómalos en renovaciones',
                'tipo': 'validacion',
                'parametros': {'dias_analisis': 90, 'min_renovaciones': 3}
            },
            {
                'nombre': 'Sanidad de Datos',
                'codigo': 'SANIDAD_DATOS',
                'descripcion': 'Valida la consistencia e integridad de datos',
                'tipo': 'validacion',
                'parametros': {'alertar_campos_vacios': True, 'alertar_fechas_inconsistentes': True}
            }
        ]
        
        creadas = 0
        existentes = 0
        
        for idx, rule_data in enumerate(rules_data, 1):
            rule_data['activa'] = True
            rule_data['orden_ejecucion'] = idx
            
            rule, created = Rule.objects.get_or_create(
                codigo=rule_data['codigo'],
                defaults=rule_data
            )
            
            if created:
                self.stdout.write(self.style.SUCCESS(f"✓ Creada: {rule.codigo}"))
                creadas += 1
            else:
                self.stdout.write(f"- Ya existe: {rule.codigo}")
                existentes += 1
        
        self.stdout.write(f"\nResumen:")
        self.stdout.write(self.style.SUCCESS(f"  Creadas: {creadas}"))
        self.stdout.write(f"  Ya existían: {existentes}")
        self.stdout.write('\n' + self.style.SUCCESS('='*80 + '\n'))
