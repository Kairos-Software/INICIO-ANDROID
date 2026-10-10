"""
Películas y capítulos de canales OFICIALES de YouTube (Movie Central, Peppa
Pig, Bluey...): los dueños los suben gratis con publicidad y dejan que se
inserten en otras páginas y apps. Capa Base, no toca la base de datos.

    videos_del_canal('https://www.youtube.com/@MovieCentralEspanol')
        -> Listado(nombre='Movie Central - ...', videos=[Video(id, titulo, segundos), ...])
    verificar_video('https://www.youtube.com/watch?v=...')   -> Resultado(FUNCIONA, tipo='yt_video')
    genero('Lo Atacaron de Noche | Terror')                   -> 'Terror'
    titulo_limpio('Búnker de Venganza | Película Completa De Acción En Español Latino') -> 'Búnker de Venganza'

Estas fuentes son del tipo "yt_video": la app NO saca el video de YouTube
(como con los vivos, tipo "youtube"), lo muestra en el reproductor oficial
de YouTube, con su logo y su publicidad. Así lo permite YouTube, se ve en
alta calidad, anda lo infantil (que no se puede sacar) y no hace falta cuenta.

Para verificar se usa oEmbed, lo mismo que usan las páginas para insertar un
video: es rápido, a los servidores no los bloquean y dice si el dueño deja
verlo fuera de YouTube.
"""

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from urllib.parse import parse_qs, quote, urlsplit

from .clasificar import sin_acentos
from .verificacion import CAIDA, FUNCIONA, SIN_VERIFICAR, TIEMPO_MAXIMO, Resultado

TIPO = 'yt_video'

# Canales oficiales revisados el 2026-10-08 (verificados por YouTube, dejan
# insertar sus videos, en español): (nombre, link, categoría, minutos mínimos, serie).
# Categoría vacía = según el género de cada título. Con serie: todos sus
# videos son capítulos de esa serie (y la categoría es de Series).
SUGERIDOS = (
    ('Movie Central Español', 'https://www.youtube.com/@MovieCentralEspanol', '', 60, ''),
    ('V Español', 'https://www.youtube.com/channel/UCH6uKFPQcZLihwbnzxnw1dA', '', 60, ''),
    ('Peppa Pig Español Latino', 'https://www.youtube.com/channel/UCrreHSUa5rnuCVDeO8dX4eA', 'Series Infantiles', 20,
     'Peppa Pig'),
    ('Bluey Español', 'https://www.youtube.com/channel/UCYvpkMpzo1S_rmcj2Axmbig', 'Series Infantiles', 20, 'Bluey'),
    ('PAW Patrol en Español', 'https://www.youtube.com/channel/UCJNBZaQWMIHACqvHT_k2cWw', 'Series Infantiles', 20,
     'Paw Patrol'),
    ('Masha y el Oso', 'https://www.youtube.com/channel/UCuSo4gcgxJRf4Bzu43wwVyg', 'Series Infantiles', 20,
     'Masha y el Oso'),
    ('Pocoyó Español', 'https://www.youtube.com/channel/UCnB5W_ZJgiDFnklejRGADxw', 'Series Infantiles', 20, 'Pocoyó'),
    ('Plim Plim', 'https://www.youtube.com/channel/UCYQo8CdhXD22qfwUBUw591Q', 'Series Infantiles', 20, 'Plim Plim'),
)
_ID = re.compile(r'^[\w-]{11}$')


@dataclass
class Video:
    id: str
    titulo: str
    segundos: int = 0

    @property
    def url(self):
        return direccion(self.id)

    @property
    def imagen(self):
        # hqdefault existe siempre (maxresdefault no en todos los videos)
        return f'https://i.ytimg.com/vi/{self.id}/hqdefault.jpg'


