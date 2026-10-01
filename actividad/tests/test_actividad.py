from django.test import TestCase
from django.urls import reverse

from actividad.models import Accion, RegistroActividad
from actividad.registro import registrar
from usuarios.catalogo_permisos import CODIGOS_PERMISOS
from usuarios.models import Rol, Usuario


class RegistroAutomaticoTests(TestCase):
    """Lo que ya existe en el sistema queda registrado solo."""

    def setUp(self):
        self.admin = Usuario.objects.create_user('admin', 'admin@test.com', 'Clave-admin-2026',
                                                 rol=Rol.objects.create(nombre='Todo', permisos=sorted(CODIGOS_PERMISOS)))
        self.empleado = Usuario.objects.create_user('empleado', None, 'x', first_name='Ana')

    def ultimo(self):
        return RegistroActividad.objects.order_by('-pk').first()

    def test_ingreso_salida_y_fallido(self):
        self.client.post(reverse('usuarios:login'), {'username': 'admin', 'password': 'mala'})
        fallido = self.ultimo()
        self.assertEqual(fallido.accion, Accion.INGRESO_FALLIDO)
        self.assertIn('admin', fallido.descripcion)
        self.assertNotIn('mala', str(fallido.__dict__))   # nunca la contraseña
        self.assertEqual(fallido.ip, '127.0.0.1')

        self.client.post(reverse('usuarios:login'), {'username': 'admin', 'password': 'Clave-admin-2026'})
        self.assertEqual(self.ultimo().accion, Accion.INGRESO)
        self.assertEqual(self.ultimo().usuario, self.admin)
        self.client.post(reverse('usuarios:logout'))
        self.assertEqual(self.ultimo().accion, Accion.SALIDA)

    def test_editar_usuario_guarda_los_cambios(self):
        rol = Rol.objects.create(nombre='Ventas')
        self.client.force_login(self.admin)
        self.client.post(reverse('usuarios:editar', args=[self.empleado.pk]), {
            'username': 'empleado', 'first_name': 'Ana María', 'rol': rol.pk, 'pais': 'Argentina',
        })
        registro = RegistroActividad.objects.get(accion=Accion.EDITAR)
        self.assertEqual(registro.usuario, self.admin)
        self.assertEqual(registro.objeto_id, str(self.empleado.pk))
        self.assertEqual(registro.cambios['Nombre/s'], ['Ana', 'Ana María'])
        self.assertEqual(registro.cambios['Rol'], ['', 'Ventas'])
        self.assertEqual(registro.ip, '127.0.0.1')

    def test_contrasenas_nunca_se_guardan(self):
        self.client.force_login(self.admin)
        self.client.post(reverse('usuarios:crear'), {
            'username': 'nuevo', 'password1': 'Secreta-123', 'password2': 'Secreta-123', 'pais': 'Argentina',
        })
        self.client.post(reverse('usuarios:restablecer_password', args=[self.empleado.pk]), {
            'password1': 'Otra-Secreta-456', 'password2': 'Otra-Secreta-456',
        })
        todo = str(list(RegistroActividad.objects.values()))
        self.assertNotIn('Secreta', todo)
        self.assertTrue(RegistroActividad.objects.filter(accion=Accion.SEGURIDAD, descripcion__icontains='contraseña').exists())

    def test_eliminar_usuario_conserva_el_nombre(self):
        self.client.force_login(self.admin)
        pk = self.empleado.pk
        self.client.post(reverse('usuarios:eliminar', args=[pk]))
        registro = RegistroActividad.objects.get(accion=Accion.ELIMINAR)
        self.assertEqual(registro.objeto_id, str(pk))
        self.assertEqual(registro.objeto_texto, 'empleado')

    def test_permisos_y_roles(self):
        self.client.force_login(self.admin)
        self.client.post(reverse('usuarios:permisos', args=[self.empleado.pk]), {'permisos': ['ver_usuarios']})
        registro = self.ultimo()
        self.assertEqual(registro.accion, Accion.SEGURIDAD)
        self.assertEqual(registro.cambios, {'Ver la lista y el detalle de los usuarios': ['No', 'Sí']})

    def test_el_registro_sobrevive_al_usuario_borrado(self):
        registrar(self.empleado, Accion.OTRO, 'Hizo algo')
        self.empleado.delete()
        registro = RegistroActividad.objects.get(descripcion='Hizo algo')
        self.assertIsNone(registro.usuario)
        self.assertEqual(registro.usuario_texto, 'empleado')


class PantallaActividadTests(TestCase):

    def setUp(self):
        self.dueno = Usuario.objects.create_superuser('dueno', 'd@test.com', 'x')
        self.empleado = Usuario.objects.create_user('empleado', None, 'x')
        registrar(self.empleado, Accion.CREAR, 'Creó el cliente Pérez', modulo='clientes')
        registrar(self.dueno, Accion.EDITAR, 'Editó el producto Yerba', modulo='productos')

    def test_requiere_permiso(self):
        self.client.force_login(self.empleado)
        self.assertEqual(self.client.get(reverse('actividad:lista')).status_code, 403)

    def test_lista_y_filtros(self):
        self.client.force_login(self.dueno)
        url = reverse('actividad:lista')
        self.assertContains(self.client.get(url), 'Creó el cliente Pérez')
        filtrado = self.client.get(url, {'modulo': 'productos'})
        self.assertContains(filtrado, 'Yerba')
        self.assertNotContains(filtrado, 'Pérez')
        por_texto = self.client.get(url, {'q': 'pérez'})
        self.assertEqual(len(por_texto.context['pagina']), 1)
        por_usuario = self.client.get(url, {'usuario': self.empleado.pk})
        self.assertNotContains(por_usuario, 'Yerba')

    def test_permiso_restringido(self):
        # ver_actividad solo lo puede dar un superusuario
        from usuarios.permisos import filtrar_otorgables
        rol = Rol.objects.create(nombre='Casi todo', permisos=sorted(CODIGOS_PERMISOS))
        jefe = Usuario.objects.create_user('jefe', None, 'x', rol=rol)
        self.assertNotIn('ver_actividad', filtrar_otorgables({'ver_actividad'}, jefe))
