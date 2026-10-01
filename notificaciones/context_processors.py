"""
Deja en todos los templates lo que necesita la campanita:
  notificaciones_no_leidas -> cantidad
  notificaciones_recientes -> las últimas 5
"""

from .models import Notificacion


def notificaciones(request):
    usuario = getattr(request, 'user', None)
    if usuario is None or not usuario.is_authenticated:
        return {}
    return {
        'notificaciones_no_leidas': Notificacion.objects.filter(destinatario=usuario, leida_en__isnull=True).count(),
        'notificaciones_recientes': Notificacion.objects.filter(destinatario=usuario)[:5],
    }
