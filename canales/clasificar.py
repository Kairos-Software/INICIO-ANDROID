"""
Saca conclusiones de los datos de una entrada M3U (capa Base, no toca la
base de datos ni sale a internet):

    idioma_y_pais(...)        -> ('es', 'AR')   el idioma ('es', 'otro' o '' = no se sabe) y el país
    contenido(url, categoria) -> 'vivo' | 'pelicula' | 'serie'
    formato(url)              -> 'hls' | 'dash' | 'directo' | 'rtsp' | 'youtube' | 'pagina' | 'rtmp' | '' (no se sabe)
    limpiar_nombre(nombre)    -> 'ES: (HD REPUESTO) DAZN LALIGA' -> 'DAZN LALIGA'
    para_adultos(nombre, categoria) -> True si es XXX / +18

Son estimaciones a partir de lo que trae la lista (atributos, prefijos del
nombre, categoría, terminación del tvg-id...). El formato real lo confirma
la verificación, que mira lo que responde el servidor.
"""

import re
import unicodedata
from urllib.parse import urlsplit

# ── Idioma y país ────────────────────────────────────────────────────

PAISES_HISPANOS = {
    'AR', 'BO', 'CL', 'CO', 'CR', 'CU', 'DO', 'EC', 'ES', 'GQ', 'GT', 'HN',
    'MX', 'NI', 'PA', 'PE', 'PR', 'PY', 'SV', 'UY', 'VE',
}

# Cómo aparece un país en las categorías y nombres de las listas -> código
_NOMBRES_DE_PAIS = {
    'argentina': 'AR', 'bolivia': 'BO', 'chile': 'CL', 'colombia': 'CO', 'costa rica': 'CR', 'cuba': 'CU',
    'dominicana': 'DO', 'republica dominicana': 'DO', 'ecuador': 'EC', 'espana': 'ES', 'spain': 'ES',
    'guatemala': 'GT', 'honduras': 'HN', 'mexico': 'MX', 'nicaragua': 'NI', 'panama': 'PA', 'peru': 'PE',
    'puerto rico': 'PR', 'paraguay': 'PY', 'el salvador': 'SV', 'uruguay': 'UY', 'venezuela': 'VE',
    'brazil': 'BR', 'brasil': 'BR', 'portugal': 'PT', 'france': 'FR', 'francia': 'FR', 'italy': 'IT',
    'italia': 'IT', 'germany': 'DE', 'deutschland': 'DE', 'alemania': 'DE', 'usa': 'US',
    'united states': 'US', 'estados unidos': 'US', 'canada': 'CA', 'united kingdom': 'GB',
    'netherlands': 'NL', 'holanda': 'NL', 'turkey': 'TR', 'turquia': 'TR', 'india': 'IN',
    'russia': 'RU', 'rusia': 'RU', 'greece': 'GR', 'grecia': 'GR', 'romania': 'RO', 'albania': 'AL',
    'serbia': 'RS', 'croatia': 'HR', 'bulgaria': 'BG', 'hungary': 'HU', 'sweden': 'SE', 'poland': 'PL',
    'egypt': 'EG', 'saudi arabia': 'SA', 'iran': 'IR', 'pakistan': 'PK', 'china': 'CN', 'japan': 'JP',
    'korea': 'KR',
}

# Prefijos de las listas: "ES: Canal", "AR | Noticias", "UK"...
_PREFIJOS = {
    'ES': 'ES', 'SP': 'ES', 'AR': 'AR', 'ARG': 'AR', 'MX': 'MX', 'MEX': 'MX', 'CO': 'CO', 'COL': 'CO',
    'CL': 'CL', 'CHI': 'CL', 'PE': 'PE', 'PER': 'PE', 'UY': 'UY', 'URU': 'UY', 'PY': 'PY', 'PAR': 'PY',
    'BO': 'BO', 'EC': 'EC', 'VE': 'VE', 'VEN': 'VE', 'CR': 'CR', 'DO': 'DO', 'PR': 'PR', 'CU': 'CU',
    'US': 'US', 'USA': 'US', 'UK': 'GB', 'GB': 'GB', 'CA': 'CA', 'FR': 'FR', 'IT': 'IT', 'DE': 'DE',
    'PT': 'PT', 'BR': 'BR', 'NL': 'NL', 'TR': 'TR', 'IN': 'IN', 'RU': 'RU', 'GR': 'GR', 'PL': 'PL',
}

