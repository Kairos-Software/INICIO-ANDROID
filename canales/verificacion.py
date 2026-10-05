"""
Comprueba si las fuentes responden (capa Base, no toca la base de datos).

Hace lo mismo que el reproductor de la app, pero desde el servidor:

  1. Pide la dirección y mira QUÉ devuelve (como VLC, no confía en la
     extensión): una lista HLS (#EXTM3U), un manifiesto DASH (<MPD>) o video
     "directo" (MPEG-TS, MP4, MKV, FLV...: lo que mandan las listas "Xtream",
     las direcciones sin extensión tipo http://servidor:8080/usuario/clave/123).
  2. Si es HLS "maestra" (la que ofrece varias calidades), pide la primera
     calidad: muchas veces la maestra responde y la señal no.
  3. En HLS, pide el pedazo de video MÁS RECIENTE (por ahí arranca el
     reproductor): hay servidores que entregan la lista pero rechazan el video.

Se presenta igual que el reproductor de la app (USER_AGENT_REPRODUCTOR, o
el User-Agent / Referer propio de la fuente). Si el servidor lo rechaza,
prueba otra vez presentándose como VLC (USER_AGENT_VLC): hay paneles que
solo le entregan la señal a reproductores conocidos. Si así anda, el
resultado trae ese User-Agent para guardarlo en la fuente (y la app lo usa).

YouTube y las páginas de video (Twitch, Dailymotion...) se comprueban con
yt-dlp (ver paginas.py). Si una dirección cualquiera responde con una página
web, también se prueba si adentro hay un video. RTSP se comprueba con un
pedido OPTIONS. RTMP la app no lo reproduce.

Cada pedido espera como máximo TIEMPO_MAXIMO segundos; se verifican HILOS
fuentes a la vez, pero nunca más de POR_SERVIDOR al mismo servidor (los
paneles IPTV cortan si una misma cuenta abre muchas conexiones).

    from canales.verificacion import verificar_url, verificar_varias
    verificar_url('https://.../playlist.m3u8')        -> Resultado('funciona', tipo='hls')
    verificar_varias({url: 'hls', url2: 'youtube'})   -> {url: Resultado, ...}
"""

import http.client
import socket
import ssl
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit

TIEMPO_MAXIMO = 9         # segundos por pedido (el HTML usa 9)
HILOS = 10                # fuentes verificadas a la vez
POR_SERVIDOR = 2          # ...pero como mucho estas al mismo servidor
BYTES_INICIALES = 64 * 1024   # para saber qué es alcanza con el principio
MAX_BYTES = 512 * 1024    # una lista .m3u8 pesa pocos KB: no hace falta leer más
BYTES_DE_VIDEO = 32 * 1024    # del pedazo de video alcanza con ver que empieza a llegar

# Cómo se presenta el reproductor de la app (la API se lo manda junto con
# cada fuente). Como un navegador de celular: hay servidores de canales que
# rechazan a "ExoPlayer" (el reproductor de Android) con error 403.
USER_AGENT_REPRODUCTOR = ('Mozilla/5.0 (Linux; Android 14; K) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/124.0.0.0 Mobile Safari/537.36')
# El segundo intento: hay paneles IPTV que solo atienden a reproductores conocidos
USER_AGENT_VLC = 'VLC/3.0.21 LibVLC/3.0.21'

FUNCIONA = 'funciona'
CAIDA = 'caida'
SIN_VERIFICAR = 'sin_verificar'


@dataclass
class Resultado:
    estado: str           # FUNCIONA, CAIDA o SIN_VERIFICAR
    error: str = ''       # por qué falló (para mostrar en el panel)
    tipo: str = ''        # el formato que se encontró: hls, dash, directo, rtsp, youtube, pagina ('' = no se sabe)
    user_agent: str = ''  # si anduvo con otro User-Agent (ej: el de VLC), cuál
    rechazo: bool = False  # el servidor respondió pero no entregó la señal (vale la pena probar como VLC)
    es_pagina: bool = False  # respondió una página web (puede tener un video adentro)
    titulo: str = ''      # YouTube / páginas: el título del video o canal (para sugerir el nombre)
    imagen: str = ''      # ...y su miniatura (para sugerir el logo)


def cabeceras_para(user_agent='', referer=''):
    """Las cabeceras con que se pide la señal (las mismas que usa la app)."""
    cabeceras = {'User-Agent': user_agent or USER_AGENT_REPRODUCTOR}
    if referer:
        cabeceras['Referer'] = referer
    return cabeceras


