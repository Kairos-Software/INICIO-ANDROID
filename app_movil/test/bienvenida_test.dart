import 'package:app_movil/bienvenida.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('la bienvenida se ve unos segundos encima de la app y se desvanece', (tester) async {
    await tester.pumpWidget(const Bienvenida(child: MaterialApp(home: Text('la app'))));
    expect(find.byType(Image), findsOneWidget);
    expect(find.text('la app'), findsOneWidget); // por debajo ya está cargando

    await tester.pump(const Duration(seconds: 2));
    expect(find.byType(Image), findsOneWidget); // todavía se ve

    await tester.pump(Bienvenida.duracion);
    await tester.pumpAndSettle(); // el desvanecido
    expect(find.byType(Image), findsNothing); // se fue
    expect(find.text('la app'), findsOneWidget);
  });
}
