import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:google_fonts/google_fonts.dart';
import '../state/app_notifier.dart';
import '../theme/app_theme.dart';
import '../models/models.dart';
import '../widgets/widgets.dart';

class ProgresoScreen extends ConsumerWidget {
  const ProgresoScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    ref.watch(appProvider);
    final provider = ref.read(appProvider.notifier);
    final sesion = provider.sesionActual;
    final theme = Theme.of(context);

    if (sesion == null) {
      return Scaffold(
        appBar: AppBar(title: const Text('Calculando...')),
        body: const Center(child: CircularProgressIndicator()),
      );
    }

    final completado = sesion.estado == EstadoCalculo.completado;
    final hayError = sesion.estado == EstadoCalculo.error;

    return Scaffold(
      appBar: AppBar(
        title: Text(
          completado ? 'RESULTADOS' : 'CALCULANDO...',
          style: GoogleFonts.rajdhani(
            fontWeight: FontWeight.w700,
            letterSpacing: 2,
          ),
        ),
        leading: completado || hayError
            ? IconButton(
                icon: const Icon(Icons.arrow_back_rounded),
                onPressed: () => Navigator.pop(context),
              )
            : const SizedBox.shrink(),
        automaticallyImplyLeading: false,
      ),
      body: completado
          ? _PantallaResultados(sesion: sesion, provider: provider)
          : hayError
              ? _PantallaError(
                  error: provider.error ?? 'Error desconocido',
                  onReintentar: () => Navigator.pop(context),
                )
              : _PantallaProgreso(sesion: sesion),
    );
  }
}

