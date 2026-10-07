// Herramienta (no es una prueba): dibuja pantallas a PNG para mirarlas.
//   flutter test test_vista/vista_test.dart
import 'dart:io';
import 'dart:ui' as ui;

import 'package:app_movil/marca.dart';
import 'package:app_movil/tv/escenario.dart';
import 'package:app_movil/tv/reposo.dart';
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

const salida = String.fromEnvironment('SALIDA', defaultValue: 'build/vista');

Future<void> cargarLetras() async {
  for (final (familia, archivos) in [
    ('PlusJakartaSans', ['PlusJakartaSans-Bold', 'PlusJakartaSans-ExtraBold', 'PlusJakartaSans-SemiBold']),
    ('Inter', ['Inter-Regular', 'Inter-Medium', 'Inter-SemiBold', 'Inter-Bold']),
  ]) {
    final cargador = FontLoader(familia);
    for (final a in archivos) {
      cargador.addFont(Future.value(ByteData.sublistView(File('assets/fuentes/$a.ttf').readAsBytesSync())));
    }
    await cargador.load();
  }
}

Future<void> foto(WidgetTester tester, String nombre, Widget pantalla, {Duration espera = const Duration(seconds: 3)}) async {
  final clave = GlobalKey();
  await tester.pumpWidget(MaterialApp(debugShowCheckedModeBanner: false, home: Material(color: Colors.black, child: RepaintBoundary(key: clave, child: pantalla))));
  await tester.pump(espera);
  await tester.runAsync(() async {
    final borde = clave.currentContext!.findRenderObject()! as RenderRepaintBoundary;
    final imagen = await borde.toImage();
    final datos = await imagen.toByteData(format: ui.ImageByteFormat.png);
    Directory(salida).createSync(recursive: true);
    File('$salida/$nombre.png').writeAsBytesSync(datos!.buffer.asUint8List());
  });
}

void main() {
  testWidgets('escenario', (tester) async {
    tester.view.physicalSize = const Size(1920, 1080);
    tester.view.devicePixelRatio = 1;
    await cargarLetras();
    await foto(
      tester,
      'escenario',
      const Stack(fit: StackFit.expand, children: [EscenarioNeon(), Center(child: LogoKairos(tamanio: 140))]),
    );
  });

  testWidgets('reposo', (tester) async {
    tester.view.physicalSize = const Size(1920, 1080);
    tester.view.devicePixelRatio = 1;
    await cargarLetras();
    final clave = GlobalKey();
    await tester.pumpWidget(
      MaterialApp(
        debugShowCheckedModeBanner: false,
        home: RepaintBoundary(
          key: clave,
          child: PantallaReposoTv(
            vidriera: Vidriera(peliculas: 1065, cantidadSeries: 419, cantidadCanales: 77),
          ),
        ),
      ),
    );
    Future<void> guardar(String nombre) => tester.runAsync(() async {
      final borde = clave.currentContext!.findRenderObject()! as RenderRepaintBoundary;
      final datos = await (await borde.toImage()).toByteData(format: ui.ImageByteFormat.png);
      File('$salida/$nombre.png').writeAsBytesSync(datos!.buffer.asUint8List());
    });
    await tester.pump(const Duration(seconds: 3));
    await guardar('reposo-logo');
    await tester.pump(const Duration(seconds: 6));
    for (var i = 0; i < 40; i++) {
      await tester.pump(const Duration(milliseconds: 100));
    }
    await guardar('reposo-cifras');
  });
}
