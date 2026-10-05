"""
Ayudas para las pantallas de canales.

    {% load canales_extras %}
    {{ canal.nombre|iniciales }}   -> 'Canal 26' -> 'C2' (lo que muestra la app si no hay logo)
"""

from django import template

register = template.Library()


@register.filter
def iniciales(nombre):
    return ''.join(palabra[0] for palabra in (nombre or '').split()[:2]).upper() or '?'
