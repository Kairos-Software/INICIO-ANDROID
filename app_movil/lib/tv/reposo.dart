/// El modo reposo de la TV: si nadie toca el control durante un rato
/// (PantallaTv.esperaReposo, 1 minuto) y no se está reproduciendo nada,
/// aparece una "vidriera" a pantalla completa, como publicidad de Kairos TV.
///
/// Todo sale del catálogo DE ESE MOMENTO (no hay imágenes fijas dentro de la
/// app): si una película se saca o deja de ser estreno, desaparece sola de la
/// vidriera, sin sacar una versión nueva. Las escenas ([Escena]):
///
///   - logo:      el logo de Kairos TV y la hora. Siempre se vuelve a ella.
///   - titulo:    una película, serie o canal: la imagen grande y borrosa de
///                fondo con un zoom lento, el póster nítido, el título y qué es.
///                Va una distinta entre cada una de las otras.
///   - estrenos:  los pósters de las películas más nuevas (por el año del nombre).
///   - cifras:    "Más de 700 películas · 400 series · 70 canales en vivo".
///   - enVivo:    los logos de los canales.
///   - series:    los pósters de algunas series.
///
/// Todas llevan el logo. Las de la marca (logo, cifras, grupos) van sobre el
/// escenario de neón DIBUJADO (tv/escenario.dart): nítido en cualquier TV.
///
/// Calidad: las imágenes del catálogo (las que traen las listas) muchas veces
/// son chicas. Antes de usarlas se mide cada una ([_PantallaReposoTvState._medir]):
/// en grande (escena "titulo") solo van las que tienen buena resolución, y en
/// los grupos, las que alcanzan para su tamaño. Si no hay suficientes, la
/// escena se saltea: mejor no mostrarla que mostrarla pixelada. Cambia cada
/// [_cadaCuanto] con un fundido.
///
/// Cualquier botón la cierra y se vuelve a donde se estaba (esa tecla no hace
/// nada más). Mantiene la pantalla encendida [_encendidaHasta]; después deja
/// que la TV se apague o ponga su propio protector (no gastar ni marcar la pantalla).
library;

import 'dart:async';
import 'dart:math';
import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:wakelock_plus/wakelock_plus.dart';

import '../api/modelos.dart';
import '../marca.dart';
import '../movil/datos.dart';
import '../movil/estilo.dart';
import 'escenario.dart';

const _cadaCuanto = Duration(seconds: 9);
const _fundido = Duration(milliseconds: 1400);
const _encendidaHasta = Duration(minutes: 30);
const _maximoTitulos = 30;

/// Cuántos pósters o logos van en las escenas de grupo, y cuántos hacen falta para armarlas.
const _porGrupo = 5;
const _logosEnVivo = 12;
const _minimoGrupo = 4;

/// Se eligen el triple de candidatos: después se descartan los de mala calidad.
const _candidatos = 3;

/// El ancho mínimo (en píxeles de la imagen original) para que se vea bien:
/// un póster en grande (380 px de ancho en la TV), un póster en un grupo
/// (~300 px), un logo en grande y un logo en la grilla.
const _minimoPosterGrande = 340.0;
const _minimoPosterGrupo = 220.0;
const _minimoLogoGrande = 240.0;
const _minimoLogoGrupo = 120.0;

enum Escena { logo, titulo, estrenos, cifras, enVivo, series }

/// Una película, serie o canal.
class Diapositiva {
  const Diapositiva({
    required this.titulo,
    required this.tipo,
    required this.imagen,
    this.detalle = '',
    this.poster = true,
  });

  final String titulo;

  /// "Película", "Serie", "En vivo".
  final String tipo;
  final String imagen;

  /// Ej: "3 temporadas", la categoría.
  final String detalle;

  /// Póster vertical (películas y series) o logo (canales).
  final bool poster;
}

