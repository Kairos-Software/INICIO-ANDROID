/// Buscar en la TV (diseno_kairos_tv: tv-14): un teclado en pantalla que se
/// maneja con las flechas (también sirve un teclado o el micrófono del
/// control, si escribe), y los resultados a la izquierda: canales, películas
/// y series. El foco arranca en la letra "A".
library;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../movil/componentes.dart';
import '../movil/datos.dart';
import '../movil/estilo.dart';
import 'detalle.dart';
import 'foco.dart';
import 'piezas.dart';
import 'reproductor.dart';

class BuscarTv extends StatefulWidget {
  const BuscarTv({super.key});

  @override
  State<BuscarTv> createState() => _BuscarTvState();
}

class _BuscarTvState extends State<BuscarTv> {
  static const _maximo = 40;
  String _texto = '';

  void _escribir(String letra) => setState(() => _texto += letra);

  void _borrar() {
    if (_texto.isNotEmpty) setState(() => _texto = _texto.substring(0, _texto.length - 1));
  }

  KeyEventResult _tecla(FocusNode _, KeyEvent evento) {
    if (evento is KeyUpEvent) return KeyEventResult.ignored;
    if (evento.logicalKey == LogicalKeyboardKey.backspace) {
      _borrar();
      return KeyEventResult.handled;
    }
    final caracter = evento.character;
    if (caracter != null && RegExp(r'^[\p{L}\p{N} ]$', unicode: true).hasMatch(caracter)) {
      _escribir(caracter);
      return KeyEventResult.handled;
    }
    return KeyEventResult.ignored;
  }

  /// Sin tildes ni mayúsculas: "noticias" encuentra "Notícias".
  static String _normal(String texto) => texto
      .toLowerCase()
      .replaceAll(RegExp('[áàä]'), 'a')
      .replaceAll(RegExp('[éèë]'), 'e')
      .replaceAll(RegExp('[íìï]'), 'i')
      .replaceAll(RegExp('[óòö]'), 'o')
      .replaceAll(RegExp('[úùü]'), 'u');

