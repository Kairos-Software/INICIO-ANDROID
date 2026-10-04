# lib/pantallas/

Cada pantalla de la app (el equivalente a una vista + su template en Django).

| Archivo | Pantalla | Endpoints que usa |
|---|---|---|
| `login.dart` | Iniciar sesión: con **código** (clientes, lo primero que se ve) o con usuario y contraseña (panel); y elegir el servidor | `login/`, `cliente/login/` |
| `cliente.dart` | Del cliente: "Mi cuenta" (vence, pantallas, cerrar sesión) y "Tu servicio venció" | `cliente/` |
| `canales.dart` | **TV en vivo**: los canales por categoría, con su logo. Se actualiza sola cada 15 min. Con el control remoto, el canal con foco se marca | `canales/` |
| `reproductor.dart` | Reproduce un canal a pantalla completa (horizontal). Si una fuente falla o se traba, pasa sola a la siguiente. En la TV: arriba/abajo o CH+/CH− cambian de canal (zapping) | — (el video va directo del servidor del canal al celular) |
| `principal.dart` | La barra flotante (TV, Inicio, Usuarios, Avisos, Perfil) y la pantalla de inicio (con "Cerrar sesión" arriba a la derecha) | `notificaciones/?no_leidas=1` (la campanita) |
| `perfil.dart` | Mi perfil, editar mis datos, cambiar mi contraseña (también la obligatoria) | `perfil/`, `perfil/opciones/`, `perfil/cambiar-password/`, `logout/` |
| `usuarios_lista.dart` | Lista de usuarios con búsqueda y filtro | `usuarios/` |
| `usuario_detalle.dart` | Detalle, activar/desactivar, contraseña nueva, eliminar | `usuarios/<id>/`, `.../estado/`, `.../restablecer-password/` |
| `usuario_formulario.dart` | Alta y edición de un usuario | `usuarios/opciones/`, `usuarios/`, `usuarios/<id>/` |
| `notificaciones.dart` | Mis notificaciones | `notificaciones/`, `.../leida/`, `marcar-todas/` |

Lo que cada uno ve depende de sus permisos (`perfil.puede('ver_usuarios')`,
`usuario.accion('eliminar')`), pero esto es solo para no mostrar botones
inútiles: **quien decide de verdad es el servidor**. Aunque alguien
modificara la app, la API rechaza lo que no tiene permitido.
