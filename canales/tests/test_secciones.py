"""Secciones nuevas de la app (Música, Radio...), temporadas al traer una serie y el máximo de minutos."""

from unittest import mock

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from api import tokens
from canales import consultas, estadisticas, organizar, secciones, servicios, youtube
from canales.models import Canal, Categoria, Contenido, EntradaImportada, Fuente, Seccion, Visto
from canales.servicios import importar_m3u
from canales.verificacion import FUNCIONA, Resultado
from usuarios.models import Usuario

Estado = EntradaImportada.Estado


def _todas_funcionan(fuentes, **_):
    return {url: Resultado(FUNCIONA, tipo=tipo) for url, tipo in fuentes.items()}


def _shakira():
    """Un canal de música: videos de 3 a 4 minutos, un concierto entero y un Short."""
    return youtube.Listado('Shakira', [
        youtube.Video('sssssssss01', 'Shakira - Hips Don\'t Lie (Official Video)', 220),
        youtube.Video('sssssssss02', 'Shakira - Waka Waka (Official Video)', 211),
        youtube.Video('sssssssss03', 'Shakira - Concierto completo en vivo', 5400),
        youtube.Video('sssssssss04', 'Shakira #shorts', 40),
    ])


def _traer(listado, **opciones):
    importacion = servicios.crear_importacion_de_youtube(listado, **opciones)
    servicios.procesar_lote(importacion, _todas_funcionan, segundos=None)
    servicios.cargar_lote(importacion)
    return importacion


class CrearSeccionesTests(TestCase):

    def test_crear_arma_la_clave_del_nombre(self):
        musica = secciones.crear('Música', Seccion.Forma.A_DEMANDA, Seccion.Icono.MUSICA)
        self.assertEqual((musica.clave, musica.forma), ('musica', 'pelicula'))
        radio = secciones.crear('  Radios   AM/FM ', Seccion.Forma.VIVO)
        self.assertEqual((radio.clave, radio.nombre), ('radiosam', 'Radios AM/FM'))
        self.assertEqual(secciones.todas()[-2:], [('musica', 'Música'), ('radiosam', 'Radios AM/FM')])
        self.assertEqual((secciones.nombre('musica'), secciones.forma('radiosam')), ('Música', 'vivo'))
        self.assertEqual(secciones.forma(Contenido.SERIE), 'serie')

    def test_no_se_repiten_ni_pisan_las_fijas(self):
        secciones.crear('Música', Seccion.Forma.A_DEMANDA)
        for nombre in ('musica', 'Películas', 'En Vivo', ''):
            with self.assertRaises(secciones.NoSePuede, msg=nombre):
                secciones.crear(nombre, Seccion.Forma.A_DEMANDA)
        with self.assertRaises(secciones.NoSePuede):
            secciones.crear('Radio', 'cualquiera')

    def test_borrada_su_clave_se_puede_volver_a_usar(self):
        musica = secciones.crear('Música', Seccion.Forma.A_DEMANDA)
        secciones.borrar(musica)
        self.assertEqual(secciones.crear('Música', Seccion.Forma.A_DEMANDA).clave, 'musica2')

    def test_borrar_con_contenido_pide_confirmarlo(self):
        musica = secciones.crear('Música', Seccion.Forma.A_DEMANDA)
        _traer(_shakira(), seccion='musica', minimo_minutos=2, maximo_minutos=6)
        with self.assertRaises(secciones.NoSePuede):
            secciones.borrar(musica)
        self.assertEqual(secciones.borrar(musica, con_contenido=True), 2)
        self.assertFalse(Canal.objects.filter(contenido='musica').exists())
        self.assertFalse(Categoria.objects.filter(contenido='musica').exists())
        self.assertFalse(secciones.es_valida('musica'))


