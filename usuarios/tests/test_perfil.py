from django.test import Client, TestCase
from django.urls import reverse

from usuarios.models import Rol, Usuario

URL_PERFIL = reverse('usuarios:perfil')
URL_EDITAR = reverse('usuarios:perfil_editar')
URL_PASSWORD = reverse('usuarios:cambiar_password')
URL_INICIO = reverse('core:inicio')

CLAVE = 'Clave-actual-2026'
NUEVA = 'Otra-clave-nueva-99'


class PerfilTests(TestCase):

    def setUp(self):
        self.rol = Rol.objects.create(nombre='Consulta', permisos=['ver_usuarios'])
        self.usuario = Usuario.objects.create_user(
            'juan', 'juan@test.com', CLAVE, first_name='Juan', rol=self.rol,
            puesto='Vendedor', notas_internas='Llega tarde',
        )
        self.client.force_login(self.usuario)

    def test_requiere_sesion(self):
        self.client.logout()
        self.assertEqual(self.client.get(URL_PERFIL).status_code, 302)

    def test_ver_perfil(self):
        respuesta = self.client.get(URL_PERFIL)
        self.assertContains(respuesta, 'juan@test.com')
        self.assertContains(respuesta, 'Vendedor')                          # solo lectura
        self.assertContains(respuesta, 'Ver la lista y el detalle de los usuarios')  # sus permisos
        self.assertNotContains(respuesta, 'Llega tarde')                     # notas internas: nunca

    def test_usuario_sin_permisos(self):
        otro = Usuario.objects.create_user('pepe', None, 'x')
        self.client.force_login(otro)
        self.assertContains(self.client.get(URL_PERFIL), 'Por ahora solo podés gestionar tu propio perfil')

    def test_editar_datos_propios(self):
        respuesta = self.client.post(URL_EDITAR, {
            'first_name': 'Juan Carlos', 'email': 'nuevo@test.com', 'pais': 'Uruguay', 'telefono': '099 123',
        })
        self.assertRedirects(respuesta, URL_PERFIL)
        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.first_name, 'Juan Carlos')
        self.assertEqual(self.usuario.email, 'nuevo@test.com')

    def test_no_puede_cambiarse_campos_de_administracion(self):
        otro_rol = Rol.objects.create(nombre='Todo', permisos=['eliminar_usuarios'])
        self.client.post(URL_EDITAR, {
            'first_name': 'Juan', 'pais': 'Argentina',
            # Campos que no están en el formulario: se ignoran
            'username': 'hacker', 'rol': otro_rol.pk, 'is_superuser': 'on', 'is_active': '',
            'puesto': 'Gerente', 'notas_internas': 'borrado', 'debe_cambiar_password': '',
        })
        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.username, 'juan')
        self.assertEqual(self.usuario.rol, self.rol)
        self.assertFalse(self.usuario.is_superuser)
        self.assertTrue(self.usuario.is_active)
        self.assertEqual(self.usuario.puesto, 'Vendedor')
        self.assertEqual(self.usuario.notas_internas, 'Llega tarde')

    def test_email_repetido(self):
        Usuario.objects.create_user('ana', 'ana@test.com', 'x')
        respuesta = self.client.post(URL_EDITAR, {'email': 'ANA@test.com', 'pais': 'Argentina'})
        self.assertContains(respuesta, 'Ya existe un usuario con ese email.')


