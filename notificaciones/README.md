# notificaciones/

Avisos internos para los usuarios: la **campanita** de la barra superior.

## Qué hay

- **Campanita** en todas las pantallas: contador de no leídas y las últimas 5.
- **Pantalla** `/notificaciones/`: todas, o solo las no leídas; "marcar todas
  como leídas".
- Al tocar una notificación se marca como leída y lleva a donde apunta.
- Cada usuario ve solo las suyas (no requiere permisos).

## Avisos que ya manda el sistema

| Cuándo | A quién |
|---|---|
| Se crea su usuario | Al nuevo usuario ("Te damos la bienvenida") |
| Le cambian el rol | A esa persona |
| Le cambian los permisos individuales | A esa persona |
| Cambian los permisos de su rol | A todos los que tienen ese rol (menos a quien lo editó) |

## Archivos

| Archivo | Capa | Qué contiene |
|---|---|---|
| `models.py` | Base | `Notificacion` (destinatario, título, mensaje, link, nivel, leída) y `Nivel` (info, éxito, aviso, error). |
| `servicios.py` | Base | `notificar(...)` y `notificar_a_quienes_puedan(...)`: lo que usa todo el sistema. Marcar como leídas. |
| `context_processors.py` | Presentación | Deja el contador y las últimas notificaciones en todos los templates (para la campanita). |
| `views.py` / `urls.py` | Presentación | Lista, abrir una notificación, marcar todas como leídas. |
| `templates/notificaciones/` | Presentación | `lista.html` y `_item.html` (una notificación; la usan la lista y la campanita). |
| `admin.py` | Técnica | Vista en `/admin/`. |
| `tests/` | Técnica | Pruebas automáticas. |

La campanita en sí está en `templates/parciales/_campanita.html`.

## Cómo avisar desde un módulo nuevo

```python
from notificaciones.models import Nivel
from notificaciones.servicios import notificar, notificar_a_quienes_puedan

# A una persona (o una lista de personas)
notificar(vendedor, 'Te asignaron un pedido', 'Pedido #123 de Juan Pérez', url='/pedidos/123/')

# A todos los que tengan un permiso
notificar_a_quienes_puedan('ver_pedidos', 'Entró un pedido nuevo', url='/pedidos/123/',
                           nivel=Nivel.AVISO, excepto=request.user)
```

- `url` solo acepta rutas internas (un link a otro sitio se descarta).
- Nunca rompe la operación principal: si falla, lo anota en el log y sigue.
- Las notificaciones se ven al cargar una página (no aparecen "en vivo" sin
  recargar).

## Limpieza

Las **leídas** se borran después de `NOTIFICACIONES_DIAS_CONSERVAR` días (90
por defecto) con `python manage.py limpiar_registros`. Las no leídas nunca se
borran.

## Contenido actual

Completo.
