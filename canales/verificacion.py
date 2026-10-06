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

De paso averigua el CÓDEC del video (h264, h265, mpeg2...): en HLS lo dice
la lista maestra (CODECS=...) o, si no, el pedazo de video; en video directo,
los primeros bytes (ver detectar_codec). No todos los aparatos saben mostrar
todos los códecs (muchos TV box no leen MPEG-2, muchos celulares no leen
H.265): la app lo compara con lo que sabe su aparato y no muestra lo que no
puede ver. Así se evita la "imagen verde o negra con sonido".

También distingue el video de 10 BITS (h264_10: H.264 "Hi10P", muy común en
anime; h265_10: H.265 "Main 10"): casi ningún TV box decodifica H.264 de 10
bits, y lo muestra con franjas verdes y la imagen rota (ver perfil_10_bits).

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
import re
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
    codec: str = ''       # el códec del video: h264, h265, h264_10, h265_10, mpeg2, mpeg4, vc1, av1, vp9 ('' = no se sabe)


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


# ── Códec del video ──────────────────────────────────────────────────

# MPEG-TS: el "stream_type" de cada pista en la tabla PMT (solo las de video)
_TIPOS_TS = {0x01: 'mpeg2', 0x02: 'mpeg2', 0x10: 'mpeg4', 0x1B: 'h264', 0x24: 'h265', 0xEA: 'vc1'}

# MKV (CodecID) y MP4 / HLS con fMP4 (nombre de la "caja" de la pista de video)
_MARCAS_DE_CODEC = [
    (b'V_MPEGH/ISO/HEVC', 'h265'), (b'V_MPEG4/ISO/AVC', 'h264'), (b'V_MPEG2', 'mpeg2'),
    (b'V_AV1', 'av1'), (b'V_VP9', 'vp9'),
    (b'hvc1', 'h265'), (b'hev1', 'h265'), (b'avc1', 'h264'), (b'avc3', 'h264'), (b'av01', 'av1'),
    (b'vp09', 'vp9'),
]

# HLS: el atributo CODECS de la lista maestra
_PREFIJOS_HLS = [('hvc1', 'h265'), ('hev1', 'h265'), ('avc1', 'h264'), ('avc3', 'h264'), ('av01', 'av1'),
                 ('vp09', 'vp9'), ('mp4v.20', 'mpeg4')]


def _codec_mpeg_ts(datos):
    """Lee las tablas PAT y PMT del MPEG-TS y devuelve el códec de la primera pista de video."""
    inicio = next((i for i in range(min(188, len(datos))) if datos[i] == 0x47), None)
    if inicio is None:
        return ''
    paquetes = [datos[i:i + 188] for i in range(inicio, len(datos) - 187, 188) if datos[i] == 0x47]

    def seccion(paquete):
        """Los datos de una tabla (PAT/PMT) dentro del paquete, o None."""
        if not paquete[1] & 0x40:      # no empieza una tabla en este paquete
            return None
        cuerpo = 4
        if paquete[3] & 0x20:          # hay "adaptation field": se saltea
            cuerpo += 1 + paquete[4]
        if cuerpo >= 188:
            return None
        cuerpo += 1 + paquete[cuerpo]  # pointer field
        return paquete[cuerpo:]

    pids_pmt = set()
    for paquete in paquetes:
        if ((paquete[1] & 0x1F) << 8 | paquete[2]) == 0:   # PAT
            tabla = seccion(paquete)
            if not tabla or len(tabla) < 12:
                continue
            largo = (tabla[1] & 0x0F) << 8 | tabla[2]
            for i in range(8, min(3 + largo - 4, len(tabla) - 3), 4):
                if tabla[i] << 8 | tabla[i + 1]:            # programa 0 = red, no sirve
                    pids_pmt.add((tabla[i + 2] & 0x1F) << 8 | tabla[i + 3])
    for paquete in paquetes:
        if ((paquete[1] & 0x1F) << 8 | paquete[2]) not in pids_pmt:
            continue
        tabla = seccion(paquete)
        if not tabla or len(tabla) < 12 or tabla[0] != 0x02:
            continue
        largo = (tabla[1] & 0x0F) << 8 | tabla[2]
        i = 12 + ((tabla[10] & 0x0F) << 8 | tabla[11])
        fin = min(3 + largo - 4, len(tabla))
        while i + 5 <= fin:
            if tabla[i] in _TIPOS_TS:
                return _TIPOS_TS[tabla[i]]
            i += 5 + ((tabla[i + 3] & 0x0F) << 8 | tabla[i + 4])
    return ''


