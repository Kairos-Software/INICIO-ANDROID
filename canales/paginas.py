"""
Videos que están dentro de una PÁGINA (YouTube, Twitch, Dailymotion, Vimeo,
Kick, OK.ru... y cientos de sitios más), no en una dirección de video directa.
Usa yt-dlp (la herramienta que usan VLC, mpv y Kodi para lo mismo) para
averiguar dónde está el video de verdad. Capa Base, no toca la base de datos.

    verificar('https://www.youtube.com/@canal/live')   -> Resultado('funciona', tipo='youtube')
    resolver('https://www.twitch.tv/canal')            -> Resuelto(url='https://...m3u8', tipo='hls', cabeceras={...})

YouTube es especial: las direcciones de video que entrega están atadas a la
IP de quien las pidió. Si las averigua el servidor, al celular le dan error
403. Por eso a YouTube la resuelve la propia app (en el aparato) y acá solo
se verifica que el video o el vivo exista. Los demás sitios los resuelve el
servidor cuando la app los pide (api/v1/canales.py -> resolver).
"""

import re
from dataclasses import dataclass, field

from .verificacion import CAIDA, FUNCIONA, SIN_VERIFICAR, TIEMPO_MAXIMO, Resultado

ES_YOUTUBE = re.compile(r'(^|\.)(youtube\.com|youtu\.be|youtube-nocookie\.com)$', re.I)


@dataclass
class Resuelto:
    url: str
    tipo: str                 # hls, dash o directo: cómo se lo tiene que leer el reproductor
    cabeceras: dict = field(default_factory=dict)


class NoSePudo(Exception):
    """El sitio no entregó el video (el mensaje dice por qué, en castellano)."""


def es_youtube(host):
    return bool(ES_YOUTUBE.search(host or ''))


def _opciones(**extra):
    return {
        'quiet': True, 'no_warnings': True, 'skip_download': True, 'noplaylist': True,
        'socket_timeout': TIEMPO_MAXIMO, 'extractor_retries': 0, 'logger': _Silencio(),
        # Primero una sola dirección con audio y video (HLS si hay): es lo que la app sabe abrir
        'format': 'best[protocol^=m3u8]/best[vcodec!=none][acodec!=none]/best',
        **extra,
    }


class _Silencio:
    def debug(self, mensaje):
        pass

    warning = info = debug

    def error(self, mensaje):
        pass


def _motivo(error):
    """El error de yt-dlp, en castellano y corto."""
    texto = str(error)
    reglas = [
        (r'not currently live|is not live|offline', 'El canal no está transmitiendo en vivo ahora.'),
        (r'will begin|premieres in|upcoming', 'Todavía no empezó (es un vivo programado).'),
        (r'private video', 'El video es privado.'),
        (r'removed|unavailable|does not exist|not found|404', 'El video ya no existe o no está disponible.'),
        (r'age|confirm your age', 'Tiene restricción de edad.'),
        (r'not available in your country|geo', 'No está disponible en este país.'),
        (r'unsupported url', 'No es una página de video que se pueda leer.'),
        (r'timed out|timeout', 'No respondió a tiempo.'),
    ]
    for patron, motivo in reglas:
        if re.search(patron, texto, re.I):
            return motivo
    return f'No se pudo leer el video ({texto.replace("ERROR: ", "")[:120]}).'


def _es_bloqueo_de_robots(error):
    """YouTube a veces le pide "iniciar sesión" a los servidores: no quiere decir que el video no ande."""
    return bool(re.search(r'sign in to confirm|not a bot|429|too many requests', str(error), re.I))


def _extraer(url, **extra):
    import yt_dlp   # se importa recién acá: tarda en cargar y solo hace falta para estas fuentes
    with yt_dlp.YoutubeDL(_opciones(**extra)) as ytdl:
        informacion = ytdl.extract_info(url, download=False)
    if informacion and informacion.get('_type') == 'playlist':
        entradas = [e for e in informacion.get('entries') or [] if e]
        informacion = entradas[0] if entradas else None
    if not informacion:
        raise NoSePudo('La página no tiene ningún video.')
    return informacion


def _tipo_de(informacion):
    protocolo = (informacion.get('protocol') or '').lower()
    if 'm3u8' in protocolo:
        return 'hls'
    if 'dash' in protocolo or (informacion.get('url') or '').split('?')[0].endswith('.mpd'):
        return 'dash'
    return 'directo'


def verificar(url, youtube=None):
    """
    ¿Hay un video que se pueda reproducir en esta página? Para YouTube no se
    pide la dirección final (no le serviría a la app), solo los datos.
    """
    from urllib.parse import urlsplit
    if youtube is None:
        youtube = es_youtube(urlsplit(url).hostname)
    tipo = 'youtube' if youtube else 'pagina'
    try:
        informacion = _extraer(url, **({'format': 'best/bestaudio'} if youtube else {}))
    except Exception as error:   # yt-dlp lanza sus propias excepciones (DownloadError, ExtractorError...)
        if _es_bloqueo_de_robots(error):
            return Resultado(SIN_VERIFICAR, 'YouTube no dejó verificar desde el servidor (la app lo intenta igual).',
                             tipo=tipo)
        return Resultado(CAIDA, _motivo(error), tipo=tipo)
    if informacion.get('live_status') in ('is_upcoming', 'post_live') and youtube:
        return Resultado(CAIDA, 'El vivo todavía no empezó o ya terminó.', tipo=tipo)
    if not youtube and not informacion.get('url'):
        return Resultado(CAIDA, 'La página no entrega una dirección de video.', tipo=tipo)
    return Resultado(FUNCIONA, tipo=tipo)


def resolver(url):
    """
    La dirección real del video en este momento (cambia seguido: hay que
    pedirla cada vez que se va a reproducir). Lanza NoSePudo si no hay.
    """
    try:
        informacion = _extraer(url)
    except NoSePudo:
        raise
    except Exception as error:
        raise NoSePudo(_motivo(error)) from error
    if not informacion.get('url'):
        raise NoSePudo('La página no entrega una dirección de video.')
    cabeceras = {clave: valor for clave, valor in (informacion.get('http_headers') or {}).items()
                 if clave.lower() in ('user-agent', 'referer', 'origin', 'cookie')}
    return Resuelto(url=informacion['url'], tipo=_tipo_de(informacion), cabeceras=cabeceras)
