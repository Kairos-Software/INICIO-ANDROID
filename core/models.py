from django.conf import settings
from django.db import models


class EstadoMantenimiento(models.Model):
    """
    Una sola fila (pk=1) con el estado del modo mantenimiento.
    Usar siempre EstadoMantenimiento.obtener(), nunca crear filas a mano.
    """
    activo = models.BooleanField(default=False)
    mensaje = models.CharField(
        max_length=300, blank=True,
        help_text='Lo que ven los usuarios. Si se deja vacío se muestra un mensaje genérico.',
    )
    vuelve_aprox = models.CharField(
        'vuelve aproximadamente', max_length=60, blank=True,
        help_text='Opcional. Ej: "a las 15:30" o "en 20 minutos".',
    )
    modificado = models.DateTimeField(auto_now=True)
    modificado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+',
    )

    class Meta:
        verbose_name = 'estado de mantenimiento'
        verbose_name_plural = 'estado de mantenimiento'

    def __str__(self):
        return 'Mantenimiento activo' if self.activo else 'Sistema funcionando'

    @classmethod
    def obtener(cls):
        estado, _ = cls.objects.get_or_create(pk=1)
        return estado
