"""
Protección de vistas por permiso.

    from usuarios.decoradores import requiere_permiso

    @requiere_permiso('ver_usuarios')
    def lista_usuarios(request): ...

    # Varios permisos: alcanza con tener uno
    @requiere_permiso('editar_usuarios', 'crear_usuarios')

Si no hay sesión, manda al login. Si hay sesión pero falta el permiso,
muestra la página 403 ("No tenés permiso").
"""

from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied

from .permisos import tiene_algun_permiso


def requiere_permiso(*codigos):
    def decorador(vista):
        @wraps(vista)
        def envoltorio(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            if not tiene_algun_permiso(request.user, *codigos):
                raise PermissionDenied
            return vista(request, *args, **kwargs)
        return envoltorio
    return decorador
