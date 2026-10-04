/// Los campos del usuario, agrupados por sección: los mismos (y en el
/// mismo orden) que SECCIONES_USUARIO y SECCIONES_PERFIL de
/// usuarios/forms.py. Las pantallas de ver y de editar se arman con esto.
library;

enum TipoCampo { texto, email, telefono, numero, fecha, opcion, multilinea, rol }

class Campo {
  const Campo(this.nombre, this.etiqueta, [this.tipo = TipoCampo.texto]);

  /// El nombre del campo en la API (igual que en Django).
  final String nombre;
  final String etiqueta;
  final TipoCampo tipo;
}

class Seccion {
  const Seccion(this.titulo, this.campos);

  final String titulo;
  final List<Campo> campos;
}

const _username = Campo('username', 'Nombre de usuario');
const _email = Campo('email', 'Email', TipoCampo.email);
const _nombre = Campo('first_name', 'Nombre/s');
const _apellido = Campo('last_name', 'Apellido/s');
const _tipoDocumento = Campo('tipo_documento', 'Tipo de documento', TipoCampo.opcion);
const _numeroDocumento = Campo('numero_documento', 'Número de documento');
const _fechaNacimiento = Campo('fecha_nacimiento', 'Fecha de nacimiento', TipoCampo.fecha);
const _genero = Campo('genero', 'Género', TipoCampo.opcion);
const _puesto = Campo('puesto', 'Puesto / cargo');
const _area = Campo('area', 'Área');
const _fechaIngreso = Campo('fecha_ingreso', 'Fecha de ingreso', TipoCampo.fecha);

const _contacto = Seccion('Contacto', [
  Campo('telefono', 'Teléfono', TipoCampo.telefono),
  Campo('telefono_alternativo', 'Teléfono alternativo', TipoCampo.telefono),
]);
const _domicilio = Seccion('Domicilio', [
  Campo('calle', 'Calle'),
  Campo('numero', 'Número'),
  Campo('piso_depto', 'Piso / depto'),
  Campo('localidad', 'Localidad'),
  Campo('provincia', 'Provincia'),
  Campo('codigo_postal', 'Código postal'),
  Campo('pais', 'País'),
]);
const _emergencia = Seccion('Contacto de emergencia', [
  Campo('emergencia_nombre', 'Contacto de emergencia'),
  Campo('emergencia_telefono', 'Teléfono de emergencia', TipoCampo.telefono),
]);

/// Gestión de usuarios (alta, edición y detalle).
const seccionesUsuario = [
  Seccion('Acceso al sistema', [_username, _email, Campo('rol', 'Rol', TipoCampo.rol)]),
  Seccion('Datos personales', [_nombre, _apellido, _tipoDocumento, _numeroDocumento, _fechaNacimiento, _genero]),
  _contacto,
  _domicilio,
  _emergencia,
  Seccion('Datos laborales', [_puesto, _area, _fechaIngreso, Campo('notas_internas', 'Notas internas', TipoCampo.multilinea)]),
];

/// Lo que cada uno puede editar de sí mismo en "Mi perfil".
const seccionesPerfil = [
  Seccion('Datos personales', [_nombre, _apellido, _email, _fechaNacimiento, _genero]),
  _contacto,
  _domicilio,
  _emergencia,
];

/// Lo que se ve en "Mi perfil" pero solo lo cambia la administración.
const seccionPerfilSoloLectura = Seccion('Datos de la cuenta', [
  _username,
  _tipoDocumento,
  _numeroDocumento,
  _puesto,
  _area,
  _fechaIngreso,
]);