@dataclass
class Listado:
    nombre: str
    videos: list = field(default_factory=list)
    # Un canal da sus videos del más nuevo al más viejo; una lista de
    # reproducción, en el orden que le puso su dueño (casi siempre el de los capítulos)
    nuevos_primero: bool = True

    def en_orden(self):
        """Los videos del primero (el más viejo, o el 1 de la lista) al último: el orden de los capítulos."""
        return list(reversed(self.videos)) if self.nuevos_primero else list(self.videos)


class NoSePudo(Exception):
    """No se pudo leer el canal (el mensaje dice por qué, en castellano)."""


def direccion(video_id):
    return f'https://www.youtube.com/watch?v={video_id}'


def id_de_video(url):
    """'https://www.youtube.com/watch?v=abc' o 'https://youtu.be/abc' -> 'abc' (None si no es un video)."""
    partes = urlsplit(url or '')
    host = (partes.hostname or '').lower()
    candidato = ''
    if host.endswith('youtu.be'):
        candidato = partes.path.strip('/').split('/')[0]
    elif host.endswith('youtube.com') or host.endswith('youtube-nocookie.com'):
        if partes.path == '/watch':
            candidato = (parse_qs(partes.query).get('v') or [''])[0]
        elif re.match(r'^/(embed|shorts|live)/', partes.path):
            candidato = partes.path.split('/')[2]
    return candidato if _ID.match(candidato) else None


# ── Traer los videos de un canal ─────────────────────────────────────

def _direccion_del_listado(url):
    """Un canal entero -> su pestaña "Videos" (sin los Shorts ni los vivos). Una lista de reproducción, tal cual."""
    url = (url or '').strip()
    partes = urlsplit(url if '://' in url else f'https://{url}')
    if not (partes.hostname or '').lower().endswith('youtube.com'):
        raise NoSePudo('Pegá el link de un canal de YouTube (youtube.com/@canal) o de una lista de reproducción.')
    if partes.path == '/playlist':
        return f'https://www.youtube.com/playlist?{partes.query}'
    ruta = partes.path.rstrip('/')
    if not re.match(r'^/(@[^/]+|channel/[^/]+|c/[^/]+|user/[^/]+)', ruta):
        raise NoSePudo('Pegá el link de un canal de YouTube (youtube.com/@canal) o de una lista de reproducción.')
    base = re.match(r'^/(@[^/]+|channel/[^/]+|c/[^/]+|user/[^/]+)', ruta).group(0)
    return f'https://www.youtube.com{base}/videos'


def videos_del_canal(url):
    """
    Los videos de un canal (o de una lista de reproducción), del más nuevo al
    más viejo: solo los datos (título y duración), no baja ningún video.
    Con miles de videos tarda hasta un minuto.
    """
    import yt_dlp   # se importa recién acá: tarda en cargar
    # lang=es: si no, YouTube devuelve los títulos traducidos solo al inglés
    # ("Summer in Venice - Episode 123" en vez de "Verano en Venecia - Capítulo 123")
    opciones = {'quiet': True, 'no_warnings': True, 'skip_download': True, 'extract_flat': 'in_playlist',
                'socket_timeout': 20, 'logger': _Silencio(), 'extractor_args': {'youtube': {'lang': ['es']}}}
    direccion_del_listado = _direccion_del_listado(url)
    try:
        with yt_dlp.YoutubeDL(opciones) as ytdl:
            informacion = ytdl.extract_info(direccion_del_listado, download=False) or {}
    except NoSePudo:
        raise
    except Exception as error:   # yt-dlp lanza sus propias excepciones
        raise NoSePudo(f'YouTube no entregó la lista de videos ({str(error).replace("ERROR: ", "")[:150]}). Si pasa '
                       f'con todos los canales, YouTube cambió algo: hay que actualizar yt-dlp en el servidor '
                       f'(ver despliegue/README.md).') from error
    videos = [Video(e['id'], (e.get('title') or '').strip(), int(e.get('duration') or 0))
              for e in informacion.get('entries') or []
              if e and _ID.match(e.get('id') or '')]
    if not videos:
        raise NoSePudo('El canal no tiene videos (o es privado).')
    nombre = informacion.get('channel') or informacion.get('uploader') or informacion.get('title') or 'YouTube'
    return Listado(nombre=re.sub(r'\s+-\s+Videos$', '', nombre).strip(), videos=videos,
                   nuevos_primero='/playlist?' not in direccion_del_listado)


