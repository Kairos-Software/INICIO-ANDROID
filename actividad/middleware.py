"""
Deja la IP de cada pedido disponible para `registrar()`, sin tener que
pasarla a mano por todos los servicios.
"""

from .registro import ip_actual


def ip_de_request(request):
    # Detrás de nginx la IP real llega en X-Real-IP (nginx la sobrescribe
    # siempre). No se usa X-Forwarded-For porque el navegador lo puede inventar.
    return request.META.get('HTTP_X_REAL_IP') or request.META.get('REMOTE_ADDR') or None


class ContextoActividadMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        token = ip_actual.set(ip_de_request(request))
        try:
            return self.get_response(request)
        finally:
            ip_actual.reset(token)
