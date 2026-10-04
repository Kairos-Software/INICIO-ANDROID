"""
Vuelve a probar todas las fuentes y actualiza su estado.

    python manage.py verificar_fuentes

Lo mismo que el botón "Volver a verificar todas" del panel. En producción
se puede programar (cron) para que corra solo, por ejemplo cada hora.
"""

from django.core.management.base import BaseCommand

from canales.servicios import verificar_fuentes_guardadas
from canales.verificacion import verificar_varias


class Command(BaseCommand):
    help = 'Vuelve a probar todas las fuentes de los canales y actualiza su estado.'

    def handle(self, *args, **options):
        self.stdout.write('Verificando las fuentes (puede tardar)...')
        resultado = verificar_fuentes_guardadas(verificar_varias)
        self.stdout.write(self.style.SUCCESS(f'Listo: {resultado}'))
