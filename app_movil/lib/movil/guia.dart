/// La guía de canales del celular (diseno_kairos_tv: mobile-05): todos los
/// canales en una lista con número, logo, nombre y categoría, con buscador y
/// filtro por categoría. Sin programación (todavía no hay EPG): no se
/// inventan horarios. Al tocar un canal, va a En Vivo reproduciéndolo.
library;

import 'package:flutter/material.dart';

import '../api/modelos.dart';
import 'componentes.dart';
import 'datos.dart';
import 'estilo.dart';

class PantallaGuia extends StatefulWidget {
  const PantallaGuia({super.key, required this.alElegir});

  /// Qué hacer con el canal elegido (En Vivo lo reproduce).
  final ValueChanged<Canal> alElegir;

  @override
  State<PantallaGuia> createState() => _PantallaGuiaState();
}

class _PantallaGuiaState extends State<PantallaGuia> {
  final _busqueda = TextEditingController();
  String? _categoria;

  @override
  void dispose() {
    _busqueda.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final catalogo = DatosScope.of(context).catalogo;
    final texto = _busqueda.text.trim().toLowerCase();
    final canales = [
      for (final canal in catalogo.canales)
        if ((_categoria == null || canal.categoria == _categoria) &&
            (texto.isEmpty || canal.nombre.toLowerCase().contains(texto) || catalogo.numeroDe(canal) == texto))
          canal,
    ];
    return Scaffold(
      backgroundColor: Tono.fondo,
      appBar: AppBar(
        backgroundColor: Tono.capaMinima,
        surfaceTintColor: Colors.transparent,
        centerTitle: true,
        title: Text(
          'GUÍA',
          style: Letra.etiqueta.copyWith(color: Tono.celesteClaro, fontWeight: FontWeight.w700, letterSpacing: 1.2),
        ),
      ),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(Espacio.margen, Espacio.margen, Espacio.margen, 12),
            child: TextField(
              controller: _busqueda,
              onChanged: (_) => setState(() {}),
              style: Letra.cuerpoGrande,
              decoration: InputDecoration(
                hintText: 'Buscar canal o número',
                hintStyle: Letra.cuerpoGrande.copyWith(color: Tono.textoApagado),
                prefixIcon: const Icon(Icons.search_rounded, color: Tono.textoSuave),
                filled: true,
                fillColor: Tono.capaBaja,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(Curva.boton),
                  borderSide: BorderSide(color: Tono.bordeSuave.withValues(alpha: .5)),
                ),
                enabledBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(Curva.boton),
                  borderSide: BorderSide(color: Tono.bordeSuave.withValues(alpha: .5)),
                ),
              ),
            ),
          ),
          SizedBox(
            height: 36,
            child: ListView(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: Espacio.margen),
              children: [
                ChipFiltro(
                  texto: 'Todos',
                  activo: _categoria == null,
                  compacto: true,
                  alTocar: () => setState(() => _categoria = null),
                ),
                for (final categoria in catalogo.categoriasEnVivo) ...[
                  const SizedBox(width: Espacio.sm),
                  ChipFiltro(
                    texto: categoriaLegible(categoria.nombre),
                    activo: _categoria == categoria.nombre,
                    compacto: true,
                    alTocar: () => setState(() => _categoria = categoria.nombre),
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(height: 12),
          Expanded(
            child: canales.isEmpty
                ? const Vacio(icono: Icons.search_off_rounded, texto: 'No hay canales con ese nombre o número.')
                : ListView.separated(
                    padding: EdgeInsets.fromLTRB(
                      Espacio.margen,
                      0,
                      Espacio.margen,
                      MediaQuery.paddingOf(context).bottom + Espacio.lg,
                    ),
                    itemCount: canales.length,
                    separatorBuilder: (_, _) => const Divider(height: 1, color: Tono.capaAlta),
                    itemBuilder: (context, i) {
                      final canal = canales[i];
                      return _FilaGuia(
                        canal: canal,
                        numero: catalogo.numeroDe(canal),
                        alTocar: () {
                          Navigator.pop(context);
                          widget.alElegir(canal);
                        },
                      );
                    },
                  ),
          ),
        ],
      ),
    );
  }
}

/// Una fila: número (dorado), logo o iniciales, nombre y categoría.
class _FilaGuia extends StatelessWidget {
  const _FilaGuia({required this.canal, required this.numero, required this.alTocar});

  final Canal canal;
  final String numero;
  final VoidCallback alTocar;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: alTocar,
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 4),
        child: Row(
          children: [
            SizedBox(
              width: 44,
              child: Text(
                numero,
                style: Letra.etiqueta.copyWith(color: Tono.dorado, fontSize: 14, fontWeight: FontWeight.w700),
              ),
            ),
            ClipRRect(
              borderRadius: BorderRadius.circular(Curva.medio),
              child: SizedBox(
                width: 44,
                height: 44,
                child: Imagen(
                  url: canal.logo,
                  nombre: canal.nombre,
                  ajuste: BoxFit.contain,
                  relleno: const EdgeInsets.all(4),
                  tamanioIniciales: 15,
                ),
              ),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    canal.nombre,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: Letra.etiqueta.copyWith(fontSize: 14, fontWeight: FontWeight.w700),
                  ),
                  if (canal.categoria.isNotEmpty)
                    Text(
                      categoriaLegible(canal.categoria),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: Letra.cuerpo.copyWith(fontSize: 13),
                    ),
                ],
              ),
            ),
            const Icon(Icons.chevron_right_rounded, color: Tono.textoSuave),
          ],
        ),
      ),
    );
  }
}