/// Lo que muestra el modo reposo, sacado del catálogo.
class Vidriera {
  Vidriera({
    this.titulos = const [],
    this.estrenos = const [],
    this.canales = const [],
    this.series = const [],
    this.peliculas = 0,
    this.cantidadSeries = 0,
    this.cantidadCanales = 0,
    this.sonEstrenos = true,
  });

  /// Para la escena "titulo" (una por vez, mezclados).
  final List<Diapositiva> titulos;
  final List<Diapositiva> estrenos;
  final List<Diapositiva> canales;
  final List<Diapositiva> series;

  /// Para las cifras.
  final int peliculas;
  final int cantidadSeries;
  final int cantidadCanales;

  /// Si las películas de "estrenos" son de este año o el anterior. Si no, se
  /// titula "Películas destacadas" (no se le dice estreno a algo de hace años).
  final bool sonEstrenos;

  static Vidriera delCatalogo(Catalogo catalogo, {Random? azar, int? anioActual}) {
    azar ??= Random();
    anioActual ??= DateTime.now().year;
    List<T> algunos<T>(Iterable<T> lista, int cuantos) => (lista.toList()..shuffle(azar)).take(cuantos).toList();

    Diapositiva dePelicula(Canal pelicula) => Diapositiva(
      titulo: sinAnio(pelicula.nombre),
      tipo: 'Película',
      imagen: pelicula.logo,
      detalle: _anio(pelicula.nombre),
    );
    Diapositiva deSerie(Serie serie) => Diapositiva(
      titulo: serie.nombre,
      tipo: 'Serie',
      imagen: serie.imagen,
      detalle: serie.temporadas.length == 1 ? '1 temporada' : '${serie.temporadas.length} temporadas',
    );
    Diapositiva deCanal(Canal canal) => Diapositiva(
      titulo: canal.nombre,
      tipo: 'En vivo',
      imagen: canal.logo,
      detalle: categoriaLegible(canal.categoria),
      poster: false,
    );

    final peliculas = catalogo.peliculas.where((p) => p.logo.isNotEmpty).toList();
    final series = catalogo.series.where((s) => s.imagen.isNotEmpty).toList();
    final canales = catalogo.canales.where((c) => c.logo.isNotEmpty).toList();

    // Estrenos: de las 15 más nuevas, 5 al azar (así cambian de una vez a la otra)
    final conAnio = peliculas.where((p) => anioDe(p.nombre) != null).toList()
      ..sort((a, b) => anioDe(b.nombre)!.compareTo(anioDe(a.nombre)!));
    final nuevas = algunos(conAnio.take(20), _porGrupo * _candidatos);
    final masNueva = nuevas.isEmpty ? 0 : nuevas.map((p) => anioDe(p.nombre)!).reduce(max);

    final titulos = [
      for (final p in algunos(peliculas, 14)) dePelicula(p),
      for (final s in algunos(series, 10)) deSerie(s),
      for (final c in algunos(canales, 6)) deCanal(c),
    ]..shuffle(azar);

    return Vidriera(
      titulos: titulos.take(_maximoTitulos).toList(),
      estrenos: [for (final p in nuevas) dePelicula(p)],
      sonEstrenos: masNueva >= anioActual - 1,
      canales: [for (final c in algunos(canales, _logosEnVivo * 2)) deCanal(c)],
      series: [for (final s in algunos(series, _porGrupo * _candidatos)) deSerie(s)],
      peliculas: catalogo.peliculas.length,
      cantidadSeries: catalogo.series.length,
      cantidadCanales: catalogo.canales.length,
    );
  }

  static String _anio(String nombre) => anioDe(nombre)?.toString() ?? '';

