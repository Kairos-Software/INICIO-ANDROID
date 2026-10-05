import 'package:app_movil/api/modelos.dart';
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
