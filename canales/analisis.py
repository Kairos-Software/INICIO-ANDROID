"""
Qué trae un video, mirando sus primeros bytes (capa Base, no sale a internet).

La verificación "a fondo" (verificacion.py) baja un pedazo de cada video y
le pregunta a este módulo:

  - si tiene SONIDO (alguna pista de audio) y de qué tipo (AAC, AC3...);
  - en qué IDIOMA está el audio (cuando el video lo dice: "spa", "eng"...);
  - la RESOLUCIÓN (cuántas líneas: 1080, 720, 480...);
  - cuántos SEGUNDOS de video hay en esos bytes (para saber si llega más
    rápido de lo que se reproduce) y, en películas, cuánto DURA entera.

Entiende MPEG-TS (lo de los canales en vivo y los pedazos de HLS), MKV y
MP4. Lo que no puede averiguar lo deja vacío ("no se sabe"): nunca adivina.

    from canales.analisis import analizar, de_la_maestra
    analizar(datos, 'h264')   -> Analisis(alto=1080, con_audio=True, audios=['aac'], idiomas=['es'], ...)
    de_la_maestra(texto_m3u8) -> Maestra(alto=1080, idiomas=['es', 'en'], audio_aparte=True)
"""

import re
import struct
from dataclasses import dataclass, field


@dataclass
class Analisis:
    alto: int = 0                 # líneas de la imagen (1080, 720...); 0 = no se sabe
    con_audio: bool | None = None   # None = no se sabe
    audios: list = field(default_factory=list)    # códecs de audio: aac, ac3, eac3, mp2, dts...
    idiomas: list = field(default_factory=list)   # idiomas del audio, en dos letras: es, en, ar...
    segundos: float = 0           # cuánto video hay en estos bytes (solo MPEG-TS)
    duracion: float = 0           # cuánto dura el video entero (MKV / MP4, si lo dice al principio)


@dataclass
class Maestra:
    """Lo que dice una lista HLS "maestra" (la que ofrece varias calidades)."""
    alto: int = 0
    idiomas: list = field(default_factory=list)
    audio_aparte: bool = False    # el audio viene en otra lista (EXT-X-MEDIA): los pedazos de video no lo traen


# ── Idiomas ──────────────────────────────────────────────────────────

# Los códigos que traen los videos (ISO 639: dos o tres letras) llevados a dos letras.
_IDIOMAS = {
    'es': ('spa', 'esp', 'es', 'cas', 'lat', 'spl', 'es-419', 'es-es', 'es-mx', 'es-ar', 'es-us'),
    'en': ('eng', 'en', 'en-us', 'en-gb'),
    'pt': ('por', 'pt', 'pob', 'pt-br', 'pt-pt'),
    'fr': ('fra', 'fre', 'fr'), 'it': ('ita', 'it'), 'de': ('deu', 'ger', 'de'), 'ar': ('ara', 'ar'),
    'ru': ('rus', 'ru'), 'tr': ('tur', 'tr'), 'hi': ('hin', 'hi'), 'zh': ('zho', 'chi', 'zh', 'cmn', 'yue'),
    'ja': ('jpn', 'ja'), 'ko': ('kor', 'ko'), 'pl': ('pol', 'pl'), 'nl': ('nld', 'dut', 'nl'),
    'el': ('ell', 'gre', 'el'), 'ro': ('ron', 'rum', 'ro'), 'fa': ('fas', 'per', 'fa'), 'ur': ('urd', 'ur'),
    'he': ('heb', 'he'), 'sv': ('swe', 'sv'), 'uk': ('ukr', 'uk'), 'hu': ('hun', 'hu'), 'cs': ('ces', 'cze', 'cs'),
    'bn': ('ben', 'bn'), 'ta': ('tam', 'ta'), 'th': ('tha', 'th'), 'vi': ('vie', 'vi'), 'id': ('ind', 'id'),
    'sq': ('sqi', 'alb', 'sq'), 'sr': ('srp', 'sr'), 'hr': ('hrv', 'hr'), 'bg': ('bul', 'bg'), 'ku': ('kur', 'ku'),
}
_A_DOS_LETRAS = {codigo: corto for corto, codigos in _IDIOMAS.items() for codigo in codigos}