class ImportarEnUnaSeccionTests(TestCase):

    def setUp(self):
        secciones.crear('Música', Seccion.Forma.A_DEMANDA, Seccion.Icono.MUSICA)
        secciones.crear('Radio', Seccion.Forma.VIVO, Seccion.Icono.RADIO)

    def test_musica_de_youtube_con_minimo_y_maximo(self):
        importacion = _traer(_shakira(), seccion='musica', minimo_minutos=2, maximo_minutos=6)
        self.assertEqual(importacion.seccion, 'musica')
        cargados = Canal.objects.filter(contenido='musica')
        self.assertEqual(cargados.count(), 2)
        # Sin categoría elegida: la del nombre del canal (el artista), en Música
        self.assertEqual({c.categoria.nombre for c in cargados}, {'Shakira'})
        self.assertEqual(Categoria.objects.get(nombre='Shakira').contenido, 'musica')
        concierto = importacion.entradas.get(tvg_id='sssssssss03')
        self.assertEqual(concierto.estado, Estado.DESCARTADA)
        self.assertIn('más largo de lo pedido (hasta 6 min)', concierto.motivo)
        self.assertIn('video corto', importacion.entradas.get(tvg_id='sssssssss04').motivo)
        # Películas no lo ve
        self.assertFalse(Canal.objects.filter(contenido=Contenido.PELICULA).exists())

    def test_en_una_seccion_nueva_un_t1_e2_no_es_una_serie(self):
        listado = youtube.Listado('Coldplay', [youtube.Video('ccccccccc01', 'Coldplay T1 E2 en vivo', 240)])
        _traer(listado, seccion='musica', minimo_minutos=2)
        self.assertEqual(Canal.objects.get().contenido, 'musica')

    def test_una_lista_de_radios(self):
        lista = ('#EXTM3U\n#EXTINF:-1 group-title="Argentina",Radio Mitre\nhttp://radio/mitre.mp3\n'
                 '#EXTINF:-1 group-title="Argentina",La 100\nhttp://radio/la100.aac\n')
        importar_m3u(lista, 'radios.m3u', seccion='radio', descartar_vod=True)
        self.assertEqual(set(Canal.objects.values_list('contenido', flat=True)), {'radio'})
        self.assertEqual(Categoria.objects.get().contenido, 'radio')

    def test_pasar_de_peliculas_a_musica(self):
        _traer(_shakira(), minimo_minutos=2, maximo_minutos=6, categoria='Pop')
        self.assertEqual(Canal.objects.filter(contenido=Contenido.PELICULA).count(), 2)
        organizar.cambiar_contenido(Canal.objects.all(), 'musica')
        self.assertEqual(set(Canal.objects.values_list('contenido', 'categoria__contenido')), {('musica', 'musica')})
        with self.assertRaises(organizar.NoSePuede):
            organizar.cambiar_contenido(Canal.objects.all(), 'no_existe')

    def test_resumen_y_lo_mas_visto_con_una_seccion_nueva(self):
        _traer(_shakira(), seccion='musica', minimo_minutos=2, maximo_minutos=6)
        self.assertEqual([b['nombre'] for b in consultas.resumen()['por_contenido']][-2:], ['Música', 'Radio'])
        canal = Canal.objects.first()
        Visto.objects.create(canal=canal, fecha=timezone.localdate(), segundos=200, vistas=1)
        ranking = estadisticas.lo_mas_visto()
        self.assertEqual([f.nombre for f in ranking.pelicula], [canal.nombre])   # Música va con las películas


