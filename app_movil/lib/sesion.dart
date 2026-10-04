/// El estado de la sesión: ¿hay alguien logueado? ¿quién?
///
/// Es el equivalente a `request.user` de Django, pero del lado de la app.
/// Cuando cambia (alguien entra o sale), avisa y la app redibuja lo que
/// corresponde: el login o las pantallas del sistema.
library;

import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import 'api/cliente.dart';
import 'api/modelos.dart';
import 'config.dart';

enum EstadoSesion { cargando, sinConexion, sinSesion, conSesion }

class Sesion extends ChangeNotifier {
  /// Guarda el token cifrado en el celular (en el Keystore de Android), no en texto plano.
  final FlutterSecureStorage _almacen = const FlutterSecureStorage();
  static const _claveToken = 'token';
  static const _claveServidor = 'servidor';

  late final ApiCliente api = ApiCliente(urlBase: urlServidorPorDefecto, alPerderSesion: _sesionPerdida);

  EstadoSesion estado = EstadoSesion.cargando;
  Perfil? perfil;
  String? errorConexion;

  /// Se llama al cerrar la sesión, para volver a la primera pantalla (ver main.dart).
  VoidCallback? alSalir;

  String get urlServidor => api.urlBase;

  /// Al abrir la app: ¿quedó una sesión guardada de la vez anterior?
  Future<void> iniciar() async {
    api.urlBase = await _almacen.read(key: _claveServidor) ?? urlServidorPorDefecto;
    api.token = await _almacen.read(key: _claveToken);
    if (api.token == null) {
      _cambiar(EstadoSesion.sinSesion);
      return;
    }
    await reintentar();
  }

  /// Vuelve a pedir el perfil con el token guardado (al abrir la app, o tras un error de conexión).
  Future<void> reintentar() async {
    _cambiar(EstadoSesion.cargando);
    try {
      perfil = Perfil(await api.get('perfil/') as Map<String, dynamic>);
      _cambiar(EstadoSesion.conSesion);
    } on ApiError catch (error) {
      if (error.sinConexion || error.status >= 500) {
        errorConexion = error.detalle;
        _cambiar(EstadoSesion.sinConexion);
      } else {
        await _olvidarSesion();
      }
    }
  }

  Future<void> ingresar(String usuario, String password) async {
    final datos = await api.post('login/', {
      'username': usuario,
      'password': password,
      'dispositivo': nombreDispositivo,
    }) as Map<String, dynamic>;
    api.token = datos['token'] as String;
    await _almacen.write(key: _claveToken, value: api.token);
    perfil = Perfil(datos['usuario'] as Map<String, dynamic>);
    _cambiar(EstadoSesion.conSesion);
  }

  Future<void> salir() async {
    try {
      await api.post('logout/');
    } on ApiError {
      // Aunque el servidor no responda, en el celular la sesión se cierra igual
    }
    await _olvidarSesion();
  }

  /// Después de editar mis datos o cambiar la contraseña.
  Future<void> recargarPerfil() async {
    perfil = Perfil(await api.get('perfil/') as Map<String, dynamic>);
    notifyListeners();
  }

  void actualizarPerfil(Perfil nuevo) {
    perfil = nuevo;
    notifyListeners();
  }

  Future<void> cambiarServidor(String url) async {
    var limpia = url.trim();
    if (!limpia.endsWith('/')) {
      limpia = '$limpia/';
    }
    api.urlBase = limpia;
    await _almacen.write(key: _claveServidor, value: limpia);
    notifyListeners();
  }

  /// El servidor dijo 401: el token venció o lo cerraron (desde la web o el admin).
  void _sesionPerdida() {
    if (estado == EstadoSesion.conSesion) {
      _olvidarSesion();
    }
  }

  Future<void> _olvidarSesion() async {
    api.token = null;
    perfil = null;
    await _almacen.delete(key: _claveToken);
    _cambiar(EstadoSesion.sinSesion);
    alSalir?.call();
  }

  void _cambiar(EstadoSesion nuevo) {
    estado = nuevo;
    notifyListeners();
  }
}

/// Deja la sesión disponible para todas las pantallas:  `SesionScope.of(context)`.
class SesionScope extends InheritedNotifier<Sesion> {
  const SesionScope({super.key, required Sesion sesion, required super.child}) : super(notifier: sesion);

  /// Para usar en `build`: la pantalla se redibuja cuando la sesión cambia.
  static Sesion of(BuildContext context) =>
      context.dependOnInheritedWidgetOfExactType<SesionScope>()!.notifier!;

  /// Para usar en botones y funciones (no redibuja).
  static Sesion leer(BuildContext context) => context.getInheritedWidgetOfExactType<SesionScope>()!.notifier!;
}
