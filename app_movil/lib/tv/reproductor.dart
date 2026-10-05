/// Los reproductores de la TV (diseno_kairos_tv: tv-12, tv-13, tv-19).
///
/// EN VIVO (ReproductorVivoTv), con el control remoto:
///   Arriba/Abajo (o CH+/CH-): cambia de canal al toque (zapping).
///   Números: se escribe el número del canal (hasta 3, 1,5 s) y cambia solo.
///   OK: muestra los controles; con los controles a la vista, OK en "Guía"
///       abre la lista de canales encima del video.
///   Atrás: cierra la guía, después los controles, después sale.
///
/// PELÍCULAS Y CAPÍTULOS (ReproductorVodTv):
///   OK: pausa/sigue.  Izquierda/Derecha: -10 s / +10 s.  En los controles,
///   la línea de tiempo también se mueve con Izquierda/Derecha.
///   Guarda por dónde va cada 5 s y al terminar un capítulo sigue con el próximo.
///
/// Los controles se esconden solos a los 5 segundos.
library;

import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:video_player/video_player.dart';
import 'package:wakelock_plus/wakelock_plus.dart';

import '../api/modelos.dart';
import '../movil/componentes.dart';
import '../movil/control_senal.dart';
import '../movil/datos.dart';
import '../movil/detalle.dart' show proximoEpisodio;
import '../movil/estilo.dart';
import '../sesion.dart';
import 'estructura.dart' show DialogoTv;
import 'foco.dart';
import 'piezas.dart';

const _esperaControles = Duration(seconds: 5);

/// Pone un canal en vivo a pantalla completa. [lista]: los canales para el zapping (por defecto, todos).
Future<void> verCanalTv(BuildContext context, Canal canal, {List<Canal>? lista}) {
  final catalogo = DatosScope.of(context).catalogo;
  return abrirTv<void>(context, ReproductorVivoTv(canal: canal, lista: lista ?? catalogo.canales));
}

/// Reproduce una película (si quedó a medias, desde ahí).
Future<void> reproducirPeliculaTv(BuildContext context, Canal pelicula, {bool desdeElInicio = false}) {
  return abrirTv<void>(
    context,
    ReproductorVodTv(canal: pelicula, desde: desdeElInicio ? null : _dondeQuedo(context, pelicula)),
  );
}

/// Reproduce un capítulo (si no se dice cuál, el que corresponde: el que quedó a medias o el siguiente).
Future<void> reproducirSerieTv(BuildContext context, Serie serie, {Episodio? episodio, bool desdeElInicio = false}) {
  final elegido = episodio ?? proximoEpisodio(serie, DatosScope.of(context).biblioteca);
  return abrirTv<void>(
    context,
    ReproductorVodTv(
      canal: elegido.canal,
      serie: serie,
      episodio: elegido,
      desde: desdeElInicio ? null : _dondeQuedo(context, elegido.canal),
    ),
  );
}

Duration? _dondeQuedo(BuildContext context, Canal canal) {
  final progreso = DatosScope.of(context).biblioteca.progresoDe(canal.id);
  return progreso == null || progreso.terminado ? null : progreso.posicion;
}

// ── En vivo ────────────────────────────────────────────────────────

class ReproductorVivoTv extends StatefulWidget {
  const ReproductorVivoTv({super.key, required this.canal, required this.lista});

  final Canal canal;
  final List<Canal> lista;

  @override
  State<ReproductorVivoTv> createState() => _ReproductorVivoTvState();
}

class _ReproductorVivoTvState extends State<ReproductorVivoTv> {
  late final ControlSenal _control = ControlSenal(SesionScope.leer(context).api)
    ..alVerCanal = ((canal) => DatosScope.of(context).biblioteca.registrarCanalVisto(canal.id))
    ..addListener(_alCambiar);
  final _raiz = FocusNode(debugLabel: 'reproductor');
  bool _controles = true;
  bool _guia = false;
  Timer? _ocultar;

  /// El número que se está escribiendo con el control ("10_").
  String _numero = '';
  Timer? _numeroListo;

  @override
  void initState() {
    super.initState();
    WakelockPlus.enable().catchError((Object _) {});
    _control.abrir(widget.canal);
    _mostrarControles();
  }

  @override
  void dispose() {
    _ocultar?.cancel();
    _numeroListo?.cancel();
    _control.dispose();
    _raiz.dispose();
    WakelockPlus.disable().catchError((Object _) {});
    super.dispose();
  }