  @override
  Widget build(BuildContext context) {
    final catalogo = DatosScope.of(context).catalogo;
    final buscado = _normal(_texto.trim());
    final resultados = <Widget>[];
    if (buscado.isNotEmpty) {
      for (final canal in catalogo.canales) {
        if (resultados.length >= _maximo) break;
        final numero = catalogo.numeroDe(canal);
        if (_normal(canal.nombre).contains(buscado) || numero == buscado) {
          final categoria = categoriaLegible(canal.categoria);
          resultados.add(
            _Resultado(
              imagen: LogoCanalTv(canal: canal, tamanioIniciales: 20, relleno: const EdgeInsets.all(6)),
              titulo: canal.nombre,
              subtitulo: ['Canal $numero', if (categoria.isNotEmpty) categoria].join(' · '),
              alOk: () => verCanalTv(context, canal),
            ),
          );
        }
      }
      for (final pelicula in catalogo.peliculas) {
        if (resultados.length >= _maximo) break;
        if (_normal(pelicula.nombre).contains(buscado)) {
          final anio = anioDe(pelicula.nombre);
          resultados.add(
            _Resultado(
              imagen: Imagen(url: pelicula.logo, nombre: pelicula.nombre, tamanioIniciales: 16),
              poster: true,
              titulo: sinAnio(pelicula.nombre),
              subtitulo: anio == null ? 'Película' : 'Película · $anio',
              alOk: () => abrirTv<void>(context, DetalleTv.pelicula(pelicula)),
            ),
          );
        }
      }
      for (final serie in catalogo.series) {
        if (resultados.length >= _maximo) break;
        if (_normal(serie.nombre).contains(buscado)) {
          resultados.add(
            _Resultado(
              imagen: Imagen(url: serie.imagen, nombre: serie.nombre, tamanioIniciales: 16),
              poster: true,
              titulo: serie.nombre,
              subtitulo: 'Serie · ${serie.episodios.length} episodios',
              alOk: () => abrirTv<void>(context, DetalleTv.serie(serie)),
            ),
          );
        }
      }
    }

    return Focus(
      onKeyEvent: _tecla,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(MargenTv.izquierda, MargenTv.arriba + 14, MargenTv.derecha, 0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Text('CATÁLOGO', style: LetraTv.sobretitulo),
            const SizedBox(height: 4),
            const Text('Buscar', style: LetraTv.pantalla),
            const SizedBox(height: 22),
            // Lo escrito (no es un campo de texto: se escribe con el teclado de abajo)
            Container(
              height: 68,
              padding: const EdgeInsets.symmetric(horizontal: 24),
              decoration: BoxDecoration(
                color: Tono.capaBaja,
                borderRadius: BorderRadius.circular(Curva.boton),
                border: Border.all(color: Tono.celeste.withValues(alpha: .7), width: 2),
                boxShadow: brilloCeleste(desenfoque: 24, opacidad: .2),
              ),
              child: Row(
                children: [
                  const Icon(Icons.search_rounded, color: Tono.textoSuave, size: 28),
                  const SizedBox(width: 16),
                  Text(
                    _texto.isEmpty ? 'Canal, película o serie' : _texto,
                    style: TextStyle(
                      fontFamily: Letra.texto,
                      fontSize: 24,
                      color: _texto.isEmpty ? Tono.textoApagado : Tono.texto,
                    ),
                  ),
                  if (_texto.isNotEmpty) Container(width: 2, height: 30, color: Tono.celeste),
                ],
              ),
            ),
            const SizedBox(height: 28),
            Expanded(
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text('Resultados', style: LetraTv.tarjeta),
                        const SizedBox(height: 14),
                        Expanded(
                          child: buscado.isEmpty
                              ? const Text('Escribí con el teclado de la derecha.', style: LetraTv.cuerpo)
                              : resultados.isEmpty
                              ? Text('No encontramos "$_texto".', style: LetraTv.cuerpo)
                              : FocusTraversalGroup(
                                  child: ListView.separated(
                                    clipBehavior: Clip.none,
                                    padding: const EdgeInsets.only(bottom: 40, right: 8),
                                    itemCount: resultados.length,
                                    separatorBuilder: (_, _) => const SizedBox(height: 14),
                                    itemBuilder: (_, i) => resultados[i],
                                  ),
                                ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 40),
                  SizedBox(
                    width: 560,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text('Teclado', style: LetraTv.tarjeta),
                        const SizedBox(height: 14),
                        _Teclado(alLetra: _escribir, alBorrar: _borrar, alLimpiar: () => setState(() => _texto = '')),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _Teclado extends StatelessWidget {
  const _Teclado({required this.alLetra, required this.alBorrar, required this.alLimpiar});

  final ValueChanged<String> alLetra;
  final VoidCallback alBorrar;
  final VoidCallback alLimpiar;

  static const _filas = ['ABCDEFGHIJ', 'KLMNÑOPQRS', 'TUVWXYZ', '1234567890'];

  @override
  Widget build(BuildContext context) {
    Widget tecla(String texto, VoidCallback alOk, {double ancho = 48, bool autofocus = false}) => Padding(
      padding: const EdgeInsets.all(4),
      child: Enfocable(
        alOk: alOk,
        autofocus: autofocus,
        curva: Curva.medio + 2,
        escala: 1.1,
        etiqueta: texto,
        child: Container(
          width: ancho,
          height: 52,
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: Tono.capaAlta,
            borderRadius: BorderRadius.circular(Curva.medio + 2),
            border: Border.all(color: Tono.bordeSuave.withValues(alpha: .45)),
          ),
          child: Text(
            texto,
            style: const TextStyle(
              fontFamily: Letra.texto,
              fontSize: 19,
              fontWeight: FontWeight.w700,
              color: Tono.texto,
            ),
          ),
        ),
      ),
    );

    return FocusTraversalGroup(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          for (final (f, fila) in _filas.indexed)
            Row(
              children: [
                for (final (i, letra) in fila.split('').indexed)
                  tecla(letra, () => alLetra(letra.toLowerCase()), autofocus: f == 0 && i == 0),
                if (f == 2) tecla('Borrar', alBorrar, ancho: 112),
              ],
            ),
          Row(children: [tecla('Espacio', () => alLetra(' '), ancho: 216), tecla('Limpiar', alLimpiar, ancho: 160)]),
        ],
      ),
    );
  }
}

class _Resultado extends StatelessWidget {
  const _Resultado({
    required this.imagen,
    required this.titulo,
    required this.subtitulo,
    required this.alOk,
    this.poster = false,
  });

  final Widget imagen;
  final String titulo;
  final String subtitulo;
  final VoidCallback alOk;
  final bool poster;

  @override
  Widget build(BuildContext context) {
    return Enfocable(
      alOk: alOk,
      curva: Curva.tarjeta,
      escala: 1.02,
      etiqueta: '$titulo, $subtitulo',
      child: Container(
        height: 88,
        padding: const EdgeInsets.symmetric(horizontal: 18),
        decoration: BoxDecoration(
          color: Tono.capa,
          borderRadius: BorderRadius.circular(Curva.tarjeta),
          border: Border.all(color: Tono.bordeSuave.withValues(alpha: .45)),
        ),
        child: Row(
          children: [
            ClipRRect(
              borderRadius: BorderRadius.circular(Curva.medio),
              child: Container(width: poster ? 46 : 72, height: poster ? 68 : 52, color: Tono.capaAlta, child: imagen),
            ),
            const SizedBox(width: 18),
            Expanded(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    titulo,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      fontFamily: Letra.texto,
                      fontSize: 20,
                      fontWeight: FontWeight.w700,
                      color: Tono.texto,
                    ),
                  ),
                  Text(subtitulo, style: LetraTv.ayuda.copyWith(fontSize: 15)),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
