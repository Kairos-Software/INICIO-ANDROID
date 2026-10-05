# lib/pantallas/

Las herramientas del panel que se abren desde "Mi Espacio" del celular (el
equivalente a una vista + su template en Django). El login, las pantallas de
los clientes y la TV están en `acceso.dart`, `movil/` y `tv/`.

| Archivo | Pantalla | Endpoints que usa |
|---|---|---|
| `perfil.dart` | Mi perfil, editar mis datos, cambiar mi contraseña (también la obligatoria) | `perfil/`, `perfil/opciones/`, `perfil/cambiar-password/`, `logout/` |
| `usuarios_lista.dart` | Lista de usuarios con búsqueda y filtro | `usuarios/` |
| `usuario_detalle.dart` | Detalle, activar/desactivar, contraseña nueva, eliminar | `usuarios/<id>/`, `.../estado/`, `.../restablecer-password/` |
| `usuario_formulario.dart` | Alta y edición de un usuario | `usuarios/opciones/`, `usuarios/`, `usuarios/<id>/` |
| `notificaciones.dart` | Mis notificaciones | `notificaciones/`, `.../leida/`, `marcar-todas/` |

Lo que cada uno ve depende de sus permisos (`perfil.puede('ver_usuarios')`,
`usuario.accion('eliminar')`), pero esto es solo para no mostrar botones
inútiles: **quien decide de verdad es el servidor**. Aunque alguien
modificara la app, la API rechaza lo que no tiene permitido.