// ═══════════════════════════════════════════════════════════
// PANTALLA DE PROGRESO EN TIEMPO REAL
// ═══════════════════════════════════════════════════════════
class _PantallaProgreso extends ConsumerWidget {
  final SesionPrediccion sesion;
  const _PantallaProgreso({required this.sesion});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    final convergiendo = sesion.estado == EstadoCalculo.convergiendo;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // ─── CABECERA DE PROGRESO ───
          Card(
            child: Padding(
              padding: const EdgeInsets.all(20),
              child: Column(
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      _PulsatingIcon(convergiendo: convergiendo),
                      const SizedBox(width: 12),
                      Text(
                        convergiendo
                            ? 'CONVERGIENDO...'
                            : 'ORACLE CLOUD TRABAJANDO',
                        style: GoogleFonts.rajdhani(
                          fontSize: 18,
                          fontWeight: FontWeight.w700,
                          letterSpacing: 1.5,
                          color: convergiendo
                              ? BonolotoTheme.amarillo
                              : BonolotoTheme.verdeAccent,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 6),
                  Text(
                    convergiendo
                        ? 'Optimizando hasta alcanzar el máximo posible...'
                        : 'Analizando ${sesion.cantidadSolicitada} combinaciones óptimas',
                    style: GoogleFonts.spaceMono(
                      fontSize: 15,
                      color: theme.colorScheme.onSurface.withValues(alpha: 0.6),
                    ),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 20),

                  // Barra de progreso general
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text(
                            'Progreso general',
                            style: GoogleFonts.spaceMono(fontSize: 15),
                          ),
                          Text(
                            '${(sesion.progresoGeneral * 100).toStringAsFixed(0)}%',
                            style: GoogleFonts.rajdhani(
                              fontSize: 17,
                              fontWeight: FontWeight.w700,
                              color: BonolotoTheme.verdeAccent,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 6),
                      ClipRRect(
                        borderRadius: BorderRadius.circular(6),
                        child: LinearProgressIndicator(
                          value: sesion.progresoGeneral,
                          minHeight: 10,
                          backgroundColor:
                              theme.colorScheme.onSurface.withValues(alpha: 0.1),
                          valueColor: const AlwaysStoppedAnimation<Color>(
                              BonolotoTheme.verdeAccent),
                        ),
                      ),
                    ],
                  ),

                  const SizedBox(height: 16),

                  // Índice de confianza actual
                  if (sesion.indiceConfianzaActual != null)
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: BonolotoTheme.amarillo.withValues(alpha: 0.08),
                        borderRadius: BorderRadius.circular(10),
                        border: Border.all(
                            color: BonolotoTheme.amarillo.withValues(alpha: 0.3)),
                      ),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          const Icon(Icons.insights_rounded,
                              color: BonolotoTheme.amarillo, size: 18),
                          const SizedBox(width: 8),
                          Text(
                            'Confianza actual: ',
                            style: GoogleFonts.spaceMono(fontSize: 16),
                          ),
                          Text(
                            '${sesion.indiceConfianzaActual!.toStringAsFixed(2)}%',
                            style: GoogleFonts.rajdhani(
                              fontSize: 22,
                              fontWeight: FontWeight.w700,
                              color: BonolotoTheme.amarillo,
                            ),
                          ),
                        ],
                      ),
                    ),

                  const SizedBox(height: 8),

                  // Iteración actual
                  Text(
                    'Iteración #${sesion.iteracion}',
                    style: GoogleFonts.spaceMono(
                      fontSize: 14,
                      color: theme.colorScheme.onSurface.withValues(alpha: 0.4),
                    ),
                  ),
                ],
              ),
            ),
          ),

          const SizedBox(height: 16),

          // ─── ALGORITMOS v3.0 AGRUPADOS ───
          _GrupoAlgoritmos(
            titulo: 'DIAGNÓSTICO Y PREPROCESAMIENTO',
            color: const Color(0xFFB84FFF),
            algoritmos: {
              'Diagnóstico': sesion.estadoAlgoritmos['Diagnóstico'] ?? EstadoAlgoritmo.pendiente,
              'Isolation Forest': sesion.estadoAlgoritmos['Isolation Forest'] ?? EstadoAlgoritmo.pendiente,
              'Test KS': sesion.estadoAlgoritmos['Test KS'] ?? EstadoAlgoritmo.pendiente,
              'Test Chi-cuadrado': sesion.estadoAlgoritmos['Test Chi-cuadrado'] ?? EstadoAlgoritmo.pendiente,
              'Decaimiento Exponencial': sesion.estadoAlgoritmos['Decaimiento Exponencial'] ?? EstadoAlgoritmo.pendiente,
              'Walk-Forward': sesion.estadoAlgoritmos['Walk-Forward'] ?? EstadoAlgoritmo.pendiente,
            },
          ).animate().fadeIn(duration: 300.ms, delay: 50.ms),

          const SizedBox(height: 8),

          _GrupoAlgoritmos(
            titulo: 'CAPA 1 — ANÁLISIS ESTADÍSTICO',
            color: BonolotoTheme.verdeAccent,
            algoritmos: {
              'Entropía': sesion.estadoAlgoritmos['Entropía'] ?? EstadoAlgoritmo.pendiente,
              'Hot/Cold Bias': sesion.estadoAlgoritmos['Hot/Cold Bias'] ?? EstadoAlgoritmo.pendiente,
              'Covarianza': sesion.estadoAlgoritmos['Covarianza'] ?? EstadoAlgoritmo.pendiente,
              'FFT Periodicidad': sesion.estadoAlgoritmos['FFT Periodicidad'] ?? EstadoAlgoritmo.pendiente,
              'Entropía Permutación': sesion.estadoAlgoritmos['Entropía Permutación'] ?? EstadoAlgoritmo.pendiente,
              'Features Estructurales': sesion.estadoAlgoritmos['Features Estructurales'] ?? EstadoAlgoritmo.pendiente,
              'Simetría Especular': sesion.estadoAlgoritmos['Simetría Especular'] ?? EstadoAlgoritmo.pendiente,
            },
          ).animate().fadeIn(duration: 300.ms, delay: 100.ms),

          const SizedBox(height: 8),

          _GrupoAlgoritmos(
            titulo: 'CAPA 2 — SERIES TEMPORALES',
            color: BonolotoTheme.colorInfo,
            algoritmos: {
              'LSTM': sesion.estadoAlgoritmos['LSTM'] ?? EstadoAlgoritmo.pendiente,
              'Transformer': sesion.estadoAlgoritmos['Transformer'] ?? EstadoAlgoritmo.pendiente,
              'Markov': sesion.estadoAlgoritmos['Markov'] ?? EstadoAlgoritmo.pendiente,
              'GRU': sesion.estadoAlgoritmos['GRU'] ?? EstadoAlgoritmo.pendiente,
              'Bi-LSTM': sesion.estadoAlgoritmos['Bi-LSTM'] ?? EstadoAlgoritmo.pendiente,
              'ARIMA': sesion.estadoAlgoritmos['ARIMA'] ?? EstadoAlgoritmo.pendiente,
              'SARIMA Estacional': sesion.estadoAlgoritmos['SARIMA Estacional'] ?? EstadoAlgoritmo.pendiente,
            },
          ).animate().fadeIn(duration: 300.ms, delay: 150.ms),

          const SizedBox(height: 8),

          _GrupoAlgoritmos(
            titulo: 'CAPA 3 — APRENDIZAJE',
            color: BonolotoTheme.amarillo,
            algoritmos: {
              'Bayesiano': sesion.estadoAlgoritmos['Bayesiano'] ?? EstadoAlgoritmo.pendiente,
              'XGBoost': sesion.estadoAlgoritmos['XGBoost'] ?? EstadoAlgoritmo.pendiente,
              'Reinforcement Learning': sesion.estadoAlgoritmos['Reinforcement Learning'] ?? EstadoAlgoritmo.pendiente,
              'HMM': sesion.estadoAlgoritmos['HMM'] ?? EstadoAlgoritmo.pendiente,
              'Información Mutua': sesion.estadoAlgoritmos['Información Mutua'] ?? EstadoAlgoritmo.pendiente,
              'Info. Mutua Condicional': sesion.estadoAlgoritmos['Info. Mutua Condicional'] ?? EstadoAlgoritmo.pendiente,
              'PCA Co-ocurrencia': sesion.estadoAlgoritmos['PCA Co-ocurrencia'] ?? EstadoAlgoritmo.pendiente,
            },
          ).animate().fadeIn(duration: 300.ms, delay: 200.ms),

          const SizedBox(height: 8),

          _GrupoAlgoritmos(
            titulo: 'CAPA 4 — ANÁLISIS TEMPORAL Y SEÑAL',
            color: const Color(0xFF00D4FF),
            algoritmos: {
              'Gaps Poisson': sesion.estadoAlgoritmos['Gaps Poisson'] ?? EstadoAlgoritmo.pendiente,
              'Test Runs': sesion.estadoAlgoritmos['Test Runs'] ?? EstadoAlgoritmo.pendiente,
              'Coef. Hurst': sesion.estadoAlgoritmos['Coef. Hurst'] ?? EstadoAlgoritmo.pendiente,
              'PACF': sesion.estadoAlgoritmos['PACF'] ?? EstadoAlgoritmo.pendiente,
              'Progresiones': sesion.estadoAlgoritmos['Progresiones'] ?? EstadoAlgoritmo.pendiente,
              'Posición Ordinal': sesion.estadoAlgoritmos['Posición Ordinal'] ?? EstadoAlgoritmo.pendiente,
              'Premios Secundarios': sesion.estadoAlgoritmos['Premios Secundarios'] ?? EstadoAlgoritmo.pendiente,
              'Complementario/Reintegro': sesion.estadoAlgoritmos['Complementario/Reintegro'] ?? EstadoAlgoritmo.pendiente,
            },
          ).animate().fadeIn(duration: 300.ms, delay: 250.ms),

          const SizedBox(height: 8),

          _GrupoAlgoritmos(
            titulo: 'CAPA 5 — ALGORITMOS CONDICIONALES',
            color: const Color(0xFFFF6B35),
            algoritmos: {
              'Monte Carlo': sesion.estadoAlgoritmos['Monte Carlo'] ?? EstadoAlgoritmo.pendiente,
              'EVT/GEV': sesion.estadoAlgoritmos['EVT/GEV'] ?? EstadoAlgoritmo.pendiente,
              'Proceso Dirichlet': sesion.estadoAlgoritmos['Proceso Dirichlet'] ?? EstadoAlgoritmo.pendiente,
              'Multi-Scale Entropy': sesion.estadoAlgoritmos['Multi-Scale Entropy'] ?? EstadoAlgoritmo.pendiente,
              'Cópulas Gaussianas': sesion.estadoAlgoritmos['Cópulas Gaussianas'] ?? EstadoAlgoritmo.pendiente,
              'Proceso Hawkes': sesion.estadoAlgoritmos['Proceso Hawkes'] ?? EstadoAlgoritmo.pendiente,
              'Multifractal DFA': sesion.estadoAlgoritmos['Multifractal DFA'] ?? EstadoAlgoritmo.pendiente,
              'Echo State Network': sesion.estadoAlgoritmos['Echo State Network'] ?? EstadoAlgoritmo.pendiente,
              'VAR Multivariante': sesion.estadoAlgoritmos['VAR Multivariante'] ?? EstadoAlgoritmo.pendiente,
              'TDA Topológico': sesion.estadoAlgoritmos['TDA Topológico'] ?? EstadoAlgoritmo.pendiente,
              'Exponente Lyapunov': sesion.estadoAlgoritmos['Exponente Lyapunov'] ?? EstadoAlgoritmo.pendiente,
              'Regresión Simbólica': sesion.estadoAlgoritmos['Regresión Simbólica'] ?? EstadoAlgoritmo.pendiente,
            },
          ).animate().fadeIn(duration: 300.ms, delay: 300.ms),

          const SizedBox(height: 8),

          _GrupoAlgoritmos(
            titulo: 'CAPA 6 — OPTIMIZACIÓN Y META-MODELO',
            color: const Color(0xFFFF4FA0),
            algoritmos: {
              'NSGA-II Multi-objetivo': sesion.estadoAlgoritmos['NSGA-II Multi-objetivo'] ?? EstadoAlgoritmo.pendiente,
              'Simulated Annealing': sesion.estadoAlgoritmos['Simulated Annealing'] ?? EstadoAlgoritmo.pendiente,
              'Rueda Combinatoria': sesion.estadoAlgoritmos['Rueda Combinatoria'] ?? EstadoAlgoritmo.pendiente,
              'Ensemble Stacking': sesion.estadoAlgoritmos['Ensemble Stacking'] ?? EstadoAlgoritmo.pendiente,
              'MoE Dinámico': sesion.estadoAlgoritmos['MoE Dinámico'] ?? EstadoAlgoritmo.pendiente,
              'Shapley Attribution': sesion.estadoAlgoritmos['Shapley Attribution'] ?? EstadoAlgoritmo.pendiente,
            },
          ).animate().fadeIn(duration: 300.ms, delay: 350.ms),

          const SizedBox(height: 8),

          _GrupoAlgoritmos(
            titulo: 'CAPA 7 — DESCOMPOSICIÓN AVANZADA',
            color: const Color(0xFF7B2FFF),
            algoritmos: {
              'SSA': sesion.estadoAlgoritmos['SSA'] ?? EstadoAlgoritmo.pendiente,
              'VMD': sesion.estadoAlgoritmos['VMD'] ?? EstadoAlgoritmo.pendiente,
              'EMD': sesion.estadoAlgoritmos['EMD'] ?? EstadoAlgoritmo.pendiente,
              'BOCPD': sesion.estadoAlgoritmos['BOCPD'] ?? EstadoAlgoritmo.pendiente,
              'RETAIN': sesion.estadoAlgoritmos['RETAIN'] ?? EstadoAlgoritmo.pendiente,
              'Lomb-Scargle': sesion.estadoAlgoritmos['Lomb-Scargle'] ?? EstadoAlgoritmo.pendiente,
              'TDA v2': sesion.estadoAlgoritmos['TDA v2'] ?? EstadoAlgoritmo.pendiente,
              'SAX Motivos': sesion.estadoAlgoritmos['SAX Motivos'] ?? EstadoAlgoritmo.pendiente,
              'MDL': sesion.estadoAlgoritmos['MDL'] ?? EstadoAlgoritmo.pendiente,
              'DWT Wavelet': sesion.estadoAlgoritmos['DWT Wavelet'] ?? EstadoAlgoritmo.pendiente,
              'GAT Grafo': sesion.estadoAlgoritmos['GAT Grafo'] ?? EstadoAlgoritmo.pendiente,
              'MaxEnt': sesion.estadoAlgoritmos['MaxEnt'] ?? EstadoAlgoritmo.pendiente,
              'N-BEATS': sesion.estadoAlgoritmos['N-BEATS'] ?? EstadoAlgoritmo.pendiente,
              'LNN/CfC': sesion.estadoAlgoritmos['LNN/CfC'] ?? EstadoAlgoritmo.pendiente,
            },
          ).animate().fadeIn(duration: 300.ms, delay: 400.ms),

          const SizedBox(height: 8),

          _GrupoAlgoritmos(
            titulo: 'PREPROCESAMIENTO — MEJORAS',
            color: const Color(0xFFB84FFF),
            algoritmos: {
              'Isolation Forest': sesion.estadoAlgoritmos['Isolation Forest'] ?? EstadoAlgoritmo.pendiente,
              'Caché Inteligente': sesion.estadoAlgoritmos['Caché Inteligente'] ?? EstadoAlgoritmo.pendiente,
              'Walk-Forward': sesion.estadoAlgoritmos['Walk-Forward'] ?? EstadoAlgoritmo.pendiente,
            },
          ).animate().fadeIn(duration: 300.ms, delay: 50.ms),

          const SizedBox(height: 10),

          _GrupoAlgoritmos(
            titulo: 'CAPA 1 — ANÁLISIS ESTADÍSTICO',
            color: BonolotoTheme.verdeAccent,
            algoritmos: {
              'Entropía': sesion.estadoAlgoritmos['Entropía'] ?? EstadoAlgoritmo.pendiente,
              'Hot/Cold Bias': sesion.estadoAlgoritmos['Hot/Cold Bias'] ?? EstadoAlgoritmo.pendiente,
              'Covarianza': sesion.estadoAlgoritmos['Covarianza'] ?? EstadoAlgoritmo.pendiente,
              'FFT Periodicidad': sesion.estadoAlgoritmos['FFT Periodicidad'] ?? EstadoAlgoritmo.pendiente,
            },
          ).animate().fadeIn(duration: 300.ms, delay: 100.ms),

          const SizedBox(height: 10),

          _GrupoAlgoritmos(
            titulo: 'CAPA 2 — SERIES TEMPORALES',
            color: BonolotoTheme.colorInfo,
            algoritmos: {
              'LSTM': sesion.estadoAlgoritmos['LSTM'] ?? EstadoAlgoritmo.pendiente,
              'Transformer': sesion.estadoAlgoritmos['Transformer'] ?? EstadoAlgoritmo.pendiente,
              'Markov': sesion.estadoAlgoritmos['Markov'] ?? EstadoAlgoritmo.pendiente,
            },
          ).animate().fadeIn(duration: 300.ms, delay: 150.ms),

          const SizedBox(height: 10),

          _GrupoAlgoritmos(
            titulo: 'CAPA 3 — APRENDIZAJE',
            color: BonolotoTheme.amarillo,
            algoritmos: {
              'Bayesiano': sesion.estadoAlgoritmos['Bayesiano'] ?? EstadoAlgoritmo.pendiente,
              'XGBoost': sesion.estadoAlgoritmos['XGBoost'] ?? EstadoAlgoritmo.pendiente,
              'Reinforcement Learning': sesion.estadoAlgoritmos['Reinforcement Learning'] ?? EstadoAlgoritmo.pendiente,
            },
          ).animate().fadeIn(duration: 300.ms, delay: 200.ms),

          const SizedBox(height: 10),

          _GrupoAlgoritmos(
            titulo: 'CAPA 4+5 — OPTIMIZACIÓN Y CONSENSO',
            color: const Color(0xFFFF6B35),
            algoritmos: {
              'Monte Carlo': sesion.estadoAlgoritmos['Monte Carlo'] ?? EstadoAlgoritmo.pendiente,
              'Algoritmo Genético (NSGA-II)': sesion.estadoAlgoritmos['Algoritmo Genético (NSGA-II)'] ?? EstadoAlgoritmo.pendiente,
              'Ensemble Stacking': sesion.estadoAlgoritmos['Ensemble Stacking'] ?? EstadoAlgoritmo.pendiente,
            },
          ).animate().fadeIn(duration: 300.ms, delay: 250.ms),

          const SizedBox(height: 24),

          // Info
          Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: theme.colorScheme.surface,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(
                  color: theme.colorScheme.onSurface.withValues(alpha: 0.05)),
            ),
            child: Row(
              children: [
                const Icon(Icons.info_outline_rounded,
                    color: BonolotoTheme.colorInfo, size: 16),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    'El sistema continuará iterando hasta que no pueda mejorar más el índice de confianza. No cierres la app.',
                    style: GoogleFonts.spaceMono(
                      fontSize: 14,
                      color: theme.colorScheme.onSurface.withValues(alpha: 0.6),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _PulsatingIcon extends ConsumerStatefulWidget {
  final bool convergiendo;
  const _PulsatingIcon({required this.convergiendo});

  @override
  ConsumerState<_PulsatingIcon> createState() => _PulsatingIconState();
}

class _PulsatingIconState extends ConsumerState<_PulsatingIcon>
    with SingleTickerProviderStateMixin {
  late AnimationController _ctrl;
  late Animation<double> _anim;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 800),
    )..repeat(reverse: true);
    _anim = Tween(begin: 0.6, end: 1.0).animate(_ctrl);
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _anim,
      builder: (_, __) => Opacity(
        opacity: _anim.value,
        child: Container(
          width: 14,
          height: 14,
          decoration: BoxDecoration(
            color: widget.convergiendo
                ? BonolotoTheme.amarillo
                : BonolotoTheme.verdeAccent,
            shape: BoxShape.circle,
          ),
        ),
      ),
    );
  }
}

