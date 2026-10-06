// Los reproductores de la TV manejados con el control remoto. El video es "de
// mentira" (_VideoDeMentira): dice que arrancó y no muestra nada, así se
// prueba el manejo sin un reproductor de verdad.
import 'dart:async';

import 'package:app_movil/api/modelos.dart';
import 'package:app_movil/movil/datos.dart';
import 'package:app_movil/sesion.dart';
import 'package:app_movil/tv/reproductor.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:video_player_platform_interface/video_player_platform_interface.dart';

class _VideoDeMentira extends VideoPlayerPlatform {
  var _proximo = 0;
  final _eventos = <int, StreamController<VideoEvent>>{};

  @override
  Future<void> init() async {}

  @override
  Future<int?> createWithOptions(VideoCreationOptions options) async {
    final id = _proximo++;
    _eventos[id] = StreamController<VideoEvent>();
    return id;
  }

  @override
  Stream<VideoEvent> videoEventsFor(int playerId) {
    final eventos = _eventos[playerId]!;
    scheduleMicrotask(
      () => eventos.add(
        VideoEvent(
          eventType: VideoEventType.initialized,
          duration: const Duration(minutes: 90),
          size: const Size(1920, 1080),
        ),
      ),
    );
    return eventos.stream;
  }

  @override
  Future<void> dispose(int playerId) async => _eventos.remove(playerId)?.close();

  @override
  Future<void> play(int playerId) async {}

  @override
  Future<void> pause(int playerId) async {}

  @override
  Future<void> setLooping(int playerId, bool looping) async {}

  @override
  Future<void> setVolume(int playerId, double volume) async {}

  @override
  Future<void> setPlaybackSpeed(int playerId, double speed) async {}

  @override
  Future<void> seekTo(int playerId, Duration position) async {}

  @override
  Future<Duration> getPosition(int playerId) async => Duration.zero;

  @override
  Future<void> setMixWithOthers(bool mixWithOthers) async {}

  @override
  Widget buildViewWithOptions(VideoViewOptions options) => const SizedBox.expand();
}

Canal _canal(int id, String nombre) => Canal({
  'id': id,
  'nombre': nombre,
  'fuentes': [
    {'id': id, 'url': 'https://x/$id.m3u8', 'tipo': 'hls', 'codec': 'h264'},
  ],
}, categoria: 'Noticias');

final _canales = [_canal(1, 'Canal 26'), _canal(2, 'Telemax'), _canal(3, 'A24')];

Future<void> _abrir(WidgetTester tester, Widget reproductor) async {
  tester.view.physicalSize = const Size(1920, 1080);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.reset);
  VideoPlayerPlatform.instance = _VideoDeMentira();
  final catalogo = Catalogo(Sesion().api)
    ..categoriasEnVivo = [
      CategoriaCanales({
        'nombre': 'Noticias',
        'canales': [
          for (final c in _canales) {'id': c.id, 'nombre': c.nombre, 'fuentes': <dynamic>[]},
        ],
      }),
    ]
    ..cargado = true;
  await tester.pumpWidget(
    SesionScope(
      sesion: Sesion(),
      child: DatosScope(
        catalogo: catalogo,
        biblioteca: Biblioteca(),
        child: MaterialApp(
          home: Builder(
            builder: (context) => Center(
              child: TextButton(
                onPressed: () => Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => reproductor)),
                child: const Text('abrir'),
              ),
            ),
          ),
        ),
      ),
    ),
  );
  await tester.tap(find.text('abrir'));
  await _pasar(tester);
}

String? _enfocado() => FocusManager.instance.primaryFocus?.debugLabel;

Future<void> _tecla(WidgetTester tester, LogicalKeyboardKey tecla) async {
  await tester.sendKeyEvent(tecla);
  await _pasar(tester);
}

/// "Atrás" del control.
Future<void> _atras(WidgetTester tester) async {
  await tester.binding.handlePopRoute();
  await _pasar(tester);
}

void main() {
  testWidgets('en vivo: el cartel solo informa y Atrás sale directo', (tester) async {
    await _abrir(tester, ReproductorVivoTv(canal: _canales[0], lista: _canales));
    expect(find.textContaining('OK: guía'), findsOneWidget); // el cartel con la ayuda
    expect(_enfocado(), 'reproductor'); // no le robó el foco a nadie
    await _atras(tester);
    expect(find.text('abrir'), findsOneWidget); // salió con un solo "Atrás"
  });

  testWidgets('en vivo: OK abre la guía en el canal actual, Abajo + OK cambia de canal', (tester) async {
    await _abrir(tester, ReproductorVivoTv(canal: _canales[0], lista: _canales));
    await _tecla(tester, LogicalKeyboardKey.select);
    expect(find.text('GUÍA DE CANALES'), findsOneWidget);
    expect(_enfocado(), 'guía: canal actual');
    await _tecla(tester, LogicalKeyboardKey.arrowDown);
    await _tecla(tester, LogicalKeyboardKey.select); // elige Telemax
    expect(find.text('GUÍA DE CANALES'), findsNothing);
    expect(find.text('Telemax'), findsOneWidget); // el cartel del canal nuevo
    expect(_enfocado(), 'reproductor');
  });

  testWidgets('en vivo: Atrás cierra la guía; las opciones toman el foco y se cierran solas', (tester) async {
    await _abrir(tester, ReproductorVivoTv(canal: _canales[0], lista: _canales));
    await _tecla(tester, LogicalKeyboardKey.select);
    await _atras(tester);
    expect(find.text('GUÍA DE CANALES'), findsNothing);
    expect(find.text('abrir'), findsNothing); // no salió: solo cerró la guía

    await _tecla(tester, LogicalKeyboardKey.arrowRight);
    expect(_enfocado(), 'opciones: guía'); // el foco ya está en el primer botón
    await tester.pump(const Duration(seconds: 6));
    await _pasar(tester);
    expect(_enfocado(), 'reproductor'); // se cerraron solas

    await _tecla(tester, LogicalKeyboardKey.arrowUp); // zapping
    expect(find.text('Telemax'), findsOneWidget);
  });

  testWidgets('película: OK pausa y deja el foco en Pausa; Atrás esconde la barra y después sale', (tester) async {
    await _abrir(tester, ReproductorVodTv(canal: _canal(9, 'Matrix (1999)')));
    expect(_enfocado(), 'reproductor');
    await _tecla(tester, LogicalKeyboardKey.select);
    expect(_enfocado(), 'pausa');
    await _atras(tester);
    expect(_enfocado(), 'reproductor'); // escondió la barra
    expect(find.text('abrir'), findsNothing);

    await _tecla(tester, LogicalKeyboardKey.arrowRight); // adelanta: la barra queda en la línea de tiempo
    expect(_enfocado(), 'línea de tiempo');
    await _atras(tester);
    await _atras(tester);
    expect(find.text('abrir'), findsOneWidget);
  });
}

/// Unos cuadros (300 ms). Sin pumpAndSettle: dejaría correr el reloj mientras
/// el video se actualiza, y los carteles se esconderían antes de mirarlos.
Future<void> _pasar(WidgetTester tester) async {
  for (var i = 0; i < 3; i++) {
    await tester.pump(const Duration(milliseconds: 100));
  }
}
