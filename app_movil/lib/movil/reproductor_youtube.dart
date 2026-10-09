/// Películas y capítulos de canales OFICIALES de YouTube (fuentes "yt_video",
/// ver canales/youtube.py en el servidor): se ven en el reproductor de YouTube,
/// el mismo que insertan las páginas web, con su logo y su publicidad. No hace
/// falta cuenta, se ve en alta calidad y anda lo infantil (que YouTube no deja
/// sacar para verlo en otro reproductor).
///
/// La misma pantalla para el celular y la TV, siempre a pantalla completa:
///   - Celular: los controles de YouTube (tocar el video).
///   - TV, con el control remoto:
///       OK (o Play/Pausa): pausa / sigue.
///       Izquierda/Derecha: -10 s / +10 s.
///       Arriba/Abajo: muestra el título y por dónde va.
///       Atrás: sale.
///
/// Como el reproductor común: guarda por dónde va cada 5 s ("Continuar
/// viendo"), arranca desde ahí, suma a "Lo más visto", al terminar un capítulo
/// sigue con el próximo y, si YouTube no lo deja ver, le avisa al servidor.
///
/// El video se carga en un WebView con la "IFrame API" de YouTube. La página
/// se presenta como de kairostv.grupokairosarg.com: YouTube pide saber desde
/// qué sitio se inserta el video (si no, da "error 153").
library;

import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:wakelock_plus/wakelock_plus.dart';
import 'package:webview_flutter/webview_flutter.dart';
import 'package:webview_flutter_android/webview_flutter_android.dart';

import '../api/cliente.dart';
import '../api/modelos.dart';
import '../sesion.dart';
import 'componentes.dart' show reloj;
import 'datos.dart';
import 'estilo.dart';
import 'medidor.dart';

/// Desde qué sitio se inserta el video (YouTube lo exige).
const sitioDeKairos = 'https://kairostv.grupokairosarg.com';

/// La fuente de YouTube oficial de un canal, si es lo primero que puede ver este aparato.
FuenteCanal? fuenteDeYoutube(Canal canal) {
  final fuentes = canal.fuentesReproducibles;
  return fuentes.isNotEmpty && fuentes.first.tipo == 'yt_video' ? fuentes.first : null;
}

/// El id del video ("https://www.youtube.com/watch?v=abc" -> "abc").
String? idDeVideo(String direccion) {
  final uri = Uri.tryParse(direccion);
  if (uri == null) return null;
  final id = uri.host.endsWith('youtu.be') ? uri.pathSegments.firstOrNull : uri.queryParameters['v'];
  return id != null && RegExp(r'^[\w-]{11}$').hasMatch(id) ? id : null;
}

/// La página con el reproductor. [controles]: los de YouTube (celular) o ninguno (TV: se usa el control remoto).
@visibleForTesting
String paginaDelReproductor(String id, {required bool controles, Duration desde = Duration.zero}) {
  final opciones = jsonEncode({
    'autoplay': 1,
    'controls': controles ? 1 : 0,
    'playsinline': 1,
    'rel': 0,
    'fs': 0,
    'iv_load_policy': 3,
    'hl': 'es',
    'start': desde.inSeconds,
    'origin': sitioDeKairos,
  });
  return '''
<!DOCTYPE html>
<html><head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>html,body{margin:0;height:100%;background:#000;overflow:hidden}#video{position:absolute;inset:0;width:100%;height:100%}</style>
</head><body>
<div id="video"></div>
<script>
function avisar(datos) { Kairos.postMessage(JSON.stringify(datos)); }
var reproductor;
function onYouTubeIframeAPIReady() {
  reproductor = new YT.Player('video', {
    videoId: '$id', playerVars: $opciones,
    events: {
      onReady: function () { avisar({e: 'listo'}); reproductor.playVideo(); },
      onStateChange: function (ev) { avisar({e: 'estado', v: ev.data}); },
      onError: function (ev) { avisar({e: 'error', v: ev.data}); }
    }
  });
  setInterval(function () {
    if (reproductor && reproductor.getCurrentTime) {
      avisar({e: 'tiempo', t: reproductor.getCurrentTime() || 0, d: reproductor.getDuration() || 0});
    }
  }, 1000);
}
</script>
<script src="https://www.youtube.com/iframe_api"></script>
</body></html>''';
}

