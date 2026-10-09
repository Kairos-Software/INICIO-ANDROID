# canales/

Los **canales de TV en vivo** que ven los clientes en la app, y también las
**películas y series** (`Canal.contenido`), que se cargan igual y la app va a
mostrar cuando tenga esas secciones (la API ya las entrega con `?contenido=`).

```
Categoria  1 ──< Canal  1 ──< Fuente

Importacion  1 ──< EntradaImportada   (cada lista subida y qué pasó con cada canal)
```

Un canal puede tener **varias fuentes** (distintas direcciones de la misma
señal). La app prueba la primera y, si falla o se corta, pasa sola a la
siguiente. Si una fuente se cae, el canal sigue andando.

> Django **solo guarda las direcciones**: el video viaja directo desde el
> servidor de cada canal al celular/TV, sin pasar por nuestro servidor. Por
> eso no consume ancho de banda propio ni choca con otros servicios de
> streaming que corran en el mismo servidor.

## Qué contiene

| Archivo / carpeta | Capa | Para qué |
|---|---|---|
| `models.py` | Base | `Categoria`, `Canal` (con idioma, baja lógica y "quitado" con motivo), `Fuente` (dirección, formato, prioridad, estado) e `Importacion` / `EntradaImportada` (cada lista subida y qué pasó con cada canal). `Visto` y `FavoritoAgregado`: cuánto se miró cada cosa y cuántas veces se agregó a favoritos, por día y sumando todos los aparatos (sin saber quién). |
| `m3u.py` | Base | Lector de listas M3U/M3U8: saca nombre, logo, categoría, número, tvg-id, país, idioma (`tvg-language`), cabeceras y dirección. No toca la base. |
| `clasificar.py` | Base | Conclusiones sobre cada entrada: idioma y país, si es en vivo / película / serie, si es para adultos, el formato que parece y el nombre limpio (`ES: (HD REPUESTO) DAZN F1` → `DAZN F1`). `episodio()`: "Arrow S02 E05" → serie, temporada y capítulo (la misma regla que la app). |
| `paginas.py` | Base | YouTube y páginas de video (Twitch, Dailymotion, Vimeo, Kick...) con **yt-dlp**: `verificar()` (¿hay video?) y `resolver()` (la dirección real en este momento). |
| `verificacion.py` | Base | Prueba si una fuente responde y **qué formato es** mirando los bytes (como VLC): HLS, DASH, video directo (MPEG-TS/MP4/MKV) o RTSP. Si el servidor rechaza al "navegador", reintenta como VLC. Además averigua el **códec** del video (h264, h265, mpeg2...) por la lista HLS o los primeros bytes (`Fuente.codec`), y si es de **10 bits** (`h264_10` / `h265_10`, mirando el perfil: la mayoría de los TV box no leen H.264 de 10 bits y lo muestran con franjas verdes). La app lo compara con lo que sabe mostrar su aparato y no muestra lo que no puede ver. Máximo 2 pedidos a la vez al mismo servidor y un tiempo límite por tanda. |
| `analisis.py` | Base | Qué trae un video mirando sus primeros bytes (MPEG-TS, MKV, MP4 y la lista HLS maestra): si tiene **sonido** y de qué tipo, el **idioma del audio**, la **resolución** (leyendo el SPS de H.264 / H.265), cuántos segundos de video hay en esos bytes y cuánto dura la película. Lo usa la prueba a fondo. |
| `servicios.py` | Base | `crear_importacion()` (analiza la lista, rápido), `procesar_lote()` (prueba las próximas 50: quedan aptas o no, con el motivo), `juzgar()` (qué pasa la prueba), `cargar_lote()` (carga las aptas), `verificar_lote_de_fuentes()` (vuelve a probar las guardadas de a 50), `quitar_canales()` / `mostrar_canales()` e `importar_m3u()` (todo de una vez, para la consola). |
| `consultas.py` | Base | `canales_disponibles(tipos)` (lo que ve la app, según los formatos que sabe reproducir), `resumen()` (los números sueltos son solo de en vivo; `por_contenido` trae en vivo, películas y series por separado), `series()` (los capítulos agrupados por serie y temporada, con cuántos ve la app; `Serie.completa` / `por_que_no_se_ve`: como la app, una serie se muestra solo si entre los capítulos que se ven está el T1:E1 y son al menos 3), `catalogo(filtros)` y `por_que_no_se_ve(canal)`. |
| `youtube.py` | Base | **Películas de canales oficiales de YouTube** (Movie Central, Peppa Pig, Bluey...; los revisados están en `SUGERIDOS`). `videos_del_canal()` lee la lista de videos de un canal con yt-dlp (solo los datos), `verificar_video()` prueba con oEmbed que exista y que el dueño deje insertarlo, y del título saca el nombre (`titulo_limpio`, `nombres_distintos`: si todos empiezan "Masha y el Oso" usa lo que sigue), el género (`genero`: la categoría), si es un capítulo (`capitulo`: "T1 E2" -> "Serie S01 E02") y si está en inglés. Son fuentes tipo `yt_video`: la app las muestra en el reproductor de YouTube (sin sacarlas de ahí) y las apps viejas no las reciben. La página `/canales/youtube/` arma con eso una importación (`servicios.crear_importacion_de_youtube`) que se prueba y carga como una lista. |
| `organizar.py` | Base | **Ordenar el contenido.** Categorías: `crear_categoria`, `renombrar_categoria` (el nombre viejo queda en `Categoria.otros_nombres`), `juntar_categorias` (todo pasa a una; los nombres de las juntadas quedan como otros nombres), `borrar_categoria` (lo suyo queda sin categoría), `ordenar_categorias` (el orden en la app) y `categorias_parecidas` (sugiere repetidas: "Deportes" / "SPORTS HD" / "AR \| Deportes"). `categoria_por_nombre` la usa la importación: si "Argentina" se juntó en "Noticias", las listas nuevas con "Argentina" van a "Noticias". **Subcategorías** (`Categoria.padre`, un solo nivel: "Música" > "Rock"; en la app se ven como "Música · Rock", pegadas a su principal): `crear_categoria(..., padre=)`, `ubicar_categoria`; `borrar_categoria(..., con_contenido=True)` borra también lo de adentro; `eliminar_contenido` (se borran sus direcciones: si se reimporta, vuelve; para que no vuelva, "quitar"); `editar_canal` / `editar_serie` / `renombrar_serie` (la edición rápida). Además `mover_a_categoria` y `cambiar_contenido` (en vivo / película / serie; con nombre de serie, numera los elegidos como capítulos: "Serie S01 E01 ..."). |
| `estadisticas.py` | Base | **Lo más visto.** `registrar()` suma lo que manda la app (`POST /api/v1/canales/visto/`: segundos mirados, vistas de más de 1 minuto y favoritos agregados) a los totales del día, **sin guardar quién lo mandó**. `lo_mas_visto(dias)`: el ranking de los últimos 7, 30 o 90 días, separado en canales en vivo, películas y series (los capítulos se juntan por serie). |
| `views.py`, `urls.py`, `forms.py`, `templates/` | Panel | `/canales/` (resumen separado de en vivo, películas y series), `/canales/importaciones/<id>/` (avance e informe), `/canales/catalogo/` (pestañas En vivo / Películas), `/canales/series/` (series agrupadas y paginadas), `/canales/series/detalle/?nombre=...` (temporadas, capítulos y fuentes) `/canales/canal/<id>/editar/` y `/canales/lo-mas-visto/` (pestañas En vivo / Películas / Series, período 7/30/90 días). `/canales/categorias/` (ordenar categorías), `/canales/organizar/` (**Organizar contenido**: TODO en un lugar. Árbol de categorías con subcategorías y cuántos tiene cada una, crear/renombrar/ubicar/ordenar/borrar la elegida; su contenido como en la app, con edición rápida —nombre, imagen, categoría, tipo, si se muestra y **de dónde salió** cada fuente, con link a su importación— y acciones sobre varios: mover, cambiar el tipo, quitar, volver a mostrar, eliminar; usa `consultas.organizar_contenido` y `consultas.categorias_en_arbol`; `/canales/como-en-la-app/` redirige acá) y, en el catálogo y en Series, acciones sobre lo elegido: mover a otra categoría y cambiar el tipo. Permisos `ver_canales`, `importar_canales` y `ver_estadisticas` (lo más visto; solo lo da un superusuario). |
| `templatetags/canales_extras.py` | Panel | Filtro `iniciales` (lo que muestra la app cuando un canal no tiene logo). |
| `admin.py` | Técnica | Editar canales, fuentes y categorías puntuales desde `/admin/`. |
| `management/commands/importar_m3u.py` | Técnica | `python manage.py importar_m3u <archivo> [--sin-verificar] [--a-fondo] [--solo-espanol] [--descartar-sin-logo] [--con-peliculas] [--con-adultos]` |
| `management/commands/verificar_fuentes.py` | Técnica | `python manage.py verificar_fuentes` (para programarlo con cron en producción). |
| `datos/canales_prueba.m3u8` | Datos | 3 canales públicos para probar (Canal 26, Telemax, TV Universidad). |
| `tests/` | Técnica | Pruebas de las herramientas (probar un link, limpiar nombres), del lector, el clasificador, la verificación, las tandas, las pantallas y la API. |

