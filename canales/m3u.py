"""
Lector de listas M3U / M3U8 (capa Base, no toca la base de datos).

Una lista M3U es texto. Cada canal ocupa dos líneas:

    #EXTINF:-1 tvg-id="Canal26.ar" tvg-logo="https://..." tvg-chno="26" group-title="Noticias",Canal 26
    https://servidor/canal26/playlist.m3u8

La primera tiene los datos (atributos clave="valor" y, después de la coma,
el nombre); la segunda, la dirección de la señal.

    from canales.m3u import leer_m3u
    for entrada in leer_m3u(texto):
        entrada.nombre, entrada.url, entrada.categoria, ...
"""

import re
import unicodedata
from dataclasses import dataclass

_ATRIBUTO = re.compile(r'([\w-]+)\s*=\s*"([^"]*)"')
# Marcas que algunas listas agregan al nombre (Ⓨ = YouTube, Ⓖ = geobloqueado...)
_MARCAS = re.compile(r'[ⓎⒼⓈ]')


@dataclass
class EntradaM3U:
    nombre: str
    url: str
    logo: str = ''
    categoria: str = ''
    numero: str = ''
    tvg_id: str = ''
    pais: str = ''

    @property
    def tipo(self):
        return 'youtube' if re.search(r'youtube\.com|youtu\.be', self.url, re.I) else 'hls'


def normalizar(texto):
    """'Canal 26 HD Ⓨ' -> 'canal 26': para reconocer el mismo canal escrito distinto."""
    texto = unicodedata.normalize('NFD', _MARCAS.sub('', texto or ''))
    texto = ''.join(c for c in texto if unicodedata.category(c) != 'Mn').lower()
    texto = re.sub(r'\((\d+p|hd|sd|fhd|4k)\)|\b(hd|sd|fhd|4k)\b', ' ', texto)
    return ' '.join(texto.split())


def leer_m3u(texto):
    """Devuelve la lista de EntradaM3U de una lista M3U (ignora lo que no entiende)."""
    entradas = []
    pendiente = None
    for linea in (texto or '').lstrip('﻿').splitlines():
        linea = linea.strip()
        if not linea:
            continue
        if linea.upper().startswith('#EXTINF'):
            atributos = dict(_ATRIBUTO.findall(linea))
            # El nombre va después de la coma que sigue al último atributo
            fin_atributos = linea.rfind('",')
            if fin_atributos >= 0:
                nombre = linea[fin_atributos + 2:].strip()
            else:
                nombre = linea.split(',', 1)[1].strip() if ',' in linea else ''
            nombre = _MARCAS.sub('', atributos.get('tvg-name') or nombre).strip() or 'Canal'
            pendiente = EntradaM3U(
                nombre=nombre,
                url='',
                logo=atributos.get('tvg-logo', ''),
                categoria=atributos.get('group-title', '').strip(),
                numero=atributos.get('tvg-chno', '').strip(),
                tvg_id=atributos.get('tvg-id', '').strip(),
                pais=atributos.get('tvg-country', '').strip().upper()[:2],
            )
        elif linea.startswith('#'):
            continue   # otras directivas (#EXTM3U, #EXTVLCOPT...) no se usan por ahora
        elif pendiente is not None:
            # Algunas listas agregan opciones después de "|" (cabeceras para VLC)
            pendiente.url = linea.split('|')[0].strip()
            if pendiente.url.lower().startswith(('http://', 'https://')):
                entradas.append(pendiente)
            pendiente = None
    return entradas
