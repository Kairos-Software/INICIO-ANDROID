"""
Importa una lista de canales M3U / M3U8.

    python manage.py importar_m3u canales/datos/canales_prueba.m3u8
    python manage.py importar_m3u lista.m3u --solo-espanol --descartar-sin-logo
    python manage.py importar_m3u lista.m3u8 --sin-verificar
    python manage.py importar_m3u lista.m3u --solo-espanol --a-fondo

Hace lo mismo que el panel (crea una importación con su informe, que se ve
en /canales/), pero todo de una vez. Los canales nuevos se crean; si un
canal ya existe, la dirección se agrega como fuente alternativa. Se puede
correr varias veces: lo repetido se ignora. Prueba cada dirección nueva y
solo agrega las que funcionan. Con --a-fondo, solo las que pasan la prueba a
fondo (sonido, idioma del audio, resolución, formato, si llega fluido). Con
--sin-verificar agrega todo sin probar.
"""

from functools import partial
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from canales.servicios import importar_m3u
from canales.verificacion import verificar_varias


class Command(BaseCommand):
    help = 'Importa los canales de una lista M3U / M3U8.'

    def add_arguments(self, parser):
        parser.add_argument('archivo', help='Ruta del archivo .m3u / .m3u8')
        parser.add_argument('--sin-verificar', action='store_true', help='No probar las direcciones.')
        parser.add_argument('--solo-espanol', action='store_true', help='Descartar los que se sabe que son de otro idioma.')
        parser.add_argument('--descartar-sin-logo', action='store_true', help='Descartar los que no tienen logo.')
        parser.add_argument('--con-peliculas', action='store_true', help='No descartar películas ni series.')
        parser.add_argument('--con-adultos', action='store_true', help='No descartar el contenido para adultos.')
        parser.add_argument('--a-fondo', action='store_true', help='La prueba a fondo (como el panel).')

    def handle(self, *args, archivo, sin_verificar, solo_espanol, descartar_sin_logo, con_peliculas, con_adultos,
               a_fondo, **options):
        ruta = Path(archivo)
        if not ruta.is_file():
            raise CommandError(f'No existe el archivo: {ruta}')
        if not sin_verificar:
            self.stdout.write('Verificando las direcciones nuevas (puede tardar)...')
        resultado = importar_m3u(ruta.read_text(encoding='utf-8', errors='replace'), origen=ruta.name,
                                 verificar=None if sin_verificar else partial(verificar_varias, a_fondo=a_fondo),
                                 solo_espanol=solo_espanol, descartar_sin_logo=descartar_sin_logo,
                                 descartar_vod=not con_peliculas, descartar_adultos=not con_adultos, a_fondo=a_fondo)
        self.stdout.write(self.style.SUCCESS(f'Listo: {resultado}'))
