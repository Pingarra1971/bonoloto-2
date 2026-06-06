import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:google_fonts/google_fonts.dart';
import '../state/app_notifier.dart';
import '../theme/app_theme.dart';
import '../models/models.dart';
import '../widgets/widgets.dart';

// ═══════════════════════════════════════════════════════════
// HISTORIAL SCREEN
// ═══════════════════════════════════════════════════════════
class HistorialScreen extends ConsumerWidget {
  const HistorialScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    ref.watch(appProvider);
    final provider = ref.read(appProvider.notifier);
    final historial = provider.historial;
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(
        title: Text('HISTORIAL',
            style: GoogleFonts.rajdhani(
                fontWeight: FontWeight.w700, letterSpacing: 2)),
      ),
      body: historial.isEmpty
          ? Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Icon(Icons.history_rounded,
                      color: BonolotoTheme.verdeAccent, size: 56),
                  const SizedBox(height: 16),
                  Text(
                    'Sin predicciones aún',
                    style: GoogleFonts.rajdhani(
                        fontSize: 20, fontWeight: FontWeight.w600),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Realiza tu primer cálculo para verlo aquí',
                    style: GoogleFonts.spaceMono(fontSize: 15),
                  ),
                ],
              ),
            )
          : ListView.builder(
              padding: const EdgeInsets.all(16),
              itemCount: historial.length,
              itemBuilder: (ctx, i) {
                final sesion = historial[i];
                return _TarjetaSesion(sesion: sesion, provider: provider)
                    .animate()
                    .fadeIn(duration: 300.ms, delay: (i * 60).ms)
                    .slideY(begin: 0.1, end: 0);
              },
            ),
    );
  }
}

class _TarjetaSesion extends ConsumerWidget {
  final SesionPrediccion sesion;
  final AppNotifier provider;
  const _TarjetaSesion({required this.sesion, required this.provider});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    final fecha = sesion.fechaSolicitud;
    final totalAciertos = sesion.combinaciones
        .where((c) => c.aciertos != null)
        .fold(0, (sum, c) => sum + (c.aciertos ?? 0));
    final tieneAciertos =
        sesion.combinaciones.any((c) => c.aciertos != null);

    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: ExpansionTile(
        tilePadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
        childrenPadding:
            const EdgeInsets.fromLTRB(16, 0, 16, 16),
        leading: Container(
          width: 44,
          height: 44,
          decoration: BoxDecoration(
            color: BonolotoTheme.verdeAccent.withValues(alpha: 0.1),
            borderRadius: BorderRadius.circular(10),
            border: Border.all(
                color: BonolotoTheme.verdeAccent.withValues(alpha: 0.3)),
          ),
          child: Center(
            child: Text(
              '${sesion.combinaciones.length}',
              style: GoogleFonts.rajdhani(
                fontSize: 20,
                fontWeight: FontWeight.w700,
                color: BonolotoTheme.verdeAccent,
              ),
            ),
          ),
        ),
        title: Text(
          '${fecha.day.toString().padLeft(2, '0')}/${fecha.month.toString().padLeft(2, '0')}/${fecha.year}',
          style: GoogleFonts.rajdhani(
            fontSize: 16,
            fontWeight: FontWeight.w700,
          ),
        ),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '${sesion.combinaciones.length} combinaciones',
              style: GoogleFonts.spaceMono(fontSize: 14),
            ),
            if (tieneAciertos)
              Text(
                'Total aciertos: $totalAciertos',
                style: GoogleFonts.spaceMono(
                  fontSize: 14,
                  color: BonolotoTheme.amarillo,
                ),
              ),
          ],
        ),
        trailing: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            if (sesion.combinaciones.isNotEmpty)
              Text(
                '${sesion.combinaciones.first.indiceConfianza.toStringAsFixed(1)}%',
                style: GoogleFonts.rajdhani(
                  fontSize: 17,
                  fontWeight: FontWeight.w700,
                  color: BonolotoTheme.verdeAccent,
                ),
              ),
            Text(
              'confianza',
              style: GoogleFonts.spaceMono(fontSize: 14),
            ),
          ],
        ),
        children: [
          const Divider(height: 1),
          const SizedBox(height: 12),
          ...sesion.combinaciones.asMap().entries.map((entry) {
            final i = entry.key;
            final combo = entry.value;
            return Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Text(
                      'Combinación ${i + 1}',
                      style: GoogleFonts.rajdhani(
                        fontSize: 16,
                        fontWeight: FontWeight.w600,
                        color: BonolotoTheme.verdeAccent,
                      ),
                    ),
                    const Spacer(),
                    if (combo.aciertos != null)
                      Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 8, vertical: 2),
                        decoration: BoxDecoration(
                          color: BonolotoTheme.amarillo.withValues(alpha: 0.15),
                          borderRadius: BorderRadius.circular(6),
                        ),
                        child: Text(
                          '${combo.aciertos} aciertos',
                          style: GoogleFonts.rajdhani(
                            fontSize: 15,
                            fontWeight: FontWeight.w700,
                            color: BonolotoTheme.amarillo,
                          ),
                        ),
                      ),
                  ],
                ),
                const SizedBox(height: 6),
                BolasNumerosWidget(numeros: combo.numeros, tamano: 34),
                const SizedBox(height: 10),
              ],
            );
          }).toList(),
          Row(
            children: [
              OutlinedButton.icon(
                onPressed: () =>
                    _mostrarMenuExportar(context, sesion.combinaciones),
                icon: const Icon(Icons.download_rounded, size: 16),
                label: Text('EXPORTAR',
                    style: GoogleFonts.rajdhani(
                        fontSize: 16, fontWeight: FontWeight.w700)),
                style: OutlinedButton.styleFrom(
                  foregroundColor: BonolotoTheme.verdeAccent,
                  side:
                      const BorderSide(color: BonolotoTheme.verdeAccent),
                  padding:
                      const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  void _mostrarMenuExportar(
      BuildContext context, List<CombinacionBonoloto> combinaciones) {
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
          children: [
            Text('EXPORTAR',
                style: GoogleFonts.rajdhani(
                    fontSize: 18,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 1.5,
                    color: BonolotoTheme.verdeAccent)),
            const SizedBox(height: 16),
            ListTile(
              leading: const Icon(Icons.picture_as_pdf_rounded,
                  color: Colors.redAccent),
              title: Text('PDF',
                  style: GoogleFonts.rajdhani(fontWeight: FontWeight.w600)),
              onTap: () {
                Navigator.pop(context);
                provider.exportarCombinaciones(combinaciones, 'pdf');
              },
            ),
            ListTile(
              leading:
                  const Icon(Icons.table_chart_rounded, color: Colors.green),
              title: Text('Excel / CSV',
                  style: GoogleFonts.rajdhani(fontWeight: FontWeight.w600)),
              onTap: () {
                Navigator.pop(context);
                provider.exportarCombinaciones(combinaciones, 'csv');
              },
            ),
            ListTile(
              leading: const Icon(Icons.text_snippet_rounded,
                  color: BonolotoTheme.colorInfo),
              title: Text('TXT',
                  style: GoogleFonts.rajdhani(fontWeight: FontWeight.w600)),
              onTap: () {
                Navigator.pop(context);
                provider.exportarCombinaciones(combinaciones, 'txt');
              },
            ),
          ],
        ),
      ),
    );
  }
}

