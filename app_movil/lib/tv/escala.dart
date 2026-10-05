/// En la TV, la app se dibuja SIEMPRE en un lienzo de 1920×1080 (las medidas
/// del diseño, diseno_kairos_tv/) y se agranda o achica para llenar la
/// pantalla. Así se ve igual en un televisor HD, Full HD o 4K: Android le
/// dice a Flutter que una TV Full HD mide 960×540, y con las medidas del
/// diseño todo quedaría el doble de grande.
library;

import 'package:flutter/material.dart';

const anchoTv = 1920.0;

class EscalaTv extends StatelessWidget {
  const EscalaTv({super.key, required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    final medidas = MediaQuery.of(context);
    if (medidas.size.width <= 0) return child;
    final escala = medidas.size.width / anchoTv;
    final alto = medidas.size.height / escala;
    return FittedBox(
      fit: BoxFit.contain,
      alignment: Alignment.topLeft,
      child: SizedBox(
        width: anchoTv,
        height: alto,
        child: MediaQuery(
          data: medidas.copyWith(
            size: Size(anchoTv, alto),
            devicePixelRatio: medidas.devicePixelRatio * escala,
            padding: medidas.padding / escala,
            viewPadding: medidas.viewPadding / escala,
            viewInsets: medidas.viewInsets / escala,
            // En la TV las letras no se agrandan con la accesibilidad del sistema: ya son grandes
            textScaler: TextScaler.noScaling,
          ),
          child: child,
        ),
      ),
    );
  }
}
