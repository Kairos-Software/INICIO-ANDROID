from datetime import timedelta

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from actividad.models import Accion, RegistroActividad
from api import tokens
from api.models import TokenAcceso
from notificaciones.servicios import notificar
from usuarios import servicios
from usuarios.catalogo_permisos import CODIGOS_PERMISOS
from usuarios.models import Rol, Usuario

URL_LOGIN = reverse('api_v1:login')
URL_LOGOUT = reverse('api_v1:logout')
URL_PERFIL = reverse('api_v1:perfil')
URL_CAMBIAR_PASSWORD = reverse('api_v1:cambiar_password')
URL_USUARIOS = reverse('api_v1:usuarios')
URL_OPCIONES = reverse('api_v1:usuarios_opciones')
URL_NOTIFICACIONES = reverse('api_v1:notificaciones')


def url_usuario(pk, nombre='usuario'):
    return reverse(f'api_v1:{nombre}', kwargs={'pk': pk})


class BaseApi(TestCase):

    def setUp(self):
        cache.clear()
        self.dueno = Usuario.objects.create_superuser('dueno', 'dueno@test.com', 'Clave-dueno-1')
        self.rol_admin = Rol.objects.create(nombre='Admin', permisos=sorted(CODIGOS_PERMISOS))
        self.rol_consulta = Rol.objects.create(nombre='Consulta', permisos=['ver_usuarios'])
        self.admin = Usuario.objects.create_user('admin', 'admin@test.com', 'Clave-admin-1', rol=self.rol_admin,
                                                 first_name='Ana')
        self.consulta = Usuario.objects.create_user('consulta', None, 'Clave-consulta-1', rol=self.rol_consulta)
        self.operador = Usuario.objects.create_user('operador', None, 'Clave-operador-1', first_name='Oscar',
                                                    telefono='111', notas_internas='Secreto')
        self.client = APIClient()

    def tearDown(self):
        cache.clear()

    def entrar(self, usuario, cliente=None):
        """Deja al cliente con el token de `usuario`. Devuelve la clave."""
        clave, _ = tokens.crear_token(usuario, 'Test')
        (cliente or self.client).credentials(HTTP_AUTHORIZATION=f'Bearer {clave}')
        return clave


# ══════════════════════════════════════════════════════════════════
#  LOGIN / LOGOUT / TOKENS
# ══════════════════════════════════════════════════════════════════

class LoginTests(BaseApi):

    def login(self, username, password, **extra):
        return self.client.post(URL_LOGIN, {'username': username, 'password': password, **extra})

    def test_login_correcto(self):
        respuesta = self.login('admin', 'Clave-admin-1', dispositivo='Samsung A54')
        self.assertEqual(respuesta.status_code, 200)
        datos = respuesta.json()
        self.assertEqual(datos['tipo'], 'Bearer')
        self.assertEqual(datos['usuario']['username'], 'admin')
        self.assertIn('crear_usuarios', datos['usuario']['permisos'])
        # En la base nunca queda el token, solo su huella
        token = TokenAcceso.objects.get(usuario=self.admin)
        self.assertNotEqual(token.clave_hash, datos['token'])
        self.assertEqual(token.dispositivo, 'Samsung A54')
        # Como en la web: último ingreso y registro de actividad
        self.admin.refresh_from_db()
        self.assertIsNotNone(self.admin.last_login)
        self.assertTrue(RegistroActividad.objects.filter(usuario=self.admin, accion=Accion.INGRESO).exists())

    def test_login_con_email(self):
        self.assertEqual(self.login('ADMIN@test.com', 'Clave-admin-1').status_code, 200)

    def test_password_incorrecta(self):
        respuesta = self.login('admin', 'mala')
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(respuesta.json()['codigo'], 'credenciales_invalidas')
        self.assertTrue(RegistroActividad.objects.filter(accion=Accion.INGRESO_FALLIDO).exists())

    def test_faltan_datos(self):
        respuesta = self.client.post(URL_LOGIN, {'password': 'x'})
        self.assertEqual(respuesta.json()['codigo'], 'datos_invalidos')
        self.assertIn('username', respuesta.json()['campos'])

    @override_settings(LOGIN_INTENTOS_MAXIMOS=2)
    def test_bloqueo_por_intentos(self):
        self.login('admin', 'mala')
        self.login('admin', 'mala')
        respuesta = self.login('admin', 'Clave-admin-1')
        self.assertEqual(respuesta.json()['codigo'], 'login_bloqueado')

    def test_usuario_inactivo(self):
        servicios.cambiar_estado(self.admin, False)
        self.assertEqual(self.login('admin', 'Clave-admin-1').json()['codigo'], 'credenciales_invalidas')

    @override_settings(MODO_MANTENIMIENTO=True)
    def test_mantenimiento_solo_superusuarios(self):
        respuesta = self.login('admin', 'Clave-admin-1')
        self.assertEqual(respuesta.status_code, 503)
        self.assertEqual(respuesta.json()['codigo'], 'mantenimiento')
        self.assertFalse(TokenAcceso.objects.exists())
        self.assertEqual(self.login('dueno', 'Clave-dueno-1').status_code, 200)


