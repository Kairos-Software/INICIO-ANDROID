"""
Los canales de TV en vivo.

    Categoria  1 ──< Canal  1 ──< Fuente

Un canal (ej: "Canal 26") puede tener VARIAS fuentes: distintas direcciones
de la misma señal. La app usa la primera que funcione y, si se corta, pasa
sola a la siguiente (failover). Así, si una fuente se cae, el canal sigue.
"""

from django.db import models

from herramientas.modelos import ModeloBase


class Categoria(ModeloBase):
    nombre = models.CharField(max_length=80)
    orden = models.PositiveIntegerField(default=0, help_text='Menor = aparece primero.')

    class Meta:
        verbose_name = 'categoría'
        verbose_name_plural = 'categorías'
        ordering = ['orden', 'nombre']
        constraints = [
            models.UniqueConstraint(fields=['nombre'], condition=models.Q(eliminado_en__isnull=True),
                                    name='categoria_nombre_unico'),
        ]

    def __str__(self):
        return self.nombre


class Canal(ModeloBase):
    nombre = models.CharField(max_length=120)
    numero = models.CharField('número', max_length=10, blank=True, help_text='Número de canal (ej: 26).')
    logo = models.URLField(max_length=500, blank=True, help_text='Dirección de la imagen del logo.')
    categoria = models.ForeignKey(
        Categoria, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='canales', verbose_name='categoría',
    )
    # El identificador de las listas M3U (tvg-id): sirve para reconocer el
    # mismo canal en distintas listas y, más adelante, para la guía (EPG).
    tvg_id = models.CharField('ID de guía (tvg-id)', max_length=120, blank=True, db_index=True)
    pais = models.CharField('país', max_length=2, blank=True, help_text='Código de 2 letras (AR, UY...).')
    activo = models.BooleanField(default=True, help_text='Un canal inactivo no aparece en la app.')
    orden = models.PositiveIntegerField(default=0, help_text='Menor = aparece primero dentro de su categoría.')

    class Meta:
        verbose_name = 'canal'
        verbose_name_plural = 'canales'
        ordering = ['orden', 'nombre']

    def __str__(self):
        return f'{self.numero} · {self.nombre}' if self.numero else self.nombre


class Fuente(models.Model):

    class Tipo(models.TextChoices):
        HLS = 'hls', 'HLS (.m3u8)'
        YOUTUBE = 'youtube', 'YouTube'

    canal = models.ForeignKey(Canal, on_delete=models.CASCADE, related_name='fuentes')
    url = models.URLField('dirección', max_length=1000)
    tipo = models.CharField(max_length=10, choices=Tipo.choices, default=Tipo.HLS)
    prioridad = models.PositiveIntegerField(default=0, help_text='Menor = se prueba primero.')
    activa = models.BooleanField(default=True)
    origen = models.CharField(max_length=150, blank=True, help_text='De qué lista se importó.')
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'fuente'
        verbose_name_plural = 'fuentes'
        ordering = ['prioridad', 'pk']
        constraints = [
            models.UniqueConstraint(fields=['canal', 'url'], name='fuente_unica_por_canal'),
        ]

    def __str__(self):
        return f'{self.canal} · {self.get_tipo_display()} · {self.url[:60]}'
