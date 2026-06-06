import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class BonolotoTheme {
  // ═══════════════════════════════════════════
  // COLORES OFICIALES BONOLOTO
  // ═══════════════════════════════════════════
  static const Color verdeOscuro = Color(0xFF006633);
  static const Color verdeMedio = Color(0xFF008040);
  static const Color verdeClaro = Color(0xFF00A651);
  static const Color verdeAccent = Color(0xFF39C96E);
  static const Color amarillo = Color(0xFFFFD100);
  static const Color amarilloClaro = Color(0xFFFFE44D);
  static const Color amarilloOscuro = Color(0xFFCCA800);

  // Colores de estado
  static const Color colorExito = Color(0xFF39C96E);
  static const Color colorError = Color(0xFFFF4444);
  static const Color colorAdvertencia = Color(0xFFFFD100);
  static const Color colorInfo = Color(0xFF4DAAFF);

  // ═══════════════════════════════════════════
  // TEMA OSCURO
  // ═══════════════════════════════════════════
  static ThemeData get darkTheme {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      colorScheme: const ColorScheme.dark(
        primary: verdeAccent,
        secondary: amarillo,
        surface: Color(0xFF0D1F15),
        onPrimary: Color(0xFF081209),
        onSecondary: Color(0xFF081209),
        onSurface: Color(0xFFE8F5EC),
        error: colorError,
        tertiary: amarilloClaro,
      ),
      scaffoldBackgroundColor: const Color(0xFF081209),
      cardColor: const Color(0xFF0D1F15),
      textTheme: _buildTextTheme(isLight: false),
      appBarTheme: const AppBarTheme(
        backgroundColor: Color(0xFF0A1A10),
        foregroundColor: Color(0xFFE8F5EC),
        elevation: 0,
        centerTitle: true,
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: verdeAccent,
          foregroundColor: const Color(0xFF081209),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
          textStyle: GoogleFonts.rajdhani(
            fontSize: 16,
            fontWeight: FontWeight.w700,
            letterSpacing: 1.2,
          ),
        ),
      ),
      cardTheme: CardThemeData(
        color: const Color(0xFF0D1F15),
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
          side: const BorderSide(color: Color(0xFF1A3A22), width: 1),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: const Color(0xFF0D1F15),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: Color(0xFF1A3A22)),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: Color(0xFF1A3A22)),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: verdeAccent, width: 2),
        ),
        labelStyle: const TextStyle(color: Color(0xFF6B9E7A)),
        hintStyle: const TextStyle(color: Color(0xFF4A7A57)),
      ),
      dividerColor: const Color(0xFF1A3A22),
      iconTheme: const IconThemeData(color: verdeAccent),
      bottomNavigationBarTheme: const BottomNavigationBarThemeData(
        backgroundColor: Color(0xFF0A1A10),
        selectedItemColor: amarillo,
        unselectedItemColor: Color(0xFF4A7A57),
        type: BottomNavigationBarType.fixed,
        elevation: 0,
      ),
    );
  }

  // ═══════════════════════════════════════════
  // TEMA CLARO
  // ═══════════════════════════════════════════
  static ThemeData get lightTheme {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.light,
      colorScheme: const ColorScheme.light(
        primary: verdeOscuro,
        secondary: amarilloOscuro,
        surface: Color(0xFFF0FAF3),
        onPrimary: Colors.white,
        onSecondary: Colors.white,
        onSurface: Color(0xFF0D2E18),
        error: colorError,
        tertiary: verdeMedio,
      ),
      scaffoldBackgroundColor: const Color(0xFFF5FBF7),
      cardColor: Colors.white,
      textTheme: _buildTextTheme(isLight: true),
      appBarTheme: const AppBarTheme(
        backgroundColor: verdeOscuro,
        foregroundColor: Colors.white,
        elevation: 0,
        centerTitle: true,
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: verdeOscuro,
          foregroundColor: Colors.white,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
          textStyle: GoogleFonts.rajdhani(
            fontSize: 16,
            fontWeight: FontWeight.w700,
            letterSpacing: 1.2,
          ),
        ),
      ),
      cardTheme: CardThemeData(
        color: Colors.white,
        elevation: 2,
        shadowColor: const Color(0x1A006633),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: Colors.white,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: Color(0xFFB8DEC4)),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: Color(0xFFB8DEC4)),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: verdeOscuro, width: 2),
        ),
        labelStyle: const TextStyle(color: Color(0xFF4A8A5E)),
        hintStyle: const TextStyle(color: Color(0xFF8AB89A)),
      ),
      dividerColor: const Color(0xFFB8DEC4),
      iconTheme: const IconThemeData(color: verdeOscuro),
      bottomNavigationBarTheme: const BottomNavigationBarThemeData(
        backgroundColor: Colors.white,
        selectedItemColor: verdeOscuro,
        unselectedItemColor: Color(0xFF8AB89A),
        type: BottomNavigationBarType.fixed,
        elevation: 8,
      ),
    );
  }

  static TextTheme _buildTextTheme({required bool isLight}) {
    final baseColor = isLight ? const Color(0xFF0D2E18) : const Color(0xFFE8F5EC);
    final mutedColor = isLight ? const Color(0xFF4A8A5E) : const Color(0xFF6B9E7A);

    return TextTheme(
      displayLarge: GoogleFonts.rajdhani(
        fontSize: 48,
        fontWeight: FontWeight.w700,
        color: baseColor,
        letterSpacing: -1,
      ),
      displayMedium: GoogleFonts.rajdhani(
        fontSize: 36,
        fontWeight: FontWeight.w700,
        color: baseColor,
        letterSpacing: -0.5,
      ),
      displaySmall: GoogleFonts.rajdhani(
        fontSize: 28,
        fontWeight: FontWeight.w600,
        color: baseColor,
      ),
      headlineLarge: GoogleFonts.rajdhani(
        fontSize: 24,
        fontWeight: FontWeight.w700,
        color: baseColor,
        letterSpacing: 0.5,
      ),
      headlineMedium: GoogleFonts.rajdhani(
        fontSize: 20,
        fontWeight: FontWeight.w600,
        color: baseColor,
      ),
      headlineSmall: GoogleFonts.rajdhani(
        fontSize: 18,
        fontWeight: FontWeight.w600,
        color: baseColor,
      ),
      titleLarge: GoogleFonts.rajdhani(
        fontSize: 16,
        fontWeight: FontWeight.w600,
        color: baseColor,
        letterSpacing: 0.8,
      ),
      bodyLarge: GoogleFonts.spaceMono(
        fontSize: 17,
        color: baseColor,
      ),
      bodyMedium: GoogleFonts.spaceMono(
        fontSize: 16,
        color: mutedColor,
      ),
      labelLarge: GoogleFonts.rajdhani(
        fontSize: 17,
        fontWeight: FontWeight.w600,
        color: baseColor,
        letterSpacing: 1.0,
      ),
    );
  }
}
