# assets/bienvenida/

La presentación que aparece al abrir la app, en la TV y en el celular (`lib/bienvenida.dart`).

| Archivo | Qué es |
|---|---|
| `portada_tv.jpg` | La imagen **apaisada** (16:9, ideal 1920×1080). Se usa en la TV y en el celular acostado. |
| `portada_celular.jpg` | La imagen **parada** (9:16 o 9:20, ideal 1080×2400). Se usa en el celular parado. |
| `sonido.mp3` | El sonido (7,8 s). Es *"Epic Cinematic Logo Reveal"* de breakzstudios, de [Pixabay](https://pixabay.com/): uso libre en apps, sin pagar ni nombrar al autor. |

Las dos imágenes **llenan toda la pantalla**: si la pantalla no tiene justo su
forma, se recorta un poco de los bordes. Por eso el logo y lo importante tienen
que ir al centro, con margen.

Para cambiarlas, se reemplaza el archivo por otro **con el mismo nombre** (JPG,
menos de 500 KB cada una para que la app abra rápido). Si el sonido nuevo dura
distinto, se ajusta `Bienvenida.duracion` en `lib/bienvenida.dart`.

Mientras arranca, Android muestra una pantalla lisa de color `#07090C` (sin logo),
así se pasa directo a esta imagen. Si las imágenes nuevas tienen otro color de
fondo, conviene cambiar ese color en `Bienvenida.fondo` y en
`android/app/src/main/res/values/colors.xml` (`fondo_arranque`).
