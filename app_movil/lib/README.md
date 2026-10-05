# lib/

El código de la app. Flutter arranca por `main.dart`.

| Archivo / carpeta | Para qué | Equivalente en Django |
|---|---|---|
| `main.dart` | Arranque, tema, idioma, y `Raiz`: decide si mostrar el login o el sistema según la sesión. | `urls.py` + `@login_required` |
| `config.dart` | Nombre de la app ("Kairos TV") y dirección del servidor por defecto. | `.env` |
| `sesion.dart` | Quién está logueado (un **cliente** con código o un **usuario** del panel), el token guardado, entrar y salir, y la "señal" del cliente cada 5 min. | `request.user` + sesiones |
| `aparato.dart` | Nombre del aparato y si es una TV (lo da `MainActivity.kt`). | — |
| `tema.dart` | El diseño: el mismo del panel en versión oscura (azul noche del menú, celeste/azul en lo activo, naranja en el foco del control remoto), letras Sora y Manrope, radios y `FondoMarca`. Si cambian los colores del panel, se cambian acá. | `static/css/sistema.css` |
| `campos.dart` | Los campos del usuario agrupados por sección, como en `usuarios/forms.py`. | `SECCIONES_USUARIO` |
| `senales.dart` | De una fuente a la dirección que abre el reproductor: YouTube se resuelve en el aparato (con Cronet), las páginas de video (Twitch...) se le piden al servidor, y le dice al reproductor el formato (HLS, DASH, video directo). | `canales/paginas.py` |
| `utiles.dart` | Funciones chicas: fechas legibles, mensajes, "¿seguro?". | `herramientas/` |
| `api/` | Cómo se habla con la API y las clases de los datos. Ver su README. | — |
| `pantallas/` | Cada pantalla de la app. Ver su README. | `views.py` + templates |
| `widgets/` | Piezas de pantalla reutilizables. Ver su README. | `templates/parciales/` |

## Cómo fluye una pantalla

1. La pantalla pide datos con `SesionScope.leer(context).api.get('usuarios/')`.
2. `ApiCliente` agrega el token, hace el pedido y convierte el JSON.
3. Si sale bien, la pantalla los guarda en su estado y se redibuja (`setState`).
4. Si sale mal, llega un `ApiError` con `detalle` (para mostrar) y `campos`
   (errores de cada campo, para los formularios).
5. Si la sesión venció (401), `Sesion` vuelve sola al login.
6. Si un cliente se quedó sin servicio (403 `servicio_vencido` / `suspendido`),
   `Sesion` muestra "Tu servicio venció" (`pantallas/cliente.dart`).
