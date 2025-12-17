"""
Management command para actualizar información de atrasos en cobranzas
Recalcula días de atraso, detecta riesgos, etc.
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from datetime import date, timedelta
from cobranzas.models import Cobranza


class Command(BaseCommand):
    help = 'Actualiza información de atrasos y riesgos en cobranzas'

    def add_arguments(self, parser):
        parser.add_argument(
            '--actualizar-atrasos',
            action='store_true',
            help='Recalcula días de atraso para todas las cobranzas pendientes'
        )
        parser.add_argument(
            '--detectar-riesgos',
            action='store_true',
            help='Detecta cobranzas en riesgo (vencidas + sin pagar)'
        )
        parser.add_argument(
            '--dias-riesgo',
            type=int,
            default=15,
            help='Días de vencimiento para considerar en riesgo (default: 15)'
        )

    @transaction.atomic
    def handle(self, *args, **options):
        actualizar_atrasos = options['actualizar_atrasos']
        detectar_riesgos = options['detectar_riesgos']
        dias_riesgo = options['dias_riesgo']

        # Si no especifica, hace todo
        if not actualizar_atrasos and not detectar_riesgos:
            actualizar_atrasos = detectar_riesgos = True

        self.stdout.write(self.style.SUCCESS('=' * 80))
        self.stdout.write(self.style.SUCCESS('Actualizando información de cobranzas'))
        self.stdout.write(self.style.SUCCESS(f'Fecha: {date.today()}'))
        self.stdout.write(self.style.SUCCESS('=' * 80))

        hoy = date.today()
        updated_count = 0

        # Actualizar atrasos
        if actualizar_atrasos:
            self.stdout.write('\n' + self.style.SUCCESS('1. Recalculando días de atraso...'))
            
            cobranzas = Cobranza.objects.filter(
                estado__in=['PENDIENTE', 'EN_PROCESO']
            )
            
            for cobranza in cobranzas:
                cobranza.actualizar_dias_atraso()
                cobranza.save()
                updated_count += 1
            
            self.stdout.write(f'   ✓ {updated_count} cobranzas actualizadas')

        # Detectar riesgos
        if detectar_riesgos:
            self.stdout.write('\n' + self.style.SUCCESS('2. Detectando cobranzas en riesgo...'))
            
            fecha_riesgo = hoy - timedelta(days=dias_riesgo)
            cobranzas_riesgo = Cobranza.objects.filter(
                fecha_vencimiento__lt=fecha_riesgo,
                estado__in=['PENDIENTE', 'EN_PROCESO'],
                tiene_alerta_financiera=False
            )
            
            count_riesgo = 0
            for cobranza in cobranzas_riesgo:
                cobranza.tiene_alerta_financiera = True
                cobranza.razon_alerta = f'Vencida sin pagar hace {cobranza.dias_atraso} días'
                cobranza.tipo_cobranza = 'RIESGO_FINANCIERO'
                cobranza.save()
                count_riesgo += 1
            
            self.stdout.write(f'   ✓ {count_riesgo} cobranzas marcadas en riesgo')

        # Resumen
        self.stdout.write('\n' + self.style.SUCCESS('=' * 80))
        self.stdout.write(self.style.SUCCESS('✓ Proceso completado'))
