"""
Ordenar el contenido desde el panel: las categorías y el tipo de cada cosa.

Las categorías salen solas del "group-title" de cada lista, así que con
varias listas se juntan muchas parecidas ("Deportes", "DEPORTES HD",
"Sports"). Acá se crean, renombran, juntan, borran y ordenan. Lo que se
junta o renombra NO se pierde: el nombre viejo queda en `otros_nombres`, y
la próxima lista que diga "Argentina" va directo a la categoría donde se
juntó "Argentina" (ver categoria_por_nombre, que usa la importación).

También se cambia el tipo (en vivo / película / serie) de lo que se importó
mal, y se pueden juntar películas sueltas como una serie numerada.

    from canales import organizar
    organizar.categoria_por_nombre('Argentina')                 -> Categoria (la crea si no existe)
    organizar.juntar_categorias([deportes, sports], 'Deportes') -> Categoria "Deportes"
    organizar.mover_a_categoria(canales, noticias)              -> cuántos se movieron
    organizar.cambiar_contenido(canales, 'serie', nombre_serie='Flash Gordon')
    organizar.categorias_parecidas()                            -> [[cat, cat], ...] posibles repetidas
"""

import re

from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from actividad.models import Accion
from actividad.registro import registrar

from . import clasificar
from .models import Canal, Categoria, Contenido


class NoSePuede(Exception):
    """Algo que se pidió no tiene sentido (se le muestra el mensaje a la persona)."""


def _clave(nombre):
    """Para comparar nombres: sin acentos, sin mayúsculas, sin espacios de más."""
    return ' '.join(clasificar.sin_acentos(nombre or '').split())


def _otros(categoria):
    return [n for n in (categoria.otros_nombres or '').splitlines() if n.strip()]


def _sumar_otros(categoria, nombres):
    """Agrega nombres a `otros_nombres` (sin repetir, ni el nombre actual)."""
    actuales = _otros(categoria)
    vistos = {_clave(n) for n in actuales} | {_clave(categoria.nombre)}
    for nombre in nombres:
        if nombre.strip() and _clave(nombre) not in vistos:
            actuales.append(nombre.strip())
            vistos.add(_clave(nombre))
    categoria.otros_nombres = '\n'.join(actuales)


def _usuario(usuario):
    return usuario if getattr(usuario, 'pk', None) else None


# ── Encontrar (o crear) una categoría por nombre ─────────────────────

def indice_de_categorias():
    """{nombre comparable: Categoria}, con sus nombres y sus otros nombres."""
    indice = {}
    for categoria in Categoria.objects.all():
        for nombre in [categoria.nombre, *_otros(categoria)]:
            indice.setdefault(_clave(nombre), categoria)
    for categoria in Categoria.objects.all():   # el nombre propio manda sobre un "otro nombre" de otra
        indice[_clave(categoria.nombre)] = categoria
    return indice


def categoria_por_nombre(nombre, indice=None, usuario=None):
    """
    La categoría que se llama así (sin importar mayúsculas ni acentos) o que
    lo tiene entre sus otros nombres. Si no hay ninguna, la crea. `indice`:
    el de indice_de_categorias(), para no consultarlo cada vez (se actualiza solo).
    """
    nombre = ' '.join((nombre or '').split())[:80]
    if not nombre:
        return None
    if indice is None:
        indice = indice_de_categorias()
    categoria = indice.get(_clave(nombre))
    if categoria is None:
        categoria = Categoria(nombre=nombre)
        categoria.marcar_autor(usuario)
        categoria.save()
        indice[_clave(nombre)] = categoria
    return categoria


# ── Las categorías ───────────────────────────────────────────────────

def categorias_con_cantidades():
    """Todas las categorías con cuántos canales, películas y capítulos tienen (sin contar lo borrado)."""
    vivos = Q(canales__eliminado_en__isnull=True)
    return Categoria.objects.annotate(
        en_vivo=Count('canales', filter=vivos & Q(canales__contenido=Contenido.VIVO)),
        peliculas=Count('canales', filter=vivos & Q(canales__contenido=Contenido.PELICULA)),
        capitulos=Count('canales', filter=vivos & Q(canales__contenido=Contenido.SERIE)),
        total=Count('canales', filter=vivos),
    ).order_by('orden', 'nombre')


