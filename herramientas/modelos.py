"""
Molde para los modelos del sistema (clientes, productos, ventas...).

    from herramientas.modelos import ModeloBase

    class Cliente(ModeloBase):
        nombre = models.CharField(max_length=150)

Con eso el modelo ya tiene:

  creado / modificado          -> fecha y hora (automáticas)
  creado_por / modificado_por  -> quién (se completa con marcar_autor)
  eliminado_en / eliminado_por -> baja lógica: "eliminar" lo oculta, no lo borra

Y dos formas de consultarlo:

  Cliente.objects.all()   -> solo los NO eliminados (lo normal)
  Cliente.todos.all()     -> todos, incluidos los eliminados (papelera, informes)

Uso típico en un servicio:

    cliente = form.save(commit=False)
    cliente.marcar_autor(request.user)
    cliente.save()

    cliente.eliminar(request.user)      # baja lógica
    cliente.restaurar(request.user)     # la deshace
    cliente.delete()                    # borrado real (usar con cuidado)

Es abstracto: no crea ninguna tabla propia; cada modelo que lo usa recibe
estos campos en su propia tabla.
"""

from django.conf import settings
from django.db import models
from django.utils import timezone


class NoEliminadosManager(models.Manager):
    """Manager por defecto: esconde los registros dados de baja."""

    def get_queryset(self):
        return super().get_queryset().filter(eliminado_en__isnull=True)


class ModeloBase(models.Model):
    creado = models.DateTimeField('creado', auto_now_add=True)
    modificado = models.DateTimeField('modificado', auto_now=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='+', verbose_name='creado por', editable=False,
    )
    modificado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='+', verbose_name='modificado por', editable=False,
    )
    eliminado_en = models.DateTimeField('eliminado', null=True, blank=True, editable=False, db_index=True)
    eliminado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='+', verbose_name='eliminado por', editable=False,
    )

    objects = NoEliminadosManager()
    todos = models.Manager()

    class Meta:
        abstract = True
        # Las relaciones (ej: cliente.ventas) usan este manager: así un
        # registro eliminado sigue visible desde lo que depende de él.
        base_manager_name = 'todos'

    @property
    def esta_eliminado(self):
        return self.eliminado_en is not None

    def marcar_autor(self, usuario):
        """Completa quién lo creó (si es nuevo) y quién lo modificó. No guarda."""
        if usuario is not None and not getattr(usuario, 'is_authenticated', False):
            usuario = None
        if self._state.adding and self.creado_por_id is None:
            self.creado_por = usuario
        self.modificado_por = usuario

    def eliminar(self, usuario=None):
        """Baja lógica: deja de aparecer en `objects`, pero sigue en la base."""
        self.eliminado_en = timezone.now()
        self.eliminado_por = usuario if getattr(usuario, 'is_authenticated', False) else None
        self.save(update_fields=['eliminado_en', 'eliminado_por', 'modificado'])

    def restaurar(self, usuario=None):
        """Deshace la baja lógica."""
        self.eliminado_en = None
        self.eliminado_por = None
        self.marcar_autor(usuario)
        self.save(update_fields=['eliminado_en', 'eliminado_por', 'modificado_por', 'modificado'])
