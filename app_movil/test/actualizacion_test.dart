import 'package:app_movil/actualizacion.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('compara versiones número por número', () {
    expect(esMasNueva('1.1.0', '1.0.0'), isTrue);
    expect(esMasNueva('1.10.0', '1.9.3'), isTrue); // no alfabético
    expect(esMasNueva('2.0', '1.9.9'), isTrue);
    expect(esMasNueva('1.1.0', '1.1.0'), isFalse);
    expect(esMasNueva('1.0.9', '1.1.0'), isFalse); // la del servidor es más vieja
    expect(esMasNueva('1.1', '1.1.0'), isFalse);
    expect(esMasNueva('1.1.0+3', '1.1.0'), isFalse); // el +N no cuenta
    expect(esMasNueva('', '1.0.0'), isFalse);
  });
}
