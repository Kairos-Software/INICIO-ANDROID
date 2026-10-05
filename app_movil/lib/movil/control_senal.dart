/// Reproduce un canal, película o capítulo probando sus fuentes en orden:
/// si una no arranca, da error o se queda trabada cargando, pasa sola a la
/// siguiente (failover) y le avisa al servidor que esa falló y por qué (ver
/// [Falla]). Si ninguna anda, queda con [error]: el motivo de la última.
///
/// Lo usan el reproductor chico de "En vivo" y los de pantalla completa.
///
///     final control = ControlSenal(api)..addListener(() => setState(() {}));
///     await control.abrir(canal);            // o abrir(pelicula, desde: Duration(minutes: 24))
///     VideoPlayer(control.video!)
library;

import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:video_player/video_player.dart';

import '../api/cliente.dart';
import '../api/modelos.dart';
import '../senales.dart';

class ControlSenal extends ChangeNotifier {
  ControlSenal(this.api);

  /// Cuánto se espera a que arranque. Una película o capítulo es un archivo
  /// grande y tarda más en empezar que un canal en vivo.
  static const _esperaVivo = Duration(seconds: 15);
  static const _esperaArchivo = Duration(seconds: 30);
  static const _esperaTrabado = Duration(seconds: 20);

  final ApiCliente api;

  /// Se llama cuando un canal en vivo empieza a verse (para "Últimos canales vistos").
  void Function(Canal canal)? alVerCanal;

  Canal? canal;
  VideoPlayerController? video;
  String? error;
  int fuente = 0;
  bool _cerrado = false;

  /// Sube cada vez que se empieza a probar una fuente: si mientras una carga
  /// se cambia de canal, su resultado (que llega tarde) se descarta.
  int _intento = 0;
  Timer? _vigiaTrabado;
  Duration? _desde;
  double _volumen = 1;
  Falla? _ultimaFalla;

  Duration get _esperaInicio => canal?.contenido == 'vivo' ? _esperaVivo : _esperaArchivo;

  List<FuenteCanal> get fuentes => canal?.fuentesReproducibles ?? const [];

  bool get cargando => error == null && (video == null || video!.value.isBuffering);

  bool get silenciado => _volumen == 0;

  /// Empieza a reproducir [nuevo] (corta lo que estaba). [desde]: para seguir donde se dejó.
  Future<void> abrir(Canal nuevo, {Duration? desde}) {
    canal = nuevo;
    _desde = desde;
    _ultimaFalla = null;
    return _probar(0);
  }

  /// Vuelve a intentar desde la primera fuente.
  Future<void> reintentar() {
    _ultimaFalla = null;
    return _probar(0);
  }

  /// Pasa a una fuente en particular (el usuario la eligió).
  Future<void> usarFuente(int indice) => _probar(indice);

  Future<void> _probar(int indice) async {
    final intento = ++_intento;
    _vigiaTrabado?.cancel();
    final anterior = video;
    video = null;
    fuente = indice;
    error = null;
    _avisar();
    await anterior?.dispose();
    if (intento != _intento || _cerrado) return;

    if (indice >= fuentes.length) {
      error = fuentes.isEmpty
          ? 'Este canal no tiene una señal que la app pueda reproducir.'
          : (_ultimaFalla?.mensaje ?? Falla.conexion.mensaje);
      _avisar();
      return;
    }

    final elegida = fuentes[indice];
    final Senal senal;
    try {
      // YouTube, Twitch...: primero hay que averiguar dónde está el video (ver senales.dart)
      senal = await resolverSenal(elegida, api).timeout(_esperaInicio);
    } catch (e) {
      if (intento == _intento && !_cerrado) {
        _avisarFalla(elegida, Falla.de(e));
        _probar(indice + 1);
      }
      return;
    }
    if (intento != _intento || _cerrado) return;

    final nuevo = VideoPlayerController.networkUrl(
      Uri.parse(senal.url),
      formatHint: senal.formato,
      httpHeaders: senal.cabeceras, // como un navegador (o VLC): algunos canales rechazan a ExoPlayer
    );
    try {
      await nuevo.initialize().timeout(_esperaInicio);
    } catch (e) {
      await nuevo.dispose();
      if (intento == _intento && !_cerrado) {
        _avisarFalla(elegida, Falla.de(e));
        _probar(indice + 1);
      }
      return;
    }
    if (intento != _intento || _cerrado) {
      await nuevo.dispose();
      return;
    }
    final desde = _desde;
    if (desde != null && desde > Duration.zero && nuevo.value.duration > desde) {
      await nuevo.seekTo(desde);
    }
    _desde = null;
    await nuevo.setVolume(_volumen);
    nuevo.addListener(_vigilar);
    await nuevo.play();
    video = nuevo;
    if (canal?.contenido == 'vivo') alVerCanal?.call(canal!);
    _avisar();
  }

