/// La presentación al abrir la app (como la de Netflix o Disney): la imagen de
/// Kairos TV con su sonido durante unos segundos, en la TV y en el celular.
///
/// Va ENCIMA de la app (ver main.dart): mientras se muestra, por debajo ya se
/// carga la sesión y el catálogo, así no se pierde tiempo. Después se desvanece.
///
///   assets/bienvenida/portada_tv.jpg        la imagen apaisada (TV, celular acostado)
///   assets/bienvenida/portada_celular.jpg   la imagen parada (celular)
///   assets/bienvenida/sonido.mp3            el sonido (7,8 s, de Pixabay: uso libre)
///
/// Las dos imágenes llenan toda la pantalla (si no tienen justo su forma, se
/// recorta un poco de los bordes: lo importante tiene que ir al centro).
///
/// Para que al abrir se vea DIRECTAMENTE esta imagen (y no antes otra cosa),
/// Android arranca con una pantalla lisa del mismo color de fondo (ver
/// android/app/src/main/res: launch_background y values-v31/styles.xml), y
/// Flutter no dibuja nada hasta que la imagen está lista ([_esperarLaImagen]).
///
/// Solo al abrir la app de cero (no al volver a ella). Si el sonido no se puede
/// reproducir, se muestra igual sin sonido.
library;

import 'dart:async';

import 'package:flutter/material.dart';
import 'package:video_player/video_player.dart';

import 'aparato.dart';

class Bienvenida extends StatefulWidget {
  const Bienvenida({super.key, required this.child, this.esperarLaImagen = true});

  final Widget child;

  /// No dibujar nada hasta tener la imagen (en las pruebas, no hace falta).
  final bool esperarLaImagen;

  /// Cuánto se ve (lo que dura el sonido) y cuánto tarda en desvanecerse.
  static const duracion = Duration(milliseconds: 7600);
  static const desvanecer = Duration(milliseconds: 700);

  /// El color de fondo: el mismo de la pantalla de arranque de Android
  /// (android/app/src/main/res/values/colors.xml -> fondo_arranque).
  static const fondo = Color(0xFF07090C);

  static const imagenTv = 'assets/bienvenida/portada_tv.jpg';
  static const imagenCelular = 'assets/bienvenida/portada_celular.jpg';

  @override
  State<Bienvenida> createState() => _BienvenidaState();
}

class _BienvenidaState extends State<Bienvenida> {
  VideoPlayerController? _sonido;
  bool _visible = true;
  bool _terminada = false;
  Timer? _reloj;
  bool _primerCuadroDemorado = false;

  @override
  void initState() {
    super.initState();
    if (widget.esperarLaImagen) {
      WidgetsBinding.instance.deferFirstFrame();
      _primerCuadroDemorado = true;
    }
    _sonar();
    _reloj = Timer(Bienvenida.duracion, () {
      if (mounted) setState(() => _visible = false);
    });
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_primerCuadroDemorado) _esperarLaImagen();
  }

  /// Baja la imagen a memoria y recién ahí deja dibujar el primer cuadro (como
  /// mucho medio segundo: si tarda más, se dibuja igual).
  Future<void> _esperarLaImagen() async {
    try {
      await precacheImage(AssetImage(_imagen(context)), context).timeout(const Duration(milliseconds: 500));
    } catch (_) {
      // Sin la imagen a tiempo, se sigue igual
    }
    _dejarDibujar();
  }

  void _dejarDibujar() {
    if (!_primerCuadroDemorado) return;
    _primerCuadroDemorado = false;
    WidgetsBinding.instance.allowFirstFrame();
  }

  /// En la TV, siempre la apaisada; en el celular, según cómo se lo tenga.
  static String _imagen(BuildContext context) {
    // Va por encima de MaterialApp (no hay MediaQuery): se le pregunta a la pantalla
    final tamanio = View.of(context).physicalSize;
    final parada = tamanio.height > tamanio.width;
    return Aparato.esTv || !parada ? Bienvenida.imagenTv : Bienvenida.imagenCelular;
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
    _dejarDibujar();
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
                child: ColoredBox(
                  color: Bienvenida.fondo,
                  child: _Portada(imagen: _imagen(context)),
                ),
              ),
            ),
          ),
      ],
    );
  }
}

/// La imagen a pantalla completa, con un acercamiento muy lento (para que no se vea "quieta").
class _Portada extends StatelessWidget {
  const _Portada({required this.imagen});

  final String imagen;

  @override
  Widget build(BuildContext context) {
    return TweenAnimationBuilder<double>(
      tween: Tween(begin: 1.0, end: 1.06),
      duration: Bienvenida.duracion + Bienvenida.desvanecer,
      curve: Curves.easeOut,
      builder: (_, escala, hijo) => Transform.scale(scale: escala, child: hijo),
      child: Image.asset(
        imagen,
        fit: BoxFit.cover,
        width: double.infinity,
        height: double.infinity,
        gaplessPlayback: true,
      ),
    );
  }
}