  /// El orden de las escenas: el logo, y entre cada una de las otras, un título.
  /// Las que no tienen con qué armarse no van.
  List<Escena> get recorrido {
    final grupos = [
      if (estrenos.length >= _minimoGrupo) Escena.estrenos,
      if (peliculas + cantidadSeries + cantidadCanales > 0) Escena.cifras,
      if (canales.length >= _minimoGrupo) Escena.enVivo,
      if (series.length >= _minimoGrupo) Escena.series,
    ];
    return [
      Escena.logo,
      for (final grupo in grupos) ...[if (titulos.isNotEmpty) Escena.titulo, grupo],
      if (grupos.isEmpty && titulos.isNotEmpty) ...List.filled(3, Escena.titulo),
    ];
  }

  /// Todas las imágenes (para medirlas y bajarlas de antemano).
  Iterable<String> get imagenes => {...titulos, ...estrenos, ...canales, ...series}.map((d) => d.imagen).toSet();
}

/// "+700", "+1.000": redondea para abajo (a 10 o a 50/100), así la cifra nunca
/// promete de más. Si es justa, sin el "+".
String cifraRedonda(int cantidad) {
  if (cantidad < 10) return '$cantidad';
  final paso = cantidad < 100 ? 10 : (cantidad < 1000 ? 50 : 100);
  final redondo = cantidad ~/ paso * paso;
  final conPuntos = '$redondo'.replaceAllMapped(RegExp(r'(\d)(?=(\d{3})+$)'), (m) => '${m[1]}.');
  return redondo == cantidad ? conPuntos : '+$conPuntos';
}

class PantallaReposoTv extends StatefulWidget {
  const PantallaReposoTv({super.key, required this.vidriera});

  final Vidriera vidriera;

  @override
  State<PantallaReposoTv> createState() => _PantallaReposoTvState();
}

class _PantallaReposoTvState extends State<PantallaReposoTv> {
  late final List<Escena> _recorrido = widget.vidriera.recorrido;
  int _paso = 0;

  /// El título que se muestra ahora y el próximo.
  Diapositiva? _titulo;
  int _siguienteTitulo = 0;
  Timer? _reloj;
  Timer? _apagar;

  /// El ancho de cada imagen ya medida (0 = no cargó).
  final _anchos = <String, double>{};
  final _escuchas = <(ImageStream, ImageStreamListener)>[];

  Escena get _escena => _recorrido[_paso];

