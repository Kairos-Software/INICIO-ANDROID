# assets/bienvenida/

La presentación en video que aparece al abrir la app (`lib/bienvenida.dart`).

| Archivo | Qué es |
|---|---|
| `intro_tv.mp4` | Video horizontal 16:9 para Android TV y celulares acostados (1920×1080). |
| `intro_celular.mp4` | Video vertical 9:16 para celulares parados (1080×1920). |

Los dos videos duran ocho segundos e incluyen su propia pista de audio. No debe
agregarse ni reproducirse un archivo de sonido separado.

La presentación llena toda la pantalla con `BoxFit.cover`; si la relación de
aspecto del aparato difiere ligeramente, se recortan solamente los bordes. El
logo y la información importante deben permanecer dentro del área central.

Mientras Flutter prepara el primer cuadro, Android muestra una pantalla lisa de
color `#07090C` (sin otro logo). Así la app pasa directamente al video y evita
mostrar dos presentaciones distintas durante el arranque.

Si se reemplazan los videos, deben mantenerse los nombres, la duración y las
relaciones de aspecto. `Bienvenida.duracion` y `Bienvenida.desvanecer` controlan
la salida hacia la aplicación.
