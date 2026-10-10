import 'package:app_movil/actualizacion.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

/// Como el inicio de la TV: carga un rato y después su primer canal pide el foco solo (autofocus).
class _InicioQueCarga extends StatefulWidget {
  const _InicioQueCarga({super.key});

  @override
  State<_InicioQueCarga> createState() => _InicioQueCargaState();
}

class _InicioQueCargaState extends State<_InicioQueCarga> {
  bool cargado = false;

  void terminarDeCargar() => setState(() => cargado = true);

  @override
  Widget build(BuildContext context) => cargado
      ? Column(
          children: [
            ElevatedButton(autofocus: true, onPressed: () {}, child: const Text('Canal 1')),
            ElevatedButton(onPressed: () {}, child: const Text('Canal 2')),
          ],
        )
      : const Text('Cargando…');
}

void main() {
  test('compara versiones número por número', () {
    expect(esMasNueva('1.1.0', '1.0.0'), isTrue);
    expect(esMasNueva('1.10.0', '1.9.3'), isTrue); // no alfabético
    expect(esMasNueva('2.0', '1.9.9'), isTrue);
    expect(esMasNueva('1.1.0', '1.1.0'), isFalse);
    expect(esMasNueva('1.0.9', '1.1.0'), isFalse); // la del servidor es más vieja
    expect(esMasNueva('1.1', '1.1.0'), isFalse);
    expect(esMasNueva('1.1.0+3', '1.1.0'), isFalse); // el +N no cuenta
    expect(esMasNueva('', '1.0.0'), isFalse);
  });

  testWidgets('el control remoto no se va del cartel aunque lo de atrás termine de cargar', (tester) async {
    final inicio = GlobalKey<_InicioQueCargaState>();
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(body: _InicioQueCarga(key: inicio)),
      ),
    );
    showDialog<bool>(
      context: inicio.currentContext!,
      barrierDismissible: false,
      builder: (_) => cartelDeActualizacion(version: '9.9.9'),
    );
    await tester.pumpAndSettle();
    final actualizar = find.widgetWithText(FilledButton, 'Actualizar');
    expect(Focus.of(tester.element(find.text('Actualizar'))).hasPrimaryFocus, isTrue);

    // Atrás termina de cargar y su primer canal pide el foco: antes se lo quedaba
    inicio.currentState!.terminarDeCargar();
    await tester.pumpAndSettle();
    expect(find.text('Canal 1'), findsOneWidget);
    expect(Focus.of(tester.element(find.text('Actualizar'))).hasPrimaryFocus, isTrue);

    // Y las flechas se mueven entre los botones del cartel
    await tester.sendKeyEvent(LogicalKeyboardKey.arrowLeft);
    await tester.pumpAndSettle();
    expect(Focus.of(tester.element(find.text('Más tarde'))).hasPrimaryFocus, isTrue);
    expect(actualizar, findsOneWidget);
  });
}
