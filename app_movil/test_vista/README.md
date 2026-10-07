# test_vista/

Una herramienta para **mirar pantallas sin instalar la app**: dibuja escenas a
PNG en `build/vista/` (que no va al repositorio), con las letras de verdad.

```
flutter test test_vista/vista_test.dart
```

No son pruebas (no comprueban nada): `flutter test` solo corre `test/`, así que
esto no se ejecuta con las pruebas normales. Sirve para revisar un diseño (ej:
el modo reposo de la TV, `lib/tv/reposo.dart`) antes de armar la APK.
Las imágenes de internet no se bajan en este modo: las escenas con pósters se
revisan en la TV.
