"""
Importa una lista de canales M3U / M3U8.

    python manage.py importar_m3u canales/datos/canales_prueba.m3u8

Los canales nuevos se crean; si un canal ya existe, la dirección se agrega
como fuente alternativa. Se puede correr varias veces: lo repetido se ignora.
"""

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from canales.servicios import importar_m3u


class Command(BaseCommand):
    help = 'Importa los canales de una lista M3U / M3U8.'

    def add_arguments(self, parser):
        parser.add_argument('archivo', help='Ruta del archivo .m3u / .m3u8')

    def handle(self, *args, archivo, **options):
        ruta = Path(archivo)
        if not ruta.is_file():
            raise CommandError(f'No existe el archivo: {ruta}')
        resultado = importar_m3u(ruta.read_text(encoding='utf-8', errors='replace'), origen=ruta.name)
        self.stdout.write(self.style.SUCCESS(f'Listo: {resultado}'))