  void _alCambiar() {
    if (mounted) setState(() {});
  }

  Canal get _canal => _control.canal ?? widget.canal;

  void _mostrarControles() {
    setState(() => _controles = true);
    _reiniciarEspera();
  }

  void _reiniciarEspera() {
    _ocultar?.cancel();
    _ocultar = Timer(_esperaControles, () {
      if (!mounted || _guia || _control.error != null) return;
      setState(() => _controles = false);
      _raiz.requestFocus();
    });
  }

  void _zapping(int paso) {
    final lista = widget.lista;
    if (lista.length < 2) return;
    final actual = lista.indexWhere((c) => c.id == _canal.id);
    _control.abrir(lista[((actual < 0 ? 0 : actual) + paso) % lista.length]);
    _mostrarControles();
  }

  void _ver(Canal canal) {
    setState(() => _guia = false);
    _control.abrir(canal);
    _mostrarControles();
    _raiz.requestFocus();
  }

  void _escribirNumero(String digito) {
    _numeroListo?.cancel();
    setState(() => _numero = (_numero + digito).length > 3 ? digito : _numero + digito);
    _numeroListo = Timer(const Duration(milliseconds: 1500), () {
      final canal = DatosScope.of(context).catalogo.canalPorNumero(_numero);
      setState(() => _numero = '');
      if (canal != null) {
        _ver(canal);
      } else {
        avisoTv(context, 'No hay un canal con ese número', icono: Icons.info_outline_rounded);
      }
    });
  }

  KeyEventResult _tecla(FocusNode _, KeyEvent evento) {
    if (evento is KeyUpEvent) return KeyEventResult.ignored;
    final tecla = evento.logicalKey;
    final digito = evento.character != null && RegExp(r'^\d$').hasMatch(evento.character!) ? evento.character : null;
    if (digito != null && !_guia) {
      _escribirNumero(digito);
      return KeyEventResult.handled;
    }
    if (tecla == LogicalKeyboardKey.channelUp) {
      _zapping(1);
      return KeyEventResult.handled;
    }
    if (tecla == LogicalKeyboardKey.channelDown) {
      _zapping(-1);
      return KeyEventResult.handled;
    }
    if (_guia) return KeyEventResult.ignored;
    if (_controles) {
      _reiniciarEspera();
      return KeyEventResult.ignored; // las flechas recorren los controles
    }
    if (tecla == LogicalKeyboardKey.arrowUp) {
      _zapping(1);
      return KeyEventResult.handled;
    }
    if (tecla == LogicalKeyboardKey.arrowDown) {
      _zapping(-1);
      return KeyEventResult.handled;
    }
    if (teclasOk.contains(tecla) || tecla == LogicalKeyboardKey.arrowLeft || tecla == LogicalKeyboardKey.arrowRight) {
      _mostrarControles();
      return KeyEventResult.handled;
    }
    return KeyEventResult.ignored;
  }

  Future<void> _elegirFuente() async {
    final elegida = await elegirFuenteTv(context, _control);
    if (elegida != null) _control.usarFuente(elegida);
  }

