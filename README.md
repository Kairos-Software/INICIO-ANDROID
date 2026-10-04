# PROYECTO BASE

Proyecto Django que sirve de punto de partida para los sistemas de Kairos Software.
Trae resuelto lo que todo sistema necesita (login, usuarios, roles y permisos,
perfil, recuperación de contraseña) para que cada proyecto nuevo arranque
directamente con lo propio de su negocio.

## Tecnologías

- Python 3.13 / Django 6.1
- PostgreSQL
- Templates de Django (HTML renderizado en el servidor)

## Estructura

Cada carpeta tiene su propio `README.md` que explica qué contiene y para qué sirve.

| Carpeta / archivo | Propósito |
|---|---|
| `proyecto/` | Configuración general de Django (settings, urls, arranque) |
| `core/` | Inicio, modo mantenimiento, páginas de error y datos de la marca |
| `usuarios/` | Usuarios, roles, permisos, login, perfil y recuperación de contraseña |
| `actividad/` | Registro de actividad: quién hizo qué y cuándo |
| `notificaciones/` | Avisos internos (la campanita) |
| `canales/` | Canales de TV en vivo: categorías, canales, fuentes e importación de listas M3U |
| `herramientas/` | Código reutilizable en todo el sistema (modelo base, formularios...) |
| `api/` | La API (JSON) para las apps de celular/TV y otros sistemas: login por token, perfil, usuarios, notificaciones |
| `app_movil/` | La app Android (Flutter) que usa la API. Tiene su propio README |
| `templates/` | HTML generales, compartidos por todas las apps |
| `static/` | CSS, JavaScript e imágenes generales |
| `media/` | Archivos que suben los usuarios (no va al repo) |
| `scripts/` | Scripts sueltos de mantenimiento o utilidades de desarrollo |
| `.env*` | Configuración por entorno (ver abajo) |
| `requirements.txt` | Librerías de Python que usa el proyecto |
| `.flake8` | Reglas de estilo que revisa el editor (largo de línea: 120) |
| `manage.py` | Comando principal de Django |

## Entornos (.env)

| Archivo | Propósito | ¿Va al repo? |
|---|---|---|
| `.env` | Solo indica qué entorno usar: `DJANGO_ENV=local` / `production` / `test` | No |
| `.env.local` | Datos para trabajar en la PC | No |
| `.env.test` | Datos para pruebas (base de datos aparte) | No |
| `.env.production` | Datos del servidor | No |
| `.env.example` | Plantilla sin datos secretos | **Sí** |

## Puesta en marcha (PC nueva)

```bash
python -m venv entorno
entorno\Scripts\activate
pip install -r requirements.txt
# copiar .env.example como .env.local y completarlo
# crear la base de datos en PostgreSQL con el nombre de DB_NAME
python manage.py migrate
python manage.py crear_roles_iniciales
python manage.py createsuperuser
python manage.py runserver
```

## Envío de mails

Por defecto (`EMAIL_BACKEND=console`) los mails **no se envían**: se
muestran en la terminal donde corre `runserver`. Sirve para probar (ahí
aparece, por ejemplo, el código de recuperación de contraseña).

Para enviarlos de verdad con Gmail, en el `.env` del entorno:

```
EMAIL_BACKEND=smtp
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=cuenta@gmail.com
EMAIL_HOST_PASSWORD=la-contraseña-de-aplicacion
DEFAULT_FROM_EMAIL=Nombre del sistema <cuenta@gmail.com>
```

`EMAIL_HOST_PASSWORD` **no** es la contraseña de la cuenta: es una
"contraseña de aplicación" que se genera en la cuenta de Google
(Seguridad → Verificación en dos pasos → Contraseñas de aplicaciones).

## Tareas programadas (en el servidor)

`python manage.py limpiar_registros` borra la actividad más vieja que
`ACTIVIDAD_DIAS_CONSERVAR` y las notificaciones leídas más viejas que
`NOTIFICACIONES_DIAS_CONSERVAR`, y las sesiones de la app vencidas
(`API_TOKEN_DIAS`). Conviene correrlo una vez por día (cron o
systemd timer).

## Cómo se organiza una app

La lógica del sistema se separa de la forma de mostrarla. Por eso la API
(`api/`, con Django REST Framework) usa los mismos modelos, permisos,
formularios y servicios que las pantallas HTML, sin repetir reglas.

| Archivo | Capa | Qué contiene |
|---|---|---|
| `models.py` | Base | Las tablas y sus datos |
| `permisos.py` | Base | Quién puede hacer qué |
| `servicios.py` | Base | Lo que el sistema **hace** (crear, modificar, dar de baja, enviar un mail...). Toda regla de negocio va acá. |
| `consultas.py` | Base | Lo que el sistema **busca o lista** (filtros, búsquedas, listados) |
| `forms.py` | Presentación | Formularios HTML y sus validaciones de pantalla |
| `views.py` o `views/` | Presentación | Recibe el pedido, llama a servicios/consultas y muestra un template. Sin lógica de negocio. Si crece, se vuelve una carpeta con un archivo por tema. |
| `urls.py` | Presentación | Las rutas de la app |
| `templates/<app>/` | Presentación | Los HTML de la app |

Regla de oro: si algo tendría que funcionar igual desde una pantalla HTML y
desde una API, va en la capa **Base**, nunca en `views.py` ni en un template.

## Reglas del proyecto

- Toda carpeta o app nueva lleva su `README.md` explicando qué contiene y su propósito.
- Nada sensible (claves, contraseñas) se escribe en el código: va en los `.env`.
- La lógica de negocio va en la capa Base (ver "Cómo se organiza una app").
