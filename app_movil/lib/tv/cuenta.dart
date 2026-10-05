/// Mi cuenta en la TV (diseno_kairos_tv: tv-16): a la izquierda los datos
/// (código, hasta cuándo, pantallas, vendedor); a la derecha las
/// preferencias: volver al último canal al abrir, favoritos, buscar
/// actualizaciones y cerrar sesión.
library;

import 'package:flutter/material.dart';

import '../actualizacion.dart';
import '../aparato.dart';
import '../movil/componentes.dart';
import '../movil/datos.dart';
import '../movil/estilo.dart';
import '../sesion.dart';
import 'estructura.dart';
import 'foco.dart';
import 'piezas.dart';

class CuentaTv extends StatelessWidget {
  const CuentaTv({super.key});

  static const _meses = [
    'enero',
    'febrero',
    'marzo',
    'abril',
    'mayo',
    'junio',
    'julio',
    'agosto',
    'septiembre',
    'octubre',
    'noviembre',
    'diciembre',
  ];

  Future<void> _buscarActualizacion(BuildContext context) async {
    final hay = await VigilarActualizacion.buscarAhora(context);
    if (!context.mounted || hay == true) return;
    avisoTv(
      context,
      hay == false
          ? 'Ya tenés la última versión${Aparato.version.isEmpty ? '' : ' (${Aparato.version})'}'
          : 'No se pudo consultar. Probá en un rato.',
      icono: hay == false ? Icons.check_circle_rounded : Icons.wifi_off_rounded,
    );
  }

  Future<void> _salir(BuildContext context) async {
    final sesion = SesionScope.leer(context);
    final salir = await showDialog<bool>(
      context: context,
      builder: (contexto) => DialogoTv(
        icono: Icons.logout_rounded,
        titulo: '¿Cerrar sesión en esta TV?',
        texto: sesion.esCliente
            ? 'La pantalla queda libre. Para volver a entrar vas a necesitar tu código.'
            : 'Para volver a entrar vas a necesitar tu usuario y contraseña.',
        botones: [
          BotonTv(texto: 'Cancelar', principal: true, autofocus: true, alOk: () => Navigator.pop(contexto, false)),
          BotonTv(texto: 'Cerrar sesión', alOk: () => Navigator.pop(contexto, true)),
        ],
      ),
    );
    if (salir == true) await sesion.salir();
  }

