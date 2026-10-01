"""
Cómo cualquier parte del sistema le avisa algo a los usuarios (capa Base).

    from notificaciones.servicios import notificar, notificar_a_quienes_puedan

    # A una o varias personas
    notificar(usuario, 'Te asignaron un pedido', 'Pedido #123 de Juan Pérez', url='/pedidos/123/')

    # A todos los que tengan un permiso (ej: los que pueden ver pedidos)
    notificar_a_quienes_puedan('ver_pedidos', 'Entró un pedido nuevo', url='/pedidos/123/', nivel='aviso')

Nunca rompe la operación principal: si falla, lo anota en el log y sigue.
"""

import logging

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme

from .models import Nivel, Notificacion

logger = logging.getLogger(__name__)


def notificar(destinatarios, titulo, mensaje='', url='', nivel=Nivel.INFO, excepto=None):
    """
    `destinatarios`: un usuario, o una lista / queryset de usuarios.
    `excepto`: usuario a quien NO avisarle (ej: el que hizo la acción).
    Devuelve la cantidad de notificaciones creadas.
    """
    if destinatarios is None:
        return 0
    if isinstance(destinatarios, get_user_model()):
        destinatarios = [destinatarios]
    # Solo rutas internas: nunca un link a otro sitio
    if url and not url_has_allowed_host_and_scheme(url, allowed_hosts=None):
        url = ''
    try:
        with transaction.atomic():
            nuevas = [
                Notificacion(destinatario=u, titulo=titulo[:150], mensaje=mensaje[:500], url=url, nivel=nivel)
                for u in destinatarios
                if u.is_active and (excepto is None or u.pk != excepto.pk)
            ]
            Notificacion.objects.bulk_create(nuevas)
            return len(nuevas)
    except Exception:  # noqa: BLE001 — avisar nunca debe romper la operación
        logger.exception('No se pudo crear la notificación: %s', titulo)
        return 0


def notificar_a_quienes_puedan(codigo_permiso, titulo, mensaje='', url='', nivel=Nivel.INFO, excepto=None):
    """Avisa a todos los usuarios activos que tienen el permiso `codigo_permiso`."""
    from usuarios.permisos import chequear_permiso  # import local: evita dependencia circular

    usuarios = get_user_model().objects.filter(is_active=True).select_related('rol')
    destinatarios = [u for u in usuarios if chequear_permiso(u, codigo_permiso)]
    return notificar(destinatarios, titulo, mensaje, url, nivel, excepto)


def cantidad_no_leidas(usuario):
    return usuario.notificaciones.filter(leida_en__isnull=True).count()


def marcar_leida(notificacion):
    if notificacion.leida_en is None:
        notificacion.leida_en = timezone.now()
        notificacion.save(update_fields=['leida_en'])


def marcar_todas_leidas(usuario):
    return usuario.notificaciones.filter(leida_en__isnull=True).update(leida_en=timezone.now())
