"""
Todas las respuestas de error de la API tienen la misma forma, así la app
las maneja siempre igual:

    {"codigo": "sin_permiso", "detalle": "No tenés permiso para hacer esto."}

Y si son errores de datos (un formulario), además los errores por campo:

    {"codigo": "datos_invalidos", "detalle": "Revisá los datos enviados.",
     "campos": {"email": ["Ya existe un usuario con ese email."]}}

`codigo` es para el programa (la app decide qué hacer); `detalle` es para
mostrarle a la persona.
"""

import logging

from django.conf import settings
from django.core.exceptions import PermissionDenied as PermisoDenegadoDjango
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import APIException, NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response

from usuarios.servicios import OperacionNoPermitida

logger = logging.getLogger(__name__)

# Códigos de DRF -> los nuestros, con su mensaje
CODIGOS_DRF = {
    'not_authenticated': ('no_autenticado', 'Tenés que iniciar sesión.'),
    'authentication_failed': ('token_invalido', 'La sesión no es válida o venció. Iniciá sesión de nuevo.'),
    'permission_denied': ('sin_permiso', 'No tenés permiso para hacer esto.'),
    'not_found': ('no_encontrado', 'No existe lo que buscás.'),
    'method_not_allowed': ('metodo_no_permitido', None),
    'throttled': ('demasiados_pedidos', None),
    'parse_error': ('json_invalido', 'Los datos enviados no tienen un formato válido.'),
    'unsupported_media_type': ('formato_no_soportado', None),
}


class ErrorApi(APIException):
    """Error con código propio. `extra` se suma a la respuesta (ej: datos del mantenimiento)."""

    def __init__(self, detalle, codigo, status_code=status.HTTP_400_BAD_REQUEST, extra=None):
        super().__init__(detalle, codigo)
        self.status_code = status_code
        self.codigo = codigo
        self.extra = extra or {}


class DatosInvalidos(ValidationError):
    """Errores por campo: {campo: [mensajes]}."""


def errores_de_formulario(form):
    """{campo: [mensajes]} de un formulario de Django. Los errores generales van en 'general'."""
    return {
        ('general' if campo == '__all__' else campo): [e['message'] for e in errores]
        for campo, errores in form.errors.get_json_data().items()
    }


def validar_formulario(form):
    """Si el formulario tiene errores, corta la vista con un 400 y los errores por campo."""
    if not form.is_valid():
        raise DatosInvalidos(errores_de_formulario(form))


def manejar_error(exc, context):
    # Import acá: este módulo lo usan las clases de permisos, que DRF carga
    # mientras arma rest_framework.views (importarlo arriba sería circular)
    from rest_framework.views import exception_handler

    # Las excepciones de Django (get_object_or_404, etc.) se pasan a las de DRF
    if isinstance(exc, Http404):
        exc = NotFound()
    elif isinstance(exc, PermisoDenegadoDjango):
        exc = PermissionDenied()
    elif isinstance(exc, OperacionNoPermitida):
        exc = ErrorApi(str(exc), 'operacion_no_permitida')

    respuesta = exception_handler(exc, context)
    if respuesta is None:
        # Error inesperado (un bug): con DEBUG se ve la pantalla de Django
        if settings.DEBUG:
            return None
        logger.exception('Error inesperado en la API', exc_info=exc)
        return Response({'codigo': 'error_interno', 'detalle': 'Ocurrió un error inesperado.'},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    if isinstance(exc, ValidationError):
        campos = respuesta.data if isinstance(respuesta.data, dict) else {'general': respuesta.data}
        respuesta.data = {'codigo': 'datos_invalidos', 'detalle': 'Revisá los datos enviados.', 'campos': campos}
        return respuesta

    if isinstance(exc, ErrorApi):
        respuesta.data = {'codigo': exc.codigo, 'detalle': str(exc.detail), **exc.extra}
        return respuesta

    codigo_drf = exc.get_codes() if isinstance(exc, APIException) else ''
    codigo, mensaje = CODIGOS_DRF.get(codigo_drf, (codigo_drf or 'error', None))
    detalle = respuesta.data.get('detail', '') if isinstance(respuesta.data, dict) else ''
    # El mensaje propio solo si la vista no puso uno específico
    if mensaje and str(detalle) == str(exc.default_detail):
        detalle = mensaje
    respuesta.data = {'codigo': codigo, 'detalle': str(detalle)}
    return respuesta
