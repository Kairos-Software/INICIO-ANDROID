"""Lo más visto: lo que cuenta la app (sin saber quién) y el ranking del panel."""

from datetime import timedelta
from decimal import Decimal

from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from canales import estadisticas
from canales.models import Canal, Contenido, FavoritoAgregado, Visto
from reventa import servicios as reventa
from usuarios.models import Rol, Usuario


def _canal(nombre, contenido=Contenido.VIVO, **datos):
    return Canal.objects.create(nombre=nombre, contenido=contenido, **datos)


class RegistrarTests(TestCase):

    def setUp(self):
        self.tn = _canal('TN')
        self.hoy = timezone.localdate()

    def test_suma_los_segundos_y_las_vistas_del_dia(self):
        estadisticas.registrar([{'id': self.tn.pk, 'segundos': 300, 'vista': True}])
        estadisticas.registrar([{'id': self.tn.pk, 'segundos': 120}])   # el mismo rato, sigue: no es otra vista
        visto = Visto.objects.get()
        self.assertEqual((visto.fecha, visto.segundos, visto.vistas), (self.hoy, 420, 1))

    def test_cada_dia_va_aparte(self):
        estadisticas.registrar([{'id': self.tn.pk, 'segundos': 60}], hoy=self.hoy - timedelta(days=1))
        estadisticas.registrar([{'id': self.tn.pk, 'segundos': 60}])
        self.assertEqual(Visto.objects.count(), 2)

    def test_ignora_lo_que_no_entiende_o_no_existe(self):
        sumados = estadisticas.registrar(
            [{'id': 999999, 'segundos': 60}, {'id': 'x'}, {'segundos': 5}, 'cualquier cosa',
             {'id': self.tn.pk, 'segundos': -40}],
            ['c:12', 's:Flash Gordon', 'otra cosa', 7, 'c:'])
        self.assertEqual(sumados, 2)   # solo los dos favoritos bien escritos
        self.assertFalse(Visto.objects.exists())
        self.assertEqual(set(FavoritoAgregado.objects.values_list('clave', flat=True)), {'c:12', 's:Flash Gordon'})

    def test_un_aviso_no_puede_sumar_mas_de_seis_horas(self):
        estadisticas.registrar([{'id': self.tn.pk, 'segundos': 10 ** 9}])
        self.assertEqual(Visto.objects.get().segundos, estadisticas.MAXIMO_DE_SEGUNDOS)


class RankingTests(TestCase):

    def setUp(self):
        self.hoy = timezone.localdate()
        self.tn = _canal('TN', logo='https://x/tn.png')
        self.c5n = _canal('C5N')
        self.matrix = _canal('Matrix (1999)', Contenido.PELICULA)
        self.ep1 = _canal('Flash Gordon S01 E01', Contenido.SERIE, logo='https://x/fg.png')
        self.ep2 = _canal('Flash Gordon S01 E02', Contenido.SERIE)
        self.otra = _canal('Superman S01 E01', Contenido.SERIE)

    def registrar(self, canal, minutos, vista=True, hace=0):
        estadisticas.registrar([{'id': canal.pk, 'segundos': minutos * 60, 'vista': vista}],
                               hoy=self.hoy - timedelta(days=hace))

    def test_separa_y_ordena_por_tiempo_mirado(self):
        self.registrar(self.tn, 30)
        self.registrar(self.c5n, 90)
        self.registrar(self.matrix, 100)
        ranking = estadisticas.lo_mas_visto(30)
        self.assertEqual([f.nombre for f in ranking.vivo], ['C5N', 'TN'])
        self.assertEqual([f.nombre for f in ranking.pelicula], ['Matrix (1999)'])
        self.assertEqual(ranking.vivo[0].tiempo, '1 h 30 min')
        self.assertEqual(ranking.totales['vivo'].tiempo, '2 h 0 min')
        self.assertEqual(ranking.totales['vivo'].vistas, 2)

    def test_las_series_se_juntan_con_sus_capitulos_y_favoritos(self):
        self.registrar(self.ep1, 20)
        self.registrar(self.ep2, 25)
        self.registrar(self.otra, 5)
        estadisticas.registrar([], ['s:Flash Gordon', 's:flash gordon', 's:Los Simuladores'])
        series = {f.nombre: f for f in estadisticas.lo_mas_visto(30).serie}
        flash = series['Flash Gordon']
        self.assertEqual((flash.segundos, flash.vistas, flash.capitulos, flash.favoritos), (45 * 60, 2, 2, 2))
        self.assertEqual(flash.logo, 'https://x/fg.png')
        self.assertEqual(list(series), ['Flash Gordon', 'Superman', 'Los Simuladores'])   # favorita sin ver: al final
        self.assertEqual(series['Los Simuladores'].favoritos, 1)

    def test_los_favoritos_de_canales_y_peliculas(self):
        estadisticas.registrar([], [f'c:{self.matrix.pk}', f'c:{self.matrix.pk}'])
        pelicula = estadisticas.lo_mas_visto(30).pelicula[0]
        self.assertEqual((pelicula.nombre, pelicula.favoritos, pelicula.segundos), ('Matrix (1999)', 2, 0))

    def test_solo_cuenta_el_periodo_elegido(self):
        self.registrar(self.tn, 10, hace=3)
        self.registrar(self.c5n, 10, hace=20)
        self.assertEqual([f.nombre for f in estadisticas.lo_mas_visto(7).vivo], ['TN'])
        self.assertEqual(len(estadisticas.lo_mas_visto(30).vivo), 2)

    def test_lo_quitado_igual_cuenta_y_se_marca(self):
        self.registrar(self.tn, 10)
        Canal.objects.filter(pk=self.tn.pk).update(activo=False)
        self.assertFalse(estadisticas.lo_mas_visto(30).vivo[0].en_la_app)


