from django.test import TestCase
from django.urls import reverse

from usuarios.catalogo_permisos import CODIGOS_PERMISOS
from usuarios.models import PermisoIndividual, Rol, Usuario
from usuarios.permisos import chequear_permiso


class BaseRoles(TestCase):

    def setUp(self):
        self.dueno = Usuario.objects.create_superuser('dueno', 'dueno@test.com', 'x')
        # Gestor: puede ver/editar roles (se los dio el superusuario) y gestionar permisos,
        # pero no tiene 'eliminar_usuarios'
        self.rol_gestor = Rol.objects.create(nombre='Gestor', permisos=[
            'ver_usuarios', 'editar_usuarios', 'gestionar_permisos',
            'ver_roles', 'crear_roles', 'editar_roles',
        ])
        self.gestor = Usuario.objects.create_user('gestor', None, 'x', rol=self.rol_gestor)
        self.rol_ventas = Rol.objects.create(nombre='Ventas', permisos=['ver_usuarios', 'eliminar_usuarios'])
        self.empleado = Usuario.objects.create_user('empleado', None, 'x', rol=self.rol_ventas)


class RolesVistasTests(BaseRoles):

    def test_lista_requiere_permiso(self):
        self.client.force_login(self.empleado)
        self.assertEqual(self.client.get(reverse('usuarios:roles_lista')).status_code, 403)

    def test_lista_muestra_roles_y_uso(self):
        self.client.force_login(self.gestor)
        respuesta = self.client.get(reverse('usuarios:roles_lista'))
        self.assertContains(respuesta, 'Ventas')
        self.assertContains(respuesta, '1 usuario')

    def test_superusuario_crea_rol(self):
        self.client.force_login(self.dueno)
        respuesta = self.client.post(reverse('usuarios:roles_crear'), {
            'nombre': 'Cajero', 'descripcion': 'Atiende la caja',
            'permisos': ['ver_usuarios', 'ver_roles', 'codigo_inventado'],
        })
        self.assertRedirects(respuesta, reverse('usuarios:roles_lista'))
        rol = Rol.objects.get(nombre='Cajero')
        # El superusuario puede dar restringidos; los códigos inventados se descartan
        self.assertEqual(rol.get_permisos(), {'ver_usuarios', 'ver_roles'})

    def test_no_crea_rol_con_permisos_que_no_tiene_ni_restringidos(self):
        self.client.force_login(self.gestor)
        self.client.post(reverse('usuarios:roles_crear'), {
            'nombre': 'Trampa', 'permisos': ['ver_usuarios', 'eliminar_usuarios', 'ver_roles'],
        })
        # eliminar_usuarios: el gestor no lo tiene. ver_roles: restringido.
        self.assertEqual(Rol.objects.get(nombre='Trampa').get_permisos(), {'ver_usuarios'})

    def test_nombre_repetido(self):
        self.client.force_login(self.dueno)
        respuesta = self.client.post(reverse('usuarios:roles_crear'), {'nombre': 'Ventas'})
        self.assertContains(respuesta, 'Ya existe un rol con ese nombre.')

    def test_editar_no_toca_lo_que_no_puede_otorgar(self):
        # El gestor edita "Ventas": puede quitar ver_usuarios, pero eliminar_usuarios
        # (que no tiene) queda como estaba aunque no venga en el formulario
        self.client.force_login(self.gestor)
        self.client.post(reverse('usuarios:roles_editar', args=[self.rol_ventas.pk]), {
            'nombre': 'Ventas', 'permisos': ['editar_usuarios'],
        })
        self.rol_ventas.refresh_from_db()
        self.assertEqual(self.rol_ventas.get_permisos(), {'editar_usuarios', 'eliminar_usuarios'})

    def test_cambio_de_rol_impacta_en_sus_usuarios(self):
        self.client.force_login(self.dueno)
        self.client.post(reverse('usuarios:roles_editar', args=[self.rol_ventas.pk]), {
            'nombre': 'Ventas', 'permisos': ['ver_roles'],
        })
        empleado = Usuario.objects.get(pk=self.empleado.pk)
        self.assertTrue(chequear_permiso(empleado, 'ver_roles'))
        self.assertFalse(chequear_permiso(empleado, 'eliminar_usuarios'))

    def test_solo_ver_roles_es_solo_lectura(self):
        rol = Rol.objects.create(nombre='Lector', permisos=['ver_roles'])
        lector = Usuario.objects.create_user('lector', None, 'x', rol=rol)
        self.client.force_login(lector)
        url = reverse('usuarios:roles_editar', args=[self.rol_ventas.pk])
        respuesta = self.client.get(url)
        self.assertContains(respuesta, '<fieldset disabled>', html=False)
        self.assertNotContains(respuesta, 'Guardar cambios')
        self.client.post(url, {'nombre': 'Hackeado', 'permisos': []})
        self.rol_ventas.refresh_from_db()
        self.assertEqual(self.rol_ventas.nombre, 'Ventas')

    def test_eliminar_rol_deja_usuarios_sin_rol(self):
        self.client.force_login(self.dueno)
        url = reverse('usuarios:roles_eliminar', args=[self.rol_ventas.pk])
        self.assertContains(self.client.get(url), 'empleado')
        self.assertRedirects(self.client.post(url), reverse('usuarios:roles_lista'))
        self.empleado.refresh_from_db()
        self.assertIsNone(self.empleado.rol)

    def test_eliminar_rol_requiere_permiso(self):
        self.client.force_login(self.gestor)
        self.assertEqual(self.client.post(reverse('usuarios:roles_eliminar', args=[self.rol_ventas.pk])).status_code, 403)


