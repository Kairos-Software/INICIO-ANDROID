/// El diseño de la app: tema oscuro con los colores del logo de Kairos
/// (azul noche, azul eléctrico, celeste y violeta) y tipografía Poppins.
///
/// A propósito es totalmente distinto de la web: misma información,
/// otra "cara".
library;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

class Colores {
  // Fondos, del más profundo al más claro
  static const fondo = Color(0xFF070D1F);
  static const superficie = Color(0xFF0F1A35);
  static const superficieAlta = Color(0xFF172548);
  static const borde = Color(0xFF243564);

  // Los del logo
  static const azul = Color(0xFF1E6BFF);
  static const celeste = Color(0xFF22D3EE);
  static const violeta = Color(0xFF7C4DFF);

  // Textos
  static const texto = Color(0xFFEAF0FF);
  static const textoSuave = Color(0xFF8D9BC2);

  // Estados
  static const exito = Color(0xFF2DD4A7);
  static const aviso = Color(0xFFFFB547);
  static const peligro = Color(0xFFFF5C7A);
}

class Degradados {
  /// El del logo: celeste → azul → violeta. Para lo más importante.
  static const principal = LinearGradient(
    colors: [Colores.celeste, Colores.azul, Colores.violeta],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  /// Suave, para fondos de encabezados.
  static const encabezado = LinearGradient(
    colors: [Color(0xFF1B3A8A), Color(0xFF2A1E6E)],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );
}

/// Radios de las esquinas (todo redondeado, como el logo).
class Radios {
  static const chico = 12.0;
  static const medio = 18.0;
  static const grande = 26.0;
}

ThemeData temaDeLaApp() {
  final esquema = const ColorScheme.dark(
    primary: Colores.azul,
    onPrimary: Colors.white,
    secondary: Colores.celeste,
    onSecondary: Colores.fondo,
    tertiary: Colores.violeta,
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

  return ThemeData(
    useMaterial3: true,
    brightness: Brightness.dark,
    colorScheme: esquema,
    fontFamily: 'Poppins',
    scaffoldBackgroundColor: Colores.fondo,
    canvasColor: Colores.fondo,
    dividerColor: Colores.borde,
    appBarTheme: const AppBarTheme(
      backgroundColor: Colores.fondo,
      surfaceTintColor: Colors.transparent,
      foregroundColor: Colores.texto,
      elevation: 0,
      scrolledUnderElevation: 0,
      centerTitle: false,
      titleTextStyle: TextStyle(fontFamily: 'Poppins', fontSize: 22, fontWeight: FontWeight.w700, color: Colores.texto),
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
      subtitleTextStyle: TextStyle(fontFamily: 'Poppins', color: Colores.textoSuave, fontSize: 13),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: Colores.superficieAlta,
      border: bordeCampo,
      enabledBorder: bordeCampo,
      focusedBorder: bordeCampo.copyWith(borderSide: const BorderSide(color: Colores.celeste, width: 1.6)),
      errorBorder: bordeCampo.copyWith(borderSide: const BorderSide(color: Colores.peligro)),
      focusedErrorBorder: bordeCampo.copyWith(borderSide: const BorderSide(color: Colores.peligro, width: 1.6)),
      labelStyle: const TextStyle(color: Colores.textoSuave),
      floatingLabelStyle: const TextStyle(color: Colores.celeste),
      hintStyle: const TextStyle(color: Colores.textoSuave),
      prefixIconColor: Colores.textoSuave,
      suffixIconColor: Colores.textoSuave,
      helperStyle: const TextStyle(color: Colores.textoSuave),
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        backgroundColor: Colores.azul,
        foregroundColor: Colors.white,
        minimumSize: const Size(0, 52),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(Radios.chico)),
        textStyle: const TextStyle(fontFamily: 'Poppins', fontWeight: FontWeight.w600, fontSize: 15),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: Colores.texto,
        minimumSize: const Size(0, 48),
        side: const BorderSide(color: Colores.borde),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(Radios.chico)),
        textStyle: const TextStyle(fontFamily: 'Poppins', fontWeight: FontWeight.w500),
      ),
    ),
    textButtonTheme: TextButtonThemeData(
      style: TextButton.styleFrom(foregroundColor: Colores.celeste),
    ),
    chipTheme: ChipThemeData(
      backgroundColor: Colores.superficie,
      selectedColor: Colores.azul,
      side: const BorderSide(color: Colores.borde),
      labelStyle: const TextStyle(fontFamily: 'Poppins', color: Colores.texto, fontSize: 13),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
      showCheckmark: false,
    ),
    dialogTheme: DialogThemeData(
      backgroundColor: Colores.superficie,
      surfaceTintColor: Colors.transparent,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(Radios.grande)),
      titleTextStyle: const TextStyle(fontFamily: 'Poppins', fontSize: 20, fontWeight: FontWeight.w700, color: Colores.texto),
    ),
    bottomSheetTheme: const BottomSheetThemeData(
      backgroundColor: Colores.superficie,
      surfaceTintColor: Colors.transparent,
      dragHandleColor: Colores.borde,
    ),
    snackBarTheme: SnackBarThemeData(
      behavior: SnackBarBehavior.floating,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(Radios.chico)),
      contentTextStyle: const TextStyle(fontFamily: 'Poppins', color: Colors.white),
    ),
    progressIndicatorTheme: const ProgressIndicatorThemeData(color: Colores.celeste),
    switchTheme: SwitchThemeData(
      thumbColor: WidgetStateProperty.resolveWith((s) => s.contains(WidgetState.selected) ? Colors.white : Colores.textoSuave),
      trackColor: WidgetStateProperty.resolveWith((s) => s.contains(WidgetState.selected) ? Colores.azul : Colores.superficieAlta),
    ),
    checkboxTheme: CheckboxThemeData(
      fillColor: WidgetStateProperty.resolveWith((s) => s.contains(WidgetState.selected) ? Colores.azul : Colors.transparent),
    ),
    floatingActionButtonTheme: const FloatingActionButtonThemeData(
      backgroundColor: Colores.azul,
      foregroundColor: Colors.white,
    ),
    datePickerTheme: const DatePickerThemeData(
      backgroundColor: Colores.superficie,
      surfaceTintColor: Colors.transparent,
    ),
    popupMenuTheme: const PopupMenuThemeData(color: Colores.superficieAlta),
  );
}
