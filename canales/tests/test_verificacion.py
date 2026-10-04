"""
Verificación de fuentes e importación desde el panel. Nunca sale a
internet: se reemplaza la descarga (o el verificador entero) por uno de mentira.
"""

import urllib.error
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from api import tokens
from canales import verificacion
from canales.models import Canal, Fuente
from canales.servicios import importar_m3u, verificar_fuentes_guardadas
from canales.verificacion import CAIDA, FUNCIONA, SIN_VERIFICAR, Resultado
from usuarios.models import Rol, Usuario

LISTA = '''#EXTM3U
#EXTINF:-1 tvg-id="Canal26.ar" group-title="Noticias",Canal 26
https://anda/c26.m3u8
#EXTINF:-1 group-title="Noticias",Telemax
https://caida/telemax.m3u8
#EXTINF:-1,Encuentro
https://www.youtube.com/user/encuentro/live
'''


def verificador_falso(fuentes, cabeceras=None):
    """Funciona todo lo de 'anda', se cae todo lo de 'caida', YouTube sin verificar."""
    def uno(url, tipo):
        if tipo == 'youtube':
            return Resultado(SIN_VERIFICAR, 'YouTube')
        return Resultado(FUNCIONA) if '//anda' in url else Resultado(CAIDA, 'No respondió a tiempo.')
    return {url: uno(url, tipo) for url, tipo in fuentes.items()}


class VerificarUrlTests(TestCase):

    def respuestas(self, por_url):
        """
        Reemplaza la descarga: devuelve el texto según la dirección (o lanza el
        error). Anota qué se pidió y con qué cabeceras en self.pedidos.
        """
        self.pedidos = []

        def descargar(url, cabeceras, maximo=None):
            self.pedidos.append((url, cabeceras))
            valor = por_url[url]
            if isinstance(valor, Exception):
                raise valor
            return valor, url
        return mock.patch.object(verificacion, '_descargar', side_effect=descargar)

    def test_lista_simple(self):
        with self.respuestas({'https://x/a.m3u8': '#EXTM3U\n#EXTINF:6,\nseg1.ts\n', 'https://x/seg1.ts': 'video'}):
            self.assertEqual(verificacion.verificar_url('https://x/a.m3u8').estado, FUNCIONA)
        # Se presenta como el reproductor de la app
        self.assertEqual(self.pedidos[0][1]['User-Agent'], verificacion.USER_AGENT_REPRODUCTOR)

    def test_prueba_el_pedazo_de_video_mas_reciente(self):
        lista = '#EXTM3U\n#EXTINF:6,\nviejo.ts\n#EXTINF:6,\nnuevo.ts\n'
        with self.respuestas({'https://x/a.m3u8': lista, 'https://x/nuevo.ts': 'video'}):
            self.assertEqual(verificacion.verificar_url('https://x/a.m3u8').estado, FUNCIONA)
        self.assertEqual(self.pedidos[-1][0], 'https://x/nuevo.ts')

    def test_lista_bien_pero_el_video_rechazado(self):
        """El caso de América: entrega la lista, pero el video responde 403."""
        rechazo = urllib.error.HTTPError('https://x/seg1.ts', 403, 'no', {}, None)
        with self.respuestas({'https://x/a.m3u8': '#EXTM3U\n#EXTINF:6,\nseg1.ts\n', 'https://x/seg1.ts': rechazo}):
            resultado = verificacion.verificar_url('https://x/a.m3u8')
        self.assertEqual((resultado.estado, resultado.error), (CAIDA, 'El canal no entrega el video al reproductor (error 403).'))

    def test_usa_las_cabeceras_propias_de_la_fuente(self):
        with self.respuestas({'https://x/a.m3u8': '#EXTM3U\n#EXTINF:6,\nseg1.ts\n', 'https://x/seg1.ts': 'video'}):
            verificacion.verificar_url('https://x/a.m3u8', 'hls', 'MiReproductor/1.0', 'https://canal.com/')
        self.assertEqual(self.pedidos[0][1], {'User-Agent': 'MiReproductor/1.0', 'Referer': 'https://canal.com/'})

    def test_lista_vacia(self):
        with self.respuestas({'https://x/a.m3u8': '#EXTM3U\n#EXT-X-VERSION:3\n'}):
            self.assertEqual(verificacion.verificar_url('https://x/a.m3u8').estado, CAIDA)

    def test_lista_maestra_prueba_la_primera_calidad(self):
        maestra = '#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=800000\n720/index.m3u8\n'
        caida = urllib.error.HTTPError('https://x/live/720/index.m3u8', 404, 'no', {}, None)
        with self.respuestas({'https://x/live/master.m3u8': maestra, 'https://x/live/720/index.m3u8': caida}):
            resultado = verificacion.verificar_url('https://x/live/master.m3u8')
        self.assertEqual((resultado.estado, resultado.error),
                         (CAIDA, 'El servidor respondió con error 404 al pedir la lista.'))

    def test_no_es_hls(self):
        with self.respuestas({'https://x/a.m3u8': '<html>Not found</html>'}):
            self.assertEqual(verificacion.verificar_url('https://x/a.m3u8').estado, CAIDA)

    def test_tiempo_agotado(self):
        with self.respuestas({'https://x/a.m3u8': urllib.error.URLError(TimeoutError())}):
            self.assertEqual(verificacion.verificar_url('https://x/a.m3u8').error, 'No respondió a tiempo.')

    def test_youtube_queda_sin_verificar(self):
        self.assertEqual(verificacion.verificar_url('https://youtube.com/x', 'youtube').estado, SIN_VERIFICAR)

    def test_varias_a_la_vez(self):
        with mock.patch.object(verificacion, 'verificar_url', side_effect=lambda url, tipo, *cabeceras: Resultado(FUNCIONA)):
            resultados = verificacion.verificar_varias({'https://a': 'hls', 'https://b': 'hls'})
        self.assertEqual(set(resultados), {'https://a', 'https://b'})


