"""
Cómo sabe la API quién hace cada pedido.

La app manda el token en un encabezado de cada pedido:

    Authorization: Bearer <token>

DRF llama a `authenticate()` antes de cada vista: si devuelve (usuario,
token), queda en `request.user` y `request.auth`, igual que en las vistas
de siempre. Si no viene el encabezado, devuelve None (pedido anónimo) y
DRF prueba la siguiente forma de autenticar (la sesión del navegador).
"""

from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed

from . import tokens


class TokenBearer(BaseAuthentication):
    palabra_clave = 'Bearer'

    def authenticate(self, request):
        partes = get_authorization_header(request).split()
        if not partes or partes[0].lower() != self.palabra_clave.lower().encode():
            return None
        if len(partes) != 2:
            raise AuthenticationFailed('El encabezado Authorization tiene que ser: Bearer <token>.')

        token = tokens.validar_token(partes[1].decode(errors='ignore'))
        if token is None:
            raise AuthenticationFailed()
        return token.usuario, token

    def authenticate_header(self, request):
        # Con esto, "no autenticado" responde 401 (y no 403)
        return self.palabra_clave
