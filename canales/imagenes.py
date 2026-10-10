"""
Las imágenes que se ponen a mano desde el panel: logos y pósters subidos
desde la compu, y la portada propia de cada serie.

Subidas: se achican (como mucho LADO_MAXIMO de lado), se guardan en
media/canales/imagenes/ con un nombre al azar y lo que queda en `logo` es su
dirección completa (https://.../media/canales/imagenes/....jpg), igual que un
link pegado: la app las carga directo, como cualquier otra. Son fotos, no
video (el video nunca pasa por el servidor).

    from canales import imagenes
    imagenes.guardar_subida(archivo, request)          -> 'https://.../media/canales/imagenes/ab12.jpg'
    imagenes.soltar(url_vieja)                         -> borra el archivo si era subido y ya nadie lo usa
    imagenes.portada_de('Pocoyó')                      -> '' si no tiene
    imagenes.portadas_de(['Pocoyó', 'Masha'])          -> {'Pocoyó': 'https://...'}  (solo las que tienen)
    imagenes.poner_portada('Pocoyó', url)              -> '' la saca (vuelve a la del primer capítulo)
    imagenes.mover_portada('Pocoyo', 'Pocoyó')         -> al renombrar o unir series
"""

import uuid
from io import BytesIO

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from PIL import Image, ImageChops, ImageDraw, ImageOps, UnidentifiedImageError

from . import clasificar
from .models import Canal, PortadaDeSerie

CARPETA = 'canales/imagenes/'
PESO_MAXIMO = 8 * 1024 * 1024   # 8 MB: una foto de celular entra de sobra
LADO_MAXIMO = 1600              # alcanza para la vidriera de la TV (1920 de ancho, con margen)
FORMATOS = {'JPEG', 'PNG', 'WEBP', 'GIF'}


class ImagenInvalida(Exception):
    """El archivo no sirve como imagen (se le muestra el mensaje a la persona)."""


def guardar_subida(archivo, request):
    """Guarda la imagen subida (achicada) y devuelve su dirección completa."""
    if archivo.size > PESO_MAXIMO:
        raise ImagenInvalida(f'La imagen pesa {archivo.size / 1024 / 1024:.0f} MB: como mucho '
                             f'{PESO_MAXIMO // 1024 // 1024} MB.')
    try:
        imagen = Image.open(archivo)
        formato = imagen.format
        imagen.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise ImagenInvalida('Ese archivo no es una imagen (tiene que ser JPG, PNG o WEBP).') from None
    if formato not in FORMATOS:
        raise ImagenInvalida(f'Las imágenes {formato} no se aceptan: tiene que ser JPG, PNG o WEBP.')

    if _tiene_transparencia(imagen):
        imagen = imagen.convert('RGBA')        # antes de girarla: si no, se pierde lo transparente
    imagen = ImageOps.exif_transpose(imagen)   # las fotos de celular vienen "acostadas" con un dato aparte
    imagen.thumbnail((LADO_MAXIMO, LADO_MAXIMO))
    imagen = sacar_cuadritos(imagen)
    salida = BytesIO()
    if _tiene_transparencia(imagen):
        # Un logo con fondo transparente: PNG, para que no quede un recuadro negro
        imagen.convert('RGBA').save(salida, 'PNG', optimize=True)
        extension = 'png'
    else:
        imagen.convert('RGB').save(salida, 'JPEG', quality=85, optimize=True)
        extension = 'jpg'
    nombre = default_storage.save(f'{CARPETA}{uuid.uuid4().hex}.{extension}', ContentFile(salida.getvalue()))
    return request.build_absolute_uri(default_storage.url(nombre))


def _tiene_transparencia(imagen):
    return imagen.mode in ('RGBA', 'LA', 'PA') or 'transparency' in imagen.info


# ── El fondo "de cuadritos" falso ────────────────────────────────────
# Muchos "PNG sin fondo" que se bajan de internet NO son transparentes: tienen
# los cuadritos grises y blancos pintados (son parte de la imagen). Se
# reconocen en el borde: dos grises que se alternan una y otra vez. Ese fondo
# (lo que está pegado al borde y es de esos dos grises) pasa a transparente.

TOLERANCIA = 8           # cuánto puede variar cada gris (compresión JPG)
MINIMO_DE_CAMBIOS = 6    # cuántas veces tienen que alternarse en un lado para ser cuadritos


def sacar_cuadritos(imagen):
    """La imagen con el fondo de cuadritos pintado vuelto transparente (o la misma, si no lo tiene)."""
    grises = _grises_de_cuadritos(imagen)
    if grises is None:
        return imagen
    imagen = imagen.convert('RGBA')
    ancho, alto = imagen.size
    # Los puntos que son de alguno de los dos grises (sin color)
    luz = imagen.convert('L')
    parecidos = luz.point(lambda v: 255 if any(abs(v - g) <= TOLERANCIA for g in grises) else 0)
    sin_color = imagen.convert('RGB').convert('HSV').getchannel('S').point(lambda v: 255 if v <= 24 else 0)
    candidatos = ImageChops.multiply(parecidos, sin_color)
    # De esos, solo los pegados al borde (el fondo): un gris adentro del logo se queda
    for x, y in _borde(ancho, alto):
        if candidatos.getpixel((x, y)) == 255:
            ImageDraw.floodfill(candidatos, (x, y), 128, thresh=0)
    fondo = candidatos.point(lambda v: 255 if v == 128 else 0)
    imagen.putalpha(ImageChops.subtract(imagen.getchannel('A'), fondo))
    return imagen


