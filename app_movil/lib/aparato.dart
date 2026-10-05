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

  /// La versión instalada (la de pubspec.yaml, ej: "1.1.0"). Vacía = no se sabe.
  static String version = '';

  /// Dónde se deja la APK nueva que se baja para actualizar (lib/actualizacion.dart).
  static String carpetaTemporal = '';

  /// Abre el instalador de Android con la APK de [ruta] (la persona confirma).
  static Future<void> instalar(String ruta) => _canal.invokeMethod('instalar', {'ruta': ruta});

  static Future<void> cargar() async {
    try {
      final datos = await _canal.invokeMapMethod<String, Object?>('datos');
      nombre = '${datos?['nombre'] ?? nombre}';
      esTv = datos?['esTv'] == true;
      version = '${datos?['version'] ?? ''}';
      carpetaTemporal = '${datos?['carpetaTemporal'] ?? ''}';
    } on MissingPluginException {
      // En los tests (o fuera de Android) no hay canal: quedan los valores por defecto
    } on PlatformException {
      // Idem
    }
  }
}
