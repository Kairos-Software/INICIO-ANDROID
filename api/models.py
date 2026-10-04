from django.conf import settings
from django.db import models


class TokenAcceso(models.Model):
    """
    Una "sesión" de la app en un dispositivo. Es el equivalente a la cookie
    de sesión del navegador: la app manda el token en cada pedido y así el
    servidor sabe quién es.

    Nunca se guarda el token: solo su huella (hash SHA-256), igual que las
    contraseñas. Si alguien copiara la base de datos, no podría usarlos.
    """
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='tokens_api')
    clave_hash = models.CharField(max_length=64, unique=True)
    dispositivo = models.CharField(max_length=100, blank=True, help_text='Ej: "Samsung A54". Lo informa la app.')
    # Huella de la contraseña al crear el token: si la contraseña cambia, el
    # token deja de servir (igual que las sesiones del navegador).
    huella_password = models.CharField(max_length=128)
    creado = models.DateTimeField(auto_now_add=True)
    ultimo_uso = models.DateTimeField()

    class Meta:
        verbose_name = 'token de acceso'
        verbose_name_plural = 'tokens de acceso'
        ordering = ['-ultimo_uso']

    def __str__(self):
        return f'{self.usuario} · {self.dispositivo or "dispositivo sin nombre"}'