La API para la app está en `api/v1/canales.py` (`GET /api/v1/canales/?formatos=...`).

## Importar una lista (desde el panel)

Menú **Kairos TV → Contenido → Importar una lista**. Acepta `.m3u`, `.m3u8`
o un `.zip` que la contenga (hasta 20 MB). Es en tres pasos, para que una
lista de miles de canales no sature el servidor y para que **solo entre lo
que está bien** (no la lista entera: se descarta la basura de cada lista):

1. **Subir y analizar** (segundos, no sale a internet). Cada entrada de la
   lista queda guardada con su idioma, país, categoría, formato y si es en
   vivo, película o serie. Según lo que se elija, se descartan desde ya (con
   el motivo): películas y series (por defecto se importan), otro idioma,
   adultos, sin logo. Siempre se descartan los que no tienen nombre y los
   RTMP. Las direcciones repetidas o ya cargadas quedan como "Ya estaba".
2. **Probar de a tandas.** La pantalla de la importación le pide al
   servidor que pruebe las próximas 50 (cada pedido dura menos de 2
   minutos), muestra la barra "35 % completado", cuánto falta y los
   contadores, y repite hasta terminar. Se puede pausar; si se cierra la
   página, después se sigue con "Continuar". **Todavía no se carga nada**:
   lo que pasa queda "Apta"; lo que no, "No responde" o "No pasó la
   prueba", con el motivo y agrupado por causa ("Audio en otro idioma: 600").
   "Volver a probar las que fallaron" reintenta las que no respondieron,
   llegaron lentas o se cortaron (a veces es algo del momento).