class TemporadasTests(TestCase):

    def setUp(self):
        Categoria.objects.create(nombre='Acción', contenido=Contenido.SERIE)

    def _rangers(self, prefijo, cuantos):
        return youtube.Listado('Power Rangers', [
            youtube.Video(f'{prefijo}{n:09d}', f'Capítulo {n} | Episodio Completo | S0{prefijo[-1]} | E{n:02d}', 1200)
            for n in range(1, cuantos + 1)])

    def test_cada_temporada_empieza_en_el_capitulo_1(self):
        _traer(self._rangers('a1', 3), serie='Power Rangers', temporada=1, categoria='Acción', minimo_minutos=15)
        _traer(self._rangers('b2', 2), serie='Power Rangers', temporada=2, categoria='Acción', minimo_minutos=15)
        nombres = sorted(Canal.objects.values_list('nombre', flat=True))
        self.assertEqual([n[:22] for n in nombres], [
            'Power Rangers S01 E01 ', 'Power Rangers S01 E02 ', 'Power Rangers S01 E03 ',
            'Power Rangers S02 E01 ', 'Power Rangers S02 E02 '])

    def test_la_pantalla_manda_la_temporada_y_el_maximo(self):
        self.client.force_login(Usuario.objects.create_superuser('admin', 'admin@test.com', 'x'))
        with mock.patch('canales.youtube.videos_del_canal', return_value=self._rangers('c2', 2)):
            respuesta = self.client.post(reverse('canales:youtube'), {
                'url': 'https://www.youtube.com/playlist?list=PLx', 'es_serie': 'on', 'nombre_serie': 'Power Rangers',
                'temporada': 2, 'categoria_destino': 'Acción', 'minimo_minutos': 15, 'maximo_minutos': 30})
        self.assertEqual(respuesta.status_code, 302)
        importacion = EntradaImportada.objects.first().importacion
        self.assertEqual((importacion.serie, importacion.temporada), ('Power Rangers', 2))
        self.assertTrue(importacion.entradas.first().nombre.startswith('Power Rangers S02 E01'))

    def test_el_maximo_no_puede_ser_menos_que_el_minimo(self):
        self.client.force_login(Usuario.objects.create_superuser('admin', 'admin@test.com', 'x'))
        respuesta = self.client.post(reverse('canales:youtube'), {
            'url': 'https://www.youtube.com/@x', 'minimo_minutos': 20, 'maximo_minutos': 5})
        self.assertContains(respuesta, 'Tiene que ser igual o más que el mínimo (20).')


