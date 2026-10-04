/// Piezas de pantalla que se repiten (como los parciales de templates/parciales/).
library;

import 'package:flutter/material.dart';

import '../tema.dart';

/// La marca Kairos TV: vertical = el logo completo; horizontal = el televisor
/// con "KairosTV" al lado, igual que el menú del panel ("Kairos" blanco y
/// "TV" naranja, en Sora). El texto se dibuja (el del PNG es azul oscuro y
/// no se vería sobre el fondo).
class MarcaKairos extends StatelessWidget {
  const MarcaKairos({super.key, this.tamanio = 56, this.vertical = false});

  final double tamanio;
  final bool vertical;

  @override
  Widget build(BuildContext context) {
    // Vertical (login y pantallas de bienvenida): el logo completo, con su texto "KairosTV"
    if (vertical) {
      return Image.asset('assets/logo/logo.png', height: tamanio * 2.4);
    }
    // El símbolo con el brillo celeste del panel (drop-shadow del .marca-isotipo)
    final simbolo = DecoratedBox(
      decoration: BoxDecoration(
        boxShadow: [BoxShadow(color: Colores.celeste.withValues(alpha: 0.22), blurRadius: tamanio * 0.45)],
      ),
      child: Image.asset('assets/logo/simbolo.png', height: tamanio),
    );
    final texto = Text.rich(
      TextSpan(
        children: [
          const TextSpan(
            text: 'Kairos',
            style: TextStyle(color: Colores.texto),
          ),
          const TextSpan(
            text: 'TV',
            style: TextStyle(color: Colores.naranja),
          ),
        ],
      ),
      style: estiloTitulo(tamanio * 0.56).copyWith(height: 1.0, letterSpacing: -tamanio * 0.025),
    );
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        simbolo,
        SizedBox(width: tamanio * 0.24),
        texto,
      ],
    );
  }
}

/// El botón principal: el .btn-primary del panel (azul, con su sombra).
class BotonDegradado extends StatelessWidget {
  const BotonDegradado({super.key, required this.texto, required this.alTocar, this.icono, this.cargando = false});

  final String texto;
  final VoidCallback? alTocar;
  final IconData? icono;
  final bool cargando;

  @override
  Widget build(BuildContext context) {
    final activo = alTocar != null && !cargando;
    return Opacity(
      opacity: activo ? 1 : 0.6,
      child: DecoratedBox(
        decoration: BoxDecoration(
          color: Colores.azul,
          borderRadius: BorderRadius.circular(Radios.chico),
          boxShadow: [
            BoxShadow(color: Colores.azul.withValues(alpha: 0.30), blurRadius: 20, offset: const Offset(0, 8)),
          ],
        ),
        child: Material(
          color: Colors.transparent,
          child: InkWell(
            borderRadius: BorderRadius.circular(Radios.chico),
            onTap: activo ? alTocar : null,
            // Con el control remoto: el foco se ve con un borde naranja (como el panel)
            focusColor: Colores.naranja.withValues(alpha: 0.25),
            child: SizedBox(
              height: 54,
              child: Center(
                child: cargando
                    ? const SizedBox(
                        height: 22,
                        width: 22,
                        child: CircularProgressIndicator(strokeWidth: 2.5, color: Colors.white),
                      )
                    : Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          if (icono != null) ...[Icon(icono, color: Colors.white, size: 20), const SizedBox(width: 8)],
                          Text(
                            texto,
                            style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w700, fontSize: 15),
                          ),
                        ],
                      ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// La foto del usuario, o sus iniciales, con un aro en degradé.
class Avatar extends StatelessWidget {
  const Avatar({super.key, required this.iniciales, this.foto, this.radio = 22});

  final String iniciales;
  final String? foto;
  final double radio;

  @override
  Widget build(BuildContext context) {
    final conFoto = foto != null && foto!.isNotEmpty;
    return Container(
      padding: EdgeInsets.all(radio * 0.08 + 1),
      decoration: const BoxDecoration(gradient: Degradados.principal, shape: BoxShape.circle),
      child: CircleAvatar(
        radius: radio,
        backgroundColor: Colores.superficieAlta,
        foregroundImage: conFoto ? NetworkImage(foto!) : null,
        child: Text(
          iniciales,
          style: TextStyle(color: Colores.texto, fontWeight: FontWeight.w700, fontSize: radio * 0.68),
        ),
      ),
    );
  }
}

/// Ícono dentro de un cuadradito redondeado con degradé (accesos, encabezados).
class IconoDegradado extends StatelessWidget {
  const IconoDegradado(this.icono, {super.key, this.tamanio = 44});

  final IconData icono;
  final double tamanio;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: tamanio,
      height: tamanio,
      decoration: BoxDecoration(gradient: Degradados.principal, borderRadius: BorderRadius.circular(tamanio * 0.32)),
      child: Icon(icono, color: Colors.white, size: tamanio * 0.5),
    );
  }
}

/// Un error a pantalla completa, con botón para reintentar.
class VistaError extends StatelessWidget {
  const VistaError({super.key, required this.mensaje, this.alReintentar});

  final String mensaje;
  final VoidCallback? alReintentar;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.wifi_off_rounded, size: 52, color: Colores.textoSuave),
            const SizedBox(height: 16),
            Text(
              mensaje,
              textAlign: TextAlign.center,
              style: const TextStyle(color: Colores.textoSuave),
            ),
            if (alReintentar != null) ...[
              const SizedBox(height: 24),
              OutlinedButton.icon(
                onPressed: alReintentar,
                icon: const Icon(Icons.refresh_rounded),
                label: const Text('Reintentar'),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

/// Un texto en gris cuando una lista está vacía.
class VistaVacia extends StatelessWidget {
  const VistaVacia({super.key, required this.mensaje, this.icono = Icons.inbox_rounded});

  final String mensaje;
  final IconData icono;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icono, size: 52, color: Colores.borde),
            const SizedBox(height: 12),
            Text(
              mensaje,
              textAlign: TextAlign.center,
              style: const TextStyle(color: Colores.textoSuave),
            ),
          ],
        ),
      ),
    );
  }
}