/// Lo que dice el reproductor de YouTube, en limpio (separado del WebView para poder probarlo).
class EstadoYoutube extends ChangeNotifier {
  // Los estados del reproductor de YouTube
  static const _termino = 0, _reproduciendo = 1, _cargando = 3;

  bool listo = false;
  int estado = -1;
  Duration posicion = Duration.zero;
  Duration duracion = Duration.zero;

  /// El error de YouTube (null = ninguno).
  int? error;

  bool get reproduciendo => estado == _reproduciendo;
  bool get cargando => !listo || estado == _cargando || estado == -1;
  bool get termino => estado == _termino;

  void recibir(String mensaje) {
    final Map<String, dynamic> datos;
    try {
      datos = jsonDecode(mensaje) as Map<String, dynamic>;
    } catch (_) {
      return;
    }
    switch (datos['e']) {
      case 'listo':
        listo = true;
      case 'estado':
        estado = (datos['v'] as num?)?.toInt() ?? estado;
      case 'error':
        error = (datos['v'] as num?)?.toInt() ?? 5;
      case 'tiempo':
        posicion = Duration(milliseconds: (((datos['t'] as num?) ?? 0) * 1000).round());
        duracion = Duration(milliseconds: (((datos['d'] as num?) ?? 0) * 1000).round());
      default:
        return;
    }
    notifyListeners();
  }

  /// El error de YouTube, en castellano.
  static String mensajeDe(int codigo) => switch (codigo) {
    100 => 'Este video ya no está en YouTube (lo borraron o es privado).',
    101 || 150 => 'El dueño de este video no deja verlo fuera de YouTube.',
    152 || 153 => 'YouTube no aceptó el reproductor (error $codigo).',
    5 => 'Este aparato no pudo reproducir el video.',
    _ => 'YouTube no pudo reproducir el video (error $codigo).',
  };

  /// Cómo se le avisa al servidor (ver MOTIVOS_DE_LOS_APARATOS en canales/servicios.py).
  static String motivoDe(int codigo) => switch (codigo) {
    100 || 101 || 150 => 'rechazo',
    5 => 'formato',
    _ => 'error',
  };
}

class PantallaYoutube extends StatefulWidget {
  const PantallaYoutube({super.key, required this.canal, required this.tv, this.serie, this.episodio, this.desde});

  final Canal canal;
  final bool tv;
  final Serie? serie;
  final Episodio? episodio;
  final Duration? desde;

  @override
  State<PantallaYoutube> createState() => _PantallaYoutubeState();
}

class _PantallaYoutubeState extends State<PantallaYoutube> {
  static const _sinRespuesta = Duration(seconds: 25);

  final _estado = EstadoYoutube();
  late final ApiCliente _api = SesionScope.leer(context).api;
  late Biblioteca _biblioteca;
  late Canal _canal = widget.canal;
  late Episodio? _episodio = widget.episodio;
  WebViewController? _web;
  Timer? _guardar;
  Timer? _vigia;
  Timer? _ocultarInfo;
  bool _info = true;
  bool _avisado = false;
  bool _siguienteLanzado = false;
  Duration _vistoDeEstaVez = Duration.zero;
  bool _vistaContada = false;
  Duration? _ultimaPosicion;

