/// Películas y Series en la TV (diseno_kairos_tv: tv-08, tv-09): chips de
/// categorías y la grilla de pósters. OK abre el detalle; OK largo agrega o
/// quita de favoritos. La grilla se arma a medida que se baja (puede haber
/// miles de títulos). También una sección nueva "a demanda" (Música...:
/// [GrillaTv.nueva]), igual que Películas.
library;

import 'package:flutter/material.dart';

import '../movil/datos.dart';
import '../movil/estilo.dart';
import 'estructura.dart';
import 'foco.dart';
import 'inicio.dart';
import 'piezas.dart';

class GrillaTv extends StatefulWidget {
  const GrillaTv({super.key, required this.contenido, this.nueva});

  /// "pelicula" o "serie"
  final String contenido;

  /// La clave de una sección nueva (Música...) para mostrar lo suyo; null = Películas o Series.
  final String? nueva;

  @override
  State<GrillaTv> createState() => _GrillaTvState();
}

class _GrillaTvState extends State<GrillaTv> {
  String? _categoria;

  @override
  Widget build(BuildContext context) {
    final datos = DatosScope.of(context);
    return ListenableBuilder(
      listenable: datos.biblioteca,
      builder: (context, _) {
        final catalogo = datos.catalogo;
        final peliculas = widget.contenido == 'pelicula';
        final nueva = widget.nueva == null ? null : catalogo.seccionNueva(widget.nueva!);
        final todas = nueva?.canales ?? catalogo.peliculas;
        final categorias = <String>{
          for (final c in peliculas ? todas.map((p) => p.categoria) : catalogo.series.map((s) => s.categoria))
            if (c.isNotEmpty) c,
        }.toList();
        final lista = peliculas ? todas.where((p) => _categoria == null || p.categoria == _categoria).toList() : null;
        final cantidad = peliculas
            ? lista!.length
            : catalogo.series.where((s) => _categoria == null || s.categoria == _categoria).length;
        final series = peliculas
            ? null
            : catalogo.series.where((s) => _categoria == null || s.categoria == _categoria).toList();

        return CustomScrollView(
          slivers: [
            SliverList.list(
              children: [
                EncabezadoTv(
                  sobretitulo: 'Catálogo',
                  titulo: nueva?.nombre ?? (peliculas ? 'Películas' : 'Series'),
                  accion: BotonTv(
                    texto: 'Buscar',
                    icono: Icons.search_rounded,
                    alOk: () => NavegacionTv.of(context).irA(SeccionTv.buscar),
                  ),
                ),
                const SizedBox(height: 10),
                if (categorias.length > 1)
                  FilaChipsTv(
                    opciones: [(null, 'Todo'), for (final c in categorias) (c, categoriaLegible(c))],
                    activa: _categoria,
                    alElegir: (valor) => setState(() => _categoria = valor),
                  ),
                Padding(
                  padding: const EdgeInsets.fromLTRB(MargenTv.izquierda, 14, MargenTv.derecha, 0),
                  child: Text(
                    nueva != null
                        ? (cantidad == 0
                              ? 'Todavía no hay nada acá.'
                              : '$cantidad ${cantidad == 1 ? 'título' : 'títulos'}')
                        : cantidad == 0
                        ? 'Todavía no hay ${peliculas ? 'películas' : 'series'}.'
                        : '$cantidad ${peliculas ? (cantidad == 1 ? 'película' : 'películas') : (cantidad == 1 ? 'serie' : 'series')}',
                    style: LetraTv.ayuda.copyWith(fontSize: 16),
                  ),
                ),
              ],
            ),
            SliverPadding(
              padding: const EdgeInsets.fromLTRB(MargenTv.izquierda, 22, MargenTv.derecha, 80),
              sliver: SliverGrid.builder(
                gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                  crossAxisCount: 7,
                  mainAxisSpacing: 30,
                  crossAxisSpacing: 22,
                  childAspectRatio: 2 / 3,
                ),
                itemCount: cantidad,
                itemBuilder: (context, i) => lista != null
                    ? posterPeliculaTv(context, lista[i], autofocus: i == 0)
                    : posterSerieTv(context, series![i], autofocus: i == 0),
              ),
            ),
          ],
        );
      },
    );
  }
}