  @override
  Widget build(BuildContext context) {
    final biblioteca = DatosScope.of(context).biblioteca;
    final catalogo = DatosScope.of(context).catalogo;
    final canal = _canal;
    final clave = Biblioteca.claveDe(canal);
    final favorito = biblioteca.estaEnMiLista(clave);
    final numero = catalogo.numeroDe(canal);
    final categoria = categoriaLegible(canal.categoria);
    final escrito = _numero.isEmpty ? null : catalogo.canalPorNumero(_numero);

    return PopScope(
      canPop: !_guia && !_controles,
      onPopInvokedWithResult: (salio, _) {
        if (salio) return;
        if (_guia) {
          setState(() => _guia = false);
          _mostrarControles();
        } else {
          setState(() => _controles = false);
          _raiz.requestFocus();
        }
      },
      child: Scaffold(
        backgroundColor: Colors.black,
        body: Focus(
          // Sin autofocus: al abrir, el foco va al primer botón de los controles;
          // cuando se esconden, lo toma la pantalla entera (_raiz)
          focusNode: _raiz,
          onKeyEvent: _tecla,
          child: Stack(
            fit: StackFit.expand,
            children: [
              _Video(control: _control),
              _EstadoSenal(
                control: _control,
                alReintentar: _control.reintentar,
                alGuia: () {
                  setState(() {
                    _guia = true;
                    _controles = true;
                  });
                },
              ),
              if (_controles || _guia)
                const Positioned(top: MargenTv.arriba, left: MargenTv.derecha, child: InsigniaEnVivoTv(grande: true)),
              if (_numero.isNotEmpty)
                Positioned(
                  top: MargenTv.arriba,
                  right: MargenTv.derecha,
                  child: _NumeroEscrito(numero: _numero, canal: escrito?.nombre),
                ),
              if (_controles && !_guia)
                Positioned(
                  left: MargenTv.derecha,
                  right: MargenTv.derecha,
                  bottom: MargenTv.abajo,
                  child: _PanelControles(
                    ayuda: '↑ ↓ cambiar de canal  ·  números: ir a un canal  ·  Atrás: ocultar',
                    fila: [
                      _BotonCuadrado(
                        icono: Icons.view_list_rounded,
                        etiqueta: 'Guía',
                        autofocus: true,
                        alOk: () => setState(() => _guia = true),
                      ),
                      const SizedBox(width: 20),
                      Container(
                        width: 84,
                        height: 62,
                        decoration: BoxDecoration(color: Tono.capa, borderRadius: BorderRadius.circular(Curva.grande)),
                        child: LogoCanalTv(canal: canal, tamanioIniciales: 22, relleno: const EdgeInsets.all(8)),
                      ),
                      const SizedBox(width: 18),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              canal.nombre,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: LetraTv.tarjeta.copyWith(fontSize: 24),
                            ),
                            const SizedBox(height: 2),
                            Text(
                              [if (numero.isNotEmpty) 'Canal $numero', if (categoria.isNotEmpty) categoria].join(' · '),
                              style: LetraTv.ayuda.copyWith(fontSize: 17, color: Tono.textoSuave),
                            ),
                          ],
                        ),
                      ),
                      _BotonCuadrado(
                        icono: favorito ? Icons.favorite_rounded : Icons.favorite_border_rounded,
                        color: favorito ? Tono.rubi : null,
                        etiqueta: favorito ? 'Quitar de favoritos' : 'Agregar a favoritos',
                        alOk: () => alternarFavoritoTv(context, clave),
                      ),
                      if (_control.fuentes.length > 1) ...[
                        const SizedBox(width: 18),
                        _BotonCuadrado(icono: Icons.settings_rounded, etiqueta: 'Fuente', alOk: _elegirFuente),
                      ],
                    ],
                  ),
                ),
              if (_guia) _GuiaEncima(lista: widget.lista, actual: canal, numeroDe: catalogo.numeroDe, alElegir: _ver),
            ],
          ),
        ),
      ),
    );
  }
}

/// El número que se está escribiendo, arriba a la derecha ("10_", y el canal si existe).
class _NumeroEscrito extends StatelessWidget {
  const _NumeroEscrito({required this.numero, this.canal});

  final String numero;
  final String? canal;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 30, vertical: 18),
      decoration: BoxDecoration(
        color: Tono.capaMinima.withValues(alpha: .9),
        borderRadius: BorderRadius.circular(Curva.panel),
        border: Border.all(color: Tono.bordeSuave.withValues(alpha: .5)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          Text(
            numero.padRight(3, '_'),
            style: const TextStyle(
              fontFamily: Letra.titulos,
              fontSize: 64,
              fontWeight: FontWeight.w800,
              letterSpacing: 6,
              color: Tono.dorado,
            ),
          ),
          if (canal != null) Text(canal!, style: LetraTv.cuerpo.copyWith(color: Tono.texto)),
        ],
      ),
    );
  }
}

/// La guía encima del video: la lista de canales a la izquierda, parada en el que se ve.
class _GuiaEncima extends StatelessWidget {
  const _GuiaEncima({required this.lista, required this.actual, required this.numeroDe, required this.alElegir});

  final List<Canal> lista;
  final Canal actual;
  final String Function(Canal) numeroDe;
  final ValueChanged<Canal> alElegir;

  static const _altoFila = 92.0;