class CambiarPasswordTests(TestCase):

    def setUp(self):
        self.usuario = Usuario.objects.create_user('juan', 'juan@test.com', CLAVE, first_name='Juan')
        self.client.post(reverse('usuarios:login'), {'username': 'juan', 'password': CLAVE})

    def cambiar(self, actual=CLAVE, nueva=NUEVA, repetir=None):
        return self.client.post(URL_PASSWORD, {
            'old_password': actual, 'new_password1': nueva, 'new_password2': repetir or nueva,
        })

    def test_cambiar_password(self):
        self.assertRedirects(self.cambiar(), URL_PERFIL)
        self.usuario.refresh_from_db()
        self.assertTrue(self.usuario.check_password(NUEVA))
        # Sigue con la sesión abierta
        self.assertEqual(self.client.get(URL_PERFIL).status_code, 200)

    def test_password_actual_incorrecta(self):
        self.assertContains(self.cambiar(actual='mala'), 'La contraseña actual no es correcta.')

    def test_nueva_igual_a_la_actual(self):
        self.assertContains(self.cambiar(nueva=CLAVE), 'tiene que ser distinta de la actual')

    def test_no_coinciden(self):
        self.assertContains(self.cambiar(repetir='Otra-cosa-distinta-1'), 'Las contraseñas no coinciden.')

    def test_debil(self):
        respuesta = self.cambiar(nueva='12345678')
        self.assertTrue(respuesta.context['form'].errors['new_password2'])

    def test_cierra_sesiones_en_otros_dispositivos(self):
        otro_dispositivo = Client()
        otro_dispositivo.post(reverse('usuarios:login'), {'username': 'juan', 'password': CLAVE})
        self.assertEqual(otro_dispositivo.get(URL_PERFIL).status_code, 200)
        self.cambiar()
        self.assertEqual(otro_dispositivo.get(URL_PERFIL).status_code, 302)  # quedó deslogueado


class CambioObligatorioTests(TestCase):

    def setUp(self):
        self.usuario = Usuario.objects.create_user('juan', None, CLAVE, debe_cambiar_password=True)
        self.client.post(reverse('usuarios:login'), {'username': 'juan', 'password': CLAVE})

    def test_redirige_a_cambiar_password_desde_cualquier_pagina(self):
        for url in (URL_INICIO, URL_PERFIL, reverse('usuarios:lista'), '/pagina-que-no-existe/'):
            self.assertRedirects(self.client.get(url), URL_PASSWORD, fetch_redirect_response=False)

    def test_pantalla_sin_menu(self):
        respuesta = self.client.get(URL_PASSWORD)
        self.assertContains(respuesta, 'Elegí una contraseña nueva')
        self.assertNotContains(respuesta, 'menu-principal')

    def test_puede_cerrar_sesion(self):
        self.assertRedirects(self.client.post(reverse('usuarios:logout')), reverse('usuarios:login'))

    def test_despues_de_cambiarla_usa_el_sistema(self):
        respuesta = self.client.post(URL_PASSWORD, {
            'old_password': CLAVE, 'new_password1': NUEVA, 'new_password2': NUEVA,
        })
        self.assertRedirects(respuesta, URL_INICIO)
        self.usuario.refresh_from_db()
        self.assertFalse(self.usuario.debe_cambiar_password)
        self.assertEqual(self.client.get(URL_PERFIL).status_code, 200)

    def test_asignada_por_admin_obliga_a_cambiarla(self):
        # Flujo completo: un admin le asigna una contraseña temporal
        admin_rol = Rol.objects.create(nombre='A', permisos=['ver_usuarios', 'restablecer_password_usuarios'])
        admin = Usuario.objects.create_user('admin', None, 'x', rol=admin_rol)
        empleado = Usuario.objects.create_user('empleado', None, CLAVE)
        cliente_admin = Client()
        cliente_admin.force_login(admin)
        cliente_admin.post(reverse('usuarios:restablecer_password', args=[empleado.pk]), {
            'password1': 'Temporal-segura-123', 'password2': 'Temporal-segura-123', 'obligar_cambio': 'on',
        })
        cliente_empleado = Client()
        cliente_empleado.post(reverse('usuarios:login'), {'username': 'empleado', 'password': 'Temporal-segura-123'})
        self.assertRedirects(cliente_empleado.get(URL_INICIO), URL_PASSWORD, fetch_redirect_response=False)
