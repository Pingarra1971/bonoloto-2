import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';

import '../models/models.dart';
import '../state/app_notifier.dart';
import '../theme/app_theme.dart';

/// Dashboard de Honestidad.
///
/// Muestra al usuario la VERDAD numérica de su relación con la Bonoloto:
///   - P&L real (apostado, ganado, balance)
///   - EV teórico vs realidad
///   - Backtest: ¿el sistema supera al azar? (casi seguro que no)
///   - Coste de oportunidad
///
/// Esta pantalla cumple el compromiso de transparencia. No vende ilusiones.
class HonestidadScreen extends ConsumerStatefulWidget {
  const HonestidadScreen({super.key});

  @override
  ConsumerState<HonestidadScreen> createState() => _HonestidadScreenState();
}

class _HonestidadScreenState extends ConsumerState<HonestidadScreen> {
  EstadisticasHonestidad _stats = EstadisticasHonestidad.vacio;
  bool _cargando = true;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _cargar());
  }

  Future<void> _cargar() async {
    setState(() => _cargando = true);
    final stats = await ref.read(appProvider.notifier).cargarHonestidad();
    if (!mounted) return;
    setState(() {
      _stats = stats ?? EstadisticasHonestidad.vacio;
      _cargando = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(
        title: Text(
          'MI RENDIMIENTO',
          style: GoogleFonts.rajdhani(
            fontWeight: FontWeight.w700,
            letterSpacing: 2,
          ),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_rounded),
            onPressed: _cargar,
          ),
        ],
      ),
      body: _cargando
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _cargar,
              child: ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  _bannerHonestidad(theme),
                  const SizedBox(height: 16),
                  _seccionPyL(theme),
                  const SizedBox(height: 16),
                  _seccionEV(theme),
                  const SizedBox(height: 16),
                  _seccionBacktest(theme),
                  const SizedBox(height: 16),
                  _seccionCosteOportunidad(theme),
                  const SizedBox(height: 24),
                  _disclaimer(theme),
                ],
              ),
            ),
    );
  }

  // ── Banner explicativo ──
  Widget _bannerHonestidad(ThemeData theme) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: theme.colorScheme.primary.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: theme.colorScheme.primary.withValues(alpha: 0.25),
        ),
      ),
      child: Row(
        children: [
          Icon(Icons.balance_rounded, color: theme.colorScheme.primary),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              'Aquí ves los números reales, sin adornos. La verdad ayuda a '
              'decidir mejor.',
              style: GoogleFonts.rajdhani(
                fontSize: 17,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ],
      ),
    );
  }

  // ── P&L ──
  Widget _seccionPyL(ThemeData theme) {
    final balance = _stats.balanceNetoEur;
    final colorBalance =
        balance >= 0 ? BonolotoTheme.verdeAccent : BonolotoTheme.colorError;

    return _Card(
      titulo: 'BALANCE',
      child: Column(
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              _kpi('Apostado', '${_stats.totalApostadoEur.toStringAsFixed(2)}€',
                  theme, color: theme.colorScheme.onSurface),
              _kpi('Ganado', '${_stats.totalGanadoEur.toStringAsFixed(2)}€',
                  theme, color: BonolotoTheme.verdeAccent),
            ],
          ),
          const Divider(height: 28),
          Column(
            children: [
              Text(
                'BALANCE NETO',
                style: GoogleFonts.rajdhani(
                  fontSize: 16,
                  letterSpacing: 1.5,
                  color: theme.colorScheme.onSurface.withValues(alpha: 0.6),
                ),
              ),
              const SizedBox(height: 4),
              Text(
                '${balance >= 0 ? '+' : ''}${balance.toStringAsFixed(2)}€',
                style: GoogleFonts.spaceMono(
                  fontSize: 34,
                  fontWeight: FontWeight.w700,
                  color: colorBalance,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            '${_stats.nApuestasEvaluadas} de ${_stats.nApuestas} apuestas evaluadas',
            style: GoogleFonts.rajdhani(
              fontSize: 16,
              color: theme.colorScheme.onSurface.withValues(alpha: 0.5),
            ),
          ),
        ],
      ),
    );
  }

  // ── EV ──
  Widget _seccionEV(ThemeData theme) {
    final ev = _stats.evApuestaActual;
    final teorico = _stats.evTeoricoAcumuladoEur;
    final dif = _stats.diferenciaRealVsTeoricoEur;

    return _Card(
      titulo: 'VALOR ESPERADO',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _filaInfo(
            'EV de una apuesta hoy',
            '${ev.evPorcentaje.toStringAsFixed(1)}%',
            theme,
            color: ev.esFavorable
                ? BonolotoTheme.verdeAccent
                : BonolotoTheme.colorError,
          ),
          const SizedBox(height: 8),
          _filaInfo(
            'Pérdida esperada acumulada',
            '${teorico.toStringAsFixed(2)}€',
            theme,
          ),
          const SizedBox(height: 8),
          _filaInfo(
            'Tu resultado vs lo esperado',
            '${dif >= 0 ? '+' : ''}${dif.toStringAsFixed(2)}€',
            theme,
            color: dif >= 0
                ? BonolotoTheme.verdeAccent
                : BonolotoTheme.colorError,
          ),
          const SizedBox(height: 12),
          Text(
            ev.esFavorable
                ? 'El bote actual hace el EV teóricamente positivo, pero la '
                    'probabilidad de acertar 6 sigue siendo 1 entre 14 millones.'
                : 'El valor esperado es negativo: en promedio se pierde. Es '
                    'estructural de la lotería.',
            style: GoogleFonts.rajdhani(
              fontSize: 16,
              fontStyle: FontStyle.italic,
              color: theme.colorScheme.onSurface.withValues(alpha: 0.6),
            ),
          ),
        ],
      ),
    );
  }

  // ── Backtest ──
  Widget _seccionBacktest(ThemeData theme) {
    final bt = _stats.backtest;
    return _Card(
      titulo: 'EL SISTEMA VS EL AZAR',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              _kpi(
                'Sistema',
                bt.aciertosMediosSistema.toStringAsFixed(3),
                theme,
                color: theme.colorScheme.primary,
                sub: 'aciertos/boleto',
              ),
              _kpi(
                'Azar',
                bt.aciertosEsperadosAzar.toStringAsFixed(3),
                theme,
                color: theme.colorScheme.onSurface.withValues(alpha: 0.6),
                sub: 'aciertos/boleto',
              ),
            ],
          ),
          const SizedBox(height: 16),
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: theme.colorScheme.surfaceContainerHighest
                  .withValues(alpha: 0.4),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Text(
              bt.veredicto,
              style: GoogleFonts.rajdhani(
                fontSize: 16,
                fontWeight: FontWeight.w500,
                height: 1.4,
              ),
            ),
          ),
          if (bt.nPredicciones > 0) ...[
            const SizedBox(height: 12),
            Text(
              'Basado en ${bt.nPredicciones} combinaciones sobre '
              '${bt.nSorteos} sorteos.',
              style: GoogleFonts.rajdhani(
                fontSize: 15,
                color: theme.colorScheme.onSurface.withValues(alpha: 0.5),
              ),
            ),
          ],
        ],
      ),
    );
  }

  // ── Coste oportunidad ──
  Widget _seccionCosteOportunidad(ThemeData theme) {
    final co = _stats.costeOportunidad;
    if (_stats.totalApostadoEur <= 0) {
      return const SizedBox.shrink();
    }
    return _Card(
      titulo: 'COSTE DE OPORTUNIDAD',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Si hubieras invertido lo apostado en un índice diversificado '
            '(~${(co.rendimientoUsado * 100).toStringAsFixed(0)}% anual):',
            style: GoogleFonts.rajdhani(fontSize: 16),
          ),
          const SizedBox(height: 12),
          _filaInfo(
            'Valdría ahora',
            '${co.valorSiInvertidoEur.toStringAsFixed(2)}€',
            theme,
            color: BonolotoTheme.verdeAccent,
          ),
          const SizedBox(height: 6),
          _filaInfo(
            'Diferencia',
            '+${co.gananciaAlternativaEur.toStringAsFixed(2)}€',
            theme,
            color: BonolotoTheme.verdeAccent,
          ),
          const SizedBox(height: 8),
          Text(
            'Dato de contexto, no consejo financiero.',
            style: GoogleFonts.rajdhani(
              fontSize: 15,
              fontStyle: FontStyle.italic,
              color: theme.colorScheme.onSurface.withValues(alpha: 0.5),
            ),
          ),
        ],
      ),
    );
  }

  Widget _disclaimer(ThemeData theme) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 8),
      child: Text(
        'La Bonoloto es un juego de azar. La probabilidad de acertar los 6 '
        'números es de 1 entre 13.983.816. Juega con responsabilidad. '
        'Si el juego deja de ser un entretenimiento, busca ayuda: '
        'www.jugarbien.es · 900 200 225',
        textAlign: TextAlign.center,
        style: GoogleFonts.rajdhani(
          fontSize: 15,
          color: theme.colorScheme.onSurface.withValues(alpha: 0.45),
          height: 1.4,
        ),
      ),
    );
  }

  // ── Helpers UI ──
  Widget _kpi(String label, String valor, ThemeData theme,
      {Color? color, String? sub}) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label.toUpperCase(),
          style: GoogleFonts.rajdhani(
            fontSize: 16,
            letterSpacing: 1,
            color: theme.colorScheme.onSurface.withValues(alpha: 0.6),
          ),
        ),
        const SizedBox(height: 2),
        Text(
          valor,
          style: GoogleFonts.spaceMono(
            fontSize: 22,
            fontWeight: FontWeight.w700,
            color: color ?? theme.colorScheme.onSurface,
          ),
        ),
        if (sub != null)
          Text(
            sub,
            style: GoogleFonts.rajdhani(
              fontSize: 14,
              color: theme.colorScheme.onSurface.withValues(alpha: 0.4),
            ),
          ),
      ],
    );
  }

  Widget _filaInfo(String label, String valor, ThemeData theme,
      {Color? color}) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(
          label,
          style: GoogleFonts.rajdhani(
            fontSize: 17,
            color: theme.colorScheme.onSurface.withValues(alpha: 0.8),
          ),
        ),
        Text(
          valor,
          style: GoogleFonts.spaceMono(
            fontSize: 17,
            fontWeight: FontWeight.w700,
            color: color ?? theme.colorScheme.onSurface,
          ),
        ),
      ],
    );
  }
}

class _Card extends StatelessWidget {
  final String titulo;
  final Widget child;
  const _Card({required this.titulo, required this.child});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: theme.colorScheme.onSurface.withValues(alpha: 0.08),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            titulo,
            style: GoogleFonts.rajdhani(
              fontSize: 16,
              fontWeight: FontWeight.w700,
              letterSpacing: 1.5,
              color: theme.colorScheme.primary,
            ),
          ),
          const SizedBox(height: 14),
          child,
        ],
      ),
    );
  }
}
