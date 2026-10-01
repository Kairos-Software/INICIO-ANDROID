"""
Lo que el sistema HACE con los usuarios (capa Base).
Las vistas HTML de hoy y una API futura llaman a estas mismas funciones.

Cuando una operación no se puede hacer por una regla del negocio, se lanza
`OperacionNoPermitida` con un mensaje listo para mostrar al usuario.
"""

import secrets

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.core.cache import cache
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import ProtectedError, Q, RestrictedError
from django.template.loader import render_to_string
from django.urls import reverse

from actividad.models import Accion
from actividad.registro import cambios_de_formulario, registrar
from notificaciones.models import Nivel
from notificaciones.servicios import notificar

from .catalogo_permisos import CODIGOS_PERMISOS, DESCRIPCION_PERMISO
from .models import (
    INTENTOS_MAXIMOS_CODIGO_RECUPERACION, VIGENCIA_CODIGO_RECUPERACION,
    CodigoRecuperacion, PermisoIndividual, Usuario,
)
from .permisos import filtrar_otorgables, limpiar_cache_permisos, permisos_efectivos, puede_otorgar_rol


class OperacionNoPermitida(Exception):
    """Una regla del negocio impide hacer la operación. El mensaje es para el usuario."""


# ══════════════════════════════════════════════════════════════════
#  ALTA, EDICIÓN, BAJA
# ══════════════════════════════════════════════════════════════════

def validar_asignacion_rol(rol_anterior_id, rol_nuevo, solicitante):
    """
    Solo se puede asignar un rol si quien lo asigna tiene todos sus
    permisos. Sin esta regla, alguien con 'editar_usuarios' podría darle a
    otro (o a un cómplice) un rol con más permisos que los propios.
    Dejar el mismo rol que ya tenía, o quitarlo, siempre se permite.

    `rol_anterior_id` es el rol que tenía ANTES de este cambio (None en un
    alta). Se pasa aparte porque el formulario ya le cargó el rol nuevo al
    objeto en memoria.
    """
    if rol_nuevo is None or rol_nuevo.pk == rol_anterior_id:
        return
    if not puede_otorgar_rol(rol_nuevo, solicitante):
        raise OperacionNoPermitida(
            f'No podés asignar el rol "{rol_nuevo}": incluye permisos que vos no tenés.'
        )


@transaction.atomic
def crear_usuario(form, solicitante):
    """Crea un usuario a partir de un UsuarioCrearForm ya validado."""
    usuario = form.save(commit=False)
    validar_asignacion_rol(None, usuario.rol, solicitante)
    usuario.set_password(form.cleaned_data['password1'])
    usuario.creado_por = solicitante
    usuario.save()
    registrar(solicitante, Accion.CREAR, f'Creó el usuario {usuario} ({usuario.descripcion_rol})', objeto=usuario)
    notificar(usuario, f'Te damos la bienvenida a {settings.NOMBRE_SISTEMA}',
              'Revisá tus datos en Mi perfil y completá lo que falte.', url=reverse('usuarios:perfil'))
    return usuario


@transaction.atomic
def actualizar_usuario(form, solicitante):
    """Guarda los cambios de un UsuarioEditarForm ya validado."""
    usuario = form.instance
    # form.initial tiene los valores de antes de editar
    validar_asignacion_rol(form.initial.get('rol'), usuario.rol, solicitante)

    rol_anterior_id = form.initial.get('rol')
    cambios = cambios_de_formulario(form)
    usuario = _guardar_con_foto(form)
    limpiar_cache_permisos(usuario)
    if cambios:
        registrar(solicitante, Accion.EDITAR, f'Editó el usuario {usuario}', objeto=usuario, cambios=cambios)
    if usuario.rol_id != rol_anterior_id:
        notificar(usuario, 'Cambió tu rol en el sistema', f'Ahora tu rol es: {usuario.descripcion_rol}.',
                  url=reverse('usuarios:perfil'), nivel=Nivel.AVISO)
    return usuario


