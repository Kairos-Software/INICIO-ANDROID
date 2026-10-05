/// Las pantallas de antes de entrar (diseno_kairos_tv: tv-01..03, tv-17,
/// tv-22 y mobile-01..03, 07, 10). Las mismas en celular y TV: con pantalla
/// ancha se parten en dos columnas.
///
///   PantallaAcceso         el código del cliente con su teclado numérico (lo
///                          principal) y, aparte, usuario y contraseña del panel.
///   PantallaServicioVencido  a quién pedirle la renovación y "volver a intentar".
///   PantallaCarga          mientras arranca.
///   PantallaSinConexion    el servidor no responde.
library;

import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'api/cliente.dart';
import 'aparato.dart';
import 'config.dart';
import 'marca.dart';
import 'movil/estilo.dart';
import 'sesion.dart';
import 'tv/foco.dart';

/// El fondo de estas pantallas: grafito con una luz celeste arriba a la izquierda.
class _Fondo extends StatelessWidget {
  const _Fondo({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Theme(
      data: temaMovil(),
      child: Scaffold(
        backgroundColor: Tono.fondo,
        body: DecoratedBox(
          decoration: const BoxDecoration(
            gradient: RadialGradient(
              center: Alignment(-.75, -.85),
              radius: 1.1,
              colors: [Color(0xFF0B2A30), Tono.fondo],
            ),
          ),
          child: SafeArea(child: child),
        ),
      ),
    );
  }
}

bool _esAncha(BuildContext context) => MediaQuery.sizeOf(context).width >= 900;

// ── Login ──────────────────────────────────────────────────────────

class PantallaAcceso extends StatefulWidget {
  const PantallaAcceso({super.key});

  @override
  State<PantallaAcceso> createState() => _PantallaAccesoState();
}

class _PantallaAccesoState extends State<PantallaAcceso> {
  static const _largoCodigo = 8;

  String _codigo = '';
  bool _conCodigo = true;
  bool _enviando = false;
  ApiError? _error;

  final _usuario = TextEditingController();
  final _password = TextEditingController();
  bool _verPassword = false;

  @override
  void initState() {
    super.initState();
    // El último código usado en este aparato, ya escrito (por si el cliente lo olvidó)
    _codigo = SesionScope.leer(context).ultimoCodigo;
  }

  @override
  void dispose() {
    _usuario.dispose();
    _password.dispose();
    super.dispose();
  }

  void _tecla(String digito) {
    if (_codigo.length >= _largoCodigo) return;
    setState(() {
      _codigo += digito;
      _error = null;
    });
  }

  void _borrar() {
    if (_codigo.isEmpty) return;
    setState(() {
      _codigo = _codigo.substring(0, _codigo.length - 1);
      _error = null;
    });
  }

  Future<void> _ingresar() async {
    if (_enviando) return;
    if (_conCodigo && _codigo.length < _largoCodigo) {
      setState(
        () => _error = ApiError(status: 400, codigo: 'codigo_corto', detalle: 'Faltan números: son 8 en total.'),
      );
      return;
    }
    FocusManager.instance.primaryFocus?.unfocus();
    setState(() {
      _enviando = true;
      _error = null;
    });
    try {
      final sesion = SesionScope.leer(context);
      if (_conCodigo) {
        await sesion.ingresarConCodigo(_codigo);
      } else {
        await sesion.ingresar(_usuario.text.trim(), _password.text);
      }
      // No hace falta navegar: la sesión avisa y main.dart muestra lo que corresponde
    } on ApiError catch (error) {
      if (mounted) setState(() => _error = error);
    } finally {
      if (mounted) setState(() => _enviando = false);
    }
  }