3. **Cargar las aptas.** Un botón "Cargar las N aptas" (de a 200, con
   avance). Recién ahí entran a la app.

### La prueba a fondo (recomendada, viene marcada)

Además de ver que responda, baja hasta 1 MB de cada entrada y revisa:

| Prueba | No pasa si... |
|---|---|
| Formato | El video es MPEG-2, VC-1 o H.264 de 10 bits: muchos aparatos lo muestran verde, cortado o no lo muestran. (Esto se revisa siempre, también sin la prueba a fondo.) |
| Sonido | No trae ninguna pista de audio, o solo DTS / TrueHD (casi ningún aparato lo reproduce). |
| Idioma | Con "Solo en español": el audio dice que está en otro idioma. Si trae español entre varios, pasa. Si el video no dice el idioma, se guía por el nombre y la categoría (paso 1). |
| Imagen | Tiene menos de 360 líneas (240p, 288p): en una TV se ve muy mal. 480 y 576 (SD común) pasan. |
| Fluidez | Llega más lento de lo que se reproduce (menos de x0.9): se cortaría a cada rato. Se mide con las marcas de tiempo del video, o con lo que pesa y lo que dura. |
| En vivo | La señal está congelada: se vuelve a pedir la lista después de un pedazo (6 a 10 s) y no tiene nada nuevo. O el video deja de llegar mientras se prueba. |
| Series | Al terminar: si de una serie no pasó el capítulo 1 de la temporada 1, o pasaron menos de 3 capítulos (contando los ya cargados), no pasa ninguno: la app no la mostraría. |

Lo que la prueba no puede averiguar (un MP4 con el índice al final, un
video que no dice su idioma) no se cuenta en contra. La calidad que
encontró ("1080p · H.264 · audio AAC (es) · llega x3.2") queda en el
informe y en la fuente (`Fuente.calidad`). Gasta hasta 1 MB por entrada
(una lista de 1.000 entradas: hasta 1 GB, una sola vez) y en vivo tarda
unos segundos más por canal (espera a que avance).

Ninguna prueba garantiza que un canal no se corte en dos horas: lo que pasa
después lo cuidan la verificación automática (cron cada 6 horas) y los
avisos de los aparatos (ver "Estado de una fuente").

Si un canal ya existe (mismo nombre limpio y país compatible), la dirección se
suma como fuente alternativa. Si el canal está **quitado**, no se vuelve a
agregar. Borrar el informe no borra lo que ya se cargó.

