/// El diseño de la app de celular: el sistema "Lumix TV" de Stitch, adaptado
/// a Kairos TV. Los valores salen tal cual del DESIGN.md y de la
/// configuración de Tailwind de sus pantallas (code.html), con los mismos
/// nombres entre paréntesis para poder compararlos.
///
/// La TV todavía usa el diseño anterior (lib/tema.dart).
library;

import 'package:flutter/material.dart';

/// Colores (tailwind.config -> colors).
class Tono {
  // Fondos, del más profundo al más claro
  static const fondo = Color(0xFF131317); // background / surface
  static const capaMinima = Color(0xFF0E0E12); // surface-container-lowest
  static const capaBaja = Color(0xFF1B1B20); // surface-container-low
  static const capa = Color(0xFF1F1F24); // surface-container
  static const capaAlta = Color(0xFF2A292E); // surface-container-high
  static const capaMaxima = Color(0xFF353439); // surface-container-highest / surface-variant
  static const bordeSuave = Color(0xFF3B494B); // outline-variant

  // Textos
  static const texto = Color(0xFFE4E1E8); // on-surface
  static const textoSuave = Color(0xFFB9CACB); // on-surface-variant
  static const textoApagado = Color(0xFF849495); // outline

  // Celeste eléctrico: lo activo, botones principales, barras de avance
  static const celeste = Color(0xFF00F0FF); // primary-container
  static const celesteClaro = Color(0xFFDBFCFF); // primary
  static const celesteFijo = Color(0xFF7DF4FF); // primary-fixed
  static const sobreCeleste = Color(0xFF006970); // on-primary-container
  static const sobreCelesteOscuro = Color(0xFF002022); // on-primary-fixed

  // Rubí: "EN VIVO", favoritos
  static const rubi = Color(0xFFDF0041); // secondary-container
  static const rubiClaro = Color(0xFFFFB3B5); // secondary
  static const sobreRubi = Color(0xFFFFF1F1); // on-secondary-container

  // Dorado: años, destacados
  static const dorado = Color(0xFFFFBA20); // tertiary-fixed-dim
  static const doradoClaro = Color(0xFFFFDEA8); // tertiary-fixed
}

/// Letras (tailwind.config -> fontSize). Plus Jakarta Sans para títulos e
/// Inter para todo lo demás.
class Letra {
  static const titulos = 'PlusJakartaSans';
  static const texto = 'Inter';

  /// display-lg-mobile: 30/38, 800 (títulos grandes de portada)
  static const display = TextStyle(
    fontFamily: titulos,
    fontSize: 30,
    height: 38 / 30,
    fontWeight: FontWeight.w800,
    letterSpacing: -0.6,
    color: Tono.texto,
  );

  /// headline-sm: 20/28, 600 (títulos de sección; en el diseño casi siempre en bold)
  static const titulo = TextStyle(
    fontFamily: titulos,
    fontSize: 20,
    height: 28 / 20,
    fontWeight: FontWeight.w700,
    letterSpacing: -0.2,
    color: Tono.texto,
  );

  /// body-lg: 16/24
  static const cuerpoGrande = TextStyle(fontFamily: texto, fontSize: 16, height: 24 / 16, color: Tono.texto);

  /// body-md: 14/20
  static const cuerpo = TextStyle(fontFamily: texto, fontSize: 14, height: 20 / 14, color: Tono.textoSuave);

  /// label-md: 12/16, 600
  static const etiqueta = TextStyle(
    fontFamily: texto,
    fontSize: 12,
    height: 16 / 12,
    fontWeight: FontWeight.w600,
    color: Tono.texto,
  );

  /// label-numeric: 12/16, 500, números tabulares (no "bailan" al cambiar)
  static const numeros = TextStyle(
    fontFamily: texto,
    fontSize: 12,
    height: 16 / 12,
    fontWeight: FontWeight.w500,
    color: Tono.textoSuave,
    fontFeatures: [FontFeature.tabularFigures()],
  );

  /// label-sm: 10/14, 700 (insignias y la barra de abajo)
  static const mini = TextStyle(
    fontFamily: texto,
    fontSize: 10,
    height: 14 / 10,
    fontWeight: FontWeight.w700,
    color: Tono.texto,
  );
}

/// Curvas de las esquinas (tailwind.config -> borderRadius): DEFAULT 4, lg 8, xl 12, 2xl 16.
class Curva {
  static const chico = 4.0;
  static const medio = 8.0;
  static const grande = 12.0;
  static const tarjeta = 16.0;
}

/// Espacios (tailwind.config -> spacing).
class Espacio {
  static const margen = 16.0; // margin / gutter / space-md
  static const xs = 4.0;
  static const sm = 8.0;
  static const lg = 24.0;
  static const xl = 40.0;
}

/// El brillo celeste de lo activo: shadow-[0_0_20px_rgba(0,240,255,0.35)] y parecidos.
List<BoxShadow> brilloCeleste({double desenfoque = 20, double opacidad = .35}) => [
  BoxShadow(
    color: Tono.celeste.withValues(alpha: opacidad),
    blurRadius: desenfoque,
  ),
];

/// El tema de Flutter para las pantallas de celular (lo que no se dibuja a mano).
ThemeData temaMovil() {
  final base = ThemeData(
    useMaterial3: true,
    brightness: Brightness.dark,
    fontFamily: Letra.texto,
    colorScheme: const ColorScheme.dark(
      primary: Tono.celeste,
      onPrimary: Tono.sobreCelesteOscuro,
      secondary: Tono.rubi,
      onSecondary: Tono.sobreRubi,
      surface: Tono.fondo,
      onSurface: Tono.texto,
      surfaceContainerHighest: Tono.capaMaxima,
    ),
    scaffoldBackgroundColor: Tono.fondo,
  );
  return base.copyWith(
    textTheme: base.textTheme.apply(fontFamily: Letra.texto, bodyColor: Tono.texto, displayColor: Tono.texto),
    progressIndicatorTheme: const ProgressIndicatorThemeData(color: Tono.celeste),
    bottomSheetTheme: const BottomSheetThemeData(
      backgroundColor: Tono.capaBaja,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(Curva.tarjeta))),
    ),
    dialogTheme: const DialogThemeData(backgroundColor: Tono.capaBaja),
    snackBarTheme: const SnackBarThemeData(
      backgroundColor: Tono.capaAlta,
      contentTextStyle: TextStyle(fontFamily: Letra.texto, color: Tono.texto),
      behavior: SnackBarBehavior.floating,
    ),
    textSelectionTheme: const TextSelectionThemeData(cursorColor: Tono.celeste),
  );
}
