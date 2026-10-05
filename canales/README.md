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
| `models.py` | Base | `Categoria`, `Canal` (con idioma, baja lógica y "quitado" con motivo), `Fuente` (dirección, formato, prioridad, estado) e `Importacion` / `EntradaImportada` (cada lista subida y qué pasó con cada canal). |
| `m3u.py` | Base | Lector de listas M3U/M3U8: saca nombre, logo, categoría, número, tvg-id, país, idioma (`tvg-language`), cabeceras y dirección. No toca la base. |
| `clasificar.py` | Base | Conclusiones sobre cada entrada: idioma y país, si es en vivo / película / serie, si es para adultos, el formato que parece y el nombre limpio (`ES: (HD REPUESTO) DAZN F1` → `DAZN F1`). |
| `paginas.py` | Base | YouTube y páginas de video (Twitch, Dailymotion, Vimeo, Kick...) con **yt-dlp**: `verificar()` (¿hay video?) y `resolver()` (la dirección real en este momento). |
| `verificacion.py` | Base | Prueba si una fuente responde y **qué formato es** mirando los bytes (como VLC): HLS, DASH, video directo (MPEG-TS/MP4/MKV) o RTSP. Si el servidor rechaza al "navegador", reintenta como VLC. Máximo 2 pedidos a la vez al mismo servidor y un tiempo límite por tanda. |
| `servicios.py` | Base | `crear_importacion()` (analiza la lista, rápido), `procesar_lote()` (verifica las próximas 50 y agrega las que andan), `verificar_lote_de_fuentes()` (vuelve a probar las guardadas de a 50), `quitar_canales()` / `mostrar_canales()` e `importar_m3u()` (todo de una vez, para la consola). |
| `consultas.py` | Base | `canales_disponibles(tipos)` (lo que ve la app, según los formatos que sabe reproducir), `resumen()`, `catalogo(filtros)` y `por_que_no_se_ve(canal)`. |
| `views.py`, `urls.py`, `forms.py`, `templates/` | Panel | `/canales/` (resumen, subir lista, verificar todas), `/canales/importaciones/<id>/` (avance e informe), `/canales/catalogo/` (los canales como en la app) y `/canales/canal/<id>/editar/`. Permisos `ver_canales` e `importar_canales`. |
| `templatetags/canales_extras.py` | Panel | Filtro `iniciales` (lo que muestra la app cuando un canal no tiene logo). |
| `admin.py` | Técnica | Editar canales, fuentes y categorías puntuales desde `/admin/`. |
| `management/commands/importar_m3u.py` | Técnica | `python manage.py importar_m3u <archivo> [--sin-verificar] [--solo-espanol] [--descartar-sin-logo] [--con-peliculas] [--con-adultos]` |
| `management/commands/verificar_fuentes.py` | Técnica | `python manage.py verificar_fuentes` (para programarlo con cron en producción). |
| `datos/canales_prueba.m3u8` | Datos | 3 canales públicos para probar (Canal 26, Telemax, TV Universidad). |
| `tests/` | Técnica | Pruebas de las herramientas (probar un link, limpiar nombres), del lector, el clasificador, la verificación, las tandas, las pantallas y la API. |

La API para la app está en `api/v1/canales.py` (`GET /api/v1/canales/?formatos=...`).

## Importar una lista (desde el panel)

Menú **Kairos TV → Canales → Importar una lista**. Acepta `.m3u`, `.m3u8` o
un `.zip` que la contenga (hasta 20 MB). Es en dos pasos, para que una lista
de miles de canales no sature el servidor:

1. **Subir y analizar** (segundos, no sale a internet). Cada canal de la
   lista queda guardado con su idioma, país, categoría, formato y si es en
   vivo o película. Según lo que se elija, se descartan desde ya (con el
   motivo): películas y series (por defecto se importan), otro idioma,
   adultos, sin logo. Siempre se
   descartan los que no tienen nombre y los RTMP. Las direcciones repetidas
   o ya cargadas quedan como "Ya estaba".
2. **Verificar de a tandas.** La pantalla de la importación le pide al
   servidor que verifique las próximas 50 (cada pedido dura menos de 1
   minuto), muestra la barra "35 % completado", cuánto falta y los
   contadores, y repite hasta terminar. Se puede pausar; si se cierra la
   página, después se sigue con "Continuar". Las que funcionan se agregan al
   momento; las que no, quedan en el informe con el motivo (y se pueden
   reintentar).

Si un canal ya existe (mismo nombre limpio y país compatible), la dirección se
suma como fuente alternativa. Si el canal está **quitado**, no se vuelve a
agregar. Borrar el informe no borra los canales.

Por consola (todo de una vez, sin barra):

```
python manage.py importar_m3u canales/datos/canales_prueba.m3u8
```

## Catálogo: elegir qué canales se ven

`/canales/catalogo/` muestra todos los canales con el aspecto de la app
(agrupados por categoría, con logo). Cada uno dice idioma, país, cuántas
fuentes andan y, si la app no lo muestra, por qué. "Ver detalle" muestra sus
fuentes (formato, estado, error, de qué lista vino). Filtros: nombre, se ve /
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
"detalle"}`). Si en un día avisan **3 aparatos distintos** (o el mismo, con
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
