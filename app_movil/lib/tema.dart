/// El diseño de la app: el mismo de la marca del panel (static/css/sistema.css),
/// en su versión oscura: el azul noche del menú y del login, el celeste y el
/// azul de los detalles, el naranja del aro del logo, y las mismas letras
/// (Sora para títulos, Manrope para textos).
///
/// Si cambian los colores del panel, se cambian acá (bloque "TOKENS" de
/// sistema.css <-> clase Colores).
library;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

class Colores {
  // Fondos: el azul noche del menú del panel, del más profundo al más claro
  static const fondo = Color(0xFF050D1D);
  static const fondoAlto = Color(0xFF071A37);
  static const superficie = Color(0xFF0B1F3E);
  static const superficieAlta = Color(0xFF112B52);
  static const borde = Color(0xFF1E3A63);

  // Los de la marca (--azul, --cian, --ambar del panel)
  static const azul = Color(0xFF076BFF);
  static const azulOscuro = Color(0xFF0059E6);
  static const celeste = Color(0xFF00CFF4);
  static const naranja = Color(0xFFFF8A1E);
  static const naranjaOscuro = Color(0xFFDB6200);

  // Textos (los del menú del panel)
  static const texto = Color(0xFFF2F7FF);
  static const textoMenu = Color(0xFFB7C9E1);
  static const textoSuave = Color(0xFF8FA9C9);

  // Estados (los del panel, aclarados para que se lean sobre fondo oscuro)
  static const exito = Color(0xFF2BC19B);
  static const aviso = naranja;
  static const peligro = Color(0xFFF0627A);
}

/// Las letras del panel: Sora para títulos y la marca, Manrope para todo lo demás.
class Letras {
  static const titulos = 'Sora';
  static const texto = 'Manrope';
}

class Degradados {
  /// Celeste → azul: las rayitas de los títulos y lo que está activo (como el panel).
  static const principal = LinearGradient(
    colors: [Colores.celeste, Colores.azul],
    begin: Alignment.topCenter,
    end: Alignment.bottomCenter,
  );

  /// El fondo del menú del panel: azul noche con brillos celeste y azul.
  static const fondo = LinearGradient(
    colors: [Colores.fondoAlto, Colores.fondo],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    stops: [0, 0.72],
  );

