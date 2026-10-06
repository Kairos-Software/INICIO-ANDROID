/// El modo reposo de la TV: si nadie toca el control durante un rato
/// (PantallaTv.esperaReposo) y no se está reproduciendo nada, aparece una
/// "vidriera" a pantalla completa con lo que hay para ver.
///
///   - La pantalla principal: el logo de Kairos TV y la hora. Siempre se
///     vuelve a ella.
///   - Entre una y otra, [_porVuelta] diapositivas con títulos del catálogo
///     (películas, series y canales con imagen): la imagen grande y borrosa de
///     fondo con un zoom lento, el póster nítido, el título y qué es.
///   - Cambia cada [_cadaCuanto] con un fundido.
///   - Cualquier botón la cierra y se vuelve a donde se estaba (esa tecla no
///     hace nada más).
///   - Mantiene la pantalla encendida [_encendidaHasta]; después deja que la
///     TV se apague o ponga su propio protector (no gastar ni marcar la pantalla).
library;

import 'dart:async';
import 'dart:math';
import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:wakelock_plus/wakelock_plus.dart';

import '../marca.dart';
import '../movil/datos.dart';
import '../movil/estilo.dart';

const _cadaCuanto = Duration(seconds: 9);
const _fundido = Duration(milliseconds: 1400);
const _porVuelta = 3;
const _encendidaHasta = Duration(minutes: 30);
const _maximoDiapositivas = 18;

/// Lo que muestra una diapositiva.
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

  /// Las diapositivas de un catálogo: títulos con imagen, mezclados.
  static List<Diapositiva> delCatalogo(Catalogo catalogo, {Random? azar}) {
    azar ??= Random();
    List<T> algunos<T>(Iterable<T> lista, int cuantos) => (lista.toList()..shuffle(azar)).take(cuantos).toList();
    final peliculas = algunos(catalogo.peliculas.where((p) => p.logo.isNotEmpty), 8);
    final series = algunos(catalogo.series.where((s) => s.imagen.isNotEmpty), 6);
    final canales = algunos(catalogo.canales.where((c) => c.logo.isNotEmpty), 4);
    final todas = [
      for (final p in peliculas)
        Diapositiva(titulo: sinAnio(p.nombre), tipo: 'Película', imagen: p.logo, detalle: _anio(p.nombre)),
      for (final s in series)
        Diapositiva(
          titulo: s.nombre,
          tipo: 'Serie',
          imagen: s.imagen,
          detalle: s.temporadas.length == 1 ? '1 temporada' : '${s.temporadas.length} temporadas',
        ),
      for (final c in canales)
        Diapositiva(
          titulo: c.nombre,
          tipo: 'En vivo',
          imagen: c.logo,
          detalle: categoriaLegible(c.categoria),
          poster: false,
        ),
    ]..shuffle(azar);
    return todas.take(_maximoDiapositivas).toList();
  }

  static String _anio(String nombre) => anioDe(nombre)?.toString() ?? '';
}

class PantallaReposoTv extends StatefulWidget {
  const PantallaReposoTv({super.key, required this.diapositivas});

  final List<Diapositiva> diapositivas;

  @override
  State<PantallaReposoTv> createState() => _PantallaReposoTvState();
}

class _PantallaReposoTvState extends State<PantallaReposoTv> {
  /// -1 = la pantalla del logo; si no, la diapositiva.
  int _actual = -1;
  int _siguiente = 0;
  int _desdeElLogo = 0;
  Timer? _reloj;
  Timer? _apagar;
  final _malas = <String>{};

  @override
  void initState() {
    super.initState();
    unawaited(WakelockPlus.enable());
    _apagar = Timer(_encendidaHasta, () => unawaited(WakelockPlus.disable()));
    _reloj = Timer.periodic(_cadaCuanto, (_) => _avanzar());
    WidgetsBinding.instance.addPostFrameCallback((_) => _precargar());
  }

  @override
  void dispose() {
    _reloj?.cancel();
    _apagar?.cancel();
    unawaited(WakelockPlus.disable());
    super.dispose();
  }

  /// La próxima diapositiva que se puede mostrar (salteando las que no cargaron), o null.
  int? _proxima() {
    final lista = widget.diapositivas;
    for (var i = 0; i < lista.length; i++) {
      final indice = (_siguiente + i) % lista.length;
      if (!_malas.contains(lista[indice].imagen)) return indice;
    }
    return null;
  }

  /// Baja de antemano la imagen que viene, así entra ya cargada (y si falla, se saltea).
  void _precargar() {
    final indice = _proxima();
    if (indice == null || !mounted) return;
    final url = widget.diapositivas[indice].imagen;
    precacheImage(NetworkImage(url), context, onError: (_, _) => _malas.add(url));
  }

  void _avanzar() {
    if (!mounted) return;
    final indice = _proxima();
    setState(() {
      if ((_actual >= 0 && _desdeElLogo >= _porVuelta) || indice == null) {
        _actual = -1; // siempre se vuelve al logo
        _desdeElLogo = 0;
      } else {
        _actual = indice;
        _siguiente = indice + 1;
        _desdeElLogo++;
      }
    });
    _precargar();
  }

  void _salir() {
    if (mounted) Navigator.of(context).maybePop();
  }

  @override
  Widget build(BuildContext context) {
    final diapositiva = _actual < 0 ? null : widget.diapositivas[_actual];
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
        child: ColoredBox(
          color: Tono.fondo,
          child: AnimatedSwitcher(
            duration: _fundido,
            switchInCurve: Curves.easeOut,
            switchOutCurve: Curves.easeIn,
            child: diapositiva == null
                ? const _PantallaLogo(key: ValueKey('logo'))
                : _PantallaTitulo(key: ValueKey(_actual), diapositiva: diapositiva),
          ),
        ),
      ),
    );
  }
}

/// La pantalla a la que siempre se vuelve: el logo, la hora y cómo salir.
class _PantallaLogo extends StatefulWidget {
  const _PantallaLogo({super.key});

  @override
  State<_PantallaLogo> createState() => _PantallaLogoState();
}

class _PantallaLogoState extends State<_PantallaLogo> with SingleTickerProviderStateMixin {
  // Un "respirar" lento del brillo detrás del logo
  late final AnimationController _pulso = AnimationController(vsync: this, duration: const Duration(seconds: 4))
    ..repeat(reverse: true);

  @override
  void dispose() {
    _pulso.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Stack(
      fit: StackFit.expand,
      children: [
        AnimatedBuilder(
          animation: _pulso,
          builder: (_, _) => DecoratedBox(
            decoration: BoxDecoration(
              gradient: RadialGradient(
                radius: .75 + _pulso.value * .15,
                colors: [
                  Tono.celeste.withValues(alpha: .10 + _pulso.value * .06),
                  Tono.fondo,
                ],
              ),
            ),
          ),
        ),
        Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const LogoKairos(tamanio: 96),
              const SizedBox(height: 40),
              const _Hora(grande: true),
              const SizedBox(height: 18),
              Text('Apretá cualquier botón para volver', style: LetraTv.ayuda.copyWith(fontSize: 18)),
            ],
          ),
        ),
      ],
    );
  }
}

/// Una película, serie o canal: la imagen de fondo borrosa con zoom lento, el póster y el título.
class _PantallaTitulo extends StatelessWidget {
  const _PantallaTitulo({super.key, required this.diapositiva});

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
        const Positioned(left: 120, bottom: 48, child: LogoKairos(tamanio: 34)),
        const Positioned(right: 120, bottom: 48, child: _Hora()),
      ],
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
