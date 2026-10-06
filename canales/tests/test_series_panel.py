from django.test import TestCase
from django.urls import reverse

from canales.models import Canal, Categoria, Fuente
from usuarios.models import Rol, Usuario


class SeriesPanelTests(TestCase):
    def setUp(self):
        self.rol = Rol.objects.create(nombre='Canales y series', permisos=['ver_canales', 'importar_canales'])
        self.usuario = Usuario.objects.create_user('series-admin', None, 'x', rol=self.rol)
        self.client.force_login(self.usuario)
        self.categoria = Categoria.objects.create(nombre='Acción')

        self.arrow_uno = self.capitulo('Arrow S01 E01 Piloto', codec='h264')
        self.arrow_dos = self.capitulo(
            'Arrow S01 E02 Honor Thy Father', estado=Fuente.Estado.CAIDA,
            codec='h265', error='No respondió a tiempo.',
        )
        self.lucifer = self.capitulo('Lucifer S02 E03 Sin City', estado=Fuente.Estado.CAIDA)

    def capitulo(self, nombre, estado=Fuente.Estado.FUNCIONA, codec='', error=''):
        canal = Canal.objects.create(nombre=nombre, contenido='serie', categoria=self.categoria)
        Fuente.objects.create(
            canal=canal,
            url=f'https://series.ejemplo.com/{canal.pk}.mkv',
            tipo=Fuente.Tipo.DIRECTO,
            estado=estado,
            codec=codec,
            error=error,
        )
        return canal

    def test_lista_responde_y_esta_paginada(self):
        respuesta = self.client.get(reverse('canales:series'))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'Arrow')
        self.assertContains(respuesta, 'Lucifer')
        self.assertEqual(respuesta.context['pagina'].paginator.per_page, 24)

    def test_busca_por_nombre(self):
        respuesta = self.client.get(reverse('canales:series'), {'q': 'arrow'})
        self.assertContains(respuesta, 'Arrow')
        self.assertNotContains(respuesta, 'Lucifer')

    def test_filtra_por_capitulos_que_se_ven(self):
        respuesta = self.client.get(reverse('canales:series'), {'estado': 'en_app'})
        self.assertContains(respuesta, 'Arrow')
        self.assertNotContains(respuesta, 'Lucifer')

    def test_filtra_series_sin_ningun_capitulo_visible(self):
        respuesta = self.client.get(reverse('canales:series'), {'estado': 'fuera'})
        self.assertContains(respuesta, 'Lucifer')
        self.assertNotContains(respuesta, 'Arrow')

    def test_detalle_muestra_temporadas_fuentes_y_motivo(self):
        respuesta = self.client.get(reverse('canales:serie_detalle'), {'nombre': 'Arrow'})
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'Temporada 1')
        self.assertContains(respuesta, 'Piloto')
        self.assertContains(respuesta, 'Honor Thy Father')
        self.assertContains(respuesta, 'h264')
        self.assertContains(respuesta, 'h265')
        self.assertContains(respuesta, 'Todas sus fuentes están caídas.')
        self.assertContains(respuesta, reverse('canales:canal_editar', args=[self.arrow_dos.pk]))

    def test_detalle_inexistente_devuelve_404(self):
        respuesta = self.client.get(reverse('canales:serie_detalle'), {'nombre': 'No existe'})
        self.assertEqual(respuesta.status_code, 404)

    def test_las_dos_pantallas_piden_permiso(self):
        self.client.force_login(Usuario.objects.create_user('sin-canales', None, 'x'))
        self.assertEqual(self.client.get(reverse('canales:series')).status_code, 403)
        self.assertEqual(
            self.client.get(reverse('canales:serie_detalle'), {'nombre': 'Arrow'}).status_code,
            403,
        )


class ContenidoEnCatalogoTests(TestCase):
    def setUp(self):
        rol = Rol.objects.create(nombre='Catálogo de contenidos', permisos=['ver_canales'])
        self.client.force_login(Usuario.objects.create_user('catalogo-contenidos', None, 'x', rol=rol))
        vivo = Canal.objects.create(nombre='Canal en vivo', contenido='vivo')
        pelicula = Canal.objects.create(nombre='Una película', contenido='pelicula')
        Fuente.objects.create(canal=vivo, url='https://tv.ejemplo.com/vivo.m3u8', estado=Fuente.Estado.FUNCIONA)
        Fuente.objects.create(
            canal=pelicula,
            url='https://tv.ejemplo.com/pelicula.mp4',
            tipo=Fuente.Tipo.DIRECTO,
            estado=Fuente.Estado.FUNCIONA,
            codec='h264',
        )

    def test_pestana_peliculas_filtra_el_catalogo_y_muestra_codec(self):
        respuesta = self.client.get(reverse('canales:catalogo'), {'contenido': 'pelicula'})
        self.assertContains(respuesta, 'Una película')
        self.assertNotContains(respuesta, 'Canal en vivo')
        self.assertContains(respuesta, 'h264')
        self.assertContains(respuesta, reverse('canales:series'))

    def test_catalogo_sin_parametro_abre_en_vivo(self):
        respuesta = self.client.get(reverse('canales:catalogo'))
        self.assertContains(respuesta, 'Canal en vivo')
        self.assertNotContains(respuesta, 'Una película')

    def test_inicio_muestra_los_tres_resumenes_sin_aviso_viejo(self):
        respuesta = self.client.get(reverse('canales:inicio'))
        self.assertContains(respuesta, 'En vivo')
        self.assertContains(respuesta, 'Película')
        self.assertContains(respuesta, 'Serie')
        self.assertNotContains(respuesta, 'app 1.0.0')