  @override
  void initState() {
    super.initState();
    WakelockPlus.enable();
    SystemChrome.setPreferredOrientations([DeviceOrientation.landscapeLeft, DeviceOrientation.landscapeRight]);
    SystemChrome.setEnabledSystemUIMode(SystemUiMode.immersiveSticky);
    _estado.addListener(_alCambiar);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _biblioteca = DatosScope.of(context).biblioteca;
      _abrir(_canal, widget.desde);
    });
    _guardar = Timer.periodic(const Duration(seconds: 5), (_) => _guardarProgreso());
    _mostrarInfo();
  }

  @override
  void dispose() {
    _guardarProgreso();
    _guardar?.cancel();
    _vigia?.cancel();
    _ocultarInfo?.cancel();
    _estado.removeListener(_alCambiar);
    unawaited(Medidor.enviar(_api));
    WakelockPlus.disable();
    SystemChrome.setPreferredOrientations([]);
    SystemChrome.setEnabledSystemUIMode(SystemUiMode.edgeToEdge);
    super.dispose();
  }

  void _abrir(Canal canal, Duration? desde) {
    final fuente = fuenteDeYoutube(canal);
    final id = fuente == null ? null : idDeVideo(fuente.url);
    _estado
      ..listo = false
      ..estado = -1
      ..error = id == null ? 2 : null
      ..posicion = Duration.zero
      ..duracion = Duration.zero;
    _avisado = false;
    _siguienteLanzado = false;
    _vistoDeEstaVez = Duration.zero;
    _vistaContada = false;
    _ultimaPosicion = null;
    if (id == null) {
      setState(() {});
      return;
    }
    final web = WebViewController(onPermissionRequest: (pedido) => pedido.deny())
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..setBackgroundColor(Colors.black)
      ..addJavaScriptChannel('Kairos', onMessageReceived: (mensaje) => _estado.recibir(mensaje.message))
      ..setNavigationDelegate(
        NavigationDelegate(
          // Que un toque en el logo o en "más videos" no saque al usuario a youtube.com dentro de la app
          onNavigationRequest: (pedido) => pedido.isMainFrame && !pedido.url.startsWith(sitioDeKairos)
              ? NavigationDecision.prevent
              : NavigationDecision.navigate,
        ),
      );
    final android = web.platform;
    if (android is AndroidWebViewController) {
      unawaited(android.setMediaPlaybackRequiresUserGesture(false)); // que arranque solo, con sonido
    }
    unawaited(web.loadHtmlString(paginaDelReproductor(id, controles: !widget.tv, desde: desde ?? Duration.zero),
        baseUrl: '$sitioDeKairos/'));
    _vigia?.cancel();
    _vigia = Timer(_sinRespuesta, () {
      if (mounted && !_estado.listo && _estado.error == null) {
        setState(() => _estado.error = -1); // no cargó: casi siempre es la conexión
      }
    });
    setState(() => _web = web);
  }

  void _alCambiar() {
    if (!mounted) return;
    _medir();
    final error = _estado.error;
    if (error != null && !_avisado && error > 0) {
      _avisado = true;
      final fuente = fuenteDeYoutube(_canal);
      if (fuente != null && error != 152 && error != 153) {
        _api
            .post('canales/fuentes/${fuente.id}/falla/', {
              'motivo': EstadoYoutube.motivoDe(error),
              'detalle': 'YouTube oficial: error $error',
            })
            .catchError((Object _) => null);
        if (error == 100 || error == 101 || error == 150) NoAnda.anotar(_canal, deFormato: false);
      }
    }
    if (_estado.termino && !_siguienteLanzado) {
      _siguienteLanzado = true;
      _guardarProgreso();
      final siguiente = _siguiente;
      if (siguiente != null && fuenteDeYoutube(siguiente.canal) != null) {
        setState(() {
          _episodio = siguiente;
          _canal = siguiente.canal;
        });
        _abrir(siguiente.canal, null);
        return;
      }
      _mostrarInfo();
    }
    if (!_estado.reproduciendo) _info = true;
    setState(() {});
  }

  /// Lo más visto: un segundo por cada aviso del reproductor mientras se ve.
  void _medir() {
    final anterior = _ultimaPosicion;
    _ultimaPosicion = _estado.posicion;
    if (!_estado.reproduciendo || anterior == null) return;
    final rato = _estado.posicion - anterior;
    if (rato <= Duration.zero || rato > const Duration(seconds: 3)) return; // saltó o recién arranca
    Medidor.sumar(_api, _canal.id, rato);
    _vistoDeEstaVez += rato;
    if (!_vistaContada && _vistoDeEstaVez >= Medidor.paraUnaVista) {
      _vistaContada = true;
      Medidor.contarVista(_canal.id);
    }
  }

  void _guardarProgreso() {
    if (_estado.duracion == Duration.zero) return;
    try {
      _biblioteca.guardarProgreso(
        _canal.id,
        _estado.termino ? _estado.duracion : _estado.posicion,
        _estado.duracion,
      );
    } catch (_) {
      // Todavía no estaba lista la biblioteca
    }
  }

  Episodio? get _siguiente {
    final serie = widget.serie;
    final actual = _episodio;
    if (serie == null || actual == null) return null;
    final episodios = serie.episodios;
    final indice = episodios.indexOf(actual);
    return indice >= 0 && indice + 1 < episodios.length ? episodios[indice + 1] : null;
  }

  void _mostrarInfo() {
    setState(() => _info = true);
    _ocultarInfo?.cancel();
    _ocultarInfo = Timer(const Duration(seconds: 4), () {
      if (mounted && _estado.reproduciendo) setState(() => _info = false);
    });
  }

  Future<void> _js(String codigo) async {
    try {
      await _web?.runJavaScript('if (reproductor) { $codigo }');
    } catch (_) {
      // El reproductor todavía no estaba
    }
  }

  void _alternarPausa() {
    unawaited(_js(_estado.reproduciendo ? 'reproductor.pauseVideo();' : 'reproductor.playVideo();'));
    _mostrarInfo();
  }

  void _saltar(int segundos) {
    final destino = _estado.posicion + Duration(seconds: segundos);
    final limite = _estado.duracion > Duration.zero ? _estado.duracion : destino;
    final segundo = (destino < Duration.zero ? Duration.zero : (destino > limite ? limite : destino)).inSeconds;
    unawaited(_js('reproductor.seekTo($segundo, true);'));
    setState(() => _estado.posicion = Duration(seconds: segundo));
    _mostrarInfo();
  }

  /// Las teclas del control remoto (solo en la TV).
  KeyEventResult _tecla(FocusNode _, KeyEvent evento) {
    if (evento is! KeyDownEvent && evento is! KeyRepeatEvent) return KeyEventResult.ignored;
    final tecla = evento.logicalKey;
    if (evento is KeyDownEvent &&
        (tecla == LogicalKeyboardKey.select ||
            tecla == LogicalKeyboardKey.enter ||
            tecla == LogicalKeyboardKey.mediaPlayPause ||
            tecla == LogicalKeyboardKey.mediaPlay ||
            tecla == LogicalKeyboardKey.mediaPause)) {
      _alternarPausa();
      return KeyEventResult.handled;
    }
    if (tecla == LogicalKeyboardKey.arrowLeft || tecla == LogicalKeyboardKey.mediaRewind) {
      _saltar(-10);
      return KeyEventResult.handled;
    }
    if (tecla == LogicalKeyboardKey.arrowRight || tecla == LogicalKeyboardKey.mediaFastForward) {
      _saltar(10);
      return KeyEventResult.handled;
    }
    if (tecla == LogicalKeyboardKey.arrowUp || tecla == LogicalKeyboardKey.arrowDown) {
      _mostrarInfo();
      return KeyEventResult.handled;
    }
    return KeyEventResult.ignored;
  }

  String get _titulo => widget.serie?.nombre ?? sinAnio(_canal.nombre);

  String get _subtitulo {
    final episodio = _episodio;
    if (episodio == null) return '';
    return '${episodio.codigo}${episodio.titulo.isEmpty ? '' : ' "${episodio.titulo}"'}';
  }

  @override
  Widget build(BuildContext context) {
    final web = _web;
    final error = _estado.error;
    Widget video = web == null ? const SizedBox.expand() : WebViewWidget(controller: web);
    // En la TV el video no recibe el foco ni toques: las teclas las maneja esta pantalla
    if (widget.tv) video = ExcludeFocus(child: IgnorePointer(child: video));

    return Focus(
      autofocus: true,
      onKeyEvent: widget.tv ? _tecla : null,
      child: Scaffold(
        backgroundColor: Colors.black,
        body: Stack(
          fit: StackFit.expand,
          children: [
            Center(child: AspectRatio(aspectRatio: 16 / 9, child: video)),
            if (error == null && _estado.cargando && !_estado.listo)
              const Center(child: CircularProgressIndicator(color: Tono.celeste)),
            if (error != null)
              _Falla(
                mensaje: error < 0
                    ? 'No se pudo cargar YouTube. Revisá la conexión a internet.'
                    : EstadoYoutube.mensajeDe(error),
                tv: widget.tv,
              ),
            if (widget.tv && error == null)
              AnimatedOpacity(
                opacity: _info ? 1 : 0,
                duration: const Duration(milliseconds: 200),
                child: _InfoTv(
                  titulo: _titulo,
                  subtitulo: _subtitulo,
                  estado: _estado,
                ),
              ),
          ],
        ),
      ),
    );
  }
}

