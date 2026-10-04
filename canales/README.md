# canales/

Los **canales de TV en vivo** que ven los clientes en la app.

```
Categoria  1 ──< Canal  1 ──< Fuente
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
| `models.py` | Base | `Categoria`, `Canal` (con baja lógica, de `ModeloBase`) y `Fuente` (dirección, tipo HLS/YouTube, prioridad). |
| `m3u.py` | Base | Lector de listas M3U/M3U8: saca nombre, logo, categoría, número, tvg-id, país y dirección. No toca la base. |
| `servicios.py` | Base | `importar_m3u()`: agrega los canales de una lista; si un canal ya existe (mismo tvg-id o nombre), suma la dirección como fuente alternativa. Nunca pisa ni duplica. |
| `verificacion.py` | Base | Prueba si una fuente responde (como el KairosTV.html, pero desde el servidor): pide la lista HLS y, si es maestra, también la primera calidad. YouTube queda "sin verificar". Varias a la vez, 9 s máximo cada una. |
| `consultas.py` | Base | `canales_disponibles()`: activos y con fuentes usables (lo que ve la app). `resumen()` y `fuentes_caidas()` para el panel. |
| `servicios.py` (cont.) | Base | `verificar_fuentes_guardadas()`: vuelve a probar todas y actualiza su estado. |
| `views.py`, `urls.py`, `forms.py`, `templates/` | Panel | `/canales/`: resumen, importar una lista subiendo el archivo y "Volver a verificar todas". Permisos `ver_canales` e `importar_canales`. |
| `admin.py` | Técnica | Editar canales, fuentes y categorías puntuales desde `/admin/`. |
| `management/commands/importar_m3u.py` | Técnica | `python manage.py importar_m3u <archivo> [--sin-verificar]` |
| `management/commands/verificar_fuentes.py` | Técnica | `python manage.py verificar_fuentes` (para programarlo con cron en producción). |
| `datos/canales_prueba.m3u8` | Datos | 3 canales públicos para probar (Canal 26, Telemax, TV Universidad). |
| `tests/` | Técnica | Pruebas del lector, la importación y la API. |

La API para la app está en `api/v1/canales.py` (`GET /api/v1/canales/`).

## Cargar canales

Desde el panel: menú **Kairos TV → Canales**, elegir el archivo y
"Importar y verificar". O por consola:

```
python manage.py importar_m3u canales/datos/canales_prueba.m3u8
```

Después se pueden editar, desactivar, ordenar o sumar fuentes desde
`/admin/` → Canales de TV.

## Estado de una fuente

| Campo | Quién lo cambia | Para qué |
|---|---|---|
| `activa` | Una persona (admin) | Apagar una fuente a mano aunque funcione. |
| `estado` | La verificación automática | `funciona`, `caida` o `sin_verificar` (YouTube, o importada con `--sin-verificar`). |

La app recibe una fuente solo si está **activa, no caída y es HLS** (el
reproductor de la app todavía no reproduce YouTube). Un canal sin ninguna
fuente así **no aparece en la app**. Las caídas se guardan igual (muchas
vuelven): "Volver a verificar todas" las reactiva solas si responden de nuevo.

**Cómo se presenta el reproductor:** hay canales que rechazan al reproductor
de Android ("ExoPlayer") con error 403 y solo entregan el video a algo que
parece un navegador. Por eso la app pide el video con el User-Agent que le
manda la API (`verificacion.USER_AGENT_REPRODUCTOR`, o el propio de la
fuente), y el verificador prueba **igual**: misma identificación, y pidiendo
también el pedazo de video más reciente, no solo la lista. Si una lista M3U
trae `#EXTVLCOPT:http-user-agent=` / `http-referrer=` o `|User-Agent=...&Referer=...`,
se guardan en la fuente (`user_agent`, `referer`) y se usan siempre.

**Se arregla sola:** cuando la app no puede reproducir una fuente, avisa
(`POST /api/v1/canales/fuentes/<id>/falla/`). El servidor la vuelve a probar
por su cuenta (como máximo una vez cada 5 minutos por fuente) y, si también
le falla, la marca caída: desde la próxima actualización de la lista, la app
ya no la recibe.

## Formato M3U (resumen)

```
#EXTINF:-1 tvg-id="Canal26.ar" tvg-logo="https://..." tvg-chno="26" group-title="Noticias",Canal 26
https://servidor/canal26/main.m3u8
```

| Atributo | Se guarda en |
|---|---|
| texto después de la coma / `tvg-name` | `Canal.nombre` |
| `tvg-logo` | `Canal.logo` |
| `group-title` | `Categoria` |
| `tvg-chno` | `Canal.numero` |
| `tvg-id` | `Canal.tvg_id` (para reconocer el canal en otras listas y para la guía) |
| `tvg-country` | `Canal.pais` |
| segunda línea | `Fuente.url` |
| `#EXTVLCOPT:http-user-agent` / `http-referrer`, o `\|User-Agent=` / `Referer=` | `Fuente.user_agent` / `Fuente.referer` |

## Pendiente (próximas etapas)

- Qué canales ve cada cliente según su plan / créditos.
- Editar canales desde el panel (hoy: `/admin/`).
- Verificación periódica automática (cron con `verificar_fuentes`).
- Guía de programación (EPG) con el `tvg-id`.
