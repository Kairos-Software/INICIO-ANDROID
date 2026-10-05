/// La app en la TV (diseno_kairos_tv/DESIGN.md -> "Menú lateral TV"): el menú
/// de la izquierda y las ocho secciones (Inicio, En vivo, Guía, Películas,
/// Series, Buscar, Favoritos y Mi cuenta).
///
/// El menú mide 88 px con solo íconos; al entrar en él (Izquierda desde el
/// contenido) se abre a 292 px con los nombres. OK abre la sección; Derecha
/// vuelve al contenido. "Atrás" en una sección vuelve a Inicio, y en Inicio
/// pregunta si salir.
///
/// Acá se crean el catálogo y la biblioteca, igual que en el celular
/// (movil/estructura.dart): se pide el catálogo al abrir, al volver a la app
/// y cada 15 minutos.
library;

import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../api/modelos.dart';
import '../marca.dart';
import '../movil/datos.dart';
import '../movil/estilo.dart';
import '../sesion.dart';
import '../utiles.dart';
import 'buscar.dart';
import 'cuenta.dart';
import 'en_vivo.dart';
import 'favoritos.dart';
import 'foco.dart';
import 'grilla.dart';
import 'guia.dart';
import 'inicio.dart';
import 'reproductor.dart';

enum SeccionTv { inicio, enVivo, guia, peliculas, series, buscar, favoritos, cuenta }

/// Para cambiar de sección desde cualquier pantalla (ej: "Abrir guía" en Inicio).
class NavegacionTv extends InheritedWidget {
  const NavegacionTv({super.key, required this.irA, required super.child});

  final void Function(SeccionTv seccion) irA;

  static NavegacionTv of(BuildContext context) => context.dependOnInheritedWidgetOfExactType<NavegacionTv>()!;

  @override
  bool updateShouldNotify(NavegacionTv oldWidget) => false;
}

class PantallaTv extends StatefulWidget {
  const PantallaTv({super.key, this.catalogo, this.biblioteca, this.seccionInicial = SeccionTv.inicio});

  /// Solo para las pruebas: un catálogo y una biblioteca ya armados.
  final Catalogo? catalogo;
  final Biblioteca? biblioteca;
  final SeccionTv seccionInicial;

  @override
  State<PantallaTv> createState() => _PantallaTvState();
}

class _PantallaTvState extends State<PantallaTv> {
  static const _cadaCuanto = Duration(minutes: 15);

  late final Catalogo _catalogo = widget.catalogo ?? Catalogo(SesionScope.leer(context).api);
  late final Biblioteca _biblioteca = widget.biblioteca ?? Biblioteca();
  late SeccionTv _seccion = widget.seccionInicial;
  final _contenido = FocusScopeNode(debugLabel: 'contenido');
  bool _menuAbierto = false;
  AppLifecycleListener? _ciclo;
  Timer? _refresco;

  @override
  void initState() {
    super.initState();
    if (widget.biblioteca == null) _biblioteca.cargar();
    _catalogo.addListener(_alCargarPorPrimeraVez);
    if (widget.catalogo != null) return;
    WidgetsBinding.instance.addPostFrameCallback((_) => _catalogo.cargar());
    _ciclo = AppLifecycleListener(onResume: _catalogo.cargar);
    _refresco = Timer.periodic(_cadaCuanto, (_) => _catalogo.cargar());
  }

  @override
  void dispose() {
    _catalogo.removeListener(_alCargarPorPrimeraVez);
    _ciclo?.dispose();
    _refresco?.cancel();
    _contenido.dispose();
    if (widget.catalogo == null) _catalogo.dispose();
    if (widget.biblioteca == null) _biblioteca.dispose();
    super.dispose();
  }

  /// "Volver al último canal al abrir" (Mi cuenta): cuenta 3 segundos (se puede cancelar) y lo pone.
  void _alCargarPorPrimeraVez() {
    if (!_catalogo.cargado) return;
    _catalogo.removeListener(_alCargarPorPrimeraVez);
    final ultimo = _biblioteca.ultimoCanal == null ? null : _catalogo.canalPorId(_biblioteca.ultimoCanal!);
    if (!_biblioteca.volverAlUltimo || ultimo == null) return;
    WidgetsBinding.instance.addPostFrameCallback((_) async {
      if (!mounted) return;
      final seguir = await showDialog<bool>(
        context: context,
        builder: (_) => CuentaRegresivaTv(canal: ultimo),
      );
      if (seguir == true && mounted) verCanalTv(_contexto, ultimo);
    });
  }

  /// Un contexto debajo de DatosScope (para abrir pantallas con el catálogo).
  BuildContext get _contexto => _claveContenido.currentContext ?? context;
  final _claveContenido = GlobalKey();