def crear_categoria(nombre, usuario=None):
    nombre = ' '.join((nombre or '').split())[:80]
    if not nombre:
        raise NoSePuede('Escribí el nombre de la categoría.')
    if _clave(nombre) in indice_de_categorias():
        raise NoSePuede(f'Ya hay una categoría "{nombre}" (o una que se llamaba así).')
    categoria = categoria_por_nombre(nombre, usuario=usuario)
    registrar(usuario, Accion.CREAR, f'Creó la categoría "{categoria}".', objeto=categoria, modulo='canales')
    return categoria


@transaction.atomic
def renombrar_categoria(categoria, nuevo, usuario=None):
    """
    Le cambia el nombre (el viejo queda como "otro nombre": las listas que lo
    traigan siguen yendo acá). Si ya hay otra con el nombre nuevo, se juntan.
    """
    nuevo = ' '.join((nuevo or '').split())[:80]
    if not nuevo:
        raise NoSePuede('Escribí el nombre nuevo.')
    otra = Categoria.objects.exclude(pk=categoria.pk).filter(nombre__iexact=nuevo).first()
    if otra is None:
        otra = next((c for c in Categoria.objects.exclude(pk=categoria.pk)
                     if _clave(c.nombre) == _clave(nuevo)), None)
    if otra is not None:
        return juntar_categorias([categoria, otra], otra.nombre, usuario)
    viejo = categoria.nombre
    categoria.nombre = nuevo
    _sumar_otros(categoria, [viejo])
    categoria.marcar_autor(usuario)
    categoria.save()
    registrar(usuario, Accion.EDITAR, f'Renombró la categoría "{viejo}" a "{nuevo}".', objeto=categoria,
              modulo='canales')
    return categoria


@transaction.atomic
def juntar_categorias(categorias, destino, usuario=None):
    """
    Pasa todo lo de `categorias` a la categoría `destino` (un nombre: puede
    ser una de ellas, otra que ya existe o una nueva) y borra las demás. Sus
    nombres quedan como "otros nombres" del destino.
    """
    categorias = [c for c in categorias if c is not None]
    if len(categorias) < 2 and not (categorias and _clave(destino) != _clave(categorias[0].nombre)):
        raise NoSePuede('Elegí al menos dos categorías para juntar (o una y otro nombre de destino).')
    destino_nombre = ' '.join((destino or '').split())[:80]
    if not destino_nombre:
        raise NoSePuede('Escribí o elegí en qué categoría juntarlas.')
    final = next((c for c in categorias if _clave(c.nombre) == _clave(destino_nombre)), None)
    if final is None:
        final = (Categoria.objects.filter(nombre__iexact=destino_nombre).first()
                 or categoria_por_nombre(destino_nombre, usuario=usuario))
    juntadas = []
    for categoria in categorias:
        if categoria.pk == final.pk:
            continue
        Canal.todos.filter(categoria=categoria).update(categoria=final, modificado=timezone.now())
        _sumar_otros(final, [categoria.nombre, *_otros(categoria)])
        categoria.eliminar(usuario)
        juntadas.append(categoria.nombre)
    if final.nombre != destino_nombre and _clave(final.nombre) == _clave(destino_nombre):
        final.nombre = destino_nombre   # mismo nombre con otras mayúsculas: queda como lo escribió
    final.marcar_autor(usuario)
    final.save()
    if juntadas:
        registrar(usuario, Accion.EDITAR, f'Juntó las categorías {", ".join(juntadas)} en "{final}".',
                  objeto=final, modulo='canales')
    return final


