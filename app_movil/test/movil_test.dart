import 'package:app_movil/api/cliente.dart';
import 'package:app_movil/api/modelos.dart';
import 'package:app_movil/aparato.dart';
import 'package:app_movil/movil/datos.dart';
import 'package:flutter_test/flutter_test.dart';

Canal _capitulo(int id, String nombre) =>
    Canal({'id': id, 'nombre': nombre, 'fuentes': <dynamic>[]}, categoria: 'SERIES | HBO', contenido: 'serie');

void main() {
  test('los capítulos sueltos se agrupan en series y temporadas', () {
    final series = agruparSeries([
      _capitulo(1, 'Silicon Veil S01 E02 El Algoritmo'),
      _capitulo(2, 'Silicon Veil S01 E01'),
      _capitulo(3, 'silicon veil - S2E1 - Vuelta'),
      _capitulo(4, 'Otra Serie 1x03'),
      _capitulo(5, 'Especial sin número'),
    ]);
    expect(series.map((s) => s.nombre), ['Silicon Veil', 'Otra Serie', 'Especial sin número']);
    final silicon = series.first;
    expect(silicon.numerosDeTemporada, [1, 2]);
    expect(silicon.temporadas[1]!.map((e) => e.numero), [1, 2]); // ordenados
    expect(silicon.temporadas[1]!.last.titulo, 'El Algoritmo');
    expect(silicon.temporadas[2]!.single.codigo, 'T2:E1');
    expect(series[1].temporadas[1]!.single.numero, 3);
  });

  test('las fuentes con un códec que el aparato no muestra no se usan (ni las de 10 bits)', () {
    final canal = Canal({
      'id': 1,
      'nombre': 'Canal 26',
      'fuentes': [
        {'id': 1, 'url': 'https://a/1.m3u8', 'tipo': 'hls', 'codec': 'mpeg2'},
        {'id': 2, 'url': 'https://a/2.m3u8', 'tipo': 'hls', 'codec': 'h264'},
        {'id': 3, 'url': 'https://a/3.m3u8', 'tipo': 'hls'}, // sin códec: se supone que anda
        {'id': 4, 'url': 'https://a/4.mkv', 'tipo': 'directo', 'codec': 'h264_10'},
      ],
    });
    Aparato.codecs = {};
    expect(canal.fuentesReproducibles.map((f) => f.id), [1, 2, 3, 4]); // no se sabe qué muestra el aparato
    Aparato.codecs = {'h264', 'h265'};
    addTearDown(() => Aparato.codecs = {});
    expect(canal.fuentesReproducibles.map((f) => f.id), [2, 3]);
    Aparato.codecs = {'h264', 'h264_10'};
    expect(canal.fuentesReproducibles.map((f) => f.id), [2, 3, 4]);
  });

  test('solo se muestran las series que arrancan en T1:E1 y tienen al menos 3 capítulos', () {
    final series = agruparSeries([
      for (var i = 1; i <= 3; i++) _capitulo(i, 'Completa S01 E0$i'),
      _capitulo(10, 'A medias S01 E05'),
      _capitulo(11, 'A medias S01 E06'),
      _capitulo(12, 'A medias S01 E07'),
      _capitulo(20, 'Cortita S01 E01'),
      _capitulo(21, 'Cortita S01 E02'),
      _capitulo(30, 'Película suelta'),
    ]);
    expect(series.where((s) => s.completa).map((s) => s.nombre), ['Completa']);
  });

  test('lo que no anduvo en este aparato se saca del catálogo enseguida', () {
    NoAnda.olvidarTodo();
    addTearDown(NoAnda.olvidarTodo);
    final pelicula = Canal({'id': 50, 'nombre': 'Rota (2024)'}, contenido: 'pelicula');
    final catalogo = Catalogo(ApiCliente(urlBase: 'http://prueba/api/v1/'))
      ..peliculas = [
        pelicula,
        Canal({'id': 51, 'nombre': 'Buena (2024)'}, contenido: 'pelicula'),
      ]
      ..series = agruparSeries([for (var i = 1; i <= 3; i++) _capitulo(i, 'Serie S01 E0$i')]);
    addTearDown(catalogo.dispose);

    NoAnda.anotar(pelicula, deFormato: false);
    expect(catalogo.peliculas.map((p) => p.id), [51]);
    expect(NoAnda.oculto(50), isTrue);

    // Si falla el primer capítulo, la serie ya no se puede empezar: se saca entera
    NoAnda.anotar(catalogo.series.single.episodios.first.canal, deFormato: true);
    expect(catalogo.series, isEmpty);
  });

  test('cuánto tiempo se oculta lo que no anduvo', () {
    expect(NoAnda.cuantoTiempo(enVivo: true, deFormato: false), const Duration(hours: 6));
    expect(NoAnda.cuantoTiempo(enVivo: false, deFormato: false), const Duration(days: 3));
    expect(NoAnda.cuantoTiempo(enVivo: true, deFormato: true), const Duration(days: 30));
  });

  test('categorías, años y nombres legibles', () {
    expect(categoriaLegible('VOD | SPAIN'), 'Spain');
    expect(categoriaLegible('LAME | ARGENTINA'), 'Argentina');
    expect(categoriaLegible('Noticias'), 'Noticias');
    expect(anioDe('6 Guns (2010)'), 2010);
    expect(anioDe('Sin año'), isNull);
    expect(sinAnio('6 Guns (2010)'), '6 Guns');
  });

  test('progreso: fracción, terminado y cuánto falta', () {
    final biblioteca = Biblioteca();
    biblioteca.guardarProgreso(7, const Duration(minutes: 30), const Duration(minutes: 60));
    biblioteca.guardarProgreso(8, const Duration(minutes: 59), const Duration(minutes: 60));
    biblioteca.guardarProgreso(9, const Duration(seconds: 20), const Duration(seconds: 40)); // muy corto: no se guarda
    expect(biblioteca.progresoDe(7)!.fraccion, .5);
    expect(biblioteca.progresoDe(7)!.falta, const Duration(minutes: 30));
    expect(biblioteca.progresoDe(8)!.terminado, isTrue);
    expect(biblioteca.continuarViendo.map((p) => p.id), [7]); // el terminado no aparece
    expect(biblioteca.progresoDe(9), isNull);
    biblioteca.alternarMiLista('s:Silicon Veil');
    expect(biblioteca.estaEnMiLista('s:Silicon Veil'), isTrue);
  });
}
