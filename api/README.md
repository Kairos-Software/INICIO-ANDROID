# api/

La **API** del sistema: la misma información y las mismas operaciones que
la web, pero respondiendo **datos (JSON)** en vez de páginas HTML. La usan
las apps (celular, TV) y cualquier otro sistema que se quiera conectar.

```
Panel web (plantillas) ─┐
                        ├──> servicios.py / consultas.py / permisos.py / forms.py
API (JSON) ─────────────┘        (la misma lógica, escrita una sola vez)
```

La API **no tiene reglas de negocio propias**: chequea permisos, valida con
los mismos formularios de la web y llama a los mismos servicios. Por eso lo
que se hace desde la app queda igual en el registro de actividad, dispara
las mismas notificaciones y respeta las mismas restricciones.

Está hecha con **Django REST Framework (DRF)**.

## Qué contiene

| Archivo / carpeta | Capa | Para qué |
|---|---|---|
| `models.py` | Base | `TokenAcceso`: cada sesión abierta de la app en un dispositivo. |
| `tokens.py` | Base | Crear, validar, renovar y borrar tokens. |
| `autenticacion.py` | Presentación | Cómo DRF lee el token de cada pedido (`Authorization: Bearer <token>`). |
| `permisos.py` | Presentación | Mantenimiento y "debe cambiar la contraseña" para toda la API, y `exigir_permiso()`. |
| `errores.py` | Presentación | Formato único de los errores y validación con formularios de Django. |
| `formularios.py` | Presentación | Adapta lo que manda la app (JSON o multipart) para los formularios de la web. |
| `paginacion.py` | Presentación | Listados por páginas (`?pagina=2`). |
| `admin.py` | Técnica | Ver y cerrar sesiones de la app desde `/admin/`. |
| `urls.py` | Presentación | `/api/` → cada versión. Lo inexistente responde 404 en JSON. |
| `v1/` | Presentación | La versión 1 de la API: endpoints y serializers (ver su README). |
| `tests/` | Técnica | Pruebas de toda la API. |

## Cómo se usa (resumen)

1. La app inicia sesión: `POST /api/v1/login/` con usuario y contraseña.
   Recibe un **token**.
2. En cada pedido siguiente manda el encabezado
   `Authorization: Bearer <token>`.
3. Al cerrar sesión: `POST /api/v1/logout/`. El token deja de servir.

La lista completa de endpoints está en `v1/README.md` y en `GET /api/v1/`.

## Tokens

- Se guarda solo la **huella** (SHA-256) del token, nunca el token.
- Duran `API_TOKEN_DIAS` (en el `.env`, 30 por defecto) **sin usarse**:
  cada uso los renueva.
- Dejan de servir al cerrar sesión, al cambiar la contraseña (salvo el del
  dispositivo donde la cambió uno mismo), al desactivar o eliminar al usuario,
  y con la herramienta "Cerrar todas las sesiones".
- `python manage.py limpiar_registros` borra los vencidos.

## Errores

Siempre con la misma forma, para que la app los maneje igual:

```json
{"codigo": "sin_permiso", "detalle": "No tenés permiso para hacer esto."}
{"codigo": "datos_invalidos", "detalle": "Revisá los datos enviados.",
 "campos": {"email": ["Ya existe un usuario con ese email."]}}
```

| HTTP | `codigo` | Cuándo |
|---|---|---|
| 400 | `datos_invalidos` | Algún dato está mal (ver `campos`) |
| 400 | `credenciales_invalidas`, `login_bloqueado` | Login |
| 400 | `operacion_no_permitida` | Una regla del negocio lo impide |
| 401 | `no_autenticado`, `token_invalido` | Falta el token o venció: volver al login |
| 403 | `sin_permiso` | No tiene el permiso |
| 403 | `debe_cambiar_password` | Solo puede ver su perfil, cambiar la contraseña o salir |
| 404 | `no_encontrado` | No existe |
| 503 | `mantenimiento` | Sistema en mantenimiento (trae `detalle` y `vuelve`) |

## Probarla desde el navegador

Con `DEBUG=True` y la sesión iniciada en el sistema, entrar a
`http://127.0.0.1:8000/api/v1/`: DRF muestra una página para navegar y
probar cada endpoint (en producción solo responde JSON).

## Para sumar un módulo a la API

1. Si hace falta, un serializer en `v1/serializers.py` (qué datos se devuelven).
2. Un archivo de vistas en `v1/` que chequee permisos con `exigir_permiso()`,
   valide con el formulario del módulo y llame a sus servicios.
3. Sus rutas en `v1/urls.py` y sus tests en `tests/`.
