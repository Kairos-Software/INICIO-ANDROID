import io
import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from usuarios.catalogo_permisos import CODIGOS_PERMISOS
from usuarios.models import Rol, Usuario

MEDIA_TEMPORAL = tempfile.mkdtemp()


def imagen_png(nombre='foto.png'):
    buffer = io.BytesIO()
    Image.new('RGB', (10, 10), 'orange').save(buffer, 'PNG')
    return SimpleUploadedFile(nombre, buffer.getvalue(), content_type='image/png')


def datos_alta(**extra):
    datos = {
        'username': 'nuevo',
        'email': 'nuevo@test.com',
        'first_name': 'Nuevo',
        'last_name': 'Usuario',
        'pais': 'Argentina',
        'password1': 'Clave-muy-segura-2026',
        'password2': 'Clave-muy-segura-2026',
        'debe_cambiar_password': 'on',
    }
    datos.update(extra)
    return datos


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class BaseGestion(TestCase):

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_TEMPORAL, ignore_errors=True)

    def setUp(self):
        self.rol_admin = Rol.objects.create(nombre='Admin', permisos=sorted(CODIGOS_PERMISOS))
        self.rol_supervisor = Rol.objects.create(
            nombre='Supervisor',
            permisos=['ver_usuarios', 'crear_usuarios', 'editar_usuarios', 'restablecer_password_usuarios'],
        )
        self.rol_consulta = Rol.objects.create(nombre='Consulta', permisos=['ver_usuarios'])

        self.jefe = Usuario.objects.create_user('jefe', 'jefe@test.com', 'x', rol=self.rol_admin)
        self.supervisor = Usuario.objects.create_user('super', None, 'x', rol=self.rol_supervisor)
        self.consulta = Usuario.objects.create_user('consulta', None, 'x', rol=self.rol_consulta)
        self.empleado = Usuario.objects.create_user('empleado', 'empleado@test.com', 'x', first_name='Ana')
        self.dueno = Usuario.objects.create_superuser('dueno', 'dueno@test.com', 'x')


class ListaTests(BaseGestion):

    def test_sin_permiso_403(self):
        self.client.force_login(self.empleado)
        self.assertEqual(self.client.get(reverse('usuarios:lista')).status_code, 403)

    def test_lista_excluye_superusuarios_y_a_uno_mismo(self):
        self.client.force_login(self.consulta)
        usuarios = list(self.client.get(reverse('usuarios:lista')).context['pagina'])
        self.assertIn(self.empleado, usuarios)
        self.assertNotIn(self.dueno, usuarios)
        self.assertNotIn(self.consulta, usuarios)

    def test_busqueda_y_filtros(self):
        self.client.force_login(self.jefe)
        url = reverse('usuarios:lista')
        self.assertEqual(list(self.client.get(url, {'q': 'ana'}).context['pagina']), [self.empleado])
        sin_rol = list(self.client.get(url, {'rol': 'sin_rol'}).context['pagina'])
        self.assertEqual(sin_rol, [self.empleado])
        self.empleado.is_active = False
        self.empleado.save()
        inactivos = list(self.client.get(url, {'estado': 'inactivos'}).context['pagina'])
        self.assertEqual(inactivos, [self.empleado])

    def test_consulta_no_ve_boton_nuevo(self):
        self.client.force_login(self.consulta)
        self.assertNotContains(self.client.get(reverse('usuarios:lista')), 'Nuevo usuario')


