/// La marca Kairos TV: el "portal" de cuatro paneles con el punto rubí del
/// vivo en el centro (diseño de ChatGPT, diseno_kairos_tv/brand/).
///
/// Se DIBUJA (no es una imagen): así se ve nítida en cualquier tamaño y, en
/// chico, las líneas se engrosan para que se siga reconociendo. Las imágenes
/// del ícono, el banner de la TV y la pantalla de arranque salen de este
/// mismo dibujo (tools/generar_marca.py usa las mismas medidas).
library;

import 'dart:math' as math;

import 'package:flutter/material.dart';

import 'movil/estilo.dart';

/// Las medidas del símbolo, en unidades donde el ancho total es 2 (de -1 a 1).
/// Es un hexágono "de punta" cortado en cuatro paneles verticales.
class GeometriaMarca {
  GeometriaMarca._();

  /// Los paneles: de dónde a dónde va cada uno en x.
  static const paneles = [(-1.0, -0.58), (-0.502, -0.102), (0.102, 0.502), (0.58, 1.0)];

  /// Media altura del costado vertical del hexágono.
  static const mediaAlturaCostado = 0.437;

  /// Cuánto sube el techo por cada unidad que se acerca al centro (tan 30°).
  static final pendiente = math.tan(math.pi / 6);

  /// Media altura total (en el centro).
  static final mediaAltura = mediaAlturaCostado + pendiente;

  static const radioPunto = 0.13;

  /// Grosor de las líneas (relativo) y el mínimo en píxeles para que en chico no desaparezcan.
  static const grosor = 0.037;
  static const grosorMinimo = 1.6;

  /// y del techo en x (negativo = arriba).
  static double techo(double x) => -(mediaAlturaCostado + pendiente * (1 - x.abs()));
}

/// El símbolo solo. [tamanio] es el alto.
class SimboloKairos extends StatelessWidget {
  const SimboloKairos({super.key, this.tamanio = 32, this.brillo = true});

  final double tamanio;

  /// El halo celeste de los bordes y rubí del punto (en chico conviene apagarlo).
  final bool brillo;

  @override
  Widget build(BuildContext context) {
    final ancho = tamanio / GeometriaMarca.mediaAltura; // ancho total = 2 unidades
    return Semantics(
      label: 'Kairos TV',
      child: SizedBox(
        width: ancho,
        height: tamanio,
        child: CustomPaint(painter: _PintorSimbolo(brillo: brillo && tamanio >= 40)),
      ),
    );
  }
}

class _PintorSimbolo extends CustomPainter {
  _PintorSimbolo({required this.brillo});

  final bool brillo;

  @override
  void paint(Canvas canvas, Size size) {
    // Se deja un margen del grosor de la línea para que no se corte
    final escala = size.height / (2 * GeometriaMarca.mediaAltura) * 0.94;
    final grosor = math.max(GeometriaMarca.grosor * escala, GeometriaMarca.grosorMinimo);
    final centro = size.center(Offset.zero);
    Offset punto(double x, double y) => centro + Offset(x * escala, y * escala);

    final relleno = Paint()..color = const Color(0xFF16161B);
    final borde = Paint()
      ..color = Tono.celeste
      ..style = PaintingStyle.stroke
      ..strokeWidth = grosor
      ..strokeJoin = StrokeJoin.miter;
    final halo = Paint()
      ..color = Tono.celeste.withValues(alpha: .55)
      ..style = PaintingStyle.stroke
      ..strokeWidth = grosor * 2.2
      ..maskFilter = MaskFilter.blur(BlurStyle.normal, grosor * 2.5);

    for (final (desde, hasta) in GeometriaMarca.paneles) {
      final camino = Path()
        ..moveTo(punto(desde, GeometriaMarca.techo(desde)).dx, punto(desde, GeometriaMarca.techo(desde)).dy)
        ..lineTo(punto(hasta, GeometriaMarca.techo(hasta)).dx, punto(hasta, GeometriaMarca.techo(hasta)).dy)
        ..lineTo(punto(hasta, -GeometriaMarca.techo(hasta)).dx, punto(hasta, -GeometriaMarca.techo(hasta)).dy)
        ..lineTo(punto(desde, -GeometriaMarca.techo(desde)).dx, punto(desde, -GeometriaMarca.techo(desde)).dy)
        ..close();
      canvas.drawPath(camino, relleno);
      if (brillo) canvas.drawPath(camino, halo);
      canvas.drawPath(camino, borde);
    }

    final radio = math.max(GeometriaMarca.radioPunto * escala, grosor * 1.4);
    if (brillo) {
      canvas.drawCircle(
        centro,
        radio * 1.6,
        Paint()
          ..color = Tono.rubi.withValues(alpha: .5)
          ..maskFilter = MaskFilter.blur(BlurStyle.normal, radio),
      );
    }
    canvas.drawCircle(centro, radio, Paint()..color = Tono.rubi);
  }

  @override
  bool shouldRepaint(_PintorSimbolo viejo) => viejo.brillo != brillo;
}

/// El logo horizontal: el símbolo y "KairosTV" al lado. [tamanio] es el alto del símbolo.
class LogoKairos extends StatelessWidget {
  const LogoKairos({super.key, this.tamanio = 48});

  final double tamanio;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        SimboloKairos(tamanio: tamanio),
        SizedBox(width: tamanio * 0.32),
        NombreKairos(tamanio: tamanio * 0.62),
      ],
    );
  }
}

/// "KairosTV" con "TV" en celeste. [tamanio] es el de la letra.
class NombreKairos extends StatelessWidget {
  const NombreKairos({super.key, this.tamanio = 30});

  final double tamanio;

  @override
  Widget build(BuildContext context) {
    return Text.rich(
      TextSpan(
        children: [
          const TextSpan(
            text: 'Kairos',
            style: TextStyle(color: Tono.texto),
          ),
          TextSpan(
            text: 'TV',
            style: TextStyle(
              color: Tono.celeste,
              shadows: [Shadow(color: Tono.celeste.withValues(alpha: .45), blurRadius: tamanio * 0.5)],
            ),
          ),
        ],
      ),
      style: TextStyle(
        fontFamily: Letra.titulos,
        fontWeight: FontWeight.w800,
        fontSize: tamanio,
        height: 1,
        letterSpacing: -tamanio * 0.03,
      ),
    );
  }
}
