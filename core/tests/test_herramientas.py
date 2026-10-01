from django.contrib.sessions.models import Session
from django.core import mail
from django.core.cache import cache
from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse

from actividad.models import RegistroActividad
from actividad.registro import registrar
from core.models import EstadoMantenimiento
from notificaciones.models import Notificacion
from notificaciones.servicios import notificar
from usuarios.catalogo_permisos import CODIGOS_PERMISOS
from usuarios.models import PermisoIndividual, Rol, Usuario

URL = reverse('core:herramientas')


class HerramientasTests(TestCase):

    def setUp(self):
        cache.clear()
        self.dueno = Usuario.objects.create_superuser('dueno', 'dueno@test.com', 'Clave-dueno-1')
        self.rol = Rol.objects.create(nombre='Todo', permisos=sorted(CODIGOS_PERMISOS))
        self.admin = Usuario.objects.create_user('admin', None, 'x', rol=self.rol)
        self.client.force_login(self.dueno)

    def usar(self, herramienta, **datos):
        return self.client.post(URL, {'herramienta': herramienta, **datos}, follow=True)

    def test_solo_superusuarios(self):
        # Ni siquiera alguien con todos los permisos
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(URL).status_code, 403)
        self.assertEqual(self.client.post(URL, {'herramienta': 'limpiar_cache'}).status_code, 403)

    def test_pantalla_con_estado(self):
        respuesta = self.client.get(URL)
        self.assertContains(respuesta, 'Estado del sistema')
        self.assertContains(respuesta, 'Reiniciar el sistema')

    def test_herramienta_desconocida(self):
        self.assertContains(self.usar('borrar_disco'), 'Herramienta desconocida')

    def test_mail_de_prueba(self):
        self.assertContains(self.usar('mail_prueba', destinatario='otro@test.com'), 'enviado a otro@test.com')
        self.assertEqual(mail.outbox[0].to, ['otro@test.com'])
        self.usar('mail_prueba')   # sin destinatario: al email propio
        self.assertEqual(mail.outbox[1].to, ['dueno@test.com'])

    def test_cerrar_sesiones_menos_la_propia(self):
        otro = Client()
        otro.force_login(self.admin)
        self.usar('cerrar_sesiones')
        self.assertEqual(Session.objects.count(), 1)
        self.assertEqual(self.client.get(URL).status_code, 200)          # sigo adentro
        self.assertEqual(otro.get(reverse('core:inicio')).status_code, 302)  # el otro no

    def test_limpiar_cache(self):
        cache.set('login_fallidos:admin:127.0.0.1', 99)
        self.usar('limpiar_cache')
        self.assertIsNone(cache.get('login_fallidos:admin:127.0.0.1'))

    def test_sincronizar_roles_suma_permisos_nuevos_al_administrador(self):
        call_command('crear_roles_iniciales', stdout=open('nul' if __import__('os').name == 'nt' else '/dev/null', 'w'))
        administrador = Rol.objects.get(nombre='Administrador')
        administrador.set_permisos(['ver_usuarios'])   # como si faltaran los nuevos
        administrador.save()
        supervisor = Rol.objects.get(nombre='Supervisor')
        supervisor.set_permisos([])
        supervisor.save()
        self.usar('sincronizar_roles')
        self.assertEqual(Rol.objects.get(nombre='Administrador').get_permisos(), set(CODIGOS_PERMISOS))
        self.assertEqual(Rol.objects.get(nombre='Supervisor').get_permisos(), set())   # no se pisa

    def test_cargar_y_borrar_demo(self):
        respuesta = self.usar('cargar_demo')
        self.assertContains(respuesta, 'Contraseña de todos')
        self.assertEqual(Usuario.objects.filter(username__startswith='demo_').count(), 5)
        self.assertContains(self.usar('cargar_demo'), 'ya existían')
        self.usar('borrar_demo')
        self.assertFalse(Usuario.objects.filter(username__startswith='demo_').exists())

    def test_borrar_actividad_pide_confirmacion(self):
        registrar(self.dueno, 'otro', 'Algo viejo')
        self.assertContains(self.usar('borrar_actividad', confirmacion='borrar'), 'tenés que escribir BORRAR')
        self.assertTrue(RegistroActividad.objects.filter(descripcion='Algo viejo').exists())
        self.usar('borrar_actividad', confirmacion='BORRAR')
        self.assertFalse(RegistroActividad.objects.filter(descripcion='Algo viejo').exists())
        # Queda solo el registro de que se borró
        self.assertEqual(RegistroActividad.objects.count(), 1)

    def test_borrar_notificaciones(self):
        notificar([self.dueno, self.admin], 'Hola')
        self.usar('borrar_notificaciones', confirmacion='BORRAR')
        self.assertFalse(Notificacion.objects.exists())

    def test_cada_herramienta_queda_registrada(self):
        self.usar('limpiar_cache')
        self.assertTrue(RegistroActividad.objects.filter(modulo='herramientas', usuario=self.dueno).exists())


class ReiniciarSistemaTests(TestCase):

    def setUp(self):
        cache.clear()
        self.dueno = Usuario.objects.create_superuser('dueno', 'dueno@test.com', 'Clave-dueno-1')
        self.otro_dueno = Usuario.objects.create_superuser('socio', 'socio@test.com', 'x')
        rol = Rol.objects.create(nombre='Rol viejo', permisos=['ver_usuarios'])
        self.empleado = Usuario.objects.create_user('empleado', None, 'x', rol=rol)
        PermisoIndividual.objects.create(usuario=self.empleado, permiso='crear_usuarios', concedido=True)
        notificar(self.dueno, 'Hola')
        EstadoMantenimiento.obtener()
        self.client.force_login(self.dueno)

    def reiniciar(self, confirmacion='REINICIAR', password='Clave-dueno-1'):
        return self.client.post(URL, {'herramienta': 'reiniciar', 'confirmacion': confirmacion, 'password': password},
                                follow=True)

    def test_muestra_que_se_borraria(self):
        respuesta = self.client.get(URL)
        self.assertContains(respuesta, 'Usuarios (no superusuarios)')

    def test_frase_incorrecta_no_borra_nada(self):
        self.assertContains(self.reiniciar(confirmacion='reiniciar'), 'tenés que escribir REINICIAR')
        self.assertTrue(Usuario.objects.filter(username='empleado').exists())

    def test_password_incorrecta_no_borra_nada(self):
        self.assertContains(self.reiniciar(password='mala'), 'La contraseña no es correcta')
        self.assertTrue(Usuario.objects.filter(username='empleado').exists())

    def test_reinicio(self):
        self.assertContains(self.reiniciar(), 'Sistema reiniciado')
        # Quedan los superusuarios, con su contraseña
        self.assertEqual(set(Usuario.objects.values_list('username', flat=True)), {'dueno', 'socio'})
        self.assertTrue(Usuario.objects.get(username='dueno').check_password('Clave-dueno-1'))
        # Se borró todo lo demás
        self.assertFalse(Rol.objects.filter(nombre='Rol viejo').exists())
        self.assertFalse(PermisoIndividual.objects.exists())
        self.assertFalse(Notificacion.objects.exists())
        # Se recrearon los roles iniciales y quedó registrado quién lo hizo
        self.assertTrue(Rol.objects.filter(nombre='Administrador').exists())
        self.assertEqual(RegistroActividad.objects.get().usuario, self.dueno)
        # Y sigo con la sesión abierta
        self.assertEqual(self.client.get(URL).status_code, 200)