class _Silencio:
    def debug(self, mensaje):
        pass

    warning = info = error = debug


# ── Verificar que se pueda ver ───────────────────────────────────────

def verificar_video(url):
    """¿El video existe y el dueño deja verlo fuera de YouTube? (sin cuenta ni restricción de privacidad)."""
    video_id = id_de_video(url)
    if not video_id:
        return Resultado(CAIDA, 'No es la dirección de un video de YouTube.', tipo=TIPO)
    pedido = urllib.request.Request(
        f'https://www.youtube.com/oembed?format=json&url={quote(direccion(video_id), safe="")}',
        headers={'User-Agent': 'Mozilla/5.0', 'Accept-Language': 'es'},
    )
    try:
        with urllib.request.urlopen(pedido, timeout=TIEMPO_MAXIMO) as respuesta:
            datos = json.loads(respuesta.read(200_000) or b'{}')
    except urllib.error.HTTPError as error:
        if error.code in (401, 403):
            return Resultado(CAIDA, 'El dueño no deja verlo fuera de YouTube.', tipo=TIPO)
        if error.code in (400, 404):
            return Resultado(CAIDA, 'El video ya no existe o es privado.', tipo=TIPO)
        return Resultado(SIN_VERIFICAR, f'YouTube respondió {error.code} al verificarlo.', tipo=TIPO)
    except (OSError, ValueError) as error:
        return Resultado(SIN_VERIFICAR, f'No se pudo verificar ({str(error)[:100]}).', tipo=TIPO)
    return Resultado(FUNCIONA, tipo=TIPO, titulo=(datos.get('title') or '')[:120],
                     imagen=f'https://i.ytimg.com/vi/{video_id}/hqdefault.jpg')


# ── Nombre y género a partir del título ──────────────────────────────

# Lo que dice el título -> la categoría (se queda con lo que aparece primero:
# "Comedia de Terror" es Comedia)
GENEROS = (
    (r'accion|action', 'Acción'),
    (r'terror|horror|miedo', 'Terror'),
    (r'suspenso|suspense|thriller|misterio', 'Suspenso'),
    (r'comedia|comedy', 'Comedia'),
    (r'romance|romantic[ao]|romantic|amor', 'Romance'),
    (r'ciencia ficcion|sci-?fi', 'Ciencia ficción'),
    (r'animacion|animad[ao]|dibujos', 'Animación'),
    (r'familiar|familia|family', 'Familiar'),
    (r'western|vaquer[oa]s?|spaghetti', 'Western'),
    (r'aventura', 'Aventura'),
    (r'belic[ao]|guerra', 'Bélica'),
    (r'policial|crimen', 'Policial'),
    (r'documental', 'Documental'),
    (r'navidad|navidena?o?', 'Navidad'),
    (r'drama|biografic[ao]', 'Drama'),
)
_GENEROS = [(re.compile(rf'\b(?:{patron})\b'), nombre) for patron, nombre in GENEROS]

