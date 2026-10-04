# lib/

El código de la app. Flutter arranca por `main.dart`.

| Archivo / carpeta | Para qué | Equivalente en Django |
|---|---|---|
| `main.dart` | Arranque, tema, idioma, y `Raiz`: decide si mostrar el login o el sistema según la sesión. | `urls.py` + `@login_required` |
| `config.dart` | Nombre de la app ("Kairos Software Móvil") y dirección del servidor por defecto. | `.env` |
| `sesion.dart` | Quién está logueado, el token guardado, entrar y salir. | `request.user` + sesiones |
| `tema.dart` | El diseño: tema oscuro con los colores del logo (azul noche, azul, celeste, violeta), degradés, radios y Poppins. A propósito, distinto de la web. | `static/css/sistema.css` |
| `campos.dart` | Los campos del usuario agrupados por sección, como en `usuarios/forms.py`. | `SECCIONES_USUARIO` |
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
