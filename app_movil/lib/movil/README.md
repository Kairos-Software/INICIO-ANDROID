# lib/movil/

La app en el **celular**, con el diseño de Stitch ("Lumix TV", adaptado a
Kairos TV), más lo que agregó el diseño de ChatGPT (`diseno_kairos_tv/`):
TV en vivo primero en Inicio, Favoritos, la guía y "volver al último canal".
La **TV** está en `lib/tv/` (usa los datos, el reproductor y los colores de
acá); se decide en `main.dart` según `Aparato.esTv`.

Los originales de Stitch (código, captura y `DESIGN.md` de cada pantalla)
están fuera del repo, en `D:\Desktop\diseños app pv\stitch\`. Los valores
(colores, letras, tamaños, curvas) se copiaron tal cual de ahí.

| Archivo | Qué es | Pantalla de Stitch |
|---|---|---|
| `estilo.dart` | Los tokens: colores (`Tono`), letras (`Letra`; `LetraTv`, más grandes, para la TV), curvas, espacios, brillo celeste y el tema de Flutter. | `DESIGN.md` |
| `datos.dart` | `Catalogo` (canales en vivo, películas y series pedidos a la API; arma las series agrupando capítulos "Show S01 E02"; numera los canales; favoritos por tipo; trae **solo lo que este aparato puede ver**: saca lo que tiene un códec que el aparato no muestra, las series que no arrancan en T1:E1 o tienen menos de 3 capítulos, y lo de `NoAnda`), `NoAnda` (lo que no se pudo ver en este aparato con ninguna fuente deja de mostrarse: 6 h en vivo, 3 días películas y capítulos, 30 días si es de formato) y `Biblioteca` (favoritos, "Continuar viendo", últimos canales vistos y "volver al último canal", guardados en el aparato). | — |
| `control_senal.dart` | Reproduce probando las fuentes en orden (si una falla o se traba, pasa a la siguiente y le avisa al servidor **por qué**: formato que el aparato no lee, rechazo, tardó demasiado...; ver `Falla`). Si suena pero no hay imagen a los 8 s, también cuenta como falla (menos las radios). Si una fuente venía andando y se corta, primero reconecta a la misma (una película sigue donde iba); en vivo, si se caen todas, da hasta 2 vueltas más. `enSuperficie`: dibuja el video en una superficie de Android (lo que usa la TV, evita la imagen verde). Si no anda ninguna, lo anota en `NoAnda`. También la calidad, el idioma y el ajuste de imagen (ver `ajustes_video.dart`). Lo usan todos los reproductores, también los de la TV. | — |
| `ajustes_video.dart` | Los **Ajustes** del video mientras se mira: Calidad (Automática o 1080p, 720p... con sus Mbps, en las señales que traen varias), Idioma del audio (si hay más de uno), Imagen (Ajustar / Llenar / Estirar) y Fuente. En el celular es una hoja de abajo (`ajustesDeVideoMovil`); en la TV, un cuadro manejado con el control (`tv/reproductor.dart`). | — |
| `componentes.dart` | Piezas repetidas: insignia EN VIVO con el punto que late, chips, tarjetas (póster, en vivo, continuar viendo), botones, encabezados. | todas |
| `estructura.dart` | La barra de arriba, las 6 secciones y la barra de abajo (Inicio · En Vivo · Series · Películas · Favoritos · Mi Espacio). | barras de todas |
| `inicio.dart` | Chips, portada con un canal en vivo, Tus canales favoritos, Últimos canales vistos, Directos Destacados, Continuar Viendo, Tendencias. | `stitch_modern_streaming_app_ui.zip` + `mobile-04` |
| `guia.dart` | La guía: todos los canales con número, logo y categoría, con buscador y filtro (se abre con "Guía" en En Vivo). | `mobile-05` |
| `favoritos.dart` | Favoritos: canales, películas y series por separado. | `mobile-06`, `mobile-09` |
| `en_vivo.dart` | Reproductor 16:9 arriba + categorías + lista de canales con favoritos; y la pantalla completa horizontal con zapping y Ajustes. | `(1).zip` |
| `detalle.dart` | Detalle de película o serie: portada, Reproducir/Continuar, Mi lista, episodios por temporada, similares. | `(2).zip` |
| `reproductor_vod.dart` | Reproductor de películas y capítulos: controles, barra para adelantar, velocidad, Ajustes (calidad, idioma, imagen, fuente), siguiente capítulo, girar a pantalla completa. Guarda por dónde vas. | `(3).zip` |
| `grilla.dart` | Secciones Películas y Series (grilla de pósters con chips de categoría). | grilla de "Tendencias" |
| `mi_espacio.dart` | Cuenta (código, vencimiento, pantallas, vendedor), Continuar viendo, "volver al último canal al abrir" y, para usuarios del panel, sus herramientas. | armada con sus piezas |
| `buscar.dart` | Buscar canales, películas y series, con los chips Todo / En vivo / Películas / Series (cuántos encontró cada uno). Arranca en el de la sección desde donde se abrió: desde Series busca series. | campo de búsqueda del `DESIGN.md` |
| `busqueda.dart` | La búsqueda en sí, la misma en el celular y en la TV: sin tildes ni mayúsculas, primero lo que empieza con lo escrito (o tiene una palabra que empieza así) y después lo que solo lo contiene. En la TV, el número del canal también lo encuentra. | — |

## Lo que el diseño muestra y todavía no tenemos

No se inventa: esas partes no aparecen hasta tener el dato.

- **Guía de programación** (qué está dando ahora, "A continuación", minutos
  restantes): hace falta cargar la EPG en el servidor.
- **Sinopsis, puntaje, actores, tráiler** de películas y series: hace falta
  traerlos de una base de películas (ej. TMDB).
- **Descargar, Chromecast, subtítulos, calidad 4K/Dolby**: más adelante.
