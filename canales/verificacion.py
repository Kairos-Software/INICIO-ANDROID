"""
Comprueba si las fuentes responden (capa Base, no toca la base de datos).

Hace lo mismo que el reproductor de la app, pero desde el servidor:

  1. Pide la lista .m3u8 y comprueba que sea una lista HLS (#EXTM3U).
  2. Si es una lista "maestra" (la que ofrece varias calidades), pide la
     primera calidad: muchas veces la maestra responde y la señal no.
  3. Pide el pedazo de video MÁS RECIENTE (por ahí arranca el reproductor):
     hay servidores que entregan la lista pero rechazan el video.

Se presenta igual que el reproductor de la app (USER_AGENT_REPRODUCTOR, o
el User-Agent / Referer propio de la fuente): hay canales que bloquean a
los reproductores que no parecen un navegador, y si el verificador se
presentara distinto, diría "funciona" a algo que en la app no anda.

YouTube no se puede comprobar sin la API de YouTube -> "sin verificar".

Cada pedido espera como máximo TIEMPO_MAXIMO segundos y se verifican
HILOS fuentes a la vez (una lista de 100 fuentes tarda menos de 1 minuto).

    from canales.verificacion import verificar_url, verificar_varias
    verificar_url('https://.../playlist.m3u8')        -> Resultado('funciona')
    verificar_varias({url: 'hls', url2: 'youtube'})   -> {url: Resultado, ...}
"""

import http.client
import socket
import ssl
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from urllib.parse import urljoin

TIEMPO_MAXIMO = 9      # segundos por pedido (el HTML usa 9)
HILOS = 10             # fuentes verificadas a la vez
MAX_BYTES = 512 * 1024  # una lista .m3u8 pesa pocos KB: no hace falta leer más
BYTES_DE_VIDEO = 32 * 1024  # del pedazo de video alcanza con ver que empieza a llegar

# Cómo se presenta el reproductor de la app (la API se lo manda junto con
# cada fuente). Como un navegador de celular: hay servidores de canales que
# rechazan a "ExoPlayer" (el reproductor de Android) con error 403.
USER_AGENT_REPRODUCTOR = ('Mozilla/5.0 (Linux; Android 14; K) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/124.0.0.0 Mobile Safari/537.36')

FUNCIONA = 'funciona'
CAIDA = 'caida'
SIN_VERIFICAR = 'sin_verificar'


@dataclass
class Resultado:
    estado: str      # FUNCIONA, CAIDA o SIN_VERIFICAR
    error: str = ''  # por qué falló (para mostrar en el panel)


def cabeceras_para(user_agent='', referer=''):
    """Las cabeceras con que se pide la señal (las mismas que usa la app)."""
    cabeceras = {'User-Agent': user_agent or USER_AGENT_REPRODUCTOR}
    if referer:
        cabeceras['Referer'] = referer
    return cabeceras


def _descargar(url, cabeceras, maximo=MAX_BYTES):
    """(texto, dirección final después de redirecciones)."""
    pedido = urllib.request.Request(url, headers=cabeceras)
    with urllib.request.urlopen(pedido, timeout=TIEMPO_MAXIMO) as respuesta:
        texto = respuesta.read(maximo).decode('utf-8', errors='replace')
        return texto, respuesta.geturl()


def _es_lista_hls(texto):
    return texto.lstrip('﻿ \r\n\t').startswith('#EXTM3U')


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
    if error.code == 403:
        return Resultado(CAIDA, f'El canal no entrega {que} al reproductor (error 403).')
    return Resultado(CAIDA, f'El servidor respondió con error {error.code} al pedir {que}.')


def verificar_url(url, tipo='hls', user_agent='', referer=''):
    if tipo == 'youtube':
        return Resultado(SIN_VERIFICAR, 'YouTube no se puede verificar desde el servidor.')
    cabeceras = cabeceras_para(user_agent, referer)
    que = 'la lista'
    try:
        texto, final = _descargar(url, cabeceras)
        if not _es_lista_hls(texto):
            return Resultado(CAIDA, 'Responde, pero no es una lista HLS.')
        calidad = _primera_calidad(texto, final)
        if calidad:
            texto, final = _descargar(calidad, cabeceras)
            if not _es_lista_hls(texto):
                return Resultado(CAIDA, 'La lista responde, pero la señal no.')
        pedazos = _direcciones(texto)
        if not pedazos:
            return Resultado(CAIDA, 'La lista no tiene video (está vacía).')
        que = 'el video'
        _descargar(urljoin(final, pedazos[-1]), cabeceras, BYTES_DE_VIDEO)   # el más reciente
        return Resultado(FUNCIONA)
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
        return Resultado(CAIDA, f'No se pudo conectar ({error.reason}).'[:200])
    except TimeoutError:
        return Resultado(CAIDA, 'No respondió a tiempo.')
    except (OSError, ValueError, http.client.HTTPException) as error:
        return Resultado(CAIDA, f'Error: {error}'[:200])


def verificar_varias(fuentes, cabeceras=None):
    """
    {url: tipo} -> {url: Resultado}. Verifica varias a la vez.
    `cabeceras`: {url: (user_agent, referer)} para las fuentes que tienen las suyas.
    """
    if not fuentes:
        return {}
    cabeceras = cabeceras or {}

    def una(par):
        url, tipo = par
        return verificar_url(url, tipo, *cabeceras.get(url, ('', '')))

    with ThreadPoolExecutor(max_workers=HILOS) as hilos:
        return dict(zip(fuentes, hilos.map(una, fuentes.items())))
