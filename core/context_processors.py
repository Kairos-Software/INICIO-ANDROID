"""Datos de la marca (y, para superusuarios, el aviso de mantenimiento) en todos los templates."""

from django.conf import settings

from .mantenimiento import estado_actual


def sistema(request):
    datos = {
        'NOMBRE_SISTEMA': settings.NOMBRE_SISTEMA,
        'NOMBRE_EMPRESA': settings.NOMBRE_EMPRESA,
    }
    usuario = getattr(request, 'user', None)
    if usuario is not None and usuario.is_authenticated and usuario.is_superuser:
        # Para mostrarle al superusuario que el sistema está en mantenimiento
        datos['mantenimiento_activo'] = estado_actual()['activo']
    return datos
