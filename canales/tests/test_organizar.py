"""Ordenar el contenido: categorías (crear, renombrar, juntar, borrar, ordenar) y cambiar el tipo."""

from django.test import TestCase
from django.urls import reverse

from canales import consultas, organizar
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


class ComoEnLaAppTests(TestCase):
    """La vista "Como en la app": las categorías con cuántos tienen, con las reglas de la app."""

    def setUp(self):
        self.admin = Usuario.objects.create_superuser('admin', 'admin@test.com', 'x')
        self.client.force_login(self.admin)
        self.kids = Categoria.objects.create(nombre='Kids', orden=1)
        self.ar_kids = Categoria.objects.create(nombre='AR | KIDS', orden=2)

    def _con_fuente(self, nombre, contenido=Contenido.VIVO, categoria=None):
        canal = _canal(nombre, contenido, categoria)
        Fuente.objects.create(canal=canal, url=f'https://x/{canal.pk}.m3u8')
        return canal

    def test_el_nombre_como_lo_muestra_la_app(self):
        self.assertEqual(consultas.nombre_en_la_app('AR | DEPORTES'), 'Deportes')
        self.assertEqual(consultas.nombre_en_la_app('Kids'), 'Kids')
        self.assertEqual(consultas.nombre_en_la_app('TV'), 'TV')
        self.assertEqual(consultas.nombre_en_la_app(''), 'Otros')

    def test_solo_cuenta_lo_que_la_app_muestra(self):
        self._con_fuente('Zenón', categoria=self.kids)
        self._con_fuente('Disney', categoria=self.kids)
        quitado = self._con_fuente('Quitado', categoria=self.kids)
        Canal.objects.filter(pk=quitado.pk).update(activo=False)
        _canal('Sin fuentes', categoria=self.kids)
        self._con_fuente('Suelto')
        grupos = consultas.como_en_la_app(Contenido.VIVO)
        self.assertEqual([(c and c.nombre, [x.nombre for x in items]) for c, items in grupos],
                         [('Kids', ['Disney', 'Zenón']), (None, ['Suelto'])])

    def test_series_solo_las_completas(self):
        for n in (1, 2, 3):
            self._con_fuente(f'Arrow S01 E0{n}', Contenido.SERIE, self.kids)
        self._con_fuente('A medias S01 E02', Contenido.SERIE, self.kids)
        [(categoria, series)] = consultas.como_en_la_app(Contenido.SERIE)
        self.assertEqual((categoria, [(s.nombre, s.capitulos) for s in series]), (self.kids, [('Arrow', 3)]))