NOMBRES_DE_IDIOMAS = {
    'es': 'español', 'en': 'inglés', 'pt': 'portugués', 'fr': 'francés', 'it': 'italiano', 'de': 'alemán',
    'ar': 'árabe', 'ru': 'ruso', 'tr': 'turco', 'hi': 'hindi', 'zh': 'chino', 'ja': 'japonés', 'ko': 'coreano',
    'pl': 'polaco', 'nl': 'neerlandés', 'el': 'griego', 'ro': 'rumano', 'fa': 'persa', 'ur': 'urdu',
    'he': 'hebreo', 'sv': 'sueco', 'uk': 'ucraniano', 'hu': 'húngaro', 'cs': 'checo', 'bn': 'bengalí',
    'ta': 'tamil', 'th': 'tailandés', 'vi': 'vietnamita', 'id': 'indonesio', 'sq': 'albanés', 'sr': 'serbio',
    'hr': 'croata', 'bg': 'búlgaro', 'ku': 'kurdo',
}


def idioma_corto(codigo):
    """'spa' -> 'es', 'ENG' -> 'en', 'es-419' -> 'es'. Los que no dicen nada ('und', 'mul', 'qaa'...) -> ''."""
    codigo = (codigo or '').strip().lower().replace('_', '-')
    if codigo in _A_DOS_LETRAS:
        return _A_DOS_LETRAS[codigo]
    base = codigo.split('-')[0]
    if base in _A_DOS_LETRAS:
        return _A_DOS_LETRAS[base]
    if base in ('und', 'mul', 'zxx', 'mis', 'unk', 'nar', 'xxx') or re.fullmatch(r'q[a-t][a-z]', base) or not base:
        return ''
    return base if re.fullmatch(r'[a-z]{2,3}', base) else ''


def _agregar_idioma(lista, codigo):
    corto = idioma_corto(codigo)
    if corto and corto not in lista:
        lista.append(corto)


# ── MPEG-TS ──────────────────────────────────────────────────────────

# El "stream_type" de cada pista en la tabla PMT
TIPOS_DE_VIDEO_TS = {0x01: 'mpeg2', 0x02: 'mpeg2', 0x10: 'mpeg4', 0x1B: 'h264', 0x24: 'h265', 0xEA: 'vc1'}
_TIPOS_DE_AUDIO_TS = {0x03: 'mp2', 0x04: 'mp2', 0x0F: 'aac', 0x11: 'aac', 0x81: 'ac3', 0x87: 'eac3', 0x82: 'dts'}
# Las pistas "privadas" (stream_type 0x06) dicen qué son con un descriptor: AC3, E-AC3, DTS...
_DESCRIPTORES_DE_AUDIO = {0x6A: 'ac3', 0x7A: 'eac3', 0x7B: 'dts'}
_IDIOMA_TS = 0x0A   # ISO_639_language_descriptor: tres letras ("spa")


@dataclass
class Pista:
    pid: int
    clase: str          # 'video', 'audio' u 'otra' (subtítulos, teletexto, datos...)
    codec: str = ''
    idioma: str = ''


def es_mpeg_ts(datos):
    """Los paquetes MPEG-TS miden 188 bytes y empiezan con 0x47."""
    return _inicio_ts(datos) is not None


def _inicio_ts(datos):
    for inicio in range(min(188, len(datos))):
        if datos[inicio] == 0x47 and all(
                inicio + 188 * k < len(datos) and datos[inicio + 188 * k] == 0x47 for k in (1, 2)):
            return inicio
    return None


def _paquetes(datos):
    inicio = _inicio_ts(datos)
    if inicio is None:
        inicio = next((i for i in range(min(188, len(datos))) if datos[i] == 0x47), None)
    if inicio is None:
        return []
    return [datos[i:i + 188] for i in range(inicio, len(datos) - 187, 188) if datos[i] == 0x47]


def _pid(paquete):
    return (paquete[1] & 0x1F) << 8 | paquete[2]


def _carga(paquete):
    """Los datos del paquete, sin la cabecera ni el "adaptation field"."""
    cuerpo = 4
    if paquete[3] & 0x20:
        cuerpo += 1 + paquete[4]
    if not paquete[3] & 0x10 or cuerpo >= 188:
        return b''
    return paquete[cuerpo:]


def _seccion(paquete):
    """Los datos de una tabla (PAT/PMT) que empieza en este paquete, o None."""
    if not paquete[1] & 0x40:
        return None
    carga = _carga(paquete)
    if not carga:
        return None
    return carga[1 + carga[0]:]   # pointer field


