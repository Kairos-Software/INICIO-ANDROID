"""
Herramientas de desarrollador (capa Base). Solo para superusuarios.

Cada herramienta es una función que recibe al superusuario que la ejecuta
(y los datos que necesite) y devuelve un texto con el resultado. Todas
quedan en el registro de actividad.

A propósito NO dependen de roles ni permisos: son del dueño del sistema y no
se pueden delegar.
"""

import platform
import secrets
from pathlib import Path

import django
from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.core.cache import cache
from django.core.mail import send_mail
from django.db import connection, transaction
from django.db.models import ProtectedError, RestrictedError

from actividad.models import Accion, RegistroActividad
from actividad.registro import registrar
from notificaciones.models import Notificacion

FRASE_REINICIO = 'REINICIAR'
FRASE_BORRAR = 'BORRAR'
PREFIJO_DEMO = 'demo_'

# Apps internas de Django que el reinicio nunca toca
APPS_INTOCABLES = {'admin', 'auth', 'contenttypes', 'sessions', 'messages', 'staticfiles', 'humanize'}


class HerramientaError(Exception):
    """La herramienta no se pudo ejecutar. El mensaje es para el usuario."""


def _registrar(usuario, descripcion):
    registrar(usuario, Accion.SISTEMA, descripcion, modulo='herramientas')


# ══════════════════════════════════════════════════════════════════
#  ESTADO DEL SISTEMA (solo lectura)
# ══════════════════════════════════════════════════════════════════

def _tamanio_legible(bytes_):
    for unidad in ('B', 'KB', 'MB', 'GB'):
        if bytes_ < 1024:
            return f'{bytes_:.0f} {unidad}' if unidad == 'B' else f'{bytes_:.1f} {unidad}'
        bytes_ /= 1024
    return f'{bytes_:.1f} TB'


def estado_del_sistema():
    """Datos para mostrar arriba de la pantalla de herramientas."""
    from api.models import TokenAcceso
    from core.mantenimiento import estado_actual
    from usuarios.models import Rol

    Usuario = get_user_model()
    with connection.cursor() as cursor:
        cursor.execute('SELECT version(), pg_database_size(current_database())')
        version_db, tamanio_db = cursor.fetchone()

    media = Path(settings.MEDIA_ROOT)
    tamanio_media = sum(f.stat().st_size for f in media.rglob('*') if f.is_file()) if media.exists() else 0
    mailer = settings.MAILERS['default']['BACKEND'].rsplit('.', 2)[-2]

    return {
        'entorno': getattr(settings, 'DJANGO_ENV', ''),
        'debug': settings.DEBUG,
        'python': platform.python_version(),
        'django': django.get_version(),
        'base_de_datos': f"{settings.DATABASES['default']['NAME']} · {version_db.split(',')[0]}",
        'tamanio_db': _tamanio_legible(tamanio_db),
        'tamanio_media': _tamanio_legible(tamanio_media),
        'mail': 'Se envían de verdad (SMTP)' if mailer == 'smtp' else 'Se muestran en la terminal (no se envían)',
        'mantenimiento': estado_actual()['activo'],
        'conteos': [
            ('Usuarios', Usuario.objects.count()),
            ('Superusuarios', Usuario.objects.filter(is_superuser=True).count()),
            ('Roles', Rol.objects.count()),
            ('Registros de actividad', RegistroActividad.objects.count()),
            ('Notificaciones', Notificacion.objects.count()),
            ('Sesiones abiertas (web)', Session.objects.count()),
            ('Sesiones abiertas (app)', TokenAcceso.objects.count()),
        ],
    }


# ══════════════════════════════════════════════════════════════════
#  HERRAMIENTAS SIMPLES
# ══════════════════════════════════════════════════════════════════

def enviar_mail_prueba(usuario, destinatario):
    destinatario = (destinatario or '').strip() or usuario.email
    if not destinatario:
        raise HerramientaError('Escribí a qué email mandarlo (tu usuario no tiene email cargado).')
    try:
        send_mail(
            subject=f'Mail de prueba — {settings.NOMBRE_SISTEMA}',
            message='Si recibiste este mensaje, el envío de mails del sistema funciona.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[destinatario],
        )
    except Exception as error:  # noqa: BLE001 — se muestra el motivo al superusuario
        raise HerramientaError(f'No se pudo enviar: {error}')
    _registrar(usuario, f'Envió un mail de prueba a {destinatario}')
    return f'Mail de prueba enviado a {destinatario}.'


def cerrar_todas_las_sesiones(usuario, sesion_actual):
    """
    Todos tienen que volver a iniciar sesión, en la web y en la app. Quedan
    abiertas solo las de quien lo ejecuta (este navegador y sus apps).
    """
    from api.models import TokenAcceso

    cantidad, _ = Session.objects.exclude(session_key=sesion_actual).delete()
    cantidad_app, _ = TokenAcceso.objects.exclude(usuario=usuario).delete()
    _registrar(usuario, f'Cerró todas las sesiones abiertas ({cantidad} en la web, {cantidad_app} en la app)')
    return (f'Se cerraron {cantidad} sesión(es) en la web y {cantidad_app} en la app. '
            'Todos van a tener que volver a iniciar sesión.')