# Palabras que alcanzan para saber el idioma aunque no se sepa el país
_PALABRAS_ESPANOL = ('latino', 'latin', 'latam', 'espanol', 'castellano', 'spanish', 'hispano')
_PALABRAS_OTRO_IDIOMA = ('english', 'arab', 'arabic', 'turkish', 'french', 'german', 'italian', 'russian',
                         'portuguese', 'asia', 'africa', 'afr', 'hindi', 'urdu', 'chinese', 'euro')

_IDIOMAS_ESPANOL = {'es', 'spa', 'spanish', 'espanol', 'castellano'}


def sin_acentos(texto):
    texto = unicodedata.normalize('NFD', texto or '')
    return ''.join(c for c in texto if unicodedata.category(c) != 'Mn').lower()


def _idioma_de_pais(pais):
    if not pais:
        return ''
    return 'es' if pais in PAISES_HISPANOS else 'otro'


def _pais_por_prefijo(texto):
    """'ES: DAZN' / 'LAME | ARGENTINA' / 'USA | VIP' -> código o ''."""
    for parte in re.split(r'\s*[|:]\s*', texto.strip())[:2]:
        parte_simple = sin_acentos(parte).strip()
        if parte.strip().upper() in _PREFIJOS:
            return _PREFIJOS[parte.strip().upper()]
        if parte_simple in _NOMBRES_DE_PAIS:
            return _NOMBRES_DE_PAIS[parte_simple]
    return ''


def _pais_por_palabras(texto):
    simple = sin_acentos(texto)
    for nombre, codigo in _NOMBRES_DE_PAIS.items():
        if re.search(rf'\b{re.escape(nombre)}\b', simple):
            return codigo
    return ''


def _pais_por_tvg_id(tvg_id):
    """'Canal26.ar' / 'Telefe.ar@SD' -> 'AR'."""
    final = (tvg_id or '').split('@')[0].rsplit('.', 1)
    if len(final) == 2 and re.fullmatch(r'[a-zA-Z]{2}', final[1]):
        codigo = final[1].upper()
        return 'GB' if codigo == 'UK' else codigo
    return ''


def _idioma_por_palabras(texto):
    palabras = sin_acentos(texto)
    if any(re.search(rf'\b{p}\b', palabras) for p in _PALABRAS_ESPANOL):
        return 'es'
    if any(re.search(rf'\b{p}\b', palabras) for p in _PALABRAS_OTRO_IDIOMA):
        return 'otro'
    return ''


def idioma_y_pais(nombre='', categoria='', pais='', tvg_id='', idioma=''):
    """
    (idioma, país). idioma: 'es', 'otro' o '' (no se sabe). Se busca en este orden:
    tvg-language, tvg-country, la categoría ("LAME | ARGENTINA", "ARAB | SUDAN"),
    el prefijo del nombre ("ES: ..."), la terminación del tvg-id (".ar") y
    palabras sueltas del nombre ("Latino").

    La categoría va antes que el prefijo del nombre porque es más clara: en
    algunas listas "AR:" quiere decir árabe, no Argentina (y la categoría dice "ARAB").
    """
    if idioma:
        primero = sin_acentos(re.split(r'[;,]', idioma)[0]).strip()
        pais = (pais or '').upper()[:2]
        return ('es' if primero in _IDIOMAS_ESPANOL else 'otro'), pais

    pais = (pais or '').upper()[:2]
    if pais:
        return _idioma_de_pais(pais), pais
    pais = _pais_por_prefijo(categoria) or _pais_por_palabras(categoria)
    if pais:
        return _idioma_de_pais(pais), pais
    por_categoria = _idioma_por_palabras(categoria)
    if por_categoria:
        return por_categoria, ''
    pais = _pais_por_prefijo(nombre) or _pais_por_tvg_id(tvg_id)
    if pais:
        return _idioma_de_pais(pais), pais
    return _idioma_por_palabras(nombre), ''


_ADULTOS = re.compile(r'\bxxx\b|\b18\s*\+|\+\s*18\b|\badult|\bporn|\bhot\s*club\b', re.I)


def para_adultos(nombre='', categoria=''):
    """Canales XXX / +18 (por el nombre o la categoría)."""
    return bool(_ADULTOS.search(f'{nombre} {categoria}'))


