import 'dart:async';

import 'package:flutter/material.dart';

import '../api/modelos.dart';
import '../sesion.dart';
import '../tema.dart';
import '../utiles.dart';
import '../widgets/comunes.dart';
import 'cliente.dart';
import 'reproductor.dart';

/// "TV en vivo": los canales agrupados por categoría (GET /api/v1/canales/).
/// Para un cliente (entró con código) es la pantalla principal, con su "Mi cuenta".
class PantallaCanales extends StatefulWidget {
  const PantallaCanales({super.key, this.esCliente = false});

  final bool esCliente;

  @override
  State<PantallaCanales> createState() => _PantallaCanalesState();
}

class _PantallaCanalesState extends State<PantallaCanales> {
  /// Cada cuánto se vuelve a pedir la lista sola (una TV puede quedar
  /// prendida todo el día): así los cambios del panel llegan sin tocar nada.
  static const _cadaCuanto = Duration(minutes: 15);

  List<CategoriaCanales>? _categorias;
  Object? _error;
  bool _cargando = false;
  AppLifecycleListener? _ciclo;
  Timer? _refresco;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _cargar());
    // También al volver a la app (ej: se prendió la TV o se volvió del inicio)
    _ciclo = AppLifecycleListener(onResume: _cargar);
    _refresco = Timer.periodic(_cadaCuanto, (_) => _cargar());
  }

  @override
  void dispose() {
    _ciclo?.dispose();
    _refresco?.cancel();
    super.dispose();
  }

  Future<void> _cargar() async {
    if (_cargando) return;
    setState(() {
      _error = null;
      _cargando = true;
    });
    try {
      final datos = await SesionScope.leer(context).api.get('canales/') as Map<String, dynamic>;
      if (!mounted) return;
      setState(
        () => _categorias = [for (final c in datos['categorias'] as List) CategoriaCanales(c as Map<String, dynamic>)],
      );
    } catch (error) {
      if (mounted) setState(() => _error = error);
    } finally {
      if (mounted) setState(() => _cargando = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final categorias = _categorias;
    return Scaffold(
      appBar: AppBar(
        title: const Row(
          children: [
            Icon(Icons.live_tv_rounded, color: Colores.celeste),
            SizedBox(width: 10),
            Text('TV en vivo'),
            SizedBox(width: 10),
            _EnVivo(),
          ],
        ),
        actions: [
          IconButton(
            tooltip: 'Actualizar canales',
            onPressed: _cargando ? null : _cargar,
            icon: _cargando
                ? const SizedBox.square(dimension: 20, child: CircularProgressIndicator(strokeWidth: 2.2))
                : const Icon(Icons.refresh_rounded),
          ),
          if (widget.esCliente)
            IconButton(
              tooltip: 'Mi cuenta',
              icon: const Icon(Icons.account_circle_rounded),
              onPressed: () =>
                  Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => const PantallaCuentaCliente())),
            ),
        ],
      ),
      body: _error != null && categorias == null
          ? VistaError(mensaje: textoDeError(_error!), alReintentar: _cargar)
          : categorias == null
          ? const Center(child: CircularProgressIndicator())
          : categorias.isEmpty
          ? const VistaVacia(mensaje: 'Todavía no hay canales disponibles.', icono: Icons.tv_off_rounded)
          : LayoutBuilder(
              builder: (context, limites) {
                final todos = [for (final c in categorias) ...c.canales];
                // Una TV necesita conservar la grilla y el foco del control remoto.
                // En celulares y tablets usamos navegación paginada en dos direcciones.
                if (limites.maxWidth >= 1000) {
                  return _VistaCanalesTV(categorias: categorias, todos: todos, alActualizar: _cargar);
                }
                return _ExploradorCanales(categorias: categorias, todos: todos, cargando: _cargando);
              },
            ),
    );
  }
}

/// En celulares la pantalla funciona como una biblioteca de filas fijas:
/// vertical = avanza una categoría; horizontal = avanza por sus canales.
class _ExploradorCanales extends StatelessWidget {
  const _ExploradorCanales({required this.categorias, required this.todos, required this.cargando});

  final List<CategoriaCanales> categorias;
  final List<Canal> todos;
  final bool cargando;

