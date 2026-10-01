import re
from datetime import timedelta
from unittest import mock

from django.core import mail
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse

from usuarios.models import CodigoRecuperacion, Usuario

URL_SOLICITAR = reverse('usuarios:recuperar')
URL_CODIGO = reverse('usuarios:recuperar_codigo')
URL_NUEVA = reverse('usuarios:recuperar_nueva')
URL_LOGIN = reverse('usuarios:login')
NUEVA = 'Recuperada-segura-2026'


def codigo_del_mail(indice=-1):
    return re.search(r'\b(\d{6})\b', mail.outbox[indice].body).group(1)


class RecuperacionTests(TestCase):

    def setUp(self):
        cache.clear()
        self.usuario = Usuario.objects.create_user('juan', 'juan@test.com', 'Vieja-clave-2026', first_name='Juan')

    def pedir(self, identificador='juan'):
        return self.client.post(URL_SOLICITAR, {'identificador': identificador})

    def test_link_en_el_login(self):
        self.assertContains(self.client.get(URL_LOGIN), URL_SOLICITAR)

    def test_flujo_completo(self):
        self.assertRedirects(self.pedir('JUAN@test.com'), URL_CODIGO)
        self.assertEqual(len(mail.outbox), 1)
        correo = mail.outbox[0]
        self.assertEqual(correo.to, ['juan@test.com'])
        codigo = codigo_del_mail()
        self.assertIn(codigo, correo.subject)
        self.assertIn(codigo, correo.alternatives[0][0])   # versión HTML

        self.assertRedirects(self.client.post(URL_CODIGO, {'codigo': codigo}), URL_NUEVA)
        respuesta = self.client.post(URL_NUEVA, {'new_password1': NUEVA, 'new_password2': NUEVA})
        self.assertRedirects(respuesta, URL_LOGIN)

        self.usuario.refresh_from_db()
        self.assertTrue(self.usuario.check_password(NUEVA))
        # Entra con la nueva
        self.assertRedirects(self.client.post(URL_LOGIN, {'username': 'juan', 'password': NUEVA}), reverse('core:inicio'))

    def test_el_codigo_se_guarda_cifrado(self):
        self.pedir()
        registro = CodigoRecuperacion.objects.get()
        self.assertNotIn(codigo_del_mail(), registro.codigo_hash)

    def test_no_revela_si_la_cuenta_existe(self):
        existente = self.pedir('juan')
        cache.clear()
        inexistente = self.client.post(URL_SOLICITAR, {'identificador': 'nadie'})
        self.assertRedirects(existente, URL_CODIGO)
        self.assertRedirects(inexistente, URL_CODIGO)
        self.assertEqual(len(mail.outbox), 1)   # solo al que existe
        # En la pantalla del código, cualquier código falla igual
        respuesta = self.client.post(URL_CODIGO, {'codigo': '123456'})
        self.assertContains(respuesta, 'El código es incorrecto o ya venció.')

    def test_inactivo_o_sin_email_no_recibe(self):
        self.usuario.is_active = False
        self.usuario.save()
        Usuario.objects.create_user('sinmail', None, 'x')
        self.assertRedirects(self.pedir('juan'), URL_CODIGO)
        cache.clear()
        self.pedir('sinmail')
        self.assertEqual(len(mail.outbox), 0)

    def test_codigo_incorrecto_y_maximo_de_intentos(self):
        self.pedir()
        codigo = codigo_del_mail()
        incorrecto = '000000' if codigo != '000000' else '111111'
        for _ in range(4):
            self.assertContains(self.client.post(URL_CODIGO, {'codigo': incorrecto}), 'incorrecto o ya venció')
        # Quinto intento: se corta y hay que pedir otro
        self.assertRedirects(self.client.post(URL_CODIGO, {'codigo': incorrecto}), URL_SOLICITAR)
        # Y el código correcto ya no sirve
        self.assertFalse(CodigoRecuperacion.objects.get().vigente)

    def test_codigo_vencido(self):
        self.pedir()
        CodigoRecuperacion.objects.update(creado=CodigoRecuperacion.objects.get().creado - timedelta(minutes=16))
        self.assertContains(self.client.post(URL_CODIGO, {'codigo': codigo_del_mail()}), 'incorrecto o ya venció')

    def test_solo_vale_el_ultimo_codigo(self):
        self.pedir()
        primero = codigo_del_mail()
        cache.clear()   # saltea la espera entre pedidos
        self.pedir()
        segundo = codigo_del_mail()
        if primero != segundo:
            self.assertContains(self.client.post(URL_CODIGO, {'codigo': primero}), 'incorrecto o ya venció')
        self.assertRedirects(self.client.post(URL_CODIGO, {'codigo': segundo}), URL_NUEVA)

    def test_espera_entre_pedidos_y_maximo_por_hora(self):
        self.pedir()
        self.assertContains(self.pedir(), 'Esperá 60 segundos')
        self.assertEqual(len(mail.outbox), 1)
        with mock.patch('usuarios.servicios.ESPERA_ENTRE_CODIGOS_SEGUNDOS', 0):
            cache.delete('recuperacion_espera:juan')
            for _ in range(4):
                cache.delete('recuperacion_espera:juan')
                self.pedir()
            cache.delete('recuperacion_espera:juan')
            self.assertContains(self.pedir(), 'Pediste demasiados códigos')
        self.assertEqual(len(mail.outbox), 5)

    def test_reenviar_codigo(self):
        self.pedir()
        cache.delete('recuperacion_espera:juan')
        self.client.post(URL_CODIGO, {'accion': 'reenviar'})
        self.assertEqual(len(mail.outbox), 2)
        self.assertRedirects(self.client.post(URL_CODIGO, {'codigo': codigo_del_mail()}), URL_NUEVA)

    def test_no_se_saltean_pasos(self):
        self.assertRedirects(self.client.get(URL_CODIGO), URL_SOLICITAR)
        self.assertRedirects(self.client.get(URL_NUEVA), URL_SOLICITAR)
        self.pedir()
        self.assertRedirects(self.client.get(URL_NUEVA), URL_SOLICITAR)   # sin verificar el código

    def test_tiempo_para_elegir_la_nueva(self):
        self.pedir()
        self.client.post(URL_CODIGO, {'codigo': codigo_del_mail()})
        sesion = self.client.session
        sesion['recuperacion']['verificado_en'] -= 11 * 60
        sesion.save()
        self.assertRedirects(self.client.get(URL_NUEVA), URL_SOLICITAR)

    def test_password_debil(self):
        self.pedir()
        self.client.post(URL_CODIGO, {'codigo': codigo_del_mail()})
        respuesta = self.client.post(URL_NUEVA, {'new_password1': '12345678', 'new_password2': '12345678'})
        self.assertEqual(respuesta.status_code, 200)
        self.usuario.refresh_from_db()
        self.assertTrue(self.usuario.check_password('Vieja-clave-2026'))

    def test_cierra_sesiones_abiertas_y_quita_cambio_obligatorio(self):
        self.usuario.debe_cambiar_password = True
        self.usuario.save()
        otro_dispositivo = Client()
        otro_dispositivo.force_login(self.usuario)

        self.pedir()
        self.client.post(URL_CODIGO, {'codigo': codigo_del_mail()})
        self.client.post(URL_NUEVA, {'new_password1': NUEVA, 'new_password2': NUEVA})

        self.assertEqual(otro_dispositivo.get(reverse('core:inicio')).status_code, 302)
        self.usuario.refresh_from_db()
        self.assertFalse(self.usuario.debe_cambiar_password)

    def test_levanta_el_bloqueo_de_login(self):
        with self.settings(LOGIN_INTENTOS_MAXIMOS=2):
            for _ in range(2):
                self.client.post(URL_LOGIN, {'username': 'juan', 'password': 'mala'})
            self.assertContains(self.client.post(URL_LOGIN, {'username': 'juan', 'password': 'x'}), 'Demasiados intentos')
            self.pedir()
            self.client.post(URL_CODIGO, {'codigo': codigo_del_mail()})
            self.client.post(URL_NUEVA, {'new_password1': NUEVA, 'new_password2': NUEVA})
            respuesta = self.client.post(URL_LOGIN, {'username': 'juan', 'password': NUEVA})
            self.assertRedirects(respuesta, reverse('core:inicio'))
