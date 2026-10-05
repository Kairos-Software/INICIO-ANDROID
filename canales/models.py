"""
Los canales de TV en vivo.

    Categoria  1 ──< Canal  1 ──< Fuente

    Importacion  1 ──< EntradaImportada  (una lista M3U subida y qué pasó con cada línea)

Un canal (ej: "Canal 26") puede tener VARIAS fuentes: distintas direcciones
de la misma señal. La app usa la primera que funcione y, si se corta, pasa
sola a la siguiente (failover). Así, si una fuente se cae, el canal sigue.
"""

from datetime import timedelta

from django.conf import settings
from django.core.validators import URLValidator
from django.db import models
from django.utils import timezone

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


class Idioma(models.TextChoices):
    ESPANOL = 'es', 'Español'
    OTRO = 'otro', 'Otro idioma'
    DESCONOCIDO = '', 'No se sabe'


class Contenido(models.TextChoices):
    VIVO = 'vivo', 'En vivo'
    PELICULA = 'pelicula', 'Película'
    SERIE = 'serie', 'Serie'


class Canal(ModeloBase):
    """
    Un canal en vivo, o una película o capítulo de serie (`contenido`). Por
    ahora la app muestra los en vivo; películas y series se cargan igual,
    para cuando la app tenga esas secciones.
    """
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
    contenido = models.CharField(max_length=10, choices=Contenido.choices, default=Contenido.VIVO, db_index=True)
    idioma = models.CharField(max_length=5, choices=Idioma.choices, blank=True, db_index=True,
                              help_text='Estimado al importar (país, categoría, prefijo del nombre...).')
    activo = models.BooleanField(default=True, help_text='Un canal inactivo ("quitado") no aparece en la app.')
    motivo_quitado = models.CharField('por qué se quitó', max_length=200, blank=True)
    orden = models.PositiveIntegerField(default=0, help_text='Menor = aparece primero dentro de su categoría.')

    class Meta:
        verbose_name = 'canal'
        verbose_name_plural = 'canales'
        ordering = ['orden', 'nombre']

    def __str__(self):
        return f'{self.numero} · {self.nombre}' if self.numero else self.nombre


# Cuántos días queda oculta una fuente que falla en los aparatos. Después la
# app la vuelve a intentar (por si el problema era pasajero).
DIAS_OCULTA = 7


def hace_dias_oculta():
    return timezone.now() - timedelta(days=DIAS_OCULTA)


class Fuente(models.Model):

    # El formato de la señal. Lo averigua la verificación mirando lo que
    # responde el servidor (como VLC), no la extensión de la dirección.
    class Tipo(models.TextChoices):
        HLS = 'hls', 'HLS (.m3u8)'
        DASH = 'dash', 'DASH (.mpd)'
        DIRECTO = 'directo', 'Video directo (TS, MP4...)'
        RTSP = 'rtsp', 'RTSP'
        YOUTUBE = 'youtube', 'YouTube'
        PAGINA = 'pagina', 'Página de video (Twitch, Dailymotion...)'

    # `activa` la decide una persona; `estado` lo pone la verificación
    # automática. La app usa una fuente solo si está activa Y no está caída.
    class Estado(models.TextChoices):
        SIN_VERIFICAR = 'sin_verificar', 'Sin verificar'
        FUNCIONA = 'funciona', 'Funciona'
        CAIDA = 'caida', 'Caída'

    canal = models.ForeignKey(Canal, on_delete=models.CASCADE, related_name='fuentes')
    url = models.CharField('dirección', max_length=1000,
                           validators=[URLValidator(schemes=['http', 'https', 'rtsp', 'rtsps'])])
    tipo = models.CharField(max_length=10, choices=Tipo.choices, default=Tipo.HLS)
    prioridad = models.PositiveIntegerField(default=0, help_text='Menor = se prueba primero.')
    activa = models.BooleanField(default=True, help_text='Apagarla a mano: la app no la usa aunque funcione.')
    estado = models.CharField(max_length=15, choices=Estado.choices, default=Estado.SIN_VERIFICAR,
                              help_text='Lo pone la verificación automática. La app no usa las caídas.')
    verificada = models.DateTimeField('última verificación', null=True, blank=True)
    error = models.CharField('motivo de la falla', max_length=200, blank=True)
    # Cómo tiene que presentarse el reproductor para que el servidor del canal
    # entregue la señal. Vacío = el de siempre (verificacion.USER_AGENT_REPRODUCTOR).
    user_agent = models.CharField('User-Agent', max_length=300, blank=True,
                                  help_text='Solo si el canal lo exige (lo traen algunas listas M3U).')
    referer = models.CharField('Referer', max_length=500, blank=True,
                               help_text='Página desde la que "viene" el pedido, si el canal lo exige.')
    origen = models.CharField(max_length=150, blank=True, help_text='De qué lista se importó.')
    creado = models.DateTimeField(auto_now_add=True)

    # Lo que avisan los APARATOS (la app), aparte de la verificación del
    # servidor: hay señales que al servidor le responden pero en los aparatos
    # no se reproducen (formato de video que no leen, servidores que aceptan
    # una sola conexión...). Si varios aparatos avisan que falla, se oculta
    # unos días aunque el servidor la vea bien (ver servicios.registrar_falla_en_aparato).
    avisos_de_aparatos = models.PositiveSmallIntegerField(default=0)
    primer_aviso = models.DateTimeField(null=True, blank=True)
    falla_en_aparatos = models.CharField('motivo según los aparatos', max_length=200, blank=True)
    oculta_desde = models.DateTimeField('oculta por fallar en los aparatos desde', null=True, blank=True)

    class Meta:
        verbose_name = 'fuente'
        verbose_name_plural = 'fuentes'
        ordering = ['prioridad', 'pk']
        constraints = [
            models.UniqueConstraint(fields=['canal', 'url'], name='fuente_unica_por_canal'),
        ]

    def __str__(self):
        return f'{self.canal} · {self.get_tipo_display()} · {self.url[:60]}'

    def usable(self):
        """¿La app la puede usar?"""
        return self.activa and self.estado != self.Estado.CAIDA and not self.oculta_por_aparatos

    @property
    def oculta_por_aparatos(self):
        return self.oculta_desde is not None and self.oculta_desde > hace_dias_oculta()

    @property
    def vuelve_a_probarse(self):
        """Cuándo deja de estar oculta (y la app la vuelve a intentar)."""
        return self.oculta_desde + timedelta(days=DIAS_OCULTA) if self.oculta_desde else None