  void _irA(SeccionTv seccion) {
    setState(() {
      _seccion = seccion;
      _menuAbierto = false;
    });
    // El foco pasa al contenido de la sección nueva (a su "foco inicial")
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) _contenido.requestFocus();
    });
  }

  Future<void> _atras() async {
    if (_seccion != SeccionTv.inicio) return _irA(SeccionTv.inicio);
    final salir = await showDialog<bool>(context: context, builder: (_) => const _ConfirmarSalida());
    if (salir == true) await SystemNavigator.pop();
  }

  Widget _seccionActual() {
    return switch (_seccion) {
      SeccionTv.inicio => const InicioTv(),
      SeccionTv.enVivo => const EnVivoTv(),
      SeccionTv.guia => const GuiaTv(),
      SeccionTv.peliculas => const GrillaTv(contenido: 'pelicula', key: ValueKey('peliculas')),
      SeccionTv.series => const GrillaTv(contenido: 'serie', key: ValueKey('series')),
      SeccionTv.buscar => const BuscarTv(),
      SeccionTv.favoritos => const FavoritosTv(),
      SeccionTv.cuenta => const CuentaTv(),
    };
  }

  @override
  Widget build(BuildContext context) {
    return Theme(
      data: temaMovil(),
      child: DatosScope(
        catalogo: _catalogo,
        biblioteca: _biblioteca,
        child: NavegacionTv(
          irA: _irA,
          child: PopScope(
            canPop: false,
            onPopInvokedWithResult: (salio, _) {
              if (!salio) _atras();
            },
            child: Scaffold(
              backgroundColor: Tono.fondo,
              body: Stack(
                children: [
                  Positioned.fill(
                    key: _claveContenido,
                    child: FocusScope(
                      node: _contenido,
                      child: ListenableBuilder(
                        listenable: _catalogo,
                        builder: (context, _) {
                          if (!_catalogo.cargado) return _Cargando(catalogo: _catalogo);
                          return KeyedSubtree(key: ValueKey(_seccion), child: _seccionActual());
                        },
                      ),
                    ),
                  ),
                  // Al abrirse, el menú oscurece el contenido
                  IgnorePointer(
                    child: AnimatedOpacity(
                      opacity: _menuAbierto ? 1 : 0,
                      duration: const Duration(milliseconds: 160),
                      child: const DecoratedBox(
                        decoration: BoxDecoration(
                          gradient: LinearGradient(colors: [Color(0xE6131317), Color(0x00131317)], stops: [.2, .6]),
                        ),
                        child: SizedBox.expand(),
                      ),
                    ),
                  ),
                  Positioned(
                    left: 32,
                    top: 54,
                    bottom: 54,
                    child: Focus(
                      canRequestFocus: false,
                      skipTraversal: true,
                      onFocusChange: (dentro) => setState(() => _menuAbierto = dentro),
                      child: _Menu(seccion: _seccion, abierto: _menuAbierto, alElegir: _irA),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _Menu extends StatelessWidget {
  const _Menu({required this.seccion, required this.abierto, required this.alElegir});

  final SeccionTv seccion;
  final bool abierto;
  final ValueChanged<SeccionTv> alElegir;

  static const _opciones = [
    (SeccionTv.inicio, Icons.home_rounded, 'Inicio'),
    (SeccionTv.enVivo, Icons.live_tv_rounded, 'En vivo'),
    (SeccionTv.guia, Icons.view_list_rounded, 'Guía'),
    (SeccionTv.peliculas, Icons.movie_rounded, 'Películas'),
    (SeccionTv.series, Icons.video_library_rounded, 'Series'),
    (SeccionTv.buscar, Icons.search_rounded, 'Buscar'),
    (SeccionTv.favoritos, Icons.favorite_rounded, 'Favoritos'),
  ];

  @override
  Widget build(BuildContext context) {
    Widget opcion(SeccionTv valor, IconData icono, String texto) {
      final activa = valor == seccion;
      return Padding(
        padding: const EdgeInsets.symmetric(vertical: 5),
        child: Enfocable(
          alOk: () => alElegir(valor),
          curva: Curva.boton,
          escala: 1.0,
          etiqueta: texto,
          child: Container(
            height: 60,
            padding: const EdgeInsets.symmetric(horizontal: 18),
            decoration: BoxDecoration(
              color: activa ? Tono.celeste.withValues(alpha: .12) : Colors.transparent,
              borderRadius: BorderRadius.circular(Curva.boton),
            ),
            child: Row(
              children: [
                Icon(icono, size: 26, color: activa ? Tono.celeste : Tono.textoSuave),
                if (abierto) ...[
                  const SizedBox(width: 18),
                  Expanded(
                    child: Text(
                      texto,
                      maxLines: 1,
                      overflow: TextOverflow.clip,
                      style: TextStyle(
                        fontFamily: Letra.texto,
                        fontSize: 19,
                        fontWeight: FontWeight.w700,
                        color: activa ? Tono.celesteClaro : Tono.texto,
                      ),
                    ),
                  ),
                ],
              ],
            ),
          ),
        ),
      );
    }

    return AnimatedContainer(
      duration: const Duration(milliseconds: 160),
      curve: Curves.easeOut,
      width: abierto ? 292 : 88,
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 24),
      decoration: BoxDecoration(
        color: Tono.capaMinima.withValues(alpha: .92),
        borderRadius: BorderRadius.circular(Curva.panel + 4),
        border: Border.all(color: Tono.bordeSuave.withValues(alpha: .45)),
        boxShadow: abierto ? const [BoxShadow(color: Colors.black54, blurRadius: 40)] : const [],
      ),
      child: FocusTraversalGroup(
        policy: OrderedTraversalPolicy(),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Align(
              alignment: abierto ? Alignment.centerLeft : Alignment.center,
              child: Padding(
                padding: EdgeInsets.only(left: abierto ? 12 : 0, bottom: 34),
                child: abierto ? const LogoKairos(tamanio: 40) : const SimboloKairos(tamanio: 42),
              ),
            ),
            for (final (valor, icono, texto) in _opciones) opcion(valor, icono, texto),
            const Spacer(),
            opcion(SeccionTv.cuenta, Icons.account_circle_rounded, 'Mi cuenta'),
          ],
        ),
      ),
    );
  }
}

/// Mientras llega el catálogo (o si no llegó).
class _Cargando extends StatelessWidget {
  const _Cargando({required this.catalogo});

  final Catalogo catalogo;

  @override
  Widget build(BuildContext context) {
    final error = catalogo.error;
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const SimboloKairos(tamanio: 110),
          const SizedBox(height: 32),
          if (error == null) ...[
            const SizedBox(
              width: 260,
              child: LinearProgressIndicator(minHeight: 4, color: Tono.celeste, backgroundColor: Tono.capaMaxima),
            ),
            const SizedBox(height: 16),
            const Text('Preparando tu contenido…', style: LetraTv.cuerpo),
          ] else ...[
            Text(textoDeError(error), textAlign: TextAlign.center, style: LetraTv.cuerpo),
            const SizedBox(height: 24),
            BotonTv(
              texto: 'Reintentar',
              icono: Icons.refresh_rounded,
              principal: true,
              autofocus: true,
              alOk: catalogo.cargar,
            ),
          ],
        ],
      ),
    );
  }
}

/// "¿Querés salir de Kairos TV?" (tv-20): el foco arranca en "Seguir mirando".
class _ConfirmarSalida extends StatelessWidget {
  const _ConfirmarSalida();

  @override
  Widget build(BuildContext context) {
    return DialogoTv(
      icono: Icons.logout_rounded,
      titulo: '¿Querés salir de Kairos TV?',
      texto: 'Tu sesión queda abierta: la próxima vez entrás directo.',
      botones: [
        BotonTv(texto: 'Seguir mirando', principal: true, autofocus: true, alOk: () => Navigator.pop(context, false)),
        BotonTv(texto: 'Salir', alOk: () => Navigator.pop(context, true)),
      ],
    );
  }
}

/// Un cartel de la TV: ícono, título, texto y botones en fila.
class DialogoTv extends StatelessWidget {
  const DialogoTv({super.key, required this.titulo, required this.botones, this.texto, this.icono, this.hijo});

  final String titulo;
  final String? texto;
  final IconData? icono;
  final List<Widget> botones;
  final Widget? hijo;

  @override
  Widget build(BuildContext context) {
    return Dialog(
      backgroundColor: Tono.capaBaja,
      insetPadding: const EdgeInsets.all(80),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(Curva.portada),
        side: BorderSide(color: Tono.bordeSuave.withValues(alpha: .5)),
      ),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 760),
        child: Padding(
          padding: const EdgeInsets.all(48),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              if (icono != null) ...[Icon(icono, size: 56, color: Tono.celeste), const SizedBox(height: 20)],
              Text(titulo, textAlign: TextAlign.center, style: LetraTv.pantalla),
              if (texto != null) ...[
                const SizedBox(height: 12),
                Text(texto!, textAlign: TextAlign.center, style: LetraTv.cuerpo),
              ],
              ?hijo,
              const SizedBox(height: 34),
              FocusTraversalGroup(
                child: Wrap(spacing: 18, runSpacing: 14, alignment: WrapAlignment.center, children: botones),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// "Volviendo a (canal) en 3…": cancelable (Mi cuenta -> "Volver al último canal al abrir").
class CuentaRegresivaTv extends StatefulWidget {
  const CuentaRegresivaTv({super.key, required this.canal});

  final Canal canal;

  @override
  State<CuentaRegresivaTv> createState() => _CuentaRegresivaTvState();
}

class _CuentaRegresivaTvState extends State<CuentaRegresivaTv> {
  int _faltan = 3;
  Timer? _reloj;

  @override
  void initState() {
    super.initState();
    _reloj = Timer.periodic(const Duration(seconds: 1), (_) {
      if (_faltan <= 1) {
        _reloj?.cancel();
        Navigator.pop(context, true);
      } else {
        setState(() => _faltan--);
      }
    });
  }

  @override
  void dispose() {
    _reloj?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return DialogoTv(
      icono: Icons.restore_rounded,
      titulo: 'Volviendo a ${widget.canal.nombre}',
      texto: 'En $_faltan…',
      botones: [
        BotonTv(texto: 'Verlo ahora', principal: true, alOk: () => Navigator.pop(context, true)),
        BotonTv(texto: 'Cancelar', autofocus: true, alOk: () => Navigator.pop(context, false)),
      ],
    );
  }
}
