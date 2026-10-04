import 'package:flutter/material.dart';

import '../api/modelos.dart';
import '../sesion.dart';
import '../tema.dart';
import '../utiles.dart';
import '../widgets/barra_flotante.dart';
import '../widgets/comunes.dart';
import 'canales.dart';
import 'notificaciones.dart';
import 'perfil.dart';
import 'usuarios_lista.dart';

/// La estructura del sistema una vez logueado: la barra flotante de abajo
/// con las secciones. "TV" es la principal (los canales en vivo); "Usuarios"
/// solo aparece si tenés el permiso ver_usuarios.
class PantallaPrincipal extends StatefulWidget {
  const PantallaPrincipal({super.key});

  @override
  State<PantallaPrincipal> createState() => _PantallaPrincipalState();
}

class _PantallaPrincipalState extends State<PantallaPrincipal> {
  int _seccion = 0;
  int _noLeidas = 0;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _actualizarNoLeidas());
  }

  /// Cuántas notificaciones sin leer hay (el número rojo de "Avisos").
  Future<void> _actualizarNoLeidas() async {
    try {
      final datos = await SesionScope.leer(context)
          .api
          .get('notificaciones/', parametros: {'no_leidas': '1', 'por_pagina': '1'}) as Map<String, dynamic>;
      if (mounted) setState(() => _noLeidas = datos['no_leidas'] as int? ?? 0);
    } catch (_) {
      // Si falla, el número queda como estaba
    }
  }

  @override
  Widget build(BuildContext context) {
    final perfil = SesionScope.of(context).perfil!;
    final verUsuarios = perfil.puede('ver_usuarios');

    final secciones = <(ItemBarra, Widget)>[
      (
        const ItemBarra(icono: Icons.live_tv_outlined, iconoActivo: Icons.live_tv_rounded, etiqueta: 'TV'),
        const PantallaCanales(),
      ),
      (
        const ItemBarra(icono: Icons.home_outlined, iconoActivo: Icons.home_rounded, etiqueta: 'Inicio'),
        _Inicio(perfil: perfil, noLeidas: _noLeidas, irA: _irA),
      ),
      if (verUsuarios)
        (
          const ItemBarra(icono: Icons.group_outlined, iconoActivo: Icons.group_rounded, etiqueta: 'Usuarios'),
          const PantallaUsuarios(),
        ),
      (
        ItemBarra(
          icono: Icons.notifications_none_rounded,
          iconoActivo: Icons.notifications_rounded,
          etiqueta: 'Avisos',
          contador: _noLeidas,
        ),
        PantallaNotificaciones(alCambiar: (cantidad) => setState(() => _noLeidas = cantidad)),
      ),
      (
        const ItemBarra(icono: Icons.person_outline_rounded, iconoActivo: Icons.person_rounded, etiqueta: 'Perfil'),
        const PantallaPerfil(),
      ),
    ];
    final actual = _seccion.clamp(0, secciones.length - 1);

    return Scaffold(
      body: IndexedStack(index: actual, children: [for (final (_, pantalla) in secciones) pantalla]),
      bottomNavigationBar: BarraFlotante(
        items: [for (final (item, _) in secciones) item],
        seleccionado: actual,
        alElegir: (indice) {
          setState(() => _seccion = indice);
          _actualizarNoLeidas();
        },
      ),
    );
  }

  void _irA(String etiqueta) {
    final etiquetas = [
      'TV',
      'Inicio',
      if (SesionScope.leer(context).perfil!.puede('ver_usuarios')) 'Usuarios',
      'Avisos',
      'Perfil',
    ];
    setState(() => _seccion = etiquetas.indexOf(etiqueta));
  }
}

/// El inicio: saludo, tu cuenta y accesos rápidos.
class _Inicio extends StatelessWidget {
  const _Inicio({required this.perfil, required this.noLeidas, required this.irA});

  final Perfil perfil;
  final int noLeidas;
  final void Function(String etiqueta) irA;

  @override
  Widget build(BuildContext context) {
    final nombre = perfil.primerNombre.isNotEmpty ? perfil.primerNombre : perfil.username;
    return Scaffold(
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 24),
          children: [
            Row(
              children: [
                const MarcaKairos(tamanio: 34),
                const Spacer(),
                IconButton(
                  tooltip: 'Cerrar sesión',
                  icon: const Icon(Icons.logout_rounded, color: Colores.textoSuave),
                  onPressed: () => preguntarYSalir(context),
                ),
              ],
            ),
            const SizedBox(height: 20),
            // Tarjeta principal con degradé
            Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                gradient: Degradados.encabezado,
                borderRadius: BorderRadius.circular(Radios.grande),
                border: Border.all(color: Colores.borde),
              ),
              child: Row(
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(saludo(), style: const TextStyle(color: Colores.textoSuave)),
                        Text(
                          nombre,
                          style: estiloTitulo(28).copyWith(height: 1.2),
                        ),
                        const SizedBox(height: 10),
                        Etiqueta(perfil.descripcionRol),
                        if (perfil.ultimoIngreso != null) ...[
                          const SizedBox(height: 10),
                          Text(
                            'Último ingreso: ${fechaLegible(perfil.ultimoIngreso)}',
                            style: const TextStyle(color: Colores.textoSuave, fontSize: 12),
                          ),
                        ],
                      ],
                    ),
                  ),
                  Avatar(iniciales: perfil.iniciales, foto: perfil.foto, radio: 32),
                ],
              ),
            ),
            const TituloSeccion('Accesos rápidos'),
            GridView.count(
              crossAxisCount: 2,
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              mainAxisSpacing: 12,
              crossAxisSpacing: 12,
              childAspectRatio: 1.15,
              children: [
                _Acceso(icono: Icons.live_tv_rounded, titulo: 'TV en vivo', texto: 'Ver canales', alTocar: () => irA('TV')),
                if (perfil.puede('ver_usuarios'))
                  _Acceso(icono: Icons.group_rounded, titulo: 'Usuarios', texto: 'Ver y gestionar', alTocar: () => irA('Usuarios')),
                _Acceso(
                  icono: Icons.notifications_rounded,
                  titulo: 'Avisos',
                  texto: noLeidas > 0 ? '$noLeidas sin leer' : 'Al día',
                  alTocar: () => irA('Avisos'),
                ),
                _Acceso(icono: Icons.person_rounded, titulo: 'Mi perfil', texto: 'Datos y permisos', alTocar: () => irA('Perfil')),
                _Acceso(
                  icono: Icons.key_rounded,
                  titulo: 'Contraseña',
                  texto: 'Cambiarla',
                  alTocar: () => Navigator.push(
                    context,
                    MaterialPageRoute<void>(builder: (_) => const PantallaCambiarPassword()),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _Acceso extends StatelessWidget {
  const _Acceso({required this.icono, required this.titulo, required this.texto, required this.alTocar});

  final IconData icono;
  final String titulo;
  final String texto;
  final VoidCallback alTocar;

  @override
  Widget build(BuildContext context) {
    return Card(
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: alTocar,
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              IconoDegradado(icono),
              const Spacer(),
              Text(titulo, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 15, color: Colores.texto)),
              Text(texto, style: const TextStyle(color: Colores.textoSuave, fontSize: 12)),
            ],
          ),
        ),
      ),
    );
  }
}