  /// Los números y "borrar" del control remoto o del teclado también escriben el código.
  KeyEventResult _teclaFisica(FocusNode _, KeyEvent evento) {
    if (!_conCodigo || evento is KeyUpEvent) return KeyEventResult.ignored;
    final caracter = evento.character;
    if (caracter != null && RegExp(r'^\d$').hasMatch(caracter)) {
      _tecla(caracter);
      return KeyEventResult.handled;
    }
    final tecla = evento.logicalKey;
    final numero = _numerosDelControl[tecla];
    if (numero != null) {
      _tecla(numero);
      return KeyEventResult.handled;
    }
    if (tecla == LogicalKeyboardKey.backspace || tecla == LogicalKeyboardKey.delete) {
      _borrar();
      return KeyEventResult.handled;
    }
    return KeyEventResult.ignored;
  }

  Future<void> _configurarServidor() async {
    final sesion = SesionScope.leer(context);
    final control = TextEditingController(text: sesion.urlServidor);
    final nueva = await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Servidor'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text(
              'Dirección de la API. En tu red, la IP de la PC donde corre Django; '
              'en producción, el dominio con https.',
              style: TextStyle(color: Tono.textoSuave, fontSize: 13),
            ),
            const SizedBox(height: 16),
            TextField(
              controller: control,
              keyboardType: TextInputType.url,
              autocorrect: false,
              decoration: const InputDecoration(hintText: 'http://192.168.1.50:8000/api/v1/'),
            ),
          ],
        ),
        actions: [
          TextButton(onPressed: () => control.text = urlServidorPorDefecto, child: const Text('Por defecto')),
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('Cancelar')),
          TextButton(onPressed: () => Navigator.pop(context, control.text), child: const Text('Guardar')),
        ],
      ),
    );
    if (nueva != null && nueva.trim().isNotEmpty) {
      await sesion.cambiarServidor(nueva);
      if (mounted) setState(() {});
    }
  }

  @override
  Widget build(BuildContext context) {
    final ancha = _esAncha(context);
    final tarjeta = _conCodigo ? _tarjetaCodigo(ancha) : _tarjetaPanel(ancha);
    return PopScope(
      // "Atrás": en el panel vuelve al código; con el código escrito, borra un número
      canPop: _conCodigo && _codigo.isEmpty,
      onPopInvokedWithResult: (salio, _) {
        if (salio) return;
        if (!_conCodigo) {
          setState(() {
            _conCodigo = true;
            _error = null;
          });
        } else {
          _borrar();
        }
      },
      child: _Fondo(
        child: Focus(
          onKeyEvent: _teclaFisica,
          child: ancha
              ? Row(
                  children: [
                    const Expanded(flex: 46, child: _Bienvenida()),
                    Expanded(
                      flex: 54,
                      child: Center(
                        child: SingleChildScrollView(
                          padding: const EdgeInsets.symmetric(horizontal: 56, vertical: 32),
                          child: ConstrainedBox(constraints: const BoxConstraints(maxWidth: 720), child: tarjeta),
                        ),
                      ),
                    ),
                  ],
                )
              : Center(
                  child: SingleChildScrollView(
                    padding: const EdgeInsets.fromLTRB(22, 32, 22, 24),
                    child: ConstrainedBox(
                      constraints: const BoxConstraints(maxWidth: 420),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          const Center(child: SimboloKairos(tamanio: 56)),
                          const SizedBox(height: 40),
                          tarjeta,
                        ],
                      ),
                    ),
                  ),
                ),
        ),
      ),
    );
  }

  Widget _servidor() {
    return Center(
      child: TextButton.icon(
        onPressed: _configurarServidor,
        icon: const Icon(Icons.dns_rounded, size: 14, color: Tono.textoApagado),
        label: Text(
          SesionScope.of(context).urlServidor,
          style: const TextStyle(color: Tono.textoApagado, fontSize: 12),
          overflow: TextOverflow.ellipsis,
        ),
      ),
    );
  }

  Widget _tarjetaCodigo(bool ancha) {
    final contenido = Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text('ACCESO DE CLIENTES', style: LetraTv.sobretitulo.copyWith(fontSize: ancha ? 14 : 13)),
        const SizedBox(height: 8),
        Text('Ingresá tu código', style: ancha ? LetraTv.pantalla.copyWith(fontSize: 40) : _tituloCelular),
        const SizedBox(height: 4),
        Text(
          ancha ? 'Escribí los 8 números que te dio tu vendedor.' : 'Los 8 números que te dio tu vendedor.',
          style: ancha ? LetraTv.cuerpo : Letra.cuerpo,
        ),
        const SizedBox(height: 24),
        _Visor(codigo: _codigo, largo: _largoCodigo, grande: ancha),
        if (_error != null) ...[const SizedBox(height: 14), _CartelError(_error!)],
        SizedBox(height: ancha ? 22 : 18),
        _TecladoNumerico(
          alTecla: _tecla,
          alBorrar: _borrar,
          alOk: _ingresar,
          enviando: _enviando,
          alto: ancha ? 72 : 56,
        ),
        if (ancha) ...[
          const SizedBox(height: 18),
          const Text(
            '← ↑ ↓ → para moverte · OK para elegir · también podés usar los números del control',
            textAlign: TextAlign.center,
            style: LetraTv.ayuda,
          ),
          const SizedBox(height: 18),
          const Divider(color: Tono.capaMaxima),
        ],
        const SizedBox(height: 18),
        BotonTv(
          texto: ancha ? 'Ingresar como revendedor o administrador' : 'Revendedores / administradores',
          alOk: () => setState(() {
            _conCodigo = false;
            _error = null;
          }),
          ancho: double.infinity,
          tamanioTexto: ancha ? 17 : 15,
          alto: ancha ? 58 : 52,
        ),
        const SizedBox(height: 12),
        _servidor(),
      ],
    );
    return ancha ? _Panel(child: contenido) : contenido;
  }

  Widget _tarjetaPanel(bool ancha) {
    final error = _error;
    final errorDeCampo = error?.campo('username') ?? error?.campo('password');
    final contenido = Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text('ACCESO SECUNDARIO', style: LetraTv.sobretitulo.copyWith(fontSize: ancha ? 14 : 13)),
        const SizedBox(height: 8),
        Text('Revendedores y administradores', style: ancha ? LetraTv.pantalla.copyWith(fontSize: 36) : _tituloCelular),
        const SizedBox(height: 4),
        Text('Ingresá con tu cuenta del panel.', style: ancha ? LetraTv.cuerpo : Letra.cuerpo),
        const SizedBox(height: 24),
        if (error != null && errorDeCampo == null) ...[_CartelError(error), const SizedBox(height: 14)],
        _Campo(
          control: _usuario,
          texto: 'Usuario o email',
          autofocus: true,
          error: error?.campo('username'),
          teclado: TextInputType.emailAddress,
          accion: TextInputAction.next,
        ),
        const SizedBox(height: 14),
        _Campo(
          control: _password,
          texto: 'Contraseña',
          oculto: !_verPassword,
          error: error?.campo('password'),
          accion: TextInputAction.done,
          alEnviar: _ingresar,
          sufijo: IconButton(
            tooltip: _verPassword ? 'Ocultar' : 'Mostrar',
            icon: Icon(_verPassword ? Icons.visibility_off_rounded : Icons.visibility_rounded, color: Tono.textoSuave),
            onPressed: () => setState(() => _verPassword = !_verPassword),
          ),
        ),
        const SizedBox(height: 22),
        BotonTv(
          texto: _enviando ? 'Ingresando…' : 'Ingresar',
          principal: true,
          alOk: _ingresar,
          ancho: double.infinity,
          alto: ancha ? 58 : 52,
        ),
        const SizedBox(height: 12),
        BotonTv(
          texto: 'Volver al código de cliente',
          alOk: () => setState(() {
            _conCodigo = true;
            _error = null;
          }),
          ancho: double.infinity,
          alto: ancha ? 58 : 52,
          tamanioTexto: ancha ? 17 : 15,
        ),
        const SizedBox(height: 12),
        _servidor(),
      ],
    );
    return ancha ? _Panel(child: contenido) : contenido;
  }
}

