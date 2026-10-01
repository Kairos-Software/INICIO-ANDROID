"""
Lo que el sistema BUSCA o LISTA de usuarios (capa Base).
"""

from django.db.models import Count, Q

from .models import Rol, Usuario


def usuarios_gestionables(solicitante):
    """
    Usuarios que `solicitante` puede ver y gestionar desde las pantallas.

    - Nunca un superusuario: si no, alguien con 'editar_usuarios' podría
      cambiarle el email al dueño y usar "Olvidé mi contraseña" para
      quedarse con su cuenta. Los superusuarios se gestionan desde /admin/.
    - Nunca a sí mismo: los datos propios se editan desde "Mi perfil", y
      así nadie puede subirse el rol ni desactivarse por error.

    TODA vista que reciba el id de un usuario tiene que buscarlo acá.
    """
    return (
        Usuario.objects
        .filter(is_superuser=False)
        .exclude(pk=solicitante.pk)
        .select_related('rol')
    )


def buscar_usuarios(solicitante, texto='', rol=None, estado=''):
    """
    Lista filtrada para la pantalla de usuarios.

    texto  -> busca en usuario, nombre, apellido, email y documento
    rol    -> id de rol, o 'sin_rol'
    estado -> 'activos' | 'inactivos' | '' (todos)
    """
    qs = usuarios_gestionables(solicitante)

    for palabra in (texto or '').split():
        qs = qs.filter(
            Q(username__icontains=palabra)
            | Q(first_name__icontains=palabra)
            | Q(last_name__icontains=palabra)
            | Q(email__icontains=palabra)
            | Q(numero_documento__icontains=palabra)
        )

    if rol == 'sin_rol':
        qs = qs.filter(rol__isnull=True)
    elif rol:
        qs = qs.filter(rol_id=rol)

    if estado == 'activos':
        qs = qs.filter(is_active=True)
    elif estado == 'inactivos':
        qs = qs.filter(is_active=False)

    return qs.order_by('-is_active', 'first_name', 'last_name', 'username')


def roles_para_filtro():
    return Rol.objects.order_by('nombre')


def roles_con_uso():
    """Roles con la cantidad de usuarios que tienen cada uno."""
    return Rol.objects.annotate(cantidad_usuarios=Count('usuarios')).order_by('nombre')
