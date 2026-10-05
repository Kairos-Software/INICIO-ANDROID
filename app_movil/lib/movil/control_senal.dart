/// Reproduce un canal, película o capítulo probando sus fuentes en orden:
/// si una no arranca, da error o se queda trabada cargando, pasa sola a la
/// siguiente (failover) y le avisa al servidor que esa falló. Si ninguna
/// anda, queda con [error].
///
/// Lo usan el reproductor chico de "En vivo" y los de pantalla completa.
///
///     final control = ControlSenal(api)..addListener(() => setState(() {}));
///     await control.abrir(canal);            // o abrir(pelicula, desde: Duration(minutes: 24))
///     VideoPlayer(control.video!)
library;

import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:video_player/video_player.dart';

import '../api/cliente.dart';
import '../api/modelos.dart';
import '../senales.dart';

class ControlSenal extends ChangeNotifier {
  ControlSenal(this.api);

  static const _esperaInicio = Duration(seconds: 15);
  static const _esperaTrabado = Duration(seconds: 20);

  final ApiCliente api;

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

  List<FuenteCanal> get fuentes => canal?.fuentesReproducibles ?? const [];

  bool get cargando => error == null && (video == null || video!.value.isBuffering);

  bool get silenciado => _volumen == 0;

  /// Empieza a reproducir [nuevo] (corta lo que estaba). [desde]: para seguir donde se dejó.
  Future<void> abrir(Canal nuevo, {Duration? desde}) {
    canal = nuevo;
    _desde = desde;
    return _probar(0);
  }

  /// Vuelve a intentar desde la primera fuente.
  Future<void> reintentar() => _probar(0);

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
          : 'No se pudo conectar con la señal. Puede estar caída o no disponible en tu zona.';
      _avisar();
      return;
    }

    final elegida = fuentes[indice];
    final Senal senal;
    try {
      // YouTube, Twitch...: primero hay que averiguar dónde está el video (ver senales.dart)
      senal = await resolverSenal(elegida, api).timeout(_esperaInicio);
    } catch (_) {
      if (intento == _intento && !_cerrado) {
        _avisarFalla(elegida);
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
    } catch (_) {
      await nuevo.dispose();
      if (intento == _intento && !_cerrado) {
        _avisarFalla(elegida);
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
    _avisar();
  }

  /// Si la señal da error o se queda cargando demasiado, pasa a la siguiente fuente.
  void _vigilar() {
    final actual = video;
    if (actual == null || _cerrado) return;
    if (actual.value.hasError) {
      actual.removeListener(_vigilar);
      _avisarFalla(fuentes[fuente]);
      _probar(fuente + 1);
      return;
    }
    if (actual.value.isBuffering) {
      _vigiaTrabado ??= Timer(_esperaTrabado, () {
        _vigiaTrabado = null;
        if (!_cerrado && video == actual && actual.value.isBuffering) {
          actual.removeListener(_vigilar);
          _avisarFalla(fuentes[fuente]);
          _probar(fuente + 1);
        }
      });
    } else {
      _vigiaTrabado?.cancel();
      _vigiaTrabado = null;
    }
    _avisar();
  }

  /// Le avisa al servidor que esta fuente no anduvo. El servidor la vuelve a
  /// probar por su cuenta y, si también le falla, deja de mandarla. No se espera la respuesta.
  void _avisarFalla(FuenteCanal fuente) {
    api.post('canales/fuentes/${fuente.id}/falla/').catchError((Object _) => null);
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
