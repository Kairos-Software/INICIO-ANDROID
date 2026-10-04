import 'package:flutter/material.dart';

import '../api/cliente.dart';
import '../api/modelos.dart';
import '../campos.dart';
import '../sesion.dart';
import '../tema.dart';
import '../utiles.dart';
import '../widgets/comunes.dart';
import '../widgets/formulario.dart';
import 'usuario_formulario.dart';

/// El detalle de un usuario, con las acciones que tengas permitidas.
/// Devuelve `true` al volver si algo cambió (para que la lista se recargue).
class PantallaUsuarioDetalle extends StatefulWidget {
  const PantallaUsuarioDetalle({super.key, required this.id});

  final int id;

  @override
  State<PantallaUsuarioDetalle> createState() => _PantallaUsuarioDetalleState();
}

class _PantallaUsuarioDetalleState extends State<PantallaUsuarioDetalle> {
  UsuarioDetalle? _usuario;
  Object? _error;
  bool _huboCambios = false;

  ApiCliente get _api => SesionScope.leer(context).api;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _cargar());
  }

  Future<void> _cargar() async {
    setState(() => _error = null);
    try {
      final datos = await _api.get('usuarios/${widget.id}/') as Map<String, dynamic>;
      if (mounted) setState(() => _usuario = UsuarioDetalle(datos));
    } catch (error) {
      if (mounted) setState(() => _error = error);
    }
  }

  Future<void> _editar() async {
    final cambio = await Navigator.push<bool>(
      context,
      MaterialPageRoute(builder: (_) => PantallaUsuarioFormulario(usuario: _usuario)),
    );
    if (cambio == true) {
      _huboCambios = true;
      _cargar();
    }
  }

  Future<void> _cambiarEstado() async {
    final usuario = _usuario!;
    final activar = !usuario.activo;
    final ok = await confirmar(
      context,
      titulo: activar ? 'Activar usuario' : 'Desactivar usuario',
      mensaje: activar
          ? '${usuario.nombreCompleto} va a poder volver a ingresar.'
          : '${usuario.nombreCompleto} no va a poder ingresar (ni en la web ni en la app).',
      aceptar: activar ? 'Activar' : 'Desactivar',
      peligroso: !activar,
    );
    if (!ok) return;
    try {
      final datos = await _api.post('usuarios/${usuario.id}/estado/', {'activo': activar}) as Map<String, dynamic>;
      _huboCambios = true;
      if (!mounted) return;
      setState(() => _usuario = UsuarioDetalle(datos));
      mostrarMensaje(context, activar ? 'Usuario activado.' : 'Usuario desactivado.');
    } catch (error) {
      if (mounted) mostrarMensaje(context, textoDeError(error), error: true);
    }
  }

  Future<void> _eliminar() async {
    final usuario = _usuario!;
    final ok = await confirmar(
      context,
      titulo: 'Eliminar usuario',
      mensaje: '¿Eliminar a ${usuario.nombreCompleto} definitivamente? No se puede deshacer.',
      aceptar: 'Eliminar',
      peligroso: true,
    );
    if (!ok) return;
    try {
      await _api.delete('usuarios/${usuario.id}/');
      if (!mounted) return;
      mostrarMensaje(context, 'Usuario eliminado.');
      Navigator.pop(context, true);
    } catch (error) {
      if (mounted) mostrarMensaje(context, textoDeError(error), error: true);
    }
  }

  Future<void> _restablecerPassword() async {
    final cambiada = await showDialog<bool>(
      context: context,
      builder: (_) => _DialogoRestablecer(usuario: _usuario!, api: _api),
    );
    if (cambiada == true && mounted) {
      mostrarMensaje(context, 'Se asignó una contraseña nueva a ${_usuario!.nombreCompleto}.');
      _cargar();
    }
  }

  @override
  Widget build(BuildContext context) {
    final usuario = _usuario;
    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (yaSalio, _) {
        if (!yaSalio) Navigator.pop(context, _huboCambios);
      },
      child: Scaffold(
        appBar: AppBar(
          title: Text(usuario?.nombreCompleto ?? 'Usuario'),
          actions: [
            if (usuario != null && usuario.accion('editar'))
              IconButton(tooltip: 'Editar', icon: const Icon(Icons.edit_outlined), onPressed: _editar),
          ],
        ),
        body: _error != null
            ? VistaError(mensaje: textoDeError(_error!), alReintentar: _cargar)
            : usuario == null
                ? const Center(child: CircularProgressIndicator())
                : RefreshIndicator(onRefresh: _cargar, child: _contenido(usuario)),
      ),
    );
  }

  Widget _contenido(UsuarioDetalle usuario) {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Center(child: Avatar(iniciales: usuario.iniciales, foto: usuario.foto, radio: 40)),
        const SizedBox(height: 10),
        Text(
          usuario.nombreCompleto,
          textAlign: TextAlign.center,
          style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w800),
        ),
        const SizedBox(height: 6),
        Wrap(
          alignment: WrapAlignment.center,
          spacing: 6,
          runSpacing: 6,
          children: [
            Etiqueta(usuario.descripcionRol),
            usuario.activo ? const Etiqueta('Activo', color: Colores.exito) : const Etiqueta('Inactivo', color: Colores.peligro),
            if (usuario.debeCambiarPassword) const Etiqueta('Debe cambiar la contraseña', color: Colores.textoSuave),
          ],
        ),
        const SizedBox(height: 16),
        _Acciones(
          usuario: usuario,
          alCambiarEstado: _cambiarEstado,
          alRestablecer: _restablecerPassword,
          alEliminar: _eliminar,
        ),
        for (final seccion in seccionesUsuario) ...[
          TituloSeccion(seccion.titulo),
          TarjetaDatos(filas: filasDeSeccion(seccion, usuario.datos)),
        ],
        const TituloSeccion('Registro'),
        TarjetaDatos(filas: [
          ('Fecha de alta', fechaLegible(usuario.datos['date_joined'])),
          ('Último ingreso', fechaLegible(usuario.datos['last_login'])),
          ('Creado por', '${usuario.datos['creado_por'] ?? ''}'),
        ]),
      ],
    );
  }
}

