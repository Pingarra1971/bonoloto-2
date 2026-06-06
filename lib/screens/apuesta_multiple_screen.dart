import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import '../state/app_notifier.dart';
import '../theme/app_theme.dart';
import '../widgets/widgets.dart';

/// Pantalla de APUESTA MÚLTIPLE.
///
/// Muestra las apuestas múltiples (de 7 a 11 números) que ha calculado el
/// servidor a partir de la última generación: los K números mejor puntuados,
/// cuántas combinaciones simples cubre cada tamaño y su coste oficial.
class ApuestaMultipleScreen extends ConsumerStatefulWidget {
  const ApuestaMultipleScreen({super.key});

  @override
  ConsumerState<ApuestaMultipleScreen> createState() =>
      _ApuestaMultipleScreenState();
}

class _ApuestaMultipleScreenState
    extends ConsumerState<ApuestaMultipleScreen> {
  int? _seleccion;

  /// Busca las apuestas múltiples en la sesión actual o, si no, en el
  /// historial más reciente que las tenga.
  Map<String, dynamic>? _obtenerApuestas() {
    final estado = ref.watch(appProvider);
    final actual = estado.sesionActual?.apuestasMultiples;
    if (actual != null && actual.isNotEmpty) return actual;
    for (final s in estado.historial) {
      final am = s.apuestasMultiples;
      if (am != null && am.isNotEmpty) return am;
    }
    return null;
  }

  List<int> _tallasDisponibles(Map<String, dynamic> am) {
    final tallas = am.keys
        .map((k) => int.tryParse(k) ?? 0)
        .where((k) => k >= 7 && k <= 11)
        .toList()
      ..sort();
    return tallas;
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final am = _obtenerApuestas();

    return Scaffold(
      appBar: AppBar(
        title: Text('APUESTA MÚLTIPLE',
            style: GoogleFonts.rajdhani(
                fontWeight: FontWeight.w700, letterSpacing: 2)),
      ),
      body: am == null
          ? _estadoVacio(theme)
          : _contenido(theme, am),
    );
  }

  Widget _estadoVacio(ThemeData theme) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.dashboard_customize_rounded,
                size: 64, color: BonolotoTheme.verdeAccent.withValues(alpha: 0.5)),
            const SizedBox(height: 20),
            Text('Aún no hay apuestas múltiples',
                textAlign: TextAlign.center,
                style: GoogleFonts.rajdhani(
                    fontSize: 22, fontWeight: FontWeight.w700)),
            const SizedBox(height: 12),
            Text(
              'Genera primero una combinación en la pestaña Inicio. '
              'Después, aquí podrás ver las apuestas múltiples de 7 a 11 '
              'números con sus combinaciones y su coste.',
              textAlign: TextAlign.center,
              style: theme.textTheme.bodyMedium,
            ),
          ],
        ),
      ),
    );
  }

  Widget _contenido(ThemeData theme, Map<String, dynamic> am) {
    final tallas = _tallasDisponibles(am);
    if (tallas.isEmpty) return _estadoVacio(theme);

    final seleccion = (_seleccion != null && tallas.contains(_seleccion))
        ? _seleccion!
        : tallas.first;

    final datos = Map<String, dynamic>.from(am[seleccion.toString()] as Map);
    final numeros = (datos['numeros'] as List? ?? [])
        .map((e) => (e as num).toInt())
        .toList();
    final combinaciones = (datos['combinaciones'] as num?)?.toInt() ?? 0;
    final coste = (datos['coste_eur'] as num?)?.toDouble() ?? 0.0;

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        // Aviso de honestidad
        Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: BonolotoTheme.amarillo.withValues(alpha: 0.08),
            borderRadius: BorderRadius.circular(14),
            border: Border.all(
                color: BonolotoTheme.amarillo.withValues(alpha: 0.35)),
          ),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Icon(Icons.info_outline_rounded,
                  color: BonolotoTheme.amarillo, size: 20),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  'Una apuesta múltiple NO mejora la probabilidad por euro '
                  'gastado: solo cubre más combinaciones a la vez pagando '
                  'proporcionalmente más. Juega con responsabilidad.',
                  style: theme.textTheme.bodyMedium,
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 20),

        Text('¿Cuántos números quieres jugar?',
            style: GoogleFonts.rajdhani(
                fontSize: 17, fontWeight: FontWeight.w700)),
        const SizedBox(height: 10),

        // Selector de talla (7-11)
        Wrap(
          spacing: 10,
          runSpacing: 10,
          children: tallas.map((k) {
            final activo = k == seleccion;
            return GestureDetector(
              onTap: () => setState(() => _seleccion = k),
              child: Container(
                width: 54,
                height: 54,
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  color: activo
                      ? BonolotoTheme.verdeClaro
                      : Colors.transparent,
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(
                    color: activo
                        ? BonolotoTheme.verdeClaro
                        : BonolotoTheme.verdeAccent.withValues(alpha: 0.4),
                    width: 2,
                  ),
                ),
                child: Text('$k',
                    style: GoogleFonts.rajdhani(
                        fontSize: 22,
                        fontWeight: FontWeight.w700,
                        color: activo ? const Color(0xFF081209) : null)),
              ),
            );
          }).toList(),
        ),
        const SizedBox(height: 24),

        // Números de la apuesta
        Text('Tus $seleccion números',
            style: GoogleFonts.rajdhani(
                fontSize: 17, fontWeight: FontWeight.w700)),
        const SizedBox(height: 12),
        Center(child: BolasNumerosWidget(numeros: numeros, tamano: 46)),
        const SizedBox(height: 24),

        // Tarjeta de combinaciones y coste
        Row(
          children: [
            Expanded(
              child: _TarjetaDato(
                etiqueta: 'COMBINACIONES',
                valor: '$combinaciones',
                color: BonolotoTheme.verdeAccent,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: _TarjetaDato(
                etiqueta: 'COSTE',
                valor: '${coste.toStringAsFixed(2)} €',
                color: BonolotoTheme.amarillo,
              ),
            ),
          ],
        ),
        const SizedBox(height: 16),
        Text(
          'Una apuesta de $seleccion números equivale a jugar $combinaciones '
          'apuestas simples de 6 números a la vez.',
          style: theme.textTheme.bodyMedium,
        ),

        const SizedBox(height: 28),
        Text('Precio de cada apuesta múltiple',
            style: GoogleFonts.rajdhani(
                fontSize: 17, fontWeight: FontWeight.w700)),
        const SizedBox(height: 10),
        ...tallas.map((k) {
          final d = Map<String, dynamic>.from(am[k.toString()] as Map);
          final comb = (d['combinaciones'] as num?)?.toInt() ?? 0;
          final c = (d['coste_eur'] as num?)?.toDouble() ?? 0.0;
          final activo = k == seleccion;
          return Container(
            margin: const EdgeInsets.only(bottom: 8),
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
            decoration: BoxDecoration(
              color: activo
                  ? BonolotoTheme.verdeClaro.withValues(alpha: 0.12)
                  : Colors.white.withValues(alpha: 0.03),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(
                color: activo
                    ? BonolotoTheme.verdeClaro.withValues(alpha: 0.5)
                    : Colors.white.withValues(alpha: 0.08),
              ),
            ),
            child: Row(
              children: [
                SizedBox(
                  width: 90,
                  child: Text('$k números',
                      style: GoogleFonts.rajdhani(
                          fontSize: 16, fontWeight: FontWeight.w700)),
                ),
                Expanded(
                  child: Text('$comb combinaciones',
                      style: theme.textTheme.bodyMedium),
                ),
                Text('${c.toStringAsFixed(2)} €',
                    style: GoogleFonts.rajdhani(
                        fontSize: 17,
                        fontWeight: FontWeight.w700,
                        color: BonolotoTheme.amarillo)),
              ],
            ),
          );
        }),
      ],
    );
  }
}

class _TarjetaDato extends StatelessWidget {
  final String etiqueta;
  final String valor;
  final Color color;

  const _TarjetaDato({
    required this.etiqueta,
    required this.valor,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 20, horizontal: 12),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: color.withValues(alpha: 0.3)),
      ),
      child: Column(
        children: [
          Text(etiqueta,
              style: GoogleFonts.rajdhani(
                  fontSize: 14,
                  fontWeight: FontWeight.w600,
                  letterSpacing: 1,
                  color: color)),
          const SizedBox(height: 8),
          Text(valor,
              style: GoogleFonts.rajdhani(
                  fontSize: 30, fontWeight: FontWeight.w700, color: color)),
        ],
      ),
    );
  }
}
