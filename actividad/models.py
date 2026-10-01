from django.conf import settings
from django.db import models


class Accion(models.TextChoices):
    INGRESO = 'ingreso', 'Ingresó al sistema'
    INGRESO_FALLIDO = 'ingreso_fallido', 'Intento de ingreso fallido'
    SALIDA = 'salida', 'Cerró sesión'
    CREAR = 'crear', 'Creó'
    EDITAR = 'editar', 'Editó'
    ELIMINAR = 'eliminar', 'Eliminó'
    SEGURIDAD = 'seguridad', 'Seguridad'      # contraseñas, permisos, roles
    SISTEMA = 'sistema', 'Sistema'            # configuración, mantenimiento
    OTRO = 'otro', 'Otro'


class RegistroActividad(models.Model):
    """
    Una fila por cada cosa que pasó en el sistema. Solo se agregan filas,
    nunca se modifican. Se guardan también textos (usuario, objeto) para que
    el registro siga siendo legible aunque después se borre lo referenciado.
    """
    fecha = models.DateTimeField(auto_now_add=True, db_index=True)

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='+',
    )
    usuario_texto = models.CharField('usuario', max_length=150, blank=True)

    accion = models.CharField(max_length=20, choices=Accion.choices, db_index=True)
    modulo = models.CharField('módulo', max_length=50, blank=True, db_index=True)
    descripcion = models.CharField('descripción', max_length=300)

    # Sobre qué se hizo (opcional)
    objeto_tipo = models.CharField(max_length=100, blank=True)
    objeto_id = models.CharField(max_length=50, blank=True)
    objeto_texto = models.CharField(max_length=200, blank=True)

    # {"campo": ["antes", "después"], ...}
    cambios = models.JSONField(default=dict, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        verbose_name = 'registro de actividad'
        verbose_name_plural = 'registro de actividad'
        ordering = ['-fecha']
        indexes = [models.Index(fields=['objeto_tipo', 'objeto_id'])]

    def __str__(self):
        return f'{self.fecha:%d/%m/%Y %H:%M} · {self.usuario_texto or "sistema"} · {self.descripcion}'