  @override
  Widget build(BuildContext context) {
    final indice = lista.indexWhere((c) => c.id == actual.id).clamp(0, lista.length);
    return Positioned(
      left: 0,
      top: 0,
      bottom: 0,
      width: 720,
      child: DecoratedBox(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            colors: [Color(0xF20E0E12), Color(0xD90E0E12), Color(0x000E0E12)],
            stops: [0, .8, 1],
          ),
        ),
        child: Padding(
          padding: const EdgeInsets.fromLTRB(MargenTv.derecha, 120, 60, 0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('GUÍA DE CANALES', style: LetraTv.sobretitulo),
              const SizedBox(height: 14),
              Expanded(
                child: FocusTraversalGroup(
                  child: ListView.builder(
                    controller: ScrollController(initialScrollOffset: (indice - 2).clamp(0, 1 << 20) * _altoFila),
                    clipBehavior: Clip.none,
                    itemExtent: _altoFila,
                    padding: const EdgeInsets.only(bottom: 60, right: 14),
                    itemCount: lista.length,
                    itemBuilder: (context, i) {
                      final canal = lista[i];
                      return Padding(
                        padding: const EdgeInsets.symmetric(vertical: 7),
                        child: FilaCanalTv(
                          canal: canal,
                          numero: numeroDe(canal),
                          autofocus: i == indice,
                          enReproduccion: canal.id == actual.id,
                          alOk: () => alElegir(canal),
                        ),
                      );
                    },
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Una fila de la guía: número dorado, logo o iniciales, nombre y categoría.
class FilaCanalTv extends StatelessWidget {
  const FilaCanalTv({
    super.key,
    required this.canal,
    required this.numero,
    required this.alOk,
    this.alOkLargo,
    this.autofocus = false,
    this.enReproduccion = false,
    this.favorito = false,
    this.ayuda,
  });

  final Canal canal;
  final String numero;
  final VoidCallback alOk;
  final VoidCallback? alOkLargo;
  final bool autofocus;
  final bool enReproduccion;
  final bool favorito;

  /// A la derecha ("OK · Pantalla completa").
  final String? ayuda;

  @override
  Widget build(BuildContext context) {
    final categoria = categoriaLegible(canal.categoria);
    return Enfocable(
      alOk: alOk,
      alOkLargo: alOkLargo,
      autofocus: autofocus,
      curva: Curva.boton,
      escala: 1.02,
      etiqueta: 'Canal $numero, ${canal.nombre}',
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 18),
        decoration: BoxDecoration(
          color: enReproduccion ? Tono.celeste.withValues(alpha: .1) : Tono.capa.withValues(alpha: .7),
          borderRadius: BorderRadius.circular(Curva.boton),
        ),
        child: Row(
          children: [
            SizedBox(
              width: 74,
              child: Text(
                numero,
                style: const TextStyle(
                  fontFamily: Letra.texto,
                  fontSize: 20,
                  fontWeight: FontWeight.w800,
                  color: Tono.dorado,
                ),
              ),
            ),
            Container(
              width: 72,
              height: 52,
              decoration: BoxDecoration(color: Tono.capaAlta, borderRadius: BorderRadius.circular(Curva.medio)),
              child: LogoCanalTv(canal: canal, tamanioIniciales: 19, relleno: const EdgeInsets.all(6)),
            ),
            const SizedBox(width: 20),
            Expanded(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Flexible(
                        child: Text(
                          canal.nombre,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(
                            fontFamily: Letra.texto,
                            fontSize: 20,
                            fontWeight: FontWeight.w700,
                            color: Tono.texto,
                          ),
                        ),
                      ),
                      if (favorito) ...[
                        const SizedBox(width: 10),
                        const Icon(Icons.favorite_rounded, size: 18, color: Tono.rubi),
                      ],
                      if (enReproduccion) ...[
                        const SizedBox(width: 12),
                        const PuntoEnVivo(tamanio: 9, color: Tono.rubi),
                      ],
                    ],
                  ),
                  if (categoria.isNotEmpty) Text(categoria, style: LetraTv.ayuda.copyWith(fontSize: 15)),
                ],
              ),
            ),
            if (ayuda != null) Text(ayuda!, style: LetraTv.ayuda.copyWith(fontSize: 15)),
          ],
        ),
      ),
    );
  }
}

// ── Películas y capítulos ──────────────────────────────────────────

class ReproductorVodTv extends StatefulWidget {
  const ReproductorVodTv({super.key, required this.canal, this.serie, this.episodio, this.desde});

  final Canal canal;
  final Serie? serie;
  final Episodio? episodio;
  final Duration? desde;

