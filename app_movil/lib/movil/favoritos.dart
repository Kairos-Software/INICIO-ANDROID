/// Favoritos (diseno_kairos_tv: mobile-06 y mobile-09): lo que más se mira,
/// separado por tipo (canales, películas, series). Se agrega con el corazón
/// de un canal o el botón "Favoritos" de una película o serie. Se guarda en
/// el aparato (Biblioteca -> "Mi lista").
library;

import 'package:flutter/material.dart';

import 'componentes.dart';
import 'datos.dart';
import 'estilo.dart';
import 'estructura.dart';
import 'grilla.dart';

class SeccionFavoritos extends StatelessWidget {
  const SeccionFavoritos({super.key});

  @override
  Widget build(BuildContext context) {
    final datos = DatosScope.of(context);
    return ListenableBuilder(
      listenable: Listenable.merge([datos.catalogo, datos.biblioteca]),
      builder: (context, _) {
        final catalogo = datos.catalogo;
        final biblioteca = datos.biblioteca;
        final canales = catalogo.canalesFavoritos(biblioteca);
        final peliculas = catalogo.peliculasFavoritas(biblioteca);
        final series = catalogo.seriesFavoritas(biblioteca);
        final irA = NavegacionMovil.of(context).irA;
        final vacio = canales.isEmpty && peliculas.isEmpty && series.isEmpty;

        return ListView(
          padding: EdgeInsets.only(
            top: altoBarraSuperior(context) + Espacio.margen,
            bottom: altoBarraInferior(context) + 40,
          ),
          children: [
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: Espacio.margen),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Favoritos', style: Letra.display.copyWith(fontSize: 28, height: 32 / 28)),
                  const SizedBox(height: 2),
                  Text('Todo lo que más mirás, separado por tipo.', style: Letra.cuerpo),
                ],
              ),
            ),
            const SizedBox(height: 24),
            if (vacio && catalogo.cargado)
              Vacio(
                icono: Icons.favorite_border_rounded,
                texto:
                    'Todavía no tenés favoritos.\nTocá el corazón de un canal, o "Favoritos" en una película o serie.',
                accion: BotonPrincipal(
                  texto: 'Explorar contenido',
                  icono: Icons.explore_rounded,
                  alTocar: () => irA(Seccion.enVivo),
                ),
              ),
            if (canales.isNotEmpty) ...[
              EncabezadoSeccion(
                titulo: 'Canales',
                final_: Text('${canales.length}', style: Letra.numeros),
              ),
              SizedBox(
                height: 238,
                child: ListView.separated(
                  scrollDirection: Axis.horizontal,
                  padding: const EdgeInsets.symmetric(horizontal: Espacio.margen),
                  itemCount: canales.length,
                  separatorBuilder: (_, _) => const SizedBox(width: Espacio.sm),
                  itemBuilder: (_, i) => Align(
                    alignment: Alignment.topCenter,
                    child: TarjetaEnVivo(
                      canal: canales[i],
                      numero: catalogo.numeroDe(canales[i]),
                      alTocar: () => irA(Seccion.enVivo, canal: canales[i].id),
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 20),
            ],
            for (final (titulo, cantidad, tarjetas) in [
              ('Películas', peliculas.length, [for (final p in peliculas) tarjetaPelicula(context, p)]),
              ('Series', series.length, [for (final s in series) tarjetaSerie(context, s)]),
            ])
              if (tarjetas.isNotEmpty) ...[
                EncabezadoSeccion(
                  titulo: titulo,
                  final_: Text('$cantidad', style: Letra.numeros),
                ),
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: Espacio.margen),
                  child: LayoutBuilder(
                    builder: (context, limites) => GridView.builder(
                      shrinkWrap: true,
                      padding: EdgeInsets.zero,
                      physics: const NeverScrollableScrollPhysics(),
                      gridDelegate: grillaPosters(limites.maxWidth),
                      itemCount: tarjetas.length,
                      itemBuilder: (_, i) => tarjetas[i],
                    ),
                  ),
                ),
                const SizedBox(height: 24),
              ],
          ],
        );
      },
    );
  }
}
