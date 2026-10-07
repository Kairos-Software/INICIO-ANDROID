/// Cómo habla la app con la API de Django.
///
/// Todas las pantallas piden datos a través de [ApiCliente]: arma la
/// dirección, agrega el token, convierte el JSON y transforma cualquier
/// error en un [ApiError] con el mismo formato que define api/errores.py.
library;

import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:isolate';

import 'package:http/http.dart' as http;

/// Un error de la API (o de la conexión), listo para mostrar.
class ApiError implements Exception {
  ApiError({
    required this.status,
    required this.codigo,
    required this.detalle,
    this.campos = const {},
    this.extra = const {},
  });

  /// Lee la respuesta de error de Django: {"codigo", "detalle", "campos"?}.
  factory ApiError.desdeRespuesta(int status, Object? datos) {
    if (datos is! Map<String, dynamic>) {
      return ApiError(
        status: status,
        codigo: 'respuesta_invalida',
        detalle: 'El servidor respondió algo inesperado (código $status).',
      );
    }
    final campos = <String, List<String>>{};
    final crudos = datos['campos'];
    if (crudos is Map) {
      crudos.forEach((campo, mensajes) {
        campos['$campo'] = mensajes is List ? mensajes.map((m) => '$m').toList() : ['$mensajes'];
      });
    }
    return ApiError(
      status: status,
      codigo: '${datos['codigo'] ?? 'error'}',
      detalle: '${datos['detalle'] ?? 'Ocurrió un error.'}',
      campos: campos,
      extra: datos,
    );
  }

  /// 0 = no hubo respuesta (sin conexión).
  final int status;
  final String codigo;
  final String detalle;
  final Map<String, List<String>> campos;
  final Map<String, dynamic> extra;

  bool get sinConexion => status == 0;
  bool get sesionVencida => status == 401;

  /// El servicio del cliente (login con código) venció o lo suspendieron.
  bool get sinServicio => status == 403 && (codigo == 'servicio_vencido' || codigo == 'suspendido');

  /// El error de un campo del formulario (o null si ese campo está bien).
  String? campo(String nombre) => campos[nombre]?.join(' ');

  /// Errores generales (no de un campo puntual).
  String? get general => campo('general');

  @override
  String toString() => detalle;
}

class ApiCliente {
  ApiCliente({required this.urlBase, this.token, this.alPerderSesion, this.alPerderServicio});

  /// Ej: http://192.168.1.241:8000/api/v1/
  String urlBase;

  /// El token de la sesión. Null = sin sesión.
  String? token;

  /// Se llama cuando el servidor responde 401 teniendo token (venció o lo cerraron).
  void Function()? alPerderSesion;

  /// Se llama cuando un cliente se queda sin servicio (venció o lo suspendieron).
  void Function(ApiError error)? alPerderServicio;

  final http.Client _http = http.Client();
  static const _tiempoMaximo = Duration(seconds: 15);

  Future<dynamic> get(String ruta, {Map<String, String>? parametros}) => _pedir('GET', ruta, parametros: parametros);

  Future<dynamic> post(String ruta, [Map<String, dynamic>? cuerpo]) => _pedir('POST', ruta, cuerpo: cuerpo);

  Future<dynamic> patch(String ruta, Map<String, dynamic> cuerpo) => _pedir('PATCH', ruta, cuerpo: cuerpo);

  Future<dynamic> delete(String ruta) => _pedir('DELETE', ruta);

  /// `ruta` puede ser relativa ("usuarios/5/") o una dirección completa
  /// (las que devuelve la paginación en "siguiente").
  Uri direccion(String ruta, [Map<String, String>? parametros]) {
    final base = Uri.parse(urlBase.endsWith('/') ? urlBase : '$urlBase/');
    final uri = base.resolve(ruta);
    final filtrados = {...?parametros}..removeWhere((_, valor) => valor.isEmpty);
    return filtrados.isEmpty ? uri : uri.replace(queryParameters: {...uri.queryParameters, ...filtrados});
  }

  Future<dynamic> _pedir(
    String metodo,
    String ruta, {
    Map<String, dynamic>? cuerpo,
    Map<String, String>? parametros,
  }) async {
    final pedido = http.Request(metodo, direccion(ruta, parametros));
    pedido.headers['Accept'] = 'application/json';
    if (token != null) {
      pedido.headers['Authorization'] = 'Bearer $token';
    }
    if (cuerpo != null) {
      pedido.headers['Content-Type'] = 'application/json; charset=utf-8';
      pedido.body = jsonEncode(cuerpo);
    }

    final http.Response respuesta;
    try {
      respuesta = await http.Response.fromStream(await _http.send(pedido).timeout(_tiempoMaximo));
    } on TimeoutException {
      throw _errorConexion('El servidor tardó demasiado en responder.');
    } on SocketException {
      throw _errorConexion('No se pudo conectar con el servidor.');
    } on http.ClientException {
      throw _errorConexion('No se pudo conectar con el servidor.');
    }

    if (respuesta.statusCode == 204) {
      return null;
    }
    final bytes = respuesta.bodyBytes;
    Object? datos;
    try {
      datos = await _leerJson(bytes);
    } on FormatException {
      datos = null;
    }

    if (respuesta.statusCode >= 400 || (datos == null && bytes.isNotEmpty)) {
      final error = ApiError.desdeRespuesta(respuesta.statusCode, datos);
      if (error.sesionVencida && token != null) {
        alPerderSesion?.call();
      } else if (error.sinServicio) {
        alPerderServicio?.call(error);
      }
      throw error;
    }
    return datos;
  }

  /// Las respuestas más grandes que esto (el catálogo: miles de películas y
  /// capítulos) se leen en otro hilo: leerlas en el principal congelaba la
  /// pantalla un momento (y trababa el video de la presentación, que se ve
  /// justo mientras se carga el catálogo).
  static const _grandeDesde = 64 * 1024;

  /// El JSON de la respuesta (siempre UTF-8: si no, los acentos y la ñ se ven mal).
  static Future<Object?> _leerJson(List<int> bytes) async {
    if (bytes.isEmpty) return null;
    if (bytes.length < _grandeDesde) return jsonDecode(utf8.decode(bytes));
    return Isolate.run(() => jsonDecode(utf8.decode(bytes)));
  }

  ApiError _errorConexion(String detalle) => ApiError(
    status: 0,
    codigo: 'sin_conexion',
    detalle: '$detalle Revisá que el celular y el servidor estén en la misma red y que el servidor esté encendido.',
  );
}
