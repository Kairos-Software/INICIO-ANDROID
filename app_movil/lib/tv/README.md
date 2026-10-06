# lib/tv/

La app en la **TV** (Android TV / Google TV), manejada con el control remoto.
El diseño está en `diseno_kairos_tv/` (pantallas `tv-*`, y el recorrido del
control en `DESIGN.md`). Usa los mismos datos, reproductor y colores que el
celular (`lib/movil/datos.dart`, `control_senal.dart`, `estilo.dart`).

**Todo se dibuja en un lienzo de 1920×1080** (las medidas del diseño) y se
escala a la pantalla (`escala.dart`): así se ve igual en cualquier televisor.

| Archivo | Qué es | Diseño |
|---|---|---|
| `escala.dart` | El lienzo de 1920×1080 que se agranda o achica a la pantalla. | — |
| `foco.dart` | `Enfocable`: lo elegido con el control se agranda, con borde celeste y brillo. OK y **OK largo** (mantener apretado). `BotonTv`. | "Foco TV" |
| `piezas.dart` | Encabezado, chips, tarjetas de canal y de póster, filas, avisos cortos, favoritos con OK largo. | todas |
| `estructura.dart` | El menú de la izquierda (se abre al entrar en él) y las 8 secciones. "Atrás" vuelve a Inicio; en Inicio pregunta si salir. "Volver al último canal" con cuenta regresiva. Cuida que el foco nunca quede "en el aire" (si cae en la pantalla en general, lo pasa al contenido; si igual se pierde, la primera tecla lo recupera). Cuenta el tiempo sin tocar el control para el modo reposo. | `tv-20` |
| `reposo.dart` | El modo reposo: a los 3 minutos sin tocar el control (y sin nada reproduciéndose) aparece la pantalla del logo con la hora y, entre una y otra, títulos del catálogo (película, serie, canal) con su imagen de fondo. Siempre vuelve al logo. Cualquier botón vuelve a donde se estaba. Mantiene la pantalla encendida 30 minutos. | — |
| `inicio.dart` | Portada con un canal en vivo, favoritos, últimos vistos, continuar viendo, una fila por categoría, películas y series. | `tv-04` |
| `en_vivo.dart` | Los canales como tarjetas: una fila por categoría, o la grilla de una categoría. | `tv-05` |
| `guia.dart` | Categorías a la izquierda, todos los canales en lista a la derecha. Los números del control saltan a un canal. | `tv-06` |
| `grilla.dart` | Películas y Series: chips y grilla de pósters. | `tv-08`, `tv-09` |
| `detalle.dart` | Detalle de película (Reproducir/Continuar, Favoritos, similares) y de serie (temporadas y episodios con lo visto). | `tv-10`, `tv-11` |
| `reproductor.dart` | En vivo: un cartel con el canal que solo informa (Atrás sale directo); **OK abre la guía** encima del video (parada en el canal actual); ↑ ↓ o CH+/CH- zapping; ← → las opciones (guía, favoritos, fuente); números. Películas y capítulos: OK pausa; ← → ±10 s; ↑ ↓ la barra (siguiente episodio, favoritos, fuente). Lo que se abre lleva el foco a su primer botón, se cierra con Atrás o solo. Error de señal con "Probar de nuevo". | `tv-12`, `tv-13`, `tv-19` |
| `buscar.dart` | Teclado en pantalla y resultados (canales, películas, series). | `tv-14` |
| `favoritos.dart` | Canales, películas y series guardados; vacío: "Explorar contenido". | `tv-15`, `tv-21` |
| `cuenta.dart` | Datos de la cuenta y preferencias (volver al último canal, modo de video "TV" o "compatible" por si la imagen sale verde, buscar actualizaciones, cerrar sesión). | `tv-16` |

El login, "Tu servicio venció" y la carga son los mismos del celular
(`lib/acceso.dart`), que en pantalla ancha se parten en dos columnas.

## El control remoto

| Tecla | Qué hace |
|---|---|
| Flechas | Moverse. Izquierda en el borde izquierdo del contenido abre el menú (parado en la sección actual); Derecha vuelve al contenido. |
| OK | Abrir, reproducir, confirmar. |
| OK largo | Agregar o quitar de favoritos (sobre una tarjeta). |
| Atrás | Cierra lo que esté abierto (también el menú); en una sección vuelve a Inicio; en Inicio pregunta si salir. |
| Arriba/Abajo, CH+/CH- (viendo un canal) | Zapping. |
| OK o Guía (viendo un canal) | La guía de canales encima del video. |
| Izquierda/Derecha (viendo un canal) | Las opciones: guía, favoritos, fuente. |
| Números (viendo un canal o en la guía) | Ir al canal con ese número. |
| Play/Pausa, adelantar, atrasar | En películas y capítulos. |