def pistas_ts(datos):
    """Las pistas del MPEG-TS según las tablas PAT y PMT ([] si no aparecen en estos bytes)."""
    paquetes = _paquetes(datos)
    pids_pmt = set()
    for paquete in paquetes:
        if _pid(paquete) == 0:
            tabla = _seccion(paquete)
            if not tabla or len(tabla) < 12:
                continue
            largo = (tabla[1] & 0x0F) << 8 | tabla[2]
            for i in range(8, min(3 + largo - 4, len(tabla) - 3), 4):
                if tabla[i] << 8 | tabla[i + 1]:            # programa 0 = red, no sirve
                    pids_pmt.add((tabla[i + 2] & 0x1F) << 8 | tabla[i + 3])
    for paquete in paquetes:
        if _pid(paquete) not in pids_pmt:
            continue
        tabla = _seccion(paquete)
        if not tabla or len(tabla) < 12 or tabla[0] != 0x02:
            continue
        largo = (tabla[1] & 0x0F) << 8 | tabla[2]
        i = 12 + ((tabla[10] & 0x0F) << 8 | tabla[11])
        fin = min(3 + largo - 4, len(tabla))
        pistas = []
        while i + 5 <= fin:
            tipo = tabla[i]
            pid = (tabla[i + 1] & 0x1F) << 8 | tabla[i + 2]
            largo_info = (tabla[i + 3] & 0x0F) << 8 | tabla[i + 4]
            descriptores = _descriptores(tabla[i + 5:i + 5 + largo_info])
            pista = Pista(pid, 'otra')
            if tipo in TIPOS_DE_VIDEO_TS:
                pista.clase, pista.codec = 'video', TIPOS_DE_VIDEO_TS[tipo]
            elif tipo in _TIPOS_DE_AUDIO_TS:
                pista.clase, pista.codec = 'audio', _TIPOS_DE_AUDIO_TS[tipo]
            elif tipo == 0x06:
                codec = next((c for etiqueta, c in _DESCRIPTORES_DE_AUDIO.items() if etiqueta in descriptores), '')
                if codec:
                    pista.clase, pista.codec = 'audio', codec
            if _IDIOMA_TS in descriptores:
                pista.idioma = descriptores[_IDIOMA_TS][:3].decode('latin-1', errors='replace')
            pistas.append(pista)
            i += 5 + largo_info
        return pistas
    return []


def _descriptores(datos):
    """{etiqueta: contenido} de una lista de descriptores (etiqueta, largo, contenido)."""
    resultado = {}
    i = 0
    while i + 2 <= len(datos):
        etiqueta, largo = datos[i], datos[i + 1]
        resultado.setdefault(etiqueta, datos[i + 2:i + 2 + largo])
        i += 2 + largo
    return resultado


def _datos_de_la_pista(paquetes, pid, maximo=256 * 1024):
    """Lo que viaja en una pista (los PES unidos), para buscar adentro el arranque del video."""
    partes, total = [], 0
    for paquete in paquetes:
        if _pid(paquete) == pid:
            carga = _carga(paquete)
            partes.append(carga)
            total += len(carga)
            if total >= maximo:
                break
    return b''.join(partes)


def _segundos_de_la_pista(paquetes, pid):
    """Cuántos segundos de video hay, según las marcas de tiempo (PTS) de la pista."""
    marcas = []
    for paquete in paquetes:
        if _pid(paquete) != pid or not paquete[1] & 0x40:
            continue
        pes = _carga(paquete)
        if len(pes) >= 14 and pes[:3] == b'\x00\x00\x01' and pes[7] & 0x80:
            b = pes[9:14]
            marcas.append(((b[0] >> 1) & 0x07) << 30 | b[1] << 22 | (b[2] >> 1) << 15 | b[3] << 7 | b[4] >> 1)
    if len(marcas) < 2:
        return 0
    segundos = (max(marcas) - min(marcas)) / 90000
    return segundos if segundos < 600 else 0   # más de 10 minutos en un pedazo: la marca dio la vuelta, no sirve


