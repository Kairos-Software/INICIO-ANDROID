/// En vivo en la TV (diseno_kairos_tv: tv-05): los canales como tarjetas,
/// igual que las películas y series. Arriba, los chips de categorías; con
/// "Todo", una fila por categoría; con una categoría elegida, todos sus
/// canales en grilla. OK pone el canal a pantalla completa; OK largo lo
/// agrega o quita de favoritos.
///
/// También muestra una sección nueva "en vivo" (Radio...: [EnVivoTv.nueva]),
/// con sus categorías y sin el botón de la guía.
library;

import 'package:flutter/material.dart';

import '../api/modelos.dart';
import '../movil/datos.dart';
import '../movil/estilo.dart';
import 'estructura.dart';
import 'foco.dart';
import 'piezas.dart';
import 'reproductor.dart';

class EnVivoTv extends StatefulWidget {
  const EnVivoTv({super.key, this.nueva});

  /// La clave de una sección nueva (Radio...) para mostrar lo suyo; null = En vivo.
  final String? nueva;

  @override
  State<EnVivoTv> createState() => _EnVivoTvState();
}

class _EnVivoTvState extends State<EnVivoTv> {
  String? _categoria;

  @override
  Widget build(BuildContext context) {
    final datos = DatosScope.of(context);
    return ListenableBuilder(
      listenable: datos.biblioteca,
      builder: (context, _) {
        final catalogo = datos.catalogo;
        final biblioteca = datos.biblioteca;
        final nueva = widget.nueva == null ? null : catalogo.seccionNueva(widget.nueva!);
        final categorias = nueva?.categorias ?? catalogo.categoriasEnVivo;
        final todos = nueva?.canales ?? catalogo.canales;
        final elegida = categorias.where((c) => c.nombre == _categoria).firstOrNull;

        Widget tarjeta(Canal canal, List<Canal> lista, {bool autofocus = false}) => TarjetaCanalTv(
          canal: canal,
          numero: catalogo.numeroDe(canal),
          autofocus: autofocus,
          favorito: biblioteca.estaEnMiLista(Biblioteca.claveDe(canal)),
          alOk: () => verCanalTv(context, canal, lista: lista),
          alOkLargo: () => alternarFavoritoTv(context, Biblioteca.claveDe(canal)),
        );

        final cabecera = [
          EncabezadoTv(
            sobretitulo: nueva != null ? 'En vivo' : 'Televisión',
            titulo: nueva?.nombre ?? 'En vivo',
            accion: nueva != null
                ? null
                : BotonTv(
                    texto: 'Guía de canales',
                    icono: Icons.view_list_rounded,
                    alOk: () => NavegacionTv.of(context).irA(SeccionTv.guia),
                  ),
          ),
          const SizedBox(height: 10),
          FilaChipsTv(
            opciones: [
              (null, 'Todo'),
              for (final c in categorias)
                (c.nombre, categoriaLegible(c.nombre).isEmpty ? 'Otros' : categoriaLegible(c.nombre)),
            ],
            activa: _categoria,
            alElegir: (valor) => setState(() => _categoria = valor),
          ),
        ];

        if (todos.isEmpty) {
          return ListView(
            children: [
              ...cabecera,
              Padding(
                padding: const EdgeInsets.all(120),
                child: Center(
                  child: Text(
                    nueva != null
                        ? 'Todavía no hay nada disponible acá.'
                        : 'Todavía no hay canales en vivo disponibles.',
                    style: LetraTv.cuerpo,
                  ),
                ),
              ),
            ],
          );
        }

        // Una categoría: todos sus canales en grilla (se arma a medida que se baja)
        if (elegida != null) {
          return CustomScrollView(
            slivers: [
              SliverList.list(children: cabecera),
              SliverPadding(
                padding: const EdgeInsets.fromLTRB(MargenTv.izquierda, 24, MargenTv.derecha, 80),
                sliver: SliverGrid.builder(
                  gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                    crossAxisCount: 5,
                    mainAxisSpacing: 26,
                    crossAxisSpacing: 22,
                    childAspectRatio: 290 / 164,
                  ),
                  itemCount: elegida.canales.length,
                  itemBuilder: (_, i) => tarjeta(elegida.canales[i], elegida.canales, autofocus: i == 0),
                ),
              ),
            ],
          );
        }

        // Todo: una fila por categoría
        return ListView.builder(
          padding: const EdgeInsets.only(bottom: 80),
          itemCount: cabecera.length + categorias.length,
          itemBuilder: (_, i) {
            if (i < cabecera.length) return cabecera[i];
            final categoria = categorias[i - cabecera.length];
            final canales = categoria.canales;
            return FilaTv(
              titulo: categoriaLegible(categoria.nombre).isEmpty ? 'Otros' : categoriaLegible(categoria.nombre),
              final_: '${canales.length} canales',
              alto: 164,
              tarjetas: [
                for (final (j, canal) in canales.indexed)
                  tarjeta(canal, canales, autofocus: i == cabecera.length && j == 0),
              ],
            );
          },
        );
      },
    );
  }
}
