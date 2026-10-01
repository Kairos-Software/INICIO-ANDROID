"""
Modo mantenimiento (capa Base).

Mientras está activo, todos ven "Estamos actualizando el sistema", salvo
los superusuarios, que pueden seguir entrando para probar.

Se activa de dos formas:
  - Desde la pantalla Sistema → Mantenimiento (solo superusuarios).
  - Desde el .env con MODO_MANTENIMIENTO=True (útil durante un despliegue:
    manda aunque la base de datos no esté disponible).
"""

from django.conf import settings
from django.core.cache import cache
from django.db import DatabaseError

from actividad.models import Accion
from actividad.registro import registrar

from .models import EstadoMantenimiento

CLAVE_CACHE = 'modo_mantenimiento'
SEGUNDOS_CACHE = 5   # cuánto tarda, como mucho, en notarse un cambio


def forzado_por_env():
    return getattr(settings, 'MODO_MANTENIMIENTO', False)


def estado_actual():
    """
    {'activo': bool, 'mensaje': str, 'vuelve_aprox': str, 'forzado': bool}
    Se guarda unos segundos en caché para no consultar la base en cada pedido.
    """
    if forzado_por_env():
        return {'activo': True, 'mensaje': '', 'vuelve_aprox': '', 'forzado': True}
    datos = cache.get(CLAVE_CACHE)
    if datos is None:
        try:
            estado = EstadoMantenimiento.obtener()
            datos = {'activo': estado.activo, 'mensaje': estado.mensaje,
                     'vuelve_aprox': estado.vuelve_aprox, 'forzado': False}
        except DatabaseError:
            # Si la base no responde, no se bloquea a nadie por esto
            datos = {'activo': False, 'mensaje': '', 'vuelve_aprox': '', 'forzado': False}
        cache.set(CLAVE_CACHE, datos, SEGUNDOS_CACHE)
    return datos


def guardar_estado(form, solicitante):
    """Guarda el EstadoMantenimientoForm ya validado y lo registra en la actividad."""
    estado = form.save(commit=False)
    estado.modificado_por = solicitante
    estado.save()
    cache.delete(CLAVE_CACHE)
    if 'activo' in form.changed_data:
        registrar(solicitante, Accion.SISTEMA,
                  'Activó el modo mantenimiento' if estado.activo else 'Desactivó el modo mantenimiento',
                  objeto=estado, modulo='sistema')
    return estado
