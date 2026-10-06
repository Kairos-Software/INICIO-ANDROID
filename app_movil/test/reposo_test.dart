import 'dart:math';

import 'package:app_movil/api/cliente.dart';
import 'package:app_movil/api/modelos.dart';
import 'package:app_movil/marca.dart';
import 'package:app_movil/movil/datos.dart';
import 'package:app_movil/tv/reposo.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

Canal _canal(int id, String nombre, {String contenido = 'vivo'}) =>
    Canal({'id': id, 'nombre': nombre, 'logo': 'http://prueba/$id.jpg'}, contenido: contenido);

Catalogo _catalogo({int peliculas = 0, int capitulos = 0, int canales = 0, int anio = 2026}) {
  return Catalogo(ApiCliente(urlBase: 'http://prueba/api/v1/'))
    ..peliculas = [for (var i = 0; i < peliculas; i++) _canal(i, 'Película $i (${anio - i})', contenido: 'pelicula')]
    ..series = agruparSeries([for (var i = 0; i < capitulos; i++) _canal(1000 + i, 'Serie $i S01 E01')])
    ..categoriasEnVivo = [
      CategoriaCanales({
        'nombre': 'Noticias',
        'canales': [
          for (var i = 0; i < canales; i++) {'id': 2000 + i, 'nombre': 'Canal $i', 'logo': 'http://prueba/c$i.png'},
        ],
      }),
    ];
}

void main() {
  test('con todo el catálogo: logo y las 4 escenas de grupo, con un título entre cada una', () {
    final vidriera = Vidriera.delCatalogo(
      _catalogo(peliculas: 30, capitulos: 10, canales: 20),
      azar: Random(1),
      anioActual: 2026,
    );
    expect(vidriera.recorrido, [
      Escena.logo,
      Escena.titulo,
      Escena.estrenos,
      Escena.titulo,
      Escena.cifras,
      Escena.titulo,
      Escena.enVivo,
      Escena.titulo,
      Escena.series,
    ]);
    // Estrenos: de las 15 más nuevas
    for (final estreno in vidriera.estrenos) {
      expect(int.parse(estreno.detalle), greaterThanOrEqualTo(2026 - 14));
    }
    expect(vidriera.sonEstrenos, isTrue);
    expect(vidriera.peliculas, 30);
    expect(vidriera.cantidadCanales, 20);
  });

  test('películas viejas no se llaman "estrenos"', () {
    final vidriera = Vidriera.delCatalogo(_catalogo(peliculas: 10, anio: 2015), anioActual: 2026);
    expect(vidriera.recorrido, contains(Escena.estrenos));
    expect(vidriera.sonEstrenos, isFalse);
  });

  test('lo que no tiene con qué armarse no va', () {
    final soloCanales = Vidriera.delCatalogo(_catalogo(canales: 2));
    expect(soloCanales.recorrido, [Escena.logo, Escena.titulo, Escena.cifras]); // 2 logos no alcanzan para la grilla
    expect(Vidriera.delCatalogo(_catalogo()).recorrido, [Escena.logo]);
  });

  test('las cifras se redondean para abajo', () {
    expect(cifraRedonda(7), '7');
    expect(cifraRedonda(70), '70');
    expect(cifraRedonda(77), 'Más de 70');
    expect(cifraRedonda(419), 'Más de 400');
    expect(cifraRedonda(700), '700');
    expect(cifraRedonda(1065), 'Más de 1000');
  });

  testWidgets('cada escena se dibuja en la TV sin desbordarse, y todas llevan el logo', (tester) async {
    tester.view.physicalSize = const Size(1920, 1080);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);
    final vidriera = Vidriera.delCatalogo(_catalogo(peliculas: 30, capitulos: 10, canales: 20), azar: Random(2));
    await tester.pumpWidget(MaterialApp(home: PantallaReposoTv(vidriera: vidriera)));
    for (var i = 0; i < vidriera.recorrido.length; i++) {
      await tester.pump(const Duration(seconds: 3)); // el fundido y las entradas
      expect(tester.takeException(), isNull);
      expect(find.byType(SimboloKairos), findsWidgets);
      await tester.pump(const Duration(seconds: 6)); // la siguiente
    }
  });
}
