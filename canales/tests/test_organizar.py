"""Ordenar el contenido: categorías (crear, renombrar, juntar, borrar, ordenar) y cambiar el tipo."""

from django.test import TestCase
from django.urls import reverse

from canales import organizar
from canales.models import Canal, Categoria, Contenido, Fuente
from canales.servicios import importar_m3u
from usuarios.models import Rol, Usuario


def _canal(nombre, contenido=Contenido.VIVO, categoria=None):
    return Canal.objects.create(nombre=nombre, contenido=contenido, categoria=categoria)


class CategoriasTests(TestCase):

    def setUp(self):
        self.deportes = Categoria.objects.create(nombre='Deportes')
        self.sports = Categoria.objects.create(nombre='SPORTS HD')
        self.ar = Categoria.objects.create(nombre='AR | Deportes')
        self.tyc = _canal('TyC', categoria=self.sports)
        self.dxtv = _canal('DeporTV', categoria=self.ar)

    def test_juntar_pasa_todo_y_recuerda_los_nombres(self):
        final = organizar.juntar_categorias([self.deportes, self.sports, self.ar], 'Deportes')
        self.assertEqual(final, self.deportes)
        self.assertEqual(set(Canal.objects.values_list('categoria__nombre', flat=True)), {'Deportes'})
        self.assertEqual(list(Categoria.objects.values_list('nombre', flat=True)), ['Deportes'])
        self.assertEqual(set(final.otros_nombres.splitlines()), {'SPORTS HD', 'AR | Deportes'})

    def test_la_importacion_respeta_lo_juntado(self):
        organizar.juntar_categorias([self.deportes, self.sports], 'Deportes')
        importar_m3u('#EXTM3U\n#EXTINF:-1 group-title="Sports HD",ESPN Prueba\nhttps://x/espn.m3u8\n'
                      '#EXTINF:-1 group-title="Infantil",Zenón\nhttps://x/zenon.m3u8\n')
        self.assertEqual(Canal.objects.get(nombre='ESPN Prueba').categoria, self.deportes)   # no volvió "SPORTS HD"
        self.assertTrue(Categoria.objects.filter(nombre='Infantil').exists())                  # lo nuevo, nuevo

    def test_juntar_en_un_nombre_nuevo(self):
        final = organizar.juntar_categorias([self.sports, self.ar], 'Fútbol')
        self.assertEqual(final.nombre, 'Fútbol')
        self.assertEqual(set(Canal.objects.values_list('categoria__nombre', flat=True)), {'Fútbol'})

    def test_juntar_necesita_dos(self):
        with self.assertRaises(organizar.NoSePuede):
            organizar.juntar_categorias([self.sports], 'SPORTS HD')

    def test_renombrar_recuerda_el_nombre_viejo(self):
        organizar.renombrar_categoria(self.sports, 'Deportes del mundo')
        self.sports.refresh_from_db()
        self.assertEqual((self.sports.nombre, self.sports.otros_nombres), ('Deportes del mundo', 'SPORTS HD'))
        self.assertEqual(organizar.categoria_por_nombre('sports hd'), self.sports)

    def test_renombrar_como_otra_que_existe_las_junta(self):
        final = organizar.renombrar_categoria(self.sports, 'deportes')
        self.assertEqual(final, self.deportes)
        self.assertEqual(Canal.objects.get(nombre='TyC').categoria, self.deportes)

    def test_crear_no_repite(self):
        organizar.crear_categoria('Infantiles')
        with self.assertRaises(organizar.NoSePuede):
            organizar.crear_categoria('INFANTILES')

    def test_borrar_deja_sin_categoria(self):
        self.assertEqual(organizar.borrar_categoria(self.sports), 1)
        self.assertIsNone(Canal.objects.get(nombre='TyC').categoria)
        self.assertFalse(Categoria.objects.filter(nombre='SPORTS HD').exists())

    def test_sugiere_las_parecidas(self):
        Categoria.objects.create(nombre='Noticias')
        grupos = organizar.categorias_parecidas(list(Categoria.objects.all()))
        self.assertEqual(len(grupos), 1)
        self.assertEqual({c.nombre for c in grupos[0]}, {'Deportes', 'SPORTS HD', 'AR | Deportes'})
        self.assertEqual(organizar.clave_parecida('Kids'), organizar.clave_parecida('INFANTILES'))


