"""
`permisos` — disponible en todos los templates para mostrar u ocultar
partes de la pantalla según los permisos del usuario:

    {% if permisos.ver_usuarios %} ... {% endif %}
    {% if 'ver_usuarios' in permisos %} ... {% endif %}

Solo sirve para la pantalla: cada vista igual chequea el permiso en el
servidor (con `requiere_permiso` o `chequear_permiso`).
"""

from .permisos import permisos_efectivos


class _Permisos:
    """Envoltorio de solo lectura sobre el set de códigos concedidos."""

    __slots__ = ('_codigos',)

    def __init__(self, codigos):
        object.__setattr__(self, '_codigos', frozenset(codigos))

    def __contains__(self, codigo):
        return codigo in self._codigos

    def __getattr__(self, codigo):
        return codigo in self._codigos

    def __bool__(self):
        return bool(self._codigos)

    def __iter__(self):
        return iter(self._codigos)


def permisos(request):
    usuario = getattr(request, 'user', None)
    return {'permisos': _Permisos(permisos_efectivos(usuario))}