class _Acciones extends StatelessWidget {
  const _Acciones({
    required this.usuario,
    required this.alCambiarEstado,
    required this.alRestablecer,
    required this.alEliminar,
  });

  final UsuarioDetalle usuario;
  final VoidCallback alCambiarEstado;
  final VoidCallback alRestablecer;
  final VoidCallback alEliminar;

  @override
  Widget build(BuildContext context) {
    final botones = [
      if (usuario.accion('editar'))
        OutlinedButton.icon(
          onPressed: alCambiarEstado,
          icon: Icon(usuario.activo ? Icons.block : Icons.check_circle_outline, size: 18),
          label: Text(usuario.activo ? 'Desactivar' : 'Activar'),
        ),
      if (usuario.accion('restablecer_password'))
        OutlinedButton.icon(
          onPressed: alRestablecer,
          icon: const Icon(Icons.key_outlined, size: 18),
          label: const Text('Contraseña'),
        ),
      if (usuario.accion('eliminar'))
        OutlinedButton.icon(
          style: OutlinedButton.styleFrom(foregroundColor: Colores.peligro),
          onPressed: alEliminar,
          icon: const Icon(Icons.delete_outline, size: 18),
          label: const Text('Eliminar'),
        ),
    ];
    if (botones.isEmpty) return const SizedBox.shrink();
    return Wrap(alignment: WrapAlignment.center, spacing: 8, runSpacing: 8, children: botones);
  }
}

/// Asignarle una contraseña nueva (`POST /usuarios/<id>/restablecer-password/`).
class _DialogoRestablecer extends StatefulWidget {
  const _DialogoRestablecer({required this.usuario, required this.api});

  final UsuarioDetalle usuario;
  final ApiCliente api;

  @override
  State<_DialogoRestablecer> createState() => _DialogoRestablecerState();
}

class _DialogoRestablecerState extends State<_DialogoRestablecer> {
  final _password1 = TextEditingController();
  final _password2 = TextEditingController();
  bool _obligarCambio = true;
  bool _guardando = false;
  ApiError? _error;

  @override
  void dispose() {
    _password1.dispose();
    _password2.dispose();
    super.dispose();
  }

  Future<void> _guardar() async {
    setState(() {
      _guardando = true;
      _error = null;
    });
    try {
      await widget.api.post('usuarios/${widget.usuario.id}/restablecer-password/', {
        'password1': _password1.text,
        'password2': _password2.text,
        'obligar_cambio': _obligarCambio,
      });
      if (mounted) Navigator.pop(context, true);
    } on ApiError catch (error) {
      if (mounted) setState(() => _error = error);
    } finally {
      if (mounted) setState(() => _guardando = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Contraseña nueva'),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text('Para ${widget.usuario.nombreCompleto}', style: const TextStyle(color: Colores.textoSuave)),
            const SizedBox(height: 16),
            if (_error != null && _error!.campos.isEmpty) AvisoError(_error!.detalle),
            TextField(
              controller: _password1,
              obscureText: true,
              decoration: InputDecoration(labelText: 'Contraseña nueva', errorText: _error?.campo('password1'), errorMaxLines: 4),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _password2,
              obscureText: true,
              decoration: InputDecoration(labelText: 'Repetir contraseña', errorText: _error?.campo('password2')),
            ),
            CheckboxListTile(
              contentPadding: EdgeInsets.zero,
              value: _obligarCambio,
              onChanged: (valor) => setState(() => _obligarCambio = valor ?? true),
              title: const Text('Pedirle que la cambie en su próximo ingreso', style: TextStyle(fontSize: 14)),
            ),
          ],
        ),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(context), child: const Text('Cancelar')),
        TextButton(
          onPressed: _guardando ? null : _guardar,
          child: const Text('Asignar', style: TextStyle(fontWeight: FontWeight.w700)),
        ),
      ],
    );
  }
}
