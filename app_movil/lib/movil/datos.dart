/// Los datos de las pantallas de celular:
///
///   - [Catalogo]: lo que hay para ver (canales en vivo, películas y series),
///     pedido a la API. Las series llegan como capítulos sueltos ("Show S01 E02")
///     y acá se agrupan por serie y temporada.
///   - [Biblioteca]: lo de cada aparato: "Mi lista" y "Continuar viendo"
///     (por dónde iba cada película o capítulo). Se guarda en el aparato.
library;

import 'dart:async';
import 'dart:convert';

import 'package:flutter/widgets.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../api/cliente.dart';
import '../api/modelos.dart';

// ── Series ─────────────────────────────────────────────────────────

/// Un capítulo de una serie.
class Episodio {
  Episodio({required this.canal, required this.temporada, required this.numero, required this.titulo});

  final Canal canal;
  final int temporada;
  final int numero;

  /// Lo que viene después de "S01 E02" en el nombre (puede estar vacío).
  final String titulo;

  /// "T1:E2"
  String get codigo => 'T$temporada:E$numero';
}

/// Una serie con sus temporadas (armada a partir de los capítulos sueltos).
class Serie {
  Serie({required this.nombre, required this.categoria});

  final String nombre;
  final String categoria;
  final Map<int, List<Episodio>> temporadas = {};

  /// La imagen de la serie: la del primer capítulo que tenga.
  String get imagen => episodios.map((e) => e.canal.logo).firstWhere((logo) => logo.isNotEmpty, orElse: () => '');

  List<int> get numerosDeTemporada => temporadas.keys.toList()..sort();

  List<Episodio> get episodios => [for (final t in numerosDeTemporada) ...temporadas[t]!];

  /// Para "Mi lista": las series se guardan por nombre (sus capítulos tienen cada uno su id).
  String get clave => 's:$nombre';
}

// "Show S01 E02", "Show - S1E2 - Título", "Show 1x02"
final _patronEpisodio = RegExp(
  r'^(.*?)[\s._\-:|]*(?:\bS(\d{1,2})\s*[._\- ]?\s*E(\d{1,4})|\b(\d{1,2})x(\d{1,3}))\b[\s._\-:|]*(.*)$',
  caseSensitive: false,
);

/// Los capítulos sueltos -> series con temporadas, en el orden en que llegaron.
List<Serie> agruparSeries(List<Canal> capitulos) {
  final series = <String, Serie>{};
  var sinNumero = 0;
  for (final capitulo in capitulos) {
    final partes = _patronEpisodio.firstMatch(capitulo.nombre);
    final String nombre;
    final int temporada;
    final int numero;
    final String titulo;
    if (partes != null && partes.group(1)!.trim().isNotEmpty) {
      nombre = partes.group(1)!.trim();
      temporada = int.parse(partes.group(2) ?? partes.group(4)!);
      numero = int.parse(partes.group(3) ?? partes.group(5)!);
      titulo = partes.group(6)!.trim();
    } else {
      // Sin "S01 E02": cada uno es una "serie" de un solo capítulo
      nombre = capitulo.nombre;
      temporada = 1;
      numero = ++sinNumero;
      titulo = '';
    }
    final serie = series.putIfAbsent(nombre.toLowerCase(), () => Serie(nombre: nombre, categoria: capitulo.categoria));
    serie.temporadas
        .putIfAbsent(temporada, () => [])
        .add(Episodio(canal: capitulo, temporada: temporada, numero: numero, titulo: titulo));
  }
  for (final serie in series.values) {
    for (final lista in serie.temporadas.values) {
      lista.sort((a, b) => a.numero.compareTo(b.numero));
    }
  }
  return series.values.toList();
}

/// "6 Guns (2010)" -> 2010 (o null).
int? anioDe(String nombre) {
  final anio = RegExp(r'\((19\d\d|20\d\d)\)').firstMatch(nombre);
  return anio == null ? null : int.parse(anio.group(1)!);
}

/// "6 Guns (2010)" -> "6 Guns"
String sinAnio(String nombre) => nombre.replaceAll(RegExp(r'\s*\((19\d\d|20\d\d)\)\s*'), ' ').trim();

/// "VOD | SPAIN" -> "Spain", "LAME | ARGENTINA" -> "Argentina", "Noticias" -> "Noticias".
String categoriaLegible(String categoria) {
  final partes = categoria.split('|').map((p) => p.trim()).where((p) => p.isNotEmpty).toList();
  final ultima = partes.isEmpty ? categoria.trim() : partes.last;
  if (ultima.isEmpty) return '';
  final esMayusculas = ultima == ultima.toUpperCase() && ultima.length > 3;
  return esMayusculas ? ultima[0] + ultima.substring(1).toLowerCase() : ultima;
}

// ── Catálogo ───────────────────────────────────────────────────────

/// Lo que hay para ver. Se pide al abrir la app, al volver a ella y cada 15
/// minutos (una TV o un celular pueden quedar abiertos todo el día).
class Catalogo extends ChangeNotifier {
  Catalogo(this.api);

  final ApiCliente api;

  List<CategoriaCanales> categoriasEnVivo = [];
  List<Canal> peliculas = [];
  List<Serie> series = [];

  bool cargando = false;
  bool cargado = false;
  Object? error;

  List<Canal> get canales => [for (final c in categoriasEnVivo) ...c.canales];