class OrganizarTests(TestCase):
    """Organizar contenido: subcategorías, edición rápida, eliminar, origen e importar en una categoría."""

    def setUp(self):
        self.client.force_login(Usuario.objects.create_superuser('admin', 'admin@test.com', 'x'))
        self.musica = Categoria.objects.create(nombre='Música', orden=1)
        self.noticias = Categoria.objects.create(nombre='Noticias', orden=2)
        self.rock = organizar.crear_categoria('Rock', padre=self.musica)
        self.pop = organizar.crear_categoria('Pop', padre=self.musica)

    def _con_fuente(self, nombre, categoria=None, contenido=Contenido.VIVO, origen='lista-prueba.m3u'):
        canal = _canal(nombre, contenido, categoria)
        Fuente.objects.create(canal=canal, url=f'https://x/{nombre.replace(" ", "")}.m3u8', origen=origen)
        return canal

    def test_la_app_ve_las_subcategorias_con_su_padre_y_en_orden(self):
        self.rock.orden = 9
        self.rock.save()
        self._con_fuente('TN', self.noticias)
        self._con_fuente('Rock FM', self.rock)
        self._con_fuente('Radio Mix', self.musica)
        canales = consultas.canales_disponibles(contenido=Contenido.VIVO)
        nombres = [c.nombre_en_app for c, _ in consultas.agrupar_por_categoria(canales)]
        self.assertEqual(nombres, ['Música', 'Música · Rock', 'Noticias'])   # Rock va pegada a Música

    def test_un_solo_nivel_de_subcategorias(self):
        with self.assertRaises(organizar.NoSePuede):
            organizar.crear_categoria('Punk', padre=self.rock)
        with self.assertRaises(organizar.NoSePuede):
            organizar.ubicar_categoria(self.musica, self.noticias)   # Música tiene subcategorías
        organizar.ubicar_categoria(self.pop, None)
        self.pop.refresh_from_db()
        self.assertIsNone(self.pop.padre)

    def test_el_arbol_cuenta_lo_de_las_subcategorias(self):
        self._con_fuente('Rock FM', self.rock)
        self._con_fuente('Rock & Pop', self.rock)
        self._con_fuente('Los 40', self.pop)
        datos = consultas.organizar_contenido(Contenido.VIVO, categoria=str(self.musica.pk))
        nodos = {n['clave']: n for n in datos.nodos}
        self.assertEqual((nodos[str(self.musica.pk)]['total'], nodos[str(self.rock.pk)]['total']), (3, 2))
        self.assertEqual(len(datos.pagina.object_list), 3)   # la principal muestra lo de sus subcategorías
        self.assertEqual([c.nombre for c, _ in datos.grupos], ['Pop', 'Rock'])

    def test_la_pagina_muestra_arbol_y_de_donde_salio(self):
        self._con_fuente('Rock FM', self.rock, origen='YouTube: Radio Oficial')
        respuesta = self.client.get(reverse('canales:organizar'), {'categoria': self.rock.pk})
        self.assertContains(respuesta, 'Nueva categoría')
        self.assertContains(respuesta, 'nivel-1')
        self.assertContains(respuesta, 'YouTube: Radio Oficial')   # en los datos de la edición rápida
        self.assertContains(respuesta, 'En la app: «Música · Rock»')
        self.assertRedirects(self.client.get(reverse('canales:como_en_la_app')), reverse('canales:organizar') + '?',
                             fetch_redirect_response=False)

    def test_crear_subcategoria_desde_la_pagina(self):
        volver = reverse('canales:organizar')
        self.client.post(reverse('canales:categorias'),
                         {'accion': 'crear', 'nombre': 'Jazz', 'padre': self.musica.pk, 'volver': volver})
        self.assertEqual(Categoria.objects.get(nombre='Jazz').padre, self.musica)

    def test_borrar_solo_la_categoria(self):
        radio = self._con_fuente('Radio Mix', self.musica)
        organizar.borrar_categoria(self.musica)
        radio.refresh_from_db()
        self.rock.refresh_from_db()
        self.assertIsNone(radio.categoria)
        self.assertIsNone(self.rock.padre)   # la subcategoría queda como principal

    def test_borrar_la_categoria_con_todo_y_poder_reimportarlo(self):
        self._con_fuente('Rock FM', self.rock)
        self._con_fuente('Radio Mix', self.musica)
        tn = self._con_fuente('TN', self.noticias)
        self.client.post(reverse('canales:categorias'), {'accion': 'borrar', 'categoria': self.musica.pk,
                                                         'con_contenido': '1'})
        self.assertEqual(list(Canal.objects.values_list('nombre', flat=True)), ['TN'])
        self.assertFalse(Categoria.objects.filter(nombre__in=['Música', 'Rock', 'Pop']).exists())
        self.assertEqual(Fuente.objects.get().canal, tn)
        importar_m3u('#EXTM3U\n#EXTINF:-1 group-title="Rock",Rock FM\nhttps://x/RockFM.m3u8\n')
        self.assertTrue(Canal.objects.filter(nombre='Rock FM').exists())   # vuelve si se importa de nuevo

    def test_edicion_rapida(self):
        canal = self._con_fuente('Rock FM', self.noticias)
        self.client.post(reverse('canales:organizar_editar'), {
            'tipo': 'canal', 'canal': canal.pk, 'nombre': 'Rock FM 95.9', 'logo': 'https://ejemplo.com/logo.png',
            'categoria': self.rock.pk, 'contenido': 'vivo', 'numero': '95'})   # sin "activo": se quita
        canal.refresh_from_db()
        self.assertEqual((canal.nombre, canal.logo, canal.categoria, canal.numero, canal.activo),
                         ('Rock FM 95.9', 'https://ejemplo.com/logo.png', self.rock, '95', False))

    def test_edicion_rapida_de_una_serie_entera(self):
        for n in (1, 2, 3):
            self._con_fuente(f'Arrow S01 E0{n} Piloto', self.noticias, Contenido.SERIE)
        self.client.post(reverse('canales:organizar_editar'), {
            'tipo': 'serie', 'serie': 'Arrow', 'nombre': 'Flecha', 'logo': '', 'categoria': self.rock.pk,
            'activo': 'on'})
        self.assertEqual(sorted(Canal.objects.values_list('nombre', 'categoria')),
                         [(f'Flecha S01 E0{n} Piloto', self.rock.pk) for n in (1, 2, 3)])

    def test_eliminar_desde_la_pagina(self):
        canal = self._con_fuente('Rock FM', self.rock)
        self.client.post(reverse('canales:organizar_eliminar'), {'canal': [canal.pk]})
        self.assertFalse(Canal.objects.filter(pk=canal.pk).exists())
        self.assertTrue(Canal.todos.filter(pk=canal.pk).exists())   # queda para las estadísticas

    def test_importar_todo_en_una_categoria(self):
        importar_m3u('#EXTM3U\n#EXTINF:-1 group-title="Varios",Rock FM\nhttps://x/rock.m3u8\n', categoria='Rock')
        self.assertEqual(Canal.objects.get(nombre='Rock FM').categoria, self.rock)

    def test_quien_solo_mira_no_puede_tocar(self):
        self._con_fuente('Rock FM', self.rock)
        solo_ve = Usuario.objects.create_user(
            'mira', None, 'x', rol=Rol.objects.create(nombre='Mira', permisos=['ver_canales']))
        self.client.force_login(solo_ve)
        respuesta = self.client.get(reverse('canales:organizar'))
        self.assertContains(respuesta, 'Rock FM')
        self.assertNotContains(respuesta, 'Nueva categoría')
        self.assertNotContains(respuesta, 'class="form-check-input canal-elegir"')
        self.assertEqual(self.client.post(reverse('canales:organizar_editar')).status_code, 403)
        self.assertEqual(self.client.post(reverse('canales:organizar_eliminar')).status_code, 403)

    def test_las_pestanias_de_peliculas_y_series(self):
        self._con_fuente('Tormenta Blanca', self.rock, Contenido.PELICULA, origen='YouTube: Movie Central')
        for n in (1, 2, 3):
            self._con_fuente(f'Arrow S01 E0{n}', self.rock, Contenido.SERIE)
        peliculas = self.client.get(reverse('canales:organizar'), {'contenido': 'pelicula', 'mostrar': 'app'})
        self.assertContains(peliculas, 'Tormenta Blanca')
        self.assertContains(peliculas, 'YouTube: Movie Central')
        series = self.client.get(reverse('canales:organizar'), {'contenido': 'serie', 'q': 'arr'})
        self.assertContains(series, 'Arrow')
        self.assertContains(series, '3 cap.')
        self.assertContains(series, 'value="Arrow"')   # se eligen series enteras