// ═══════════════════════════════════════════════════════════
// TUTORIAL SCREEN
// ═══════════════════════════════════════════════════════════
class TutorialScreen extends ConsumerWidget {
  const TutorialScreen({super.key});

  static final List<_InfoAlgoritmo> _mejoras = [
    _InfoAlgoritmo(
      nombre: 'FFT — Detección de Ciclos',
      icono: Icons.waves_rounded,
      color: Color(0xFF00D4FF),
      capa: 'MEJORA 1 — PERIODICIDAD',
      descripcion:
          'Aplica la Transformada Rápida de Fourier sobre la serie temporal de apariciones de cada número. Detecta ciclos dominantes (periodos en número de sorteos) y puntúa más alto los números cuyo próximo pico de ciclo está más cercano. Activo desde el primer día con datos históricos reales.',
      fortaleza: 'Detección de patrones cíclicos ocultos',
    ),
    _InfoAlgoritmo(
      nombre: 'Isolation Forest',
      icono: Icons.filter_alt_rounded,
      color: Color(0xFFB84FFF),
      capa: 'MEJORA 2 — ANOMALÍAS',
      descripcion:
          'Detecta y filtra automáticamente sorteos estadísticamente anómalos antes de entrenar los modelos. Construye árboles de aislamiento: los sorteos anómalos se aíslan más rápido que los normales. Evita que datos "envenenados" distorsionen las predicciones. Nunca filtra más del 10% del histórico.',
      fortaleza: 'Limpieza automática de datos atípicos',
    ),
    _InfoAlgoritmo(
      nombre: 'Walk-Forward Validation',
      icono: Icons.trending_up_rounded,
      color: Color(0xFF39C96E),
      capa: 'MEJORA 3 — VALIDACIÓN REAL',
      descripcion:
          'Divide el histórico en 5 ventanas temporales y mide el error real de cada algoritmo en datos que no vio. Los pesos del meta-modelo se calibran con métricas empíricamente validadas, no estimadas. Desde el primer día usa métricas teóricas calibradas que se refinan con cada sorteo real.',
      fortaleza: 'Precisión medida empíricamente, no estimada',
    ),
    _InfoAlgoritmo(
      nombre: 'Caché Inteligente',
      icono: Icons.bolt_rounded,
      color: Color(0xFFFFD100),
      capa: 'MEJORA 4 — EFICIENCIA',
      descripcion:
          'Almacena los scores de cada algoritmo con un hash del histórico actual. Si el histórico no ha cambiado desde el último cálculo (no hay sorteo nuevo), reutiliza los scores directamente en lugar de recalcularlos. Reduce el tiempo de convergencia un 60-70% en el segundo cálculo del día.',
      fortaleza: 'Reducción de tiempo de cálculo del 60-70%',
    ),
    _InfoAlgoritmo(
      nombre: 'NSGA-II Multi-objetivo',
      icono: Icons.account_tree_rounded,
      color: Color(0xFFFF6B35),
      capa: 'MEJORA 5 — EVOLUCIÓN AVANZADA',
      descripcion:
          'Sustituye al Algoritmo Genético simple por NSGA-II, que optimiza simultáneamente 4 objetivos: score estadístico, balance par/impar, suma en rango óptimo y cobertura de decenas. Genera una frontera de Pareto de combinaciones no dominadas, donde ninguna es mejor en todos los objetivos simultáneamente.',
      fortaleza: 'Optimización simultánea de 4 objetivos',
    ),
    _InfoAlgoritmo(
      nombre: 'Ensemble Stacking v2',
      icono: Icons.layers_rounded,
      color: Color(0xFFFF4FA0),
      capa: 'MEJORA 6 — META-APRENDIZAJE',
      descripcion:
          'En lugar de una media ponderada fija, un meta-modelo de regresión con SGD y regularización Ridge ajusta CÓMO combinar los outputs de los 115 algoritmos. Se actualiza tras cada sorteo. Nota honesta: este ajuste optimiza la combinación de scores, pero no aumenta la probabilidad de acertar un sorteo aleatorio — ningún método puede hacerlo.',
      fortaleza: 'Combinación de scores ajustada automáticamente',
    ),
    _InfoAlgoritmo(
      nombre: 'Entropía',
      icono: Icons.waves_rounded,
      color: Color(0xFF00D4FF),
      capa: 'CAPA 1 — ANÁLISIS ESTADÍSTICO',
      descripcion:
          'Mide el grado de desorden o aleatoriedad real del sistema de sorteos. Si la entropía detecta que ciertos números se desvían de la distribución esperada, los marca como candidatos estadísticamente relevantes. Es el primer filtro del sistema.',
      fortaleza: 'Detección de sesgos estadísticos',
    ),
    _InfoAlgoritmo(
      nombre: 'Hot/Cold Bias',
      icono: Icons.thermostat_rounded,
      color: Color(0xFFFF6B35),
      capa: 'CAPA 1 — ANÁLISIS ESTADÍSTICO',
      descripcion:
          'Clasifica cada número del 1 al 49 como "caliente" (sobrerepresentado), "frío" (infrarepresentado) o "neutro" basándose en ventanas temporales dinámicas: últimos 50, 100 y 500 sorteos. Detecta micro-sesgos mecánicos de la máquina.',
      fortaleza: 'Análisis de tendencias temporales',
    ),
    _InfoAlgoritmo(
      nombre: 'Análisis de Covarianza',
      icono: Icons.scatter_plot_rounded,
      color: Color(0xFFB84FFF),
      capa: 'CAPA 1 — ANÁLISIS ESTADÍSTICO',
      descripcion:
          'Construye una matriz de co-ocurrencia que identifica qué pares o tríos de números aparecen juntos con una frecuencia estadísticamente significativa, por encima de lo esperado por pura aleatoriedad. Alimenta al resto de algoritmos.',
      fortaleza: 'Identificación de patrones de pares',
    ),
    _InfoAlgoritmo(
      nombre: 'LSTM',
      icono: Icons.timeline_rounded,
      color: Color(0xFF39C96E),
      capa: 'CAPA 2 — SERIES TEMPORALES',
      descripcion:
          'Red neuronal recurrente especializada en memorizar dependencias a largo plazo en secuencias de datos. Analiza el histórico completo de sorteos como una serie temporal y aprende qué patrones de números tienden a seguir a otros.',
      fortaleza: 'Memoria a largo plazo de secuencias',
    ),
    _InfoAlgoritmo(
      nombre: 'Transformer + Atención',
      icono: Icons.auto_awesome_rounded,
      color: Color(0xFFFFD100),
      capa: 'CAPA 2 — SERIES TEMPORALES',
      descripcion:
          'Arquitectura Transformer con mecanismo de atención (la misma familia técnica que usan los grandes modelos de lenguaje). Pondera qué partes del histórico pesan más al construir su representación. Nota honesta: detecta estructura en datos pasados, pero en un sorteo aleatorio esa estructura es ruido y no anticipa el resultado futuro.',
      fortaleza: 'Mecanismo de atención sobre el histórico',
    ),
    _InfoAlgoritmo(
      nombre: 'Cadenas de Markov',
      icono: Icons.account_tree_rounded,
      color: Color(0xFF00BFFF),
      capa: 'CAPA 2 — SERIES TEMPORALES',
      descripcion:
          'Modela las transiciones entre estados: qué números tienen más probabilidad de aparecer dado el resultado del sorteo anterior. Construye una matriz de transición que captura dependencias entre sorteos consecutivos.',
      fortaleza: 'Dependencias entre sorteos consecutivos',
    ),
    _InfoAlgoritmo(
      nombre: 'Bayesiano',
      icono: Icons.calculate_rounded,
      color: Color(0xFFFF4FA0),
      capa: 'CAPA 3 — APRENDIZAJE',
      descripcion:
          'Actualiza las probabilidades de cada número de forma continua tras cada nuevo sorteo usando el Teorema de Bayes. Combina el conocimiento previo (histórico) con la nueva evidencia (último resultado) para refinar las predicciones.',
      fortaleza: 'Actualización continua de probabilidades',
    ),
    _InfoAlgoritmo(
      nombre: 'XGBoost + Gradient Boosting',
      icono: Icons.forest_rounded,
      color: Color(0xFF8BC34A),
      capa: 'CAPA 3 — APRENDIZAJE',
      descripcion:
          'Campeón consistente en competiciones de Machine Learning. Combina cientos de árboles de decisión en un modelo extremadamente robusto. Analiza variables como frecuencia, distancia entre apariciones, suma total y distribución par/impar.',
      fortaleza: 'Máxima precisión en clasificación',
    ),
    _InfoAlgoritmo(
      nombre: 'Reinforcement Learning',
      icono: Icons.psychology_rounded,
      color: Color(0xFFFF8C00),
      capa: 'CAPA 3 — APRENDIZAJE',
      descripcion:
          'Aprende por ensayo-error igual que DeepMind para el ajedrez. El agente recibe "recompensa" cuando una combinación generada coincide parcialmente con sorteos reales, ajustando su estrategia de selección continuamente.',
      fortaleza: 'Aprendizaje autónomo por experiencia',
    ),
    _InfoAlgoritmo(
      nombre: 'Monte Carlo',
      icono: Icons.casino_rounded,
      color: Color(0xFF00A651),
      capa: 'CAPA 4 — OPTIMIZACIÓN',
      descripcion:
          'Simula millones de escenarios de sorteo posibles usando números aleatorios para estimar distribuciones de probabilidad. Cuanto más iteraciones, más precisa la estimación. Es la base de la simulación estadística moderna.',
      fortaleza: 'Simulación masiva de escenarios',
    ),
    _InfoAlgoritmo(
      nombre: 'Algoritmo Genético',
      icono: Icons.biotech_rounded,
      color: Color(0xFF8B4513),
      capa: 'CAPA 4 — OPTIMIZACIÓN',
      descripcion:
          'Simula la evolución natural: genera miles de combinaciones candidatas, las evalúa con una función de aptitud estadística, descarta las peores y "cruza" las mejores para generar una nueva generación de combinaciones superiores. Proceso iterativo.',
      fortaleza: 'Optimización evolutiva convergente',
    ),
  ];

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(
        title: Text('TUTORIAL',
            style: GoogleFonts.rajdhani(
                fontWeight: FontWeight.w700, letterSpacing: 2)),
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // Intro
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      const Icon(Icons.info_rounded,
                          color: BonolotoTheme.amarillo),
                      const SizedBox(width: 8),
                      Text('¿CÓMO FUNCIONA EL SISTEMA?',
                          style: GoogleFonts.rajdhani(
                            fontSize: 16,
                            fontWeight: FontWeight.w700,
                            letterSpacing: 1,
                            color: BonolotoTheme.amarillo,
                          )),
                    ],
                  ),
                  const SizedBox(height: 12),
                  Text(
                    'El motor de Oracle Cloud ejecuta 115 algoritmos en varias capas. Cada algoritmo analiza el histórico de sorteos desde un enfoque diferente. El meta-modelo de consenso pondera los resultados y genera combinaciones con un índice de confianza interno del 0 al 100%. Importante: ese índice mide el acuerdo entre algoritmos, NO la probabilidad de acertar. En un sorteo aleatorio todas las combinaciones tienen la misma probabilidad.',
                    style: GoogleFonts.spaceMono(fontSize: 15, height: 1.6),
                  ),
                  const SizedBox(height: 12),
                  Container(
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: BonolotoTheme.colorError.withValues(alpha: 0.08),
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(
                          color: BonolotoTheme.colorError.withValues(alpha: 0.3)),
                    ),
                    child: Row(
                      children: [
                        const Icon(Icons.warning_rounded,
                            color: BonolotoTheme.colorError, size: 16),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            'La Bonoloto es un sistema certificado de aleatoriedad. Este sistema maximiza la cobertura estadística pero no garantiza ningún premio.',
                            style: GoogleFonts.spaceMono(
                                fontSize: 14,
                                color: BonolotoTheme.colorError),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          )
              .animate()
              .fadeIn(duration: 400.ms)
              .slideY(begin: 0.1, end: 0),

          const SizedBox(height: 16),

          Text('LAS MEJORAS AVANZADAS',
              style: theme.textTheme.labelLarge?.copyWith(
                letterSpacing: 2,
                color: BonolotoTheme.colorInfo,
              )),
          const SizedBox(height: 10),

          ..._mejoras.asMap().entries.map((entry) {
            final i = entry.key;
            final alg = entry.value;
            return _TarjetaAlgoritmo(info: alg)
                .animate()
                .fadeIn(duration: 300.ms, delay: (i * 60).ms)
                .slideX(begin: -0.1, end: 0);
          }).toList(),

          const SizedBox(height: 16),

          Text('LOS ALGORITMOS BASE',
              style: theme.textTheme.labelLarge?.copyWith(
                letterSpacing: 2,
                color: BonolotoTheme.verdeAccent,
              )),
          const SizedBox(height: 10),

          const Padding(
            padding: EdgeInsets.symmetric(vertical: 8),
            child: Text(
              'El sistema combina más de 100 técnicas estadísticas en el '
              'servidor (LSTM, Transformer, Markov, Monte Carlo, Bayesiano, '
              'algoritmos genéticos y muchas más). Todas buscan equilibrar '
              'las combinaciones, pero ninguna aumenta la probabilidad de '
              'acertar: la Bonoloto es un sorteo aleatorio.',
            ),
          ),

          const SizedBox(height: 16),

          // Meta-modelo
          Card(
            child: Container(
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(16),
                gradient: LinearGradient(
                  colors: [
                    BonolotoTheme.verdeOscuro.withValues(alpha: 0.3),
                    BonolotoTheme.amarillo.withValues(alpha: 0.1),
                  ],
                ),
              ),
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        const Icon(Icons.hub_rounded,
                            color: BonolotoTheme.amarillo),
                        const SizedBox(width: 8),
                        Text('CAPA 5 — META-MODELO DE CONSENSO',
                            style: GoogleFonts.rajdhani(
                              fontSize: 17,
                              fontWeight: FontWeight.w700,
                              letterSpacing: 1,
                              color: BonolotoTheme.amarillo,
                            )),
                      ],
                    ),
                    const SizedBox(height: 10),
                    Text(
                      'No confía ciegamente en ningún algoritmo. Aprende cuál ha tenido mejor rendimiento histórico y ajusta los pesos dinámicamente. Combina los 11 resultados en una predicción final con convergencia automática: sigue iterando hasta que no puede mejorar más el índice de confianza.',
                      style: GoogleFonts.spaceMono(fontSize: 15, height: 1.6),
                    ),
                  ],
                ),
              ),
            ),
          ).animate().fadeIn(duration: 400.ms, delay: 700.ms),

          const SizedBox(height: 32),
        ],
      ),
    );
  }
}

