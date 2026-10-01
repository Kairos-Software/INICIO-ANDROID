# api/

**Por ahora está vacía, a propósito.** Es el lugar reservado para la API del
sistema, para cuando un proyecto la necesite (una app de celular o de TV,
otro sistema que se conecte, una pantalla hecha en React/Vue).

Mientras esté vacía no hace nada: no está registrada en Django ni tiene
rutas.

## Qué es la API

Hoy el sistema responde con páginas HTML (las plantillas). La API responde
con **datos** (JSON) para que otro programa los muestre a su manera: la APK,
una app de iPhone, un televisor, etc.

```
Panel web (plantillas) ─┐
                        ├──> servicios.py / consultas.py / permisos.py
API (JSON) ─────────────┘        (la misma lógica, escrita una sola vez)
```

La API **no tiene lógica propia**: recibe el pedido, chequea permisos y llama
a los mismos `servicios.py` y `consultas.py` que usan las pantallas. Así una
regla de negocio nunca queda escrita dos veces.

## Qué iría acá cuando se use

| Parte | Para qué |
|---|---|
| Django REST Framework | La librería que se usa para armar la API |
| Login por token | Las apps no usan la sesión del navegador: se identifican con un token |
| Permisos | Los mismos del panel (`usuarios/permisos.py`), para que la app no pueda hacer lo que la web no deja |
| Límite de intentos y errores uniformes | Seguridad y que las apps siempre reciban los errores en el mismo formato |
| Versiones en la dirección (`/api/v1/`) | Poder cambiar la API sin romper las apps ya instaladas |
| Endpoints | Una carpeta o archivo por tema (perfil, y luego lo de cada negocio) |

Lo propio de cada negocio (por ejemplo activar un dispositivo con un código,
consumir créditos, el catálogo) se agrega en cada proyecto, no en la base.

## Recordatorio de seguridad

Una API prendida que nadie usa es una puerta abierta de más: se activa solo
en los proyectos que la necesiten.