  int _categoriasVisibles(BoxConstraints limites) {
    if (limites.maxHeight >= 620) return 3;
    if (limites.maxHeight >= 390) return 2;
    return 1;
  }

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, limites) {
        final visibles = _categoriasVisibles(limites).clamp(1, categorias.length);

        return Column(
          children: [
            AnimatedSize(
              duration: const Duration(milliseconds: 180),
              child: cargando ? const LinearProgressIndicator(minHeight: 2) : const SizedBox(height: 2),
            ),
            Expanded(
              child: _CategoriasEncajadas(
                key: ValueKey(visibles),
                categorias: categorias,
                todos: todos,
                visibles: visibles,
              ),
            ),
          ],
        );
      },
    );
  }
}

/// El alto del visor no cambia. `viewportFraction` decide cuántas categorías
/// entran al mismo tiempo y PageView encaja siempre de a una fila.
class _CategoriasEncajadas extends StatefulWidget {
  const _CategoriasEncajadas({super.key, required this.categorias, required this.todos, required this.visibles});

  final List<CategoriaCanales> categorias;
  final List<Canal> todos;
  final int visibles;

  @override
  State<_CategoriasEncajadas> createState() => _CategoriasEncajadasState();
}

class _CategoriasEncajadasState extends State<_CategoriasEncajadas> {
  late final PageController _control = PageController(viewportFraction: 1 / widget.visibles);

  @override
  void dispose() {
    _control.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return PageView.builder(
      controller: _control,
      scrollDirection: Axis.vertical,
      padEnds: false,
      pageSnapping: true,
      physics: const BouncingScrollPhysics(),
      itemCount: widget.categorias.length,
      itemBuilder: (context, indice) => Padding(
        padding: EdgeInsets.fromLTRB(14, indice == 0 ? 2 : 5, 14, indice == widget.categorias.length - 1 ? 14 : 5),
        child: _CarruselCategoria(
          key: ValueKey(widget.categorias[indice].nombre),
          categoria: widget.categorias[indice],
          todos: widget.todos,
          autofocus: indice == 0,
        ),
      ),
    );
  }
}

class _CarruselCategoria extends StatefulWidget {
  const _CarruselCategoria({super.key, required this.categoria, required this.todos, this.autofocus = false});

  final CategoriaCanales categoria;
  final List<Canal> todos;
  final bool autofocus;

  @override
  State<_CarruselCategoria> createState() => _CarruselCategoriaState();
}

class _CarruselCategoriaState extends State<_CarruselCategoria> with AutomaticKeepAliveClientMixin {
  PageController? _controlCanales;
  double? _fraccionCanal;