# ── Contenido: en vivo, película o serie ─────────────────────────────

_EXTENSIONES_DE_ARCHIVO = ('.mkv', '.mp4', '.avi', '.mov', '.wmv', '.m4v')


def contenido(url, categoria=''):
    """
    'vivo', 'pelicula' o 'serie'. Las listas "Xtream" separan por carpeta
    (/movie/, /series/); si no, un archivo .mkv/.mp4 es una película o capítulo.
    """
    ruta = urlsplit(url).path.lower()
    if '/series/' in ruta:
        return 'serie'
    if '/movie/' in ruta or '/movies/' in ruta or '/vod/' in ruta:
        return 'pelicula'
    if ruta.endswith(_EXTENSIONES_DE_ARCHIVO):
        return 'serie' if re.search(r'\bseries?\b', sin_acentos(categoria)) else 'pelicula'
    return 'vivo'


# ── Formato de la señal (estimado por la dirección) ──────────────────

# Sitios donde el video está dentro de una página (los lee yt-dlp, ver paginas.py)
_SITIOS_DE_VIDEO = re.compile(
    r'(^|\.)(twitch\.tv|dailymotion\.com|dai\.ly|vimeo\.com|kick\.com|ok\.ru|facebook\.com|fb\.watch|'
    r'tiktok\.com|rumble\.com|vk\.com|vkvideo\.ru|bilibili\.com|streamable\.com|instagram\.com|x\.com|twitter\.com)$',
    re.I)


def formato(url):
    """
    Lo que parece ser según la dirección. '' = no se sabe (ej: las listas
    "Xtream" sin extensión): lo averigua la verificación.
    """
    host = urlsplit(url).hostname or ''
    if re.search(r'(^|\.)(youtube\.com|youtu\.be|youtube-nocookie\.com)$', host, re.I):
        return 'youtube'
    if _SITIOS_DE_VIDEO.search(host):
        return 'pagina'
    esquema = urlsplit(url).scheme.lower()
    if esquema in ('rtsp', 'rtsps'):
        return 'rtsp'
    if esquema.startswith('rtmp'):
        return 'rtmp'
    ruta = urlsplit(url).path.lower()
    if ruta.endswith('.m3u8') or ruta.endswith('.m3u') or 'm3u8' in url.lower():
        return 'hls'
    if ruta.endswith('.mpd'):
        return 'dash'
    if ruta.endswith(('.ts', '.flv', '.mp3', '.aac') + _EXTENSIONES_DE_ARCHIVO):
        return 'directo'
    return ''


# ── Nombre ───────────────────────────────────────────────────────────

# Marcas que algunas listas agregan al nombre (Ⓨ = YouTube, Ⓖ = geobloqueado...)
_MARCAS = re.compile(r'[ⓎⒼⓈ]')
_PREFIJO_PAIS = re.compile(r'^\s*[A-Z]{2,4}\s*[:|]\s*')
_CALIDAD = r'(?:u?hd|fhd|sd|4k|8k|\d{3,4}p|h\.?26[45]|hevc|repuesto\s*\d*|backup\s*\d*|alt\s*\d*|op\s*\d+)'
_ENTRE_PARENTESIS = re.compile(rf'\(\s*{_CALIDAD}(?:\s+{_CALIDAD})*\s*\)', re.I)
_SUELTA = re.compile(rf'(?<![\w+]){_CALIDAD}(?![\w+])', re.I)
_ENTRE_CORCHETES = re.compile(r'\[[^\]]*\]')


def limpiar_nombre(nombre):
    """
    El nombre para mostrar en la app: sin el prefijo de país, sin la calidad
    ni "REPUESTO" (así las variantes del mismo canal quedan juntas como
    fuentes alternativas). 'ES: (HD REPUESTO) DAZN LALIGA' -> 'DAZN LALIGA'.
    """
    original = _MARCAS.sub('', nombre or '').strip()
    texto = _PREFIJO_PAIS.sub('', original)
    texto = _ENTRE_CORCHETES.sub(' ', texto)
    texto = _ENTRE_PARENTESIS.sub(' ', texto)
    texto = _SUELTA.sub(' ', texto)
    texto = re.sub(r'\(\s*\)', ' ', texto)
    texto = ' '.join(texto.split()).strip(' -|:·')
    return texto or original