const _tituloCelular = TextStyle(
  fontFamily: Letra.titulos,
  fontSize: 28,
  height: 32 / 28,
  fontWeight: FontWeight.w800,
  letterSpacing: -0.8,
  color: Tono.texto,
);

/// Las teclas numéricas del control remoto (algunos mandan estas y no el carácter).
final _numerosDelControl = {
  for (var i = 0; i <= 9; i++) LogicalKeyboardKey(LogicalKeyboardKey.digit0.keyId + i): '$i',
  for (var i = 0; i <= 9; i++) LogicalKeyboardKey(LogicalKeyboardKey.numpad0.keyId + i): '$i',
};

/// La columna izquierda del login en la TV: la marca y la frase.
class _Bienvenida extends StatelessWidget {
  const _Bienvenida();

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(80, 64, 40, 64),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SimboloKairos(tamanio: 84),
          const Spacer(),
          Text('KAIROS TV', style: LetraTv.sobretitulo.copyWith(fontSize: 15)),
          const SizedBox(height: 14),
          Text(
            'Todo lo que querés ver, en el momento indicado.',
            style: LetraTv.portada.copyWith(fontSize: 60, letterSpacing: -2),
          ),
          const SizedBox(height: 22),
          const Text(
            'Canales en vivo, películas y series en una experiencia pensada para tu pantalla.',
            style: LetraTv.cuerpo,
          ),
          const Spacer(flex: 2),
        ],
      ),
    );
  }
}

