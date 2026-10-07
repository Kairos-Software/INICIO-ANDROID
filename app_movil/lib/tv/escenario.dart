/// El "escenario" de la marca: un pasillo oscuro con paneles de neón celeste a
/// los costados que se pierden hacia el centro, arcos de luz, el piso que
/// refleja y un punto rubí (como la pantalla de carga v2). Está DIBUJADO (no es
/// una imagen): se ve nítido en cualquier TV, también en 4K, y no pesa nada.
///
/// Se mueve despacio: el brillo respira y una luz recorre el borde del piso.
///
///   EscenarioNeon()                 a pleno (pantalla del logo)
///   EscenarioNeon(intensidad: .5)   más tenue, de fondo detrás de contenido
library;

import 'dart:math';

import 'package:flutter/material.dart';

import '../movil/estilo.dart';

class EscenarioNeon extends StatefulWidget {
  const EscenarioNeon({super.key, this.intensidad = 1, this.puntoRubi = true});

  /// 0 a 1: cuánto brillan los neones.
  final double intensidad;

  /// El reflejo rubí en el piso, debajo del centro (donde va el logo).
  final bool puntoRubi;

  @override
  State<EscenarioNeon> createState() => _EscenarioNeonState();
}

class _EscenarioNeonState extends State<EscenarioNeon> with SingleTickerProviderStateMixin {
  late final AnimationController _tiempo = AnimationController(vsync: this, duration: const Duration(seconds: 12))
    ..repeat();

  @override
  void dispose() {
    _tiempo.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return RepaintBoundary(
      child: CustomPaint(painter: _PintorEscenario(_tiempo, widget.intensidad, widget.puntoRubi), size: Size.infinite),
    );
  }
}

class _PintorEscenario extends CustomPainter {
  _PintorEscenario(this.tiempo, this.intensidad, this.puntoRubi) : super(repaint: tiempo);

  final Animation<double> tiempo;
  final double intensidad;
  final bool puntoRubi;

  static const _celeste = Tono.celeste;
  static const _rubi = Tono.rubi;

  @override
  void paint(Canvas canvas, Size tamanio) {
    final ancho = tamanio.width;
    final alto = tamanio.height;
    final t = tiempo.value;
    // El brillo "respira" (dos veces por vuelta)
    final respiro = .82 + .18 * sin(t * 2 * pi * 2);
    final brillo = intensidad * respiro;
    final centro = Offset(ancho / 2, alto * .46);
    final piso = alto * .66;

    // ── Fondo: casi negro, con un poco de azul petróleo en el horizonte ──
    canvas.drawRect(
      Offset.zero & tamanio,
      Paint()
        ..shader = const LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [Color(0xFF040507), Color(0xFF061219), Color(0xFF071A22), Color(0xFF030405)],
          stops: [0, .55, .66, 1],
        ).createShader(Offset.zero & tamanio),
    );

    // Un resplandor grande detrás del centro
    canvas.drawCircle(
      centro,
      ancho * .42,
      Paint()
        ..shader = RadialGradient(
          colors: [
            _celeste.withValues(alpha: .10 * brillo),
            _celeste.withValues(alpha: 0),
          ],
        ).createShader(Rect.fromCircle(center: centro, radius: ancho * .42)),
    );

