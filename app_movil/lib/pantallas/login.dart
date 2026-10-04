import 'package:flutter/material.dart';

import '../api/cliente.dart';
import '../config.dart';
import '../sesion.dart';
import '../tema.dart';
import '../widgets/comunes.dart';

/// Iniciar sesión. Usa POST /api/v1/login/ (el mismo login de la web:
/// usuario o email, bloqueo por intentos fallidos, modo mantenimiento).
class PantallaLogin extends StatefulWidget {
  const PantallaLogin({super.key});

  @override
  State<PantallaLogin> createState() => _PantallaLoginState();
}

class _PantallaLoginState extends State<PantallaLogin> {
  final _usuario = TextEditingController();
  final _password = TextEditingController();
  bool _verPassword = false;
  bool _enviando = false;
  ApiError? _error;

  @override
  void dispose() {
    _usuario.dispose();
    _password.dispose();
    super.dispose();
  }

  Future<void> _ingresar() async {
    FocusScope.of(context).unfocus();
    setState(() {
      _enviando = true;
      _error = null;
    });
    try {
      await SesionScope.leer(context).ingresar(_usuario.text.trim(), _password.text);
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

  @override
  Widget build(BuildContext context) {
    final sesion = SesionScope.of(context);
    final errorDeCampo = _error?.campo('username') ?? _error?.campo('password');

    return Scaffold(
      body: Stack(
        children: [
          // Brillos de color de fondo (los del logo, muy difuminados)
          const Positioned(top: -120, right: -100, child: _Brillo(color: Colores.violeta, tamanio: 320)),
          const Positioned(bottom: -140, left: -120, child: _Brillo(color: Colores.azul, tamanio: 360)),
          SafeArea(
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
                      const Text(
                        'Bienvenido',
                        style: TextStyle(fontSize: 26, fontWeight: FontWeight.w700, color: Colores.texto),
                      ),
                      const Text('Ingresá con tu usuario o email', style: TextStyle(color: Colores.textoSuave)),
                      const SizedBox(height: 24),
                      if (_error != null && errorDeCampo == null) AvisoError(_error!.detalle),
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
                              actions: [
                                TextButton(onPressed: () => Navigator.pop(context), child: const Text('Entendido')),
                              ],
                            ),
                          ),
                          child: const Text('¿Olvidaste tu contraseña?'),
                        ),
                      ),
                      const SizedBox(height: 8),
                      BotonDegradado(texto: 'Ingresar', icono: Icons.arrow_forward_rounded, cargando: _enviando, alTocar: _ingresar),
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
        ],
      ),
    );
  }
}

/// Un círculo de color muy difuminado (decoración del fondo).
class _Brillo extends StatelessWidget {
  const _Brillo({required this.color, required this.tamanio});

  final Color color;
  final double tamanio;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: tamanio,
      height: tamanio,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        gradient: RadialGradient(colors: [color.withValues(alpha: 0.35), color.withValues(alpha: 0)]),
      ),
    );
  }
}
