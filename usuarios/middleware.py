"""
Middleware = código que corre en CADA pedido, antes de llegar a la vista.

CambioPasswordObligatorioMiddleware: si el usuario tiene la marca
"debe cambiar la contraseña" (ej: un administrador le asignó una
temporal), lo manda a cambiarla y no lo deja usar el sistema hasta que lo
haga. Solo le permite cambiar la contraseña, cerrar sesión y cargar los
archivos estáticos.
"""

from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse


class CambioPasswordObligatorioMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        usuario = getattr(request, 'user', None)
        if usuario is not None and usuario.is_authenticated and usuario.debe_cambiar_password:
            if not self._ruta_permitida(request.path):
                return redirect('usuarios:cambiar_password')
        return self.get_response(request)

    @staticmethod
    def _ruta_permitida(ruta):
        permitidas = (
            reverse('usuarios:cambiar_password'),
            reverse('usuarios:logout'),
            '/api/',   # la API lo resuelve sola y responde JSON (api/permisos.py)
            settings.STATIC_URL,
            settings.MEDIA_URL,
        )
        return ruta.startswith(permitidas)
