import 'package:flutter/material.dart';

import '../api/modelos.dart';
import '../sesion.dart';
import '../tema.dart';
import '../utiles.dart';
import '../widgets/lista_paginada.dart';

/// Mis notificaciones (la campanita de la web).
class PantallaNotificaciones extends StatefulWidget {
  const PantallaNotificaciones({super.key, required this.alCambiar});

  /// Avisa cuántas quedan sin leer, para el número de la barra de abajo.
  final void Function(int noLeidas) alCambiar;

  @override
  State<PantallaNotificaciones> createState() => _PantallaNotificacionesState();
}

class _PantallaNotificacionesState extends State<PantallaNotificaciones> {
  final _lista = GlobalKey<ListaPaginadaState<Notificacion>>();

  Future<Pagina<Notificacion>> _cargar(String? siguiente) async {
    final datos = await SesionScope.leer(context).api.get(siguiente ?? 'notificaciones/') as Map<String, dynamic>;
    return Pagina.desdeJson(datos, Notificacion.new);
  }

  Future<void> _abrir(Notificacion notificacion) async {
    final api = SesionScope.leer(context).api;
    if (!notificacion.leida) {
      try {
        await api.post('notificaciones/${notificacion.id}/leida/');
        _lista.currentState?.recargar();
      } catch (_) {
        // Si no se pudo marcar, igual se muestra
      }
    }
    if (!mounted) return;
    await showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      builder: (context) => Padding(
        padding: const EdgeInsets.fromLTRB(24, 0, 24, 32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(notificacion.titulo, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
            const SizedBox(height: 4),
            Text(fechaLegible(notificacion.creada), style: const TextStyle(color: Colores.textoSuave, fontSize: 12)),
            if (notificacion.mensaje.isNotEmpty) ...[const SizedBox(height: 16), Text(notificacion.mensaje)],
          ],
        ),
      ),
    );
  }

  Future<void> _marcarTodas() async {
    try {
      await SesionScope.leer(context).api.post('notificaciones/marcar-todas/');
      _lista.currentState?.recargar();
    } catch (error) {
      if (mounted) mostrarMensaje(context, textoDeError(error), error: true);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Avisos'),
        actions: [
          IconButton(tooltip: 'Marcar todas como leídas', icon: const Icon(Icons.done_all), onPressed: _marcarTodas),
        ],
      ),
      body: ListaPaginada<Notificacion>(
        key: _lista,
        cargar: _cargar,
        mensajeVacio: 'No tenés notificaciones.',
        alCargar: (pagina) => widget.alCambiar(pagina.extra['no_leidas'] as int? ?? 0),
        item: (context, n) => Card(
          child: ListTile(
            onTap: () => _abrir(n),
            leading: Icon(_icono(n.nivel), color: _color(n.nivel)),
            title: Text(
              n.titulo,
              style: TextStyle(
                fontWeight: n.leida ? FontWeight.w400 : FontWeight.w600,
                color: n.leida ? Colores.textoSuave : Colores.texto,
              ),
            ),
            subtitle: Text(
              [if (n.mensaje.isNotEmpty) n.mensaje, haceCuanto(n.creada)].join('\n'),
              maxLines: 3,
              overflow: TextOverflow.ellipsis,
            ),
            trailing: n.leida
                ? null
                : Container(
                    width: 10,
                    height: 10,
                    decoration: const BoxDecoration(gradient: Degradados.principal, shape: BoxShape.circle),
                  ),
          ),
        ),
      ),
    );
  }

  IconData _icono(String nivel) => switch (nivel) {
    'exito' => Icons.check_circle_outline,
    'aviso' => Icons.warning_amber_outlined,
    'error' => Icons.error_outline,
    _ => Icons.info_outline,
  };

  Color _color(String nivel) => switch (nivel) {
    'exito' => Colores.exito,
    'aviso' => Colores.aviso,
    'error' => Colores.peligro,
    _ => Colores.celeste,
  };
}