  @override
  void initState() {
    super.initState();
    WakelockPlus.enable().catchError((Object _) {});
    _apagar = Timer(_encendidaHasta, () => WakelockPlus.disable().catchError((Object _) {}));
    _reloj = Timer.periodic(_cadaCuanto, (_) => _avanzar());
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) _medir();
    });
  }

  @override
  void dispose() {
    for (final (flujo, escucha) in _escuchas) {
      flujo.removeListener(escucha);
    }
    _reloj?.cancel();
    _apagar?.cancel();
    WakelockPlus.disable().catchError((Object _) {});
    super.dispose();
  }

  /// Baja todas las imágenes y anota de qué tamaño es cada una (la escena del
  /// logo, que va primero, da tiempo de sobra).
  void _medir() {
    for (final url in widget.vidriera.imagenes) {
      final flujo = NetworkImage(url).resolve(createLocalImageConfiguration(context));
      late final (ImageStream, ImageStreamListener) par;
      void anotar(double ancho) {
        _anchos[url] = ancho;
        // Ya se sabe: se suelta (y se saca de la lista, para no soltarla dos veces al cerrar)
        if (_escuchas.remove(par)) flujo.removeListener(par.$2);
      }

      par = (
        flujo,
        ImageStreamListener((info, _) => anotar(info.image.width.toDouble()), onError: (_, _) => anotar(0)),
      );
      _escuchas.add(par);
      flujo.addListener(par.$2);
    }
  }

  /// ¿Se ve bien a este tamaño? (las que todavía no se midieron, no)
  bool _sirve(Diapositiva diapositiva, {required bool grande}) {
    final ancho = _anchos[diapositiva.imagen] ?? 0;
    final minimo = diapositiva.poster
        ? (grande ? _minimoPosterGrande : _minimoPosterGrupo)
        : (grande ? _minimoLogoGrande : _minimoLogoGrupo);
    return ancho >= minimo;
  }

  List<Diapositiva> _buenas(List<Diapositiva> lista, int cuantas) =>
      lista.where((d) => _sirve(d, grande: false)).take(cuantas).toList();

  /// El próximo título que se ve bien en grande, o null.
  int? _proximoTitulo() {
    final lista = widget.vidriera.titulos;
    for (var i = 0; i < lista.length; i++) {
      final indice = (_siguienteTitulo + i) % lista.length;
      if (_sirve(lista[indice], grande: true)) return indice;
    }
    return null;
  }

  /// ¿Esta escena tiene con qué armarse bien ahora?
  bool _sePuede(Escena escena) {
    final vidriera = widget.vidriera;
    return switch (escena) {
      Escena.logo || Escena.cifras => true,
      Escena.titulo => _proximoTitulo() != null,
      Escena.estrenos => _buenas(vidriera.estrenos, _porGrupo).length >= _minimoGrupo,
      Escena.series => _buenas(vidriera.series, _porGrupo).length >= _minimoGrupo,
      Escena.enVivo => _buenas(vidriera.canales, _logosEnVivo).length >= _minimoGrupo,
    };
  }

  void _avanzar() {
    if (!mounted) return;
    setState(() {
      // La siguiente que se pueda armar (el logo siempre se puede)
      do {
        _paso = (_paso + 1) % _recorrido.length;
      } while (!_sePuede(_escena));
      if (_escena != Escena.titulo) return;
      final indice = _proximoTitulo()!;
      _titulo = widget.vidriera.titulos[indice];
      _siguienteTitulo = indice + 1;
    });
  }

  void _salir() {
    if (mounted) Navigator.of(context).maybePop();
  }

  Widget _pantalla() {
    final vidriera = widget.vidriera;
    return switch (_escena) {
      Escena.logo => const _PantallaLogo(),
      Escena.titulo => _PantallaTitulo(diapositiva: _titulo!),
      Escena.estrenos => _PantallaGrupo(
        sobretitulo: vidriera.sonEstrenos ? 'Recién llegadas' : 'Para ver hoy',
        titulo: vidriera.sonEstrenos ? 'Estrenos' : 'Películas destacadas',
        bajada: vidriera.sonEstrenos ? 'Las películas más nuevas, ya en Kairos TV' : 'Elegí la tuya en Kairos TV',
        diapositivas: _buenas(vidriera.estrenos, _porGrupo),
      ),
      Escena.series => _PantallaGrupo(
        sobretitulo: 'Series',
        titulo: 'Temporadas completas',
        bajada: 'Seguí tus series capítulo a capítulo',
        diapositivas: _buenas(vidriera.series, _porGrupo),
      ),
      Escena.enVivo => _PantallaEnVivo(
        canales: _buenas(vidriera.canales, _logosEnVivo),
        cantidad: vidriera.cantidadCanales,
      ),
      Escena.cifras => _PantallaCifras(vidriera: vidriera),
    };
  }

  @override
  Widget build(BuildContext context) {
    return Focus(
      autofocus: true,
      // Cualquier botón vuelve (y no hace nada más). Se sale al SOLTARLO: si
      // no, el "soltar OK" llegaría a la pantalla de abajo y abriría lo elegido.
      onKeyEvent: (_, evento) {
        if (evento is KeyUpEvent) _salir();
        return KeyEventResult.handled;
      },
      child: GestureDetector(
        onTap: _salir,
        child: Material(
          color: Colors.black,
          child: AnimatedSwitcher(
            duration: _fundido,
            switchInCurve: Curves.easeOut,
            switchOutCurve: Curves.easeIn,
            child: KeyedSubtree(key: ValueKey(_paso), child: _pantalla()),
          ),
        ),
      ),
    );
  }
}