def _borde(ancho, alto):
    yield from ((x, y) for y in (0, alto - 1) for x in range(ancho))
    yield from ((x, y) for x in (0, ancho - 1) for y in range(1, alto - 1))


def _grises_de_cuadritos(imagen):
    """Los dos grises del fondo de cuadritos, si el borde lo tiene; si no, None."""
    if imagen.width < 16 or imagen.height < 16:
        return None
    rgba = imagen.convert('RGBA')
    lados = [
        [rgba.getpixel((x, 0)) for x in range(rgba.width)],
        [rgba.getpixel((x, rgba.height - 1)) for x in range(rgba.width)],
        [rgba.getpixel((0, y)) for y in range(rgba.height)],
        [rgba.getpixel((rgba.width - 1, y)) for y in range(rgba.height)],
    ]
    puntos = [p for lado in lados for p in lado]
    # Grises opacos (lo transparente de verdad no cuenta: esa imagen ya está bien)
    grises = [p[0] for p in puntos if p[3] == 255 and max(p[:3]) - min(p[:3]) <= 12]
    if len(grises) < len(puntos) * 0.8:
        return None
    # Los dos tonos más comunes, separados entre sí
    cuantos = {}
    for g in grises:
        cuantos[g // 4] = cuantos.get(g // 4, 0) + 1
    tonos = sorted(cuantos, key=cuantos.get, reverse=True)
    primero = tonos[0] * 4 + 2
    segundo = next((t * 4 + 2 for t in tonos[1:] if abs(t * 4 + 2 - primero) > 2 * TOLERANCIA), None)
    if segundo is None:
        return None
    de_cada_uno = [sum(1 for g in grises if abs(g - tono) <= TOLERANCIA) for tono in (primero, segundo)]
    if min(de_cada_uno) < len(puntos) * 0.2 or sum(de_cada_uno) < len(puntos) * 0.75:
        return None
    # Y que se alternen a lo largo de los lados (cuadritos, no dos franjas)
    def cambios(lado):
        tonos_del_lado = [0 if abs(p[0] - primero) <= TOLERANCIA else 1 if abs(p[0] - segundo) <= TOLERANCIA else None
                          for p in lado]
        conocidos = [t for t in tonos_del_lado if t is not None]
        return sum(1 for a, b in zip(conocidos, conocidos[1:]) if a != b)
    if sum(1 for lado in lados if cambios(lado) >= MINIMO_DE_CAMBIOS) < 2:
        return None
    return primero, segundo


def _archivo_subido(url):
    """El nombre en media/ si `url` es una imagen subida acá ('' si es un link de afuera)."""
    marca = f'{settings.MEDIA_URL}{CARPETA}'
    if marca not in (url or ''):
        return ''
    return CARPETA + url.split(marca, 1)[1].split('?')[0]


def soltar(url):
    """Si `url` era una imagen subida y ya no la usa nadie, borra el archivo (no se acumulan)."""
    nombre = _archivo_subido(url)
    if not nombre or '/' in nombre[len(CARPETA):] or '..' in nombre:
        return
    if Canal.todos.filter(logo=url).exists() or PortadaDeSerie.objects.filter(imagen=url).exists():
        return
    default_storage.delete(nombre)


# ── Portadas de series ───────────────────────────────────────────────

def _clave(nombre):
    """Como organizar._clave: sin acentos, sin mayúsculas, sin espacios de más."""
    return ' '.join(clasificar.sin_acentos(nombre or '').split())[:90]


def portada_de(nombre):
    return PortadaDeSerie.objects.filter(clave=_clave(nombre)).values_list('imagen', flat=True).first() or ''


def portadas_de(nombres):
    """{nombre: imagen} de las series de `nombres` que tienen portada (con el nombre tal como vino)."""
    por_clave = {}
    for nombre in nombres:
        por_clave.setdefault(_clave(nombre), []).append(nombre)
    resultado = {}
    for clave, imagen in PortadaDeSerie.objects.filter(clave__in=por_clave).values_list('clave', 'imagen'):
        for nombre in por_clave[clave]:
            resultado[nombre] = imagen
    return resultado


def poner_portada(nombre, imagen):
    """Le pone (o cambia) la portada a la serie; con `imagen` vacía se la saca. Devuelve True si cambió."""
    clave = _clave(nombre)
    actual = PortadaDeSerie.objects.filter(clave=clave).first()
    vieja = actual.imagen if actual else ''
    if vieja == imagen:
        return False
    if not imagen:
        actual.delete()
    elif actual:
        actual.imagen, actual.nombre = imagen, nombre[:90]
        actual.save()
    else:
        PortadaDeSerie.objects.create(clave=clave, nombre=nombre[:90], imagen=imagen)
    soltar(vieja)
    return True


def mover_portada(viejo, nuevo):
    """
    Al renombrar una serie (o unirla con otra), la portada va con ella. Si la
    de destino ya tenía una, queda la del destino.
    """
    origen = PortadaDeSerie.objects.filter(clave=_clave(viejo)).first()
    if origen is None or _clave(viejo) == _clave(nuevo):
        if origen is not None:
            origen.nombre = nuevo[:90]
            origen.save()
        return
    if PortadaDeSerie.objects.filter(clave=_clave(nuevo)).exists():
        imagen = origen.imagen
        origen.delete()
        soltar(imagen)
        return
    origen.clave, origen.nombre = _clave(nuevo), nuevo[:90]
    origen.save()