class TokenTests(BaseApi):

    def test_sin_token(self):
        respuesta = self.client.get(URL_PERFIL)
        self.assertEqual(respuesta.status_code, 401)
        self.assertEqual(respuesta.json()['codigo'], 'no_autenticado')
        self.assertEqual(respuesta['WWW-Authenticate'], 'Bearer')

    def test_token_inventado(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer inventado')
        self.assertEqual(self.client.get(URL_PERFIL).json()['codigo'], 'token_invalido')

    def test_encabezado_mal_armado(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer a b')
        self.assertEqual(self.client.get(URL_PERFIL).status_code, 401)

    def test_token_valido(self):
        self.entrar(self.admin)
        self.assertEqual(self.client.get(URL_PERFIL).json()['username'], 'admin')

    def test_logout_invalida_el_token(self):
        self.entrar(self.admin)
        self.assertEqual(self.client.post(URL_LOGOUT).status_code, 204)
        self.assertEqual(self.client.get(URL_PERFIL).status_code, 401)
        self.assertTrue(RegistroActividad.objects.filter(usuario=self.admin, accion=Accion.SALIDA).exists())

    def test_vencido(self):
        self.entrar(self.admin)
        TokenAcceso.objects.update(ultimo_uso=timezone.now() - timedelta(days=31))
        self.assertEqual(self.client.get(URL_PERFIL).status_code, 401)
        self.assertFalse(TokenAcceso.objects.exists())

    def test_el_uso_lo_renueva(self):
        self.entrar(self.admin)
        hace_rato = timezone.now() - timedelta(days=20)
        TokenAcceso.objects.update(ultimo_uso=hace_rato)
        self.client.get(URL_PERFIL)
        self.assertGreater(TokenAcceso.objects.get().ultimo_uso, hace_rato)

    def test_cambio_de_password_por_otro_lo_invalida(self):
        self.entrar(self.admin)
        servicios.restablecer_password(self.admin, 'Otra-clave-99', solicitante=self.dueno)
        self.assertEqual(self.client.get(URL_PERFIL).status_code, 401)

    def test_usuario_desactivado(self):
        self.entrar(self.admin)
        servicios.cambiar_estado(self.admin, False)
        self.assertEqual(self.client.get(URL_PERFIL).status_code, 401)

    def test_cambiar_mi_password_mantiene_este_token_y_cierra_los_otros(self):
        otro = APIClient()
        self.entrar(self.admin, otro)
        self.entrar(self.admin)
        respuesta = self.client.post(URL_CAMBIAR_PASSWORD, {
            'old_password': 'Clave-admin-1', 'new_password1': 'Nueva-clave-77', 'new_password2': 'Nueva-clave-77',
        })
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(self.client.get(URL_PERFIL).status_code, 200)
        self.assertEqual(otro.get(URL_PERFIL).status_code, 401)

    def test_borrar_vencidos(self):
        tokens.crear_token(self.admin)
        tokens.crear_token(self.consulta)
        TokenAcceso.objects.filter(usuario=self.admin).update(ultimo_uso=timezone.now() - timedelta(days=40))
        self.assertEqual(tokens.borrar_vencidos(), 1)
        self.assertEqual(TokenAcceso.objects.get().usuario, self.consulta)


# ══════════════════════════════════════════════════════════════════
#  PERFIL
# ══════════════════════════════════════════════════════════════════

class PerfilTests(BaseApi):

    def test_ver(self):
        self.entrar(self.operador)
        datos = self.client.get(URL_PERFIL).json()
        self.assertEqual(datos['nombre_completo'], 'Oscar')
        self.assertEqual(datos['descripcion_rol'], 'Personalizado')
        self.assertEqual(datos['permisos'], [])
        self.assertEqual(datos['permisos_por_modulo'], [])
        self.assertNotIn('notas_internas', datos)   # nunca lo ve el propio usuario

    def test_permisos_legibles(self):
        self.entrar(self.consulta)
        datos = self.client.get(URL_PERFIL).json()
        self.assertEqual(datos['permisos_por_modulo'],
                         [{'modulo': 'Usuarios', 'permisos': ['Ver la lista y el detalle de los usuarios']}])

    def test_opciones(self):
        self.entrar(self.operador)
        generos = self.client.get(reverse('api_v1:perfil_opciones')).json()['genero']
        self.assertIn({'valor': 'femenino', 'texto': 'Femenino'}, generos)

    def test_modificar_solo_lo_que_viene(self):
        self.entrar(self.operador)
        respuesta = self.client.patch(URL_PERFIL, {'telefono': '222', 'username': 'hackeado', 'rol': self.rol_admin.pk})
        self.assertEqual(respuesta.status_code, 200)
        self.operador.refresh_from_db()
        self.assertEqual(self.operador.telefono, '222')
        self.assertEqual(self.operador.first_name, 'Oscar')    # no vino: no se tocó
        self.assertEqual(self.operador.username, 'operador')   # no se puede cambiar desde el perfil
        self.assertIsNone(self.operador.rol)

    def test_error_de_validacion(self):
        self.entrar(self.operador)
        respuesta = self.client.patch(URL_PERFIL, {'email': 'admin@test.com'})
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(respuesta.json()['campos']['email'], ['Ya existe un usuario con ese email.'])

    def test_password_actual_incorrecta(self):
        self.entrar(self.operador)
        respuesta = self.client.post(URL_CAMBIAR_PASSWORD, {
            'old_password': 'mala', 'new_password1': 'Nueva-clave-77', 'new_password2': 'Nueva-clave-77',
        })
        self.assertIn('old_password', respuesta.json()['campos'])

    def test_debe_cambiar_password(self):
        servicios.restablecer_password(self.admin, 'Temporal-123', obligar_cambio=True)
        self.entrar(self.admin)
        respuesta = self.client.get(URL_USUARIOS)
        self.assertEqual(respuesta.status_code, 403)
        self.assertEqual(respuesta.json()['codigo'], 'debe_cambiar_password')
        self.assertEqual(self.client.get(URL_PERFIL).status_code, 200)   # su perfil sí
        self.client.post(URL_CAMBIAR_PASSWORD, {
            'old_password': 'Temporal-123', 'new_password1': 'Nueva-clave-77', 'new_password2': 'Nueva-clave-77',
        })
        self.assertEqual(self.client.get(URL_USUARIOS).status_code, 200)


# ══════════════════════════════════════════════════════════════════
#  USUARIOS
# ══════════════════════════════════════════════════════════════════

class UsuariosTests(BaseApi):

    def test_sin_permiso(self):
        self.entrar(self.operador)
        respuesta = self.client.get(URL_USUARIOS)
        self.assertEqual(respuesta.status_code, 403)
        self.assertEqual(respuesta.json()['codigo'], 'sin_permiso')
        # Ni siquiera se sabe si un usuario existe
        self.assertEqual(self.client.get(url_usuario(self.admin.pk)).status_code, 403)

    def test_lista_sin_superusuarios_ni_uno_mismo(self):
        self.entrar(self.admin)
        datos = self.client.get(URL_USUARIOS).json()
        self.assertEqual(datos['cantidad'], 2)
        self.assertEqual({u['username'] for u in datos['resultados']}, {'consulta', 'operador'})
        self.assertIn('paginas', datos)

    def test_lista_filtrada(self):
        self.entrar(self.admin)
        datos = self.client.get(URL_USUARIOS, {'q': 'osc'}).json()
        self.assertEqual([u['username'] for u in datos['resultados']], ['operador'])
        self.assertEqual(self.client.get(URL_USUARIOS, {'rol': 'cualquiera'}).status_code, 400)

    def test_detalle(self):
        self.entrar(self.consulta)
        datos = self.client.get(url_usuario(self.operador.pk)).json()
        self.assertEqual(datos['notas_internas'], 'Secreto')
        self.assertEqual(datos['acciones'], {'editar': False, 'restablecer_password': False, 'eliminar': False})
        self.assertEqual(self.client.get(url_usuario(self.dueno.pk)).status_code, 404)
        self.assertEqual(self.client.get(url_usuario(99999)).json()['codigo'], 'no_encontrado')

    def test_crear(self):
        self.entrar(self.admin)
        respuesta = self.client.post(URL_USUARIOS, {
            'username': 'nuevo', 'email': 'nuevo@test.com', 'rol': self.rol_consulta.pk,
            'first_name': 'Nora', 'password1': '1234', 'password2': '1234',
        })
        self.assertEqual(respuesta.status_code, 201)
        nuevo = Usuario.objects.get(username='nuevo')
        self.assertTrue(nuevo.check_password('1234'))
        self.assertTrue(nuevo.debe_cambiar_password)
        self.assertEqual(nuevo.creado_por, self.admin)
        self.assertTrue(RegistroActividad.objects.filter(accion=Accion.CREAR, objeto_id=str(nuevo.pk)).exists())

    def test_crear_con_errores(self):
        self.entrar(self.admin)
        respuesta = self.client.post(URL_USUARIOS, {'username': 'consulta', 'password1': 'a', 'password2': 'b'})
        campos = respuesta.json()['campos']
        self.assertIn('username', campos)
        self.assertIn('password2', campos)

    def test_no_puede_dar_un_rol_con_mas_permisos(self):
        supervisor = Rol.objects.create(nombre='Supervisor', permisos=['ver_usuarios', 'crear_usuarios'])
        jefe = Usuario.objects.create_user('jefe', None, 'x', rol=supervisor)
        self.entrar(jefe)
        respuesta = self.client.post(URL_USUARIOS, {
            'username': 'complice', 'rol': self.rol_admin.pk, 'password1': '1', 'password2': '1',
        })
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn('rol', respuesta.json()['campos'])
        self.assertFalse(Usuario.objects.filter(username='complice').exists())

    def test_modificar_solo_lo_que_viene(self):
        self.entrar(self.admin)
        respuesta = self.client.patch(url_usuario(self.operador.pk), {'puesto': 'Cajero'})
        self.assertEqual(respuesta.status_code, 200)
        self.operador.refresh_from_db()
        self.assertEqual(self.operador.puesto, 'Cajero')
        self.assertEqual(self.operador.first_name, 'Oscar')
        self.assertEqual(self.operador.notas_internas, 'Secreto')

    def test_eliminar(self):
        self.entrar(self.admin)
        self.assertEqual(self.client.delete(url_usuario(self.operador.pk)).status_code, 204)
        self.assertFalse(Usuario.objects.filter(pk=self.operador.pk).exists())

    def test_cambiar_estado(self):
        self.entrar(self.admin)
        url = url_usuario(self.operador.pk, 'usuario_estado')
        self.assertFalse(self.client.post(url, {'activo': False}).json()['activo'])
        self.assertEqual(self.client.post(url, {'activo': 'no'}).status_code, 400)

    def test_restablecer_password(self):
        self.entrar(self.admin)
        url = url_usuario(self.operador.pk, 'usuario_restablecer_password')
        respuesta = self.client.post(url, {'password1': 'Nueva-clave-77', 'password2': 'Nueva-clave-77'})
        self.assertEqual(respuesta.status_code, 200)
        self.operador.refresh_from_db()
        self.assertTrue(self.operador.check_password('Nueva-clave-77'))
        self.assertTrue(self.operador.debe_cambiar_password)

    def test_opciones(self):
        supervisor = Rol.objects.create(nombre='Supervisor', permisos=['ver_usuarios', 'crear_usuarios'])
        jefe = Usuario.objects.create_user('jefe', None, 'x', rol=supervisor)
        self.entrar(jefe)
        datos = self.client.get(URL_OPCIONES).json()
        puede = {r['nombre']: r['puede_asignar'] for r in datos['roles']}
        self.assertEqual(puede, {'Admin': False, 'Consulta': True, 'Supervisor': True})
        self.assertIn({'valor': 'dni', 'texto': 'DNI'}, datos['tipo_documento'])


# ══════════════════════════════════════════════════════════════════
#  NOTIFICACIONES
# ══════════════════════════════════════════════════════════════════

class NotificacionesTests(BaseApi):

    def test_solo_las_propias(self):
        notificar(self.operador, 'Para Oscar')
        notificar(self.admin, 'Para Ana')
        self.entrar(self.operador)
        datos = self.client.get(URL_NOTIFICACIONES).json()
        self.assertEqual([n['titulo'] for n in datos['resultados']], ['Para Oscar'])
        self.assertEqual(datos['no_leidas'], 1)

    def test_marcar_leidas(self):
        notificar(self.operador, 'Una')
        notificar(self.operador, 'Otra')
        ajena = notificar(self.admin, 'Ajena') and self.admin.notificaciones.get()
        self.entrar(self.operador)
        primera = self.operador.notificaciones.first()
        self.assertTrue(self.client.post(reverse('api_v1:notificacion_leida', args=[primera.pk])).json()['leida'])
        self.assertEqual(self.client.get(URL_NOTIFICACIONES, {'no_leidas': 1}).json()['cantidad'], 1)
        self.assertEqual(self.client.post(reverse('api_v1:notificacion_leida', args=[ajena.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse('api_v1:notificaciones_marcar_todas')).json()['marcadas'], 1)


# ══════════════════════════════════════════════════════════════════
#  GENERALES
# ══════════════════════════════════════════════════════════════════

class GeneralesTests(BaseApi):

    def test_endpoint_inexistente_responde_json(self):
        respuesta = self.client.get('/api/v1/no-existe/')
        self.assertEqual(respuesta.status_code, 404)
        self.assertEqual(respuesta.json()['codigo'], 'no_encontrado')

    def test_indice_publico(self):
        self.assertIn('login', self.client.get(reverse('api_v1:indice')).json()['endpoints'])

    def test_con_la_sesion_del_navegador(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(URL_PERFIL).json()['username'], 'admin')

    def test_mantenimiento(self):
        self.entrar(self.admin)
        with override_settings(MODO_MANTENIMIENTO=True):
            respuesta = self.client.get(URL_PERFIL)
            self.assertEqual(respuesta.status_code, 503)
            self.assertEqual(respuesta.json()['codigo'], 'mantenimiento')
            self.assertEqual(self.client.post(URL_LOGOUT).status_code, 204)   # salir siempre se puede
            self.entrar(self.dueno)
            self.assertEqual(self.client.get(URL_PERFIL).status_code, 200)

    def test_herramienta_cerrar_sesiones_incluye_la_app(self):
        from core.herramientas_dev import cerrar_todas_las_sesiones
        tokens.crear_token(self.admin)
        tokens.crear_token(self.dueno)
        cerrar_todas_las_sesiones(self.dueno, sesion_actual=None)
        self.assertEqual(list(TokenAcceso.objects.values_list('usuario__username', flat=True)), ['dueno'])