class PermisosIndividualesTests(BaseRoles):

    def url(self, usuario):
        return reverse('usuarios:permisos', args=[usuario.pk])

    def test_requiere_permiso(self):
        self.client.force_login(self.empleado)
        self.assertEqual(self.client.get(self.url(self.gestor)).status_code, 403)

    def test_pantalla_muestra_origen(self):
        PermisoIndividual.objects.create(usuario=self.empleado, permiso='editar_usuarios', concedido=True)
        self.client.force_login(self.gestor)
        respuesta = self.client.get(self.url(self.empleado))
        self.assertContains(respuesta, 'Por su rol')
        self.assertContains(respuesta, 'Agregado a este usuario')
        self.assertContains(respuesta, 'No lo podés cambiar porque vos no lo tenés')
        self.assertContains(respuesta, 'Solo lo puede cambiar un superusuario')

    def test_guardar_crea_y_borra_excepciones(self):
        self.client.force_login(self.gestor)
        # Quita ver_usuarios (lo da el rol) y agrega editar_usuarios (no lo da el rol)
        self.client.post(self.url(self.empleado), {'permisos': ['editar_usuarios']})
        excepciones = dict(self.empleado.permisos_individuales.values_list('permiso', 'concedido'))
        self.assertEqual(excepciones, {'ver_usuarios': False, 'editar_usuarios': True})

        # Volver a marcar lo mismo que el rol borra las excepciones
        self.client.post(self.url(self.empleado), {'permisos': ['ver_usuarios']})
        self.assertFalse(self.empleado.permisos_individuales.exists())

    def test_no_puede_tocar_lo_que_no_tiene(self):
        # El empleado tiene eliminar_usuarios por rol; el gestor no lo tiene:
        # aunque no lo mande marcado, no se le quita
        self.client.force_login(self.gestor)
        self.client.post(self.url(self.empleado), {'permisos': ['ver_usuarios']})
        empleado = Usuario.objects.get(pk=self.empleado.pk)
        self.assertTrue(chequear_permiso(empleado, 'eliminar_usuarios'))
        # Y tampoco puede dar restringidos
        self.client.post(self.url(self.empleado), {'permisos': ['ver_usuarios', 'ver_roles']})
        self.assertFalse(chequear_permiso(Usuario.objects.get(pk=self.empleado.pk), 'ver_roles'))

    def test_personalizado_sin_etiquetas_de_origen(self):
        sin_rol = Usuario.objects.create_user('sinrol', None, 'x')
        PermisoIndividual.objects.create(usuario=sin_rol, permiso='ver_usuarios', concedido=True)
        self.client.force_login(self.gestor)
        respuesta = self.client.get(self.url(sin_rol))
        self.assertContains(respuesta, 'permisos personalizados')
        self.assertNotContains(respuesta, 'Agregado a este usuario')
        self.assertNotContains(respuesta, 'Volver a los permisos del rol')
        # Guardar le da exactamente lo marcado
        self.client.post(self.url(sin_rol), {'permisos': ['ver_usuarios', 'editar_usuarios']})
        sin_rol = Usuario.objects.get(pk=sin_rol.pk)
        self.assertTrue(chequear_permiso(sin_rol, 'editar_usuarios'))
        self.assertFalse(chequear_permiso(sin_rol, 'crear_usuarios'))

    def test_volver_al_rol(self):
        PermisoIndividual.objects.create(usuario=self.empleado, permiso='editar_usuarios', concedido=True)
        self.client.force_login(self.gestor)
        self.client.post(self.url(self.empleado), {'accion': 'volver_al_rol'})
        self.assertFalse(self.empleado.permisos_individuales.exists())

    def test_no_se_gestionan_superusuarios_ni_a_si_mismo(self):
        self.client.force_login(self.gestor)
        self.assertEqual(self.client.get(self.url(self.dueno)).status_code, 404)
        self.assertEqual(self.client.post(self.url(self.gestor), {'permisos': list(CODIGOS_PERMISOS)}).status_code, 404)