Por consola (todo de una vez, sin barra):

```
python manage.py importar_m3u canales/datos/canales_prueba.m3u8
```

## Catálogo: elegir qué canales se ven

`/canales/catalogo/` tiene pestañas para **En vivo** y **Películas**; cada una
muestra solo ese contenido con el aspecto de la app (agrupado por categoría,
con logo). La pestaña **Series** abre `/canales/series/`, donde los capítulos
se agrupan por nombre y temporada. Se puede buscar una serie y filtrar las que
muestra la app, las que están **a medias** (se ven capítulos, pero falta el
T1:E1 o son menos de 3: la app no las muestra, igual que no muestra una serie
que no se puede empezar) o las que no tienen ninguno visible. El detalle de
una serie despliega sus temporadas y muestra, por capítulo, disponibilidad,
motivo si no se ve, fuentes y acceso a la edición.

Cada canal o película dice idioma, país, cuántas
fuentes andan y, si la app no lo muestra, por qué. "Ver detalle" muestra sus
fuentes (formato, códec, estado, error, de qué lista vino). Filtros: nombre, se ve /
no se ve / quitado, idioma, categoría, lista de origen y "solo sin logo".

**Quitar** = el canal deja de verse en la app (no se borra). Se puede quitar
uno, los elegidos o todos los que coinciden con el filtro, con un motivo.
"Volver a mostrar" lo deshace.

**Editar** (botón en cada canal del catálogo, o el nombre en el informe de
una importación): nombre, logo (con vista previa de cómo queda en la app),
número, categoría (elegir una o escribir una nueva), contenido, idioma, país,
orden y si se muestra. Abajo, sus fuentes: cambiar el orden en que la app las
prueba, apagarlas, borrarlas o agregar una dirección nueva (se prueba al guardar).

## Probar un link y agregarlo a mano

`/canales/probar/` (botón **Probar un link** en Canales): se pega una
dirección y se prueba igual que al importar (formato real, como la app y como
VLC; YouTube y páginas con yt-dlp). Dice si funciona, de qué tipo es y por
qué no anda. Si es YouTube o una página, sugiere el nombre y la imagen. Con
el resultado se completa nombre, logo, categoría... y se crea el canal (si
no anda, se puede agregar igual: aparece en la app cuando una verificación lo
encuentre funcionando). Si la dirección ya estaba cargada, avisa en qué canal.

## Limpiar nombres

Botón **Limpiar nombres** en Canales: pasa los nombres cargados antes al
formato limpio ("ES: (FHD) DAZN 1" -> "DAZN 1"). Si dos canales quedan
iguales (mismo contenido y país compatible), se juntan en uno: sus fuentes
quedan como alternativas y el repetido se da de baja.

## Formatos que reproduce la app

| Formato | Ejemplo | App 1.0.0 | App 1.1.0 |
|---|---|---|---|
| HLS | `.../playlist.m3u8` | Sí | Sí |
| Video directo (MPEG-TS, MP4...) | `http://servidor:8080/usuario/clave/123` (listas IPTV) | No | Sí |
| DASH | `.../manifest.mpd` | No | Sí |
| RTSP | `rtsp://...` | No | Sí |
| YouTube (vivos y videos) | `youtube.com/@canal/live`, `youtu.be/...` | No | Sí |
| Página de video | Twitch, Dailymotion, Vimeo, Kick, OK.ru, Facebook... | No | Sí |
| RTMP | `rtmp://...` | No | No (se descarta) |

**YouTube** lo verifica el servidor con yt-dlp (si el canal no está en vivo
ahora, queda caído con ese motivo y "Volver a verificar" lo reactiva cuando
vuelve). Pero lo **resuelve la app en el aparato**: las direcciones de video
de YouTube quedan atadas a la IP de quien las pidió, y si las pidiera el
servidor al celular le darían error. **Las páginas** (Twitch...) las resuelve
el servidor en el momento de reproducir: `GET /api/v1/canales/fuentes/<id>/resolver/`.

yt-dlp hay que **actualizarlo seguido** (los sitios cambian y lo rompen):
`pip install -U yt-dlp` en el servidor (ver `despliegue/README.md`).

La app le dice al servidor qué formatos sabe (`?formatos=hls,dash,directo,rtsp,youtube,pagina`);
la 1.0.0 no dice nada y recibe solo HLS, así no le llegan canales que no
puede abrir.