class _InfoAlgoritmo {
  final String nombre;
  final IconData icono;
  final Color color;
  final String capa;
  final String descripcion;
  final String fortaleza;

  const _InfoAlgoritmo({
    required this.nombre,
    required this.icono,
    required this.color,
    required this.capa,
    required this.descripcion,
    required this.fortaleza,
  });
}

class _TarjetaAlgoritmo extends ConsumerWidget {
  final _InfoAlgoritmo info;
  const _TarjetaAlgoritmo({required this.info});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Card(
      margin: const EdgeInsets.only(bottom: 10),
      child: ExpansionTile(
        leading: Container(
          width: 40,
          height: 40,
          decoration: BoxDecoration(
            color: info.color.withValues(alpha: 0.12),
            borderRadius: BorderRadius.circular(10),
          ),
          child: Icon(info.icono, color: info.color, size: 22),
        ),
        title: Text(info.nombre,
            style: GoogleFonts.rajdhani(
                fontSize: 17, fontWeight: FontWeight.w700)),
        subtitle: Text(info.capa,
            style: GoogleFonts.spaceMono(
                fontSize: 14,
                color: info.color,
                fontWeight: FontWeight.bold)),
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Divider(),
                const SizedBox(height: 8),
                Text(info.descripcion,
                    style:
                        GoogleFonts.spaceMono(fontSize: 15, height: 1.6)),
                const SizedBox(height: 10),
                Container(
                  padding: const EdgeInsets.symmetric(
                      horizontal: 10, vertical: 6),
                  decoration: BoxDecoration(
                    color: info.color.withValues(alpha: 0.08),
                    borderRadius: BorderRadius.circular(8),
                    border:
                        Border.all(color: info.color.withValues(alpha: 0.3)),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.star_rounded, color: info.color, size: 14),
                      const SizedBox(width: 6),
                      Text(
                        'Fortaleza: ${info.fortaleza}',
                        style: GoogleFonts.spaceMono(
                          fontSize: 14,
                          color: info.color,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ],
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

// ═══════════════════════════════════════════════════════════
// AJUSTES SCREEN
// ═══════════════════════════════════════════════════════════
class AjustesScreen extends ConsumerWidget {
  const AjustesScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    ref.watch(appProvider);
    final provider = ref.read(appProvider.notifier);
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(
        title: Text('AJUSTES',
            style: GoogleFonts.rajdhani(
                fontWeight: FontWeight.w700, letterSpacing: 2)),
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // Apariencia
          _SeccionAjustes(titulo: 'APARIENCIA', items: [
            _ItemSwitch(
              icono: Icons.dark_mode_rounded,
              etiqueta: 'Modo oscuro',
              valor: provider.config.modoOscuro,
              onChange: (v) {
                provider.toggleTema();
              },
            ),
          ]),

          const SizedBox(height: 16),

          // Notificaciones
          _SeccionAjustes(titulo: 'NOTIFICACIONES', items: [
            _ItemSwitch(
              icono: Icons.notifications_rounded,
              etiqueta: 'Notificaciones activas',
              valor: provider.config.notificacionesActivas,
              onChange: (v) {
                final nueva = provider.config.copyWith(
                  notificacionesActivas: v,
                );
                provider.actualizarConfiguracion(nueva);
              },
            ),
          ]),

          const SizedBox(height: 16),

          // Telegram
          _SeccionAjustes(titulo: 'TELEGRAM', items: [
            _ItemTelegramSwitch(provider: provider),
          ]),

          const SizedBox(height: 16),

          // Backup
          _SeccionAjustes(titulo: 'COPIA DE SEGURIDAD', items: [
            _ItemAccion(
              icono: Icons.backup_rounded,
              etiqueta: 'Realizar backup ahora',
              subtitulo: provider.config.ultimoBackup != null
                  ? 'Último: ${provider.config.ultimoBackup!.day}/${provider.config.ultimoBackup!.month}/${provider.config.ultimoBackup!.year}'
                  : 'Nunca realizado',
              color: BonolotoTheme.verdeAccent,
              onTap: () => provider.realizarBackup(),
            ),
          ]),

          const SizedBox(height: 16),

          // Credenciales
          _SeccionAjustes(titulo: 'CONEXIONES', items: [
            _ItemAccion(
              icono: Icons.vpn_key_rounded,
              etiqueta: 'Credenciales y API Keys',
              subtitulo: provider.credenciales.estaConfigurado
                  ? 'Sistema configurado ✓'
                  : 'Sin configurar — toca para configurar',
              color: provider.credenciales.estaConfigurado
                  ? BonolotoTheme.colorExito
                  : BonolotoTheme.colorAdvertencia,
              onTap: () =>
                  Navigator.pushNamed(context, '/credenciales'),
            ),
            _ItemAccion(
              icono: Icons.wifi_tethering_rounded,
              etiqueta: 'Probar conexión',
              subtitulo: 'Comprueba el servidor y la API de loterías',
              color: BonolotoTheme.colorInfo,
              onTap: () async {
                // Diálogo "probando..."
                showDialog(
                  context: context,
                  barrierDismissible: false,
                  builder: (_) => const AlertDialog(
                    content: Row(
                      children: [
                        CircularProgressIndicator(),
                        SizedBox(width: 16),
                        Expanded(child: Text('Probando conexión...')),
                      ],
                    ),
                  ),
                );
                final res = await ref
                    .read(appProvider.notifier)
                    .probarConexion();
                if (context.mounted) Navigator.pop(context); // cerrar "probando"
                if (context.mounted) {
                  showDialog(
                    context: context,
                    builder: (_) => AlertDialog(
                      icon: Icon(
                        res.correcto
                            ? Icons.check_circle_rounded
                            : Icons.error_rounded,
                        color: res.correcto
                            ? BonolotoTheme.colorExito
                            : BonolotoTheme.colorAdvertencia,
                        size: 48,
                      ),
                      title: Text(
                          res.correcto ? 'Conexión correcta' : 'Hay un problema'),
                      content: Text(res.mensaje),
                      actions: [
                        TextButton(
                          onPressed: () => Navigator.pop(context),
                          child: const Text('Entendido'),
                        ),
                      ],
                    ),
                  );
                }
              },
            ),
          ]),

          const SizedBox(height: 16),

          // Info
          _SeccionAjustes(titulo: 'INFORMACIÓN', items: [
            _ItemAccion(
              icono: Icons.info_rounded,
              etiqueta: 'Bonoloto 2.0',
              subtitulo: 'Versión 2.0.0 — Motor Oracle Cloud ARM 24GB',
              color: BonolotoTheme.colorInfo,
              onTap: () {},
            ),
            _ItemAccion(
              icono: Icons.school_rounded,
              etiqueta: 'Tutorial de algoritmos',
              subtitulo: 'Los 117 algoritmos explicados',
              color: BonolotoTheme.amarillo,
              onTap: () =>
                  Navigator.pushNamed(context, '/tutorial'),
            ),
          ]),
        ],
      ),
    );
  }
}

class _SeccionAjustes extends ConsumerWidget {
  final String titulo;
  final List<Widget> items;
  const _SeccionAjustes({required this.titulo, required this.items});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(titulo,
            style: GoogleFonts.rajdhani(
              fontSize: 16,
              fontWeight: FontWeight.w700,
              letterSpacing: 2,
              color: BonolotoTheme.verdeAccent,
            )),
        const SizedBox(height: 8),
        Card(
          child: Column(
            children: items
                .asMap()
                .entries
                .map((e) => Column(
                      children: [
                        e.value,
                        if (e.key < items.length - 1)
                          const Divider(height: 1, indent: 56),
                      ],
                    ))
                .toList(),
          ),
        ),
      ],
    );
  }
}

