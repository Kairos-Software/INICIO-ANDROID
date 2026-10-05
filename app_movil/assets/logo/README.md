# assets/logo/

Imágenes de la marca **Kairos TV**: el "portal" de cuatro paneles con el punto
rubí del vivo en el centro (diseño en `diseno_kairos_tv/brand/`). No se editan
a mano: las **dibuja** `python tools/generar_marca.py` con las mismas medidas
que `lib/marca.dart` (dentro de la app la marca se dibuja en código, así se ve
nítida en cualquier tamaño).

| Archivo | Para qué |
|---|---|
| `simbolo.png` | El símbolo solo, sin fondo (1024 px). Para usarlo fuera de la app (ej: el panel web). |
| `logo.png` | El símbolo con "KairosTV" al lado, sin fondo. |
| `icono.png` | Ícono de la app (1024×1024): el símbolo sobre grafito. Lo usan los Android viejos. |
| `icono_frente.png` | Frente del **ícono adaptable** (Android 8+): el símbolo con margen y sin fondo. Cada marca de celular lo recorta con su forma (círculo, cuadrado redondeado...), por eso el margen. |

El script también arma el **banner** de Android TV
(`android/app/src/main/res/drawable-xhdpi/banner.png`) y el símbolo de la
pantalla de arranque (`drawable-*/arranque_simbolo.png`).

Los íconos de `android/app/src/main/res/mipmap-*` **no se editan a mano**:
los genera `dart run flutter_launcher_icons` a partir de `icono.png` e
`icono_frente.png` (configuración en `pubspec.yaml`).
