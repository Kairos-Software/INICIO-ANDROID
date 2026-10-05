# descargas/

La **app Android (APK) para descargar** desde el panel.

| Ruta | Quién | Para qué |
|---|---|---|
| `/descargar/` | **Cualquiera** (sin sesión) | Baja la última versión publicada. Corta a propósito: se escribe con el control remoto en la app *Downloader* de la TV. Sin un código de cliente válido la app no sirve, por eso es pública. |
| `/descargar/<id>/` | Cualquiera (las ocultas, solo quien publica) | Una versión puntual. |
| `/api/v1/app/` | Cualquiera | La última versión publicada (`version`, `notas`, `descarga`). La app la consulta al abrirse y, si la suya es más vieja, ofrece actualizar (ver `api/v1/app.py`). |
| `/app-android/` | Usuarios del panel (revendedores incluidos) | Link, instrucciones de instalación y, con `publicar_app`, subir versiones y ocultarlas. |

## Publicar una versión

1. Subir el número en `app_movil/pubspec.yaml` (`version: 1.0.1+2`).
2. `flutter build apk --release` (en `app_movil/`).
3. En el panel, `/app-android/` → subir `build/app/outputs/flutter-apk/app-release.apk`
   con la **misma versión** de `pubspec.yaml` (ej. `1.0.1`): la app compara ese
   número con el suyo para saber si hay una nueva. Lo que se escriba en
   "qué cambió" aparece en el cartel de la app.

Se valida que sea `.apk`, que sea de verdad una APK (un ZIP: empieza con
`PK`), que pese menos de 200 MB y que la versión no esté repetida. Los
archivos quedan en `media/apk/` (no van al repo).

## Qué contiene

| Archivo | Para qué |
|---|---|
| `models.py` | `VersionApp`: versión, archivo, notas, publicada, quién y cuándo. |
| `views.py`, `urls.py`, `forms.py`, `templates/` | La descarga pública y la página del panel. |
| `admin.py` | Vista técnica en `/admin/`. |
| `tests/` | Subir, validar, descargar, ocultar y permisos. |

## En producción

nginx tiene que aceptar archivos grandes en esa ruta
(`client_max_body_size 200m;`) y conviene que sirva `/media/` directamente.
