from django.core.cache import cache
from django.http import HttpResponse
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from usuarios.decoradores import requiere_permiso
from usuarios.models import Rol, Usuario

URL_LOGIN = reverse('usuarios:login')
URL_INICIO = reverse('core:inicio')


class LoginTests(TestCase):

    def setUp(self):
        cache.clear()
        self.usuario = Usuario.objects.create_user('juan', 'juan@test.com', 'clave-segura-123')

    def entrar(self, identificador, password='clave-segura-123', **extra):
        return self.client.post(URL_LOGIN, {'username': identificador, 'password': password, **extra})

    def test_pantalla_login(self):
        respuesta = self.client.get(URL_LOGIN)
        self.assertContains(respuesta, 'Iniciar sesión')

    def test_entrar_con_usuario(self):
        self.assertRedirects(self.entrar('juan'), URL_INICIO)

    def test_entrar_con_email_y_mayusculas(self):
        self.assertRedirects(self.entrar('JUAN@Test.com'), URL_INICIO)
        self.client.logout()
        self.assertRedirects(self.entrar('Juan'), URL_INICIO)

    def test_password_incorrecta(self):
        respuesta = self.entrar('juan', 'otra')
        self.assertContains(respuesta, 'Usuario o contraseña incorrectos.')

    def test_usuario_inexistente(self):
        self.assertContains(self.entrar('nadie'), 'Usuario o contraseña incorrectos.')

    def test_usuario_inactivo_no_entra(self):
        self.usuario.is_active = False
        self.usuario.save()
        self.assertContains(self.entrar('juan'), 'Usuario o contraseña incorrectos.')

    @override_settings(LOGIN_INTENTOS_MAXIMOS=3)
    def test_bloqueo_por_intentos_fallidos(self):
        for _ in range(3):
            self.entrar('juan', 'mala')
        # Con la contraseña correcta igual queda bloqueado
        respuesta = self.entrar('juan')
        self.assertContains(respuesta, 'Demasiados intentos fallidos')
        # Otro usuario desde la misma IP no se ve afectado
        Usuario.objects.create_user('ana', None, 'clave-segura-123')
        self.assertRedirects(self.entrar('ana'), URL_INICIO)

    def test_login_exitoso_limpia_intentos(self):
        self.entrar('juan', 'mala')
        self.entrar('juan')
        self.assertEqual(cache.get('login_fallidos:juan:127.0.0.1'), None)

    def test_sin_recordarme_la_sesion_cierra_con_el_navegador(self):
        self.entrar('juan')
        self.assertTrue(self.client.session.get_expire_at_browser_close())

    def test_con_recordarme_la_sesion_dura(self):
        self.entrar('juan', recordarme='on')
        self.assertFalse(self.client.session.get_expire_at_browser_close())

    def test_con_sesion_iniciada_el_login_redirige(self):
        self.client.force_login(self.usuario)
        self.assertRedirects(self.client.get(URL_LOGIN), URL_INICIO)

    def test_respeta_next(self):
        respuesta = self.client.post(
            f'{URL_LOGIN}?next=/admin/',
            {'username': 'juan', 'password': 'clave-segura-123', 'next': '/admin/'},
        )
        self.assertEqual(respuesta.url, '/admin/')

    def test_next_externo_se_ignora(self):
        respuesta = self.entrar('juan', next='https://sitio-malicioso.com/')
        self.assertRedirects(respuesta, URL_INICIO)

    def test_ingreso_anterior(self):
        self.entrar('juan')
        self.assertContains(self.client.get(URL_INICIO), 'Es tu primer ingreso')
        self.client.post(reverse('usuarios:logout'))
        self.entrar('juan')
        self.assertNotContains(self.client.get(URL_INICIO), 'Es tu primer ingreso')


class LogoutTests(TestCase):

    def test_logout_por_post(self):
        usuario = Usuario.objects.create_user('juan', None, 'x')
        self.client.force_login(usuario)
        respuesta = self.client.post(reverse('usuarios:logout'))
        self.assertRedirects(respuesta, URL_LOGIN)
        self.assertRedirects(self.client.get(URL_INICIO), f'{URL_LOGIN}?next={URL_INICIO}')

    def test_logout_por_get_no_permitido(self):
        self.assertEqual(self.client.get(reverse('usuarios:logout')).status_code, 405)


class InicioTests(TestCase):

    def test_inicio_requiere_sesion(self):
        self.assertRedirects(self.client.get(URL_INICIO), f'{URL_LOGIN}?next={URL_INICIO}')

    def test_inicio_con_sesion(self):
        usuario = Usuario.objects.create_user('juan', None, 'x', first_name='Juan')
        self.client.force_login(usuario)
        respuesta = self.client.get(URL_INICIO)
        self.assertContains(respuesta, 'Juan.')
        self.assertContains(respuesta, 'Personalizado')


class RequierePermisoTests(TestCase):

    def setUp(self):
        self.factory = RequestFactory()

        @requiere_permiso('ver_usuarios')
        def vista(request):
            return HttpResponse('ok')

        self.vista = vista

    def pedir(self, usuario):
        request = self.factory.get('/algo/')
        request.user = usuario
        return self.vista(request)

    def test_sin_sesion_va_al_login(self):
        from django.contrib.auth.models import AnonymousUser
        respuesta = self.pedir(AnonymousUser())
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn(URL_LOGIN, respuesta.url)

    def test_sin_permiso_da_403(self):
        from django.core.exceptions import PermissionDenied
        with self.assertRaises(PermissionDenied):
            self.pedir(Usuario.objects.create_user('juan', None, 'x'))

    def test_con_permiso_pasa(self):
        rol = Rol.objects.create(nombre='Consulta', permisos=['ver_usuarios'])
        usuario = Usuario.objects.create_user('juan', None, 'x', rol=rol)
        self.assertEqual(self.pedir(usuario).content, b'ok')
