import 'package:app_movil/config.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  // La app que se publica tiene que hablar SIEMPRE con producción (una vez
  // salió una versión apuntando a la PC y ningún aparato pudo conectarse)
  test('la versión de producción habla con el servidor de producción', () {
    expect(esVersionLocal, isFalse);
    expect(urlServidor, 'https://kairostv.grupokairosarg.com/api/v1/');
  });
}
