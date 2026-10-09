// Pantalla verde en algunas TVs: si varios canales seguidos no andan, se sugiere reiniciar la TV.

import 'package:flutter_test/flutter_test.dart';

import 'package:app_movil/api/cliente.dart';
import 'package:app_movil/movil/control_senal.dart';

void main() {
  tearDown(() => ControlSenal.canalesSinAndar = 0);

  test('solo con un error y después de varios canales sin andar', () {
    final control = ControlSenal(ApiCliente(urlBase: 'http://prueba/api/v1/'));
    ControlSenal.canalesSinAndar = 5;
    expect(control.sugerirReiniciarAparato, isFalse); // sin error a la vista, no se dice nada
    control.error = 'No se pudo conectar con la señal.';
    ControlSenal.canalesSinAndar = 1;
    expect(control.sugerirReiniciarAparato, isFalse); // un canal caído es el canal, no la TV
    ControlSenal.canalesSinAndar = 2;
    expect(control.sugerirReiniciarAparato, isTrue);
    control.dispose();
  });
}
