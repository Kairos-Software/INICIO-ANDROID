/// Configuración general de la app.
library;

import 'package:flutter/services.dart' show appFlavor;

/// Nombre que se muestra dentro de la app. El que aparece debajo del ícono
/// sale de android/app/build.gradle.kts (app_name de cada versión).
const String nombreSistema = 'Kairos TV';
const String nombreEmpresa = 'Kairos Software';

/// Hay dos versiones de la app (ver android/app/build.gradle.kts):
///   - produccion: la que se publica. SIEMPRE habla con el servidor de
///     producción; no se puede cambiar ni se muestra en ningún lado.
///   - local: "Kairos TV Local", para probar contra la PC. Por defecto la IP
///     de abajo; se puede cambiar al armarla:
///       flutter run --flavor local --dart-define=API_URL=http://192.168.1.50:8000/api/v1/
const bool esVersionLocal = appFlavor == 'local';

const String _servidorProduccion = 'https://kairostv.grupokairosarg.com/api/v1/';
const String _servidorLocal = String.fromEnvironment('API_URL', defaultValue: 'http://192.168.1.241:8000/api/v1/');

/// La dirección de la API con la que habla esta versión de la app.
const String urlServidor = esVersionLocal ? _servidorLocal : _servidorProduccion;

/// El nombre del aparato que se le informa al servidor está en aparato.dart.
