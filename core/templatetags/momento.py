"""
Valores iniciales del "momento" (saludo, hora, avance del día) calculados
en el servidor. El JS de static/js/sistema.js después los mantiene al día
con la hora del dispositivo.

    {% load momento %}
    {% saludo %}          -> "Buenas tardes"
    {% avance_dia %}      -> "58.33%"
"""

from django import template
from django.utils import timezone

register = template.Library()


@register.simple_tag
def saludo():
    hora = timezone.localtime().hour
    if 6 <= hora < 13:
        return 'Buen día'
    if 13 <= hora < 20:
        return 'Buenas tardes'
    return 'Buenas noches'


@register.simple_tag
def avance_dia():
    ahora = timezone.localtime()
    return f'{(ahora.hour * 60 + ahora.minute) / 1440 * 100:.2f}%'