/// El logo abajo a la izquierda y la hora abajo a la derecha, en todas las escenas (menos la del logo).
class _Pie extends StatelessWidget {
  const _Pie();

  @override
  Widget build(BuildContext context) {
    return const Stack(
      children: [
        Positioned(left: 120, bottom: 48, child: LogoKairos(tamanio: 34)),
        Positioned(right: 120, bottom: 48, child: _Hora()),
      ],
    );
  }
}

/// El fondo de las escenas de grupo: el escenario de neón, tenue y oscurecido
/// arriba a la izquierda (donde va el texto) para que se lea bien.
class _FondoMarca extends StatelessWidget {
  const _FondoMarca({this.centrado = false});

  /// El texto va al centro (las cifras): se oscurece el medio en vez de la izquierda.
  final bool centrado;

  @override
  Widget build(BuildContext context) {
    return Stack(
      fit: StackFit.expand,
      children: [
        const EscenarioNeon(intensidad: .7, puntoRubi: false),
        DecoratedBox(
          decoration: BoxDecoration(
            gradient: centrado
                ? const RadialGradient(radius: .6, colors: [Color(0xB3040507), Color(0x00040507)])
                : const LinearGradient(
                    begin: Alignment.centerLeft,
                    end: Alignment.centerRight,
                    colors: [Color(0xCC040507), Color(0x66040507), Color(0x33040507)],
                  ),
          ),
        ),
      ],
    );
  }
}

/// "RECIÉN LLEGADAS" en celeste, el título grande y una bajada.
class _Encabezado extends StatelessWidget {
  const _Encabezado({required this.sobretitulo, required this.titulo, required this.bajada, this.color = Tono.celeste});

  final String sobretitulo;
  final String titulo;
  final String bajada;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          sobretitulo.toUpperCase(),
          style: TextStyle(
            fontFamily: Letra.texto,
            fontSize: 20,
            fontWeight: FontWeight.w800,
            letterSpacing: 3,
            color: color,
          ),
        ),
        const SizedBox(height: 10),
        Text(titulo, style: LetraTv.portada.copyWith(fontSize: 64)),
        const SizedBox(height: 8),
        Text(bajada, style: LetraTv.cuerpo.copyWith(fontSize: 24)),
      ],
    );
  }
}

/// La pantalla a la que siempre se vuelve: el logo, la hora y cómo salir.
class _PantallaLogo extends StatefulWidget {
  const _PantallaLogo();

  @override
  State<_PantallaLogo> createState() => _PantallaLogoState();
}