def _guardar_con_foto(form):
    """Guarda el formulario y, si se cambió o se quitó la foto, borra el archivo viejo."""
    foto_anterior = form.initial.get('foto')
    nombre_foto_anterior = foto_anterior.name if foto_anterior else ''
    usuario = form.save()
    if nombre_foto_anterior and nombre_foto_anterior != usuario.foto.name:
        usuario.foto.storage.delete(nombre_foto_anterior)
    return usuario


def actualizar_perfil(form):
    """El propio usuario guarda sus datos (PerfilForm ya validado)."""
    cambios = cambios_de_formulario(form)
    usuario = _guardar_con_foto(form)
    if cambios:
        registrar(usuario, Accion.EDITAR, 'Editó sus datos personales', objeto=usuario, cambios=cambios)
    return usuario


def cambiar_password_propia(usuario, password_nueva):
    """
    El usuario cambia su propia contraseña. Se quita la marca de "debe
    cambiarla". Las sesiones abiertas en otros dispositivos se cierran solas
    (Django las invalida al cambiar la contraseña); la vista mantiene la actual.
    """
    usuario.set_password(password_nueva)
    usuario.debe_cambiar_password = False
    usuario.save(update_fields=['password', 'debe_cambiar_password', 'modificado'])
    registrar(usuario, Accion.SEGURIDAD, 'Cambió su contraseña', objeto=usuario)
    return usuario


def cambiar_estado(usuario, activo, solicitante=None):
    """Activa o desactiva un usuario. Un usuario inactivo no puede iniciar sesión."""
    usuario.is_active = activo
    usuario.save(update_fields=['is_active', 'modificado'])
    limpiar_cache_permisos(usuario)
    verbo = 'Activó' if activo else 'Desactivó'
    antes, despues = ('No', 'Sí') if activo else ('Sí', 'No')
    registrar(solicitante, Accion.EDITAR, f'{verbo} al usuario {usuario}', objeto=usuario,
              cambios={'Activo': [antes, despues]})
    return usuario


def eliminar_usuario(usuario, solicitante=None):
    """
    Elimina el usuario definitivamente. Si otros datos del sistema dependen
    de él (ej: ventas que registró), no se puede: conviene desactivarlo.
    """
    foto = usuario.foto
    descripcion = f'Eliminó el usuario {usuario} ({usuario.get_full_name()})'
    objeto_id, objeto_texto = usuario.pk, str(usuario)
    try:
        usuario.delete()
    except (ProtectedError, RestrictedError):
        raise OperacionNoPermitida(
            'No se puede eliminar: tiene información asociada en el sistema. '
            'Desactivalo para que no pueda ingresar.'
        )
    if foto:
        foto.storage.delete(foto.name)
    registro = registrar(solicitante, Accion.ELIMINAR, descripcion, modulo='usuarios')
    if registro:
        # El usuario ya no existe: se guardan su id y nombre como texto
        registro.objeto_tipo = 'usuarios.Usuario'
        registro.objeto_id = str(objeto_id)
        registro.objeto_texto = objeto_texto
        registro.save(update_fields=['objeto_tipo', 'objeto_id', 'objeto_texto'])


def restablecer_password(usuario, password, obligar_cambio=True, solicitante=None):
    """
    Un administrador le asigna una contraseña nueva a otro usuario.
    Por defecto se le pide cambiarla en el próximo ingreso.
    """
    usuario.set_password(password)
    usuario.debe_cambiar_password = obligar_cambio
    usuario.save(update_fields=['password', 'debe_cambiar_password', 'modificado'])
    registrar(solicitante, Accion.SEGURIDAD, f'Le asignó una contraseña nueva a {usuario}', objeto=usuario)
    return usuario


# ══════════════════════════════════════════════════════════════════
#  ROLES
# ══════════════════════════════════════════════════════════════════

def combinar_permisos(actuales, enviados, solicitante):
    """
    Calcula los permisos finales de un rol cuando `solicitante` lo edita.

    - Los que `solicitante` puede otorgar: quedan como los marcó.
    - Los que NO puede otorgar: quedan como estaban (ni los agrega ni los
      quita). Así nadie le saca a un rol un permiso que no le corresponde
      manejar, ni se lo agrega.
    """
    otorgables = filtrar_otorgables(CODIGOS_PERMISOS, solicitante)
    enviados = set(enviados) & CODIGOS_PERMISOS
    return (set(actuales) - otorgables) | (enviados & otorgables)


