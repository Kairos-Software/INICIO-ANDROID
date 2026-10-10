/// Buscar canales, películas y series por nombre (la lupa de la barra de arriba).
/// El campo sigue el diseño de Stitch: fondo oscuro, borde que se pone celeste.
///
/// Abajo del campo, los chips Todo / En vivo / Películas / Series (con cuántos
/// encontró cada uno). Arranca en el de la sección desde donde se abrió: desde
/// Series busca series. En "Todo" también aparece lo de las secciones nuevas
/// (Música, Radio...). La búsqueda en sí está en busqueda.dart (es la misma
/// que la de la TV).
library;

import 'package:flutter/material.dart';

import '../api/modelos.dart';
import 'busqueda.dart';
import 'componentes.dart';
import 'datos.dart';
import 'estilo.dart';
import 'estructura.dart';
import 'grilla.dart';
import 'secciones_nuevas.dart';

class PantallaBuscar extends StatefulWidget {
  const PantallaBuscar({super.key, required this.irA, this.que = QueBuscar.todo});

  /// Para ir a En Vivo con un canal (esta pantalla se abre encima de las secciones).
  final void Function(Seccion seccion, {String? categoria, int? canal}) irA;

  /// Qué se busca al abrir (según la sección desde donde se abrió).
  final QueBuscar que;

  /// Lo que se busca desde cada sección.
  static QueBuscar queDesde(Seccion seccion) => switch (seccion) {
    Seccion.enVivo => QueBuscar.enVivo,
    Seccion.peliculas => QueBuscar.peliculas,
    Seccion.series => QueBuscar.series,
    _ => QueBuscar.todo,
  };

  @override
  State<PantallaBuscar> createState() => _PantallaBuscarState();
}

class _PantallaBuscarState extends State<PantallaBuscar> {
  final _texto = TextEditingController();
  String _buscado = '';
  late QueBuscar _que = widget.que;

  @override
  void dispose() {
    _texto.dispose();
    super.dispose();
  }

  String get _ayuda => switch (_que) {
    QueBuscar.todo => 'Buscar canales, películas, series...',
    QueBuscar.enVivo => 'Buscar canales en vivo...',
    QueBuscar.peliculas => 'Buscar películas...',
    QueBuscar.series => 'Buscar series...',
  };