/// La tarjeta de vidrio oscuro donde va el formulario (en la TV).
class _Panel extends StatelessWidget {
  const _Panel({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(Curva.portada),
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 20, sigmaY: 20),
        child: Container(
          padding: const EdgeInsets.all(44),
          decoration: BoxDecoration(
            color: Tono.capaBaja.withValues(alpha: .88),
            borderRadius: BorderRadius.circular(Curva.portada),
            border: Border.all(color: Tono.bordeSuave.withValues(alpha: .5)),
          ),
          child: child,
        ),
      ),
    );
  }
}

/// Donde se ve el código: "4821 9037", con rayitas en lo que falta.
class _Visor extends StatelessWidget {
  const _Visor({required this.codigo, required this.largo, required this.grande});

  final String codigo;
  final int largo;
  final bool grande;

  @override
  Widget build(BuildContext context) {
    final estilo = TextStyle(
      fontFamily: Letra.titulos,
      fontWeight: FontWeight.w800,
      fontSize: grande ? 40 : 30,
      letterSpacing: grande ? 10 : 7,
      color: Tono.celesteClaro,
      fontFeatures: const [FontFeature.tabularFigures()],
    );
    String grupo(int desde) =>
        [for (var i = desde; i < desde + largo ~/ 2; i++) i < codigo.length ? codigo[i] : '_'].join();
    return Container(
      height: grande ? 82 : 64,
      alignment: Alignment.center,
      decoration: BoxDecoration(
        color: Tono.capaMinima,
        borderRadius: BorderRadius.circular(Curva.boton),
        border: Border.all(color: Tono.bordeSuave.withValues(alpha: .6)),
      ),
      child: Semantics(
        label: 'Código: ${codigo.split('').join(' ')}',
        child: Text('${grupo(0)}  ${grupo(largo ~/ 2)}', style: estilo),
      ),
    );
  }
}

/// El teclado numérico de la pantalla (para el control remoto y el dedo).
class _TecladoNumerico extends StatelessWidget {
  const _TecladoNumerico({
    required this.alTecla,
    required this.alBorrar,
    required this.alOk,
    required this.enviando,
    required this.alto,
  });

  final ValueChanged<String> alTecla;
  final VoidCallback alBorrar;
  final VoidCallback alOk;
  final bool enviando;
  final double alto;

