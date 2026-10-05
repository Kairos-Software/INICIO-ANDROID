/// De una fuente a la dirección que puede abrir el reproductor.
///
/// La mayoría de las fuentes ya son la dirección del video (HLS, DASH, video
/// directo, RTSP). Dos tipos no:
///
///   - "youtube": se resuelve ACÁ, en el aparato. Las direcciones de video de
///     YouTube quedan atadas a la IP de quien las pidió: si las pidiera el
///     servidor, al celular le darían error. En un vivo se usa su lista HLS;
///     en un video común, la versión con audio y video juntos.
///   - "pagina" (Twitch, Dailymotion, Vimeo...): se la pide al servidor
///     (`GET canales/fuentes/<id>/resolver/`), que la averigua con yt-dlp.
///
/// Las direcciones resueltas duran un rato: se piden cada vez que se va a
/// reproducir, nunca se guardan.
///
/// OJO con YouTube: le responde "demasiados pedidos" (error 429) al cliente
/// de red de Dart, aunque se presente como navegador (probado: el mismo
/// pedido con curl o Python da 200). Por eso en Android se le habla con
/// Cronet, el motor de red de Chrome (el mismo de la app oficial de YouTube).
/// Si el aparato no lo tiene (TV boxes sin servicios de Google), se usa el común.
library;

import 'dart:io' show Platform;

import 'package:cronet_http/cronet_http.dart';
import 'package:http/http.dart' as http;
import 'package:video_player/video_player.dart';
import 'package:youtube_explode_dart/youtube_explode_dart.dart';

import 'api/cliente.dart';
import 'api/modelos.dart';

/// Lo que necesita el reproductor para abrir una señal.
class Senal {
  const Senal({required this.url, required this.tipo, this.cabeceras = const {}});

  final String url;

  /// hls, dash, directo o rtsp.
  final String tipo;
  final Map<String, String> cabeceras;

  /// Cómo tiene que leer la señal el reproductor. Hace falta decírselo: las
  /// listas IPTV suelen tener direcciones sin extensión (".../usuario/clave/123")
  /// y por la dirección sola no se sabe si es HLS o video directo.
  ///   - hls / dash: listas que van pidiendo pedacitos de video.
  ///   - directo (MPEG-TS, MP4...): sin pista, el reproductor lo lee tal cual
  ///     llega (como hace VLC).
  ///   - rtsp: lo reconoce solo por el "rtsp://" del principio.
  VideoFormat? get formato => switch (tipo) {
    'hls' => VideoFormat.hls,
    'dash' => VideoFormat.dash,
    _ => null,
  };
}

/// No se pudo sacar la dirección del video (el mensaje dice por qué).
class SenalNoDisponible implements Exception {
  const SenalNoDisponible(this.mensaje);

  final String mensaje;

  @override
  String toString() => mensaje;
}

/// La señal de una fuente, lista para el reproductor.
Future<Senal> resolverSenal(FuenteCanal fuente, ApiCliente api) async {
  switch (fuente.tipo) {
    case 'youtube':
      return resolverYoutube(fuente.url);
    case 'pagina':
      final datos = await api.get('canales/fuentes/${fuente.id}/resolver/') as Map<String, dynamic>;
      return Senal(
        url: '${datos['url']}',
        tipo: '${datos['tipo'] ?? 'directo'}',
        cabeceras: {for (final e in (datos['cabeceras'] as Map? ?? {}).entries) '${e.key}': '${e.value}'},
      );
    default:
      return Senal(url: fuente.url, tipo: fuente.tipo, cabeceras: fuente.cabeceras);
  }
}

/// YouTube, resuelto en el aparato.
/// Sirve para un video (youtube.com/watch?v=..., youtu.be/...) o para el vivo
/// de un canal (youtube.com/@canal/live, /c/..., /user/..., /channel/...).
Future<Senal> resolverYoutube(String direccion) async {
  final cliente = _clienteParaYoutube();
  final yt = YoutubeExplode(httpClient: YoutubeHttpClient(cliente));
  try {
    final id = VideoId.parseVideoId(direccion) ?? await _videoDelVivo(direccion, cliente);
    if (id == null) throw const SenalNoDisponible('El canal no está transmitiendo en vivo ahora.');
    final video = await yt.videos.get(id);
    if (video.isLive) {
      final lista = await yt.videos.streams.getHttpLiveStreamUrl(VideoId(id));
      return Senal(url: lista, tipo: 'hls');
    }
    final manifiesto = await yt.videos.streams.getManifest(id);
    if (manifiesto.muxed.isNotEmpty) {
      return Senal(url: manifiesto.muxed.withHighestBitrate().url.toString(), tipo: 'directo');
    }
    if (manifiesto.hls.isNotEmpty) {
      return Senal(url: manifiesto.hls.first.url.toString(), tipo: 'hls');
    }
    throw const SenalNoDisponible('YouTube no entregó una versión que se pueda reproducir.');
  } finally {
    yt.close();
    cliente.close();
  }
}

/// Cronet (el motor de red de Chrome) en Android; si no está, el cliente común.
http.Client _clienteParaYoutube() {
  if (Platform.isAndroid) {
    try {
      return CronetClient.fromCronetEngine(CronetEngine.build(), closeEngine: true);
    } catch (_) {
      // Sin Cronet en este aparato: se intenta igual con el común
    }
  }
  return http.Client();
}

/// El video que está transmitiendo en vivo un canal de YouTube ahora (o null).
/// La página ".../live" de un canal, si está en vivo, dice cuál es el video.
Future<String?> _videoDelVivo(String direccion, http.Client cliente) async {
  var pagina = Uri.parse(direccion);
  if (!pagina.path.endsWith('/live')) {
    pagina = pagina.replace(path: '${pagina.path.replaceAll(RegExp(r'/+$'), '')}/live');
  }
  final respuesta = await cliente.get(
    pagina,
    headers: {
      'User-Agent': 'Mozilla/5.0 (Linux; Android 14; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36',
      'Accept-Language': 'es-AR,es;q=0.9',
      'Cookie': 'CONSENT=YES+1', // evita la página de "aceptar cookies"
    },
  );
  final canonica = RegExp(r'<link rel="canonical" href="https://www\.youtube\.com/watch\?v=([\w-]{11})"')
      .firstMatch(respuesta.body);
  return canonica?.group(1);
}
