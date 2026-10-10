"""Imágenes puestas a mano: subirlas desde la compu y la portada propia de cada serie."""

import shutil
import tempfile
from io import BytesIO
from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image
from rest_framework.test import APIClient

from api import tokens
from canales import consultas, imagenes, organizar
from canales.models import Canal, Categoria, Contenido, Fuente, PortadaDeSerie
from usuarios.models import Usuario

MEDIA_TEMPORAL = tempfile.mkdtemp()


def _imagen(nombre='poster.png', tamano=(2400, 3600), modo='RGB', formato='PNG'):
    buffer = BytesIO()
    Image.new(modo, tamano, (200, 30, 30, 0) if modo == 'RGBA' else 'orange').save(buffer, formato)
    return SimpleUploadedFile(nombre, buffer.getvalue(), content_type=f'image/{formato.lower()}')


def _capitulo(nombre, logo='', categoria=None):
    canal = Canal.objects.create(nombre=nombre, contenido=Contenido.SERIE, logo=logo, categoria=categoria)
    Fuente.objects.create(canal=canal, url=f'https://x/{nombre.replace(" ", "")}.m3u8')
    return canal


def _pocoyo():
    for n in (1, 2, 3):
        _capitulo(f'Pocoyó S01 E0{n} Título', logo=f'https://i.ytimg.com/{n}.jpg')


