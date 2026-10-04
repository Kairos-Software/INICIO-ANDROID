"""
Genera TODAS las imágenes de la marca de la app a partir de un solo archivo:
assets/logo/original.png (el logo de Kairos TV, 1254x1254, sin fondo).

    python tools/generar_marca.py
    dart run flutter_launcher_icons      # después: arma los íconos de Android

Si cambia el logo, se reemplaza original.png y se vuelven a correr los dos.
El televisor (símbolo) y el texto "KairosTV" se separan en la fila CORTE.
"""

from pathlib import Path

from PIL import Image

AQUI = Path(__file__).resolve().parent.parent
LOGO = AQUI / 'assets/logo'
RES = AQUI / 'android/app/src/main/res'
CORTE = 880                       # donde termina el televisor y empieza el texto
FONDO = (0x05, 0x0D, 0x1D)        # Colores.fondo de lib/tema.dart (azul noche)


def recortar(imagen):
    """Saca el borde transparente."""
    return imagen.crop(imagen.getchannel('A').getbbox())


def centrar(imagen, lado, ocupa, fondo=None):
    """La imagen centrada en un cuadrado de `lado`, ocupando `ocupa` (0 a 1) del lado."""
    lienzo = Image.new('RGBA', (lado, lado), fondo + (255,) if fondo else (0, 0, 0, 0))
    copia = imagen.copy()
    copia.thumbnail((int(lado * ocupa), int(lado * ocupa)), Image.LANCZOS)
    lienzo.alpha_composite(copia, ((lado - copia.width) // 2, (lado - copia.height) // 2))
    return lienzo


original = Image.open(LOGO / 'original.png').convert('RGBA')
logo = recortar(original)
simbolo = recortar(original.crop((0, 0, original.width, CORTE)))
texto = recortar(original.crop((0, CORTE, original.width, original.height)))

# Dentro de la app (login, pantallas)
logo.save(LOGO / 'logo.png')
simbolo.save(LOGO / 'simbolo.png')

# Ícono: Android viejo (cuadrado con fondo) y adaptable (Android 8+: el
# frente con margen, porque cada marca lo recorta con su forma)
centrar(simbolo, 1024, 0.86, FONDO).convert('RGB').save(LOGO / 'icono.png')
centrar(simbolo, 1024, 0.62).save(LOGO / 'icono_frente.png')

# Pantalla de arranque (lo que se ve mientras carga), una por densidad de pantalla
for carpeta, ancho in {'mdpi': 160, 'hdpi': 240, 'xhdpi': 320, 'xxhdpi': 480, 'xxxhdpi': 640}.items():
    copia = simbolo.copy()
    copia.thumbnail((ancho, ancho), Image.LANCZOS)
    copia.save(RES / f'drawable-{carpeta}' / 'arranque_simbolo.png')

# Banner de Android TV (320x180): televisor a la izquierda y "KairosTV" a la derecha
banner = Image.new('RGBA', (320, 180), FONDO + (255,))
chico = simbolo.copy()
chico.thumbnail((130, 130), Image.LANCZOS)
banner.alpha_composite(chico, (14, (180 - chico.height) // 2))
letras = texto.copy()
letras.thumbnail((320 - chico.width - 40, 90), Image.LANCZOS)
banner.alpha_composite(letras, (14 + chico.width + 10, (180 - letras.height) // 2))
banner.convert('RGB').save(RES / 'drawable-xhdpi' / 'banner.png')

print('Listo: logo, símbolo, íconos, arranque y banner.')