/// Recuadro con un error general (arriba de un formulario).
class AvisoError extends StatelessWidget {
  const AvisoError(this.mensaje, {super.key});

  final String mensaje;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      margin: const EdgeInsets.only(bottom: 16),
      decoration: BoxDecoration(
        color: Colores.peligro.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(Radios.chico),
        border: Border.all(color: Colores.peligro.withValues(alpha: 0.4)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Icon(Icons.error_outline_rounded, color: Colores.peligro, size: 20),
          const SizedBox(width: 10),
          Expanded(
            child: Text(mensaje, style: const TextStyle(color: Colores.peligro)),
          ),
        ],
      ),
    );
  }
}

/// Título de una sección, con la rayita celeste → azul de los títulos del panel.
class TituloSeccion extends StatelessWidget {
  const TituloSeccion(this.texto, {super.key});

  final String texto;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(4, 24, 4, 10),
      child: Row(
        children: [
          const RayitaTitulo(),
          const SizedBox(width: 10),
          Flexible(
            child: Text(
              texto,
              overflow: TextOverflow.ellipsis,
              style: estiloTitulo(16, peso: FontWeight.w600),
            ),
          ),
        ],
      ),
    );
  }
}

/// La rayita vertical celeste → azul, con brillo, de los títulos del panel (.tarjeta-titulo::before).
class RayitaTitulo extends StatelessWidget {
  const RayitaTitulo({super.key, this.alto = 16});

  final double alto;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 4,
      height: alto,
      decoration: BoxDecoration(
        gradient: Degradados.principal,
        borderRadius: BorderRadius.circular(99),
        boxShadow: [BoxShadow(color: Colores.celeste.withValues(alpha: 0.35), blurRadius: 9)],
      ),
    );
  }
}

/// Una tarjeta con filas "etiqueta / valor" (para ver datos).
class TarjetaDatos extends StatelessWidget {
  const TarjetaDatos({super.key, required this.filas});

  final List<(String, String)> filas;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          for (final (indice, (etiqueta, valor)) in filas.indexed) ...[
            if (indice > 0) const Divider(height: 1, color: Colores.borde, indent: 16, endIndent: 16),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(etiqueta, style: const TextStyle(color: Colores.textoSuave, fontSize: 12)),
                  const SizedBox(height: 2),
                  Text(
                    valor.isEmpty ? '—' : valor,
                    style: TextStyle(fontWeight: FontWeight.w500, color: valor.isEmpty ? Colores.borde : Colores.texto),
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }
}

/// Etiqueta de color ("Activo", "Administrador").
class Etiqueta extends StatelessWidget {
  const Etiqueta(this.texto, {super.key, this.color = Colores.celeste});

  final String texto;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.14),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: color.withValues(alpha: 0.35)),
      ),
      child: Text(
        texto,
        style: TextStyle(color: color, fontSize: 12, fontWeight: FontWeight.w600),
      ),
    );
  }
}
