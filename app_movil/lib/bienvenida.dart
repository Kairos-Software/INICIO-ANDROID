/// La presentación al abrir la app (como la de Netflix o Disney): un video de
/// Kairos TV de ocho segundos, con su sonido incorporado.
///
/// Va ENCIMA de la app (ver main.dart): mientras se reproduce, por debajo ya se
/// cargan la sesión y el catálogo, así no se pierde tiempo. Después se desvanece.
///
///   assets/bienvenida/intro_tv.mp4        TV y celular acostado (1920×1080)
///   assets/bienvenida/intro_celular.mp4   celular parado (1080×1920)
///
/// Para que al abrir se vea DIRECTAMENTE el video (y no antes otro logo),
/// Android arranca con una pantalla lisa del mismo color de fondo (ver
/// android/app/src/main/res: launch_background y values-v31/styles.xml). Flutter
/// espera a que el reproductor tenga listo el primer cuadro antes de dibujar.
///
/// Solo se muestra al abrir la app de cero, no al volver a ella. Si el video no
/// se puede iniciar, se deja pasar a la app inmediatamente.
library;

import 'dart:async';

import 'package:flutter/material.dart';
import 'package:video_player/video_player.dart';

import 'aparato.dart';

class Bienvenida extends StatefulWidget {
  const Bienvenida({
    super.key,
    required this.child,
    this.esperarElVideo = true,
  });

  final Widget child;

  /// Demora el primer cuadro de Flutter hasta que el video esté preparado.
  /// En las pruebas se desactiva para que el motor no quede esperando.
  final bool esperarElVideo;

  static const duracion = Duration(seconds: 8);
  static const desvanecer = Duration(milliseconds: 450);

  /// El mismo color de la pantalla de arranque nativa de Android.
  static const fondo = Color(0xFF07090C);

  static const videoTv = 'assets/bienvenida/intro_tv.mp4';
  static const videoCelular = 'assets/bienvenida/intro_celular.mp4';

  @override
  State<Bienvenida> createState() => _BienvenidaState();
}

class _BienvenidaState extends State<Bienvenida> {
  VideoPlayerController? _video;
  Timer? _reloj;
  bool _visible = true;
  bool _terminada = false;
  bool _preparando = false;
  bool _primerCuadroDemorado = false;

  @override
  void initState() {
    super.initState();
    if (widget.esperarElVideo) {
      WidgetsBinding.instance.deferFirstFrame();
      _primerCuadroDemorado = true;
    }
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (!_preparando) _prepararVideo();
  }

  /// En TV siempre se usa el video horizontal. En celular se elige según la
  /// orientación física para que nunca se estire ni queden barras negras.
  static String _asset(BuildContext context) {
    final tamanio = View.of(context).physicalSize;
    final vertical = tamanio.height > tamanio.width;
    return Aparato.esTv || !vertical
        ? Bienvenida.videoTv
        : Bienvenida.videoCelular;
  }

  Future<void> _prepararVideo() async {
    _preparando = true;
    final controlador = VideoPlayerController.asset(
      _asset(context),
      videoPlayerOptions: VideoPlayerOptions(mixWithOthers: false),
    );

    try {
      await controlador.initialize().timeout(const Duration(seconds: 3));
      await controlador.setLooping(false);
      await controlador.setVolume(1);

      if (!mounted) {
        await controlador.dispose();
        return;
      }

      setState(() => _video = controlador);
      _dejarDibujar();
      await controlador.play();

      // El desvanecido ocupa los últimos 450 ms: video y audio terminan juntos.
      _reloj = Timer(Bienvenida.duracion - Bienvenida.desvanecer, () {
        if (mounted) setState(() => _visible = false);
      });
    } catch (_) {
      await controlador.dispose();
      _dejarDibujar();
      if (mounted) {
        setState(() {
          _video = null;
          _visible = false;
          _terminada = true;
        });
      }
    }
  }

  void _dejarDibujar() {
    if (!_primerCuadroDemorado) return;
    _primerCuadroDemorado = false;
    WidgetsBinding.instance.allowFirstFrame();
  }

  @override
  void dispose() {
    _dejarDibujar();
    _reloj?.cancel();
    _video?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Stack(
      textDirection: TextDirection.ltr,
      children: [
        widget.child,
        if (!_terminada)
          Positioned.fill(
            child: AbsorbPointer(
              absorbing: _visible,
              child: AnimatedOpacity(
                opacity: _visible ? 1 : 0,
                duration: Bienvenida.desvanecer,
                curve: Curves.easeOut,
                onEnd: () {
                  if (!_visible && mounted) {
                    setState(() => _terminada = true);
                    _video?.dispose();
                    _video = null;
                  }
                },
                child: ColoredBox(
                  color: Bienvenida.fondo,
                  child: _video == null
                      ? const SizedBox.expand()
                      : _VideoPantalla(controlador: _video!),
                ),
              ),
            ),
          ),
      ],
    );
  }
}

class _VideoPantalla extends StatelessWidget {
  const _VideoPantalla({required this.controlador});

  final VideoPlayerController controlador;

  @override
  Widget build(BuildContext context) {
    final tamanio = controlador.value.size;
    return ClipRect(
      child: SizedBox.expand(
        child: FittedBox(
          fit: BoxFit.cover,
          child: SizedBox(
            width: tamanio.width,
            height: tamanio.height,
            child: VideoPlayer(controlador),
          ),
        ),
      ),
    );
  }
}
