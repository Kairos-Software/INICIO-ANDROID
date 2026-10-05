/// Buscar canales, películas y series por nombre (la lupa de la barra de arriba).
/// El campo sigue el diseño de Stitch: fondo oscuro, borde que se pone celeste.
library;

import 'package:flutter/material.dart';

import '../api/modelos.dart';
import 'componentes.dart';
import 'datos.dart';
import 'estilo.dart';
import 'estructura.dart';
import 'grilla.dart';

class PantallaBuscar extends StatefulWidget {
  const PantallaBuscar({super.key, required this.irA});

  /// Para ir a En Vivo con un canal (esta pantalla se abre encima de las secciones).
  final void Function(Seccion seccion, {String? categoria, int? canal}) irA;

  @override
  State<PantallaBuscar> createState() => _PantallaBuscarState();
}

class _PantallaBuscarState extends State<PantallaBuscar> {
  final _texto = TextEditingController();
  String _buscado = '';

  @override
  void dispose() {
    _texto.dispose();
    super.dispose();
  }

  static String _simple(String texto) {
    const conAcento = 'áéíóúüñ';
    const sinAcento = 'aeiouun';
    final minusculas = texto.toLowerCase();
    final buffer = StringBuffer();
    for (final letra in minusculas.split('')) {
      final i = conAcento.indexOf(letra);
      buffer.write(i >= 0 ? sinAcento[i] : letra);
    }
    return buffer.toString();
  }

  @override
  Widget build(BuildContext context) {
    final catalogo = DatosScope.of(context).catalogo;
    final buscado = _simple(_buscado.trim());
    bool coincide(String nombre) => buscado.length >= 2 && _simple(nombre).contains(buscado);
    final canales = catalogo.canales.where((c) => coincide(c.nombre)).take(30).toList();
    final peliculas = catalogo.peliculas.where((p) => coincide(p.nombre)).take(40).toList();
    final series = catalogo.series.where((s) => coincide(s.nombre)).take(40).toList();
    final nada = canales.isEmpty && peliculas.isEmpty && series.isEmpty;

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
              hintText: 'Buscar canales, películas, series...',
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
      ),
      body: buscado.length < 2
          ? const Vacio(icono: Icons.search_rounded, texto: 'Escribí al menos dos letras del nombre.')
          : nada
          ? Vacio(icono: Icons.search_off_rounded, texto: 'No encontramos nada con "$_buscado".')
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
