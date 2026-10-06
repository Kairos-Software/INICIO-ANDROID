import 'package:app_movil/api/cliente.dart';
import 'package:app_movil/api/modelos.dart';
import 'package:app_movil/campos.dart';
import 'package:app_movil/senales.dart';
import 'package:app_movil/utiles.dart';
import 'package:app_movil/widgets/formulario.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:video_player/video_player.dart';

void main() {
  group('ApiError', () {
    test('lee el formato de error de la API', () {
      final error = ApiError.desdeRespuesta(400, {
        'codigo': 'datos_invalidos',
        'detalle': 'Revisá los datos enviados.',
        'campos': {
          'email': ['Ya existe un usuario con ese email.'],
          'general': ['Algo general.'],
        },
      });
      expect(error.codigo, 'datos_invalidos');
      expect(error.campo('email'), 'Ya existe un usuario con ese email.');
      expect(error.campo('username'), isNull);
      expect(error.general, 'Algo general.');
    });

    test('una respuesta que no es JSON se informa entendible', () {
      final error = ApiError.desdeRespuesta(500, null);
      expect(error.codigo, 'respuesta_invalida');
      expect(error.detalle, contains('500'));
    });

    test('401 es sesión vencida', () {
      expect(ApiError.desdeRespuesta(401, {'codigo': 'token_invalido', 'detalle': 'x'}).sesionVencida, isTrue);
    });
  });

  group('ApiCliente.direccion', () {
    final api = ApiCliente(urlBase: 'http://192.168.1.10:8000/api/v1');

    test('arma rutas relativas sobre la base', () {
      expect(api.direccion('usuarios/5/').toString(), 'http://192.168.1.10:8000/api/v1/usuarios/5/');
    });

    test('agrega los filtros que no están vacíos', () {
      final uri = api.direccion('usuarios/', {'q': 'ana', 'estado': ''});
      expect(uri.queryParameters, {'q': 'ana'});
    });

    test('respeta las direcciones completas de la paginación', () {
      const siguiente = 'http://192.168.1.10:8000/api/v1/usuarios/?pagina=2';
      expect(api.direccion(siguiente).toString(), siguiente);
    });
  });

  group('Modelos', () {
    test('Perfil y sus permisos', () {
      final perfil = Perfil({
        'id': 1,
        'username': 'ana',
        'first_name': 'Ana María',
        'es_superusuario': false,
        'permisos': ['ver_usuarios'],
        'permisos_por_modulo': [
          {
            'modulo': 'Usuarios',
            'permisos': ['Ver la lista'],
          },
        ],
      });
      expect(perfil.primerNombre, 'Ana');
      expect(perfil.puede('ver_usuarios'), isTrue);
      expect(perfil.puede('crear_usuarios'), isFalse);
      expect(perfil.permisosPorModulo.first.$1, 'Usuarios');
    });

    test('el superusuario puede todo', () {
      expect(Perfil({'id': 1, 'es_superusuario': true}).puede('lo_que_sea'), isTrue);
    });

    test('Pagina', () {
      final pagina = Pagina.desdeJson({
        'cantidad': 30,
        'siguiente': 'http://x/?pagina=2',
        'resultados': [
          {'id': 1, 'username': 'ana'},
        ],
      }, UsuarioResumen.new);
      expect(pagina.cantidad, 30);
      expect(pagina.resultados.single.username, 'ana');
      expect(pagina.siguiente, isNotNull);
    });
  });

  group('Formulario', () {
    test('devuelve lo cargado listo para la API', () {
      final datos = DatosFormulario(seccionesUsuario, {
        'first_name': 'Ana',
        'genero': 'femenino',
        'fecha_nacimiento': '1990-05-20',
        'rol': {'id': 3, 'nombre': 'Consulta'},
        'email': null,
      });
      datos.textos['telefono']!.text = ' 111 ';
      final valores = datos.valores();
      expect(valores['first_name'], 'Ana');
      expect(valores['telefono'], '111');
      expect(valores['genero'], 'femenino');
      expect(valores['fecha_nacimiento'], '1990-05-20');
      expect(valores['email'], '');
      expect(datos.rol, 3);
      expect(datos.textos['fecha_nacimiento']!.text, '20/05/1990');
      datos.liberar();
    });

    test('muestra los valores legibles', () {
      final filas = filasDeSeccion(seccionesPerfil.first, {
        'first_name': 'Ana',
        'genero': 'femenino',
        'genero_texto': 'Femenino',
        'fecha_nacimiento': '1990-05-20',
      });
      expect(filas, contains(('Género', 'Femenino')));
      expect(filas, contains(('Fecha de nacimiento', '20/05/1990')));
    });
  });

  test('Canales: solo se reproducen las fuentes HLS, en orden', () {
    final categoria = CategoriaCanales({
      'nombre': 'Noticias',
      'canales': [
        {
          'id': 1,
          'nombre': 'Canal 26',
          'numero': '26',
          'logo': 'https://logo/26.png',
          'fuentes': [
            {'id': 1, 'url': 'https://www.youtube.com/x/live', 'tipo': 'youtube'},
            {'id': 2, 'url': 'https://a/main.m3u8', 'tipo': 'hls'},
            {'id': 3, 'url': 'https://b/main.m3u8', 'tipo': 'hls'},
            {'id': 4, 'url': 'http://c:8080/u/p/1', 'tipo': 'directo'},
            {'id': 5, 'url': 'rtmp://d/vivo', 'tipo': 'rtmp'},
          ],
        },
      ],
    });
    final canal = categoria.canales.single;
    expect(canal.numero, '26');
    // RTMP no: la app no lo reproduce. YouTube y el video directo (IPTV) sí.
    expect(canal.fuentesReproducibles.map((f) => f.url), [
      'https://www.youtube.com/x/live',
      'https://a/main.m3u8',
      'https://b/main.m3u8',
      'http://c:8080/u/p/1',
    ]);
  });

  test('fechaLegible', () {
    expect(fechaLegible('2026-10-02'), '02/10/2026');
    expect(fechaLegible(null), '');
    expect(fechaLegible('2026-10-02T15:04:00'), '02/10/2026 15:04');
  });

  group('Clientes (login con código)', () {
    test('servicio vencido o suspendido se reconoce', () {
      expect(ApiError.desdeRespuesta(403, {'codigo': 'servicio_vencido', 'detalle': 'x'}).sinServicio, isTrue);
      expect(ApiError.desdeRespuesta(403, {'codigo': 'suspendido', 'detalle': 'x'}).sinServicio, isTrue);
      expect(ApiError.desdeRespuesta(403, {'codigo': 'sin_permiso', 'detalle': 'x'}).sinServicio, isFalse);
      expect(ApiError.desdeRespuesta(409, {'codigo': 'cuenta_en_uso', 'detalle': 'x'}).sinServicio, isFalse);
    });

    test('DatosCliente', () {
      final vence = DateTime.now().add(const Duration(days: 10, hours: 2));
      final cliente = DatosCliente({
        'nombre': 'Ana',
        'vence': vence.toUtc().toIso8601String(),
        'pantallas': 2,
        'conectados': 1,
      });
      expect(cliente.nombre, 'Ana');
      expect(cliente.pantallas, 2);
      expect(cliente.diasRestantes, 10);
      expect(DatosCliente({'nombre': 'Beto'}).vence, isNull);
    });
  });

  group('Señales', () {
    test('cada formato con su pista para el reproductor', () {
      expect(const Senal(url: 'https://x/a.m3u8', tipo: 'hls').formato, VideoFormat.hls);
      expect(const Senal(url: 'https://x/a.mpd', tipo: 'dash').formato, VideoFormat.dash);
      // Video directo (IPTV) y RTSP: sin pista, el reproductor lo detecta como VLC
      expect(const Senal(url: 'http://x:8080/u/p/1', tipo: 'directo').formato, isNull);
      expect(const Senal(url: 'rtsp://x/vivo', tipo: 'rtsp').formato, isNull);
    });

    test('las fuentes comunes no se resuelven: van tal cual', () async {
      final fuente = FuenteCanal({'id': 1, 'url': 'http://x:8080/u/p/1', 'tipo': 'directo', 'user_agent': 'VLC'});
      final senal = await resolverSenal(fuente, ApiCliente(urlBase: 'http://servidor/api/v1/'));
      expect((senal.url, senal.tipo), ('http://x:8080/u/p/1', 'directo'));
      expect(senal.cabeceras, {'User-Agent': 'VLC'});
    });
  });

  group('Fuentes', () {
    test('cabeceras para pedir el video', () {
      final fuente = FuenteCanal({
        'id': 1,
        'url': 'https://x/a.m3u8',
        'tipo': 'hls',
        'user_agent': 'Mozilla/5.0',
        'referer': '',
      });
      expect(fuente.cabeceras, {'User-Agent': 'Mozilla/5.0'});
      expect(FuenteCanal({'id': 2, 'url': 'https://x'}).cabeceras, isEmpty);
    });
  });
}