def _descargar(url, cabeceras, maximo=MAX_BYTES):
    """(bytes, dirección final después de redirecciones, Content-Type)."""
    pedido = urllib.request.Request(url, headers=cabeceras)
    with urllib.request.urlopen(pedido, timeout=TIEMPO_MAXIMO) as respuesta:
        return respuesta.read(maximo), respuesta.geturl(), respuesta.headers.get('Content-Type', '') or ''


def _texto(datos):
    return datos.decode('utf-8', errors='replace')


def _es_lista_hls(datos):
    return datos.lstrip(b'\xef\xbb\xbf \r\n\t').startswith(b'#EXTM3U')


def _es_mpeg_ts(datos):
    """Los paquetes MPEG-TS miden 188 bytes y empiezan con 0x47."""
    for inicio in range(min(188, len(datos))):
        if datos[inicio] == 0x47 and all(
                inicio + 188 * k < len(datos) and datos[inicio + 188 * k] == 0x47 for k in (1, 2)):
            return True
    return False


def detectar_formato(datos, tipo_contenido=''):
    """
    Qué es lo que respondió el servidor, mirando los primeros bytes:
    'hls', 'dash', 'directo' (video o audio que se reproduce tal cual) o '' (otra cosa).
    """
    if _es_lista_hls(datos):
        return 'hls'
    tipo_contenido = tipo_contenido.lower()
    if b'<MPD' in datos[:4096]:
        return 'dash'
    if (_es_mpeg_ts(datos)
            or datos[4:8] == b'ftyp'                 # MP4
            or datos[:4] == b'\x1aE\xdf\xa3'         # MKV / WebM
            or datos[:3] in (b'FLV', b'ID3')         # FLV / MP3
            or tipo_contenido.startswith(('video/', 'audio/'))):
        return 'directo'
    if 'mpegurl' in tipo_contenido:
        return 'hls'
    return ''


def _direcciones(texto):
    return [linea.strip() for linea in texto.splitlines() if linea.strip() and not linea.strip().startswith('#')]


def _primera_calidad(texto, base):
    """En una lista maestra, la dirección de la primera calidad (o None si no es maestra)."""
    lineas = [linea.strip() for linea in texto.splitlines()]
    for i, linea in enumerate(lineas):
        if linea.startswith('#EXT-X-STREAM-INF'):
            for siguiente in lineas[i + 1:]:
                if siguiente and not siguiente.startswith('#'):
                    return urljoin(base, siguiente)  # puede ser relativa a la maestra
    return None


def _error_http(error, que):
    if error.code in (401, 403):
        return Resultado(CAIDA, f'El canal no entrega {que} al reproductor (error {error.code}).', rechazo=True)
    return Resultado(CAIDA, f'El servidor respondió con error {error.code} al pedir {que}.',
                     rechazo=400 <= error.code < 500)


def _probar(url, cabeceras):
    """Una prueba completa con estas cabeceras."""
    que = 'la lista'
    try:
        datos, final, tipo_contenido = _descargar(url, cabeceras, BYTES_INICIALES)
        tipo = detectar_formato(datos, tipo_contenido)
        if tipo == 'directo':
            return Resultado(FUNCIONA, tipo='directo') if datos else Resultado(CAIDA, 'No llegó video.')
        if tipo == 'dash':
            return Resultado(FUNCIONA, tipo='dash')
        if tipo != 'hls':
            if b'<html' in datos[:2048].lower() or b'<!doctype' in datos[:2048].lower():
                return Resultado(CAIDA, 'Responde, pero con una página web, no con video.', rechazo=True,
                                 es_pagina=True)
            return Resultado(CAIDA, 'Responde, pero no es un formato de video conocido.', rechazo=True)

        if len(datos) >= BYTES_INICIALES:   # una lista larga: se pide entera
            datos, final, _ = _descargar(url, cabeceras, MAX_BYTES)
        texto = _texto(datos)
        calidad = _primera_calidad(texto, final)
        if calidad:
            datos, final, _ = _descargar(calidad, cabeceras, MAX_BYTES)
            if not _es_lista_hls(datos):
                return Resultado(CAIDA, 'La lista responde, pero la señal no.', tipo='hls')
            texto = _texto(datos)
        pedazos = _direcciones(texto)
        if not pedazos:
            return Resultado(CAIDA, 'La lista no tiene video (está vacía).', tipo='hls')
        que = 'el video'
        _descargar(urljoin(final, pedazos[-1]), cabeceras, BYTES_DE_VIDEO)   # el más reciente
        return Resultado(FUNCIONA, tipo='hls')
    except urllib.error.HTTPError as error:
        return _error_http(error, que)
    except urllib.error.URLError as error:
        if isinstance(error.reason, TimeoutError):
            return Resultado(CAIDA, 'No respondió a tiempo.')
        if isinstance(error.reason, ssl.SSLCertVerificationError):
            # El reproductor de Android también la rechazaría
            return Resultado(CAIDA, 'Certificado de seguridad inválido.')
        if isinstance(error.reason, socket.gaierror):
            return Resultado(CAIDA, 'El servidor ya no existe (dirección desconocida).')
        if isinstance(error.reason, ConnectionRefusedError):
            return Resultado(CAIDA, 'El servidor rechazó la conexión.')
        return Resultado(CAIDA, f'No se pudo conectar ({error.reason}).'[:200])
    except TimeoutError:
        return Resultado(CAIDA, 'No respondió a tiempo.')
    except (ConnectionResetError, http.client.RemoteDisconnected):
        # Algunos paneles cortan la conexión a los reproductores que no conocen
        return Resultado(CAIDA, 'El servidor cortó la conexión.', rechazo=True)
    except (OSError, ValueError, http.client.HTTPException) as error:
        return Resultado(CAIDA, f'Error: {error}'[:200])


