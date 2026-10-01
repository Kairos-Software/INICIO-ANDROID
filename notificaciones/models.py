from django.conf import settings
from django.db import models


class Nivel(models.TextChoices):
    INFO = 'info', 'Información'
    EXITO = 'exito', 'Éxito'
    AVISO = 'aviso', 'Aviso'
    ERROR = 'error', 'Error'


class Notificacion(models.Model):
    destinatario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notificaciones',
    )
    titulo = models.CharField('título', max_length=150)
    mensaje = models.CharField(max_length=500, blank=True)
    # A dónde lleva al tocarla (opcional). Una ruta interna, ej: /usuarios/5/
    url = models.CharField(max_length=300, blank=True)
    nivel = models.CharField(max_length=10, choices=Nivel.choices, default=Nivel.INFO)
    creada = models.DateTimeField(auto_now_add=True)
    leida_en = models.DateTimeField('leída', null=True, blank=True)

    class Meta:
        verbose_name = 'notificación'
        verbose_name_plural = 'notificaciones'
        ordering = ['-creada', '-pk']
        indexes = [models.Index(fields=['destinatario', 'leida_en'])]

    def __str__(self):
        return f'{self.destinatario} · {self.titulo}'

    @property
    def leida(self):
        return self.leida_en is not None