  @override
  State<ReproductorVodTv> createState() => _ReproductorVodTvState();
}

class _ReproductorVodTvState extends State<ReproductorVodTv> {
  static const _salto = Duration(seconds: 10);

  late final ControlSenal _control = ControlSenal(SesionScope.leer(context).api)..addListener(_alCambiar);
  late final Biblioteca _biblioteca = DatosScope.of(context).biblioteca;
  final _raiz = FocusNode(debugLabel: 'reproductor');
  late Canal _canal = widget.canal;
  late Episodio? _episodio = widget.episodio;
  bool _controles = true;
  bool _siguienteLanzado = false;
  Timer? _ocultar;
  Timer? _guardar;

  @override
  void initState() {
    super.initState();
    WakelockPlus.enable().catchError((Object _) {});
    _control.abrir(_canal, desde: widget.desde);
    _guardar = Timer.periodic(const Duration(seconds: 5), (_) => _guardarProgreso());
    _mostrarControles();
  }

  @override
  void dispose() {
    _guardarProgreso();
    _ocultar?.cancel();
    _guardar?.cancel();
    _control.dispose();
    _raiz.dispose();
    WakelockPlus.disable().catchError((Object _) {});
    super.dispose();
  }

  VideoPlayerValue? get _valor => _control.video?.value;

  void _alCambiar() {
    if (!mounted) return;
    final valor = _valor;
    // Terminó: el capítulo siguiente sigue solo
    if (valor != null &&
        valor.isInitialized &&
        valor.duration > Duration.zero &&
        valor.position >= valor.duration - const Duration(milliseconds: 800) &&
        !_siguienteLanzado) {
      _siguienteLanzado = true;
      _guardarProgreso();
      if (_siguiente != null) _pasarA(_siguiente!);
    }
    setState(() {});
  }

  void _guardarProgreso() {
    final valor = _valor;
    if (valor == null || !valor.isInitialized || valor.duration == Duration.zero) return;
    _biblioteca.guardarProgreso(_canal.id, valor.position, valor.duration);
  }

  Episodio? get _siguiente {
    final serie = widget.serie;
    final actual = _episodio;
    if (serie == null || actual == null) return null;
    final episodios = serie.episodios;
    final indice = episodios.indexOf(actual);
    return indice >= 0 && indice + 1 < episodios.length ? episodios[indice + 1] : null;
  }

  void _pasarA(Episodio episodio) {
    _guardarProgreso();
    setState(() {
      _episodio = episodio;
      _canal = episodio.canal;
      _siguienteLanzado = false;
    });
    final progreso = _biblioteca.progresoDe(episodio.canal.id);
    _control.abrir(episodio.canal, desde: progreso == null || progreso.terminado ? null : progreso.posicion);
    _mostrarControles();
  }

  void _mostrarControles() {
    setState(() => _controles = true);
    _reiniciarEspera();
  }

  void _reiniciarEspera() {
    _ocultar?.cancel();
    _ocultar = Timer(_esperaControles, () {
      if (!mounted || !(_valor?.isPlaying ?? false)) return;
      setState(() => _controles = false);
      _raiz.requestFocus();
    });
  }

  void _saltar(Duration cuanto) {
    _control.saltar(cuanto);
    _mostrarControles();
  }

  KeyEventResult _tecla(FocusNode _, KeyEvent evento) {
    if (evento is KeyUpEvent) return KeyEventResult.ignored;
    final tecla = evento.logicalKey;
    // Las teclas de reproducción del control funcionan siempre
    if (tecla == LogicalKeyboardKey.mediaPlayPause ||
        tecla == LogicalKeyboardKey.mediaPlay ||
        tecla == LogicalKeyboardKey.mediaPause) {
      _control.alternarPausa();
      _mostrarControles();
      return KeyEventResult.handled;
    }
    if (tecla == LogicalKeyboardKey.mediaFastForward) {
      _saltar(_salto * 3);
      return KeyEventResult.handled;
    }
    if (tecla == LogicalKeyboardKey.mediaRewind) {
      _saltar(-_salto * 3);
      return KeyEventResult.handled;
    }
    if (_controles) {
      _reiniciarEspera();
      return KeyEventResult.ignored;
    }
    if (tecla == LogicalKeyboardKey.arrowLeft) {
      _saltar(-_salto);
      return KeyEventResult.handled;
    }
    if (tecla == LogicalKeyboardKey.arrowRight) {
      _saltar(_salto);
      return KeyEventResult.handled;
    }
    if (teclasOk.contains(tecla) || tecla == LogicalKeyboardKey.arrowUp || tecla == LogicalKeyboardKey.arrowDown) {
      _mostrarControles();
      return KeyEventResult.handled;
    }
    return KeyEventResult.ignored;
  }

