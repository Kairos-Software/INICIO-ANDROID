import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:video_player/video_player.dart';
import 'package:wakelock_plus/wakelock_plus.dart';

import '../api/modelos.dart';
import '../senales.dart';
import '../sesion.dart';
import '../tema.dart';
import 'canales.dart';

/// Reproduce un canal en vivo a pantalla completa (horizontal).
///
/// Prueba las fuentes del canal en orden: si una no arranca, da error o se
/// queda trabada cargando, pasa sola a la siguiente (failover). Si ninguna
/// anda, muestra el error con "Reintentar".
///
/// Con el control remoto (TV): arriba / abajo o CH+ / CH− cambian de canal
/// (zapping), OK o cualquier flecha muestra los datos del canal, y "Atrás"
/// vuelve a la lista.
class PantallaReproductor extends StatefulWidget {
  const PantallaReproductor({super.key, required this.canal, this.todos = const []});

  final Canal canal;

  /// Todos los canales en orden, para el zapping. Vacío = sin zapping.
  final List<Canal> todos;

  @override
  State<PantallaReproductor> createState() => _PantallaReproductorState();
}

class _PantallaReproductorState extends State<PantallaReproductor> {
  static const _esperaInicio = Duration(seconds: 15);
  static const _esperaTrabado = Duration(seconds: 20);

  VideoPlayerController? _video;
  int _fuente = 0;
  String? _error;
  bool _controlesVisibles = true;
  Timer? _ocultarControles;
  Timer? _vigiaTrabado;

  /// El canal que se está mirando (cambia con el zapping, sin salir de esta pantalla).
  late Canal _canal = widget.canal;

  /// Sube cada vez que se empieza a probar una fuente: si mientras una carga
  /// se cambia de canal, su resultado (que llega tarde) se descarta.
  int _intento = 0;

  List<FuenteCanal> get _fuentes => _canal.fuentesReproducibles;

  @override
  void initState() {
    super.initState();
    // Pantalla completa, horizontal, y que no se apague mientras se mira
    SystemChrome.setPreferredOrientations([DeviceOrientation.landscapeLeft, DeviceOrientation.landscapeRight]);
    SystemChrome.setEnabledSystemUIMode(SystemUiMode.immersiveSticky);
    WakelockPlus.enable();
    _probarFuente(0);
  }

  @override
  void dispose() {
    _ocultarControles?.cancel();
    _vigiaTrabado?.cancel();
    _video?.dispose();
    SystemChrome.setPreferredOrientations([]);
    SystemChrome.setEnabledSystemUIMode(SystemUiMode.edgeToEdge);
    WakelockPlus.disable();
    super.dispose();
  }

  Future<void> _probarFuente(int indice) async {
    final intento = ++_intento;
    final api = SesionScope.leer(context).api;
    _vigiaTrabado?.cancel();
    final anterior = _video;
    setState(() {
      _video = null;
      _fuente = indice;
      _error = null;
    });
    await anterior?.dispose();
    if (intento != _intento) return;

    if (indice >= _fuentes.length) {
      setState(
        () => _error = _fuentes.isEmpty
            ? 'Este canal no tiene una señal que la app pueda reproducir.'
            : 'No se pudo conectar con la señal. Puede estar caída o no disponible en tu zona.',
      );
      return;
    }

    final fuente = _fuentes[indice];
    // YouTube, Twitch...: primero hay que averiguar dónde está el video (ver senales.dart)
    final Senal senal;
    try {
      senal = await resolverSenal(fuente, api).timeout(_esperaInicio);
    } catch (_) {
      if (mounted && intento == _intento) {
        _avisarFalla(fuente);
        _probarFuente(indice + 1);
      }
      return;
    }
    if (!mounted || intento != _intento) return;

    final video = VideoPlayerController.networkUrl(
      Uri.parse(senal.url),
      formatHint: senal.formato,
      httpHeaders: senal.cabeceras, // como un navegador (o VLC): algunos canales rechazan a ExoPlayer
    );
    try {
      await video.initialize().timeout(_esperaInicio);
    } catch (_) {
      await video.dispose();
      if (mounted && intento == _intento) {
        _avisarFalla(_fuentes[indice]);
        _probarFuente(indice + 1); // esta no arrancó: la siguiente
      }
      return;
    }
    if (!mounted || intento != _intento) {
      await video.dispose();
      return;
    }
    video.addListener(_vigilar);
    await video.play();
    setState(() => _video = video);
    _mostrarControles();
  }

  /// Si la señal da error o se queda cargando demasiado, pasa a la siguiente fuente.
  void _vigilar() {
    final video = _video;
    if (video == null || !mounted) return;
    if (video.value.hasError) {
      video.removeListener(_vigilar);
      _avisarFalla(_fuentes[_fuente]);
      _probarFuente(_fuente + 1);
      return;
    }
    if (video.value.isBuffering) {
      _vigiaTrabado ??= Timer(_esperaTrabado, () {
        _vigiaTrabado = null;
        if (mounted && _video == video && video.value.isBuffering) {
          video.removeListener(_vigilar);
          _avisarFalla(_fuentes[_fuente]);
          _probarFuente(_fuente + 1);
        }
      });
    } else {
      _vigiaTrabado?.cancel();
      _vigiaTrabado = null;
    }
    setState(() {}); // para mostrar u ocultar el "cargando"
  }