@transaction.atomic
def guardar_rol(form, permisos_enviados, solicitante):
    """Crea o actualiza un rol desde un RolForm ya validado."""
    rol_es_nuevo = form.instance.pk is None
    cambios = {} if rol_es_nuevo else cambios_de_formulario(form)
    rol = form.save(commit=False)
    # Permisos que tenía antes de editar (se leen de la base: el formulario no los trae)
    actuales = type(rol).objects.get(pk=rol.pk).get_permisos() if rol.pk else set()
    rol.set_permisos(combinar_permisos(actuales, permisos_enviados, solicitante))
    rol.save()
    cambios.update(_cambios_de_permisos(actuales, rol.get_permisos()))
    if rol_es_nuevo:
        registrar(solicitante, Accion.CREAR, f'Creó el rol {rol}', objeto=rol, cambios=cambios)
    elif cambios:
        registrar(solicitante, Accion.SEGURIDAD, f'Editó el rol {rol}', objeto=rol, cambios=cambios)
        if actuales != rol.get_permisos():
            notificar(rol.usuarios.all(), f'Cambiaron los permisos de tu rol "{rol}"',
                      'En Mi perfil podés ver lo que podés hacer ahora.',
                      url=reverse('usuarios:perfil'), nivel=Nivel.AVISO, excepto=solicitante)
    return rol


def _cambios_de_permisos(antes, despues):
    """{descripción del permiso: [antes, después]} solo de los que cambiaron."""
    cambios = {}
    for codigo in sorted(set(antes) ^ set(despues)):
        tenia, tiene = codigo in antes, codigo in despues
        cambios[DESCRIPCION_PERMISO.get(codigo, codigo)] = ['Sí' if tenia else 'No', 'Sí' if tiene else 'No']
    return cambios


def sincronizar_roles_iniciales():
    """
    Crea los roles de ROLES_INICIALES que falten. A los que tienen '*' (todos
    los permisos) les suma los permisos nuevos del catálogo; nunca les quita.
    Devuelve una lista de líneas describiendo lo que hizo.
    """
    from .catalogo_permisos import ROLES_INICIALES
    from .models import Rol

    lineas = []
    for datos in ROLES_INICIALES:
        todos = datos['permisos'] == '*'
        permisos = set(CODIGOS_PERMISOS) if todos else set(datos['permisos'])
        rol, creado = Rol.objects.get_or_create(nombre=datos['nombre'], defaults={'descripcion': datos['descripcion']})
        if creado:
            rol.set_permisos(permisos)
            rol.save()
            lineas.append(f'Creado: {rol.nombre}')
        elif todos and not permisos <= rol.get_permisos():
            nuevos = permisos - rol.get_permisos()
            rol.set_permisos(rol.get_permisos() | nuevos)
            rol.save()
            lineas.append(f'Actualizado: {rol.nombre} (+{len(nuevos)} permiso(s) nuevo(s): {", ".join(sorted(nuevos))})')
        else:
            lineas.append(f'Sin cambios: {rol.nombre}')
    return lineas


def eliminar_rol(rol, solicitante=None):
    """
    Elimina el rol. Sus usuarios quedan sin rol, es decir con permisos
    personalizados: conservan solo los individuales que tengan.
    """
    cantidad = rol.usuarios.count()
    registrar(solicitante, Accion.ELIMINAR,
              f'Eliminó el rol {rol} ({cantidad} usuario(s) pasaron a permisos personalizados)', objeto=rol)
    rol.delete()
    return cantidad


# ══════════════════════════════════════════════════════════════════
#  PERMISOS INDIVIDUALES
# ══════════════════════════════════════════════════════════════════

