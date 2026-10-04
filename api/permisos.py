"""
Quién puede usar la API.

- `SistemaDisponible` se aplica a TODAS las vistas (ver REST_FRAMEWORK en
  settings): si el sistema está en mantenimiento solo deja pasar a los
  superusuarios, y si el usuario tiene que cambiar la contraseña solo lo
  deja ver su perfil, cambiarla y cerrar sesión. Es lo mismo que hacen los
  middlewares en la web.
- `exigir_permiso()` chequea los permisos del catálogo, con la misma lógica
  que la web (usuarios/permisos.py).
"""

from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission

from core.mantenimiento import estado_actual
from usuarios.permisos import tiene_algun_permiso

from .errores import ErrorApi

# Lo único que puede hacer quien tiene que cambiar la contraseña
VISTAS_CON_PASSWORD_PENDIENTE = {'api_v1:perfil', 'api_v1:cambiar_password', 'api_v1:logout'}


def error_mantenimiento(estado):
    return ErrorApi(
        estado['mensaje'] or 'Estamos actualizando el sistema. Volvé a intentar en unos minutos.',
        'mantenimiento', status.HTTP_503_SERVICE_UNAVAILABLE,
        extra={'vuelve': estado['vuelve_aprox']},
    )


class SistemaDisponible(BasePermission):

    def has_permission(self, request, view):
        usuario = request.user
        if not usuario.is_superuser:
            estado = estado_actual()
            if estado['activo']:
                raise error_mantenimiento(estado)

        if usuario.is_authenticated and usuario.debe_cambiar_password:
            vista = request.resolver_match.view_name if request.resolver_match else ''
            if vista not in VISTAS_CON_PASSWORD_PENDIENTE:
                raise ErrorApi('Tenés que cambiar tu contraseña antes de seguir.', 'debe_cambiar_password',
                               status.HTTP_403_FORBIDDEN)
        return True


def exigir_permiso(usuario, *codigos):
    """Corta con 403 si `usuario` no tiene ninguno de los permisos `codigos`."""
    if not tiene_algun_permiso(usuario, *codigos):
        raise PermissionDenied()
