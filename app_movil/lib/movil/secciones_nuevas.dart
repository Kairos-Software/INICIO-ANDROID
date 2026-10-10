/// Las secciones que se crean en el panel (Música, Radio...: [SeccionNueva]).
///
/// En el celular se abren desde los chips de arriba de Inicio, en una pantalla
/// propia: las "en vivo" (radios) como En Vivo (reproductor arriba y la lista
/// abajo) y las "a demanda" (música) como Películas (grilla de pósters).
library;

import 'package:flutter/material.dart';

import 'componentes.dart';
import 'datos.dart';
import 'en_vivo.dart';
import 'estilo.dart';
import 'grilla.dart';

/// El ícono que se eligió en el panel para la sección.
IconData iconoDeSeccion(String icono) => switch (icono) {
  'musica' => Icons.music_note_rounded,
  'radio' => Icons.radio_rounded,
  'deportes' => Icons.sports_soccer_rounded,
  'documentales' => Icons.public_rounded,
  'infantil' => Icons.child_care_rounded,
  'noticias' => Icons.newspaper_rounded,
  _ => Icons.auto_awesome_rounded,
};

Future<void> abrirSeccionNueva(BuildContext context, SeccionNueva seccion) =>
    abrirPantalla<void>(context, PantallaSeccionNueva(clave: seccion.clave, nombre: seccion.nombre));

class PantallaSeccionNueva extends StatelessWidget {
  const PantallaSeccionNueva({super.key, required this.clave, required this.nombre});

  /// Por clave (y no la sección misma): al volver a pedir el catálogo llegan secciones nuevas.
  final String clave;
  final String nombre;

  @override
  Widget build(BuildContext context) {
    final catalogo = DatosScope.of(context).catalogo;
    return Scaffold(
      backgroundColor: Tono.fondo,
      appBar: AppBar(
        backgroundColor: Tono.capaMinima,
        surfaceTintColor: Colors.transparent,
        centerTitle: true,
        title: Text(
          nombre.toUpperCase(),
          style: Letra.etiqueta.copyWith(color: Tono.celesteClaro, fontWeight: FontWeight.w700, letterSpacing: 1.2),
        ),
      ),
      body: ListenableBuilder(
        listenable: catalogo,
        builder: (context, _) {
          final seccion = catalogo.seccionNueva(clave);
          if (seccion == null) {
            return const Vacio(icono: Icons.inbox_outlined, texto: 'Esta sección ya no tiene nada para ver.');
          }
          return seccion.enVivo
              ? SeccionEnVivo(visible: true, nueva: clave)
              : SeccionGrilla(contenido: 'pelicula', nueva: clave);
        },
      ),
    );
  }
}