@transaction.atomic
def guardar_permisos_individuales(usuario, concedidos, solicitante):
    """
    `concedidos` = códigos que tienen que quedar concedidos para `usuario`
    (los que el administrador dejó marcados).

    Para cada permiso que `solicitante` puede otorgar:
      - si coincide con lo que da el rol -> se borra la excepción (manda el rol)
      - si difiere                       -> se guarda la excepción
    Los permisos que `solicitante` no puede otorgar no se tocan.
    """
    if usuario.is_superuser:
        raise OperacionNoPermitida('Un superusuario tiene todos los permisos: no se pueden modificar.')

    concedidos = set(concedidos)
    permisos_rol = usuario.rol.get_permisos() if usuario.rol_id else set()
    limpiar_cache_permisos(usuario)
    antes = set(permisos_efectivos(usuario))

    for codigo in filtrar_otorgables(CODIGOS_PERMISOS, solicitante):
        quiere = codigo in concedidos
        if quiere == (codigo in permisos_rol):
            PermisoIndividual.objects.filter(usuario=usuario, permiso=codigo).delete()
        else:
            PermisoIndividual.objects.update_or_create(
                usuario=usuario, permiso=codigo, defaults={'concedido': quiere},
            )
    limpiar_cache_permisos(usuario)
    _registrar_cambio_permisos(usuario, antes, solicitante)


def _registrar_cambio_permisos(usuario, antes, solicitante):
    despues = set(permisos_efectivos(usuario))
    cambios = _cambios_de_permisos(antes, despues)
    if cambios:
        registrar(solicitante, Accion.SEGURIDAD, f'Cambió los permisos de {usuario}', objeto=usuario, cambios=cambios)
        notificar(usuario, 'Cambiaron tus permisos', 'En Mi perfil podés ver lo que podés hacer ahora.',
                  url=reverse('usuarios:perfil'), nivel=Nivel.AVISO)
    return cambios


def quitar_permisos_individuales(usuario, solicitante):
    """Vuelve a los permisos del rol: borra las excepciones que `solicitante` puede manejar."""
    codigos = filtrar_otorgables(CODIGOS_PERMISOS, solicitante)
    limpiar_cache_permisos(usuario)
    antes = set(permisos_efectivos(usuario))
    usuario.permisos_individuales.filter(permiso__in=codigos).delete()
    limpiar_cache_permisos(usuario)
    _registrar_cambio_permisos(usuario, antes, solicitante)


# ══════════════════════════════════════════════════════════════════
#  RECUPERACIÓN DE CONTRASEÑA (código de 6 dígitos por mail)
# ══════════════════════════════════════════════════════════════════

ESPERA_ENTRE_CODIGOS_SEGUNDOS = 60
CODIGOS_MAXIMOS_POR_HORA = 5


def _clave_pedidos(identificador):
    return f'recuperacion_pedidos:{(identificador or "").strip().lower()}'


def _clave_espera(identificador):
    return f'recuperacion_espera:{(identificador or "").strip().lower()}'


def buscar_usuario_para_recuperar(identificador):
    """Usuario activo con email cargado, por nombre de usuario o email. None si no hay."""
    identificador = (identificador or '').strip()
    if not identificador:
        return None
    return (
        Usuario.objects
        .filter(Q(username__iexact=identificador) | Q(email__iexact=identificador))
        .filter(is_active=True, email__isnull=False)
        .exclude(email='')
        .order_by('pk')
        .first()
    )


def solicitar_codigo_recuperacion(identificador):
    """
    Genera y manda por mail un código para `identificador` (usuario o email).
    Devuelve el usuario, o None si no existe / está inactivo / no tiene email.

    Importante: quien llama NO debe mostrar si se encontró o no el usuario
    (así nadie puede averiguar qué cuentas existen). Los límites de pedidos
    se aplican por lo que se escribió, exista o no, por el mismo motivo.
    """
    if cache.get(_clave_espera(identificador)):
        raise OperacionNoPermitida(
            f'Esperá {ESPERA_ENTRE_CODIGOS_SEGUNDOS} segundos antes de pedir otro código.'
        )
    pedidos = cache.get(_clave_pedidos(identificador), 0)
    if pedidos >= CODIGOS_MAXIMOS_POR_HORA:
        raise OperacionNoPermitida('Pediste demasiados códigos. Probá de nuevo en una hora.')

    cache.set(_clave_espera(identificador), True, timeout=ESPERA_ENTRE_CODIGOS_SEGUNDOS)
    cache.set(_clave_pedidos(identificador), pedidos + 1, timeout=60 * 60)

    usuario = buscar_usuario_para_recuperar(identificador)
    if usuario is None:
        return None

    # Solo vale el último código pedido
    usuario.codigos_recuperacion.filter(usado=False).update(usado=True)
    codigo = f'{secrets.randbelow(1_000_000):06d}'
    CodigoRecuperacion.objects.create(usuario=usuario, codigo_hash=make_password(codigo))
    enviar_mail_codigo(usuario, codigo)
    return usuario


