import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:video_player/video_player.dart';
import 'package:wakelock_plus/wakelock_plus.dart';

import '../api/modelos.dart';
import '../tema.dart';
import 'canales.dart';

/// Reproduce un canal en vivo a pantalla completa (horizontal).
///
/// Prueba las fuentes del canal en orden: si una no arranca, da error o se
/// queda trabada cargando, pasa sola a la siguiente (failover). Si ninguna
/// anda, muestra el error con "Reintentar".
class PantallaReproductor extends StatefulWidget {
  const PantallaReproductor({super.key, required this.canal});

  final Canal canal;

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

  List<FuenteCanal> get _fuentes => widget.canal.fuentesReproducibles;

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
    _vigiaTrabado?.cancel();
    final anterior = _video;
    setState(() {
      _video = null;
      _fuente = indice;
      _error = null;
    });
    await anterior?.dispose();

    if (indice >= _fuentes.length) {
      setState(() => _error = _fuentes.isEmpty
          ? 'Este canal no tiene una señal que la app pueda reproducir.'
          : 'No se pudo conectar con la señal. Puede estar caída o no disponible en tu zona.');
      return;
    }

    final video = VideoPlayerController.networkUrl(
      Uri.parse(_fuentes[indice].url),
      formatHint: VideoFormat.hls,
    );
    try {
      await video.initialize().timeout(_esperaInicio);
    } catch (_) {
      await video.dispose();
      if (mounted) _probarFuente(indice + 1);   // esta no arrancó: la siguiente
      return;
    }
    if (!mounted) {
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
      _probarFuente(_fuente + 1);
      return;
    }
    if (video.value.isBuffering) {
      _vigiaTrabado ??= Timer(_esperaTrabado, () {
        _vigiaTrabado = null;
        if (mounted && _video == video && video.value.isBuffering) {
          video.removeListener(_vigilar);
          _probarFuente(_fuente + 1);
        }
      });
    } else {
      _vigiaTrabado?.cancel();
      _vigiaTrabado = null;
    }
    setState(() {});   // para mostrar u ocultar el "cargando"
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
      body: GestureDetector(
        behavior: HitTestBehavior.opaque,
        onTap: () => _controlesVisibles ? setState(() => _controlesVisibles = false) : _mostrarControles(),
        child: Stack(
          fit: StackFit.expand,
          children: [
            if (video != null)
              Center(child: AspectRatio(aspectRatio: video.value.aspectRatio, child: VideoPlayer(video))),
            if (cargando) const Center(child: CircularProgressIndicator()),
            if (_error != null) _Error(mensaje: _error!, alReintentar: () => _probarFuente(0)),
            AnimatedOpacity(
              opacity: _controlesVisibles || _error != null ? 1 : 0,
              duration: const Duration(milliseconds: 250),
              child: _BarraSuperior(canal: widget.canal, fuente: _fuente, totalFuentes: _fuentes.length),
            ),
          ],
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
            Text(mensaje, textAlign: TextAlign.center, style: const TextStyle(color: Colores.texto)),
            const SizedBox(height: 20),
            OutlinedButton.icon(
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