  @override
  Widget build(BuildContext context) {
    Widget tecla(String texto, VoidCallback alOk, {IconData? icono, bool autofocus = false, String? etiqueta}) {
      return Expanded(
        child: Padding(
          padding: const EdgeInsets.all(6),
          child: Enfocable(
            alOk: alOk,
            autofocus: autofocus,
            curva: Curva.boton,
            escala: 1.05,
            etiqueta: etiqueta ?? texto,
            child: Container(
              height: alto,
              alignment: Alignment.center,
              decoration: BoxDecoration(
                color: Tono.capaAlta,
                borderRadius: BorderRadius.circular(Curva.boton),
                border: Border.all(color: Tono.bordeSuave.withValues(alpha: .45)),
              ),
              child: icono != null
                  ? Icon(icono, color: Tono.texto, size: alto * .38)
                  : Text(
                      texto,
                      style: TextStyle(
                        fontFamily: Letra.texto,
                        fontWeight: FontWeight.w700,
                        fontSize: alto * (texto.length > 1 ? .3 : .36),
                        color: Tono.texto,
                      ),
                    ),
            ),
          ),
        ),
      );
    }

    return FocusTraversalGroup(
      policy: ReadingOrderTraversalPolicy(),
      child: Column(
        children: [
          for (final fila in [
            ['1', '2', '3'],
            ['4', '5', '6'],
            ['7', '8', '9'],
          ])
            Row(children: [for (final n in fila) tecla(n, () => alTecla(n), autofocus: n == '1' && Aparato.esTv)]),
          Row(
            children: [
              tecla('Borrar', alBorrar, icono: Icons.backspace_outlined, etiqueta: 'Borrar'),
              tecla('0', () => alTecla('0')),
              tecla(enviando ? '…' : 'OK', alOk, etiqueta: 'Entrar'),
            ],
          ),
        ],
      ),
    );
  }
}

/// Un campo de texto del login del panel (usuario, contraseña).
class _Campo extends StatelessWidget {
  const _Campo({
    required this.control,
    required this.texto,
    this.autofocus = false,
    this.oculto = false,
    this.error,
    this.teclado,
    this.accion,
    this.alEnviar,
    this.sufijo,
  });

  final TextEditingController control;
  final String texto;
  final bool autofocus;
  final bool oculto;
  final String? error;
  final TextInputType? teclado;
  final TextInputAction? accion;
  final VoidCallback? alEnviar;
  final Widget? sufijo;

  @override
  Widget build(BuildContext context) {
    OutlineInputBorder borde(Color color, double ancho) => OutlineInputBorder(
      borderRadius: BorderRadius.circular(Curva.boton),
      borderSide: BorderSide(color: color, width: ancho),
    );
    return TextField(
      controller: control,
      autofocus: autofocus,
      obscureText: oculto,
      keyboardType: teclado,
      textInputAction: accion,
      autocorrect: false,
      onSubmitted: alEnviar == null ? null : (_) => alEnviar!(),
      style: const TextStyle(fontFamily: Letra.texto, fontSize: 17, color: Tono.texto),
      decoration: InputDecoration(
        hintText: texto,
        hintStyle: const TextStyle(color: Tono.textoApagado),
        errorText: error,
        filled: true,
        fillColor: Tono.capaMinima,
        contentPadding: const EdgeInsets.symmetric(horizontal: 18, vertical: 18),
        suffixIcon: sufijo,
        enabledBorder: borde(Tono.bordeSuave.withValues(alpha: .6), 1),
        focusedBorder: borde(Tono.celeste, 3),
        errorBorder: borde(Tono.rubi, 1),
        focusedErrorBorder: borde(Tono.rubi, 3),
      ),
    );
  }
}

/// Lo que salió mal al entrar: título y explicación sobre rubí (mobile-03).
class _CartelError extends StatelessWidget {
  const _CartelError(this.error);

  final ApiError error;