class _PantallaLogoState extends State<_PantallaLogo> {
  @override
  Widget build(BuildContext context) {
    return Stack(
      fit: StackFit.expand,
      children: [
        const EscenarioNeon(),
        // El logo, un poco arriba del centro (sobre el punto de fuga del pasillo)
        const Align(alignment: Alignment(0, -.12), child: LogoKairos(tamanio: 150)),
        Align(
          alignment: const Alignment(0, .62),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const _Hora(grande: true),
              const SizedBox(height: 10),
              Text(
                'Apretá cualquier botón para volver',
                style: LetraTv.ayuda.copyWith(fontSize: 18, color: Tono.textoSuave),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

/// Una película, serie o canal: la imagen de fondo borrosa con zoom lento, el póster y el título.
class _PantallaTitulo extends StatelessWidget {
  const _PantallaTitulo({required this.diapositiva});

  final Diapositiva diapositiva;

  @override
  Widget build(BuildContext context) {
    final imagen = Image.network(
      diapositiva.imagen,
      fit: diapositiva.poster ? BoxFit.cover : BoxFit.contain,
      errorBuilder: (_, _, _) => const SizedBox.shrink(),
    );
    return Stack(
      fit: StackFit.expand,
      children: [
        // Fondo: la misma imagen, enorme, borrosa y con un zoom lento ("Ken Burns")
        TweenAnimationBuilder<double>(
          tween: Tween(begin: 1.08, end: 1.22),
          duration: _cadaCuanto + _fundido,
          builder: (_, escala, hijo) => Transform.scale(scale: escala, child: hijo),
          child: ImageFiltered(
            imageFilter: ImageFilter.blur(sigmaX: 40, sigmaY: 40),
            child: Image.network(
              diapositiva.imagen,
              fit: BoxFit.cover,
              errorBuilder: (_, _, _) => const SizedBox.shrink(),
            ),
          ),
        ),
        // Oscurecido para que se lea el texto
        const DecoratedBox(
          decoration: BoxDecoration(
            gradient: LinearGradient(
              colors: [Color(0xF2131317), Color(0xB3131317), Color(0x66131317)],
              stops: [0, .5, 1],
            ),
          ),
        ),
        Padding(
          padding: const EdgeInsets.fromLTRB(120, 90, 120, 90),
          child: Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 7),
                      decoration: BoxDecoration(
                        color: diapositiva.tipo == 'En vivo' ? Tono.rubi : Tono.celeste,
                        borderRadius: BorderRadius.circular(99),
                      ),
                      child: Text(
                        diapositiva.tipo.toUpperCase(),
                        style: TextStyle(
                          fontFamily: Letra.texto,
                          fontSize: 15,
                          fontWeight: FontWeight.w800,
                          letterSpacing: 1.4,
                          color: diapositiva.tipo == 'En vivo' ? Colors.white : Tono.sobreCelesteOscuro,
                        ),
                      ),
                    ),
                    const SizedBox(height: 26),
                    Text(
                      diapositiva.titulo,
                      maxLines: 3,
                      overflow: TextOverflow.ellipsis,
                      style: LetraTv.portada.copyWith(fontSize: 72),
                    ),
                    if (diapositiva.detalle.isNotEmpty) ...[
                      const SizedBox(height: 14),
                      Text(diapositiva.detalle, style: LetraTv.cuerpo.copyWith(fontSize: 24)),
                    ],
                    const SizedBox(height: 34),
                    Text(
                      'Disponible en Kairos TV',
                      style: LetraTv.ayuda.copyWith(fontSize: 20, color: Tono.celesteClaro),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 80),
              // El póster nítido (o el logo del canal sobre una tarjeta)
              Container(
                width: diapositiva.poster ? 380 : 420,
                height: diapositiva.poster ? 570 : 300,
                padding: diapositiva.poster ? EdgeInsets.zero : const EdgeInsets.all(48),
                decoration: BoxDecoration(
                  color: Tono.capaAlta,
                  borderRadius: BorderRadius.circular(Curva.portada),
                  boxShadow: const [BoxShadow(color: Colors.black54, blurRadius: 60, offset: Offset(0, 24))],
                ),
                clipBehavior: Clip.antiAlias,
                child: imagen,
              ),
            ],
          ),
        ),
        const _Pie(),
      ],
    );
  }
}

/// Estrenos o series: el encabezado y una fila de pósters que suben de a uno.
class _PantallaGrupo extends StatelessWidget {
  const _PantallaGrupo({
    required this.sobretitulo,
    required this.titulo,
    required this.bajada,
    required this.diapositivas,
  });

  final String sobretitulo;
  final String titulo;
  final String bajada;
  final List<Diapositiva> diapositivas;

  @override
  Widget build(BuildContext context) {
    return Stack(
      fit: StackFit.expand,
      children: [
        const _FondoMarca(),
        Padding(
          padding: const EdgeInsets.fromLTRB(120, 110, 120, 150),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _Encabezado(sobretitulo: sobretitulo, titulo: titulo, bajada: bajada),
              const SizedBox(height: 56),
              Expanded(
                child: Row(
                  children: [
                    for (var i = 0; i < diapositivas.length; i++) ...[
                      if (i > 0) const SizedBox(width: 36),
                      Expanded(
                        child: _Entrada(
                          orden: i,
                          child: _Poster(diapositiva: diapositivas[i]),
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            ],
          ),
        ),
        const _Pie(),
      ],
    );
  }
}

/// Los logos de los canales en una grilla, con "EN VIVO" en rubí.
class _PantallaEnVivo extends StatelessWidget {
  const _PantallaEnVivo({required this.canales, required this.cantidad});

  final List<Diapositiva> canales;
  final int cantidad;

  @override
  Widget build(BuildContext context) {
    return Stack(
      fit: StackFit.expand,
      children: [
        const _FondoMarca(),
        Padding(
          padding: const EdgeInsets.fromLTRB(120, 110, 120, 150),
          child: Row(
            children: [
              SizedBox(
                width: 560,
                child: _Encabezado(
                  sobretitulo: 'En vivo',
                  titulo: '${cifraRedonda(cantidad)} canales',
                  bajada: 'Noticias, deportes, películas y más, las 24 horas',
                  color: Tono.rubiClaro,
                ),
              ),
              const SizedBox(width: 80),
              Expanded(
                child: GridView.count(
                  crossAxisCount: 4,
                  mainAxisSpacing: 24,
                  crossAxisSpacing: 24,
                  childAspectRatio: 16 / 10,
                  physics: const NeverScrollableScrollPhysics(),
                  children: [
                    for (var i = 0; i < canales.length; i++)
                      _Entrada(
                        orden: i,
                        paso: const Duration(milliseconds: 60),
                        child: Container(
                          padding: const EdgeInsets.all(22),
                          decoration: BoxDecoration(
                            color: Tono.capaAlta,
                            borderRadius: BorderRadius.circular(Curva.panel),
                          ),
                          child: Image.network(
                            canales[i].imagen,
                            fit: BoxFit.contain,
                            errorBuilder: (_, _, _) => Center(
                              child: Text(
                                canales[i].titulo,
                                maxLines: 2,
                                textAlign: TextAlign.center,
                                overflow: TextOverflow.ellipsis,
                                style: LetraTv.cuerpo.copyWith(color: Tono.texto),
                              ),
                            ),
                          ),
                        ),
                      ),
                  ],
                ),
              ),
            ],
          ),
        ),
        const _Pie(),
      ],
    );
  }
}

/// "Todo en un solo lugar": el logo grande y las cifras del catálogo.
class _PantallaCifras extends StatelessWidget {
  const _PantallaCifras({required this.vidriera});

  final Vidriera vidriera;

  @override
  Widget build(BuildContext context) {
    final cifras = [
      if (vidriera.peliculas > 0) (cifraRedonda(vidriera.peliculas), 'películas', Tono.celeste),
      if (vidriera.cantidadSeries > 0) (cifraRedonda(vidriera.cantidadSeries), 'series', Tono.dorado),
      if (vidriera.cantidadCanales > 0) (cifraRedonda(vidriera.cantidadCanales), 'canales en vivo', Tono.rubiClaro),
    ];
    return Stack(
      fit: StackFit.expand,
      children: [
        const _FondoMarca(centrado: true),
        Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const LogoKairos(tamanio: 80),
              const SizedBox(height: 28),
              Text('Todo en un solo lugar', style: LetraTv.portada.copyWith(fontSize: 56)),
              const SizedBox(height: 64),
              Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  for (var i = 0; i < cifras.length; i++) ...[
                    if (i > 0) Container(width: 1, height: 110, color: Tono.bordeSuave.withValues(alpha: .7)),
                    _Entrada(
                      orden: i,
                      paso: const Duration(milliseconds: 250),
                      child: Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 72),
                        child: Column(
                          children: [
                            Text(
                              cifras[i].$1,
                              style: TextStyle(
                                fontFamily: Letra.titulos,
                                fontSize: 96,
                                fontWeight: FontWeight.w800,
                                letterSpacing: -1.5,
                                color: cifras[i].$3,
                              ),
                            ),
                            Text(
                              cifras[i].$2.toUpperCase(),
                              style: LetraTv.cuerpo.copyWith(fontSize: 20, letterSpacing: 4, color: Tono.textoSuave),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ],
                ],
              ),
            ],
          ),
        ),
        const Positioned(right: 120, bottom: 48, child: _Hora()),
      ],
    );
  }
}

/// Un póster con su título debajo.
class _Poster extends StatelessWidget {
  const _Poster({required this.diapositiva});

  final Diapositiva diapositiva;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(
          child: Container(
            width: double.infinity,
            decoration: BoxDecoration(
              color: Tono.capaAlta,
              borderRadius: BorderRadius.circular(Curva.tarjeta),
              boxShadow: const [BoxShadow(color: Colors.black54, blurRadius: 40, offset: Offset(0, 16))],
            ),
            clipBehavior: Clip.antiAlias,
            child: Image.network(
              diapositiva.imagen,
              fit: BoxFit.cover,
              errorBuilder: (_, _, _) => const Center(child: SimboloKairos(tamanio: 64)),
            ),
          ),
        ),
        const SizedBox(height: 14),
        Text(
          diapositiva.titulo,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: LetraTv.cuerpo.copyWith(fontSize: 22, color: Tono.texto, fontWeight: FontWeight.w600),
        ),
        if (diapositiva.detalle.isNotEmpty) Text(diapositiva.detalle, style: LetraTv.ayuda.copyWith(fontSize: 18)),
      ],
    );
  }
}

/// Aparece subiendo y aclarándose, un poco después que el anterior ([orden] × [paso]).
class _Entrada extends StatefulWidget {
  const _Entrada({required this.orden, required this.child, this.paso = const Duration(milliseconds: 140)});

