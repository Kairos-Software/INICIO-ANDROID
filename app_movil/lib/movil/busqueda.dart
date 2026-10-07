/// Buscar en el catálogo, igual en el celular (movil/buscar.dart) y en la TV
/// (tv/buscar.dart): sin tildes ni mayúsculas, y primero lo que EMPIEZA con
/// lo escrito (o tiene una palabra que empieza así), después lo que solo lo
/// contiene. Ej: "la" muestra antes "La casa de papel" que "Atlántida".
///
/// [QueBuscar] es el filtro de arriba de los resultados (Todo, En vivo,
/// Películas, Series). Arranca en el de la sección donde se estaba: buscar
/// desde Series busca series.
library;

import '../api/modelos.dart';
import 'datos.dart';

enum QueBuscar {
  todo('Todo'),
  enVivo('En vivo'),
  peliculas('Películas'),
  series('Series');

  const QueBuscar(this.texto);

  final String texto;
}

/// "Notícias Ñandú" -> "noticias nandu".
String sinTildes(String texto) {
  const conTilde = 'áàäâãéèëêíìïîóòöôõúùüûñç';
  const sinTilde = 'aaaaaeeeeiiiiooooouuuunc';
  final buffer = StringBuffer();
  for (final letra in texto.toLowerCase().split('')) {
    final i = conTilde.indexOf(letra);
    buffer.write(i >= 0 ? sinTilde[i] : letra);
  }
  return buffer.toString();
}

/// Lo que se encontró, por tipo (cada lista con [maximo] como mucho).
class Encontrado {
  const Encontrado({this.canales = const [], this.peliculas = const [], this.series = const []});

  static const nada = Encontrado();

  final List<Canal> canales;
  final List<Canal> peliculas;
  final List<Serie> series;

  int cuantos(QueBuscar que) => switch (que) {
    QueBuscar.todo => canales.length + peliculas.length + series.length,
    QueBuscar.enVivo => canales.length,
    QueBuscar.peliculas => peliculas.length,
    QueBuscar.series => series.length,
  };

  bool vacio(QueBuscar que) => cuantos(que) == 0;
}

/// Busca [texto] en todo el catálogo. Con [conNumeros] (en la TV), "15"
/// también encuentra el canal 15.
Encontrado buscarEnCatalogo(Catalogo catalogo, String texto, {int maximo = 40, bool conNumeros = false}) {
  final buscado = sinTildes(texto.trim());
  if (buscado.isEmpty) return Encontrado.nada;

  List<T> filtrar<T>(Iterable<T> lista, String Function(T) nombre, [bool Function(T)? tambien]) {
    final empiezan = <T>[];
    final contienen = <T>[];
    for (final elemento in lista) {
      final simple = ' ${sinTildes(nombre(elemento))}';
      if (simple.contains(' $buscado') || (tambien?.call(elemento) ?? false)) {
        empiezan.add(elemento);
        if (empiezan.length >= maximo) break;
      } else if (contienen.length < maximo && simple.contains(buscado)) {
        contienen.add(elemento);
      }
    }
    return [...empiezan, ...contienen].take(maximo).toList();
  }

  return Encontrado(
    canales: filtrar(catalogo.canales, (c) => c.nombre, conNumeros ? (c) => catalogo.numeroDe(c) == buscado : null),
    peliculas: filtrar(catalogo.peliculas, (p) => p.nombre),
    series: filtrar(catalogo.series, (s) => s.nombre),
  );
}