# Los "perfiles" de 10 bits (o más). H.264: High 10 (110), High 4:2:2 (122), High 4:4:4 (244).
# H.265: Main 10 (2) y Range Extensions (4).
_PERFILES_10_BITS = {'h264': {110, 122, 244}, 'h265': {2, 4}}
_PERFILES_H264 = {66, 77, 88, 100, 110, 118, 122, 128, 144, 244, 44}


def _perfil_en_registro(datos, inicio, codec):
    """El perfil en un registro avcC / hvcC (empieza con la versión 1, el perfil es el byte siguiente)."""
    if inicio + 2 > len(datos) or datos[inicio] != 1:
        return None
    return datos[inicio + 1] & (0x1F if codec == 'h265' else 0xFF)


def _perfil_en_sps(datos, codec):
    """El perfil leyendo el SPS del video "crudo" (MPEG-TS, pedazos de HLS): 00 00 01 + encabezado."""
    i = datos.find(b'\x00\x00\x01')
    while 0 <= i < len(datos) - 6:
        encabezado = datos[i + 3]
        if codec == 'h264' and encabezado & 0x1F == 7 and datos[i + 4] in _PERFILES_H264:
            return datos[i + 4]
        if codec == 'h265' and (encabezado >> 1) & 0x3F == 33:   # el SPS de H.265
            return datos[i + 6] & 0x1F
        i = datos.find(b'\x00\x00\x01', i + 3)
    return None


def perfil_10_bits(datos, codec):
    """
    Si el video es de 10 bits (o más): mira el perfil del códec. En MP4 está en
    la "caja" avcC / hvcC; en MKV, en el CodecPrivate (el mismo registro); en
    MPEG-TS, en el SPS (los datos de arranque del video). Si no lo encuentra, False.
    """
    if codec not in _PERFILES_10_BITS:
        return False
    perfil = None
    caja = datos.find(b'avcC' if codec == 'h264' else b'hvcC')
    if caja >= 0:
        perfil = _perfil_en_registro(datos, caja + 4, codec)
    if perfil is None:
        marca = datos.find(b'V_MPEG4/ISO/AVC' if codec == 'h264' else b'V_MPEGH/ISO/HEVC')
        privado = datos.find(b'\x63\xa2', marca) if marca >= 0 else -1   # CodecPrivate de MKV
        if privado >= 0 and privado + 2 < len(datos):
            primero = datos[privado + 2]
            largo_del_tamanio = next((n for n in range(1, 9) if primero & (0x80 >> (n - 1))), 8)
            perfil = _perfil_en_registro(datos, privado + 2 + largo_del_tamanio, codec)
    if perfil is None:
        perfil = _perfil_en_sps(datos, codec)
    return perfil in _PERFILES_10_BITS[codec]


def detectar_codec(datos):
    """El códec del video mirando los primeros bytes (MPEG-TS, MKV o MP4). '' = no se sabe."""
    if not datos:
        return ''
    codec = ''
    if _es_mpeg_ts(datos):
        codec = _codec_mpeg_ts(datos)
    else:
        codec = next((codec for marca, codec in _MARCAS_DE_CODEC if marca in datos), '')
    if perfil_10_bits(datos, codec):
        return f'{codec}_10'
    return codec


def _perfil_hls(parte, codec):
    """El perfil en el CODECS de HLS: avc1.6E0028 -> 0x6E = 110; hvc1.2.4.L120 -> 2 (puede venir como A2, B2...)."""
    try:
        if codec == 'h264':
            return int(parte.split('.')[1][:2], 16)
        return int(re.sub(r'^[A-Ca-c]', '', parte.split('.')[1]))
    except (IndexError, ValueError):
        return None


def codec_de_hls(texto):
    """El códec de la primera calidad de una lista maestra (CODECS="avc1.64001f,mp4a.40.2")."""
    for linea in texto.splitlines():
        codecs = re.search(r'CODECS="([^"]*)"', linea) if linea.startswith('#EXT-X-STREAM-INF') else None
        if codecs:
            for parte in codecs.group(1).split(','):
                parte = parte.strip()
                for prefijo, codec in _PREFIJOS_HLS:
                    if parte.lower().startswith(prefijo):
                        if _perfil_hls(parte, codec) in _PERFILES_10_BITS.get(codec, ()):
                            return f'{codec}_10'
                        return codec
            return ''
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
            if not datos:
                return Resultado(CAIDA, 'No llegó video.')
            return Resultado(FUNCIONA, tipo='directo', codec=detectar_codec(datos))
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
        codec = codec_de_hls(texto)
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
        pedazo, _, _ = _descargar(urljoin(final, pedazos[-1]), cabeceras, BYTES_DE_VIDEO)   # el más reciente
        if not pedazo:
            return Resultado(CAIDA, 'La lista responde, pero no llega video.', tipo='hls')
        return Resultado(FUNCIONA, tipo='hls', codec=codec or detectar_codec(pedazo))
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