  Future<void> _elegirFuente() async {
    final elegida = await elegirFuenteTv(context, _control);
    if (elegida != null) _control.usarFuente(elegida);
  }

  @override
  Widget build(BuildContext context) {
    final valor = _valor;
    final serie = widget.serie;
    final episodio = _episodio;
    final clave = serie?.clave ?? Biblioteca.claveDe(_canal);
    final favorito = _biblioteca.estaEnMiLista(clave);
    final titulo = serie?.nombre ?? sinAnio(_canal.nombre);
    final subtitulo = episodio == null
        ? 'Película'
        : 'Temporada ${episodio.temporada} · Episodio ${episodio.numero}'
              '${episodio.titulo.isEmpty ? '' : ' · ${episodio.titulo}'}';
    final duracion = valor?.duration ?? Duration.zero;
    final posicion = valor?.position ?? Duration.zero;
    final siguiente = _siguiente;

    return PopScope(
      canPop: !_controles || !(valor?.isPlaying ?? false),
      onPopInvokedWithResult: (salio, _) {
        if (salio) return;
        setState(() => _controles = false);
        _raiz.requestFocus();
      },
      child: Scaffold(
        backgroundColor: Colors.black,
        body: Focus(
          // Sin autofocus: al abrir, el foco va al primer botón de los controles;
          // cuando se esconden, lo toma la pantalla entera (_raiz)
          focusNode: _raiz,
          onKeyEvent: _tecla,
          child: Stack(
            fit: StackFit.expand,
            children: [
              _Video(control: _control),
              _EstadoSenal(control: _control, alReintentar: _control.reintentar),
              if (_controles)
                Positioned(
                  top: MargenTv.arriba,
                  left: MargenTv.derecha,
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 9),
                    decoration: BoxDecoration(
                      color: Tono.capaAlta.withValues(alpha: .85),
                      borderRadius: BorderRadius.circular(99),
                      border: Border.all(color: Tono.bordeSuave.withValues(alpha: .6)),
                    ),
                    child: Text(
                      episodio == null ? 'PELÍCULA' : 'T${episodio.temporada} · E${episodio.numero}',
                      style: const TextStyle(
                        fontFamily: Letra.texto,
                        fontSize: 16,
                        fontWeight: FontWeight.w800,
                        letterSpacing: .6,
                        color: Tono.texto,
                      ),
                    ),
                  ),
                ),
              if (_controles)
                Positioned(
                  left: MargenTv.derecha,
                  right: MargenTv.derecha,
                  bottom: MargenTv.abajo,
                  child: _PanelControles(
                    fila: [
                      _BotonCuadrado(
                        icono: (valor?.isPlaying ?? false) ? Icons.pause_rounded : Icons.play_arrow_rounded,
                        etiqueta: (valor?.isPlaying ?? false) ? 'Pausa' : 'Seguir',
                        autofocus: true,
                        alOk: () {
                          _control.alternarPausa();
                          _reiniciarEspera();
                        },
                      ),
                      const SizedBox(width: 20),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              titulo,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: LetraTv.tarjeta.copyWith(fontSize: 24),
                            ),
                            Text(
                              subtitulo,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: LetraTv.ayuda.copyWith(fontSize: 17, color: Tono.textoSuave),
                            ),
                          ],
                        ),
                      ),
                      if (siguiente != null) ...[
                        BotonTv(
                          texto: 'Siguiente episodio',
                          icono: Icons.skip_next_rounded,
                          alto: 62,
                          alOk: () => _pasarA(siguiente),
                        ),
                        const SizedBox(width: 18),
                      ],
                      _BotonCuadrado(
                        icono: favorito ? Icons.favorite_rounded : Icons.favorite_border_rounded,
                        color: favorito ? Tono.rubi : null,
                        etiqueta: favorito ? 'Quitar de favoritos' : 'Agregar a favoritos',
                        alOk: () => alternarFavoritoTv(context, clave),
                      ),
                      if (_control.fuentes.length > 1) ...[
                        const SizedBox(width: 18),
                        _BotonCuadrado(icono: Icons.settings_rounded, etiqueta: 'Fuente', alOk: _elegirFuente),
                      ],
                    ],
                    debajo: _LineaDeTiempo(
                      posicion: posicion,
                      duracion: duracion,
                      alSaltar: (cuanto) {
                        _control.saltar(cuanto);
                        _reiniciarEspera();
                      },
                    ),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}

/// La línea de tiempo: con el foco, Izquierda/Derecha mueven ±10 s.
class _LineaDeTiempo extends StatelessWidget {
  const _LineaDeTiempo({required this.posicion, required this.duracion, required this.alSaltar});

  final Duration posicion;
  final Duration duracion;
  final ValueChanged<Duration> alSaltar;

  @override
  Widget build(BuildContext context) {
    final fraccion = duracion.inMilliseconds == 0
        ? 0.0
        : (posicion.inMilliseconds / duracion.inMilliseconds).clamp(0.0, 1.0);
    return Column(
      children: [
        Enfocable(
          curva: 99,
          escala: 1.0,
          etiqueta: 'Línea de tiempo: ${reloj(posicion)} de ${reloj(duracion)}',
          alTecla: (evento) {
            if (evento is KeyUpEvent) return KeyEventResult.ignored;
            if (evento.logicalKey == LogicalKeyboardKey.arrowLeft) {
              alSaltar(const Duration(seconds: -10));
              return KeyEventResult.handled;
            }
            if (evento.logicalKey == LogicalKeyboardKey.arrowRight) {
              alSaltar(const Duration(seconds: 10));
              return KeyEventResult.handled;
            }
            return KeyEventResult.ignored;
          },
          child: SizedBox(
            height: 26,
            child: LayoutBuilder(
              builder: (context, limites) => Stack(
                alignment: Alignment.centerLeft,
                children: [
                  Container(
                    height: 8,
                    decoration: BoxDecoration(color: Tono.capaMaxima, borderRadius: BorderRadius.circular(99)),
                  ),
                  Container(
                    height: 8,
                    width: limites.maxWidth * fraccion,
                    decoration: BoxDecoration(
                      color: Tono.celeste,
                      borderRadius: BorderRadius.circular(99),
                      boxShadow: brilloCeleste(desenfoque: 10, opacidad: .6),
                    ),
                  ),
                  Positioned(
                    left: (limites.maxWidth * fraccion - 11).clamp(0, limites.maxWidth - 22),
                    child: Container(
                      width: 22,
                      height: 22,
                      decoration: BoxDecoration(
                        color: Tono.celesteClaro,
                        shape: BoxShape.circle,
                        boxShadow: brilloCeleste(desenfoque: 14, opacidad: .8),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
        const SizedBox(height: 10),
        Row(
          children: [
            Text(reloj(posicion), style: _estiloTiempo),
            const Spacer(),
            Text(duracion == Duration.zero ? '--:--' : reloj(duracion), style: _estiloTiempo),
          ],
        ),
      ],
    );
  }

  static const _estiloTiempo = TextStyle(
    fontFamily: Letra.texto,
    fontSize: 15,
    fontWeight: FontWeight.w700,
    color: Tono.texto,
    fontFeatures: [FontFeature.tabularFigures()],
  );
}

// ── Piezas compartidas ─────────────────────────────────────────────

class _Video extends StatelessWidget {
  const _Video({required this.control});

  final ControlSenal control;

  @override
  Widget build(BuildContext context) {
    final video = control.video;
    if (video == null || !video.value.isInitialized) return const SizedBox.expand();
    return Center(
      child: AspectRatio(
        aspectRatio: video.value.aspectRatio == 0 ? 16 / 9 : video.value.aspectRatio,
        child: VideoPlayer(video),
      ),
    );
  }
}

/// Cargando, "probando otra señal…" o el error con "Probar de nuevo" (tv-19).
class _EstadoSenal extends StatelessWidget {
  const _EstadoSenal({required this.control, required this.alReintentar, this.alGuia});

  final ControlSenal control;
  final VoidCallback alReintentar;
  final VoidCallback? alGuia;

  @override
  Widget build(BuildContext context) {
    final error = control.error;
    if (error != null) {
      return Center(
        child: Container(
          width: 820,
          padding: const EdgeInsets.all(48),
          decoration: BoxDecoration(
            color: Tono.capaBaja.withValues(alpha: .95),
            borderRadius: BorderRadius.circular(Curva.portada),
            border: Border.all(color: Tono.rubi.withValues(alpha: .5)),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.signal_wifi_connected_no_internet_4_rounded, size: 56, color: Tono.rubiClaro),
              const SizedBox(height: 18),
              const Text('Esto no está disponible ahora', textAlign: TextAlign.center, style: LetraTv.pantalla),
              const SizedBox(height: 10),
              Text(error, textAlign: TextAlign.center, style: LetraTv.cuerpo),
              const SizedBox(height: 30),
              FocusTraversalGroup(
                child: Wrap(
                  spacing: 18,
                  children: [
                    BotonTv(
                      texto: 'Probar de nuevo',
                      icono: Icons.refresh_rounded,
                      principal: true,
                      autofocus: true,
                      alOk: alReintentar,
                    ),
                    if (alGuia != null) BotonTv(texto: 'Ver la guía', icono: Icons.view_list_rounded, alOk: alGuia),
                  ],
                ),
              ),
            ],
          ),
        ),
      );
    }
    if (!control.cargando) return const SizedBox.shrink();
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const SizedBox(width: 64, height: 64, child: CircularProgressIndicator(strokeWidth: 5, color: Tono.celeste)),
          const SizedBox(height: 22),
          Text(
            control.fuente > 0 ? 'Esta señal no responde. Probando otra señal…' : 'Conectando…',
            style: LetraTv.cuerpo.copyWith(color: Tono.texto),
          ),
        ],
      ),
    );
  }
}

/// El panel de abajo con los controles (vidrio oscuro) y una ayuda de las teclas.
class _PanelControles extends StatelessWidget {
  const _PanelControles({required this.fila, this.debajo, this.ayuda});

  final List<Widget> fila;
  final Widget? debajo;
  final String? ayuda;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(32, 26, 32, 22),
      decoration: BoxDecoration(
        color: Tono.capaMinima.withValues(alpha: .9),
        borderRadius: BorderRadius.circular(Curva.panel),
        border: Border.all(color: Tono.bordeSuave.withValues(alpha: .45)),
        boxShadow: const [BoxShadow(color: Colors.black54, blurRadius: 40)],
      ),
      child: FocusTraversalGroup(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Row(children: fila),
            if (debajo != null) ...[const SizedBox(height: 22), debajo!],
            if (ayuda != null) ...[
              const SizedBox(height: 16),
              Text(ayuda!, style: LetraTv.ayuda.copyWith(fontSize: 15)),
            ],
          ],
        ),
      ),
    );
  }
}

class _BotonCuadrado extends StatelessWidget {
  const _BotonCuadrado({
    required this.icono,
    required this.etiqueta,
    required this.alOk,
    this.autofocus = false,
    this.color,
  });