def _analizar_ts(datos, codec):
    paquetes = _paquetes(datos)
    pistas = pistas_ts(datos)
    resultado = Analisis()
    if not pistas:
        return resultado
    audios = [p for p in pistas if p.clase == 'audio']
    resultado.con_audio = bool(audios)
    for pista in audios:
        if pista.codec not in resultado.audios:
            resultado.audios.append(pista.codec)
        _agregar_idioma(resultado.idiomas, pista.idioma)
    video = next((p for p in pistas if p.clase == 'video'), None)
    if video:
        resultado.segundos = _segundos_de_la_pista(paquetes, video.pid)
        resultado.alto = alto_en_el_video(_datos_de_la_pista(paquetes, video.pid), codec or video.codec)
    elif audios:
        resultado.segundos = _segundos_de_la_pista(paquetes, audios[0].pid)
    return resultado


# ── La resolución, leyendo el SPS (los datos de arranque del video) ──

class _Bits:
    """Lee de a bits, y números "Exp-Golomb" (como vienen en el SPS)."""

    def __init__(self, datos):
        self.datos, self.posicion = datos, 0

    def bit(self):
        byte = self.datos[self.posicion >> 3]   # IndexError si se termina
        self.posicion += 1
        return (byte >> (7 - ((self.posicion - 1) & 7))) & 1

    def bits(self, cantidad):
        valor = 0
        for _ in range(cantidad):
            valor = valor << 1 | self.bit()
        return valor

    def ue(self):
        ceros = 0
        while not self.bit():
            ceros += 1
            if ceros > 31:
                raise ValueError('número inválido')
        return (1 << ceros) - 1 + self.bits(ceros)

    def se(self):
        valor = self.ue()
        return (valor + 1) // 2 if valor & 1 else -(valor // 2)


_PERFILES_CON_CROMA = {100, 110, 122, 244, 44, 83, 86, 118, 128, 138, 139, 134, 135}


def _alto_h264(sps):
    b = _Bits(sps)
    perfil = b.bits(8)
    b.bits(16)
    b.ue()
    croma = 1
    if perfil in _PERFILES_CON_CROMA:
        croma = b.ue()
        if croma == 3:
            b.bit()
        b.ue()
        b.ue()
        b.bit()
        if b.bit():   # matrices de escalado: se saltean
            for i in range(12 if croma == 3 else 8):
                if b.bit():
                    ultimo = siguiente = 8
                    for _ in range(16 if i < 6 else 64):
                        if siguiente:
                            siguiente = (ultimo + b.se() + 256) % 256
                        ultimo = siguiente or ultimo
    b.ue()
    orden = b.ue()
    if orden == 0:
        b.ue()
    elif orden == 1:
        b.bit()
        b.se()
        b.se()
        cantidad = b.ue()
        if cantidad > 255:
            raise ValueError('SPS inválido')
        for _ in range(cantidad):
            b.se()
    b.ue()
    b.bit()
    b.ue()   # ancho
    alto_en_bloques = b.ue()
    solo_cuadros = b.bit()
    if not solo_cuadros:
        b.bit()
    b.bit()
    alto = (2 - solo_cuadros) * (alto_en_bloques + 1) * 16
    if b.bit():   # recorte
        b.ue()
        b.ue()
        arriba, abajo = b.ue(), b.ue()
        unidad = (2 - solo_cuadros) * (2 if croma == 1 else 1)
        alto -= unidad * (arriba + abajo)
    return alto


def _alto_h265(sps):
    b = _Bits(sps)
    b.bits(4)
    subcapas = b.bits(3)
    b.bit()
    b.bits(88)   # perfil general
    b.bits(8)    # nivel general
    presentes = [(b.bit(), b.bit()) for _ in range(subcapas)]
    if subcapas:
        b.bits(2 * (8 - subcapas))
    for perfil, nivel in presentes:
        if perfil:
            b.bits(88)
        if nivel:
            b.bits(8)
    b.ue()
    croma = b.ue()
    if croma == 3:
        b.bit()
    b.ue()   # ancho
    alto = b.ue()
    if b.bit():   # ventana de recorte
        b.ue()
        b.ue()
        arriba, abajo = b.ue(), b.ue()
        alto -= (2 if croma == 1 else 1) * (arriba + abajo)
    return alto


def _alto_seguro(leer, datos):
    try:
        alto = leer(datos.replace(b'\x00\x00\x03', b'\x00\x00'))
    except (IndexError, ValueError):
        return 0
    return alto if 100 <= alto <= 4320 else 0