  /// Si la señal da error o se queda cargando demasiado, pasa a la siguiente fuente.
  void _vigilar() {
    final actual = video;
    if (actual == null || _cerrado) return;
    if (actual.value.hasError) {
      actual.removeListener(_vigilar);
      _avisarFalla(fuentes[fuente], Falla.de(actual.value.errorDescription ?? ''));
      _probar(fuente + 1);
      return;
    }
    if (actual.value.isBuffering) {
      _vigiaTrabado ??= Timer(_esperaTrabado, () {
        _vigiaTrabado = null;
        if (!_cerrado && video == actual && actual.value.isBuffering) {
          actual.removeListener(_vigilar);
          _avisarFalla(fuentes[fuente], Falla.trabada);
          _probar(fuente + 1);
        }
      });
    } else {
      _vigiaTrabado?.cancel();
      _vigiaTrabado = null;
    }
    _avisar();
  }

  /// Le avisa al servidor que esta fuente no anduvo y por qué. El servidor la
  /// vuelve a probar por su cuenta y, si también le falla (o si falla en varios
  /// aparatos), deja de mandarla. No se espera la respuesta.
  void _avisarFalla(FuenteCanal fuente, Falla falla) {
    _ultimaFalla = falla;
    // Si el problema es la conexión de este aparato, la señal no tiene la culpa
    if (falla.motivo == Falla.sinInternet.motivo) return;
    api
        .post('canales/fuentes/${fuente.id}/falla/', {'motivo': falla.motivo, 'detalle': falla.detalle})
        .catchError((Object _) => null);
  }

  void alternarPausa() {
    final actual = video;
    if (actual == null) return;
    actual.value.isPlaying ? actual.pause() : actual.play();
    _avisar();
  }

  void alternarSonido() {
    _volumen = _volumen == 0 ? 1 : 0;
    video?.setVolume(_volumen);
    _avisar();
  }

  Future<void> saltar(Duration cuanto) async {
    final actual = video;
    if (actual == null) return;
    final destino = actual.value.position + cuanto;
    await actual.seekTo(destino < Duration.zero ? Duration.zero : destino);
  }

  /// Corta la reproducción (libera la conexión: hay listas IPTV que permiten una sola).
  Future<void> detener() async {
    ++_intento;
    _vigiaTrabado?.cancel();
    final actual = video;
    video = null;
    _avisar();
    await actual?.dispose();
  }

  void _avisar() {
    if (!_cerrado) notifyListeners();
  }

  @override
  void dispose() {
    _cerrado = true;
    ++_intento;
    _vigiaTrabado?.cancel();
    video?.dispose();
    super.dispose();
  }
}

/// Por qué no se pudo reproducir una fuente: lo que se le muestra a la persona
/// y lo que se le avisa al servidor ([motivo]: formato, rechazo, tiempo,
/// conexion, error; ver canales/servicios.py -> MOTIVOS_DE_LOS_APARATOS).
class Falla {
  const Falla(this.motivo, this.mensaje, [this.detalle = '']);

  final String motivo;
  final String mensaje;

  /// Lo técnico (lo que dijo el reproductor), recortado. Para el panel.
  final String detalle;

  static const formato = Falla('formato', 'Este aparato no puede reproducir el formato de este video.');
  static const tiempo = Falla('tiempo', 'La señal tardó demasiado en arrancar. Probá de nuevo en un rato.');
  static const trabada = Falla('tiempo', 'La señal se quedó trabada cargando.');
  static const conexion = Falla(
    'conexion',
    'No se pudo conectar con la señal. Puede estar caída o no disponible en tu zona.',
  );
  static const sinInternet = Falla('sin_internet', 'Revisá la conexión a internet de este aparato.');

  /// Lee el error que dio el reproductor (ExoPlayer) o la espera.
  factory Falla.de(Object error) {
    if (error is TimeoutException) return tiempo;
    final texto = error is PlatformException ? '${error.message} ${error.details ?? ''}' : '$error';
    final detalle = texto.replaceAll(RegExp(r'\s+'), ' ').trim();
    final corto = detalle.length > 120 ? detalle.substring(0, 120) : detalle;
    if (RegExp(
      r'UnknownHost|Unable to resolve host|ENETUNREACH|Network is unreachable',
      caseSensitive: false,
    ).hasMatch(texto)) {
      return sinInternet;
    }
    final codigo = RegExp(r'Response code: (\d{3})').firstMatch(texto)?.group(1);
    if (codigo != null && codigo.startsWith('4')) {
      return Falla('rechazo', 'El servidor de la señal no deja verla (error $codigo).', corto);
    }
    if (RegExp(
      r'Decoder|MediaCodec|NO_UNSUPPORTED|format_supported=NO|UnrecognizedInputFormat|None of the available extractors',
      caseSensitive: false,
    ).hasMatch(texto)) {
      return Falla(formato.motivo, formato.mensaje, corto);
    }
    if (error is SenalNoDisponible) return Falla('error', error.toString(), corto);
    return Falla(conexion.motivo, conexion.mensaje, corto);
  }
}
