"""
Management command para generar datos de cobranzas de ejemplo
Crea cobranzas para pólizas existentes
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta, datetime
import random
from polizas.models import Poliza
from cobranzas.models import Cobranza


class Command(BaseCommand):
    help = 'Genera datos de cobranzas de ejemplo para pólizas existentes'

    def add_arguments(self, parser):
        parser.add_argument(
            '--cantidad',
            type=int,
            default=100,
            help='Cantidad de cobranzas a generar (default: 100)'
        )
        parser.add_argument(
            '--limpiar',
            action='store_true',
            help='Elimina todas las cobranzas antes de generar nuevas'
        )

    def handle(self, *args, **options):
        cantidad = options['cantidad']
        limpiar = options['limpiar']

        if limpiar:
            count = Cobranza.objects.count()
            Cobranza.objects.all().delete()
            self.stdout.write(
                self.style.SUCCESS(f'Eliminadas {count} cobranzas existentes')
            )

        # Obtener pólizas
        polizas = Poliza.objects.all()[:cantidad]
        
        if not polizas.exists():
            self.stdout.write(self.style.ERROR('No hay pólizas para generar cobranzas'))
            return

        estados = ['PENDIENTE', 'EN_PROCESO', 'PAGADA', 'VENCIDA', 'CANCELADA']
        metodos_pago = ['TRANSFERENCIA', 'CHEQUE', 'EFECTIVO', 'TARJETA', 'DEBITO_AUTOMATICO']
        
        cobranzas_creadas = 0
        hoy = datetime.now().date()
        
        self.stdout.write(f'\nGenerando {len(polizas)} cobranzas...\n')

        for poliza in polizas:
            try:
                # Fechas aleatorias
                dias_emision = random.randint(-60, -1)
                dias_vencimiento = random.randint(1, 60)
                
                fecha_emision = hoy + timedelta(days=dias_emision)
                fecha_vencimiento = fecha_emision + timedelta(days=dias_vencimiento)
                
                # Estado aleatorio
                estado = random.choice(estados)
                
                # Si está pagada, asignar fecha de pago
                fecha_pago = None
                if estado == 'PAGADA':
                    dias_pago = random.randint(0, dias_vencimiento)
                    fecha_pago = fecha_emision + timedelta(days=dias_pago)
                
                # Monto aleatorio
                monto_uf = round(random.uniform(50, 500), 2)
                valor_uf = round(random.uniform(32000, 35000), 2)
                monto_pesos = round(monto_uf * valor_uf, 0)
                
                # Crear cobranza
                cobranza = Cobranza.objects.create(
                    poliza=poliza,
                    monto_uf=monto_uf,
                    monto_pesos=monto_pesos,
                    valor_uf=valor_uf,
                    fecha_emision=fecha_emision,
                    fecha_vencimiento=fecha_vencimiento,
                    fecha_pago=fecha_pago,
                    estado=estado,
                    metodo_pago=random.choice(metodos_pago) if estado != 'PENDIENTE' else None,
                    observaciones='Cobranza de ejemplo generada automáticamente'
                )
                
                cobranzas_creadas += 1
                
                if cobranzas_creadas % 10 == 0:
                    self.stdout.write(f'  Generadas {cobranzas_creadas}...')
                    
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f'Error creando cobranza para {poliza.numero}: {str(e)}')
                )
                continue

        # Estadísticas finales
        self.stdout.write('\n' + '=' * 80)
        self.stdout.write(self.style.SUCCESS(f'Cobranzas generadas: {cobranzas_creadas}'))
        
        # Mostrar estadísticas
        total = Cobranza.objects.count()
        por_estado = dict(
            Cobranza.objects.values('estado').annotate(
                count=__import__('django.db.models', fromlist=['Count']).Count('id')
            ).values_list('estado', 'count')
        )
        
        self.stdout.write(f'\nTotal de cobranzas en BD: {total}')
        self.stdout.write('\nDistribución por estado:')
        for estado, cantidad in sorted(por_estado.items(), key=lambda x: x[1], reverse=True):
            self.stdout.write(f'  - {estado}: {cantidad}')
        
        self.stdout.write('=' * 80 + '\n')
