/// Configuración general de la app.
library;

/// Nombre que se muestra dentro de la app. El que aparece debajo del ícono
/// está en android/app/src/main/AndroidManifest.xml (android:label).
const String nombreSistema = 'Kairos TV';
const String nombreEmpresa = 'Kairos Software';

/// Dirección de la API por defecto. Se puede cambiar de dos formas:
///   - al compilar:  flutter run --dart-define=API_URL=http://192.168.1.50:8000/api/v1/
///   - desde la app: en el login, tocando "Servidor".
/// En producción será algo como https://midominio.com/api/v1/
const String urlServidorPorDefecto = String.fromEnvironment(
  'API_URL',
  defaultValue: 'http://192.168.1.241:8000/api/v1/',
);

/// El nombre del aparato que se le informa al servidor está en aparato.dart.
