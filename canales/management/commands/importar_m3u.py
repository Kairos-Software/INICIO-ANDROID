"""
Importa una lista de canales M3U / M3U8.

    python manage.py importar_m3u canales/datos/canales_prueba.m3u8
    python manage.py importar_m3u lista.m3u8 --sin-verificar

Los canales nuevos se crean; si un canal ya existe, la dirección se agrega
como fuente alternativa. Se puede correr varias veces: lo repetido se ignora.
Antes de guardar, prueba cada dirección nueva (las caídas se guardan como
caídas y la app no las usa). Con --sin-verificar no prueba nada.
"""

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from canales.servicios import importar_m3u
from canales.verificacion import verificar_varias


class Command(BaseCommand):
    help = 'Importa los canales de una lista M3U / M3U8.'

    def add_arguments(self, parser):
        parser.add_argument('archivo', help='Ruta del archivo .m3u / .m3u8')
        parser.add_argument('--sin-verificar', action='store_true', help='No probar las direcciones.')

    def handle(self, *args, archivo, sin_verificar, **options):
        ruta = Path(archivo)
        if not ruta.is_file():
            raise CommandError(f'No existe el archivo: {ruta}')
        if not sin_verificar:
            self.stdout.write('Verificando las direcciones nuevas (puede tardar)...')
        resultado = importar_m3u(ruta.read_text(encoding='utf-8', errors='replace'), origen=ruta.name,
                                 verificar=None if sin_verificar else verificar_varias)
        self.stdout.write(self.style.SUCCESS(f'Listo: {resultado}'))