  final int orden;
  final Duration paso;
  final Widget child;

  @override
  State<_Entrada> createState() => _EntradaState();
}

class _EntradaState extends State<_Entrada> with SingleTickerProviderStateMixin {
  late final AnimationController _animacion = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 700),
  );
  Timer? _espera;

  @override
  void initState() {
    super.initState();
    _espera = Timer(_fundido ~/ 2 + widget.paso * widget.orden, () {
      if (mounted) _animacion.forward();
    });
  }

  @override
  void dispose() {
    _espera?.cancel();
    _animacion.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final curva = CurvedAnimation(parent: _animacion, curve: Curves.easeOutCubic);
    return FadeTransition(
      opacity: curva,
      child: SlideTransition(
        position: Tween(begin: const Offset(0, .12), end: Offset.zero).animate(curva),
        child: widget.child,
      ),
    );
  }
}

/// La hora (se actualiza sola).
class _Hora extends StatefulWidget {
  const _Hora({this.grande = false});

  final bool grande;

  @override
  State<_Hora> createState() => _HoraState();
}

class _HoraState extends State<_Hora> {
  late DateTime _ahora = DateTime.now();
  Timer? _reloj;

  @override
  void initState() {
    super.initState();
    _reloj = Timer.periodic(const Duration(seconds: 15), (_) => setState(() => _ahora = DateTime.now()));
  }

  @override
  void dispose() {
    _reloj?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final hora = '${_ahora.hour.toString().padLeft(2, '0')}:${_ahora.minute.toString().padLeft(2, '0')}';
    return Text(
      hora,
      style: TextStyle(
        fontFamily: Letra.titulos,
        fontSize: widget.grande ? 64 : 28,
        fontWeight: FontWeight.w700,
        letterSpacing: -1,
        color: widget.grande ? Tono.texto : Tono.textoSuave,
        fontFeatures: const [FontFeature.tabularFigures()],
      ),
    );
  }
}
