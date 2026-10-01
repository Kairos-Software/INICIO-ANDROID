"""
ModoMantenimientoMiddleware: si el modo mantenimiento está activo, muestra
la pantalla "Estamos actualizando el sistema" a todos menos a los
superusuarios. Deja pasar el login (para que un superusuario pueda
entrar), los archivos estáticos y el admin de Django.

Si quien llega tiene la sesión iniciada y no es superusuario, se la cierra:
así el login vuelve a quedar libre para que entre un superusuario desde ese
mismo navegador.
"""

from django.conf import settings
from django.contrib.auth import logout
from django.urls import reverse

from .mantenimiento import estado_actual


class ModoMantenimientoMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        usuario = getattr(request, 'user', None)
        es_superusuario = usuario is not None and usuario.is_authenticated and usuario.is_superuser
        if not es_superusuario and not self._ruta_libre(request.path):
            estado = estado_actual()
            if estado['activo']:
                if usuario is not None and usuario.is_authenticated:
                    logout(request)
                from .views import pantalla_mantenimiento
                return pantalla_mantenimiento(estado)
        return self.get_response(request)

    @staticmethod
    def _ruta_libre(ruta):
        libres = (
            reverse('usuarios:login'),
            reverse('usuarios:logout'),
            '/admin/',
            settings.STATIC_URL,
            settings.MEDIA_URL,
        )
        return ruta.startswith(libres)