class CambiarTipoTests(TestCase):

    def test_peliculas_a_una_serie_numerada(self):
        for nombre in ('Flash Gordon Capitulo 10 El final', 'Flash Gordon Capitulo 2 La caverna',
                       'Flash Gordon Capitulo 1 El planeta'):
            _canal(nombre, Contenido.PELICULA)
        cantidad, sin_numero = organizar.cambiar_contenido(
            Canal.objects.all(), Contenido.SERIE, nombre_serie='Flash Gordon', temporada=1)
        self.assertEqual((cantidad, sin_numero), (3, 0))
        nombres = list(Canal.objects.order_by('nombre').values_list('nombre', 'contenido'))
        self.assertEqual(nombres, [('Flash Gordon S01 E01 Capitulo 1 El planeta', 'serie'),
                                   ('Flash Gordon S01 E02 Capitulo 2 La caverna', 'serie'),
                                   ('Flash Gordon S01 E03 Capitulo 10 El final', 'serie')])   # 10 va después de 2

    def test_a_serie_sin_nombre_avisa_los_que_no_dicen_capitulo(self):
        _canal('Arrow S01 E01', Contenido.PELICULA)
        _canal('Una película cualquiera', Contenido.PELICULA)
        self.assertEqual(organizar.cambiar_contenido(Canal.objects.all(), Contenido.SERIE), (2, 1))
        self.assertEqual(Canal.objects.get(nombre='Arrow S01 E01').contenido, Contenido.SERIE)

    def test_series_enteras_a_peliculas(self):
        for n in (1, 2, 3):
            _canal(f'Arrow S01 E0{n}', Contenido.SERIE)
        _canal('Otra S01 E01', Contenido.SERIE)
        capitulos = organizar.capitulos_de(['arrow'])
        self.assertEqual(capitulos.count(), 3)
        organizar.cambiar_contenido(capitulos, Contenido.PELICULA)
        self.assertEqual(Canal.objects.filter(contenido=Contenido.PELICULA).count(), 3)


class PantallasTests(TestCase):

    def setUp(self):
        self.admin = Usuario.objects.create_superuser('admin', 'admin@test.com', 'x')
        self.client.force_login(self.admin)
        self.deportes = Categoria.objects.create(nombre='Deportes')
        self.sports = Categoria.objects.create(nombre='Sports')
        self.tyc = _canal('TyC', categoria=self.sports)
        Fuente.objects.create(canal=self.tyc, url='https://x/tyc.m3u8')

    def test_la_pagina_muestra_las_parecidas(self):
        respuesta = self.client.get(reverse('canales:categorias'))
        self.assertContains(respuesta, 'Parecen repetidas')
        self.assertContains(respuesta, 'Sports')

    def test_juntar_y_ordenar_desde_la_pagina(self):
        url = reverse('canales:categorias')
        self.client.post(url, {'accion': 'juntar', 'elegida': [self.deportes.pk, self.sports.pk], 'destino': 'Deportes'})
        self.assertEqual(Canal.objects.get(nombre='TyC').categoria, self.deportes)
        self.client.post(url, {'accion': 'ordenar', f'orden_{self.deportes.pk}': '5'})
        self.deportes.refresh_from_db()
        self.assertEqual(self.deportes.orden, 5)
        respuesta = self.client.post(url, {'accion': 'crear', 'nombre': ''}, follow=True)
        self.assertContains(respuesta, 'Escribí el nombre')

    def test_mover_elegidos_desde_el_catalogo(self):
        self.client.post(reverse('canales:catalogo_categoria'), {'canal': [self.tyc.pk], 'nueva_categoria': 'Fútbol'})
        self.assertEqual(Canal.objects.get(nombre='TyC').categoria.nombre, 'Fútbol')
        self.client.post(reverse('canales:catalogo_categoria'), {'canal': [self.tyc.pk], 'categoria': 'ninguna'})
        self.assertIsNone(Canal.objects.get(nombre='TyC').categoria)

    def test_cambiar_tipo_desde_el_catalogo(self):
        respuesta = self.client.post(reverse('canales:catalogo_contenido'),
                                     {'canal': [self.tyc.pk], 'contenido': 'pelicula'}, follow=True)
        self.assertContains(respuesta, 'pasaron a películas')
        self.assertEqual(Canal.objects.get(nombre='TyC').contenido, Contenido.PELICULA)
        self.assertEqual(self.client.get(reverse('canales:catalogo'), {'contenido': 'pelicula'}).status_code, 200)

    def test_acciones_sobre_series(self):
        for n in (1, 2, 3):
            _canal(f'Arrow S01 E0{n}', Contenido.SERIE)
        self.assertContains(self.client.get(reverse('canales:series')), 'Mover elegidas')
        self.client.post(reverse('canales:series_acciones'),
                         {'serie': ['Arrow'], 'accion': 'mover', 'categoria': self.deportes.pk})
        self.assertEqual(set(Canal.objects.filter(contenido='serie').values_list('categoria', flat=True)),
                         {self.deportes.pk})
        self.client.post(reverse('canales:series_acciones'), {'serie': ['Arrow'], 'accion': 'a_peliculas'})
        self.assertFalse(Canal.objects.filter(contenido='serie').exists())

    def test_solo_con_permiso_de_importar(self):
        solo_ve = Usuario.objects.create_user(
            'mira', None, 'x', rol=Rol.objects.create(nombre='Mira', permisos=['ver_canales']))
        self.client.force_login(solo_ve)
        self.assertEqual(self.client.get(reverse('canales:categorias')).status_code, 403)
        self.assertEqual(self.client.post(reverse('canales:catalogo_categoria')).status_code, 403)
        self.assertEqual(self.client.post(reverse('canales:catalogo_contenido')).status_code, 403)
        self.assertEqual(self.client.post(reverse('canales:series_acciones')).status_code, 403)
        self.assertNotContains(self.client.get(reverse('canales:series')), 'Mover elegidas')
