"""Búsqueda en el registro de actividad (capa Base)."""

from datetime import datetime, time

from django.db.models import Q
from django.utils import timezone

from .models import RegistroActividad


def _fecha(texto, fin_del_dia=False):
    try:
        dia = datetime.strptime(texto, '%Y-%m-%d').date()
    except (TypeError, ValueError):
        return None
    return timezone.make_aware(datetime.combine(dia, time.max if fin_del_dia else time.min))


def buscar_actividad(texto='', accion='', modulo='', desde='', hasta='', usuario_id=''):
    qs = RegistroActividad.objects.all()
    for palabra in (texto or '').split():
        qs = qs.filter(
            Q(descripcion__icontains=palabra)
            | Q(usuario_texto__icontains=palabra)
            | Q(objeto_texto__icontains=palabra)
        )
    if accion:
        qs = qs.filter(accion=accion)
    if modulo:
        qs = qs.filter(modulo=modulo)
    if usuario_id:
        # Lo que hizo ese usuario, o lo que le hicieron a él
        qs = qs.filter(
            Q(usuario_id=usuario_id)
            | Q(objeto_tipo='usuarios.Usuario', objeto_id=str(usuario_id))
        )
    if (inicio := _fecha(desde)) is not None:
        qs = qs.filter(fecha__gte=inicio)
    if (fin := _fecha(hasta, fin_del_dia=True)) is not None:
        qs = qs.filter(fecha__lte=fin)
    return qs.order_by('-fecha', '-pk')


def modulos_registrados():
    return list(
        RegistroActividad.objects.exclude(modulo='')
        .order_by('modulo').values_list('modulo', flat=True).distinct()
    )
