"""
Lo que el sistema HACE con los tokens de la API (capa Base).

Cómo funciona:
  1. Al iniciar sesión se genera un texto aleatorio imposible de adivinar
     (el token) y se le entrega a la app UNA sola vez.
  2. En la base se guarda solo su huella (SHA-256).
  3. En cada pedido la app manda `Authorization: Bearer <token>`; el
     servidor calcula la huella y la busca.

Un token deja de servir si:
  - pasan API_TOKEN_DIAS sin usarlo,
  - el usuario cierra sesión en la app (se borra),
  - cambia la contraseña del usuario,
  - el usuario queda inactivo o se elimina.
"""

import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from .models import TokenAcceso

# Cada cuánto se actualiza `ultimo_uso` (no en cada pedido: ahorra escrituras)
INTERVALO_ACTUALIZAR_USO = timedelta(minutes=5)


def _huella(clave):
    return hashlib.sha256(clave.encode()).hexdigest()


def vencimiento(token):
    return token.ultimo_uso + timedelta(days=settings.API_TOKEN_DIAS)


def crear_token(usuario, dispositivo=''):
    """Genera un token nuevo. Devuelve (clave, token): la clave solo existe en este momento."""
    clave = secrets.token_urlsafe(32)
    token = TokenAcceso.objects.create(
        usuario=usuario,
        clave_hash=_huella(clave),
        dispositivo=(dispositivo or '')[:100],
        huella_password=usuario.get_session_auth_hash(),
        ultimo_uso=timezone.now(),
    )
    return clave, token


def validar_token(clave):
    """
    El TokenAcceso de esa clave si sigue siendo válido; None si no.
    Los tokens vencidos o de una contraseña vieja se borran al encontrarlos.
    """
    if not clave:
        return None
    token = TokenAcceso.objects.select_related('usuario', 'usuario__rol').filter(clave_hash=_huella(clave)).first()
    if token is None:
        return None

    ahora = timezone.now()
    usuario = token.usuario
    if ahora > vencimiento(token) or token.huella_password != usuario.get_session_auth_hash():
        token.delete()
        return None
    if not usuario.is_active:
        return None

    if ahora - token.ultimo_uso > INTERVALO_ACTUALIZAR_USO:
        token.ultimo_uso = ahora
        token.save(update_fields=['ultimo_uso'])
    return token


def revocar(token):
    token.delete()


def mantener_tras_cambio_de_password(token):
    """
    Después de que el usuario cambia SU contraseña desde la app: este token
    sigue valiendo (los de otros dispositivos no). Igual que en la web.
    """
    token.huella_password = token.usuario.get_session_auth_hash()
    token.save(update_fields=['huella_password'])


def borrar_vencidos():
    """Borra los tokens sin uso hace más de API_TOKEN_DIAS. Devuelve cuántos."""
    limite = timezone.now() - timedelta(days=settings.API_TOKEN_DIAS)
    cantidad, _ = TokenAcceso.objects.filter(ultimo_uso__lt=limite).delete()
    return cantidad
