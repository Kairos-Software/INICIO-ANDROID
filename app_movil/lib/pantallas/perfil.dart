import 'package:flutter/material.dart';

import '../api/cliente.dart';
import '../api/modelos.dart';
import '../campos.dart';
import '../sesion.dart';
import '../tema.dart';
import '../utiles.dart';
import '../widgets/comunes.dart';
import '../widgets/formulario.dart';

/// "Mi perfil": mis datos, lo que puedo hacer, y los botones para editar,
/// cambiar la contraseña y salir.
class PantallaPerfil extends StatelessWidget {
  const PantallaPerfil({super.key});

  @override
  Widget build(BuildContext context) {
    final sesion = SesionScope.of(context);
    final perfil = sesion.perfil!;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Mi perfil'),
        actions: [
          IconButton(
            tooltip: 'Cerrar sesión',
            icon: const Icon(Icons.logout_rounded, color: Colores.peligro),
            onPressed: () => preguntarYSalir(context),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () async {
          try {
            await sesion.recargarPerfil();
          } catch (error) {
            if (context.mounted) mostrarMensaje(context, textoDeError(error), error: true);
          }
        },
        child: ListView(
          padding: const EdgeInsets.fromLTRB(20, 8, 20, 24),
          children: [
            Container(
              padding: const EdgeInsets.symmetric(vertical: 24, horizontal: 16),
              decoration: BoxDecoration(
                gradient: Degradados.encabezado,
                borderRadius: BorderRadius.circular(Radios.grande),
                border: Border.all(color: Colores.borde),
              ),
              child: Column(
                children: [
                  Avatar(iniciales: perfil.iniciales, foto: perfil.foto, radio: 44),
                  const SizedBox(height: 12),
                  Text(
                    perfil.nombreCompleto,
                    textAlign: TextAlign.center,
                    style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w700, color: Colores.texto),
                  ),
                  Text('@${perfil.username}', style: const TextStyle(color: Colores.textoSuave)),
                  const SizedBox(height: 10),
                  Etiqueta(perfil.descripcionRol),
                ],
              ),
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton.icon(
                    icon: const Icon(Icons.edit_outlined, size: 18),
                    label: const Text('Editar datos'),
                    onPressed: () => Navigator.push(
                      context,
                      MaterialPageRoute<void>(builder: (_) => const PantallaPerfilEditar()),
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: OutlinedButton.icon(
                    icon: const Icon(Icons.key_outlined, size: 18),
                    label: const Text('Contraseña'),
                    onPressed: () => Navigator.push(
                      context,
                      MaterialPageRoute<void>(builder: (_) => const PantallaCambiarPassword()),
                    ),
                  ),
                ),
              ],
            ),
            for (final seccion in [...seccionesPerfil, seccionPerfilSoloLectura]) ...[
              TituloSeccion(seccion.titulo),
              TarjetaDatos(filas: filasDeSeccion(seccion, perfil.datos)),
            ],
            const TituloSeccion('Lo que podés hacer'),
            _MisPermisos(perfil: perfil),
            const SizedBox(height: 24),
            OutlinedButton.icon(
              style: OutlinedButton.styleFrom(
                foregroundColor: Colores.peligro,
                side: BorderSide(color: Colores.peligro.withValues(alpha: 0.5)),
              ),
              icon: const Icon(Icons.logout_rounded),
              label: const Text('Cerrar sesión'),
              onPressed: () => preguntarYSalir(context),
            ),
            const SizedBox(height: 8),
            Text(
              'Servidor: ${sesion.urlServidor}',
              textAlign: TextAlign.center,
              style: const TextStyle(color: Colores.textoSuave, fontSize: 12),
            ),
          ],
        ),
      ),
    );
  }
}

class _MisPermisos extends StatelessWidget {
  const _MisPermisos({required this.perfil});

  final Perfil perfil;

  @override
  Widget build(BuildContext context) {
    if (perfil.esSuperusuario) {
      return const Card(
        child: ListTile(
          leading: Icon(Icons.verified_user_rounded, color: Colores.exito),
          title: Text('Superusuario: tenés todos los permisos.'),
        ),
      );
    }
    final modulos = perfil.permisosPorModulo;
    if (modulos.isEmpty) {
      return const Card(
        child: ListTile(title: Text('Por ahora solo podés gestionar tu propio perfil.')),
      );
    }
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            for (final (modulo, permisos) in modulos) ...[
              Text(modulo, style: const TextStyle(fontWeight: FontWeight.w600, color: Colores.celeste)),
              const SizedBox(height: 4),
              for (final permiso in permisos)
                Padding(
                  padding: const EdgeInsets.only(bottom: 4),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Icon(Icons.check_circle_rounded, size: 16, color: Colores.exito),
                      const SizedBox(width: 6),
                      Expanded(child: Text(permiso, style: const TextStyle(fontSize: 13))),
                    ],
                  ),
                ),
              const SizedBox(height: 8),
            ],
          ],
        ),
      ),
    );
  }
}

/// Editar mis datos (PATCH /api/v1/perfil/).
class PantallaPerfilEditar extends StatefulWidget {
  const PantallaPerfilEditar({super.key});