def alto_en_el_video(datos, codec):
    """Las líneas de la imagen leyendo el SPS del video "crudo" (00 00 01 + encabezado). 0 = no se sabe."""
    codec = (codec or '').split('_')[0]
    if codec not in ('h264', 'h265'):
        return 0
    i = datos.find(b'\x00\x00\x01')
    while 0 <= i < len(datos) - 5:
        encabezado = datos[i + 3]
        if codec == 'h264' and encabezado & 0x1F == 7:
            return _alto_seguro(_alto_h264, datos[i + 4:i + 4 + 300])
        if codec == 'h265' and (encabezado >> 1) & 0x3F == 33:
            return _alto_seguro(_alto_h265, datos[i + 5:i + 5 + 300])
        i = datos.find(b'\x00\x00\x01', i + 3)
    return 0


# ── MKV ──────────────────────────────────────────────────────────────

_AUDIO_MKV = {'A_AAC': 'aac', 'A_AC3': 'ac3', 'A_EAC3': 'eac3', 'A_DTS': 'dts', 'A_MPEG/L3': 'mp3',
              'A_MPEG/L2': 'mp2', 'A_OPUS': 'opus', 'A_VORBIS': 'vorbis', 'A_FLAC': 'flac', 'A_TRUEHD': 'truehd'}
# El comienzo de cada pista (TrackEntry 0xAE + tamaño) seguido de su número (TrackNumber 0xD7)
_PISTA_MKV = re.compile(rb'\xae(?:[\x80-\xff]|[\x40-\x7f].|[\x20-\x3f]..|[\x10-\x1f]...)\xd7', re.S)


def _texto_ebml(datos, etiqueta):
    """El texto de un elemento corto (tamaño de un byte) dentro de estos datos, o ''."""
    posicion = datos.find(etiqueta)
    if posicion < 0 or posicion + len(etiqueta) >= len(datos):
        return ''
    tamanio = datos[posicion + len(etiqueta)]
    if not tamanio & 0x80:
        return ''
    inicio = posicion + len(etiqueta) + 1
    return datos[inicio:inicio + (tamanio & 0x7F)].decode('latin-1', errors='replace').strip('\x00')


def _numero_ebml(datos, etiqueta):
    posicion = datos.find(etiqueta)
    if posicion < 0 or posicion + len(etiqueta) >= len(datos):
        return None
    tamanio = datos[posicion + len(etiqueta)]
    if not tamanio & 0x80 or not 1 <= tamanio & 0x7F <= 8:
        return None
    inicio = posicion + len(etiqueta) + 1
    return datos[inicio:inicio + (tamanio & 0x7F)]


def _analizar_mkv(datos):
    resultado = Analisis()
    pistas_en = datos.find(b'\x16\x54\xae\x6b')   # "Tracks"
    if pistas_en >= 0:
        comienzos = [m.start() for m in _PISTA_MKV.finditer(datos, pistas_en)]
        hay_video = False
        for n, comienzo in enumerate(comienzos):
            pista = datos[comienzo:comienzos[n + 1] if n + 1 < len(comienzos) else comienzo + 4096]
            codec = _texto_ebml(pista, b'\x86')
            if codec.startswith('V_'):
                hay_video = True
                alto = _numero_ebml(pista[pista.find(b'\xe0'):] if b'\xe0' in pista else b'', b'\xba')
                if alto and not resultado.alto:
                    resultado.alto = int.from_bytes(alto, 'big')
            elif codec.startswith('A_'):
                nombre = _AUDIO_MKV.get(codec, codec[2:].split('/')[0].lower())
                if nombre not in resultado.audios:
                    resultado.audios.append(nombre)
                _agregar_idioma(resultado.idiomas,
                                _texto_ebml(pista, b'\x22\xb5\x9d') or _texto_ebml(pista, b'\x22\xb5\x9c'))
        if hay_video:
            resultado.con_audio = bool(resultado.audios)
    # Cuánto dura: Duration (en "ticks") x TimestampScale (nanosegundos por tick, 1 ms si no lo dice)
    duracion = _numero_ebml(datos, b'\x44\x89')
    if duracion and len(duracion) in (4, 8):
        escala = _numero_ebml(datos, b'\x2a\xd7\xb1')
        nanos = int.from_bytes(escala, 'big') if escala else 1_000_000
        ticks = struct.unpack('>f' if len(duracion) == 4 else '>d', duracion)[0]
        if 0 < ticks * nanos / 1e9 < 24 * 3600:
            resultado.duracion = ticks * nanos / 1e9
    return resultado