class _ItemSwitch extends ConsumerWidget {
  final IconData icono;
  final String etiqueta;
  final bool valor;
  final ValueChanged<bool> onChange;
  const _ItemSwitch(
      {required this.icono,
      required this.etiqueta,
      required this.valor,
      required this.onChange});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return ListTile(
      leading: Icon(icono, color: BonolotoTheme.verdeAccent),
      title:
          Text(etiqueta, style: GoogleFonts.rajdhani(fontWeight: FontWeight.w600)),
      trailing: Switch.adaptive(
        value: valor,
        onChanged: onChange,
        activeColor: BonolotoTheme.verdeAccent,
      ),
    );
  }
}

class _ItemAccion extends ConsumerWidget {
  final IconData icono;
  final String etiqueta;
  final String subtitulo;
  final Color color;
  final VoidCallback onTap;
  const _ItemAccion(
      {required this.icono,
      required this.etiqueta,
      required this.subtitulo,
      required this.color,
      required this.onTap});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return ListTile(
      onTap: onTap,
      leading: Container(
        width: 36,
        height: 36,
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(8),
        ),
        child: Icon(icono, color: color, size: 20),
      ),
      title:
          Text(etiqueta, style: GoogleFonts.rajdhani(fontWeight: FontWeight.w600)),
      subtitle: Text(subtitulo, style: GoogleFonts.spaceMono(fontSize: 14)),
      trailing: Icon(Icons.chevron_right_rounded,
          color: Theme.of(context).colorScheme.onSurface.withValues(alpha: 0.3)),
    );
  }
}

