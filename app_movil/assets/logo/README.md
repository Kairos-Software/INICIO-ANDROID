# assets/logo/

Imágenes de la marca **Kairos TV**. Todas salen de `original.png` con
`python tools/generar_marca.py` (no se editan a mano: si cambia el logo, se
reemplaza `original.png` y se vuelve a correr).

| Archivo | Para qué |
|---|---|
| `original.png` | El logo tal cual lo diseñaron (televisor + "KairosTV"), sin fondo. La fuente de todo lo demás. |
| `logo.png` | Logo completo, recortado. Para el login y las pantallas de bienvenida. |
| `simbolo.png` | Solo el televisor, sin fondo. Para lugares chicos dentro de la app. |
| `icono.png` | Ícono de la app (1024×1024): el televisor sobre azul noche. Lo usan los Android viejos. |
| `icono_frente.png` | Frente del **ícono adaptable** (Android 8+): el símbolo con margen y sin fondo. Cada marca de celular lo recorta con su forma (círculo, cuadrado redondeado...), por eso el margen. |

Los íconos de `android/app/src/main/res/mipmap-*` **no se editan a mano**:
los genera `dart run flutter_launcher_icons` a partir de `icono.png` e
`icono_frente.png` (configuración en `pubspec.yaml`).
