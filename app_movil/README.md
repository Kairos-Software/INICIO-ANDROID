# app_movil/

**Kairos TV**: la app Android (celulares y televisores) del sistema, hecha con **Flutter** (lenguaje Dart). Muestra los
**canales de TV en vivo** y además hace lo mismo que la web (login, inicio, mi perfil, usuarios, notificaciones)
hablando con la API de Django (`../api/`). No tiene datos ni reglas
propias: todo lo pide y lo valida el servidor.

```
Celular (esta app)  ──WiFi / internet──>  Django: /api/v1/...  ──>  PostgreSQL
```

## Qué contiene

| Carpeta / archivo | Para qué |
|---|---|
| `lib/` | **El código de la app** (lo único que se toca normalmente). Ver su README. |
| `test/` | Tests (`flutter test`). |
| `assets/` | Lo que va dentro de la app: `logo/` (logo e íconos) y `fuentes/` (Sora y Manrope, las del panel). Cada una con su README. |
| `android/` | El proyecto Android que Flutter genera para compilar. Solo se toca para cosas de Android: permisos y nombre en `android/app/src/main/AndroidManifest.xml`, el id de la app en `android/app/build.gradle.kts`, la pantalla de arranque en `android/app/src/main/res/` (`drawable*/launch_background.xml`, `values*/styles.xml`). |
| `tools/generar_marca.py` | Genera logo, símbolo, íconos, pantalla de arranque y banner de Android TV desde `assets/logo/original.png`. |
| `pubspec.yaml` | Nombre, versión y **paquetes** que usa la app (como `requirements.txt`). |
| `pubspec.lock` | Versiones exactas instaladas (lo genera Flutter, va al repo). |
| `analysis_options.yaml` | Reglas de estilo que revisa `flutter analyze` (como `.flake8`). |
| `build/`, `.dart_tool/` | Generadas al compilar. No van al repo. |

## Dos formas de entrar

- **Código de 8 números** (lo que se ve primero): los clientes que miran la
  TV. Ven solo los canales y "Mi cuenta". La app da una "señal" al servidor
  cada 5 minutos; si el servicio vence, muestra "Tu servicio venció" (y al
  renovar sigue sin volver a poner el código). Si ya hay tantos aparatos
  conectados como pantallas pagadas, el nuevo ve "cuenta en uso".
- **Usuario y contraseña** ("Entrar con usuario y contraseña"):
  administradores y revendedores. Ven todo lo de antes (TV, inicio, perfil,
  usuarios, avisos). El superusuario ve los canales sin créditos.

## Android TV

La misma APK se instala en celulares y en televisores Android / Google TV:

- `AndroidManifest.xml`: `leanback` y `touchscreen` como *no obligatorios*,
  la categoría `LEANBACK_LAUNCHER` (aparece en el menú de la TV) y el
  `android:banner` (`res/drawable-xhdpi/banner.png`, 320×180, sale de `tools/generar_marca.py`).
- Con el **control remoto**: el canal con foco se marca (borde celeste); OK
  lo abre. En el reproductor, **arriba / abajo o CH+ / CH−** cambian de canal
  (zapping), OK muestra los datos del canal y "Atrás" vuelve.
- `MainActivity.kt` le pasa a Flutter el **nombre del aparato** (ej:
  "Philips 55PUD7406") y si es una TV (`lib/aparato.dart`). El nombre se ve
  en el panel, en "Dispositivos conectados" del cliente.

Instalar en una TV: copiar la APK con un pendrive, o con la app *Downloader*
desde una dirección web (cuando esté en producción), o por la red:
`adb connect <ip-de-la-tv>` y `flutter install` / `adb install app-release.apk`
(en la TV: Ajustes → Preferencias del dispositivo → Opciones de desarrollador →
Depuración por red).

## Paquetes que usa

| Paquete | Para qué |
|---|---|
| `http` | Hacer los pedidos a la API. |
| `flutter_secure_storage` | Guardar el token cifrado en el celular (Keystore de Android). |
| `flutter_localizations` | Textos de Flutter (calendario, copiar/pegar) en español. |
| `video_player` | El reproductor de video (en Android usa ExoPlayer; reproduce HLS). |
| `wakelock_plus` | Que la pantalla no se apague mientras se mira un canal. |
| `flutter_launcher_icons` (solo desarrollo) | Genera los íconos de Android desde el logo: `dart run flutter_launcher_icons`. |

Agregar uno: `flutter pub add <paquete>` (como `pip install`).

## Cómo probarla

1. Django escuchando en la red (no solo en la PC):
   ```
   python manage.py runserver 0.0.0.0:8000
   ```
   La IP de la PC tiene que estar en `ALLOWED_HOSTS` del `.env.local`. Si
   Windows pregunta por el firewall, permitir el acceso en redes privadas.
2. El celular conectado por USB (con depuración USB activada) y en el mismo WiFi.
3. Desde esta carpeta:
   ```
   flutter run
   ```
   Instala la app y la abre. Con la app abierta, al guardar un cambio en el
   código y apretar `r` en la terminal, se actualiza al instante (hot reload).

La dirección del servidor por defecto está en `lib/config.dart`, y se puede
cambiar desde la app (login → "Servidor").

## Generar la APK para compartir

1. **Una sola vez:** crear la clave de firma y el archivo `android/key.properties`
   (copiando `android/key.properties.ejemplo`). La clave (`.jks`) se guarda
   **fuera del proyecto y con copia de seguridad**: todas las versiones de la
   app se firman con ella, y sin ella no se pueden publicar actualizaciones.
2. Generar la APK, indicando a qué servidor se conecta:
   ```
   flutter build apk --dart-define=API_URL=http://192.168.1.241:8000/api/v1/
   ```
   Queda en `build/app/outputs/flutter-apk/app-release.apk`.
3. Pasarla al celular (WhatsApp, Drive, cable) e instalarla aceptando
   "instalar apps de origen desconocido".

Para producción es lo mismo, cambiando la dirección por la del dominio con
`https` (y quitando `usesCleartextTraffic` del `AndroidManifest.xml`).
Cada versión nueva: subir `version:` en `pubspec.yaml` (ej. `1.0.1+2`).

## Comandos útiles

| Comando | Qué hace |
|---|---|
| `flutter run` | Instala y abre la app en el celular conectado |
| `flutter build apk` | Genera la APK para instalar en cualquier Android (`build/app/outputs/flutter-apk/`) |
| `flutter test` | Corre los tests |
| `flutter analyze` | Revisa el código buscando errores |
| `flutter pub get` | Instala los paquetes de `pubspec.yaml` (después de clonar el repo) |
| `flutter doctor` | Revisa que las herramientas estén bien instaladas |
