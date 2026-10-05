"""
Genera TODAS las imágenes de la marca de la app: el símbolo (el "portal" de
cuatro paneles con el punto rubí), el logo con el texto, el ícono, el banner
de Android TV y la pantalla de arranque.

    python tools/generar_marca.py
    dart run flutter_launcher_icons      # después: arma los íconos de Android

El símbolo se DIBUJA con las mismas medidas que lib/marca.dart
(GeometriaMarca): si se cambia una, cambiar la otra. Se dibuja 4 veces más
grande y se achica, para que los bordes queden suaves.
"""

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

AQUI = Path(__file__).resolve().parent.parent
LOGO = AQUI / 'assets/logo'
RES = AQUI / 'android/app/src/main/res'
LETRA = AQUI / 'assets/fuentes/PlusJakartaSans-ExtraBold.ttf'

FONDO = (0x13, 0x13, 0x17)        # Tono.fondo (grafito)
CELESTE = (0x00, 0xF0, 0xFF)      # Tono.celeste
RUBI = (0xDF, 0x00, 0x41)         # Tono.rubi
TEXTO = (0xE4, 0xE1, 0xE8)        # Tono.texto
PANEL = (0x16, 0x16, 0x1B)

# lib/marca.dart -> GeometriaMarca
PANELES = [(-1.0, -0.58), (-0.502, -0.102), (0.102, 0.502), (0.58, 1.0)]
COSTADO = 0.437
PENDIENTE = math.tan(math.pi / 6)
MEDIA_ALTURA = COSTADO + PENDIENTE
RADIO_PUNTO = 0.13
GROSOR = 0.037
SUPER = 4


def techo(x):
    return -(COSTADO + PENDIENTE * (1 - abs(x)))


def simbolo(alto, brillo=True, grosor=GROSOR):
    """El símbolo sobre fondo transparente, de `alto` píxeles (con lugar para el brillo)."""
    margen = 0.18 if brillo else 0.04
    escala = alto * SUPER / (2 * MEDIA_ALTURA) / (1 + margen)
    ancho = int(2 * escala * (1 + margen))
    lienzo = (ancho, alto * SUPER)
    cx, cy = lienzo[0] / 2, lienzo[1] / 2

    def punto(x, y):
        return (cx + x * escala, cy + y * escala)

    paneles = [[punto(a, techo(a)), punto(b, techo(b)), punto(b, -techo(b)), punto(a, -techo(a))]
               for a, b in PANELES]
    linea = max(int(grosor * escala), 2)
    radio = RADIO_PUNTO * escala

    capas = Image.new('RGBA', lienzo, (0, 0, 0, 0))
    if brillo:
        halo = Image.new('RGBA', lienzo, (0, 0, 0, 0))
        dibujo = ImageDraw.Draw(halo)
        for panel in paneles:
            dibujo.polygon(panel, outline=CELESTE + (150,), width=linea * 3)
        dibujo.ellipse([cx - radio * 1.7, cy - radio * 1.7, cx + radio * 1.7, cy + radio * 1.7], fill=RUBI + (140,))
        capas.alpha_composite(halo.filter(ImageFilter.GaussianBlur(linea * 3)))

    dibujo = ImageDraw.Draw(capas)
    for panel in paneles:
        dibujo.polygon(panel, fill=PANEL + (255,), outline=CELESTE + (255,), width=linea)
    dibujo.ellipse([cx - radio, cy - radio, cx + radio, cy + radio], fill=RUBI + (255,))
    return capas.resize((lienzo[0] // SUPER, lienzo[1] // SUPER), Image.LANCZOS)


def recortar(imagen):
    """Saca el borde transparente."""
    return imagen.crop(imagen.getchannel('A').getbbox())


def centrar(imagen, ancho, alto, ocupa, fondo=None):
    """La imagen centrada, ocupando `ocupa` (0 a 1) del alto."""
    lienzo = Image.new('RGBA', (ancho, alto), fondo + (255,) if fondo else (0, 0, 0, 0))
    copia = imagen.copy()
    copia.thumbnail((int(ancho * ocupa), int(alto * ocupa)), Image.LANCZOS)
    lienzo.alpha_composite(copia, ((ancho - copia.width) // 2, (alto - copia.height) // 2))
    return lienzo


def con_luz(ancho, alto):
    """El fondo grafito con una luz celeste suave en el centro (el de las pantallas de la app)."""
    fondo = Image.new('RGBA', (ancho, alto), FONDO + (255,))
    luz = Image.new('RGBA', (ancho, alto), (0, 0, 0, 0))
    lado = min(ancho, alto)
    ImageDraw.Draw(luz).ellipse(
        [ancho / 2 - lado * .38, alto / 2 - lado * .38, ancho / 2 + lado * .38, alto / 2 + lado * .38],
        fill=(0x0B, 0x3B, 0x42, 160))
    fondo.alpha_composite(luz.filter(ImageFilter.GaussianBlur(lado * .14)))
    return fondo


def logo_horizontal(alto, grosor=GROSOR):
    """El símbolo y "KairosTV" al lado ("TV" en celeste), sin fondo."""
    marca = recortar(simbolo(alto, grosor=grosor))
    letra = ImageFont.truetype(str(LETRA), int(alto * 0.62))
    medida = ImageDraw.Draw(Image.new('RGBA', (1, 1)))
    ancho_kairos = medida.textlength('Kairos', font=letra)
    ancho_tv = medida.textlength('TV', font=letra)
    separacion = int(alto * 0.3)
    lienzo = Image.new('RGBA', (marca.width + separacion + int(ancho_kairos + ancho_tv) + 8, marca.height),
                       (0, 0, 0, 0))
    lienzo.alpha_composite(marca, (0, 0))
    dibujo = ImageDraw.Draw(lienzo)
    x, y = marca.width + separacion, marca.height / 2
    dibujo.text((x, y), 'Kairos', font=letra, fill=TEXTO, anchor='lm')
    dibujo.text((x + ancho_kairos, y), 'TV', font=letra, fill=CELESTE, anchor='lm')
    return lienzo


if __name__ == '__main__':
    # Dentro de la app y para el panel
    recortar(simbolo(1024)).save(LOGO / 'simbolo.png')
    logo_horizontal(400).save(LOGO / 'logo.png')

    # Ícono: Android viejo (cuadrado con fondo) y adaptable (Android 8+: el
    # frente sin fondo y con margen, porque cada marca lo recorta con su forma)
    icono = con_luz(1024, 1024)
    icono.alpha_composite(centrar(simbolo(1024), 1024, 1024, 0.7))
    icono.convert('RGB').save(LOGO / 'icono.png')
    centrar(simbolo(1024), 1024, 1024, 0.8).save(LOGO / 'icono_frente.png')

    # Pantalla de arranque (lo que se ve mientras carga), una por densidad de pantalla
    for carpeta, alto in {'mdpi': 96, 'hdpi': 144, 'xhdpi': 192, 'xxhdpi': 288, 'xxxhdpi': 384}.items():
        simbolo(alto).save(RES / f'drawable-{carpeta}' / 'arranque_simbolo.png')

    # Banner de Android TV (320x180): el logo horizontal sobre grafito con luz
    banner = con_luz(320, 180)
    # Se dibuja al tamaño final y con líneas más gruesas: achicado, el símbolo se borra
    logo = logo_horizontal(64, grosor=0.08)
    banner.alpha_composite(logo, ((320 - logo.width) // 2, (180 - logo.height) // 2))
    banner.convert('RGB').save(RES / 'drawable-xhdpi' / 'banner.png')
    print('Listo. Ahora: dart run flutter_launcher_icons')
