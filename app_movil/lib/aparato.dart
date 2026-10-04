/// Datos del aparato donde corre la app (los da MainActivity.kt por el
/// canal "kairos/dispositivo"). Se leen una sola vez, al abrir la app.
library;

import 'package:flutter/services.dart';

class Aparato {
  Aparato._();

  static const _canal = MethodChannel('kairos/dispositivo');

  /// Fabricante y modelo (ej: "Philips 55PUD7406"). Se le informa al servidor
  /// al entrar, y aparece en el panel en "Dispositivos conectados".
  static String nombre = 'App Android';

  /// ¿Es un televisor (Android TV / Google TV)? Se maneja con el control remoto.
  static bool esTv = false;

  static Future<void> cargar() async {
    try {
      final datos = await _canal.invokeMapMethod<String, Object?>('datos');
      nombre = '${datos?['nombre'] ?? nombre}';
      esTv = datos?['esTv'] == true;
    } on MissingPluginException {
      // En los tests (o fuera de Android) no hay canal: quedan los valores por defecto
    } on PlatformException {
      // Idem
    }
  }
}