    // ── Arcos concéntricos (como un túnel) ──
    for (var i = 0; i < 5; i++) {
      final radio = alto * (.30 + i * .11);
      final arco = Rect.fromCenter(center: centro.translate(0, alto * .05), width: radio * 2.2, height: radio * 2);
      canvas.drawArc(
        arco,
        pi * 1.08,
        pi * .84,
        false,
        Paint()
          ..style = PaintingStyle.stroke
          ..strokeWidth = 2
          ..color = _celeste.withValues(alpha: (.16 - i * .025) * brillo)
          ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 2),
      );
    }

    // ── Paneles de los costados (tres por lado, cada uno más lejos) ──
    for (final lado in [-1.0, 1.0]) {
      for (var i = 2; i >= 0; i--) {
        _panel(canvas, tamanio, centro, piso, lado, i, brillo);
      }
    }

    // ── El piso ──
    final rectPiso = Rect.fromLTRB(0, piso, ancho, alto);
    canvas.drawRect(
      rectPiso,
      Paint()
        ..shader = LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [
            _celeste.withValues(alpha: .07 * brillo),
            const Color(0x00000000),
          ],
        ).createShader(rectPiso),
    );
    // La línea del horizonte, con una luz que la recorre desde el centro hacia afuera
    canvas.drawLine(
      Offset(ancho * .08, piso),
      Offset(ancho * .92, piso),
      Paint()
        ..shader = LinearGradient(
          colors: [
            _celeste.withValues(alpha: 0),
            _celeste.withValues(alpha: .85 * brillo),
            _celeste.withValues(alpha: 0),
          ],
        ).createShader(Rect.fromLTRB(ancho * .08, piso - 2, ancho * .92, piso + 2))
        ..strokeWidth = 3,
    );
    final avance = Curves.easeInOut.transform((t * 2) % 1);
    for (final lado in [-1.0, 1.0]) {
      final x = ancho / 2 + lado * avance * ancho * .42;
      canvas.drawCircle(
        Offset(x, piso),
        18,
        Paint()
          ..color = _celeste.withValues(alpha: .5 * intensidad * (1 - avance))
          ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 14),
      );
    }

    // El reflejo rubí debajo del centro
    if (puntoRubi) {
      final reflejo = Rect.fromCenter(center: Offset(ancho / 2, piso + alto * .07), width: 26, height: alto * .16);
      canvas.drawRect(
        reflejo,
        Paint()
          ..shader = LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [
              _rubi.withValues(alpha: .55 * brillo),
              _rubi.withValues(alpha: 0),
            ],
          ).createShader(reflejo)
          ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 10),
      );
    }

    // Viñeta: los bordes más oscuros, para que la vista vaya al centro
    canvas.drawRect(
      Offset.zero & tamanio,
      Paint()
        ..shader = RadialGradient(
          radius: .9,
          colors: const [Color(0x00000000), Color(0x73000000)],
          stops: const [.6, 1],
        ).createShader(Offset.zero & tamanio),
    );
  }

  /// Un panel: una placa vertical oscura con el borde de neón, en perspectiva hacia el centro.
  void _panel(Canvas canvas, Size tamanio, Offset centro, double piso, double lado, int profundidad, double brillo) {
    final ancho = tamanio.width;
    final alto = tamanio.height;
    // Cuánto se acerca al punto de fuga (0 = adelante, en el borde de la pantalla)
    final lejos = [.0, .16, .30][profundidad];
    double haciaElCentro(double valor, double destino) => valor + (destino - valor) * lejos;

    final xAfuera = haciaElCentro(lado < 0 ? -ancho * .02 : ancho * 1.02, centro.dx);
    final xAdentro = haciaElCentro(ancho / 2 + lado * ancho * .44, centro.dx);
    final arribaAfuera = haciaElCentro(-alto * .05, centro.dy);
    final arribaAdentro = haciaElCentro(alto * .10, centro.dy);
    final abajo = haciaElCentro(piso + alto * .04, piso);

    final placa = Path()
      ..moveTo(xAfuera, arribaAfuera)
      ..lineTo(xAdentro, arribaAdentro)
      ..lineTo(xAdentro, abajo)
      ..lineTo(xAfuera, abajo)
      ..close();
    canvas.drawPath(
      placa,
      Paint()
        ..shader = LinearGradient(
          begin: lado < 0 ? Alignment.centerLeft : Alignment.centerRight,
          end: lado < 0 ? Alignment.centerRight : Alignment.centerLeft,
          colors: [const Color(0xFF071318), const Color(0xFF0B2A33)],
        ).createShader(placa.getBounds()),
    );
    // La cara del panel toma luz del borde de neón
    final cara = placa.getBounds();
    canvas.drawPath(
      placa,
      Paint()
        ..shader = LinearGradient(
          begin: lado < 0 ? Alignment.centerRight : Alignment.centerLeft,
          end: lado < 0 ? Alignment.centerLeft : Alignment.centerRight,
          colors: [
            _celeste.withValues(alpha: .28 * brillo),
            _celeste.withValues(alpha: 0),
          ],
          stops: const [0, .6],
        ).createShader(cara),
    );

    // El borde de adentro y el de arriba, con brillo (más tenue cuanto más lejos)
    final fuerza = brillo * (1 - profundidad * .15);
    final borde = Path()
      ..moveTo(xAfuera, arribaAfuera)
      ..lineTo(xAdentro, arribaAdentro)
      ..lineTo(xAdentro, abajo);
    canvas.drawPath(
      borde,
      Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 40
        ..color = _celeste.withValues(alpha: .45 * fuerza)
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 26),
    );
    canvas.drawPath(
      borde,
      Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 10
        ..color = _celeste.withValues(alpha: .9 * fuerza)
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 5),
    );
    canvas.drawPath(
      borde,
      Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 3.5
        ..color = Color.lerp(_celeste, Colors.white, .7)!.withValues(alpha: fuerza.clamp(0, 1)),
    );

    // Su reflejo en el piso
    final reflejo = Rect.fromLTRB(xAdentro - 6, abajo, xAdentro + 6, abajo + alto * .22 * (1 - lejos));
    canvas.drawRect(
      reflejo,
      Paint()
        ..shader = LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [
            _celeste.withValues(alpha: .6 * fuerza),
            _celeste.withValues(alpha: 0),
          ],
        ).createShader(reflejo)
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 6),
    );
  }

  @override
  bool shouldRepaint(_PintorEscenario anterior) => anterior.intensidad != intensidad || anterior.puntoRubi != puntoRubi;
}