  (String, String) get _textos => switch (error.codigo) {
    'codigo_invalido' => ('Código incorrecto', 'Revisá los 8 números.'),
    'codigo_corto' => ('Código incompleto', error.detalle),
    'cuenta_en_uso' => ('Cuenta en uso', error.detalle),
    'login_bloqueado' || 'bloqueado' => ('Demasiados intentos', error.detalle),
    'sin_conexion' => ('Sin conexión', error.detalle),
    _ => ('No se pudo entrar', error.detalle),
  };

  @override
  Widget build(BuildContext context) {
    final (titulo, texto) = _textos;
    return Container(
      padding: const EdgeInsets.fromLTRB(18, 14, 18, 14),
      decoration: BoxDecoration(
        color: const Color(0xFF2A1219),
        borderRadius: BorderRadius.circular(Curva.boton),
        border: Border.all(color: Tono.rubi.withValues(alpha: .55)),
      ),
      child: Semantics(
        liveRegion: true,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              titulo,
              style: const TextStyle(
                fontFamily: Letra.texto,
                fontWeight: FontWeight.w700,
                fontSize: 17,
                color: Tono.rubiClaro,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              texto,
              style: const TextStyle(fontFamily: Letra.texto, fontSize: 14, color: Tono.rubiClaro),
            ),
          ],
        ),
      ),
    );
  }
}

// ── Servicio vencido ───────────────────────────────────────────────

class PantallaServicioVencido extends StatelessWidget {
  const PantallaServicioVencido({super.key});

  @override
  Widget build(BuildContext context) {
    final sesion = SesionScope.of(context);
    final vendedor = sesion.vendedorSinServicio;
    final motivo = sesion.motivoSinServicio ?? 'Tu servicio no está activo.';
    final suspendido = motivo.toLowerCase().contains('suspend');
    final ancha = _esAncha(context);
    // En la TV no hay WhatsApp: ahí se muestra el teléfono para anotarlo
    final puedeEscribir = vendedor.numeroWhatsapp.isNotEmpty && !Aparato.esTv;

    Future<void> escribir() async {
      final abierto = await Aparato.abrir(
        'https://wa.me/${vendedor.numeroWhatsapp}?text=${Uri.encodeComponent('Hola, quiero renovar mi servicio de Kairos TV.')}',
      );
      if (!abierto && context.mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text('No se pudo abrir WhatsApp. El número es ${vendedor.telefono}.')));
      }
    }

    return _Fondo(
      child: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(28),
          child: ConstrainedBox(
            constraints: BoxConstraints(maxWidth: ancha ? 640 : 420),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Icon(Icons.timelapse_rounded, size: ancha ? 64 : 48, color: Tono.rubi),
                const SizedBox(height: 18),
                Text(
                  suspendido ? 'SERVICIO SUSPENDIDO' : 'SERVICIO VENCIDO',
                  textAlign: TextAlign.center,
                  style: LetraTv.sobretitulo.copyWith(color: Tono.rubiClaro, fontSize: ancha ? 15 : 13),
                ),
                const SizedBox(height: 8),
                Text(
                  suspendido ? 'Tu servicio está suspendido' : 'Tu servicio venció',
                  textAlign: TextAlign.center,
                  style: ancha ? LetraTv.pantalla.copyWith(fontSize: 44) : _tituloCelular,
                ),
                const SizedBox(height: 8),
                Text(
                  'Contactá a tu vendedor para volver a mirar Kairos TV.',
                  textAlign: TextAlign.center,
                  style: ancha ? LetraTv.cuerpo : Letra.cuerpo,
                ),
                const SizedBox(height: 24),
                if (vendedor.hayDatos)
                  Container(
                    padding: const EdgeInsets.all(20),
                    decoration: BoxDecoration(
                      color: Tono.capaBaja,
                      borderRadius: BorderRadius.circular(Curva.panel),
                      border: Border.all(color: Tono.bordeSuave.withValues(alpha: .5)),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text('Tu vendedor', style: LetraTv.ayuda),
                        const SizedBox(height: 6),
                        if (vendedor.nombre.isNotEmpty)
                          Text(vendedor.nombre, style: LetraTv.tarjeta.copyWith(fontSize: ancha ? 22 : 18)),
                        if (vendedor.telefono.isNotEmpty)
                          Text(
                            vendedor.telefono,
                            style: TextStyle(
                              fontFamily: Letra.texto,
                              fontWeight: FontWeight.w700,
                              fontSize: ancha ? 26 : 18,
                              color: Tono.celeste,
                            ),
                          ),
                      ],
                    ),
                  ),
                const SizedBox(height: 22),
                if (puedeEscribir) ...[
                  BotonTv(
                    texto: 'Escribirle por WhatsApp',
                    icono: Icons.chat_rounded,
                    principal: true,
                    autofocus: true,
                    alOk: escribir,
                    ancho: double.infinity,
                  ),
                  const SizedBox(height: 12),
                ],
                BotonTv(
                  texto: 'Ya renové, volver a intentar',
                  icono: Icons.refresh_rounded,
                  principal: !puedeEscribir,
                  autofocus: !puedeEscribir,
                  alOk: sesion.reintentar,
                  ancho: double.infinity,
                ),
                const SizedBox(height: 12),
                BotonTv(texto: 'Entrar con otro código', alOk: sesion.salir, ancho: double.infinity),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

// ── Carga y sin conexión ───────────────────────────────────────────

class PantallaCarga extends StatelessWidget {
  const PantallaCarga({super.key, this.texto = 'Preparando tu contenido…'});

  final String texto;

  @override
  Widget build(BuildContext context) {
    final ancha = _esAncha(context);
    return _Fondo(
      child: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            SimboloKairos(tamanio: ancha ? 120 : 88),
            const SizedBox(height: 22),
            NombreKairos(tamanio: ancha ? 40 : 30),
            const SizedBox(height: 34),
            SizedBox(
              width: ancha ? 260 : 180,
              child: ClipRRect(
                borderRadius: BorderRadius.circular(4),
                child: const LinearProgressIndicator(
                  minHeight: 4,
                  color: Tono.celeste,
                  backgroundColor: Tono.capaMaxima,
                ),
              ),
            ),
            const SizedBox(height: 14),
            Text(texto, style: ancha ? LetraTv.ayuda.copyWith(fontSize: 16) : Letra.cuerpo),
          ],
        ),
      ),
    );
  }
}