class CrearTests(BaseGestion):

    def test_crear_usuario(self):
        self.client.force_login(self.supervisor)
        respuesta = self.client.post(reverse('usuarios:crear'), datos_alta(rol=self.rol_consulta.pk))
        nuevo = Usuario.objects.get(username='nuevo')
        self.assertRedirects(respuesta, reverse('usuarios:detalle', args=[nuevo.pk]))
        self.assertTrue(nuevo.check_password('Clave-muy-segura-2026'))
        self.assertTrue(nuevo.debe_cambiar_password)
        self.assertEqual(nuevo.creado_por, self.supervisor)
        self.assertEqual(nuevo.rol, self.rol_consulta)

    def test_consulta_no_puede_crear(self):
        self.client.force_login(self.consulta)
        self.assertEqual(self.client.get(reverse('usuarios:crear')).status_code, 403)

    def test_no_puede_asignar_rol_con_mas_permisos(self):
        self.client.force_login(self.supervisor)
        respuesta = self.client.post(reverse('usuarios:crear'), datos_alta(rol=self.rol_admin.pk))
        self.assertContains(respuesta, 'incluye permisos que vos no tenés')
        self.assertFalse(Usuario.objects.filter(username='nuevo').exists())

    def test_passwords_distintas(self):
        self.client.force_login(self.jefe)
        respuesta = self.client.post(reverse('usuarios:crear'), datos_alta(password2='otra-cosa-123'))
        self.assertContains(respuesta, 'Las contraseñas no coinciden.')

    def test_password_inicial_puede_ser_cualquiera(self):
        # Un solo carácter, o igual al nombre de usuario: se acepta
        self.client.force_login(self.jefe)
        for usuario, clave in (('uno', '1'), ('pepe', 'pepe')):
            self.client.post(reverse('usuarios:crear'), datos_alta(username=usuario, email='', password1=clave, password2=clave))
            self.assertTrue(Usuario.objects.get(username=usuario).check_password(clave))

    def test_sin_rol_lleva_a_elegir_permisos(self):
        self.client.force_login(self.jefe)
        respuesta = self.client.post(reverse('usuarios:crear'), datos_alta())
        nuevo = Usuario.objects.get(username='nuevo')
        self.assertIsNone(nuevo.rol)
        self.assertRedirects(respuesta, reverse('usuarios:permisos', args=[nuevo.pk]))

    def test_sin_rol_y_sin_permiso_para_gestionarlos_va_al_detalle(self):
        # El supervisor no tiene 'gestionar_permisos': no lo puede llevar ahí
        self.client.force_login(self.supervisor)
        respuesta = self.client.post(reverse('usuarios:crear'), datos_alta())
        nuevo = Usuario.objects.get(username='nuevo')
        self.assertRedirects(respuesta, reverse('usuarios:detalle', args=[nuevo.pk]))

    def test_username_y_email_repetidos_sin_mayusculas(self):
        self.client.force_login(self.jefe)
        respuesta = self.client.post(reverse('usuarios:crear'), datos_alta(username='EMPLEADO', email='EMPLEADO@test.com'))
        errores = respuesta.context['form'].errors
        self.assertIn('Ya existe un usuario con ese nombre de usuario.', str(errores))
        self.assertIn('Ya existe un usuario con ese email.', str(errores))

    def test_crear_con_foto(self):
        self.client.force_login(self.jefe)
        self.client.post(reverse('usuarios:crear'), datos_alta(foto=imagen_png()))
        nuevo = Usuario.objects.get(username='nuevo')
        self.assertTrue(nuevo.foto.name.startswith('usuarios/fotos/'))