class PantallasTests(TestCase):

    def setUp(self):
        self.client.force_login(Usuario.objects.create_superuser('admin', 'admin@test.com', 'x'))

    def test_el_catalogo_tecnico_tiene_las_secciones_nuevas(self):
        secciones.crear('Radio', Seccion.Forma.VIVO, Seccion.Icono.RADIO)
        importar_m3u('#EXTM3U\n#EXTINF:-1 group-title="AM",Radio Mitre\nhttp://radio/mitre.m3u8\n', seccion='radio')
        importar_m3u('#EXTM3U\n#EXTINF:-1 group-title="Noticias",Canal 26\nhttp://tv/26.m3u8\n')
        # El catálogo viejo lleva a Organizar, a la misma sección
        organizar_ = reverse('canales:organizar')
        for pedido, va in (('radio', 'radio'), ('serie', 'serie'), ('cualquiera', 'vivo')):
            self.assertRedirects(self.client.get(reverse('canales:catalogo'), {'contenido': pedido}),
                                 f'{organizar_}?contenido={va}', fetch_redirect_response=False)
        radio = self.client.get(organizar_, {'contenido': 'radio'})
        self.assertContains(radio, 'Radio Mitre')
        self.assertNotContains(radio, 'Canal 26')

    def test_crear_una_seccion_desde_organizar(self):
        respuesta = self.client.post(reverse('canales:secciones'), {
            'accion': 'crear', 'nombre': 'Música', 'forma': 'pelicula', 'icono': 'musica'})
        self.assertRedirects(respuesta, reverse('canales:organizar') + '?contenido=musica', fetch_redirect_response=False)
        pagina = self.client.get(reverse('canales:organizar'), {'contenido': 'musica'})
        self.assertContains(pagina, 'Categorías de Música')
        self.assertContains(pagina, 'Cambiar la sección «Música»')
        # Crear una categoría en Música
        self.client.post(reverse('canales:categorias'), {'accion': 'crear', 'nombre': 'Rock', 'seccion': 'musica'})
        self.assertEqual(Categoria.objects.get(nombre='Rock').contenido, 'musica')

    def test_cambiar_y_borrar(self):
        musica = secciones.crear('Música', Seccion.Forma.A_DEMANDA)
        self.client.post(reverse('canales:secciones'), {'accion': 'editar', 'seccion_pk': musica.pk,
                                                        'nombre': 'Música Latina', 'icono': 'radio', 'orden': 4})
        musica.refresh_from_db()
        self.assertEqual((musica.nombre, musica.icono, musica.orden, musica.clave), ('Música Latina', 'radio', 4,
                                                                                      'musica'))
        respuesta = self.client.post(reverse('canales:secciones'), {'accion': 'crear', 'nombre': 'Series',
                                                                    'forma': 'pelicula'}, follow=True)
        self.assertContains(respuesta, 'Ya hay una sección')
        self.client.post(reverse('canales:secciones'), {'accion': 'borrar', 'seccion_pk': musica.pk})
        self.assertFalse(Seccion.objects.exists())

    def test_youtube_e_importar_ofrecen_la_seccion(self):
        secciones.crear('Música', Seccion.Forma.A_DEMANDA)
        secciones.crear('Radio', Seccion.Forma.VIVO)
        youtube_pagina = self.client.get(reverse('canales:youtube'))
        self.assertContains(youtube_pagina, '<option value="musica">Música</option>', html=True)
        self.assertNotContains(youtube_pagina, '<option value="radio">Radio</option>', html=True)   # en vivo: no
        inicio = self.client.get(reverse('canales:inicio'))
        self.assertContains(inicio, '<option value="radio">Radio</option>', html=True)

    def test_la_categoria_tiene_que_ser_de_la_seccion(self):
        secciones.crear('Música', Seccion.Forma.A_DEMANDA)
        Categoria.objects.create(nombre='Acción', contenido=Contenido.PELICULA)
        respuesta = self.client.post(reverse('canales:youtube'), {
            'url': 'https://www.youtube.com/@x', 'minimo_minutos': 2, 'seccion_destino': 'musica',
            'categoria_destino': 'Acción'})
        self.assertContains(respuesta, 'no es una categoría de Música')

    def test_editar_un_canal_a_una_seccion_nueva(self):
        secciones.crear('Radio', Seccion.Forma.VIVO)
        canal = Canal.objects.create(nombre='Radio Mitre')
        Fuente.objects.create(canal=canal, url='http://radio/mitre.mp3')
        self.client.post(reverse('canales:organizar_editar'), {'tipo': 'canal', 'canal': canal.pk, 'nombre': 'Radio Mitre',
                                                               'contenido': 'radio', 'activo': 'on', 'categoria': 'ninguna'})
        canal.refresh_from_db()
        self.assertEqual(canal.contenido, 'radio')


class ApiSeccionesTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        clave, _ = tokens.crear_token(Usuario.objects.create_user('cliente', None, 'x'))
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {clave}')
        secciones.crear('Radio', Seccion.Forma.VIVO, Seccion.Icono.RADIO)
        importar_m3u('#EXTM3U\n#EXTINF:-1 group-title="AM",Radio Mitre\nhttp://radio/mitre.m3u8\n', seccion='radio')
        importar_m3u('#EXTM3U\n#EXTINF:-1 group-title="Noticias",Canal 26\nhttp://tv/26.m3u8\n')

    def test_la_lista_de_secciones(self):
        datos = self.client.get(reverse('api_v1:canales_secciones')).json()
        self.assertEqual(datos, {'secciones': [{'clave': 'radio', 'nombre': 'Radio', 'forma': 'vivo',
                                                'icono': 'radio'}]})

    def test_cada_seccion_trae_lo_suyo(self):
        url = reverse('api_v1:canales')
        en_vivo = self.client.get(url).json()
        self.assertEqual([c['nombre'] for g in en_vivo['categorias'] for c in g['canales']], ['Canal 26'])
        radio = self.client.get(url, {'contenido': 'radio'}).json()
        self.assertEqual([(g['nombre'], [c['nombre'] for c in g['canales']]) for g in radio['categorias']],
                         [('AM', ['Radio Mitre'])])
