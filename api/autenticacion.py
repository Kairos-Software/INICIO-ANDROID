"""
Cómo sabe la API quién hace cada pedido.

La app manda el token en un encabezado de cada pedido:

    Authorization: Bearer <token>

DRF llama a `authenticate()` antes de cada vista: si devuelve (usuario,
token), queda en `request.user` y `request.auth`, igual que en las vistas
de siempre. Si no viene el encabezado, devuelve None (pedido anónimo) y
DRF prueba la siguiente forma de autenticar (la sesión del navegador).

Hay dos clases de token, con la misma palabra "Bearer":
  - TokenBearer:  usuarios del panel (login con usuario y contraseña).
  - TokenCliente: clientes que miran la TV (login con su código). Sus
    tokens empiezan con "c_"; `request.user` es un ClienteApp.
"""

from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed

from reventa import sesiones

from . import tokens


def _clave_bearer(request, palabra_clave):
    """La clave que viene en 'Authorization: Bearer <clave>', o None si no vino ese encabezado."""
    partes = get_authorization_header(request).split()
    if not partes or partes[0].lower() != palabra_clave.lower().encode():
        return None
    if len(partes) != 2:
        raise AuthenticationFailed('El encabezado Authorization tiene que ser: Bearer <token>.')
    return partes[1].decode(errors='ignore')


class TokenBearer(BaseAuthentication):
    palabra_clave = 'Bearer'

    def authenticate(self, request):
        clave = _clave_bearer(request, self.palabra_clave)
        if clave is None or sesiones.es_token_de_cliente(clave):
            return None   # sin token, o es de un cliente: lo resuelve TokenCliente
        token = tokens.validar_token(clave)
        if token is None:
            raise AuthenticationFailed()
        return token.usuario, token

    def authenticate_header(self, request):
        # Con esto, "no autenticado" responde 401 (y no 403)
        return self.palabra_clave


class TokenCliente(TokenBearer):
    """Token de un cliente (empieza con "c_"). request.user = ClienteApp, request.auth = Dispositivo."""

    def authenticate(self, request):
        clave = _clave_bearer(request, self.palabra_clave)
        if clave is None or not sesiones.es_token_de_cliente(clave):
            return None
        dispositivo = sesiones.validar(clave)
        if dispositivo is None:
            raise AuthenticationFailed()
        return sesiones.ClienteApp(dispositivo), dispositivo
