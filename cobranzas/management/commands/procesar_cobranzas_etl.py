"""
Management command para procesar cobranzas desde ETL
Detecta pólizas con pagos pendientes y crea cobranzas automáticamente
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from datetime import date
from cobranzas.utils import (
    detectar_pagos_pendientes,
    detectar_pagos_vencidos,
    crear_cobranzas_desde_etl,
    obtener_estadisticas_cobranzas,
)


class Command(BaseCommand):
    help = 'Procesa cobranzas desde ETL: detecta pagos pendientes y crea cobranzas automáticamente'

    def add_arguments(self, parser):
        parser.add_argument(
            '--vigentes',
            action='store_true',
            help='Procesa solo pólizas vigentes con pagos pendientes'
        )
        parser.add_argument(
            '--vencidas',
            action='store_true',
            help='Procesa solo pólizas vencidas sin pagar'
        )
        parser.add_argument(
            '--dias-emision',
            type=int,
            default=30,
            help='Días mínimos desde la emisión para crear cobranza (default: 30)'
        )
        parser.add_argument(
            '--mostrar-stats',
            action='store_true',
            help='Muestra estadísticas de cobranzas al final'
        )

    @transaction.atomic
    def handle(self, *args, **options):
        vigentes = options['vigentes']
        vencidas = options['vencidas']
        dias_emision = options['dias_emision']
        mostrar_stats = options['mostrar_stats']

        # Si no especifica, procesa ambas
        if not vigentes and not vencidas:
            vigentes = vencidas = True

        self.stdout.write(self.style.SUCCESS('=' * 80))
        self.stdout.write(self.style.SUCCESS('Procesando Cobranzas desde ETL'))
        self.stdout.write(self.style.SUCCESS(f'Fecha: {date.today()}'))
        self.stdout.write(self.style.SUCCESS('=' * 80))

        total_creadas = 0
        total_duplicadas = 0
        total_errores = 0

        # Procesar pólizas vigentes
        if vigentes:
            self.stdout.write('\n' + self.style.SUCCESS('1. Detectando pólizas vigentes con pagos pendientes...'))
            polizas_vigentes = detectar_pagos_pendientes(dias_desde_emision=dias_emision)
            cantidad = polizas_vigentes.count()
            
            if cantidad > 0:
                self.stdout.write(f'   ✓ Encontradas {cantidad} pólizas vigentes con pagos pendientes')
                
                stats = crear_cobranzas_desde_etl(polizas_vigentes)
                total_creadas += stats['creadas']
                total_duplicadas += stats['duplicadas']
                total_errores += stats['errores']
                
                self.stdout.write(f'   Resultados: {stats["creadas"]} creadas, {stats["duplicadas"]} duplicadas, {stats["errores"]} errores')
            else:
                self.stdout.write('   ℹ No hay pólizas vigentes con pagos pendientes')

        # Procesar pólizas vencidas
        if vencidas:
            self.stdout.write('\n' + self.style.SUCCESS('2. Detectando pólizas vencidas sin pagar...'))
            polizas_vencidas = detectar_pagos_vencidos()
            cantidad = polizas_vencidas.count()
            
            if cantidad > 0:
                self.stdout.write(f'   ✓ Encontradas {cantidad} pólizas vencidas sin pagar')
                
                stats = crear_cobranzas_desde_etl(polizas_vencidas)
                total_creadas += stats['creadas']
                total_duplicadas += stats['duplicadas']
                total_errores += stats['errores']
                
                self.stdout.write(f'   Resultados: {stats["creadas"]} creadas, {stats["duplicadas"]} duplicadas, {stats["errores"]} errores')
            else:
                self.stdout.write('   ℹ No hay pólizas vencidas sin pagar')

        # Mostrar resumen
        self.stdout.write('\n' + self.style.SUCCESS('=' * 80))
        self.stdout.write(self.style.SUCCESS('RESUMEN FINAL'))
        self.stdout.write(self.style.SUCCESS('=' * 80))
        self.stdout.write(f'Cobranzas creadas:    {total_creadas}')
        self.stdout.write(f'Duplicadas:           {total_duplicadas}')
        self.stdout.write(f'Errores:              {total_errores}')

        # Mostrar estadísticas si se solicita
        if mostrar_stats:
            self.stdout.write('\n' + self.style.SUCCESS('ESTADÍSTICAS DE COBRANZAS'))
            self.stdout.write(self.style.SUCCESS('=' * 80))
            stats = obtener_estadisticas_cobranzas()
            self.stdout.write(f'Total de cobranzas:      {stats["total_cobranzas"]}')
            self.stdout.write(f'Pendientes:              {stats["pendientes"]}')
            self.stdout.write(f'En proceso:              {stats["en_proceso"]}')
            self.stdout.write(f'Pagadas:                 {stats["pagadas"]}')
            self.stdout.write(f'Vencidas:                {stats["vencidas"]}')
            self.stdout.write(f'En riesgo:               {stats["en_riesgo"]}')
            self.stdout.write(f'Monto total pendiente:   {stats["monto_total_pendiente"]} UF')
            self.stdout.write(f'Promedio días atraso:    {stats["promedio_dias_atraso"]} días')

        self.stdout.write('\n' + self.style.SUCCESS('✓ Proceso completado'))
