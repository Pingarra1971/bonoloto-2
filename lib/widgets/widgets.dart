import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../theme/app_theme.dart';

// ═══════════════════════════════════════════════════════════
// BOLAS DE NÚMEROS ESTILO BONOLOTO
// ═══════════════════════════════════════════════════════════
class BolasNumerosWidget extends StatelessWidget {
  final List<int> numeros;
  final double tamano;

  const BolasNumerosWidget({
    super.key,
    required this.numeros,
    this.tamano = 44,
  });

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: 6,
      runSpacing: 6,
      children: numeros.map((n) => _Bola(numero: n, tamano: tamano)).toList(),
    );
  }
}

class _Bola extends StatelessWidget {
  final int numero;
  final double tamano;
  const _Bola({required this.numero, required this.tamano});

  @override
  Widget build(BuildContext context) {
    // Colores por rango de número, estilo oficial Bonoloto
    final colores = _coloresPorNumero(numero);

    return Container(
      width: tamano,
      height: tamano,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        gradient: RadialGradient(
          center: const Alignment(-0.3, -0.3),
          radius: 0.8,
          colors: [
            colores[0],
            colores[1],
          ],
        ),
        boxShadow: [
          BoxShadow(
            color: colores[1].withValues(alpha: 0.4),
            blurRadius: 8,
            offset: const Offset(0, 3),
          ),
        ],
      ),
      child: Center(
        child: Text(
          '$numero',
          style: GoogleFonts.rajdhani(
            fontSize: tamano * 0.38,
            fontWeight: FontWeight.w700,
            color: Colors.white,
            shadows: [
              Shadow(
                color: Colors.black.withValues(alpha: 0.3),
                blurRadius: 4,
                offset: const Offset(0, 1),
              ),
            ],
          ),
        ),
      ),
    );
  }

  List<Color> _coloresPorNumero(int n) {
    if (n <= 9) {
      return [const Color(0xFF4CAF50), const Color(0xFF1B5E20)];
    } else if (n <= 19) {
      return [const Color(0xFFFFD100), const Color(0xFFCCA800)];
    } else if (n <= 29) {
      return [const Color(0xFF2196F3), const Color(0xFF0D47A1)];
    } else if (n <= 39) {
      return [const Color(0xFFFF5722), const Color(0xFFBF360C)];
    } else {
      return [const Color(0xFF9C27B0), const Color(0xFF4A148C)];
    }
  }
}

// ═══════════════════════════════════════════════════════════
// BARRA DE CONFIANZA
// ═══════════════════════════════════════════════════════════
class BarraConfianzaWidget extends StatelessWidget {
  final double valor; // 0 a 100

  const BarraConfianzaWidget({super.key, required this.valor});

  @override
  Widget build(BuildContext context) {
    final color = valor >= 70
        ? BonolotoTheme.colorExito
        : valor >= 40
            ? BonolotoTheme.amarillo
            : BonolotoTheme.colorInfo;

    // No envolvemos en Expanded: eso solo es válido dentro de Row/Column/Flex
    // y rompía cuando se usaba en una Column (bug #153). El llamador que lo
    // use dentro de un Row debe envolverlo en Expanded él mismo.
    return ClipRRect(
      borderRadius: BorderRadius.circular(4),
      child: LinearProgressIndicator(
        value: (valor / 100).clamp(0.0, 1.0),
        minHeight: 8,
        backgroundColor:
            Theme.of(context).colorScheme.onSurface.withValues(alpha: 0.08),
        valueColor: AlwaysStoppedAnimation<Color>(color),
      ),
    );
  }
}

// ═══════════════════════════════════════════════════════════
// CHIP DE ESTADO
// ═══════════════════════════════════════════════════════════
class ChipEstado extends StatelessWidget {
  final String etiqueta;
  final Color color;
  final IconData? icono;

  const ChipEstado({
    super.key,
    required this.etiqueta,
    required this.color,
    this.icono,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: color.withValues(alpha: 0.4)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (icono != null) ...[
            Icon(icono, color: color, size: 12),
            const SizedBox(width: 4),
          ],
          Text(
            etiqueta,
            style: GoogleFonts.rajdhani(
              fontSize: 15,
              fontWeight: FontWeight.w700,
              color: color,
            ),
          ),
        ],
      ),
    );
  }
}

// ═══════════════════════════════════════════════════════════
// TARJETA MÉTRICA
// ═══════════════════════════════════════════════════════════
class TarjetaMetrica extends StatelessWidget {
  final String titulo;
  final String valor;
  final IconData icono;
  final Color color;

  const TarjetaMetrica({
    super.key,
    required this.titulo,
    required this.valor,
    required this.icono,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.07),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withValues(alpha: 0.2)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icono, color: color, size: 20),
          const SizedBox(height: 8),
          Text(
            valor,
            style: GoogleFonts.rajdhani(
              fontSize: 22,
              fontWeight: FontWeight.w700,
              color: theme.colorScheme.onSurface,
            ),
          ),
          Text(
            titulo,
            style: GoogleFonts.spaceMono(
              fontSize: 14,
              color: theme.colorScheme.onSurface.withValues(alpha: 0.5),
            ),
          ),
        ],
      ),
    );
  }
}

// ═══════════════════════════════════════════════════════════
// SEPARADOR CON ETIQUETA
// ═══════════════════════════════════════════════════════════
class SeparadorEtiqueta extends StatelessWidget {
  final String etiqueta;

  const SeparadorEtiqueta({super.key, required this.etiqueta});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 12),
      child: Row(
        children: [
          Expanded(
            child: Divider(
                color: theme.colorScheme.onSurface.withValues(alpha: 0.1)),
          ),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12),
            child: Text(
              etiqueta,
              style: GoogleFonts.rajdhani(
                fontSize: 15,
                fontWeight: FontWeight.w600,
                letterSpacing: 1.5,
                color: BonolotoTheme.verdeAccent,
              ),
            ),
          ),
          Expanded(
            child: Divider(
                color: theme.colorScheme.onSurface.withValues(alpha: 0.1)),
          ),
        ],
      ),
    );
  }
}
