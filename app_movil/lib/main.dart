/// Punto de entrada de la app (como manage.py / wsgi.py en Django).
library;

import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';

import 'config.dart';
import 'pantallas/login.dart';
import 'pantallas/perfil.dart';
import 'pantallas/principal.dart';
import 'sesion.dart';
import 'tema.dart';
import 'widgets/comunes.dart';

/// Permite volver a la primera pantalla desde cualquier lado (ej: al vencer la sesión).
final claveNavegador = GlobalKey<NavigatorState>();

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  final sesion = Sesion();
  sesion.alSalir = () => claveNavegador.currentState?.popUntil((ruta) => ruta.isFirst);
  sesion.iniciar();
  runApp(SesionScope(sesion: sesion, child: const App()));
}

class App extends StatelessWidget {
  const App({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: nombreSistema,
      navigatorKey: claveNavegador,
      debugShowCheckedModeBanner: false,
      theme: temaDeLaApp(),
      // Textos de Flutter (calendario, copiar/pegar...) en español
      locale: const Locale('es', 'AR'),
      supportedLocales: const [Locale('es', 'AR'), Locale('es')],
      localizationsDelegates: GlobalMaterialLocalizations.delegates,
      home: const Raiz(),
    );
  }
}

/// Decide qué mostrar según la sesión (como el @login_required de Django).
class Raiz extends StatelessWidget {
  const Raiz({super.key});

  @override
  Widget build(BuildContext context) {
    final sesion = SesionScope.of(context);
    switch (sesion.estado) {
      case EstadoSesion.cargando:
        return const Scaffold(body: Center(child: CircularProgressIndicator()));
      case EstadoSesion.sinConexion:
        return Scaffold(
          body: SafeArea(
            child: Column(
              children: [
                Expanded(child: VistaError(mensaje: sesion.errorConexion ?? '', alReintentar: sesion.reintentar)),
                TextButton(onPressed: sesion.salir, child: const Text('Cerrar sesión e ingresar con otro servidor')),
                const SizedBox(height: 16),
              ],
            ),
          ),
        );
      case EstadoSesion.sinSesion:
        return const PantallaLogin();
      case EstadoSesion.conSesion:
        // Un administrador le asignó una contraseña temporal: primero tiene que cambiarla
        if (sesion.perfil!.debeCambiarPassword) {
          return const PantallaCambiarPassword(obligatorio: true);
        }
        return const PantallaPrincipal();
    }
  }
}