class AvisoDeLaAppTests(TestCase):
    """POST /api/v1/canales/visto/ desde la app de un cliente (el que entra con el código)."""

    def setUp(self):
        cache.clear()
        juan = reventa.crear_revendedor('juan', 'Clave-segura-2026', precio_pantalla=Decimal('5000'))
        reventa.regalar_creditos(juan, 5)
        cliente = reventa.crear_cliente(juan, 'Ana')
        reventa.renovar(cliente, dispositivos=1)
        cliente.refresh_from_db()
        respuesta = APIClient().post(reverse('api_v1:cliente_login'),
                                     {'codigo': cliente.codigo_legible, 'dispositivo': 'TV'})
        self.app = APIClient()
        self.app.credentials(HTTP_AUTHORIZATION=f'Bearer {respuesta.json()["token"]}')
        self.tn = _canal('TN')

    def test_el_cliente_puede_avisar_y_se_suma(self):
        respuesta = self.app.post(reverse('api_v1:canales_visto'),
                                  {'vistos': [{'id': self.tn.pk, 'segundos': 300, 'vista': True}],
                                   'favoritos': [f'c:{self.tn.pk}']}, format='json')
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        self.assertEqual(respuesta.json()['sumados'], 2)
        self.assertEqual(Visto.objects.get().segundos, 300)
        self.assertEqual(FavoritoAgregado.objects.get().veces, 1)

    def test_un_pedido_mal_armado_no_rompe(self):
        for cuerpo in ({}, {'vistos': 'x', 'favoritos': {'a': 1}}, {'vistos': [None]}):
            respuesta = self.app.post(reverse('api_v1:canales_visto'), cuerpo, format='json')
            self.assertEqual(respuesta.status_code, 200)
            self.assertEqual(respuesta.json()['sumados'], 0)

    def test_sin_sesion_no(self):
        respuesta = APIClient().post(reverse('api_v1:canales_visto'), {}, format='json')
        self.assertIn(respuesta.status_code, (401, 403))


class PantallaDelPanelTests(TestCase):
    URL = reverse('canales:lo_mas_visto')

    def setUp(self):
        self.admin = Usuario.objects.create_superuser('admin', 'admin@test.com', 'x')
        tn = _canal('TN')
        estadisticas.registrar([{'id': tn.pk, 'segundos': 3600, 'vista': True}])

    def test_el_administrador_la_ve(self):
        self.client.force_login(self.admin)
        respuesta = self.client.get(self.URL)
        self.assertContains(respuesta, 'Lo más visto')
        self.assertContains(respuesta, 'TN')
        self.assertContains(respuesta, '1 h 0 min')
        self.assertContains(self.client.get(self.URL, {'tipo': 'serie', 'dias': 7}), 'Todavía no hay datos')
        self.assertEqual(self.client.get(self.URL, {'tipo': 'otro', 'dias': 'x'}).status_code, 200)

    def test_sin_el_permiso_no(self):
        solo_ve = Usuario.objects.create_user(
            'mira', None, 'x', rol=Rol.objects.create(nombre='Mira', permisos=['ver_canales']))
        self.client.force_login(solo_ve)
        self.assertEqual(self.client.get(self.URL).status_code, 403)
        self.assertNotContains(self.client.get(reverse('canales:inicio')), 'Lo más visto')