def limpiar_cache(usuario):
    """Borra la caché: desbloquea los logins bloqueados y los límites de recuperación de contraseña."""
    cache.clear()
    _registrar(usuario, 'Limpió la caché del sistema')
    return 'Caché limpia: se desbloquearon los ingresos bloqueados por intentos fallidos.'


def sincronizar_roles(usuario):
    from usuarios.servicios import sincronizar_roles_iniciales
    lineas = sincronizar_roles_iniciales()
    _registrar(usuario, 'Sincronizó los roles iniciales')
    return ' · '.join(lineas)


def borrar_actividad(usuario, confirmacion):
    _exigir_frase(confirmacion, FRASE_BORRAR)
    cantidad, _ = RegistroActividad.objects.all().delete()
    # Lo único que queda es el registro de que se borró
    _registrar(usuario, f'Borró todo el registro de actividad ({cantidad} registros)')
    return f'Se borraron {cantidad} registros de actividad.'


def borrar_notificaciones(usuario, confirmacion):
    _exigir_frase(confirmacion, FRASE_BORRAR)
    cantidad, _ = Notificacion.objects.all().delete()
    _registrar(usuario, f'Borró todas las notificaciones ({cantidad})')
    return f'Se borraron {cantidad} notificaciones.'


def _exigir_frase(escrita, esperada):
    if (escrita or '').strip() != esperada:
        raise HerramientaError(f'Para confirmar tenés que escribir {esperada} (en mayúsculas).')


# ══════════════════════════════════════════════════════════════════
#  DATOS DE DEMOSTRACIÓN
# ══════════════════════════════════════════════════════════════════

USUARIOS_DEMO = [
    # (usuario, nombre, apellido, rol, puesto)
    ('demo_lperez', 'Lucía', 'Pérez', 'Administrador', 'Gerenta general'),
    ('demo_jgomez', 'Julián', 'Gómez', 'Supervisor', 'Encargado de sucursal'),
    ('demo_mruiz', 'Martina', 'Ruiz', 'Consulta', 'Contadora'),
    ('demo_fdiaz', 'Facundo', 'Díaz', 'Operador', 'Vendedor'),
    ('demo_csosa', 'Camila', 'Sosa', None, 'Pasante'),
]


def cargar_demo(usuario):
    """Crea usuarios de ejemplo (demo_*) con una contraseña común, para probar o mostrar el sistema."""
    from usuarios.models import Rol
    from usuarios.servicios import sincronizar_roles_iniciales

    sincronizar_roles_iniciales()
    Usuario = get_user_model()
    roles = {r.nombre: r for r in Rol.objects.all()}
    password = f'Demo-{secrets.randbelow(9000) + 1000}'
    creados = 0
    for username, nombre, apellido, rol, puesto in USUARIOS_DEMO:
        if Usuario.objects.filter(username__iexact=username).exists():
            continue
        Usuario.objects.create_user(
            username, f'{username}@demo.local', password,
            first_name=nombre, last_name=apellido, rol=roles.get(rol), puesto=puesto,
            localidad='San Miguel', provincia='Buenos Aires',
        )
        creados += 1
    _registrar(usuario, f'Cargó {creados} usuario(s) de demostración')
    if not creados:
        return 'Los usuarios de demostración ya existían: no se creó ninguno.'
    return f'Se crearon {creados} usuarios de demostración (demo_*). Contraseña de todos: {password}'


def borrar_demo(usuario):
    Usuario = get_user_model()
    usuarios = Usuario.objects.filter(username__startswith=PREFIJO_DEMO, is_superuser=False)
    fotos = [u.foto.name for u in usuarios if u.foto]
    cantidad = usuarios.count()
    usuarios.delete()
    _borrar_archivos(fotos)
    _registrar(usuario, f'Borró {cantidad} usuario(s) de demostración')
    return f'Se borraron {cantidad} usuarios de demostración.'


def _borrar_archivos(nombres):
    from django.core.files.storage import default_storage
    for nombre in nombres:
        default_storage.delete(nombre)


# ══════════════════════════════════════════════════════════════════
#  BORRAR EL CONTENIDO: canales, películas y series (no toca usuarios ni créditos)
# ══════════════════════════════════════════════════════════════════

# Qué se puede borrar: el valor del formulario -> (Canal.contenido o None = todo, nombre legible)
QUE_BORRAR = {
    'todo': (None, 'todo el contenido'),
    'vivo': ('vivo', 'los canales en vivo'),
    'pelicula': ('pelicula', 'las películas'),
    'serie': ('serie', 'las series'),
}