// ─────────────────────────────────────────────
// WIDGET TELEGRAM SWITCH — Con indicador visual de estado
// ─────────────────────────────────────────────
class _ItemTelegramSwitch extends ConsumerWidget {
  final AppNotifier provider;
  const _ItemTelegramSwitch({required this.provider});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final activo = provider.config.telegramActivo;
    final telegramConfigurado = provider.credenciales.telegramBotToken.isNotEmpty &&
        provider.credenciales.telegramChatId.isNotEmpty;
    final theme = Theme.of(context);

    return Column(
      children: [
        // Fila principal con switch
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 4),
          child: Row(
            children: [
              // Icono animado Telegram
              AnimatedContainer(
                duration: const Duration(milliseconds: 300),
                width: 36,
                height: 36,
                decoration: BoxDecoration(
                  color: activo
                      ? const Color(0xFF0088CC).withValues(alpha: 0.15)
                      : Colors.grey.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Icon(
                  Icons.telegram_rounded,
                  color: activo ? const Color(0xFF0088CC) : Colors.grey,
                  size: 20,
                ),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Envío a Telegram',
                      style: GoogleFonts.rajdhani(
                        fontSize: 17,
                        fontWeight: FontWeight.w600,
                        color: theme.colorScheme.onSurface,
                      ),
                    ),
                    AnimatedSwitcher(
                      duration: const Duration(milliseconds: 250),
                      child: Text(
                        activo
                            ? (telegramConfigurado
                                ? 'Activo — combinaciones y aciertos'
                                : 'Activo — configura el bot primero')
                            : 'Desactivado — sin envíos a Telegram',
                        key: ValueKey(activo),
                        style: GoogleFonts.spaceMono(
                          fontSize: 14,
                          color: activo
                              ? (telegramConfigurado
                                  ? const Color(0xFF0088CC)
                                  : BonolotoTheme.colorAdvertencia)
                              : Colors.grey,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              Switch.adaptive(
                value: activo,
                onChanged: (v) {
                  final nueva = provider.config.copyWith(
                    telegramActivo: v,
                  );
                  provider.actualizarConfiguracion(nueva);

                  // Mostrar snackbar de confirmación
                  ScaffoldMessenger.of(context).clearSnackBars();
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(
                      content: Row(
                        children: [
                          Icon(
                            v
                                ? Icons.telegram_rounded
                                : Icons.notifications_off_rounded,
                            color: Colors.white,
                            size: 18,
                          ),
                          const SizedBox(width: 8),
                          Text(
                            v
                                ? 'Telegram activado'
                                : 'Telegram desactivado',
                            style: GoogleFonts.rajdhani(
                              fontWeight: FontWeight.w600,
                              color: Colors.white,
                            ),
                          ),
                        ],
                      ),
                      backgroundColor: v
                          ? const Color(0xFF0088CC)
                          : Colors.grey.shade700,
                      duration: const Duration(seconds: 2),
                      behavior: SnackBarBehavior.floating,
                      shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(10)),
                      margin: const EdgeInsets.all(12),
                    ),
                  );
                },
                activeColor: const Color(0xFF0088CC),
              ),
            ],
          ),
        ),

        // Banner de advertencia si Telegram no está configurado pero está activo
        if (activo && !telegramConfigurado) ...[
          const SizedBox(height: 8),
          Container(
            margin: const EdgeInsets.symmetric(horizontal: 4),
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            decoration: BoxDecoration(
              color: BonolotoTheme.colorAdvertencia.withValues(alpha: 0.08),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(
                  color: BonolotoTheme.colorAdvertencia.withValues(alpha: 0.3)),
            ),
            child: Row(
              children: [
                const Icon(Icons.warning_amber_rounded,
                    color: BonolotoTheme.colorAdvertencia, size: 16),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    'Bot de Telegram no configurado. Ve a Ajustes → Credenciales.',
                    style: GoogleFonts.spaceMono(
                      fontSize: 14,
                      color: BonolotoTheme.colorAdvertencia,
                    ),
                  ),
                ),
                TextButton(
                  onPressed: () =>
                      Navigator.pushNamed(context, '/credenciales'),
                  style: TextButton.styleFrom(
                    padding: EdgeInsets.zero,
                    minimumSize: const Size(50, 24),
                  ),
                  child: Text(
                    'CONFIGURAR',
                    style: GoogleFonts.rajdhani(
                      fontSize: 15,
                      fontWeight: FontWeight.w700,
                      color: BonolotoTheme.colorAdvertencia,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],

        // Detalle de qué mensajes se envían cuando está activo
        if (activo && telegramConfigurado) ...[
          const SizedBox(height: 8),
          Container(
            margin: const EdgeInsets.symmetric(horizontal: 4),
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            decoration: BoxDecoration(
              color: const Color(0xFF0088CC).withValues(alpha: 0.06),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(
                  color: const Color(0xFF0088CC).withValues(alpha: 0.2)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'SE ENVIARÁN A TELEGRAM:',
                  style: GoogleFonts.rajdhani(
                    fontSize: 14,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 1.2,
                    color: const Color(0xFF0088CC),
                  ),
                ),
                const SizedBox(height: 4),
                _FilaDetalleTelegram(
                    icono: Icons.auto_awesome_rounded,
                    texto: 'Combinaciones al completar el cálculo'),
                _FilaDetalleTelegram(
                    icono: Icons.scoreboard_rounded,
                    texto: 'Informe de aciertos tras el sorteo (21:45h)'),
              ],
            ),
          ),
        ],
      ],
    );
  }
}

class _FilaDetalleTelegram extends ConsumerWidget {
  final IconData icono;
  final String texto;
  const _FilaDetalleTelegram({required this.icono, required this.texto});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Padding(
      padding: const EdgeInsets.only(top: 3),
      child: Row(
        children: [
          Icon(icono, size: 12, color: const Color(0xFF0088CC)),
          const SizedBox(width: 6),
          Expanded(
            child: Text(
              texto,
              style: GoogleFonts.spaceMono(
                fontSize: 14,
                color: Theme.of(context).colorScheme.onSurface.withValues(alpha: 0.6),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// ═══════════════════════════════════════════════════════════
// CREDENCIALES SCREEN
// ═══════════════════════════════════════════════════════════
class CredencialesScreen extends ConsumerStatefulWidget {
  const CredencialesScreen({super.key});

  @override
  ConsumerState<CredencialesScreen> createState() => _CredencialesScreenState();
}

class _CredencialesScreenState extends ConsumerState<CredencialesScreen> {
  final _formKey = GlobalKey<FormState>();
  late TextEditingController _loteriasCtrl;
  late TextEditingController _oracleUrlCtrl;
  late TextEditingController _oracleTokenCtrl;
  late TextEditingController _telegramTokenCtrl;
  late TextEditingController _telegramChatCtrl;
  bool _guardando = false;
  Map<String, bool?> _estadoConexion = {};

  @override
  void initState() {
    super.initState();
    final creds = ref.read(appProvider.notifier).credenciales;
    _loteriasCtrl = TextEditingController(text: creds.loteriasApiKey);
    _oracleUrlCtrl = TextEditingController(text: creds.oracleCloudUrl);
    _oracleTokenCtrl = TextEditingController(text: creds.oracleCloudToken);
    _telegramTokenCtrl = TextEditingController(text: creds.telegramBotToken);
    _telegramChatCtrl = TextEditingController(text: creds.telegramChatId);
  }

  @override
  void dispose() {
    _loteriasCtrl.dispose();
    _oracleUrlCtrl.dispose();
    _oracleTokenCtrl.dispose();
    _telegramTokenCtrl.dispose();
    _telegramChatCtrl.dispose();
    super.dispose();
  }

  Future<void> _guardar() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _guardando = true);

    final nuevas = Credenciales(
      loteriasApiKey: _loteriasCtrl.text.trim(),
      oracleCloudUrl: _oracleUrlCtrl.text.trim(),
      oracleCloudToken: _oracleTokenCtrl.text.trim(),
      telegramBotToken: _telegramTokenCtrl.text.trim(),
      telegramChatId: _telegramChatCtrl.text.trim(),
    );

    await ref.read(appProvider.notifier).actualizarCredenciales(nuevas);
    if (!mounted) return;
    setState(() => _guardando = false);

    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Credenciales guardadas correctamente',
              style: GoogleFonts.rajdhani(fontWeight: FontWeight.w600)),
          backgroundColor: BonolotoTheme.verdeAccent,
        ),
      );
      Navigator.pop(context);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(
        title: Text('CREDENCIALES',
            style: GoogleFonts.rajdhani(
                fontWeight: FontWeight.w700, letterSpacing: 2)),
        actions: [
          TextButton(
            onPressed: _guardando ? null : _guardar,
            child: _guardando
                ? const SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(
                        strokeWidth: 2, color: Colors.white))
                : Text('GUARDAR',
                    style: GoogleFonts.rajdhani(
                        color: BonolotoTheme.amarillo,
                        fontWeight: FontWeight.w700,
                        fontSize: 17)),
          ),
        ],
      ),
      body: Form(
        key: _formKey,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            _SeccionCredencial(
              titulo: 'LOTERIAS API',
              icono: Icons.dataset_rounded,
              color: BonolotoTheme.verdeAccent,
              descripcion:
                  'API Key para acceder a loteriasapi.com y obtener el histórico completo de sorteos de Bonoloto.',
              campos: [
                _CampoCredencial(
                  controller: _loteriasCtrl,
                  etiqueta: 'API Key de loteriasapi.com',
                  icono: Icons.key_rounded,
                  esSecreto: true,
                  validador: (v) => null, // opcional: se puede guardar vacío
                ),
              ],
            ),

            const SizedBox(height: 16),

            _SeccionCredencial(
              titulo: 'ORACLE CLOUD',
              icono: Icons.cloud_rounded,
              color: BonolotoTheme.colorInfo,
              descripcion:
                  'URL de tu instancia Oracle Cloud y token JWT para autenticar el motor de IA. Se genera en tu servidor Oracle Cloud.',
              campos: [
                _CampoCredencial(
                  controller: _oracleUrlCtrl,
                  etiqueta: 'URL de Oracle Cloud (https://...)',
                  icono: Icons.link_rounded,
                  esSecreto: false,
                  validador: (v) {
                    if (v == null || v.isEmpty) return null; // opcional
                    if (!v.startsWith('http'))
                      return 'Debe ser una URL válida';
                    return null;
                  },
                ),
                _CampoCredencial(
                  controller: _oracleTokenCtrl,
                  etiqueta: 'Token JWT de Oracle Cloud',
                  icono: Icons.token_rounded,
                  esSecreto: true,
                  validador: (v) => null, // opcional
                ),
              ],
            ),

            const SizedBox(height: 16),

            _SeccionCredencial(
              titulo: 'TELEGRAM',
              icono: Icons.telegram_rounded,
              color: const Color(0xFF0088CC),
              descripcion:
                  'Token del bot de Telegram y tu Chat ID. El bot te enviará las combinaciones y el informe de aciertos tras cada sorteo.',
              campos: [
                _CampoCredencial(
                  controller: _telegramTokenCtrl,
                  etiqueta: 'Token del Bot de Telegram',
                  icono: Icons.smart_toy_rounded,
                  esSecreto: true,
                  validador: (v) => null, // opcional
                ),
                _CampoCredencial(
                  controller: _telegramChatCtrl,
                  etiqueta: 'Chat ID de Telegram',
                  icono: Icons.tag_rounded,
                  esSecreto: false,
                  validador: (v) => null, // opcional
                ),
              ],
            ),

            const SizedBox(height: 24),

            ElevatedButton.icon(
              onPressed: _guardando ? null : _guardar,
              icon: const Icon(Icons.save_rounded),
              label: Text(
                'GUARDAR CREDENCIALES',
                style: GoogleFonts.rajdhani(
                    fontSize: 16, fontWeight: FontWeight.w700, letterSpacing: 1),
              ),
              style: ElevatedButton.styleFrom(
                minimumSize: const Size(double.infinity, 52),
              ),
            ),

            const SizedBox(height: 32),
          ],
        ),
      ),
    );
  }
}