class _FilaAlgoritmo extends ConsumerWidget {
  final String nombre;
  final EstadoAlgoritmo estado;
  final Color? colorGrupo;
  const _FilaAlgoritmo({required this.nombre, required this.estado, this.colorGrupo});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    final color = estado == EstadoAlgoritmo.procesando
        ? (colorGrupo ?? BonolotoTheme.verdeAccent)
        : _colorEstado(estado);
    final icono = _iconoEstado(estado);
    final etiqueta = _etiquetaEstado(estado);

    return Container(
      margin: const EdgeInsets.only(bottom: 4),
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.05),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: color.withValues(alpha: 0.15)),
      ),
      child: Row(
        children: [
          Icon(icono, color: color, size: 16),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              nombre,
              style: GoogleFonts.rajdhani(
                fontSize: 16,
                fontWeight: FontWeight.w600,
                color: theme.colorScheme.onSurface,
              ),
            ),
          ),
          if (estado == EstadoAlgoritmo.procesando)
            SizedBox(
              width: 12,
              height: 12,
              child: CircularProgressIndicator(
                color: color,
                strokeWidth: 2,
              ),
            )
          else
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
              decoration: BoxDecoration(
                color: color.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(5),
              ),
              child: Text(
                etiqueta,
                style: GoogleFonts.spaceMono(
                  fontSize: 14,
                  color: color,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
        ],
      ),
    );
  }

  Color _colorEstado(EstadoAlgoritmo e) {
    switch (e) {
      case EstadoAlgoritmo.pendiente:
        return Colors.grey;
      case EstadoAlgoritmo.procesando:
        return BonolotoTheme.verdeAccent;
      case EstadoAlgoritmo.completado:
        return BonolotoTheme.colorExito;
      case EstadoAlgoritmo.error:
        return BonolotoTheme.colorError;
    }
  }

  IconData _iconoEstado(EstadoAlgoritmo e) {
    switch (e) {
      case EstadoAlgoritmo.pendiente:
        return Icons.radio_button_unchecked_rounded;
      case EstadoAlgoritmo.procesando:
        return Icons.pending_rounded;
      case EstadoAlgoritmo.completado:
        return Icons.check_circle_rounded;
      case EstadoAlgoritmo.error:
        return Icons.error_rounded;
    }
  }

  String _etiquetaEstado(EstadoAlgoritmo e) {
    switch (e) {
      case EstadoAlgoritmo.pendiente:
        return 'ESPERA';
      case EstadoAlgoritmo.procesando:
        return 'ACTIVO';
      case EstadoAlgoritmo.completado:
        return 'LISTO';
      case EstadoAlgoritmo.error:
        return 'ERROR';
    }
  }
}