def resumen_contenido():
    """Cuánto hay de cada cosa: {'vivo': 243, 'pelicula': 1065, 'serie': 5954, 'importaciones': 4}."""
    from django.db.models import Count

    from canales.models import Canal, Importacion
    cantidades = dict(Canal._base_manager.values_list('contenido').annotate(n=Count('pk')))
    return {
        'vivo': cantidades.get('vivo', 0),
        'pelicula': cantidades.get('pelicula', 0),
        'serie': cantidades.get('serie', 0),
        'importaciones': Importacion.objects.count(),
    }


def borrar_contenido(usuario, que, confirmacion, password):
    """
    Borra de verdad (no a la papelera) los canales en vivo, las películas, las
    series o todo, con sus fuentes. Con "todo", también las importaciones
    (el historial de listas subidas) y las categorías. Con una parte, las
    categorías que quedan vacías. Usuarios, clientes, créditos y la app no se
    tocan. Pide escribir BORRAR y la contraseña. No se puede deshacer.
    """
    from canales.models import Canal, Categoria, Importacion

    if que not in QUE_BORRAR:
        raise HerramientaError('Elegí qué contenido borrar.')
    _exigir_frase(confirmacion, FRASE_BORRAR)
    if not usuario.check_password(password or ''):
        raise HerramientaError('La contraseña no es correcta.')

    contenido, nombre = QUE_BORRAR[que]
    with transaction.atomic():
        canales = Canal._base_manager.all()
        if contenido:
            canales = canales.filter(contenido=contenido)
        cantidad = canales.count()
        canales.delete()   # las fuentes se borran con su canal
        if contenido is None:
            Importacion.objects.all().delete()
            Categoria._base_manager.all().delete()
        else:
            Categoria._base_manager.filter(canales__isnull=True).delete()
    cache.clear()
    _registrar(usuario, f'Borró {nombre} ({cantidad} en total)')
    return f'Se borró {nombre}: {cantidad}.'


# ══════════════════════════════════════════════════════════════════
#  REINICIAR EL SISTEMA: borra todo menos los superusuarios
# ══════════════════════════════════════════════════════════════════

def _modelos_a_vaciar():
    """Todos los modelos de las apps del proyecto (no los internos de Django), salvo el de usuarios."""
    Usuario = get_user_model()
    base = Path(settings.BASE_DIR).resolve()
    modelos = []
    for app in apps.get_app_configs():
        if app.label in APPS_INTOCABLES or not Path(app.path).resolve().is_relative_to(base):
            continue
        for modelo in app.get_models():
            if modelo is not Usuario and not modelo._meta.proxy and modelo._meta.managed:
                modelos.append(modelo)
    return modelos


def resumen_reinicio():
    """Qué se borraría: [(nombre legible, cantidad), ...] (solo lo que tiene datos)."""
    Usuario = get_user_model()
    resumen = [('Usuarios (no superusuarios)', Usuario.objects.filter(is_superuser=False).count())]
    for modelo in _modelos_a_vaciar():
        resumen.append((str(modelo._meta.verbose_name_plural).capitalize(), modelo._base_manager.count()))
    return [(nombre, cantidad) for nombre, cantidad in resumen if cantidad]


def reiniciar_sistema(usuario, confirmacion, password):
    """
    Borra TODOS los datos del sistema menos los superusuarios. Pide escribir
    REINICIAR y la contraseña de quien lo ejecuta. No se puede deshacer.
    """
    _exigir_frase(confirmacion, FRASE_REINICIO)
    if not usuario.check_password(password or ''):
        raise HerramientaError('La contraseña no es correcta.')

    Usuario = get_user_model()
    fotos = [u.foto.name for u in Usuario.objects.filter(is_superuser=False) if u.foto]

    with transaction.atomic():
        Usuario.objects.filter(is_superuser=False).delete()
        pendientes = _modelos_a_vaciar()
        # Se repite mientras haya avances: algunas tablas solo se pueden
        # vaciar después de otras (relaciones protegidas).
        while pendientes:
            no_se_pudo = []
            for modelo in pendientes:
                try:
                    with transaction.atomic():
                        modelo._base_manager.all().delete()
                except (ProtectedError, RestrictedError):
                    no_se_pudo.append(modelo)
            if len(no_se_pudo) == len(pendientes):
                nombres = ', '.join(m._meta.label for m in no_se_pudo)
                raise HerramientaError(f'No se pudieron vaciar: {nombres}. No se borró nada.')
            pendientes = no_se_pudo

    _borrar_archivos(fotos)
    cache.clear()
    # Las sesiones de los usuarios borrados quedan inválidas solas
    from usuarios.servicios import sincronizar_roles_iniciales
    sincronizar_roles_iniciales()
    _registrar(usuario, 'Reinició el sistema: borró todos los datos menos los superusuarios')
    return 'Sistema reiniciado: quedaron solo los superusuarios y los roles iniciales.'