class _SeccionCredencial extends ConsumerWidget {
  final String titulo;
  final IconData icono;
  final Color color;
  final String descripcion;
  final List<Widget> campos;
  const _SeccionCredencial({
    required this.titulo,
    required this.icono,
    required this.color,
    required this.descripcion,
    required this.campos,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(icono, color: color, size: 18),
            const SizedBox(width: 8),
            Text(titulo,
                style: GoogleFonts.rajdhani(
                  fontSize: 16,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 2,
                  color: color,
                )),
          ],
        ),
        const SizedBox(height: 6),
        Text(descripcion,
            style: GoogleFonts.spaceMono(
              fontSize: 14,
              color: Theme.of(context).colorScheme.onSurface.withValues(alpha: 0.6),
            )),
        const SizedBox(height: 12),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(12),
            child: Column(
              children: campos
                  .asMap()
                  .entries
                  .map((e) => Column(
                        children: [
                          e.value,
                          if (e.key < campos.length - 1)
                            const SizedBox(height: 12),
                        ],
                      ))
                  .toList(),
            ),
          ),
        ),
      ],
    );
  }
}

class _CampoCredencial extends ConsumerStatefulWidget {
  final TextEditingController controller;
  final String etiqueta;
  final IconData icono;
  final bool esSecreto;
  final String? Function(String?) validador;

  const _CampoCredencial({
    required this.controller,
    required this.etiqueta,
    required this.icono,
    required this.esSecreto,
    required this.validador,
  });

  @override
  ConsumerState<_CampoCredencial> createState() => _CampoCredencialState();
}

class _CampoCredencialState extends ConsumerState<_CampoCredencial> {
  bool _oculto = true;

  @override
  Widget build(BuildContext context) {
    return TextFormField(
      controller: widget.controller,
      obscureText: widget.esSecreto && _oculto,
      validator: widget.validador,
      style: GoogleFonts.spaceMono(fontSize: 16),
      decoration: InputDecoration(
        labelText: widget.etiqueta,
        prefixIcon: Icon(widget.icono, size: 18),
        suffixIcon: widget.esSecreto
            ? IconButton(
                icon: Icon(
                  _oculto ? Icons.visibility_rounded : Icons.visibility_off_rounded,
                  size: 18,
                ),
                onPressed: () => setState(() => _oculto = !_oculto),
              )
            : null,
      ),
    );
  }
}
