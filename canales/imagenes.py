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
from PIL import Image, ImageOps, UnidentifiedImageError

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

    imagen = ImageOps.exif_transpose(imagen)   # las fotos de celular vienen "acostadas" con un dato aparte
    imagen.thumbnail((LADO_MAXIMO, LADO_MAXIMO))
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
    return imagen.mode in ('RGBA', 'LA') or (imagen.mode == 'P' and 'transparency' in imagen.info)


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
