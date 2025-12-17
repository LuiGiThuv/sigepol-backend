"""
Management command para generar alertas automáticas de frescura de datos
PASO 15: Auto-alertas cuando datos están desactualizados

Uso:
    python manage.py auto_alertar_frescura_datos
    python manage.py auto_alertar_frescura_datos --dias-limite=45
"""
from django.core.management.base import BaseCommand
from importaciones.models import DataFreshness
from alertas.utils import crear_alerta
from django.utils import timezone


class Command(BaseCommand):
    help = "Genera alertas automáticas cuando datos de clientes están desactualizados"

    def add_arguments(self, parser):
        parser.add_argument(
            '--dias-limite',
            type=int,
            default=30,
            help='Días sin actualizar para considerar datos desactualizados (default: 30)'
        )
        parser.add_argument(
            '--sin-filtro',
            action='store_true',
            help='Generar alertas sin filtro de fecha (regenerar todas)'
        )

    def handle(self, *args, **options):
        dias_limite = options.get('dias_limite', 30)
        sin_filtro = options.get('sin_filtro', False)

        self.stdout.write(
            self.style.SUCCESS(
                f'\n[INICIO] Generando alertas de frescura de datos (límite: {dias_limite} días)'
            )
        )

        # Obtener clientes desactualizados
        clientes_desactualizados = DataFreshness.obtener_clientes_desactualizados(
            dias_limite=dias_limite
        )

        if not clientes_desactualizados.exists():
            self.stdout.write(
                self.style.SUCCESS(
                    f'\n✓ No hay clientes desactualizados. Proceso completado.\n'
                )
            )
            return

        alertas_creadas = 0
        alertas_existentes = 0

        for data_freshness in clientes_desactualizados:
            cliente = data_freshness.cliente
            estado = data_freshness.obtener_estado_frescura()
            
            # Generar título y mensaje según estado
            if estado['status'] == 'CRÍTICO':
                severidad = 'critical'
                titulo = f"CRÍTICO: Datos no actualizados para {cliente}"
                mensaje = (
                    f"Los datos del cliente {cliente} no han sido actualizados hace {estado['dias_sin_actualizar']} días. "
                    f"Por favor, cargar el archivo Excel más reciente para este cliente."
                )
            else:  # ADVERTENCIA
                severidad = 'warning'
                titulo = f"Advertencia: Datos desactualizados para {cliente}"
                mensaje = (
                    f"Los datos del cliente {cliente} llevan {estado['dias_sin_actualizar']} días sin actualizar. "
                    f"Se recomienda cargar los datos más recientes."
                )
            
            try:
                # Verificar si ya existe alerta similar activa
                from alertas.models import Alerta
                alerta_existente = Alerta.objects.filter(
                    tipo='data_freshness_warning',
                    cliente__rut=cliente,
                    estado__in=['PENDIENTE', 'LEIDA']
                ).exists()
                
                if alerta_existente and not sin_filtro:
                    alertas_existentes += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f'  [SKIP] {cliente} - Alerta existente'
                        )
                    )
                else:
                    # Obtener cliente
                    from clientes.models import Cliente
                    try:
                        cliente_obj = Cliente.objects.get(rut=cliente)
                    except Cliente.DoesNotExist:
                        cliente_obj = None
                    
                    # Crear alerta
                    alerta = crear_alerta(
                        tipo='data_freshness_warning',
                        titulo=titulo,
                        mensaje=mensaje,
                        severidad=severidad,
                        cliente=cliente_obj,
                        usuario=data_freshness.usuario_ultima_carga
                    )
                    
                    # El campo confiable ya se establece en crear_alerta()
                    alerta.confiable = False
                    alerta.razon_no_confiable = f"Sistema detectó datos desactualizados hace {estado['dias_sin_actualizar']} días"
                    alerta.save()
                    
                    alertas_creadas += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'  [OK] {cliente} ({estado["dias_sin_actualizar"]}d) - Alerta creada'
                        )
                    )
            
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f'  [ERROR] {cliente} - {str(e)}'
                    )
                )

        # Resumen
        self.stdout.write(
            self.style.SUCCESS(
                f'\n[COMPLETO] Resumen:'
                f'\n  - Alertas creadas: {alertas_creadas}'
                f'\n  - Alertas existentes (saltadas): {alertas_existentes}'
                f'\n  - Total clientes desactualizados: {clientes_desactualizados.count()}\n'
            )
        )