  @override
  bool get wantKeepAlive => true;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final ancho = MediaQuery.sizeOf(context).width;
    final fraccion = ancho >= 720
        ? .24
        : ancho >= 520
        ? .29
        : ancho >= 370
        ? .36
        : .46;
    if (_fraccionCanal != fraccion) {
      final pagina = _controlCanales?.hasClients == true ? _controlCanales!.page?.round() ?? 0 : 0;
      final ultimaPagina = widget.categoria.canales.isEmpty ? 0 : widget.categoria.canales.length - 1;
      _controlCanales?.dispose();
      _controlCanales = PageController(initialPage: pagina.clamp(0, ultimaPagina), viewportFraction: fraccion);
      _fraccionCanal = fraccion;
    }
  }

  @override
  void dispose() {
    _controlCanales?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    super.build(context);
    return Container(
      decoration: BoxDecoration(
        border: Border(bottom: BorderSide(color: Colores.borde.withValues(alpha: .7))),
      ),
      child: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(2, 5, 2, 5),
            child: Row(
              children: [
                const RayitaTitulo(),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    widget.categoria.nombre,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: estiloTitulo(15, peso: FontWeight.w600),
                  ),
                ),
              ],
            ),
          ),
          Expanded(
            child: PageView.builder(
              controller: _controlCanales,
              scrollDirection: Axis.horizontal,
              padEnds: false,
              pageSnapping: true,
              physics: const BouncingScrollPhysics(),
              itemCount: widget.categoria.canales.length,
              itemBuilder: (context, indice) => Padding(
                padding: const EdgeInsets.only(right: 9, bottom: 7),
                child: Align(
                  child: AspectRatio(
                    aspectRatio: .82,
                    child: _TarjetaCanal(
                      canal: widget.categoria.canales[indice],
                      todos: widget.todos,
                      autofocus: widget.autofocus && indice == 0,
                    ),
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/// En pantallas de TV se conserva la grilla completa para que el recorrido
/// con flechas y el foco del control remoto sigan siendo naturales.
class _VistaCanalesTV extends StatelessWidget {
  const _VistaCanalesTV({required this.categorias, required this.todos, required this.alActualizar});

  final List<CategoriaCanales> categorias;
  final List<Canal> todos;
  final Future<void> Function() alActualizar;

  @override
  Widget build(BuildContext context) {
    return RefreshIndicator(
      onRefresh: alActualizar,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(20, 0, 20, 24),
        children: [
          for (final (numeroCategoria, categoria) in categorias.indexed) ...[
            TituloSeccion(categoria.nombre),
            GridView.builder(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
                maxCrossAxisExtent: 140,
                mainAxisSpacing: 12,
                crossAxisSpacing: 12,
                childAspectRatio: 0.82,
              ),
              itemCount: categoria.canales.length,
              itemBuilder: (context, i) =>
                  _TarjetaCanal(canal: categoria.canales[i], todos: todos, autofocus: numeroCategoria == 0 && i == 0),
            ),
          ],
        ],
      ),
    );
  }
}

/// Un canal de la grilla. Con el control remoto de la TV, el que tiene el
/// foco se marca con un borde naranja (el foco del panel) y un poco más
/// grande; OK lo abre.
class _TarjetaCanal extends StatefulWidget {
  const _TarjetaCanal({required this.canal, required this.todos, this.autofocus = false});

  final Canal canal;

  /// Todos los canales en orden: para el zapping (arriba / abajo en el reproductor).
  final List<Canal> todos;
  final bool autofocus;

  @override
  State<_TarjetaCanal> createState() => _TarjetaCanalState();
}

class _TarjetaCanalState extends State<_TarjetaCanal> {
  bool _conFoco = false;

  @override
  Widget build(BuildContext context) {
    final canal = widget.canal;
    return AnimatedScale(
      scale: _conFoco ? 1.07 : 1,
      duration: const Duration(milliseconds: 150),
      child: Card(
        clipBehavior: Clip.antiAlias,
        color: _conFoco ? Colores.superficieAlta : Colores.superficie,
        shadowColor: Colores.naranja,
        elevation: _conFoco ? 10 : 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(Radios.medio),
          side: BorderSide(color: _conFoco ? Colores.naranja : Colores.borde, width: _conFoco ? 3 : 1),
        ),
        child: InkWell(
          autofocus: widget.autofocus,
          onFocusChange: (conFoco) => setState(() => _conFoco = conFoco),
          focusColor: Colors.transparent, // el foco ya se ve en el borde
          onTap: () => Navigator.push(
            context,
            MaterialPageRoute<void>(
              builder: (_) => PantallaReproductor(canal: canal, todos: widget.todos),
            ),
          ),
          child: Padding(
            padding: const EdgeInsets.all(10),
            child: Column(
              children: [
                Expanded(child: LogoCanal(canal: canal)),
                const SizedBox(height: 8),
                Text(
                  canal.nombre,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13, color: Colores.texto),
                ),
                if (canal.numero.isNotEmpty)
                  Text(
                    'Canal ${canal.numero}',
                    style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: Colores.textoSuave),
                  ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

/// El logo del canal sobre un fondo claro (los logos vienen pensados para fondo blanco).
/// Si no tiene logo, o no carga, muestra las iniciales.
class LogoCanal extends StatelessWidget {
  const LogoCanal({super.key, required this.canal});

  final Canal canal;

  @override
  Widget build(BuildContext context) {
    final iniciales = canal.nombre.split(' ').where((p) => p.isNotEmpty).take(2).map((p) => p[0]).join().toUpperCase();
    final sinLogo = Center(
      child: Text(
        iniciales,
        style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w800, color: Colores.fondo),
      ),
    );
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: const Color(0xFFF3F7FC), // el --papel del panel
        borderRadius: BorderRadius.circular(Radios.chico),
      ),
      child: canal.logo.isEmpty
          ? sinLogo
          : Image.network(canal.logo, fit: BoxFit.contain, errorBuilder: (_, _, _) => sinLogo),
    );
  }
}

/// El cartelito naranja "EN VIVO" al lado del título.
class _EnVivo extends StatelessWidget {
  const _EnVivo();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: Colores.naranja.withValues(alpha: 0.14),
        borderRadius: BorderRadius.circular(99),
        border: Border.all(color: Colores.naranja.withValues(alpha: 0.4)),
      ),
      child: const Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.circle, size: 7, color: Colores.naranja),
          SizedBox(width: 5),
          Text(
            'EN VIVO',
            style: TextStyle(
              fontFamily: Letras.texto,
              fontSize: 10,
              fontWeight: FontWeight.w800,
              letterSpacing: 1,
              color: Colores.naranja,
            ),
          ),
        ],
      ),
    );
  }
}