@transaction.atomic
def borrar_categoria(categoria, usuario=None):
    """La borra: lo que tenía queda "Sin categoría" (en la app, en "Otros"). Devuelve cuántos tenía."""
    cantidad = Canal.todos.filter(categoria=categoria).update(categoria=None, modificado=timezone.now())
    categoria.eliminar(usuario)
    registrar(usuario, Accion.ELIMINAR, f'Borró la categoría "{categoria}" ({cantidad} quedaron sin categoría).',
              objeto=categoria, modulo='canales')
    return cantidad


def ordenar_categorias(ordenes, usuario=None):
    """{pk: orden} -> guarda el orden (menor = aparece primero en la app). Devuelve cuántas cambiaron."""
    cambiadas = 0
    for categoria in Categoria.objects.filter(pk__in=list(ordenes)):
        orden = max(0, int(ordenes[categoria.pk]))
        if categoria.orden != orden:
            categoria.orden = orden
            categoria.marcar_autor(usuario)
            categoria.save(update_fields=['orden', 'modificado', 'modificado_por'])
            cambiadas += 1
    if cambiadas:
        registrar(usuario, Accion.EDITAR, f'Cambió el orden de {cambiadas} categoría(s).', modulo='canales')
    return cambiadas


# Para sugerir categorías repetidas: palabras que no cambian de qué se trata,
# y nombres en inglés que son lo mismo que uno en castellano.
_RELLENO = {'hd', 'fhd', 'uhd', 'sd', '4k', 'tv', 'canal', 'canales', 'channel', 'channels', 'vod', 'de', 'del',
            'y', 'and', 'the', 'la', 'las', 'los', 'el', 'en', 'vivo', 'live', '24', '7', 'h', 'ar', 'arg', 'es',
            'mx', 'co', 'cl', 'pe', 'us', 'usa', 'uk', 've', 'uy', 'py', 'bo', 'ec', 'latam', 'latino', 'latin'}
_SINONIMOS = {'kids': 'infantil', 'kid': 'infantil', 'ninos': 'infantil', 'nino': 'infantil', 'infantiles': 'infantil',
              'sports': 'deporte', 'sport': 'deporte', 'deportes': 'deporte', 'deportivo': 'deporte',
              'news': 'noticia', 'noticias': 'noticia', 'informativo': 'noticia', 'movies': 'pelicula',
              'movie': 'pelicula', 'peliculas': 'pelicula', 'cine': 'pelicula', 'films': 'pelicula',
              'music': 'musica', 'musical': 'musica', 'documentary': 'documental', 'documentales': 'documental',
              'entertainment': 'entretenimiento', 'series': 'serie', 'religious': 'religion', 'religiosos': 'religion',
              'religioso': 'religion', 'cultura': 'cultural', 'culture': 'cultural', 'general': 'general',
              'animation': 'infantil', 'animacion': 'infantil', 'dibujos': 'infantil', 'comedy': 'comedia',
              'novelas': 'novela', 'telenovelas': 'novela', 'telenovela': 'novela'}


def clave_parecida(nombre):
    """'DEPORTES HD' / 'Sports' / 'AR | Deportes' -> 'deporte'. '' si no queda nada que comparar."""
    palabras = re.split(r'[^a-z0-9]+', clasificar.sin_acentos(nombre or ''))
    utiles = []
    for palabra in palabras:
        if not palabra or palabra in _RELLENO:
            continue
        palabra = _SINONIMOS.get(palabra, palabra)
        if len(palabra) > 4 and palabra.endswith('s') and palabra not in ('series',):
            palabra = palabra[:-1]
        if palabra not in utiles:
            utiles.append(palabra)
    return ' '.join(sorted(utiles))


def categorias_parecidas(categorias=None):
    """Grupos de categorías que parecen la misma ([[Deportes, DEPORTES HD, Sports], ...])."""
    grupos = {}
    for categoria in categorias if categorias is not None else categorias_con_cantidades():
        clave = clave_parecida(categoria.nombre)
        if clave:
            grupos.setdefault(clave, []).append(categoria)
    return [grupo for grupo in grupos.values() if len(grupo) > 1]