/// No se pudo ver: el motivo y cómo salir.
class _Falla extends StatelessWidget {
  const _Falla({required this.mensaje, required this.tv});

  final String mensaje;
  final bool tv;

  @override
  Widget build(BuildContext context) {
    return ColoredBox(
      color: Colors.black,
      child: Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.error_outline_rounded, color: Tono.rubiClaro, size: 48),
              const SizedBox(height: 16),
              Text(
                mensaje,
                textAlign: TextAlign.center,
                style: const TextStyle(color: Tono.texto, fontSize: 18, fontWeight: FontWeight.w600),
              ),
              const SizedBox(height: 8),
              Text(
                tv ? 'Atrás: volver' : 'Tocá Atrás para volver',
                style: const TextStyle(color: Tono.textoApagado, fontSize: 14),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// TV: el título, por dónde va y qué hace cada tecla (abajo, sobre un degradé).
class _InfoTv extends StatelessWidget {
  const _InfoTv({required this.titulo, required this.subtitulo, required this.estado});

  final String titulo;
  final String subtitulo;
  final EstadoYoutube estado;

  @override
  Widget build(BuildContext context) {
    final total = estado.duracion.inMilliseconds;
    final fraccion = total == 0 ? 0.0 : (estado.posicion.inMilliseconds / total).clamp(0.0, 1.0);
    return IgnorePointer(
      child: Align(
        alignment: Alignment.bottomCenter,
        child: Container(
          width: double.infinity,
          padding: const EdgeInsets.fromLTRB(56, 48, 56, 28),
          decoration: const BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topCenter,
              end: Alignment.bottomCenter,
              colors: [Colors.transparent, Color(0xE6000000)],
            ),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(
                    estado.reproduciendo ? Icons.pause_rounded : Icons.play_arrow_rounded,
                    color: Tono.celeste,
                    size: 36,
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      subtitulo.isEmpty ? titulo : '$titulo · $subtitulo',
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(color: Tono.texto, fontSize: 24, fontWeight: FontWeight.w700),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 14),
              ClipRRect(
                borderRadius: BorderRadius.circular(99),
                child: LinearProgressIndicator(
                  value: fraccion,
                  minHeight: 6,
                  color: Tono.celeste,
                  backgroundColor: Tono.capaMaxima,
                ),
              ),
              const SizedBox(height: 8),
              Row(
                children: [
                  Text(reloj(estado.posicion), style: const TextStyle(color: Tono.celeste, fontSize: 16)),
                  const Spacer(),
                  const Text(
                    'OK: pausa · ← →: 10 s · Atrás: salir',
                    style: TextStyle(color: Tono.textoSuave, fontSize: 15),
                  ),
                  const Spacer(),
                  Text(reloj(estado.duracion), style: const TextStyle(color: Tono.texto, fontSize: 16)),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