class _GrupoAlgoritmos extends ConsumerWidget {
  final String titulo;
  final Color color;
  final Map<String, EstadoAlgoritmo> algoritmos;

  const _GrupoAlgoritmos({
    required this.titulo,
    required this.color,
    required this.algoritmos,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Container(
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.04),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withValues(alpha: 0.15)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(12, 8, 12, 4),
            child: Text(
              titulo,
              style: GoogleFonts.rajdhani(
                fontSize: 14,
                fontWeight: FontWeight.w700,
                letterSpacing: 1.5,
                color: color,
              ),
            ),
          ),
          ...algoritmos.entries.map((entry) => Padding(
            padding: const EdgeInsets.fromLTRB(8, 0, 8, 2),
            child: _FilaAlgoritmo(
              nombre: entry.key,
              estado: entry.value,
              colorGrupo: color,
            ),
          )),
          const SizedBox(height: 6),
        ],
      ),
    );
  }
}

// ═══════════════════════════════════════════════════════════
// PANTALLA DE RESULTADOS
// ═══════════════════════════════════════════════════════════
class _PantallaResultados extends ConsumerWidget {
  final SesionPrediccion sesion;
  final AppNotifier provider;
  const _PantallaResultados(
      {required this.sesion, required this.provider});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);

    return Column(
      children: [
        // Cabecera de éxito
        Container(
          width: double.infinity,
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            gradient: LinearGradient(
              colors: [
                BonolotoTheme.verdeOscuro.withValues(alpha: 0.4),
                BonolotoTheme.verdeAccent.withValues(alpha: 0.1),
              ],
            ),
          ),
          child: Column(
            children: [
              const Icon(Icons.auto_awesome_rounded,
                      color: BonolotoTheme.amarillo, size: 36)
                  .animate()
                  .scale(duration: 400.ms, curve: Curves.elasticOut),
              const SizedBox(height: 8),
              Text(
                '¡CÁLCULO COMPLETADO!',
                style: GoogleFonts.rajdhani(
                  fontSize: 22,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 2,
                  color: Colors.white,
                ),
              ),
              Text(
                '${sesion.combinaciones.length} combinaciones óptimas generadas',
                style: GoogleFonts.spaceMono(
                  fontSize: 16,
                  color: BonolotoTheme.verdeAccent,
                ),
              ),
              if (sesion.fechaSorteoObjetivo != null)
                Padding(
                  padding: const EdgeInsets.only(top: 6),
                  child: Text(
                    'Para jugar en el sorteo del ${sesion.fechaSorteoTexto}',
                    textAlign: TextAlign.center,
                    style: GoogleFonts.rajdhani(
                      fontSize: 16,
                      fontWeight: FontWeight.w700,
                      color: BonolotoTheme.amarillo,
                    ),
                  ),
                ),
              const SizedBox(height: 8),
              if (sesion.combinaciones.isNotEmpty)
                Text(
                  'Confianza máxima: ${sesion.combinaciones.map((c) => c.indiceConfianza).reduce((a, b) => a > b ? a : b).toStringAsFixed(1)}%',
                  style: GoogleFonts.rajdhani(
                    fontSize: 16,
                    fontWeight: FontWeight.w700,
                    color: BonolotoTheme.amarillo,
                  ),
                ),
              if (sesion.combinaciones.isNotEmpty)
                Padding(
                  padding: const EdgeInsets.only(top: 4),
                  child: Text(
                    'Coste de jugarlas: ${sesion.costeTotalEur.toStringAsFixed(2)} €  '
                    '(${sesion.combinaciones.length} × 0,50 €)',
                    style: GoogleFonts.rajdhani(
                      fontSize: 15,
                      fontWeight: FontWeight.w600,
                      color: Colors.white,
                    ),
                  ),
                ),
            ],
          ),
        ),

        // Lista de combinaciones
        Expanded(
          child: ListView.builder(
            padding: const EdgeInsets.all(16),
            itemCount: sesion.combinaciones.length,
            itemBuilder: (ctx, i) => _TarjetaCombinacion(
              combinacion: sesion.combinaciones[i],
              indice: i + 1,
            )
                .animate()
                .fadeIn(duration: 300.ms, delay: (i * 80).ms)
                .slideY(begin: 0.2, end: 0),
          ),
        ),

        // Botones de acción
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: theme.cardColor,
            border: Border(
              top: BorderSide(
                  color: theme.colorScheme.onSurface.withValues(alpha: 0.08)),
            ),
          ),
          child: Row(
            children: [
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: () => _mostrarMenuExportar(context),
                  icon: const Icon(Icons.download_rounded, size: 18),
                  label: Text('EXPORTAR',
                      style: GoogleFonts.rajdhani(
                          fontWeight: FontWeight.w700, letterSpacing: 1)),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: BonolotoTheme.verdeAccent,
                    side: const BorderSide(color: BonolotoTheme.verdeAccent),
                    padding: const EdgeInsets.symmetric(vertical: 12),
                  ),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: ElevatedButton.icon(
                  onPressed: () => Navigator.pop(context),
                  icon: const Icon(Icons.home_rounded, size: 18),
                  label: Text('INICIO',
                      style: GoogleFonts.rajdhani(
                          fontWeight: FontWeight.w700, letterSpacing: 1)),
                  style: ElevatedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(vertical: 12),
                  ),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  void _mostrarMenuExportar(BuildContext context) {
    showModalBottomSheet(
      context: context,
      backgroundColor: Theme.of(context).cardColor,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (_) => Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('EXPORTAR COMBINACIONES',
                style: GoogleFonts.rajdhani(
                  fontSize: 18,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 1.5,
                  color: BonolotoTheme.verdeAccent,
                )),
            const SizedBox(height: 20),
            _ItemExportar(
              icono: Icons.table_chart_rounded,
              etiqueta: 'Descargar como CSV',
              color: Colors.green,
              onTap: () async {
                Navigator.pop(context);
                final messenger = ScaffoldMessenger.of(context);
                final ruta = await provider.descargarCombinaciones(
                    sesion.combinaciones, 'csv');
                messenger.showSnackBar(SnackBar(
                  content: Text(ruta != null
                      ? 'Guardado en: $ruta'
                      : 'No se pudo guardar el archivo'),
                ));
              },
            ),
            _ItemExportar(
              icono: Icons.text_snippet_rounded,
              etiqueta: 'Descargar como TXT',
              color: BonolotoTheme.colorInfo,
              onTap: () async {
                Navigator.pop(context);
                final messenger = ScaffoldMessenger.of(context);
                final ruta = await provider.descargarCombinaciones(
                    sesion.combinaciones, 'txt');
                messenger.showSnackBar(SnackBar(
                  content: Text(ruta != null
                      ? 'Guardado en: $ruta'
                      : 'No se pudo guardar el archivo'),
                ));
              },
            ),
            const Divider(height: 8),
            _ItemExportar(
              icono: Icons.sticky_note_2_rounded,
              etiqueta: 'Copiar como nota',
              color: BonolotoTheme.amarillo,
              onTap: () {
                Navigator.pop(context);
                mostrarNotaParaCopiar(
                    context, provider.notaCombinaciones(sesion.combinaciones));
              },
            ),
          ],
        ),
      ),
    );
  }
}