# ── Mover y cambiar de tipo ──────────────────────────────────────────

def mover_a_categoria(canales, categoria, usuario=None):
    """Pone los canales (películas, capítulos...) en `categoria` (None = sin categoría). Devuelve cuántos."""
    cantidad = canales.exclude(categoria=categoria).update(
        categoria=categoria, modificado=timezone.now(), modificado_por=_usuario(usuario))
    if cantidad:
        registrar(usuario, Accion.EDITAR,
                  f'Movió {cantidad} canal(es) a la categoría "{categoria or "Sin categoría"}".', modulo='canales')
    return cantidad


def _orden_natural(texto):
    """'Capítulo 10' va después de 'Capítulo 9' (los números se comparan como números)."""
    return [int(parte) if parte.isdigit() else parte for parte in re.split(r'(\d+)', clasificar.sin_acentos(texto))]


def _titulo_del_capitulo(nombre, nombre_serie):
    """Lo que queda del nombre para usarlo como título del capítulo (sin la serie ni "S01 E02")."""
    serie, _, _, titulo = clasificar.episodio(nombre)
    titulo = titulo if titulo or serie != nombre else nombre
    titulo = re.sub(re.escape(nombre_serie), ' ', titulo, flags=re.I)
    titulo = re.sub(r'\(\s*\d{4}\s*\)', ' ', titulo)
    return ' '.join(titulo.split()).strip(' -:|.')


@transaction.atomic
def cambiar_contenido(canales, contenido, nombre_serie='', temporada=1, usuario=None):
    """
    Cambia el tipo (en vivo / película / serie) de los elegidos.

    A serie con `nombre_serie`: además los renombra como capítulos de esa
    serie, numerados en el orden de sus nombres ("Flash Gordon S01 E01
    El planeta del peligro"...), para que la app los arme como una serie.
    A serie sin nombre: solo cambia el tipo; la app los agrupa por el nombre
    ("Arrow S02 E05"), así que tienen que decir temporada y capítulo.

    Devuelve (cuántos cambiaron, cuántos quedaron como serie sin "S01 E01" en el nombre).
    """
    if contenido not in Contenido.values:
        raise NoSePuede('Tipo de contenido desconocido.')
    nombre_serie = ' '.join((nombre_serie or '').split())[:90]
    elegidos = sorted(canales, key=lambda c: _orden_natural(c.nombre))
    if not elegidos:
        return 0, 0
    ahora, quien = timezone.now(), _usuario(usuario)
    for numero, canal in enumerate(elegidos, start=1):
        canal.contenido = contenido
        if contenido == Contenido.SERIE and nombre_serie:
            titulo = _titulo_del_capitulo(canal.nombre, nombre_serie)
            canal.nombre = f'{nombre_serie} S{int(temporada):02d} E{numero:02d}{f" {titulo}" if titulo else ""}'[:120]
        canal.modificado, canal.modificado_por = ahora, quien
    Canal.objects.bulk_update(elegidos, ['contenido', 'nombre', 'modificado', 'modificado_por'])
    sin_numero = 0
    if contenido == Contenido.SERIE and not nombre_serie:
        sin_numero = sum(1 for c in elegidos if clasificar.episodio(c.nombre)[2] is None)
    detalle = f' como la serie "{nombre_serie}" (temporada {temporada})' if nombre_serie else ''
    registrar(usuario, Accion.EDITAR, f'Pasó {len(elegidos)} a {Contenido(contenido).label.lower()}{detalle}.',
              modulo='canales')
    return len(elegidos), sin_numero


def capitulos_de(nombres_de_series):
    """Los capítulos (Canal) de esas series, por nombre de serie (como las arma la app)."""
    buscados = {_clave(n) for n in nombres_de_series if n.strip()}
    pks = [canal.pk for canal in Canal.objects.filter(contenido=Contenido.SERIE).only('pk', 'nombre')
           if _clave(clasificar.episodio(canal.nombre)[0]) in buscados]
    return Canal.objects.filter(pk__in=pks)
