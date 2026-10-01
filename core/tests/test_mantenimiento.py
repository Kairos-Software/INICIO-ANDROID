from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from actividad.models import Accion, RegistroActividad
from core.models import EstadoMantenimiento
from usuarios.models import Usuario

URL_CONFIG = reverse('core:mantenimiento')
URL_INICIO = reverse('core:inicio')


class ModoMantenimientoTests(TestCase):

    def setUp(self):
        cache.clear()
        self.dueno = Usuario.objects.create_superuser('dueno', 'd@test.com', 'x')
        self.empleado = Usuario.objects.create_user('empleado', None, 'Clave-empleado-1')

    def tearDown(self):
        cache.clear()   # el estado se guarda en caché: que no pase al siguiente test

    def activar(self, **extra):
        self.client.force_login(self.dueno)
        self.client.post(URL_CONFIG, {'activo': 'on', **extra})
        self.client.logout()

    def test_solo_superusuario_configura(self):
        self.client.force_login(self.empleado)
        self.assertEqual(self.client.get(URL_CONFIG).status_code, 403)

    def test_empleado_ve_la_pantalla_de_mantenimiento(self):
        self.activar(mensaje='Actualizamos la facturación', vuelve_aprox='a las 15:30')
        self.client.force_login(self.empleado)
        respuesta = self.client.get(URL_INICIO)
        self.assertEqual(respuesta.status_code, 503)
        self.assertContains(respuesta, 'Estamos actualizando el sistema', status_code=503)
        self.assertContains(respuesta, 'Actualizamos la facturación', status_code=503)
        self.assertContains(respuesta, 'a las 15:30', status_code=503)
        self.assertEqual(respuesta['Retry-After'], '300')

    def test_superusuario_sigue_entrando_y_ve_el_aviso(self):
        self.activar()
        self.client.force_login(self.dueno)
        respuesta = self.client.get(URL_INICIO)
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'Modo mantenimiento activo')

    def test_login_sigue_disponible(self):
        self.activar()
        self.assertEqual(self.client.get(reverse('usuarios:login')).status_code, 200)

    def test_pantalla_ofrece_ingresar(self):
        self.activar()
        self.assertContains(self.client.get(URL_INICIO), reverse('usuarios:login'), status_code=503)

    def test_empleado_no_puede_iniciar_sesion(self):
        self.activar()
        respuesta = self.client.post(reverse('usuarios:login'),
                                     {'username': 'empleado', 'password': 'Clave-empleado-1'})
        self.assertContains(respuesta, 'solo pueden ingresar los administradores')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_sesion_de_empleado_se_cierra_y_puede_entrar_un_superusuario(self):
        # El caso que dejaba trabado: un empleado con sesión abierta no podía
        # volver al login (lo mandaba al inicio = pantalla de mantenimiento)
        self.dueno.set_password('Clave-dueno-1')
        self.dueno.save()
        self.client.force_login(self.empleado)
        self.activar()
        self.client.force_login(self.empleado)
        self.assertEqual(self.client.get(URL_INICIO).status_code, 503)
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertEqual(self.client.get(reverse('usuarios:login')).status_code, 200)
        self.client.post(reverse('usuarios:login'), {'username': 'dueno', 'password': 'Clave-dueno-1'})
        self.assertEqual(self.client.get(URL_INICIO).status_code, 200)

    def test_desactivar(self):
        self.activar()
        self.client.force_login(self.dueno)
        self.client.post(URL_CONFIG, {})
        self.client.force_login(self.empleado)
        self.assertEqual(self.client.get(URL_INICIO).status_code, 200)

    def test_queda_registrado(self):
        self.activar()
        registro = RegistroActividad.objects.get(accion=Accion.SISTEMA)
        self.assertEqual(registro.usuario, self.dueno)
        self.assertIn('Activó el modo mantenimiento', registro.descripcion)

    @override_settings(MODO_MANTENIMIENTO=True)
    def test_forzado_desde_el_env(self):
        self.assertFalse(EstadoMantenimiento.obtener().activo)
        self.client.force_login(self.empleado)
        self.assertEqual(self.client.get(URL_INICIO).status_code, 503)
        self.client.force_login(self.dueno)
        self.assertContains(self.client.get(URL_CONFIG), 'forzado desde el archivo .env')

    def test_vista_previa(self):
        self.client.force_login(self.dueno)
        respuesta = self.client.get(reverse('core:mantenimiento_vista_previa'))
        self.assertContains(respuesta, 'Estamos actualizando el sistema')


class LimpiarRegistrosTests(TestCase):

    def test_borra_lo_viejo(self):
        from datetime import timedelta

        from django.core.management import call_command
        from django.utils import timezone

        from actividad.registro import registrar
        from notificaciones.models import Notificacion
        from notificaciones.servicios import notificar

        usuario = Usuario.objects.create_user('ana', None, 'x')
        viejo = registrar(usuario, Accion.OTRO, 'Viejo')
        registrar(usuario, Accion.OTRO, 'Reciente')
        RegistroActividad.objects.filter(pk=viejo.pk).update(fecha=timezone.now() - timedelta(days=400))

        notificar(usuario, 'Leída vieja')
        notificar(usuario, 'Sin leer vieja')
        hace_mucho = timezone.now() - timedelta(days=100)
        Notificacion.objects.update(creada=hace_mucho)
        Notificacion.objects.filter(titulo='Leída vieja').update(leida_en=hace_mucho)

        call_command('limpiar_registros', stdout=open('nul' if __import__('os').name == 'nt' else '/dev/null', 'w'))

        self.assertEqual(list(RegistroActividad.objects.values_list('descripcion', flat=True)), ['Reciente'])
        # Las no leídas nunca se borran
        self.assertEqual(list(Notificacion.objects.values_list('titulo', flat=True)), ['Sin leer vieja'])
