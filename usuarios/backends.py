"""
Backend de autenticación: permite iniciar sesión con el nombre de usuario
o con el email, sin distinguir mayúsculas.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q


class UsuarioOEmailBackend(ModelBackend):

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None
        Usuario = get_user_model()
        identificador = username.strip()
        usuario = (
            Usuario.objects
            .filter(Q(username__iexact=identificador) | Q(email__iexact=identificador))
            .order_by('pk')
            .first()
        )
        if usuario is None:
            # Se calcula un hash igual, para que no se pueda saber por el
            # tiempo de respuesta si el usuario existe o no.
            Usuario().set_password(password)
            return None
        if usuario.check_password(password) and self.user_can_authenticate(usuario):
            return usuario
        return None