  final IconData icono;
  final String etiqueta;
  final VoidCallback alOk;
  final bool autofocus;
  final Color? color;

  @override
  Widget build(BuildContext context) {
    return Tooltip(
      message: etiqueta,
      child: Enfocable(
        alOk: alOk,
        autofocus: autofocus,
        curva: Curva.boton,
        escala: 1.08,
        etiqueta: etiqueta,
        child: Container(
          width: 62,
          height: 62,
          decoration: BoxDecoration(
            color: Tono.capaAlta,
            borderRadius: BorderRadius.circular(Curva.boton),
            border: Border.all(color: Tono.bordeSuave.withValues(alpha: .6)),
          ),
          child: Icon(icono, size: 30, color: color ?? Tono.texto),
        ),
      ),
    );
  }
}

/// Elegir otra fuente de la señal (si el canal tiene varias).
Future<int?> elegirFuenteTv(BuildContext context, ControlSenal control) {
  return showDialog<int>(
    context: context,
    builder: (contexto) => DialogoTv(
      icono: Icons.settings_input_antenna_rounded,
      titulo: 'Fuente de la señal',
      texto: 'Si se corta o se ve mal, probá con otra.',
      botones: [
        for (final (i, _) in control.fuentes.indexed)
          BotonTv(
            texto: 'Fuente ${i + 1}${i == control.fuente ? ' (actual)' : ''}',
            principal: i == control.fuente,
            autofocus: i == control.fuente,
            alOk: () => Navigator.pop(contexto, i),
          ),
      ],
    ),
  );
}
