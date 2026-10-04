from pathlib import Path

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from actividad.models import RegistroActividad
from api import tokens
from canales.m3u import leer_m3u, normalizar
from canales.models import Canal, Categoria, Fuente
from canales.servicios import importar_m3u
from usuarios.models import Usuario

LISTA = '''#EXTM3U x-tvg-url="https://epg/guia.xml.gz"
#EXTINF:-1 tvg-id="Canal26.ar" tvg-name="Canal 26" tvg-logo="https://logo/26.png" tvg-chno="26" tvg-country="AR" group-title="Noticias",Canal 26
https://servidor-a/canal26/main.m3u8
#EXTINF:-1 tvg-logo="https://logo/enc.png" group-title="Cultura",Encuentro Ⓨ
https://www.youtube.com/user/encuentro/live
#EXTINF:0,Sin atributos
http://servidor-b/sin/playlist.m3u8|User-Agent=VLC
#EXTINF:-1,Sin dirección
#EXTVLCOPT:http-referrer=https://x
'''


class LectorM3UTests(TestCase):

    def test_lee_los_datos(self):
        entradas = leer_m3u(LISTA)
        self.assertEqual([e.nombre for e in entradas], ['Canal 26', 'Encuentro', 'Sin atributos'])
        canal26 = entradas[0]
        self.assertEqual(canal26.logo, 'https://logo/26.png')
        self.assertEqual(canal26.categoria, 'Noticias')
        self.assertEqual(canal26.numero, '26')
        self.assertEqual(canal26.tvg_id, 'Canal26.ar')
        self.assertEqual(canal26.pais, 'AR')
        self.assertEqual(canal26.tipo, 'hls')
        self.assertEqual(entradas[1].tipo, 'youtube')
        # Las opciones después de "|" no son parte de la dirección
        self.assertEqual(entradas[2].url, 'http://servidor-b/sin/playlist.m3u8')

    def test_normalizar(self):
        self.assertEqual(normalizar('Canal 26 HD Ⓨ'), 'canal 26')
        self.assertEqual(normalizar('Telefé (720p)'), 'telefe')


class ImportarTests(TestCase):

    def test_crea_canales_categorias_y_fuentes(self):
        resultado = importar_m3u(LISTA, origen='prueba.m3u8')
        self.assertEqual(resultado.canales_nuevos, 3)
        self.assertEqual(Canal.objects.count(), 3)
        self.assertEqual(set(Categoria.objects.values_list('nombre', flat=True)), {'Noticias', 'Cultura'})
        self.assertEqual(Canal.objects.get(tvg_id='Canal26.ar').categoria.nombre, 'Noticias')
        self.assertTrue(RegistroActividad.objects.filter(modulo='canales').exists())

    def test_reimportar_no_duplica(self):
        importar_m3u(LISTA)
        resultado = importar_m3u(LISTA)
        self.assertEqual((resultado.canales_nuevos, resultado.fuentes_nuevas, resultado.repetidas), (0, 0, 3))
        self.assertEqual(Fuente.objects.count(), 3)

    def test_el_mismo_canal_en_otra_lista_suma_una_alternativa(self):
        importar_m3u(LISTA)
        otra = ('#EXTM3U\n#EXTINF:-1 tvg-id="canal26.ar",Canal 26 HD\nhttps://servidor-c/c26.m3u8\n'
                '#EXTINF:-1,Sin Atributos\nhttps://servidor-d/otra.m3u8\n')
        resultado = importar_m3u(otra)
        self.assertEqual((resultado.canales_nuevos, resultado.fuentes_nuevas), (0, 2))
        canal26 = Canal.objects.get(tvg_id='Canal26.ar')
        self.assertEqual(list(canal26.fuentes.values_list('url', flat=True)),
                         ['https://servidor-a/canal26/main.m3u8', 'https://servidor-c/c26.m3u8'])

    def test_comando(self):
        archivo = Path(__file__).resolve().parent.parent / 'datos' / 'canales_prueba.m3u8'
        call_command('importar_m3u', str(archivo), stdout=open('nul' if __import__('os').name == 'nt' else '/dev/null', 'w'))
        self.assertEqual(Canal.objects.count(), 3)


class ApiCanalesTests(TestCase):
    URL = reverse('api_v1:canales')

    def setUp(self):
        importar_m3u(LISTA)
        self.client = APIClient()
        usuario = Usuario.objects.create_user('cliente', None, 'x')
        clave, _ = tokens.crear_token(usuario)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {clave}')

    def test_pide_sesion(self):
        self.assertEqual(APIClient().get(self.URL).status_code, 401)

    def test_agrupados_por_categoria(self):
        datos = self.client.get(self.URL).json()
        self.assertEqual(datos['cantidad'], 3)
        por_categoria = {c['nombre']: [canal['nombre'] for canal in c['canales']] for c in datos['categorias']}
        self.assertEqual(por_categoria, {'Cultura': ['Encuentro'], 'Noticias': ['Canal 26'], 'Otros': ['Sin atributos']})
        canal26 = datos['categorias'][1]['canales'][0]
        self.assertEqual(canal26['fuentes'][0]['url'], 'https://servidor-a/canal26/main.m3u8')
        self.assertEqual(canal26['logo'], 'https://logo/26.png')

    def test_no_muestra_inactivos_ni_sin_fuentes(self):
        Canal.objects.filter(nombre='Encuentro').update(activo=False)
        Fuente.objects.filter(canal__nombre='Sin atributos').update(activa=False)
        datos = self.client.get(self.URL).json()
        self.assertEqual(datos['cantidad'], 1)

    def test_fuentes_en_orden_de_prioridad(self):
        canal = Canal.objects.get(nombre='Canal 26')
        Fuente.objects.create(canal=canal, url='https://primera/x.m3u8', prioridad=0)
        datos = self.client.get(self.URL).json()
        noticias = next(c for c in datos['categorias'] if c['nombre'] == 'Noticias')
        self.assertEqual(noticias['canales'][0]['fuentes'][0]['url'], 'https://primera/x.m3u8')
