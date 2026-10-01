# actividad/

Registro de actividad: **quién hizo qué, cuándo y desde dónde**. Sirve para
revisar qué pasó cuando algo sale mal ("¿quién le cambió el rol a Juan?").

## Qué se registra solo

- **Sesión:** ingresos, salidas e intentos de ingreso fallidos (con lo que se
  escribió como usuario; la contraseña nunca).
- **Usuarios:** alta, edición (con cada dato que cambió: antes → después),
  activar/desactivar, eliminar, asignar contraseña, cambio y recuperación de
  la propia contraseña, edición de Mi perfil.
- **Roles y permisos:** alta, edición y baja de roles, cambios de permisos
  individuales (qué permiso se agregó o se quitó).
- **Sistema:** activar/desactivar el modo mantenimiento.

Se guarda también la **IP** y el **nombre del usuario como texto**, para que el
registro se siga leyendo aunque después se borre ese usuario.

## Archivos

| Archivo | Capa | Qué contiene |
|---|---|---|
| `models.py` | Base | `RegistroActividad` (una fila por cada cosa que pasó) y `Accion` (tipos: ingreso, crear, editar, eliminar, seguridad...). |
| `registro.py` | Base | `registrar(...)`: la función que usa todo el sistema. `cambios_de_formulario(form)`: arma el "antes → después" de un formulario. |
| `consultas.py` | Base | Búsqueda con filtros para la pantalla. |
| `signals.py` | Base | Registra ingresos, salidas e intentos fallidos (Django avisa con "señales"). |
| `middleware.py` | Presentación | Deja la IP de cada pedido disponible para `registrar()`. |
| `views.py` / `urls.py` | Presentación | Pantalla `/actividad/`. |
| `templates/actividad/lista.html` | Presentación | La lista con filtros y el detalle de cambios. |
| `admin.py` | Técnica | Vista de solo lectura en `/admin/`. |
| `tests/` | Técnica | Pruebas automáticas. |

## Pantalla

`/actividad/` (menú: Sistema → Actividad). Requiere el permiso
`ver_actividad`, que es **restringido**: solo un superusuario lo puede dar.
Filtros: texto, tipo de acción, módulo, rango de fechas. Desde la ficha de un
usuario, "Ver su actividad" muestra lo que hizo y lo que le hicieron.

## Cómo registrar desde un módulo nuevo

```python
from actividad.models import Accion
from actividad.registro import cambios_de_formulario, registrar

# En el servicio, después de guardar:
registrar(request.user, Accion.CREAR, f'Creó el cliente {cliente}', objeto=cliente)

# Al editar, calcular los cambios ANTES de form.save():
cambios = cambios_de_formulario(form)
form.save()
registrar(request.user, Accion.EDITAR, f'Editó el cliente {cliente}', objeto=cliente, cambios=cambios)
```

`registrar` nunca rompe la operación: si falla, lo anota en el log y sigue.

## Limpieza

Se guarda `ACTIVIDAD_DIAS_CONSERVAR` días (365 por defecto, en el `.env`).
`python manage.py limpiar_registros` borra lo más viejo (conviene programarlo
una vez por día en el servidor).

## Contenido actual

Completo.