def _archivos():
    return sorted(p.name for p in (Path(MEDIA_TEMPORAL) / imagenes.CARPETA).glob('*'))


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class SubirImagenTests(TestCase):

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(MEDIA_TEMPORAL, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        shutil.rmtree(Path(MEDIA_TEMPORAL) / imagenes.CARPETA, ignore_errors=True)
        self.client.force_login(Usuario.objects.create_superuser('admin', 'admin@test.com', 'x'))
        self.pelicula = Canal.objects.create(nombre='EL REGRESO (2019) Película completa', contenido=Contenido.PELICULA,
                                             logo='https://i.ytimg.com/vi/abc/hq.jpg')

    def _editar(self, follow=False, **datos):
        return self.client.post(reverse('canales:organizar_editar'), {
            'tipo': 'canal', 'canal': self.pelicula.pk, 'nombre': self.pelicula.nombre, 'logo': self.pelicula.logo,
            'contenido': 'pelicula', 'categoria': 'ninguna', 'activo': 'on', **datos}, follow=follow)

    def test_subida_se_achica_y_queda_como_imagen(self):
        self._editar(nombre='El regreso', imagen=_imagen())
        self.pelicula.refresh_from_db()
        self.assertEqual(self.pelicula.nombre, 'El regreso')
        self.assertRegex(self.pelicula.logo, r'^http://testserver/media/canales/imagenes/[0-9a-f]{32}\.jpg$')
        archivo, = _archivos()
        with Image.open(Path(MEDIA_TEMPORAL) / imagenes.CARPETA / archivo) as guardada:
            self.assertEqual((guardada.format, guardada.size), ('JPEG', (1067, 1600)))   # no más de 1600 de lado

    def test_un_logo_transparente_queda_png(self):
        self._editar(imagen=_imagen(tamano=(300, 300), modo='RGBA'))
        self.pelicula.refresh_from_db()
        self.assertTrue(self.pelicula.logo.endswith('.png'))

    def test_al_cambiarla_la_subida_vieja_se_borra(self):
        self._editar(imagen=_imagen())
        self.pelicula.refresh_from_db()
        self.assertEqual(len(_archivos()), 1)
        self._editar(logo='https://ejemplo.com/otra.jpg')
        self.assertEqual(_archivos(), [])

    def test_si_otro_la_usa_no_se_borra(self):
        self._editar(imagen=_imagen())
        self.pelicula.refresh_from_db()
        Canal.objects.create(nombre='Otra', contenido=Contenido.PELICULA, logo=self.pelicula.logo)
        self._editar(logo='https://ejemplo.com/otra.jpg')
        self.assertEqual(len(_archivos()), 1)

    def test_lo_que_no_es_imagen_no_se_guarda(self):
        respuesta = self._editar(nombre='Otro nombre',
                                 imagen=SimpleUploadedFile('virus.png', b'MZ no soy una imagen', 'image/png'),
                                 follow=True)
        self.assertContains(respuesta, 'no es una imagen')
        self.pelicula.refresh_from_db()
        self.assertEqual((self.pelicula.nombre, self.pelicula.logo),
                         ('EL REGRESO (2019) Película completa', 'https://i.ytimg.com/vi/abc/hq.jpg'))
        self.assertEqual(_archivos(), [])

    def test_el_dialogo_permite_subir(self):
        respuesta = self.client.get(reverse('canales:organizar'), {'contenido': 'pelicula'})
        self.assertContains(respuesta, 'enctype="multipart/form-data"')
        self.assertContains(respuesta, 'name="imagen"')


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class PortadaDeSerieTests(TestCase):

    def setUp(self):
        self.client.force_login(Usuario.objects.create_superuser('admin', 'admin@test.com', 'x'))
        self.infantiles = Categoria.objects.create(nombre='Series Infantiles', contenido=Contenido.SERIE)
        _pocoyo()

    def _editar(self, serie='Pocoyó', **datos):
        return self.client.post(reverse('canales:organizar_editar'), {
            'tipo': 'serie', 'serie': serie, 'nombre': serie, 'logo': '', 'categoria': self.infantiles.pk,
            'activo': 'on', **datos})

    def test_la_portada_no_pisa_las_imagenes_de_los_capitulos(self):
        self._editar(logo='https://ejemplo.com/pocoyo.jpg')
        self.assertEqual(imagenes.portada_de('pocoyo'), 'https://ejemplo.com/pocoyo.jpg')
        self.assertEqual(sorted(Canal.objects.values_list('logo', flat=True)),
                         [f'https://i.ytimg.com/{n}.jpg' for n in (1, 2, 3)])
        serie, = consultas.series()
        self.assertEqual((serie.logo, serie.portada), ('https://ejemplo.com/pocoyo.jpg', 'https://ejemplo.com/pocoyo.jpg'))

    def test_sin_tocar_la_imagen_no_se_crea_portada(self):
        # El cuadro muestra la del primer capítulo: guardar sin cambiarla no la vuelve portada
        self._editar(logo='https://i.ytimg.com/1.jpg', categoria='ninguna')
        self.assertFalse(PortadaDeSerie.objects.exists())

    def test_borrarla_vuelve_a_la_del_primer_capitulo(self):
        imagenes.poner_portada('Pocoyó', 'https://ejemplo.com/pocoyo.jpg')
        self._editar(logo='')
        self.assertFalse(PortadaDeSerie.objects.exists())
        self.assertEqual(consultas.series()[0].logo, 'https://i.ytimg.com/1.jpg')

    def test_subida_desde_la_compu(self):
        self._editar(imagen=_imagen())
        self.assertRegex(imagenes.portada_de('Pocoyó'), r'/media/canales/imagenes/[0-9a-f]{32}\.jpg$')

    def test_va_con_la_serie_al_renombrarla_y_al_unirla(self):
        imagenes.poner_portada('Pocoyó', 'https://ejemplo.com/pocoyo.jpg')
        self._editar(nombre='Pocoyó y sus amigos', logo='https://ejemplo.com/pocoyo.jpg')   # como la manda el cuadro
        self.assertEqual(imagenes.portada_de('Pocoyó y sus amigos'), 'https://ejemplo.com/pocoyo.jpg')
        self.assertEqual(imagenes.portada_de('Pocoyó'), '')
        _capitulo('Pato S01 E01 Solo')
        organizar.unir_en_una_serie(['Pato', 'Pocoyó y sus amigos'], 'Pocoyó Todo')
        self.assertEqual(imagenes.portada_de('Pocoyó Todo'), 'https://ejemplo.com/pocoyo.jpg')
        self.assertEqual(PortadaDeSerie.objects.count(), 1)

    def test_eliminar_la_serie_le_saca_la_portada(self):
        imagenes.poner_portada('Pocoyó', 'https://ejemplo.com/pocoyo.jpg')
        self.client.post(reverse('canales:organizar_eliminar'), {'serie': 'Pocoyó'})
        self.assertFalse(PortadaDeSerie.objects.exists())

    def test_la_api_la_manda_aparte(self):
        imagenes.poner_portada('pocoyo', 'https://ejemplo.com/pocoyo.jpg')
        cliente = APIClient()
        clave, _ = tokens.crear_token(Usuario.objects.create_user('cliente', None, 'x'))
        cliente.credentials(HTTP_AUTHORIZATION=f'Bearer {clave}')
        datos = cliente.get(reverse('api_v1:canales'), {'contenido': 'serie'}).json()
        self.assertEqual(datos['portadas'], {'Pocoyó': 'https://ejemplo.com/pocoyo.jpg'})
        self.assertEqual([c['logo'] for g in datos['categorias'] for c in g['canales']],
                         [f'https://i.ytimg.com/{n}.jpg' for n in (1, 2, 3)])
        self.assertNotIn('portadas', cliente.get(reverse('api_v1:canales'), {'contenido': 'pelicula'}).json())

    def test_el_panel_muestra_la_portada(self):
        imagenes.poner_portada('Pocoyó', 'https://ejemplo.com/pocoyo.jpg')
        respuesta = self.client.get(reverse('canales:organizar'), {'contenido': 'serie'})
        self.assertContains(respuesta, 'src="https://ejemplo.com/pocoyo.jpg"')
        self.assertContains(respuesta, '&quot;portada&quot;: true')