  @override
  State<PantallaPerfilEditar> createState() => _PantallaPerfilEditarState();
}

class _PantallaPerfilEditarState extends State<PantallaPerfilEditar> {
  late final DatosFormulario _datos = DatosFormulario(seccionesPerfil, SesionScope.leer(context).perfil!.datos);
  Map<String, List<Opcion>> _opciones = {};
  ApiError? _error;
  bool _guardando = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _cargarOpciones());
  }

  @override
  void dispose() {
    _datos.liberar();
    super.dispose();
  }

  Future<void> _cargarOpciones() async {
    try {
      final datos = await SesionScope.leer(context).api.get('perfil/opciones/') as Map<String, dynamic>;
      if (!mounted) return;
      setState(() => _opciones = {
            'genero': [for (final o in datos['genero'] as List) Opcion.desdeJson(o as Map<String, dynamic>)],
          });
    } catch (error) {
      if (mounted) mostrarMensaje(context, textoDeError(error), error: true);
    }
  }

  Future<void> _guardar() async {
    FocusScope.of(context).unfocus();
    final sesion = SesionScope.leer(context);
    setState(() {
      _guardando = true;
      _error = null;
    });
    try {
      final datos = await sesion.api.patch('perfil/', _datos.valores()) as Map<String, dynamic>;
      sesion.actualizarPerfil(Perfil(datos));
      if (!mounted) return;
      mostrarMensaje(context, 'Tus datos se guardaron.');
      Navigator.pop(context);
    } on ApiError catch (error) {
      if (mounted) setState(() => _error = error);
    } finally {
      if (mounted) setState(() => _guardando = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Editar mis datos')),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(20, 8, 20, 32),
        children: [
          if (_error != null) AvisoError(_error!.general ?? _error!.detalle),
          CamposFormulario(secciones: seccionesPerfil, datos: _datos, error: _error, opciones: _opciones),
          const SizedBox(height: 12),
          BotonDegradado(texto: 'Guardar', icono: Icons.check_rounded, cargando: _guardando, alTocar: _guardar),
        ],
      ),
    );
  }
}

/// Cambiar mi contraseña. Con `obligatorio`, es la pantalla que aparece
/// cuando un administrador te asignó una temporal (como en la web).
class PantallaCambiarPassword extends StatefulWidget {
  const PantallaCambiarPassword({super.key, this.obligatorio = false});

  final bool obligatorio;

  @override
  State<PantallaCambiarPassword> createState() => _PantallaCambiarPasswordState();
}

class _PantallaCambiarPasswordState extends State<PantallaCambiarPassword> {
  final _actual = TextEditingController();
  final _nueva = TextEditingController();
  final _repetir = TextEditingController();
  ApiError? _error;
  bool _guardando = false;

  @override
  void dispose() {
    _actual.dispose();
    _nueva.dispose();
    _repetir.dispose();
    super.dispose();
  }

  Future<void> _guardar() async {
    FocusScope.of(context).unfocus();
    final sesion = SesionScope.leer(context);
    setState(() {
      _guardando = true;
      _error = null;
    });
    try {
      await sesion.api.post('perfil/cambiar-password/', {
        'old_password': _actual.text,
        'new_password1': _nueva.text,
        'new_password2': _repetir.text,
      });
      await sesion.recargarPerfil();   // ya no "debe cambiarla": main.dart muestra el sistema
      if (!mounted) return;
      mostrarMensaje(context, 'Tu contraseña se cambió.');
      if (!widget.obligatorio) Navigator.pop(context);
    } on ApiError catch (error) {
      if (mounted) setState(() => _error = error);
    } finally {
      if (mounted) setState(() => _guardando = false);
    }
  }

  Widget _campo(TextEditingController control, String etiqueta, String nombre) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: TextField(
        controller: control,
        obscureText: true,
        decoration: InputDecoration(labelText: etiqueta, errorText: _error?.campo(nombre), errorMaxLines: 4),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Cambiar contraseña'),
        automaticallyImplyLeading: !widget.obligatorio,
        actions: [
          if (widget.obligatorio)
            TextButton(
              onPressed: () => SesionScope.leer(context).salir(),
              child: const Text('Salir', style: TextStyle(color: Colores.peligro)),
            ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          if (widget.obligatorio)
            const Padding(
              padding: EdgeInsets.only(bottom: 16),
              child: Text(
                'Antes de seguir, elegí tu propia contraseña: la que tenés fue asignada por un administrador.',
              ),
            ),
          if (_error != null && _error!.campos.isEmpty) AvisoError(_error!.detalle),
          if (_error?.general != null) AvisoError(_error!.general!),
          _campo(_actual, 'Contraseña actual', 'old_password'),
          _campo(_nueva, 'Contraseña nueva', 'new_password1'),
          _campo(_repetir, 'Repetir contraseña nueva', 'new_password2'),
          const SizedBox(height: 8),
          BotonDegradado(texto: 'Cambiar contraseña', icono: Icons.key_rounded, cargando: _guardando, alTocar: _guardar),
        ],
      ),
    );
  }
}