def enviar_mail_codigo(usuario, codigo):
    contexto = {
        'usuario': usuario,
        'codigo': codigo,
        'minutos': int(VIGENCIA_CODIGO_RECUPERACION.total_seconds() // 60),
        'NOMBRE_SISTEMA': settings.NOMBRE_SISTEMA,
        'NOMBRE_EMPRESA': settings.NOMBRE_EMPRESA,
    }
    send_mail(
        subject=f'{codigo} es tu código para recuperar la contraseña — {settings.NOMBRE_SISTEMA}',
        message=render_to_string('usuarios/emails/recuperar_password.txt', contexto),
        html_message=render_to_string('usuarios/emails/recuperar_password.html', contexto),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[usuario.email],
    )


def verificar_codigo_recuperacion(usuario_id, codigo):
    """
    True si `codigo` es el último código vigente del usuario. Cada intento
    fallido suma; al llegar al máximo, el código deja de servir.
    """
    if not usuario_id:
        return False
    registro = (
        CodigoRecuperacion.objects
        .filter(usuario_id=usuario_id, usado=False)
        .order_by('-creado')
        .first()
    )
    if registro is None or not registro.vigente:
        return False

    if check_password((codigo or '').strip(), registro.codigo_hash):
        registro.usado = True
        registro.save(update_fields=['usado'])
        return True

    registro.intentos += 1
    if registro.intentos >= INTENTOS_MAXIMOS_CODIGO_RECUPERACION:
        registro.usado = True
    registro.save(update_fields=['intentos', 'usado'])
    return False


def establecer_password_recuperada(usuario, password, ip=''):
    """
    Guarda la contraseña nueva después de verificar el código. Cierra todas
    las sesiones abiertas (Django las invalida al cambiar la contraseña) y
    levanta el bloqueo de login por intentos fallidos.
    """
    usuario.set_password(password)
    usuario.debe_cambiar_password = False
    usuario.save(update_fields=['password', 'debe_cambiar_password', 'modificado'])
    registrar(usuario, Accion.SEGURIDAD, 'Recuperó su contraseña con el código enviado por mail',
              objeto=usuario, ip=ip or None)
    for identificador in (usuario.username, usuario.email):
        if identificador:
            limpiar_login_fallidos(identificador, ip)
    return usuario


# ══════════════════════════════════════════════════════════════════
#  BLOQUEO DE LOGIN POR INTENTOS FALLIDOS
#  Se cuenta por (usuario ingresado + IP): así un atacante no puede
#  bloquear a otra persona desde otra computadora.
# ══════════════════════════════════════════════════════════════════

def _clave_intentos(identificador, ip):
    return f'login_fallidos:{(identificador or "").strip().lower()}:{ip or "-"}'


def login_bloqueado(identificador, ip):
    return cache.get(_clave_intentos(identificador, ip), 0) >= settings.LOGIN_INTENTOS_MAXIMOS


def registrar_login_fallido(identificador, ip):
    clave = _clave_intentos(identificador, ip)
    intentos = cache.get(clave, 0) + 1
    cache.set(clave, intentos, timeout=settings.LOGIN_BLOQUEO_MINUTOS * 60)
    return intentos


def limpiar_login_fallidos(identificador, ip):
    cache.delete(_clave_intentos(identificador, ip))