class ImportarConVerificacionTests(TestCase):

    def test_guarda_las_caidas_como_caidas(self):
        resultado = importar_m3u(LISTA, verificar=verificador_falso)
        self.assertEqual((resultado.funcionan, resultado.caidas, resultado.sin_verificar), (1, 1, 1))
        self.assertEqual(resultado.detalle_caidas,
                         [('Telemax', 'https://caida/telemax.m3u8', 'No respondió a tiempo.')])
        telemax = Fuente.objects.get(canal__nombre='Telemax')
        self.assertEqual(telemax.estado, Fuente.Estado.CAIDA)
        self.assertTrue(telemax.activa)          # el interruptor manual no se toca
        self.assertIsNotNone(telemax.verificada)

    def test_la_app_no_muestra_canales_con_todas_las_fuentes_caidas(self):
        importar_m3u(LISTA, verificar=verificador_falso)
        cliente = APIClient()
        clave, _ = tokens.crear_token(Usuario.objects.create_user('cliente', None, 'x'))
        cliente.credentials(HTTP_AUTHORIZATION=f'Bearer {clave}')
        datos = cliente.get(reverse('api_v1:canales')).json()
        nombres = {c['nombre'] for cat in datos['categorias'] for c in cat['canales']}
        # Telemax: su única fuente está caída. Encuentro: solo YouTube (la app no lo reproduce)
        self.assertEqual(nombres, {'Canal 26'})

    def test_no_vuelve_a_verificar_lo_que_ya_estaba(self):
        importar_m3u(LISTA, verificar=verificador_falso)
        pedidas = []
        importar_m3u(LISTA, verificar=lambda fuentes, cabeceras=None: pedidas.append(fuentes) or {})
        self.assertEqual(pedidas, [{}])

    def test_verificar_todas_revive_las_que_volvieron(self):
        importar_m3u(LISTA, verificar=verificador_falso)

        def ahora_anda_todo(fuentes, cabeceras=None):
            return {url: Resultado(FUNCIONA if tipo == 'hls' else SIN_VERIFICAR) for url, tipo in fuentes.items()}

        resultado = verificar_fuentes_guardadas(ahora_anda_todo)
        self.assertEqual((resultado.revividas, resultado.funcionan), (1, 2))
        self.assertEqual(Fuente.objects.get(canal__nombre='Telemax').estado, Fuente.Estado.FUNCIONA)


