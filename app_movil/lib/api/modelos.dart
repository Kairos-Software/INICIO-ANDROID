/// Los datos que devuelve la API, convertidos a clases de Dart.
///
/// Son el "espejo" de los serializers de Django (api/v1/serializers.py):
/// cada clase lee el JSON y lo deja cómodo para las pantallas.
library;

/// Una página de un listado: {"cantidad", "siguiente", "resultados": [...]}.
class Pagina<T> {
  Pagina({required this.cantidad, required this.resultados, this.siguiente, this.extra = const {}});

  factory Pagina.desdeJson(Map<String, dynamic> json, T Function(Map<String, dynamic>) convertir) {
    return Pagina(
      cantidad: json['cantidad'] as int? ?? 0,
      siguiente: json['siguiente'] as String?,
      resultados: [for (final item in json['resultados'] as List? ?? []) convertir(item as Map<String, dynamic>)],
      extra: json,
    );
  }

  final int cantidad;
  final List<T> resultados;

  /// Dirección de la página siguiente (null si es la última).
  final String? siguiente;
  final Map<String, dynamic> extra;
}

/// Mis datos (GET /perfil/ y el login).
class Perfil {
  Perfil(this.datos);

  /// Todo lo que vino del servidor, para mostrar cualquier campo por su nombre.
  final Map<String, dynamic> datos;

  int get id => datos['id'] as int;
  String get username => '${datos['username'] ?? ''}';
  String get nombreCompleto => '${datos['nombre_completo'] ?? ''}';
  String get primerNombre => '${datos['first_name'] ?? ''}'.split(' ').first;
  String get iniciales => '${datos['iniciales'] ?? ''}';
  String? get foto => datos['foto'] as String?;
  String get descripcionRol => '${datos['descripcion_rol'] ?? ''}';
  bool get esSuperusuario => datos['es_superusuario'] == true;
  bool get debeCambiarPassword => datos['debe_cambiar_password'] == true;
  String? get ultimoIngreso => datos['last_login'] as String?;

  Set<String> get permisos => {for (final p in datos['permisos'] as List? ?? []) '$p'};

  /// [(módulo, [descripciones])] — para mostrar "Lo que podés hacer".
  List<(String, List<String>)> get permisosPorModulo => [
    for (final m in datos['permisos_por_modulo'] as List? ?? [])
      ('${m['modulo']}', [for (final p in m['permisos'] as List) '$p']),
  ];

  bool puede(String codigo) => esSuperusuario || permisos.contains(codigo);
}

/// Una fila de la lista de usuarios.
class UsuarioResumen {
  UsuarioResumen(this.datos);

  final Map<String, dynamic> datos;

  int get id => datos['id'] as int;
  String get username => '${datos['username'] ?? ''}';
  String get nombreCompleto => '${datos['nombre_completo'] ?? ''}';
  String get iniciales => '${datos['iniciales'] ?? ''}';
  String? get foto => datos['foto'] as String?;
  String get descripcionRol => '${datos['descripcion_rol'] ?? ''}';
  bool get activo => datos['activo'] == true;
}

/// Un usuario completo (`GET /usuarios/<id>/`).
class UsuarioDetalle extends UsuarioResumen {
  UsuarioDetalle(super.datos);

  int? get rolId => (datos['rol'] as Map?)?['id'] as int?;
  bool get debeCambiarPassword => datos['debe_cambiar_password'] == true;

  /// Qué puede hacer con este usuario quien lo está mirando.
  bool accion(String nombre) => (datos['acciones'] as Map?)?[nombre] == true;
}

class Notificacion {
  Notificacion(this.datos);

  final Map<String, dynamic> datos;

  int get id => datos['id'] as int;
  String get titulo => '${datos['titulo'] ?? ''}';
  String get mensaje => '${datos['mensaje'] ?? ''}';
  String get nivel => '${datos['nivel'] ?? 'info'}';
  String get creada => '${datos['creada'] ?? ''}';
  bool get leida => datos['leida'] == true;
}

/// Una opción de un campo de elegir: {"valor": "dni", "texto": "DNI"}.
class Opcion {
  const Opcion(this.valor, this.texto);

  factory Opcion.desdeJson(Map<String, dynamic> json) => Opcion('${json['valor']}', '${json['texto']}');

  final String valor;
  final String texto;
}

/// Un rol para el formulario de usuarios.
class RolOpcion {
  RolOpcion(Map<String, dynamic> json)
    : id = json['id'] as int,
      nombre = '${json['nombre']}',
      descripcion = '${json['descripcion'] ?? ''}',
      puedeAsignar = json['puede_asignar'] == true;

  final int id;
  final String nombre;
  final String descripcion;

  /// False si el rol tiene permisos que quien carga el formulario no tiene.
  final bool puedeAsignar;
}

/// Una dirección de la señal de un canal. La app prueba las fuentes en orden.
class FuenteCanal {
  FuenteCanal(Map<String, dynamic> json)
    : id = json['id'] as int,
      url = '${json['url']}',
      tipo = '${json['tipo'] ?? 'hls'}',
      userAgent = '${json['user_agent'] ?? ''}',
      referer = '${json['referer'] ?? ''}';

  final int id;
  final String url;

  /// Cómo tiene que presentarse el reproductor para que el canal entregue la
  /// señal (lo decide el servidor). Hay canales que rechazan a "ExoPlayer".
  final String userAgent;
  final String referer;

  /// Las cabeceras con que se pide el video.
  Map<String, String> get cabeceras => {
    if (userAgent.isNotEmpty) 'User-Agent': userAgent,
    if (referer.isNotEmpty) 'Referer': referer,
  };

  /// "hls" o "youtube" (por ahora la app reproduce solo HLS).
  final String tipo;

  bool get esHls => tipo == 'hls';
}

/// Un canal de TV en vivo (GET /canales/).
class Canal {
  Canal(Map<String, dynamic> json)
    : id = json['id'] as int,
      nombre = '${json['nombre'] ?? ''}',
      numero = '${json['numero'] ?? ''}',
      logo = '${json['logo'] ?? ''}',
      fuentes = [for (final f in json['fuentes'] as List? ?? []) FuenteCanal(f as Map<String, dynamic>)];

  final int id;
  final String nombre;
  final String numero;
  final String logo;
  final List<FuenteCanal> fuentes;

  /// Las fuentes que la app sabe reproducir, en orden de prioridad.
  List<FuenteCanal> get fuentesReproducibles => fuentes.where((f) => f.esHls).toList();
}

/// Una categoría con sus canales.
class CategoriaCanales {
  CategoriaCanales(Map<String, dynamic> json)
    : nombre = '${json['nombre'] ?? ''}',
      canales = [for (final c in json['canales'] as List? ?? []) Canal(c as Map<String, dynamic>)];

  final String nombre;
  final List<Canal> canales;
}

/// Un cliente que mira la TV (GET /cliente/): entró con su código, no con usuario.
class DatosCliente {
  DatosCliente(Map<String, dynamic> json)
    : nombre = '${json['nombre'] ?? ''}',
      codigo = '${json['codigo'] ?? ''}',
      vence = DateTime.tryParse('${json['vence'] ?? ''}')?.toLocal(),
      pantallas = json['pantallas'] as int? ?? 0,
      conectados = json['conectados'] as int? ?? 0;

  final String nombre;

  /// Su código de acceso ("4821 9037"), por si lo olvida.
  final String codigo;
  final DateTime? vence;
  final int pantallas;
  final int conectados;

  /// Días que le quedan (0 si vence hoy).
  int? get diasRestantes => vence?.difference(DateTime.now()).inDays;
}