class DetalleYEdicionTests(BaseGestion):

    def test_detalle(self):
        self.client.force_login(self.consulta)
        respuesta = self.client.get(reverse('usuarios:detalle', args=[self.empleado.pk]))
        self.assertContains(respuesta, 'empleado@test.com')
        self.assertNotContains(respuesta, 'Editar')

    def test_no_se_puede_ver_ni_editar_superusuario(self):
        self.client.force_login(self.jefe)
        for nombre in ('detalle', 'editar', 'restablecer_password', 'eliminar'):
            url = reverse(f'usuarios:{nombre}', args=[self.dueno.pk])
            self.assertEqual(self.client.get(url).status_code, 404, nombre)

    def test_no_se_puede_gestionar_a_si_mismo(self):
        self.client.force_login(self.jefe)
        self.assertEqual(self.client.get(reverse('usuarios:editar', args=[self.jefe.pk])).status_code, 404)

    def test_editar(self):
        self.client.force_login(self.supervisor)
        url = reverse('usuarios:editar', args=[self.empleado.pk])
        respuesta = self.client.post(url, {
            'username': 'empleado', 'email': 'nuevo-mail@test.com', 'first_name': 'Ana María',
            'pais': 'Argentina', 'fecha_nacimiento': '1990-05-20',
        })
        self.assertRedirects(respuesta, reverse('usuarios:detalle', args=[self.empleado.pk]))
        self.empleado.refresh_from_db()
        self.assertEqual(self.empleado.first_name, 'Ana María')
        self.assertEqual(str(self.empleado.fecha_nacimiento), '1990-05-20')

    def test_quitar_el_rol_lleva_a_elegir_permisos(self):
        con_rol = Usuario.objects.create_user('conrol', None, 'x', rol=self.rol_consulta)
        self.client.force_login(self.jefe)
        respuesta = self.client.post(reverse('usuarios:editar', args=[con_rol.pk]), {
            'username': 'conrol', 'rol': '', 'pais': 'Argentina',
        })
        self.assertRedirects(respuesta, reverse('usuarios:permisos', args=[con_rol.pk]))
        self.assertContains(self.client.get(reverse('usuarios:detalle', args=[con_rol.pk])), 'Personalizado')

    def test_editar_no_puede_subir_rol(self):
        self.client.force_login(self.supervisor)
        url = reverse('usuarios:editar', args=[self.empleado.pk])
        respuesta = self.client.post(url, {'username': 'empleado', 'rol': self.rol_admin.pk, 'pais': 'Argentina'})
        self.assertContains(respuesta, 'incluye permisos que vos no tenés')
        self.empleado.refresh_from_db()
        self.assertIsNone(self.empleado.rol)

    def test_editar_mantener_rol_alto_se_permite(self):
        # El supervisor puede editar otros datos de alguien con rol más alto sin cambiárselo
        otro_admin = Usuario.objects.create_user('otroadmin', None, 'x', rol=self.rol_admin)
        self.client.force_login(self.supervisor)
        url = reverse('usuarios:editar', args=[otro_admin.pk])
        respuesta = self.client.post(url, {
            'username': 'otroadmin', 'rol': self.rol_admin.pk, 'pais': 'Argentina', 'puesto': 'Gerente',
        })
        self.assertEqual(respuesta.status_code, 302)
        otro_admin.refresh_from_db()
        self.assertEqual(otro_admin.puesto, 'Gerente')

    def test_reemplazar_y_quitar_foto(self):
        self.client.force_login(self.jefe)
        url = reverse('usuarios:editar', args=[self.empleado.pk])
        base = {'username': 'empleado', 'pais': 'Argentina'}
        self.client.post(url, {**base, 'foto': imagen_png('a.png')})
        self.empleado.refresh_from_db()
        primera = self.empleado.foto.name
        self.client.post(url, {**base, 'foto': imagen_png('b.png')})
        self.empleado.refresh_from_db()
        self.assertNotEqual(self.empleado.foto.name, primera)
        self.assertFalse(self.empleado.foto.storage.exists(primera))  # se borró la vieja
        segunda = self.empleado.foto.name
        self.client.post(url, {**base, 'quitar_foto': 'on'})
        self.empleado.refresh_from_db()
        self.assertFalse(self.empleado.foto)
        self.assertFalse(self.empleado.foto.storage.exists(segunda))


class AccionesTests(BaseGestion):

    def test_desactivar_y_activar(self):
        self.client.force_login(self.supervisor)
        url = reverse('usuarios:cambiar_estado', args=[self.empleado.pk])
        self.client.post(url)
        self.empleado.refresh_from_db()
        self.assertFalse(self.empleado.is_active)
        self.client.post(url)
        self.empleado.refresh_from_db()
        self.assertTrue(self.empleado.is_active)

    def test_cambiar_estado_solo_por_post(self):
        self.client.force_login(self.jefe)
        self.assertEqual(self.client.get(reverse('usuarios:cambiar_estado', args=[self.empleado.pk])).status_code, 405)

    def test_restablecer_password(self):
        self.client.force_login(self.supervisor)
        url = reverse('usuarios:restablecer_password', args=[self.empleado.pk])
        self.client.post(url, {
            'password1': 'Otra-clave-segura-99', 'password2': 'Otra-clave-segura-99', 'obligar_cambio': 'on',
        })
        self.empleado.refresh_from_db()
        self.assertTrue(self.empleado.check_password('Otra-clave-segura-99'))
        self.assertTrue(self.empleado.debe_cambiar_password)

    def test_eliminar_requiere_permiso(self):
        self.client.force_login(self.supervisor)
        self.assertEqual(self.client.post(reverse('usuarios:eliminar', args=[self.empleado.pk])).status_code, 403)

    def test_eliminar(self):
        self.client.force_login(self.jefe)
        url = reverse('usuarios:eliminar', args=[self.empleado.pk])
        self.assertContains(self.client.get(url), 'No se puede deshacer')
        self.assertRedirects(self.client.post(url), reverse('usuarios:lista'))
        self.assertFalse(Usuario.objects.filter(pk=self.empleado.pk).exists())