  @override
  Widget build(BuildContext context) {
    final sesion = SesionScope.of(context);
    final biblioteca = DatosScope.of(context).biblioteca;
    final cliente = sesion.cliente;
    final perfil = sesion.perfil;
    final nombre = cliente?.nombre ?? perfil?.nombreCompleto ?? '';
    final vence = cliente?.vence;
    final dias = cliente?.diasRestantes;

    return ListenableBuilder(
      listenable: biblioteca,
      builder: (context, _) => Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const EncabezadoTv(sobretitulo: 'Perfil', titulo: 'Mi cuenta'),
          const SizedBox(height: 26),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: MargenTv.izquierda).copyWith(right: MargenTv.derecha),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  flex: 11,
                  child: _Tarjeta(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Container(
                              width: 92,
                              height: 92,
                              alignment: Alignment.center,
                              decoration: const BoxDecoration(color: Tono.celeste, shape: BoxShape.circle),
                              child: Text(
                                inicialesDe(nombre.isEmpty ? 'TV' : nombre),
                                style: const TextStyle(
                                  fontFamily: Letra.titulos,
                                  fontSize: 34,
                                  fontWeight: FontWeight.w800,
                                  color: Tono.sobreCelesteOscuro,
                                ),
                              ),
                            ),
                            const SizedBox(width: 24),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(nombre, maxLines: 1, overflow: TextOverflow.ellipsis, style: LetraTv.seccion),
                                  Text(
                                    cliente != null ? 'Cliente' : (perfil?.descripcionRol ?? ''),
                                    style: LetraTv.cuerpo,
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                        const Padding(
                          padding: EdgeInsets.symmetric(vertical: 26),
                          child: Divider(height: 1, color: Tono.capaMaxima),
                        ),
                        if (cliente != null) ...[
                          _Dato('Código de acceso', cliente.codigo),
                          _Dato(
                            'Servicio vigente hasta',
                            vence == null ? '—' : '${vence.day} de ${_meses[vence.month - 1]} de ${vence.year}',
                            alerta: dias != null && dias <= 3
                                ? (dias <= 0 ? 'Vence hoy: renovalo con tu vendedor.' : 'Quedan $dias día(s).')
                                : null,
                          ),
                          _Dato('Pantallas', '${cliente.conectados} de ${cliente.pantallas} en uso'),
                          if (cliente.vendedor.hayDatos)
                            _Dato(
                              'Tu vendedor',
                              [
                                cliente.vendedor.nombre,
                                cliente.vendedor.telefono,
                              ].where((d) => d.isNotEmpty).join(' · '),
                            ),
                        ] else
                          _Dato('Usuario del panel', perfil?.username ?? ''),
                        if (Aparato.version.isNotEmpty) _Dato('Versión de la app', Aparato.version),
                      ],
                    ),
                  ),
                ),
                const SizedBox(width: 30),
                Expanded(
                  flex: 9,
                  child: _Tarjeta(
                    child: FocusTraversalGroup(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          const Text('Preferencias', style: LetraTv.tarjeta),
                          const SizedBox(height: 18),
                          BotonTv(
                            texto: biblioteca.volverAlUltimo
                                ? 'Volver al último canal al abrir: Sí'
                                : 'Volver al último canal al abrir: No',
                            icono: biblioteca.volverAlUltimo ? Icons.toggle_on_rounded : Icons.toggle_off_rounded,
                            color: biblioteca.volverAlUltimo ? Tono.celeste : null,
                            autofocus: true,
                            ancho: double.infinity,
                            alOk: () => biblioteca.volverAlUltimo = !biblioteca.volverAlUltimo,
                          ),
                          const SizedBox(height: 14),
                          BotonTv(
                            texto: 'Administrar favoritos',
                            icono: Icons.favorite_rounded,
                            ancho: double.infinity,
                            alOk: () => NavegacionTv.of(context).irA(SeccionTv.favoritos),
                          ),
                          const SizedBox(height: 14),
                          BotonTv(
                            texto: 'Buscar actualizaciones',
                            icono: Icons.system_update_rounded,
                            ancho: double.infinity,
                            alOk: () => _buscarActualizacion(context),
                          ),
                          const SizedBox(height: 14),
                          BotonTv(
                            texto: 'Cerrar sesión',
                            icono: Icons.logout_rounded,
                            color: Tono.rubiClaro,
                            ancho: double.infinity,
                            alOk: () => _salir(context),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _Tarjeta extends StatelessWidget {
  const _Tarjeta({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(34),
      decoration: BoxDecoration(
        color: Tono.capaBaja,
        borderRadius: BorderRadius.circular(Curva.portada),
        border: Border.all(color: Tono.bordeSuave.withValues(alpha: .5)),
      ),
      child: child,
    );
  }
}

class _Dato extends StatelessWidget {
  const _Dato(this.titulo, this.valor, {this.alerta});

  final String titulo;
  final String valor;
  final String? alerta;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(titulo, style: LetraTv.ayuda.copyWith(fontSize: 16)),
          const SizedBox(height: 2),
          Text(
            valor,
            style: const TextStyle(
              fontFamily: Letra.texto,
              fontSize: 21,
              fontWeight: FontWeight.w700,
              color: Tono.texto,
            ),
          ),
          if (alerta != null) Text(alerta!, style: LetraTv.ayuda.copyWith(fontSize: 16, color: Tono.rubiClaro)),
        ],
      ),
    );
  }
}
