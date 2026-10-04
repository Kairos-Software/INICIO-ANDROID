import 'package:flutter/material.dart';

import '../api/cliente.dart';
import '../api/modelos.dart';
import '../campos.dart';
import '../sesion.dart';
import '../utiles.dart';
import '../widgets/comunes.dart';
import '../widgets/formulario.dart';

/// Alta (sin `usuario`) o edición (con `usuario`) de un usuario.
/// Las validaciones las hace el servidor con el mismo formulario de la web;
/// acá solo se muestran los errores debajo de cada campo.
class PantallaUsuarioFormulario extends StatefulWidget {
  const PantallaUsuarioFormulario({super.key, this.usuario});

  final UsuarioDetalle? usuario;

  @override
  State<PantallaUsuarioFormulario> createState() => _PantallaUsuarioFormularioState();
}

class _PantallaUsuarioFormularioState extends State<PantallaUsuarioFormulario> {
  late final DatosFormulario _datos = DatosFormulario(seccionesUsuario, widget.usuario?.datos ?? {'pais': 'Argentina'});
  final _password1 = TextEditingController();
  final _password2 = TextEditingController();
  bool _debeCambiar = true;

  List<RolOpcion> _roles = [];
  Map<String, List<Opcion>> _opciones = {};
  bool _cargandoOpciones = true;
  ApiError? _error;
  bool _guardando = false;

  bool get _creando => widget.usuario == null;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _cargarOpciones());
  }

  @override
  void dispose() {
    _datos.liberar();
    _password1.dispose();
    _password2.dispose();
    super.dispose();
  }

  /// Roles, tipos de documento y géneros (GET /usuarios/opciones/).
  Future<void> _cargarOpciones() async {
    try {
      final datos = await SesionScope.leer(context).api.get('usuarios/opciones/') as Map<String, dynamic>;
      List<Opcion> lista(String clave) => [for (final o in datos[clave] as List) Opcion.desdeJson(o as Map<String, dynamic>)];
      if (!mounted) return;
      setState(() {
        _roles = [for (final r in datos['roles'] as List) RolOpcion(r as Map<String, dynamic>)];
        _opciones = {'tipo_documento': lista('tipo_documento'), 'genero': lista('genero')};
        _cargandoOpciones = false;
      });
    } catch (error) {
      if (!mounted) return;
      setState(() => _cargandoOpciones = false);
      mostrarMensaje(context, textoDeError(error), error: true);
    }
  }

  Future<void> _guardar() async {
    FocusScope.of(context).unfocus();
    final api = SesionScope.leer(context).api;
    final cuerpo = {..._datos.valores(), 'rol': _datos.rol};
    if (_creando) {
      cuerpo['password1'] = _password1.text;
      cuerpo['password2'] = _password2.text;
      cuerpo['debe_cambiar_password'] = _debeCambiar;
    }

    setState(() {
      _guardando = true;
      _error = null;
    });
    try {
      final datos = _creando
          ? await api.post('usuarios/', cuerpo) as Map<String, dynamic>
          : await api.patch('usuarios/${widget.usuario!.id}/', cuerpo) as Map<String, dynamic>;
      if (!mounted) return;
      final usuario = UsuarioDetalle(datos);
      final personalizado = usuario.rolId == null;
      mostrarMensaje(
        context,
        _creando
            ? 'Usuario ${usuario.username} creado.${personalizado ? ' Elegí sus permisos desde la web.' : ''}'
            : 'Cambios guardados.',
      );
      Navigator.pop(context, true);
    } on ApiError catch (error) {
      if (!mounted) return;
      setState(() => _error = error);
      mostrarMensaje(context, error.detalle, error: true);
    } finally {
      if (mounted) setState(() => _guardando = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(_creando ? 'Nuevo usuario' : 'Editar usuario')),
      body: _cargandoOpciones
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.fromLTRB(20, 8, 20, 32),
              children: [
                if (_error?.general != null) AvisoError(_error!.general!),
                if (_error != null && _error!.campos.isEmpty) AvisoError(_error!.detalle),
                CamposFormulario(
                  secciones: seccionesUsuario,
                  datos: _datos,
                  error: _error,
                  opciones: _opciones,
                  roles: _roles,
                ),
                if (_creando) ...[
                  const TituloSeccion('Contraseña inicial'),
                  TextField(
                    controller: _password1,
                    obscureText: true,
                    decoration: InputDecoration(
                      labelText: 'Contraseña inicial',
                      helperText: 'Puede ser cualquiera: es solo para su primer ingreso.',
                      errorText: _error?.campo('password1'),
                    ),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: _password2,
                    obscureText: true,
                    decoration: InputDecoration(labelText: 'Repetir contraseña inicial', errorText: _error?.campo('password2')),
                  ),
                  SwitchListTile(
                    contentPadding: EdgeInsets.zero,
                    value: _debeCambiar,
                    onChanged: (valor) => setState(() => _debeCambiar = valor),
                    title: const Text('Pedirle que elija su propia contraseña en el primer ingreso'),
                  ),
                ],
                const SizedBox(height: 16),
                BotonDegradado(
                  texto: _creando ? 'Crear usuario' : 'Guardar cambios',
                  icono: _creando ? Icons.person_add_alt_1_rounded : Icons.check_rounded,
                  cargando: _guardando,
                  alTocar: _guardar,
                ),
              ],
            ),
    );
  }
}