# Pedazos del título que no son el nombre de la película (se descartan enteros)
_RELLENO = re.compile(
    r'pel[ií]cula|completa|full movie|movie|espa[ñn]ol|spanish|latino|subtitulad|\bhd\b|4k|1080|estreno|'
    r'canal oficial|official channel|episodios? completos?|compilaci[oó]n|recopilaci[oó]n|colecci[oó]n|'
    r'nuevo (cap[ií]tulo|episodio)|canciones infantiles',
    re.I,
)
# ...y frases de relleno dentro de un pedazo ("[119 min]", "CARICATURAS y DIBUJOS ANIMADOS para niños")
_FRASES_DE_RELLENO = re.compile(
    r'\[[^\]]*\]|\(\s*\d+\s*min[^)]*\)|(caricaturas y )?dibujos animados( para ni[ñn]os)?|para ni[ñn]os',
    re.I,
)
# "in English", o "Full Movie" sin decir que está en español
_EN_INGLES = re.compile(r'\b(in english|english version|en ingl[eé]s)\b|\|\s*english\b', re.I)
_FULL_MOVIE = re.compile(r'\bfull (\w+ )?movies?\b', re.I)
_DICE_ESPANOL = re.compile(r'spanish|espa[ñn]ol|latino|castellano', re.I)
_EMOJIS = re.compile('[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\uFE0F\u200D]+')


def genero(titulo):
    """La categoría que sugiere el título ('' si no dice ninguna)."""
    texto = sin_acentos(titulo)
    encontrados = [(m.start(), nombre) for patron, nombre in _GENEROS for m in [patron.search(texto)] if m]
    return min(encontrados)[1] if encontrados else ''


def en_ingles(titulo):
    """El título dice que está en inglés (o es "Full Movie" sin decir que está en español)."""
    titulo = titulo or ''
    return bool(_EN_INGLES.search(titulo) or (_FULL_MOVIE.search(titulo) and not _DICE_ESPANOL.search(titulo)))


def titulo_limpio(titulo, evitar=()):
    """
    El nombre de la película, sin "| Película Completa en Español", emojis ni
    el género. `evitar`: pedazos que no sirven de nombre (en minúsculas), como
    "masha y el oso" en un canal donde todos los títulos empiezan así.
    """
    # Los emojis, "|" y " - " separan pedazos: "Peppa Pig en Español ⭐️ EL ESPECTÁCULO..." -> 2 pedazos
    separado = _EMOJIS.sub('|', titulo or '')
    partes = [re.sub(r'\s+', ' ', _FRASES_DE_RELLENO.sub('', p)).strip(' -–·!¡:')
              for p in re.split(r'[|｜]|\s[-–]\s', separado)]
    partes = [p for p in partes if p]
    utiles = [p for p in partes if not _RELLENO.search(p) and not _es_solo_genero(p)]
    nombre = next((p for p in utiles if p.casefold() not in evitar), None) or (utiles or partes or [''])[0]
    letras = [c for c in nombre if c.isalpha()]
    if letras and all(c.isupper() for c in letras) and len(letras) > 3:
        nombre = nombre.capitalize()   # "ASESINO AMERICANO" -> "Asesino americano"
    return nombre[:120]


_TEMPORADA = re.compile(r'\b(?:T|temporada\s*)(\d{1,2})\b', re.I)
_NUMERO = re.compile(r'\b(?:E|episodio\s*|cap[ií]tulo\s*)(\d{1,3})\b', re.I)


def capitulo(titulo):
    """
    Si el título es un capítulo de una serie, el nombre como lo arma la app:
      'T2 E5: Realidad | Crónicas del Metal Hurlant | Serie de Ciencia Ficción'
          -> 'Crónicas del Metal Hurlant S02 E05 Realidad'
      'En la Oscuridad T1 | Episodio 10 completo en español latino' -> 'En la Oscuridad S01 E10'
    Si no dice temporada Y capítulo, None (es una película).
    """
    temporada, numero = _TEMPORADA.search(titulo or ''), _NUMERO.search(titulo or '')
    if not (temporada and numero):
        return None
    serie, nombre_del_capitulo = '', ''
    for parte in (p.strip() for p in re.split(r'[|｜]', _EMOJIS.sub('|', titulo))):
        sin_marcas = _NUMERO.sub('', _TEMPORADA.sub('', parte)).strip(' :-–·')
        if parte != sin_marcas and ':' in parte:          # "T2 E5: Realidad"
            nombre_del_capitulo = parte.split(':', 1)[1].strip()
        elif _RELLENO.search(parte) or _es_solo_genero(parte) or not sin_marcas:
            continue
        elif not serie:
            serie = sin_marcas                            # "En la Oscuridad T1" -> "En la Oscuridad"
    if not serie:
        return None
    nombre = f'{serie} S{int(temporada.group(1)):02d} E{int(numero.group(1)):02d}'
    return f'{nombre} {nombre_del_capitulo}'.strip()[:120]