def _verificar_rtsp(url):
    """RTSP no es http: se le pregunta OPTIONS y se espera "RTSP/1.0 200"."""
    partes = urlsplit(url)
    try:
        with socket.create_connection((partes.hostname, partes.port or 554), timeout=TIEMPO_MAXIMO) as conexion:
            conexion.sendall(f'OPTIONS {url} RTSP/1.0\r\nCSeq: 1\r\nUser-Agent: {USER_AGENT_VLC}\r\n\r\n'.encode())
            respuesta = conexion.recv(512).decode('latin-1')
    except TimeoutError:
        return Resultado(CAIDA, 'No respondió a tiempo.', tipo='rtsp')
    except OSError as error:
        return Resultado(CAIDA, f'No se pudo conectar ({error}).'[:200], tipo='rtsp')
    if respuesta.startswith('RTSP/1.0 200'):
        return Resultado(FUNCIONA, tipo='rtsp')
    return Resultado(CAIDA, f'El servidor RTSP respondió: {respuesta.splitlines()[0] if respuesta else "nada"}'[:200],
                     tipo='rtsp')


def verificar_url(url, tipo='hls', user_agent='', referer=''):
    if tipo in ('youtube', 'pagina'):
        from . import paginas
        return paginas.verificar(url, youtube=tipo == 'youtube')
    esquema = urlsplit(url).scheme.lower()
    if esquema.startswith('rtmp'):
        return Resultado(CAIDA, 'Es RTMP: la app todavía no reproduce ese formato.')
    if esquema in ('rtsp', 'rtsps'):
        return _verificar_rtsp(url)

    resultado = _probar(url, cabeceras_para(user_agent, referer))
    if resultado.estado == CAIDA and resultado.rechazo and not user_agent:
        como_vlc = _probar(url, cabeceras_para(USER_AGENT_VLC, referer))
        if como_vlc.estado == FUNCIONA:
            como_vlc.user_agent = USER_AGENT_VLC
            return como_vlc
    if resultado.es_pagina:
        # Una página web: puede ser de un sitio de videos que yt-dlp sabe leer
        from . import paginas
        en_la_pagina = paginas.verificar(url, youtube=False)
        if en_la_pagina.estado == FUNCIONA:
            return en_la_pagina
    return resultado


def verificar_varias(fuentes, cabeceras=None, hasta=None):
    """
    {url: tipo} -> {url: Resultado}. Verifica varias a la vez.
    `cabeceras`: {url: (user_agent, referer)} para las fuentes que tienen las suyas.
    `hasta`: momento (time.monotonic()) a partir del cual no se empieza ninguna
    más; las que no llegaron a probarse NO vienen en el resultado (quedan para
    la próxima tanda). Así un pedido del panel nunca tarda demasiado.
    """
    if not fuentes:
        return {}
    cabeceras = cabeceras or {}
    por_servidor = {}
    candado = threading.Lock()

    def turno(url):
        servidor = (urlsplit(url).hostname or '').lower()
        with candado:
            return por_servidor.setdefault(servidor, threading.Semaphore(POR_SERVIDOR))

    def una(par):
        url, tipo = par
        with turno(url):
            if hasta is not None and time.monotonic() >= hasta:
                return None
            return verificar_url(url, tipo, *cabeceras.get(url, ('', '')))

    with ThreadPoolExecutor(max_workers=HILOS) as hilos:
        resultados = dict(zip(fuentes, hilos.map(una, fuentes.items())))
    return {url: resultado for url, resultado in resultados.items() if resultado is not None}