# ── MP4 ──────────────────────────────────────────────────────────────

_AUDIO_MP4 = {b'mp4a': 'aac', b'ac-3': 'ac3', b'ec-3': 'eac3', b'dtsc': 'dts', b'dtsh': 'dts', b'Opus': 'opus',
              b'.mp3': 'mp3', b'fLaC': 'flac'}
_VIDEO_MP4 = (b'avc1', b'avc3', b'hvc1', b'hev1', b'av01', b'vp09', b'mp4v')


def _analizar_mp4(datos):
    """Solo si el índice ("moov") está al principio: si está al final, no se sabe nada."""
    resultado = Analisis()
    moov = datos.find(b'moov')
    if moov < 0:
        return resultado
    try:
        mvhd = datos.find(b'mvhd', moov)
        if mvhd >= 0:
            if datos[mvhd + 4] == 1:
                escala, duracion = struct.unpack('>IQ', datos[mvhd + 24:mvhd + 36])
            else:
                escala, duracion = struct.unpack('>II', datos[mvhd + 16:mvhd + 24])
            if escala and 0 < duracion / escala < 24 * 3600:
                resultado.duracion = duracion / escala
        manejadores = []
        for mdhd in (m.start() for m in re.finditer(b'mdhd', datos)):
            corrido = 36 if datos[mdhd + 4] == 1 else 24
            empaquetado = struct.unpack('>H', datos[mdhd + corrido:mdhd + corrido + 2])[0]
            idioma = ''.join(chr(((empaquetado >> d) & 0x1F) + 0x60) for d in (10, 5, 0))
            hdlr = datos.find(b'hdlr', mdhd)
            if hdlr >= 0:
                manejadores.append((datos[hdlr + 12:hdlr + 16], idioma))
        if any(tipo == b'vide' for tipo, _ in manejadores):
            resultado.con_audio = any(tipo == b'soun' for tipo, _ in manejadores)
        for tipo, idioma in manejadores:
            if tipo == b'soun':
                _agregar_idioma(resultado.idiomas, idioma)
        stsd = datos.find(b'stsd', moov)
        while stsd >= 0:
            for marca, nombre in _AUDIO_MP4.items():
                if datos[stsd + 16:stsd + 20] == marca and nombre not in resultado.audios:
                    resultado.audios.append(nombre)
            if datos[stsd + 16:stsd + 20] in _VIDEO_MP4 and not resultado.alto:
                entrada = stsd + 16
                alto = struct.unpack('>H', datos[entrada + 30:entrada + 32])[0]
                resultado.alto = alto if 100 <= alto <= 4320 else 0
            stsd = datos.find(b'stsd', stsd + 4)
    except struct.error:
        pass
    return resultado


# ── Todo junto ───────────────────────────────────────────────────────

def analizar(datos, codec=''):
    """Lo que se puede saber de estos bytes de video (MPEG-TS, MKV o MP4)."""
    if not datos:
        return Analisis()
    if es_mpeg_ts(datos):
        return _analizar_ts(datos, codec)
    if datos[:4] == b'\x1aE\xdf\xa3':
        return _analizar_mkv(datos)
    if datos[4:8] in (b'ftyp', b'moov') or b'moov' in datos[:64]:
        return _analizar_mp4(datos)
    return Analisis()


def de_la_maestra(texto):
    """La resolución más alta y los idiomas del audio que ofrece una lista HLS maestra."""
    resultado = Maestra()
    for linea in texto.splitlines():
        linea = linea.strip()
        if linea.startswith('#EXT-X-STREAM-INF'):
            resolucion = re.search(r'RESOLUTION=(\d+)x(\d+)', linea)
            if resolucion:
                resultado.alto = max(resultado.alto, int(resolucion.group(2)))
        elif linea.startswith('#EXT-X-MEDIA') and re.search(r'TYPE=AUDIO', linea):
            resultado.audio_aparte = resultado.audio_aparte or 'URI=' in linea
            idioma = re.search(r'LANGUAGE="([^"]*)"', linea)
            if idioma:
                _agregar_idioma(resultado.idiomas, idioma.group(1))
    return resultado
