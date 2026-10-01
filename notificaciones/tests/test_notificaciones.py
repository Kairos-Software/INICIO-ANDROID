from django.test import TestCase
from django.urls import reverse

from notificaciones.models import Nivel, Notificacion
from notificaciones.servicios import notificar, notificar_a_quienes_puedan
from usuarios.catalogo_permisos import CODIGOS_PERMISOS
from usuarios.models import Rol, Usuario


class ServiciosTests(TestCase):

    def setUp(self):
        self.ana = Usuario.objects.create_user('ana', None, 'x')
        self.juan = Usuario.objects.create_user('juan', None, 'x')

    def test_notificar_a_uno_y_a_varios(self):
        self.assertEqual(notificar(self.ana, 'Hola'), 1)
        self.assertEqual(notificar([self.ana, self.juan], 'Para los dos', excepto=self.juan), 1)
        self.assertEqual(self.ana.notificaciones.count(), 2)

    def test_no_notifica_inactivos(self):
        self.juan.is_active = False
        self.juan.save()
        self.assertEqual(notificar([self.ana, self.juan], 'Hola'), 1)

    def test_url_externa_se_descarta(self):
        notificar(self.ana, 'Hola', url='https://sitio-malicioso.com/')
        self.assertEqual(self.ana.notificaciones.get().url, '')

    def test_a_quienes_tengan_un_permiso(self):
        rol = Rol.objects.create(nombre='Ve usuarios', permisos=['ver_usuarios'])
        con_permiso = Usuario.objects.create_user('conpermiso', None, 'x', rol=rol)
        jefe = Usuario.objects.create_superuser('jefe', 'j@test.com', 'x')
        creadas = notificar_a_quienes_puedan('ver_usuarios', 'Algo nuevo', nivel=Nivel.AVISO)
        self.assertEqual(creadas, 2)
        self.assertTrue(con_permiso.notificaciones.exists())
        self.assertTrue(jefe.notificaciones.exists())
        self.assertFalse(self.ana.notificaciones.exists())


class PantallasTests(TestCase):

    def setUp(self):
        self.ana = Usuario.objects.create_user('ana', None, 'x')
        self.juan = Usuario.objects.create_user('juan', None, 'x')
        self.client.force_login(self.ana)

    def test_campanita_con_contador(self):
        notificar(self.ana, 'Primera')
        notificar(self.ana, 'Segunda')
        respuesta = self.client.get(reverse('core:inicio'))
        self.assertEqual(respuesta.context['notificaciones_no_leidas'], 2)
        self.assertContains(respuesta, 'Segunda')

    def test_abrir_marca_leida_y_redirige(self):
        notificar(self.ana, 'Mirá tu perfil', url=reverse('usuarios:perfil'))
        n = self.ana.notificaciones.get()
        self.assertRedirects(self.client.get(reverse('notificaciones:abrir', args=[n.pk])), reverse('usuarios:perfil'))
        n.refresh_from_db()
        self.assertTrue(n.leida)

    def test_no_puede_abrir_las_de_otro(self):
        notificar(self.juan, 'Privada')
        n = self.juan.notificaciones.get()
        self.assertEqual(self.client.get(reverse('notificaciones:abrir', args=[n.pk])).status_code, 404)

    def test_marcar_todas(self):
        notificar(self.ana, 'Una')
        notificar(self.ana, 'Otra')
        self.client.post(reverse('notificaciones:marcar_todas'))
        self.assertFalse(self.ana.notificaciones.filter(leida_en__isnull=True).exists())

    def test_lista_solo_no_leidas(self):
        notificar(self.ana, 'Leída')
        Notificacion.objects.update(leida_en='2026-01-01T00:00Z')
        notificar(self.ana, 'Nueva')
        respuesta = self.client.get(reverse('notificaciones:lista'), {'ver': 'no_leidas'})
        self.assertEqual([n.titulo for n in respuesta.context['pagina']], ['Nueva'])


class AvisosDeUsuariosTests(TestCase):
    """Los cambios de permisos y rol le avisan a la persona afectada."""

    def setUp(self):
        self.admin = Usuario.objects.create_user('admin', None, 'x',
                                                 rol=Rol.objects.create(nombre='Todo', permisos=sorted(CODIGOS_PERMISOS)))
        self.rol = Rol.objects.create(nombre='Ventas', permisos=['ver_usuarios'])
        self.empleado = Usuario.objects.create_user('empleado', None, 'x', rol=self.rol)
        self.dueno = Usuario.objects.create_superuser('dueno', 'd@test.com', 'x')

    def test_bienvenida_al_crear(self):
        self.client.force_login(self.admin)
        self.client.post(reverse('usuarios:crear'), {'username': 'nuevo', 'password1': 'a', 'password2': 'a', 'pais': 'Argentina'})
        self.assertTrue(Usuario.objects.get(username='nuevo').notificaciones.filter(titulo__icontains='bienvenida').exists())

    def test_aviso_al_cambiar_sus_permisos(self):
        self.client.force_login(self.admin)
        self.client.post(reverse('usuarios:permisos', args=[self.empleado.pk]), {'permisos': ['ver_usuarios', 'crear_usuarios']})
        self.assertTrue(self.empleado.notificaciones.filter(titulo='Cambiaron tus permisos').exists())

    def test_aviso_al_cambiar_permisos_de_su_rol(self):
        self.client.force_login(self.dueno)
        self.client.post(reverse('usuarios:roles_editar', args=[self.rol.pk]), {'nombre': 'Ventas', 'permisos': ['crear_usuarios']})
        self.assertTrue(self.empleado.notificaciones.filter(titulo__icontains='tu rol').exists())
