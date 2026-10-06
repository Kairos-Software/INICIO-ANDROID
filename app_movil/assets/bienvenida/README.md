# assets/bienvenida/

La presentación que aparece al abrir la app, en la TV y en el celular (`lib/bienvenida.dart`).

| Archivo | Qué es |
|---|---|
| `portada.jpg` | La imagen de Kairos TV (16:9). En la TV y en el celular acostado llena la pantalla; en el celular parado se ve entera, con fondo oscuro arriba y abajo. |
| `sonido.mp3` | El sonido (4 s). Es *"Modern Tech Logo"* de muzaproduction, de [Pixabay](https://pixabay.com/): uso libre en apps, sin pagar ni nombrar al autor. Se le agregó un final suave de medio segundo. |

Para cambiarlos, se reemplaza el archivo por otro **con el mismo nombre**. Si el
sonido nuevo dura distinto, se ajusta `Bienvenida.duracion` en `lib/bienvenida.dart`.