  @override
  Widget build(BuildContext context) {
    final catalogo = DatosScope.of(context).catalogo;
    final texto = _buscado.trim();
    final encontrado = texto.length < 2 ? Encontrado.nada : buscarEnCatalogo(catalogo, texto);
    bool muestra(QueBuscar que) => _que == QueBuscar.todo || _que == que;
    final canales = muestra(QueBuscar.enVivo) ? encontrado.canales : const <Canal>[];
    final peliculas = muestra(QueBuscar.peliculas) ? encontrado.peliculas : const <Canal>[];
    final series = muestra(QueBuscar.series) ? encontrado.series : const <Serie>[];
    final nuevas = _que == QueBuscar.todo ? encontrado.nuevas : const <(SeccionNueva, List<Canal>)>[];

    return Scaffold(
      backgroundColor: Tono.fondo,
      appBar: AppBar(
        backgroundColor: Tono.capaMinima,
        surfaceTintColor: Colors.transparent,
        titleSpacing: 0,
        title: Padding(
          padding: const EdgeInsets.only(right: Espacio.margen),
          child: TextField(
            controller: _texto,
            autofocus: true,
            onChanged: (valor) => setState(() => _buscado = valor),
            style: Letra.cuerpoGrande,
            textInputAction: TextInputAction.search,
            decoration: InputDecoration(
              hintText: _ayuda,
              hintStyle: Letra.cuerpo,
              isDense: true,
              filled: true,
              fillColor: Tono.capaBaja,
              prefixIcon: const Icon(Icons.search_rounded, color: Tono.textoSuave, size: 20),
              suffixIcon: _buscado.isEmpty
                  ? null
                  : IconButton(
                      onPressed: () => setState(() {
                        _texto.clear();
                        _buscado = '';
                      }),
                      icon: const Icon(Icons.close_rounded, color: Tono.textoSuave, size: 20),
                    ),
              contentPadding: const EdgeInsets.symmetric(vertical: 12),
              enabledBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(99),
                borderSide: const BorderSide(color: Tono.capaMaxima),
              ),
              focusedBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(99),
                borderSide: const BorderSide(color: Tono.celeste),
              ),
            ),
          ),
        ),
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(52),
          child: SizedBox(
            height: 52,
            child: ListView(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.fromLTRB(Espacio.margen, 4, Espacio.margen, 10),
              children: [
                for (final que in QueBuscar.values) ...[
                  if (que != QueBuscar.values.first) const SizedBox(width: Espacio.xs),
                  ChipFiltro(
                    texto: texto.length < 2 ? que.texto : '${que.texto} (${encontrado.cuantos(que)})',
                    icono: que == QueBuscar.todo ? Icons.auto_awesome_rounded : null,
                    puntoEnVivo: que == QueBuscar.enVivo,
                    activo: _que == que,
                    alTocar: () => setState(() => _que = que),
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
      body: texto.length < 2
          ? const Vacio(icono: Icons.search_rounded, texto: 'Escribí al menos dos letras del nombre.')
          : encontrado.vacio(_que)
          ? Vacio(
              icono: Icons.search_off_rounded,
              texto: _que == QueBuscar.todo || encontrado.vacio(QueBuscar.todo)
                  ? 'No encontramos nada con "$texto".'
                  : 'No hay ${_que.texto.toLowerCase()} con "$texto". Probá en "Todo".',
            )
          : CustomScrollView(
              slivers: [
                const SliverToBoxAdapter(child: SizedBox(height: Espacio.margen)),
                if (canales.isNotEmpty) ...[
                  SliverToBoxAdapter(
                    child: EncabezadoSeccion(
                      titulo: 'Canales en vivo',
                      icono: const PuntoEnVivo(tamanio: 10, color: Tono.rubi),
                    ),
                  ),
                  SliverList.builder(
                    itemCount: canales.length,
                    itemBuilder: (context, i) => _ResultadoCanal(
                      canal: canales[i],
                      alTocar: () {
                        Navigator.pop(context);
                        widget.irA(Seccion.enVivo, canal: canales[i].id);
                      },
                    ),
                  ),
                  const SliverToBoxAdapter(child: SizedBox(height: Espacio.lg)),
                ],
                for (final (titulo, cantidad, esSerie) in [
                  ('Películas', peliculas.length, false),
                  ('Series', series.length, true),
                ])
                  if (cantidad > 0) ...[
                    SliverToBoxAdapter(
                      child: EncabezadoSeccion(
                        titulo: titulo,
                        icono: Icon(
                          esSerie ? Icons.video_library_rounded : Icons.movie_rounded,
                          size: 20,
                          color: Tono.celeste,
                        ),
                      ),
                    ),
                    SliverPadding(
                      padding: const EdgeInsets.fromLTRB(Espacio.margen, 0, Espacio.margen, Espacio.lg),
                      sliver: SliverLayoutBuilder(
                        builder: (context, limites) => SliverGrid.builder(
                          gridDelegate: grillaPosters(limites.crossAxisExtent),
                          itemCount: cantidad,
                          itemBuilder: (context, i) =>
                              esSerie ? tarjetaSerie(context, series[i]) : tarjetaPelicula(context, peliculas[i]),
                        ),
                      ),
                    ),
                  ],
                // Las secciones nuevas: las "en vivo" (radios) como los canales, las otras como películas
                for (final (seccion, lista) in nuevas) ...[
                  SliverToBoxAdapter(
                    child: EncabezadoSeccion(
                      titulo: seccion.nombre,
                      icono: Icon(iconoDeSeccion(seccion.icono), size: 20, color: Tono.celeste),
                    ),
                  ),
                  if (seccion.enVivo) ...[
                    SliverList.builder(
                      itemCount: lista.length,
                      itemBuilder: (context, i) => _ResultadoCanal(
                        canal: lista[i],
                        alTocar: () => abrirSeccionNueva(context, seccion, canal: lista[i].id),
                      ),
                    ),
                    const SliverToBoxAdapter(child: SizedBox(height: Espacio.lg)),
                  ] else
                    SliverPadding(
                      padding: const EdgeInsets.fromLTRB(Espacio.margen, 0, Espacio.margen, Espacio.lg),
                      sliver: SliverLayoutBuilder(
                        builder: (context, limites) => SliverGrid.builder(
                          gridDelegate: grillaPosters(limites.crossAxisExtent),
                          itemCount: lista.length,
                          itemBuilder: (context, i) => tarjetaPelicula(context, lista[i], tipo: seccion.nombre),
                        ),
                      ),
                    ),
                ],
              ],
            ),
    );
  }
}

class _ResultadoCanal extends StatelessWidget {
  const _ResultadoCanal({required this.canal, required this.alTocar});

  final Canal canal;
  final VoidCallback alTocar;

  @override
  Widget build(BuildContext context) {
    return ListTile(
      onTap: alTocar,
      contentPadding: const EdgeInsets.symmetric(horizontal: Espacio.margen, vertical: 2),
      leading: ClipRRect(
        borderRadius: BorderRadius.circular(Curva.medio),
        child: SizedBox(
          width: 56,
          height: 40,
          child: Imagen(
            url: canal.logo,
            nombre: canal.nombre,
            ajuste: BoxFit.contain,
            relleno: const EdgeInsets.all(4),
            fondo: Tono.capa,
            tamanioIniciales: 14,
          ),
        ),
      ),
      title: Text(canal.nombre, style: Letra.etiqueta.copyWith(fontSize: 14, fontWeight: FontWeight.w700)),
      subtitle: Text(categoriaLegible(canal.categoria), style: Letra.numeros),
      trailing: const Icon(Icons.play_circle_outline_rounded, color: Tono.celeste),
    );
  }
}