class _ItemExportar extends ConsumerWidget {
  final IconData icono;
  final String etiqueta;
  final Color color;
  final VoidCallback onTap;

  const _ItemExportar({
    required this.icono,
    required this.etiqueta,
    required this.color,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return ListTile(
      onTap: onTap,
      leading: Container(
        width: 40,
        height: 40,
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(10),
        ),
        child: Icon(icono, color: color, size: 22),
      ),
      title: Text(
        etiqueta,
        style: GoogleFonts.rajdhani(
          fontSize: 17,
          fontWeight: FontWeight.w600,
        ),
      ),
      trailing: const Icon(Icons.chevron_right_rounded),
    );
  }
}

class _TarjetaCombinacion extends ConsumerWidget {
  final CombinacionBonoloto combinacion;
  final int indice;
  const _TarjetaCombinacion(
      {required this.combinacion, required this.indice});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    final confianza = combinacion.indiceConfianza;

    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  width: 28,
                  height: 28,
                  decoration: BoxDecoration(
                    color: BonolotoTheme.verdeAccent.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(
                        color: BonolotoTheme.verdeAccent.withValues(alpha: 0.3)),
                  ),
                  child: Center(
                    child: Text(
                      '$indice',
                      style: GoogleFonts.rajdhani(
                        fontSize: 17,
                        fontWeight: FontWeight.w700,
                        color: BonolotoTheme.verdeAccent,
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 10),
                Text(
                  'Combinación $indice',
                  style: theme.textTheme.titleLarge,
                ),
                const Spacer(),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: _colorConfianza(confianza).withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(
                        color: _colorConfianza(confianza).withValues(alpha: 0.4)),
                  ),
                  child: Text(
                    '${confianza.toStringAsFixed(1)}%',
                    style: GoogleFonts.rajdhani(
                      fontSize: 17,
                      fontWeight: FontWeight.w700,
                      color: _colorConfianza(confianza),
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 14),
            BolasNumerosWidget(numeros: combinacion.numeros, tamano: 44),
            const SizedBox(height: 12),
            BarraConfianzaWidget(valor: confianza),
            const SizedBox(height: 6),
            // Banda de confianza bootstrap
            if (combinacion.icInferior != null && combinacion.icSuperior != null)
              Row(
                children: [
                  const Icon(Icons.analytics_rounded,
                      size: 11, color: BonolotoTheme.colorInfo),
                  const SizedBox(width: 4),
                  Text(
                    'Banda 90%: ${combinacion.icInferior!.toStringAsFixed(1)}% — ${combinacion.icSuperior!.toStringAsFixed(1)}%',
                    style: GoogleFonts.spaceMono(
                      fontSize: 14,
                      color: BonolotoTheme.colorInfo,
                    ),
                  ),
                ],
              ),
            if (combinacion.aciertos != null) ...[
              const SizedBox(height: 6),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: BonolotoTheme.amarillo.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(color: BonolotoTheme.amarillo.withValues(alpha: 0.3)),
                ),
                child: Text(
                  '${combinacion.aciertos} aciertos en sorteo oficial',
                  style: GoogleFonts.rajdhani(
                    fontSize: 15, fontWeight: FontWeight.w700,
                    color: BonolotoTheme.amarillo),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Color _colorConfianza(double v) {
    if (v >= 70) return BonolotoTheme.colorExito;
    if (v >= 40) return BonolotoTheme.amarillo;
    return BonolotoTheme.colorInfo;
  }
}

// ═══════════════════════════════════════════════════════════
// PANTALLA DE ERROR
// ═══════════════════════════════════════════════════════════
class _PantallaError extends ConsumerWidget {
  final String error;
  final VoidCallback onReintentar;
  const _PantallaError({required this.error, required this.onReintentar});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.cloud_off_rounded,
                    color: BonolotoTheme.colorError, size: 64)
                .animate()
                .scale(duration: 400.ms),
            const SizedBox(height: 20),
            Text(
              'ERROR DE CÁLCULO',
              style: GoogleFonts.rajdhani(
                fontSize: 22,
                fontWeight: FontWeight.w700,
                color: BonolotoTheme.colorError,
              ),
            ),
            const SizedBox(height: 10),
            Text(
              error,
              style: GoogleFonts.spaceMono(fontSize: 16),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 30),
            ElevatedButton.icon(
              onPressed: onReintentar,
              icon: const Icon(Icons.arrow_back_rounded),
              label: Text('VOLVER',
                  style: GoogleFonts.rajdhani(fontWeight: FontWeight.w700)),
            ),
          ],
        ),
      ),
    );
  }
}
