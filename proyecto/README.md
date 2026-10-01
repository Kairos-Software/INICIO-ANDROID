# proyecto/

Configuración general de Django. No contiene lógica del negocio: solo define
cómo arranca y cómo se arma el sistema.

## Archivos

| Archivo | Qué hace |
|---|---|
| `settings.py` | Toda la configuración: apps instaladas, base de datos, mail, archivos estáticos, seguridad. Lee los valores de los archivos `.env`. |
| `urls.py` | Punto de entrada de las URLs. Deriva cada ruta a la app que corresponde. |
| `wsgi.py` | Arranque del sistema en el servidor (gunicorn). |
| `asgi.py` | Arranque alternativo para servidores asíncronos (no se usa por ahora). |
| `__init__.py` | Marca la carpeta como paquete de Python. |

## Reglas

- Al crear una app nueva, se agrega en `INSTALLED_APPS` (settings.py) y sus
  URLs se incluyen en `urls.py`.
- Ningún valor secreto se escribe acá: se agrega al `.env` y se lee con `os.environ`.