class Importacion(models.Model):
    """
    Una lista M3U subida desde el panel. Se analiza toda al subirla (rápido)
    y después se verifica de a tandas (TAMANIO_LOTE): la pantalla va pidiendo
    tanda por tanda y muestra el avance. Así una lista de miles de canales no
    traba el servidor, y si se cierra la página se puede seguir después.
    """
    archivo = models.CharField(max_length=150)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                related_name='+')
    creada = models.DateTimeField(auto_now_add=True)
    terminada = models.DateTimeField(null=True, blank=True)
    total = models.PositiveIntegerField(default=0)
    # Cuántas quedaron para verificar en esta ronda (sin las descartadas ni
    # repetidas al subirla): sobre esto se calcula el porcentaje de avance.
    para_verificar = models.PositiveIntegerField(default=0)
    # Lo que se eligió al subirla
    solo_espanol = models.BooleanField(default=False)
    descartar_sin_logo = models.BooleanField(default=False)
    descartar_vod = models.BooleanField('descartar películas y series', default=False)
    descartar_adultos = models.BooleanField('descartar contenido para adultos', default=True)

    class Meta:
        verbose_name = 'importación'
        verbose_name_plural = 'importaciones'
        ordering = ['-creada']

    def __str__(self):
        return f'{self.archivo} ({self.creada:%d/%m/%Y %H:%M})'


class EntradaImportada(models.Model):
    """Un canal de la lista importada y qué pasó con él (y por qué)."""

    class Estado(models.TextChoices):
        PENDIENTE = 'pendiente', 'Por verificar'
        AGREGADA = 'agregada', 'Agregada'
        CAIDA = 'caida', 'No funciona'
        DESCARTADA = 'descartada', 'Descartada'
        REPETIDA = 'repetida', 'Ya estaba'

    Contenido = Contenido

    importacion = models.ForeignKey(Importacion, on_delete=models.CASCADE, related_name='entradas')
    posicion = models.PositiveIntegerField()
    nombre_original = models.CharField(max_length=200, help_text='Como venía en la lista.')
    nombre = models.CharField(max_length=120, help_text='Limpio: sin prefijo de país ni calidad.')
    logo = models.CharField(max_length=500, blank=True)
    categoria = models.CharField(max_length=80, blank=True)
    numero = models.CharField(max_length=10, blank=True)
    tvg_id = models.CharField(max_length=120, blank=True)
    pais = models.CharField(max_length=2, blank=True)
    idioma = models.CharField(max_length=5, choices=Idioma.choices, blank=True)
    contenido = models.CharField(max_length=10, choices=Contenido.choices, default=Contenido.VIVO)
    url = models.CharField(max_length=1000)
    tipo = models.CharField('formato', max_length=10, blank=True)
    user_agent = models.CharField(max_length=300, blank=True)
    referer = models.CharField(max_length=500, blank=True)
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.PENDIENTE)
    motivo = models.CharField(max_length=200, blank=True)
    canal = models.ForeignKey(Canal, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')

    class Meta:
        verbose_name = 'entrada importada'
        verbose_name_plural = 'entradas importadas'
        ordering = ['posicion']
        indexes = [models.Index(fields=['importacion', 'estado', 'posicion'])]

    def __str__(self):
        return f'{self.nombre} · {self.get_estado_display()}'

    def get_tipo_display(self):
        return dict(Fuente.Tipo.choices).get(self.tipo) or ('RTMP' if self.tipo == 'rtmp' else 'Se averigua al verificar')