  /// Tarjetas destacadas (saludo, perfil): como la tarjeta "en vivo" del panel.
  static const encabezado = LinearGradient(
    colors: [Color(0xFF0D3570), Color(0xFF0A1C3C)],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  /// Lo que está seleccionado (como el item activo del menú del panel).
  static final activo = LinearGradient(
    colors: [Colores.celeste.withValues(alpha: 0.18), Colores.azul.withValues(alpha: 0.12)],
  );
}

/// Radios de las esquinas (los del panel: --radio-chico 11-12px y --radio 18px).
class Radios {
  static const chico = 12.0;
  static const medio = 18.0;
  static const grande = 24.0;
}

/// Título con la letra de los títulos del panel (Sora, apretada).
TextStyle estiloTitulo(double tamanio, {Color color = Colores.texto, FontWeight peso = FontWeight.w700}) =>
    TextStyle(fontFamily: Letras.titulos, fontSize: tamanio, fontWeight: peso, color: color, letterSpacing: -0.6);

ThemeData temaDeLaApp() {
  final esquema = const ColorScheme.dark(
    primary: Colores.azul,
    onPrimary: Colors.white,
    secondary: Colores.celeste,
    onSecondary: Colores.fondo,
    tertiary: Colores.naranja,
    onTertiary: Colors.white,
    error: Colores.peligro,
    surface: Colores.superficie,
    onSurface: Colores.texto,
    onSurfaceVariant: Colores.textoSuave,
    outline: Colores.borde,
    outlineVariant: Colores.borde,
  );
  final bordeCampo = OutlineInputBorder(
    borderRadius: BorderRadius.circular(Radios.chico),
    borderSide: const BorderSide(color: Colores.borde),
  );
  const textoBoton = TextStyle(fontFamily: Letras.texto, fontWeight: FontWeight.w700, fontSize: 15);

  return ThemeData(
    useMaterial3: true,
    brightness: Brightness.dark,
    colorScheme: esquema,
    fontFamily: Letras.texto,
    scaffoldBackgroundColor: Colores.fondo,
    canvasColor: Colores.fondo,
    dividerColor: Colores.borde,
    // El foco del control remoto: naranja, como el :focus-visible del panel
    focusColor: Colores.naranja.withValues(alpha: 0.22),
    textTheme: const TextTheme(
      headlineLarge: TextStyle(fontFamily: Letras.titulos, fontWeight: FontWeight.w700, letterSpacing: -0.8),
      headlineMedium: TextStyle(fontFamily: Letras.titulos, fontWeight: FontWeight.w700, letterSpacing: -0.6),
      headlineSmall: TextStyle(fontFamily: Letras.titulos, fontWeight: FontWeight.w700, letterSpacing: -0.5),
      titleLarge: TextStyle(fontFamily: Letras.titulos, fontWeight: FontWeight.w600, letterSpacing: -0.4),
    ),
    appBarTheme: const AppBarTheme(
      backgroundColor: Colores.fondo,
      surfaceTintColor: Colors.transparent,
      foregroundColor: Colores.texto,
      elevation: 0,
      scrolledUnderElevation: 0,
      centerTitle: false,
      titleTextStyle: TextStyle(
        fontFamily: Letras.titulos,
        fontSize: 21,
        fontWeight: FontWeight.w700,
        color: Colores.texto,
        letterSpacing: -0.6,
      ),
      // Íconos de la barra de estado (hora, batería) en blanco
      systemOverlayStyle: SystemUiOverlayStyle(
        statusBarColor: Colors.transparent,
        statusBarIconBrightness: Brightness.light,
        systemNavigationBarColor: Colores.fondo,
        systemNavigationBarIconBrightness: Brightness.light,
      ),
    ),
    cardTheme: CardThemeData(
      color: Colores.superficie,
      surfaceTintColor: Colors.transparent,
      elevation: 0,
      margin: EdgeInsets.zero,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(Radios.medio),
        side: const BorderSide(color: Colores.borde),
      ),
    ),
    listTileTheme: const ListTileThemeData(
      iconColor: Colores.textoSuave,
      textColor: Colores.texto,
      subtitleTextStyle: TextStyle(fontFamily: Letras.texto, color: Colores.textoSuave, fontSize: 13),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: Colores.superficie,
      border: bordeCampo,
      enabledBorder: bordeCampo,
      focusedBorder: bordeCampo.copyWith(borderSide: const BorderSide(color: Colores.celeste, width: 1.6)),
      errorBorder: bordeCampo.copyWith(borderSide: const BorderSide(color: Colores.peligro)),
      focusedErrorBorder: bordeCampo.copyWith(borderSide: const BorderSide(color: Colores.peligro, width: 1.6)),
      labelStyle: const TextStyle(color: Colores.textoSuave),
      floatingLabelStyle: const TextStyle(color: Colores.celeste),
      hintStyle: TextStyle(color: Colores.textoSuave.withValues(alpha: 0.6)),
      prefixIconColor: Colores.textoSuave,
      suffixIconColor: Colores.textoSuave,
      helperStyle: const TextStyle(color: Colores.textoSuave),
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
    ),
    // Botón principal = el .btn-primary del panel (azul)
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        backgroundColor: Colores.azul,
        foregroundColor: Colors.white,
        minimumSize: const Size(0, 52),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(Radios.chico)),
        textStyle: textoBoton,
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: Colores.texto,
        minimumSize: const Size(0, 48),
        side: const BorderSide(color: Colores.borde),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(Radios.chico)),
        textStyle: textoBoton.copyWith(fontWeight: FontWeight.w600),
      ),
    ),
    textButtonTheme: TextButtonThemeData(
      style: TextButton.styleFrom(
        foregroundColor: Colores.celeste,
        textStyle: const TextStyle(fontFamily: Letras.texto, fontWeight: FontWeight.w600),
      ),
    ),
    iconButtonTheme: IconButtonThemeData(style: IconButton.styleFrom(foregroundColor: Colores.textoMenu)),
    chipTheme: ChipThemeData(
      backgroundColor: Colores.superficie,
      selectedColor: Colores.azul,
      side: const BorderSide(color: Colores.borde),
      labelStyle: const TextStyle(
        fontFamily: Letras.texto,
        color: Colores.texto,
        fontSize: 13,
        fontWeight: FontWeight.w600,
      ),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
      showCheckmark: false,
    ),
    dialogTheme: DialogThemeData(
      backgroundColor: Colores.fondoAlto,
      surfaceTintColor: Colors.transparent,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(Radios.grande),
        side: const BorderSide(color: Colores.borde),
      ),
      titleTextStyle: estiloTitulo(20),
    ),
    bottomSheetTheme: const BottomSheetThemeData(
      backgroundColor: Colores.fondoAlto,
      surfaceTintColor: Colors.transparent,
      dragHandleColor: Colores.borde,
    ),
    snackBarTheme: SnackBarThemeData(
      behavior: SnackBarBehavior.floating,
      backgroundColor: Colores.superficieAlta,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(Radios.chico)),
      contentTextStyle: const TextStyle(fontFamily: Letras.texto, color: Colors.white, fontWeight: FontWeight.w600),
    ),
    progressIndicatorTheme: const ProgressIndicatorThemeData(
      color: Colores.celeste,
      linearTrackColor: Colors.transparent,
    ),
    switchTheme: SwitchThemeData(
      thumbColor: WidgetStateProperty.resolveWith(
        (s) => s.contains(WidgetState.selected) ? Colors.white : Colores.textoSuave,
      ),
      trackColor: WidgetStateProperty.resolveWith(
        (s) => s.contains(WidgetState.selected) ? Colores.azul : Colores.superficieAlta,
      ),
    ),
    checkboxTheme: CheckboxThemeData(
      fillColor: WidgetStateProperty.resolveWith(
        (s) => s.contains(WidgetState.selected) ? Colores.azul : Colors.transparent,
      ),
    ),
    // El "+" de crear = el .btn-acento del panel (naranja)
    floatingActionButtonTheme: const FloatingActionButtonThemeData(
      backgroundColor: Colores.naranja,
      foregroundColor: Colors.white,
    ),
    datePickerTheme: const DatePickerThemeData(
      backgroundColor: Colores.fondoAlto,
      surfaceTintColor: Colors.transparent,
    ),
    popupMenuTheme: const PopupMenuThemeData(color: Colores.superficieAlta),
  );
}

/// Fondo de pantalla como el menú del panel: degradé azul noche con un
/// brillo celeste arriba a la izquierda y uno azul abajo a la derecha.
class FondoMarca extends StatelessWidget {
  const FondoMarca({super.key, required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: const BoxDecoration(gradient: Degradados.fondo),
      child: Stack(
        children: [
          const Positioned(top: -140, left: -120, child: _Brillo(color: Colores.celeste, tamanio: 380, alfa: 0.20)),
          const Positioned(bottom: -160, right: -140, child: _Brillo(color: Colores.azul, tamanio: 440, alfa: 0.22)),
          Positioned.fill(child: child),
        ],
      ),
    );
  }
}

class _Brillo extends StatelessWidget {
  const _Brillo({required this.color, required this.tamanio, required this.alfa});

  final Color color;
  final double tamanio;
  final double alfa;

  @override
  Widget build(BuildContext context) {
    return IgnorePointer(
      child: Container(
        width: tamanio,
        height: tamanio,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          gradient: RadialGradient(
            colors: [
              color.withValues(alpha: alfa),
              color.withValues(alpha: 0),
            ],
          ),
        ),
      ),
    );
  }
}
