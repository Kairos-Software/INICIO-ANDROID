# assets/logo/

Imágenes de la marca **Kairos Software Móvil**.

| Archivo | Para qué |
|---|---|
| `logo.png` | Logo completo (símbolo + "Kairos Software Móvil"), sin fondo. Para pantallas como el login. |
| `simbolo.png` | Solo el símbolo, sin fondo. Para lugares chicos dentro de la app. |
| `icono.png` | Ícono de la app (1024×1024): el símbolo sobre fondo blanco. Lo usan los Android viejos. |
| `icono_frente.png` | Frente del **ícono adaptable** (Android 8+): el símbolo con margen y sin fondo. Cada marca de celular lo recorta con su forma (círculo, cuadrado redondeado...), por eso el margen. |

Los íconos de `android/app/src/main/res/mipmap-*` **no se editan a mano**:
los genera `dart run flutter_launcher_icons` a partir de `icono.png` e
`icono_frente.png` (configuración en `pubspec.yaml`).
