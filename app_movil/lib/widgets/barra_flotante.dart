/// La barra de navegación inferior flotante: una cápsula redondeada sobre
/// el contenido, con el ítem activo resaltado en degradé.
library;

import 'package:flutter/material.dart';

import '../tema.dart';

class ItemBarra {
  const ItemBarra({required this.icono, required this.iconoActivo, required this.etiqueta, this.contador = 0});

  final IconData icono;
  final IconData iconoActivo;
  final String etiqueta;

  /// Número en rojo arriba del ícono (ej: notificaciones sin leer). 0 = no se muestra.
  final int contador;
}

class BarraFlotante extends StatelessWidget {
  const BarraFlotante({super.key, required this.items, required this.seleccionado, required this.alElegir});

  final List<ItemBarra> items;
  final int seleccionado;
  final ValueChanged<int> alElegir;

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      top: false,
      child: Container(
        margin: const EdgeInsets.fromLTRB(16, 0, 16, 12),
        padding: const EdgeInsets.all(6),
        decoration: BoxDecoration(
          color: Colores.fondoAlto.withValues(alpha: 0.97),
          borderRadius: BorderRadius.circular(Radios.grande),
          border: Border.all(color: Colores.borde),
          boxShadow: const [BoxShadow(color: Colors.black54, blurRadius: 24, offset: Offset(0, 10))],
        ),
        child: Row(
          children: [
            for (final (indice, item) in items.indexed)
              Expanded(child: _Item(item: item, activo: indice == seleccionado, alTocar: () => alElegir(indice))),
          ],
        ),
      ),
    );
  }
}

class _Item extends StatelessWidget {
  const _Item({required this.item, required this.activo, required this.alTocar});

  final ItemBarra item;
  final bool activo;
  final VoidCallback alTocar;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: alTocar,
      behavior: HitTestBehavior.opaque,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 220),
        curve: Curves.easeOut,
        padding: const EdgeInsets.symmetric(vertical: 10),
        // Activo = como el item activo del menú del panel: velo celeste/azul con borde celeste
        decoration: BoxDecoration(
          gradient: activo ? Degradados.activo : null,
          borderRadius: BorderRadius.circular(Radios.grande - 6),
          border: Border.all(color: activo ? Colores.celeste.withValues(alpha: 0.25) : Colors.transparent),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Badge(
              isLabelVisible: item.contador > 0,
              backgroundColor: Colores.peligro,
              label: Text('${item.contador}'),
              child: Icon(activo ? item.iconoActivo : item.icono, color: activo ? Colores.celeste : Colores.textoSuave),
            ),
            const SizedBox(height: 2),
            Text(
              item.etiqueta,
              style: TextStyle(
                fontSize: 11,
                fontWeight: activo ? FontWeight.w700 : FontWeight.w600,
                color: activo ? Colors.white : Colores.textoSuave,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