class PantallaSinConexion extends StatelessWidget {
  const PantallaSinConexion({super.key});

  @override
  Widget build(BuildContext context) {
    final sesion = SesionScope.of(context);
    final ancha = _esAncha(context);
    return _Fondo(
      child: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(28),
          child: ConstrainedBox(
            constraints: BoxConstraints(maxWidth: ancha ? 640 : 420),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Icon(Icons.wifi_off_rounded, size: ancha ? 64 : 48, color: Tono.textoApagado),
                const SizedBox(height: 18),
                Text(
                  'No hay conexión con el servidor',
                  textAlign: TextAlign.center,
                  style: ancha ? LetraTv.pantalla : _tituloCelular,
                ),
                const SizedBox(height: 8),
                Text(
                  sesion.errorConexion ?? 'Revisá la conexión a internet de este aparato.',
                  textAlign: TextAlign.center,
                  style: ancha ? LetraTv.cuerpo : Letra.cuerpo,
                ),
                const SizedBox(height: 28),
                BotonTv(
                  texto: 'Reintentar',
                  icono: Icons.refresh_rounded,
                  principal: true,
                  autofocus: true,
                  alOk: sesion.reintentar,
                  ancho: double.infinity,
                ),
                const SizedBox(height: 12),
                BotonTv(
                  texto: 'Cerrar sesión e ingresar con otro servidor',
                  alOk: sesion.salir,
                  ancho: double.infinity,
                  tamanioTexto: 15,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
