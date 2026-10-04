"""
Las versiones de la app Android (la APK) que se descargan desde el panel.

Cada vez que se compila una versión nueva, el administrador la sube acá.
/descargar/ siempre entrega la ÚLTIMA versión publicada.
"""

from django.conf import settings
from django.db import models


class VersionApp(models.Model):
    version = models.CharField('versión', max_length=30, help_text='Ej: 1.0.3 (la de pubspec.yaml).')
    archivo = models.FileField('APK', upload_to='apk/')
    notas = models.TextField('qué cambió', blank=True)
    publicada = models.BooleanField(default=True, help_text='Las no publicadas no se descargan.')
    subida = models.DateTimeField(auto_now_add=True)
    subida_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='+')

    class Meta:
        verbose_name = 'versión de la app'
        verbose_name_plural = 'versiones de la app'
        ordering = ['-subida', '-pk']

    def __str__(self):
        return f'Kairos TV {self.version}'

    @property
    def nombre_descarga(self):
        return f'KairosTV-{self.version}.apk'

    @classmethod
    def ultima(cls):
        return cls.objects.filter(publicada=True).first()
