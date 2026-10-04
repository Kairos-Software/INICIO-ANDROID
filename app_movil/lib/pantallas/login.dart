import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../api/cliente.dart';
import '../config.dart';
import '../sesion.dart';
import '../tema.dart';
import '../widgets/comunes.dart';

/// Iniciar sesión, de dos formas:
///   - CÓDIGO (lo que se ve primero): los clientes ponen su código de 8
///     números (POST /api/v1/cliente/login/). Cómodo con el control remoto.
///   - USUARIO Y CONTRASEÑA: administradores y revendedores (POST /api/v1/login/,
///     el mismo login de la web: bloqueo por intentos fallidos, mantenimiento).
class PantallaLogin extends StatefulWidget {
  const PantallaLogin({super.key});

  @override
  State<PantallaLogin> createState() => _PantallaLoginState();
}

class _PantallaLoginState extends State<PantallaLogin> {
  final _usuario = TextEditingController();
  final _password = TextEditingController();
  final _codigo = TextEditingController();
  bool _conCodigo = true;
  bool _verPassword = false;
  bool _enviando = false;
  ApiError? _error;

  @override
  void initState() {
    super.initState();
    // El último código usado en este aparato, ya escrito (por si el cliente lo olvidó)
    _codigo.text = SesionScope.leer(context).ultimoCodigo;
  }

  @override
  void dispose() {
    _usuario.dispose();
    _password.dispose();
    _codigo.dispose();
    super.dispose();
  }

  Future<void> _ingresar() async {
    FocusScope.of(context).unfocus();
    setState(() {
      _enviando = true;
      _error = null;
    });
    try {
      final sesion = SesionScope.leer(context);
      if (_conCodigo) {
        await sesion.ingresarConCodigo(_codigo.text);
      } else {
        await sesion.ingresar(_usuario.text.trim(), _password.text);
      }
      // No hace falta navegar: la sesión avisa y main.dart muestra el sistema
    } on ApiError catch (error) {
      if (mounted) setState(() => _error = error);
    } finally {
      if (mounted) setState(() => _enviando = false);
    }
  }

  Future<void> _configurarServidor() async {
    final sesion = SesionScope.leer(context);
    final control = TextEditingController(text: sesion.urlServidor);
    final nueva = await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Servidor'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text(
              'Dirección de la API. En tu red, la IP de la PC donde corre Django; '
              'en producción, el dominio con https.',
              style: TextStyle(color: Colores.textoSuave, fontSize: 13),
            ),
            const SizedBox(height: 16),
            TextField(
              controller: control,
              keyboardType: TextInputType.url,
              autocorrect: false,
              decoration: const InputDecoration(hintText: 'http://192.168.1.50:8000/api/v1/'),
            ),
          ],
        ),
        actions: [
          TextButton(onPressed: () => control.text = urlServidorPorDefecto, child: const Text('Por defecto')),
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('Cancelar')),
          TextButton(onPressed: () => Navigator.pop(context, control.text), child: const Text('Guardar')),
        ],
      ),
    );
    if (nueva != null && nueva.trim().isNotEmpty) {
      await sesion.cambiarServidor(nueva);
      if (mounted) setState(() {});
    }
  }

  /// El código: solo números, hasta 8, grande (se ve bien en la TV).
  List<Widget> _campoCodigo() => [
    TextField(
      controller: _codigo,
      autofocus: true,
      keyboardType: TextInputType.number,
      inputFormatters: [FilteringTextInputFormatter.digitsOnly, LengthLimitingTextInputFormatter(8)],
      textAlign: TextAlign.center,
      style: const TextStyle(fontFamily: Letras.titulos, fontSize: 30, letterSpacing: 8, fontWeight: FontWeight.w700),
      decoration: const InputDecoration(hintText: '00000000', counterText: ''),
      textInputAction: TextInputAction.done,
      onSubmitted: (_) => _ingresar(),
    ),
    const SizedBox(height: 14),
  ];

  List<Widget> _camposUsuario() => [
    TextField(
      controller: _usuario,
      decoration: InputDecoration(
        labelText: 'Usuario o email',
        prefixIcon: const Icon(Icons.person_rounded),
        errorText: _error?.campo('username'),
      ),
      keyboardType: TextInputType.emailAddress,
      autocorrect: false,
      textInputAction: TextInputAction.next,
    ),
    const SizedBox(height: 14),
    TextField(
      controller: _password,
      obscureText: !_verPassword,
      decoration: InputDecoration(
        labelText: 'Contraseña',
        prefixIcon: const Icon(Icons.lock_rounded),
        errorText: _error?.campo('password'),
        suffixIcon: IconButton(
          icon: Icon(_verPassword ? Icons.visibility_off_rounded : Icons.visibility_rounded),
          onPressed: () => setState(() => _verPassword = !_verPassword),
        ),
      ),
      textInputAction: TextInputAction.done,
      onSubmitted: (_) => _ingresar(),
    ),
    Align(
      alignment: Alignment.centerRight,
      child: TextButton(
        onPressed: () => showDialog<void>(
          context: context,
          builder: (context) => AlertDialog(
            title: const Text('¿Olvidaste tu contraseña?'),
            content: const Text(
              'Por ahora se recupera desde la web: en el login, "¿Olvidaste tu contraseña?". '
              'Te llega un código por mail.',
            ),
            actions: [TextButton(onPressed: () => Navigator.pop(context), child: const Text('Entendido'))],
          ),
        ),
        child: const Text('¿Olvidaste tu contraseña?'),
      ),
    ),
  ];

  @override
  Widget build(BuildContext context) {
    final sesion = SesionScope.of(context);
    final errorDeCampo = _error?.campo('username') ?? _error?.campo('password');

    return Scaffold(
      // El fondo del login del panel: azul noche con brillos celeste y azul
      body: FondoMarca(
        child: SafeArea(
          child: Center(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(28),
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 420),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    const Center(child: MarcaKairos(tamanio: 76, vertical: true)),
                    const SizedBox(height: 40),
                    Text(_conCodigo ? 'Bienvenido' : 'Panel', style: estiloTitulo(28)),
                    Text(
                      _conCodigo
                          ? 'Ingresá el código de 8 números que te dio quien te vendió el servicio'
                          : 'Administradores y revendedores: usuario o email',
                      style: const TextStyle(color: Colores.textoSuave),
                    ),
                    const SizedBox(height: 24),
                    if (_error != null && (_conCodigo || errorDeCampo == null)) AvisoError(_error!.detalle),
                    if (_conCodigo) ..._campoCodigo() else ..._camposUsuario(),
                    const SizedBox(height: 8),
                    BotonDegradado(
                      texto: _conCodigo ? 'Entrar' : 'Ingresar',
                      icono: Icons.arrow_forward_rounded,
                      cargando: _enviando,
                      alTocar: _ingresar,
                    ),
                    const SizedBox(height: 12),
                    Center(
                      child: TextButton(
                        onPressed: () => setState(() {
                          _conCodigo = !_conCodigo;
                          _error = null;
                        }),
                        child: Text(_conCodigo ? 'Entrar con usuario y contraseña' : 'Entrar con código'),
                      ),
                    ),
                    const SizedBox(height: 40),
                    Center(
                      child: TextButton.icon(
                        onPressed: _configurarServidor,
                        icon: const Icon(Icons.dns_rounded, size: 16, color: Colores.textoSuave),
                        label: Text(
                          sesion.urlServidor,
                          style: const TextStyle(color: Colores.textoSuave, fontSize: 12),
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
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