@mock.patch('canales.views.verificar_varias', verificador_falso)
class PantallaCanalesTests(TestCase):
    URL = reverse('canales:inicio')

    def setUp(self):
        self.admin = Usuario.objects.create_user(
            'admin', None, 'x', rol=Rol.objects.create(nombre='Canales', permisos=['ver_canales', 'importar_canales']))
        self.solo_ve = Usuario.objects.create_user(
            'mira', None, 'x', rol=Rol.objects.create(nombre='Mira', permisos=['ver_canales']))
        self.client.force_login(self.admin)

    def subir(self, nombre='lista.m3u8', contenido=LISTA):
        return self.client.post(self.URL, {'archivo': SimpleUploadedFile(nombre, contenido.encode())})

    def test_importa_y_muestra_el_resultado(self):
        respuesta = self.subir()
        self.assertContains(respuesta, 'Resultado de la importación')
        self.assertContains(respuesta, 'No respondió a tiempo.')
        self.assertEqual(Canal.objects.count(), 3)

    def test_rechaza_otros_archivos(self):
        self.assertContains(self.subir('foto.png'), 'Tiene que ser un archivo .m3u o .m3u8.')
        self.assertContains(self.subir(contenido='hola'), 'No se encontró ningún canal')
        self.assertEqual(Canal.objects.count(), 0)

    def test_verificar_todas(self):
        self.subir()
        respuesta = self.client.post(reverse('canales:verificar'), follow=True)
        self.assertContains(respuesta, 'Verificación terminada.')

    def test_sin_permiso_de_importar_solo_ve(self):
        self.client.force_login(self.solo_ve)
        respuesta = self.client.get(self.URL)
        self.assertEqual(respuesta.status_code, 200)
        self.assertNotContains(respuesta, 'Importar y verificar')
        self.assertEqual(self.subir().status_code, 403)
        self.assertEqual(self.client.post(reverse('canales:verificar')).status_code, 403)

    def test_sin_permiso_de_ver(self):
        self.client.force_login(Usuario.objects.create_user('otro', None, 'x'))
        self.assertEqual(self.client.get(self.URL).status_code, 403)


@mock.patch('api.v1.canales.verificar_url')
class AvisoDeFallaTests(TestCase):
    """La app avisa que una fuente no anda; el servidor la vuelve a probar."""

    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        importar_m3u(LISTA, verificar=verificador_falso)
        self.fuente = Fuente.objects.get(canal__nombre='Canal 26')
        self.app = APIClient()
        clave, _ = tokens.crear_token(Usuario.objects.create_user('cliente', None, 'x'))
        self.app.credentials(HTTP_AUTHORIZATION=f'Bearer {clave}')

    def avisar(self, fuente=None):
        return self.app.post(reverse('api_v1:fuente_falla', args=[(fuente or self.fuente).pk]))

    def test_si_al_servidor_tambien_le_falla_deja_de_mandarla(self, verificar_url):
        verificar_url.return_value = Resultado(CAIDA, 'No respondió a tiempo.')
        self.assertEqual(self.avisar().json()['estado'], CAIDA)
        self.assertEqual(self.app.get(reverse('api_v1:canales')).json()['cantidad'], 0)

    def test_si_al_servidor_le_anda_la_sigue_mandando(self, verificar_url):
        verificar_url.return_value = Resultado(FUNCIONA)
        self.assertEqual(self.avisar().json()['estado'], FUNCIONA)
        self.assertEqual(self.app.get(reverse('api_v1:canales')).json()['cantidad'], 1)

    def test_no_la_reprueba_muchas_veces_seguidas(self, verificar_url):
        verificar_url.return_value = Resultado(FUNCIONA)
        for _ in range(5):
            self.avisar()
        self.assertEqual(verificar_url.call_count, 1)

    def test_solo_fuentes_que_la_app_recibe(self, verificar_url):
        youtube = Fuente.objects.get(canal__nombre='Encuentro')
        self.assertEqual(self.avisar(youtube).status_code, 404)
        verificar_url.assert_not_called()
