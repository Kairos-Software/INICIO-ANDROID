# lib/movil/

La app en el **celular**, con el diseño de Stitch ("Lumix TV", adaptado a
Kairos TV). La **TV** todavía usa el diseño anterior (`lib/pantallas/`); se
decide en `main.dart` según `Aparato.esTv`.

Los originales de Stitch (código, captura y `DESIGN.md` de cada pantalla)
están fuera del repo, en `D:\Desktop\diseños app pv\stitch\`. Los valores
(colores, letras, tamaños, curvas) se copiaron tal cual de ahí.

| Archivo | Qué es | Pantalla de Stitch |
|---|---|---|
| `estilo.dart` | Los tokens: colores (`Tono`), letras (`Letra`: Plus Jakarta Sans e Inter), curvas, espacios, brillo celeste y el tema de Flutter. | `DESIGN.md` |
| `datos.dart` | `Catalogo` (canales en vivo, películas y series pedidos a la API; arma las series agrupando capítulos "Show S01 E02") y `Biblioteca` ("Mi lista" y "Continuar viendo", guardados en el aparato). | — |
| `control_senal.dart` | Reproduce probando las fuentes en orden (si una falla o se traba, pasa a la siguiente y avisa al servidor). Lo usan todos los reproductores. | — |
| `componentes.dart` | Piezas repetidas: insignia EN VIVO con el punto que late, chips, tarjetas (póster, en vivo, continuar viendo), botones, encabezados. | todas |
| `estructura.dart` | La barra de arriba, las 5 secciones y la barra de abajo (Inicio · En Vivo · Series · Películas · Mi Espacio). | barras de todas |
| `inicio.dart` | Chips, portada destacada, Continuar Viendo, Directos Destacados, Tendencias. | `stitch_modern_streaming_app_ui.zip` |
| `en_vivo.dart` | Reproductor 16:9 arriba + categorías + lista de canales con favoritos; y la pantalla completa horizontal con zapping. | `(1).zip` |
| `detalle.dart` | Detalle de película o serie: portada, Reproducir/Continuar, Mi lista, episodios por temporada, similares. | `(2).zip` |
| `reproductor_vod.dart` | Reproductor de películas y capítulos: controles, barra para adelantar, velocidad, fuente, siguiente capítulo, girar a pantalla completa. Guarda por dónde vas. | `(3).zip` |
| `grilla.dart` | Secciones Películas y Series (grilla de pósters con chips de categoría). | grilla de "Tendencias" |
| `mi_espacio.dart` | Cuenta (código, vencimiento, pantallas), Continuar viendo, Mi lista y, para usuarios del panel, sus herramientas. | armada con sus piezas |
| `buscar.dart` | Buscar canales, películas y series. | campo de búsqueda del `DESIGN.md` |

## Lo que el diseño muestra y todavía no tenemos

No se inventa: esas partes no aparecen hasta tener el dato.

- **Guía de programación** (qué está dando ahora, "A continuación", minutos
  restantes): hace falta cargar la EPG en el servidor.
- **Sinopsis, puntaje, actores, tráiler** de películas y series: hace falta
  traerlos de una base de películas (ej. TMDB).
- **Descargar, Chromecast, subtítulos, calidad 4K/Dolby**: más adelante.
