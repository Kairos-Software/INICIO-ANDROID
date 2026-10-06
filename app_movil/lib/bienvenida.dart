/// La presentación al abrir la app (como la de Netflix o Disney): la imagen de
/// Kairos TV con su sonido durante unos segundos, en la TV y en el celular.
///
/// Va ENCIMA de la app (ver main.dart): mientras se muestra, por debajo ya se
/// carga la sesión y el catálogo, así no se pierde tiempo. Después se desvanece.
///
///   assets/bienvenida/portada.jpg   la imagen (16:9; en un celular parado se
///                                   ve entera, con el fondo oscuro arriba y abajo)
///   assets/bienvenida/sonido.mp3    el sonido (4 s, de Pixabay: uso libre)
///
/// Solo al abrir la app de cero (no al volver a ella). Si el sonido no se puede
/// reproducir, se muestra igual sin sonido.
library;

import 'dart:async';

import 'package:flutter/material.dart';
import 'package:video_player/video_player.dart';

class Bienvenida extends StatefulWidget {
  const Bienvenida({super.key, required this.child});

  final Widget child;

  /// Cuánto se ve (lo que dura el sonido) y cuánto tarda en desvanecerse.
  static const duracion = Duration(milliseconds: 3600);
  static const desvanecer = Duration(milliseconds: 700);

  @override
  State<Bienvenida> createState() => _BienvenidaState();
}

class _BienvenidaState extends State<Bienvenida> {
  // El color de los bordes de la imagen: rellena lo que sobra en pantallas que no son 16:9
  static const _fondo = Color(0xFF07090C);

  VideoPlayerController? _sonido;
  bool _visible = true;
  bool _terminada = false;
  Timer? _reloj;

  @override
  void initState() {
    super.initState();
    _sonar();
    _reloj = Timer(Bienvenida.duracion, () {
      if (mounted) setState(() => _visible = false);
    });
  }

  Future<void> _sonar() async {
    try {
      final sonido = _sonido = VideoPlayerController.asset('assets/bienvenida/sonido.mp3');
      await sonido.initialize();
      if (mounted && _visible) await sonido.play();
    } catch (_) {
      // Sin sonido no pasa nada: la imagen se muestra igual
    }
  }

  @override
  void dispose() {
    _reloj?.cancel();
    _sonido?.dispose();
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
            // Mientras se ve, no deja tocar lo de abajo
            child: AbsorbPointer(
              absorbing: _visible,
              child: AnimatedOpacity(
                opacity: _visible ? 1 : 0,
                duration: Bienvenida.desvanecer,
                curve: Curves.easeOut,
                onEnd: () {
                  setState(() => _terminada = true);
                  _sonido?.dispose();
                  _sonido = null;
                },
                child: const ColoredBox(color: _fondo, child: _Portada()),
              ),
            ),
          ),
      ],
    );
  }
}

/// La imagen, con un acercamiento muy lento (para que no se vea "quieta").
class _Portada extends StatelessWidget {
  const _Portada();

  @override
  Widget build(BuildContext context) {
    return TweenAnimationBuilder<double>(
      tween: Tween(begin: 1.0, end: 1.06),
      duration: Bienvenida.duracion + Bienvenida.desvanecer,
      curve: Curves.easeOut,
      builder: (_, escala, hijo) => Transform.scale(scale: escala, child: hijo),
      child: LayoutBuilder(
        builder: (context, medidas) {
          // Apaisada (TV, celular acostado): la imagen llena la pantalla.
          // Parada (celular): se ve entera, centrada, sin cortar el logo.
          final apaisada = medidas.maxWidth >= medidas.maxHeight;
          return Image.asset(
            'assets/bienvenida/portada.jpg',
            fit: apaisada ? BoxFit.cover : BoxFit.contain,
            width: double.infinity,
            height: double.infinity,
          );
        },
      ),
    );
  }
}