**Por qué VLC los reproducía y la app no:** las listas IPTV mandan video
directo sin extensión. Antes el verificador exigía HLS (las marcaba caídas)
y la app le decía al reproductor "es HLS". Ahora el verificador mira lo que
llega, guarda el formato real en la fuente, y la app se lo pasa al reproductor.

## Estado de una fuente

| Campo | Quién lo cambia | Para qué |
|---|---|---|
| `activa` | Una persona (admin) | Apagar una fuente a mano aunque funcione. |
| `estado` | La verificación automática | `funciona`, `caida` o `sin_verificar` (si YouTube no dejó verificar desde el servidor, o importada con `--sin-verificar`). |
| `tipo` | La verificación automática | El formato real (ver la tabla de arriba). |
| `codec` | La verificación automática | Códec de video (`h264`, `h265`, `mpeg2`...; `h264_10` / `h265_10` si es de 10 bits), o vacío si todavía no se sabe. |

La app recibe una fuente solo si está **activa, no caída y es de un formato
que esa versión reproduce**. Un canal sin ninguna fuente así **no aparece en
la app**. "Volver a verificar todas" (de a tandas, con barra de avance)
reactiva las caídas que volvieron y corrige el formato de las viejas.

**Cómo se presenta el reproductor:** hay canales que rechazan al reproductor
de Android ("ExoPlayer") con error 403 y solo entregan el video a algo que
parece un navegador, y paneles IPTV que solo se lo entregan a VLC. Por eso la
app pide el video con el User-Agent que le manda la API
(`verificacion.USER_AGENT_REPRODUCTOR`, o el propio de la fuente), y el
verificador prueba **igual**; si así lo rechazan, prueba como VLC
(`USER_AGENT_VLC`) y, si anda, lo guarda en la fuente para que la app también
lo use. Si una lista M3U trae `#EXTVLCOPT:http-user-agent=` / `http-referrer=`
o `|User-Agent=...&Referer=...`, se guardan en la fuente (`user_agent`,
`referer`) y se usan siempre.

**Se arregla sola:** cuando la app no puede reproducir una fuente, avisa
(`POST /api/v1/canales/fuentes/<id>/falla/`). El servidor la vuelve a probar
por su cuenta (como máximo una vez cada 5 minutos por fuente) y, si también
le falla, la marca caída: desde la próxima actualización de la lista, la app
ya no la recibe.

**Lo que el servidor ve bien pero los aparatos no:** hay señales que al
servidor le responden pero en los celulares y TV no se reproducen (un formato
de video que el aparato no lee, servidores que aceptan una sola conexión,
otros que rechazan a los reproductores). Por eso la app manda también el
motivo (`{"motivo": "formato" | "rechazo" | "tiempo" | "conexion" | "error",
"detalle"}`). Si en un día avisan **2 aparatos distintos** (o el mismo, con
media hora de diferencia), la fuente se **oculta 7 días** aunque al servidor
le ande (`Fuente.oculta_desde`, `falla_en_aparatos`; ver
`servicios.registrar_falla_en_aparato`). En el catálogo el canal aparece como
"Oculto porque no se reproduce en los aparatos (motivo)". Pasados los 7 días,
la app lo vuelve a intentar sola. Si falla porque el aparato no tiene
internet, la app no avisa.

## Formato M3U (resumen)

```
#EXTINF:-1 tvg-id="Canal26.ar" tvg-logo="https://..." tvg-chno="26" group-title="Noticias",Canal 26
https://servidor/canal26/main.m3u8
```

| Atributo | Se guarda en |
|---|---|
| texto después de la coma / `tvg-name` | `Canal.nombre` (limpio: sin prefijo de país ni calidad) |
| `tvg-logo` | `Canal.logo` |
| `group-title` | `Categoria` |
| `tvg-chno` | `Canal.numero` |
| `tvg-id` | `Canal.tvg_id` (para la guía, más adelante) |
| `tvg-country` | `Canal.pais` (si no viene, se estima) |
| `tvg-language` | `Canal.idioma` (si no viene, se estima por país, categoría o prefijo) |
| segunda línea | `Fuente.url` |
| `#EXTVLCOPT:http-user-agent` / `http-referrer`, o `\|User-Agent=` / `Referer=` | `Fuente.user_agent` / `Fuente.referer` |

## Pendiente (próximas etapas)

- Qué canales ve cada cliente según su plan / créditos.
- Verificación periódica automática (cron con `verificar_fuentes`).
- Secciones de películas y series en la app (agrupar capítulos por serie y temporada).
- Guía de programación (EPG) con el `tvg-id`.