_NUMERO_EN_EL_TITULO = re.compile(r'\b(?:cap[ií]tulo|episodio|chapter|episode|ep)\.?\s*(\d{1,4})\b', re.I)
# Temporada y capítulo juntos: "S02 E26", "S01 | E01", "T4 EP7", "1x01", "1*01"
_TEMPORADA_Y_CAPITULO = [
    re.compile(r'\b[ST](\d{1,2})\s*[|:-]?\s*EP?\.?\s*(\d{1,4})\b', re.I),
    re.compile(r'\b(\d{1,2})\s*[x*]\s*(\d{1,4})\b', re.I),
]


def numero_de_capitulo(titulo):
    """
    (temporada, capítulo) que dice el título: 'Rosario Tijeras | Capítulo 67 | Temporada 2' -> (2, 67),
    'Transformers Prime: S02 E26' -> (2, 26), 'Yu-Gi-Oh! GX 1x01' -> (1, 1).
    Sin temporada, 0. None si no dice el capítulo.
    """
    for patron in _TEMPORADA_Y_CAPITULO:
        juntos = patron.search(titulo or '')
        if juntos:
            return int(juntos.group(1)), int(juntos.group(2))
    numero = _NUMERO_EN_EL_TITULO.search(titulo or '')
    if not numero:
        return None
    temporada = _TEMPORADA.search(titulo or '')
    return (int(temporada.group(1)) if temporada else 0, int(numero.group(1)))


def en_orden_de_capitulos(listado):
    """
    Los videos de una serie en el orden de sus capítulos. Si casi todos dicen
    su número ("Capítulo 12", "EP12"), por ese número: hay listas al revés
    (del último al primero) o desordenadas. Si no, del más viejo al más nuevo
    (un canal) o como está la lista. Los que no dicen número ("Capítulo
    Final") quedan al final, en el orden en que venían.
    """
    videos = listado.en_orden()
    numeros = [numero_de_capitulo(video.titulo) for video in videos]
    if not videos or sum(n is not None for n in numeros) < 0.8 * len(videos):
        return videos
    orden = sorted(range(len(videos)), key=lambda i: (numeros[i] is None, numeros[i] or (0, 0), i))
    return [videos[i] for i in orden]


def nombres_distintos(titulos):
    """
    El nombre de cada video de un mismo canal, sin repetir: si muchos empiezan
    igual ("Masha y el Oso | ..."), se usa el pedazo que sigue. Los que igual
    quedan repetidos llevan un número ("Masha y el Oso (2)").
    """
    evitar = set()
    for _ in range(3):
        nombres = [titulo_limpio(t, evitar) for t in titulos]
        cuantos = {}
        for nombre in nombres:
            cuantos[nombre.casefold()] = cuantos.get(nombre.casefold(), 0) + 1
        repetidos = {clave for clave, veces in cuantos.items() if veces >= 3} - evitar
        if not repetidos:
            break
        evitar |= repetidos
    vistos, resultado = {}, []
    for nombre in nombres:
        vistos[nombre.casefold()] = vistos.get(nombre.casefold(), 0) + 1
        veces = vistos[nombre.casefold()]
        resultado.append(nombre if veces == 1 else f'{nombre} ({veces})'[:120])
    return resultado


def _es_solo_genero(parte):
    sin_generos = sin_acentos(parte)
    for patron, _ in _GENEROS:
        sin_generos = patron.sub('', sin_generos)
    return not re.sub(r'[\W_]|\b(y|de|en|la|el|serie)\b', '', sin_generos)