  Future<void> cargar() async {
    if (cargando) return;
    cargando = true;
    error = null;
    notifyListeners();
    final formatos = FuenteCanal.formatosQueReproduce.join(',');
    Future<List<CategoriaCanales>> pedir(String contenido) async {
      final datos =
          await api.get('canales/', parametros: {'formatos': formatos, 'contenido': contenido}) as Map<String, dynamic>;
      return [
        for (final c in datos['categorias'] as List) CategoriaCanales(c as Map<String, dynamic>, contenido: contenido),
      ];
    }

    try {
      final resultados = await Future.wait([pedir('vivo'), pedir('pelicula'), pedir('serie')]);
      categoriasEnVivo = resultados[0];
      peliculas = [for (final c in resultados[1]) ...c.canales];
      series = agruparSeries([for (final c in resultados[2]) ...c.canales]);
      cargado = true;
    } catch (e) {
      error = e;
    } finally {
      cargando = false;
      notifyListeners();
    }
  }

  Canal? canalPorId(int id) {
    for (final canal in canales) {
      if (canal.id == id) return canal;
    }
    for (final pelicula in peliculas) {
      if (pelicula.id == id) return pelicula;
    }
    for (final serie in series) {
      for (final episodio in serie.episodios) {
        if (episodio.canal.id == id) return episodio.canal;
      }
    }
    return null;
  }

  Serie? serieDe(Canal capitulo) {
    for (final serie in series) {
      if (serie.episodios.any((e) => e.canal.id == capitulo.id)) return serie;
    }
    return null;
  }

  Serie? seriePorNombre(String nombre) {
    for (final serie in series) {
      if (serie.nombre == nombre) return serie;
    }
    return null;
  }
}

// ── Biblioteca (lo de este aparato) ────────────────────────────────

/// Por dónde iba una película o capítulo.
class Progreso {
  Progreso({required this.id, required this.posicion, required this.duracion, required this.cuando});

  factory Progreso.desdeJson(Map<String, dynamic> json) => Progreso(
    id: json['id'] as int,
    posicion: Duration(seconds: json['p'] as int? ?? 0),
    duracion: Duration(seconds: json['d'] as int? ?? 0),
    cuando: DateTime.fromMillisecondsSinceEpoch(json['t'] as int? ?? 0),
  );

  final int id;
  final Duration posicion;
  final Duration duracion;
  final DateTime cuando;

  double get fraccion => duracion.inSeconds == 0 ? 0 : (posicion.inSeconds / duracion.inSeconds).clamp(0, 1);

  /// Ya casi termina: cuenta como visto.
  bool get terminado => fraccion >= .95;

  Duration get falta => duracion - posicion;

  Map<String, dynamic> aJson() => {
    'id': id,
    'p': posicion.inSeconds,
    'd': duracion.inSeconds,
    't': cuando.millisecondsSinceEpoch,
  };
}

/// "Mi lista" y "Continuar viendo". Se guarda en el aparato (no en el servidor).
class Biblioteca extends ChangeNotifier {
  static const _claveLista = 'kairos.mi_lista';
  static const _claveProgreso = 'kairos.progreso';
  static const _maximoProgresos = 60;

  SharedPreferences? _preferencias;
  final Set<String> _miLista = {};
  final Map<int, Progreso> _progresos = {};

  Future<void> cargar() async {
    try {
      final preferencias = await SharedPreferences.getInstance();
      _preferencias = preferencias;
      _miLista.addAll(preferencias.getStringList(_claveLista) ?? []);
      final guardados = jsonDecode(preferencias.getString(_claveProgreso) ?? '[]') as List;
      for (final p in guardados) {
        final progreso = Progreso.desdeJson(p as Map<String, dynamic>);
        _progresos[progreso.id] = progreso;
      }
    } catch (_) {
      // Si no se puede leer (ej: en los tests), se arranca vacía
    }
    notifyListeners();
  }

  // Mi lista: canales y películas por "c:<id>", series por "s:<nombre>"
  static String claveDe(Canal canal) => 'c:${canal.id}';

  bool estaEnMiLista(String clave) => _miLista.contains(clave);

  Iterable<String> get miLista => _miLista;

  void alternarMiLista(String clave) {
    _miLista.contains(clave) ? _miLista.remove(clave) : _miLista.add(clave);
    _preferencias?.setStringList(_claveLista, _miLista.toList());
    notifyListeners();
  }

  // Continuar viendo
  Progreso? progresoDe(int id) => _progresos[id];

  /// Los que quedaron a medias, el último visto primero.
  List<Progreso> get continuarViendo =>
      _progresos.values.where((p) => p.fraccion > .01 && !p.terminado).toList()
        ..sort((a, b) => b.cuando.compareTo(a.cuando));

  void guardarProgreso(int id, Duration posicion, Duration duracion) {
    if (duracion.inSeconds < 60) return; // un vivo o algo muy corto: no tiene sentido
    _progresos[id] = Progreso(id: id, posicion: posicion, duracion: duracion, cuando: DateTime.now());
    if (_progresos.length > _maximoProgresos) {
      final viejo = _progresos.values.reduce((a, b) => a.cuando.isBefore(b.cuando) ? a : b);
      _progresos.remove(viejo.id);
    }
    _preferencias?.setString(_claveProgreso, jsonEncode([for (final p in _progresos.values) p.aJson()]));
    notifyListeners();
  }

  void olvidarProgreso(int id) {
    _progresos.remove(id);
    _preferencias?.setString(_claveProgreso, jsonEncode([for (final p in _progresos.values) p.aJson()]));
    notifyListeners();
  }
}

/// Pone el catálogo y la biblioteca al alcance de todas las pantallas de celular.
class DatosScope extends InheritedWidget {
  const DatosScope({super.key, required this.catalogo, required this.biblioteca, required super.child});

  final Catalogo catalogo;
  final Biblioteca biblioteca;

  static DatosScope of(BuildContext context) => context.dependOnInheritedWidgetOfExactType<DatosScope>()!;

  @override
  bool updateShouldNotify(DatosScope oldWidget) => catalogo != oldWidget.catalogo || biblioteca != oldWidget.biblioteca;
}
