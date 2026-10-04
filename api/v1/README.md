# api/v1/

**Versión 1** de la API. Si algún día hay que cambiarla de una forma que
rompería las apps ya instaladas, se crea `v2/` al lado y las dos conviven.

## Qué contiene

| Archivo | Para qué |
|---|---|
| `urls.py` | Las rutas de la v1 (y `GET /api/v1/`, que las lista). |
| `serializers.py` | Cómo se convierte cada objeto a JSON (lo que la app **recibe**). |
| `auth.py` | Iniciar y cerrar sesión. |
| `perfil.py` | Mi perfil y cambiar mi contraseña. |
| `usuarios.py` | Gestión de usuarios. |
| `notificaciones.py` | Mis notificaciones. |
| `canales.py` | Los canales de TV para la app. |

Lo que la app **envía** se valida con los formularios de la web
(`usuarios/forms.py`): los campos se llaman igual.

## Endpoints

Todos piden `Authorization: Bearer <token>`, salvo `login` y el índice.

| Método | Ruta | Permiso | Qué hace |
|---|---|---|---|
| GET | `/api/v1/` | — | Lista de endpoints |
| POST | `/api/v1/login/` | — | `{username, password, dispositivo}` → `{token, vence, usuario}` |
| POST | `/api/v1/logout/` | sesión | Cierra la sesión de este dispositivo |
| GET | `/api/v1/perfil/` | sesión | Mis datos y mis permisos (`permisos`: códigos; `permisos_por_modulo`: legibles) |
| PATCH | `/api/v1/perfil/` | sesión | Modificar mis datos (solo lo que cambia) |
| GET | `/api/v1/perfil/opciones/` | sesión | Opciones para el formulario del perfil (géneros) |
| POST | `/api/v1/perfil/cambiar-password/` | sesión | `{old_password, new_password1, new_password2}` |
| GET | `/api/v1/usuarios/` | `ver_usuarios` | Lista. Filtros: `q`, `rol` (id o `sin_rol`), `estado` (`activos`/`inactivos`), `pagina` |
| POST | `/api/v1/usuarios/` | `crear_usuarios` | Crear (`password1`, `password2` y los datos) |
| GET | `/api/v1/usuarios/opciones/` | crear o editar | Roles (y si se pueden asignar), tipos de documento, géneros |
| GET | `/api/v1/usuarios/<id>/` | `ver_usuarios` | Detalle, con `acciones` que puede hacer quien pregunta |
| PATCH | `/api/v1/usuarios/<id>/` | `editar_usuarios` | Modificar (solo lo que cambia) |
| DELETE | `/api/v1/usuarios/<id>/` | `eliminar_usuarios` | Eliminar |
| POST | `/api/v1/usuarios/<id>/estado/` | `editar_usuarios` | `{activo: true/false}` |
| POST | `/api/v1/usuarios/<id>/restablecer-password/` | `restablecer_password_usuarios` | `{password1, password2, obligar_cambio}` |
| GET | `/api/v1/canales/` | sesión | Canales de TV activos, agrupados por categoría, con sus fuentes en orden de prioridad |
| GET | `/api/v1/notificaciones/` | sesión | Mis notificaciones (`?no_leidas=1`); trae `no_leidas` |
| POST | `/api/v1/notificaciones/<id>/leida/` | sesión | Marcar una como leída |
| POST | `/api/v1/notificaciones/marcar-todas/` | sesión | Marcar todas como leídas |

Para subir una foto (perfil o usuario), mandar el pedido como
`multipart/form-data` con el campo `foto`. Para quitarla: `quitar_foto: true`.