  /// Le avisa al servidor que esta fuente no anduvo. El servidor la vuelve a
  /// probar por su cuenta y, si también le falla, deja de mandarla: así los
  /// canales caídos desaparecen solos de la lista. No se espera la respuesta.
  void _avisarFalla(FuenteCanal fuente) {
    SesionScope.leer(context).api.post('canales/fuentes/${fuente.id}/falla/').catchError((Object _) {
      // Si el aviso no llega, no pasa nada: la verificación del servidor la va a encontrar igual
      return null;
    });
  }

  /// Pasa al canal siguiente (+1) o anterior (−1), dando la vuelta en los extremos.
  /// Se queda en esta misma pantalla: así no se pierde la pantalla completa
  /// ni el "no apagar la pantalla" entre canal y canal.
  void _zapping(int paso) {
    final todos = widget.todos;
    final actual = todos.indexWhere((c) => c.id == _canal.id);
    if (todos.length < 2 || actual < 0) return;
    setState(() => _canal = todos[(actual + paso) % todos.length]);
    _probarFuente(0);
  }

  KeyEventResult _tecla(FocusNode nodo, KeyEvent evento) {
    if (evento is! KeyDownEvent) return KeyEventResult.ignored;
    final tecla = evento.logicalKey;
    if (tecla == LogicalKeyboardKey.arrowUp || tecla == LogicalKeyboardKey.channelUp) {
      _zapping(1);
      return KeyEventResult.handled;
    }
    if (tecla == LogicalKeyboardKey.arrowDown || tecla == LogicalKeyboardKey.channelDown) {
      _zapping(-1);
      return KeyEventResult.handled;
    }
    if (tecla == LogicalKeyboardKey.select ||
        tecla == LogicalKeyboardKey.enter ||
        tecla == LogicalKeyboardKey.arrowLeft ||
        tecla == LogicalKeyboardKey.arrowRight) {
      // Con el error en pantalla, OK tiene que llegar al botón "Reintentar"
      if (_error != null) return KeyEventResult.ignored;
      _mostrarControles();
      return KeyEventResult.handled;
    }
    return KeyEventResult.ignored;
  }

  void _mostrarControles() {
    setState(() => _controlesVisibles = true);
    _ocultarControles?.cancel();
    _ocultarControles = Timer(const Duration(seconds: 4), () {
      if (mounted) setState(() => _controlesVisibles = false);
    });
  }

  @override
  Widget build(BuildContext context) {
    final video = _video;
    final cargando = _error == null && (video == null || video.value.isBuffering);

    return Scaffold(
      backgroundColor: Colors.black,
      body: Focus(
        autofocus: true,
        onKeyEvent: _tecla,
        child: GestureDetector(
          behavior: HitTestBehavior.opaque,
          onTap: () => _controlesVisibles ? setState(() => _controlesVisibles = false) : _mostrarControles(),
          child: Stack(
            fit: StackFit.expand,
            children: [
              if (video != null)
                Center(
                  child: AspectRatio(aspectRatio: video.value.aspectRatio, child: VideoPlayer(video)),
                ),
              if (cargando) const Center(child: CircularProgressIndicator()),
              if (_error != null) _Error(mensaje: _error!, alReintentar: () => _probarFuente(0)),
              AnimatedOpacity(
                opacity: _controlesVisibles || _error != null ? 1 : 0,
                duration: const Duration(milliseconds: 250),
                child: _BarraSuperior(canal: _canal, fuente: _fuente, totalFuentes: _fuentes.length),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _BarraSuperior extends StatelessWidget {
  const _BarraSuperior({required this.canal, required this.fuente, required this.totalFuentes});

  final Canal canal;
  final int fuente;
  final int totalFuentes;

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: Alignment.topCenter,
      child: Container(
        padding: const EdgeInsets.fromLTRB(12, 16, 24, 32),
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            colors: [Colors.black87, Colors.transparent],
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
          ),
        ),
        child: SafeArea(
          bottom: false,
          child: Row(
            children: [
              IconButton(
                icon: const Icon(Icons.arrow_back_rounded, color: Colors.white),
                onPressed: () => Navigator.pop(context),
              ),
              const SizedBox(width: 4),
              SizedBox(width: 44, height: 44, child: LogoCanal(canal: canal)),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  canal.nombre,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.w700),
                ),
              ),
              if (totalFuentes > 1)
                Padding(
                  padding: const EdgeInsets.only(right: 12),
                  child: Text(
                    'Fuente ${(fuente + 1).clamp(1, totalFuentes)} de $totalFuentes',
                    style: const TextStyle(color: Colores.textoSuave, fontSize: 12),
                  ),
                ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(color: Colores.peligro, borderRadius: BorderRadius.circular(6)),
                child: const Text(
                  'EN VIVO',
                  style: TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.w700, letterSpacing: 1),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _Error extends StatelessWidget {
  const _Error({required this.mensaje, required this.alReintentar});

  final String mensaje;
  final VoidCallback alReintentar;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.signal_wifi_connected_no_internet_4_rounded, color: Colores.textoSuave, size: 52),
            const SizedBox(height: 16),
            Text(
              mensaje,
              textAlign: TextAlign.center,
              style: const TextStyle(color: Colores.texto),
            ),
            const SizedBox(height: 20),
            OutlinedButton.icon(
              autofocus: true, // con el control remoto, OK reintenta
              onPressed: alReintentar,
              icon: const Icon(Icons.refresh_rounded),
              label: const Text('Reintentar'),
            ),
          ],
        ),
      ),
    );
  }
}
