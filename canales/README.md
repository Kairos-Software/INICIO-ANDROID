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
| `consultas.py` | Base | `canales_disponibles()`: activos y con fuentes activas (lo que ve la app). |
| `admin.py` | Técnica | Administrar canales, fuentes y categorías desde `/admin/` (hasta que tengan pantallas en el panel). |
| `management/commands/importar_m3u.py` | Técnica | `python manage.py importar_m3u <archivo>` |
| `datos/canales_prueba.m3u8` | Datos | 3 canales públicos para probar (Canal 26, Telemax, TV Universidad). |
| `tests/` | Técnica | Pruebas del lector, la importación y la API. |

La API para la app está en `api/v1/canales.py` (`GET /api/v1/canales/`).

## Cargar canales

```
python manage.py importar_m3u canales/datos/canales_prueba.m3u8
```

Después se pueden editar, desactivar, ordenar o sumar fuentes desde
`/admin/` → Canales de TV.

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

## Pendiente (próximas etapas)

- Qué canales ve cada cliente según su plan / créditos.
- Pantallas en el panel web (hoy: `/admin/`).
- Verificar automáticamente qué fuentes funcionan.
- Guía de programación (EPG) con el `tvg-id`.
