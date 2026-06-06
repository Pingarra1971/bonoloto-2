import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:fl_chart/fl_chart.dart';
import '../state/app_notifier.dart';
import '../theme/app_theme.dart';
import '../models/models.dart';

class EstadisticasScreen extends ConsumerStatefulWidget {
  const EstadisticasScreen({super.key});

  @override
  ConsumerState<EstadisticasScreen> createState() => _EstadisticasScreenState();
}

class _EstadisticasScreenState extends ConsumerState<EstadisticasScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 4, vsync: this);
    WidgetsBinding.instance.addPostFrameCallback((_) {
        ref.read(appProvider.notifier).cargarEstadisticas();
    });
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(
        title: Text(
          'ESTADÍSTICAS',
          style: GoogleFonts.rajdhani(
              fontWeight: FontWeight.w700, letterSpacing: 2),
        ),
        bottom: TabBar(
          controller: _tabController,
          indicatorColor: BonolotoTheme.amarillo,
          labelColor: BonolotoTheme.amarillo,
          unselectedLabelColor:
              theme.colorScheme.onSurface.withValues(alpha: 0.4),
          labelStyle: GoogleFonts.rajdhani(
              fontSize: 15, fontWeight: FontWeight.w700, letterSpacing: 1),
          tabs: const [
            Tab(text: 'FRECUENCIA'),
            Tab(text: 'CONFIANZA'),
            Tab(text: 'CALOR'),
            Tab(text: 'ALGORITMOS'),
          ],
        ),
      ),
      body: TabBarView(
        controller: _tabController,
        children: const [
          _TabFrecuencia(),
          _TabConfianza(),
          _TabMapaCalor(),
          _TabRendimientoAlgoritmos(),
        ],
      ),
    );
  }
}

// ═══════════════════════════════════════════════════════════
// TAB 1 — FRECUENCIA HISTÓRICA DE CADA NÚMERO
// ═══════════════════════════════════════════════════════════
class _TabFrecuencia extends ConsumerStatefulWidget {
  const _TabFrecuencia();

  @override
  ConsumerState<_TabFrecuencia> createState() => _TabFrecuenciaState();
}

class _TabFrecuenciaState extends ConsumerState<_TabFrecuencia> {
  String _filtro = 'total'; // total, 50, 100, 500

  @override
  Widget build(BuildContext context) {
    ref.watch(appProvider);
    final provider = ref.read(appProvider.notifier);
    final stats = provider.estadisticas;
    final theme = Theme.of(context);

    if (stats.isEmpty) {
      return _CargandoWidget();
    }

    final valores = stats.map((s) {
      switch (_filtro) {
        case '50':
          return s.frecuenciaUltimos50.toDouble();
        case '100':
          return s.frecuenciaUltimos100.toDouble();
        case '500':
          return s.frecuenciaUltimos500.toDouble();
        default:
          return s.frecuenciaTotal.toDouble();
      }
    }).toList();

    final maxVal = valores.reduce((a, b) => a > b ? a : b);

    return Column(
      children: [
        // Filtros
        Padding(
          padding: const EdgeInsets.all(12),
          child: Row(
            children: [
              Text('Período: ',
                  style: GoogleFonts.spaceMono(fontSize: 15)),
              const SizedBox(width: 8),
              ...[
                ('total', 'Total'),
                ('500', 'Últ. 500'),
                ('100', 'Últ. 100'),
                ('50', 'Últ. 50'),
              ].map((item) => Padding(
                    padding: const EdgeInsets.only(right: 6),
                    child: ChoiceChip(
                      label: Text(item.$2,
                          style: GoogleFonts.rajdhani(
                              fontSize: 15, fontWeight: FontWeight.w600)),
                      selected: _filtro == item.$1,
                      onSelected: (_) =>
                          setState(() => _filtro = item.$1),
                      selectedColor: BonolotoTheme.verdeAccent,
                      labelStyle: TextStyle(
                        color: _filtro == item.$1
                            ? Colors.black
                            : theme.colorScheme.onSurface,
                      ),
                    ),
                  )),
            ],
          ),
        ),

        // Leyenda caliente/fría/neutra
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 12),
          child: Row(
            children: [
              _Leyenda(color: const Color(0xFFFF6B35), etiqueta: 'Caliente'),
              const SizedBox(width: 16),
              _Leyenda(color: BonolotoTheme.colorInfo, etiqueta: 'Frío'),
              const SizedBox(width: 16),
              _Leyenda(
                  color: BonolotoTheme.verdeAccent, etiqueta: 'Neutro'),
            ],
          ),
        ),
        const SizedBox(height: 8),

        // Gráfico de barras
        Expanded(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(8, 0, 16, 16),
            child: BarChart(
              BarChartData(
                alignment: BarChartAlignment.start,
                maxY: maxVal * 1.15,
                barTouchData: BarTouchData(
                  touchTooltipData: BarTouchTooltipData(
                    tooltipBgColor: theme.cardColor,
                    getTooltipItem: (group, groupIndex, rod, rodIndex) {
                      final num = stats[group.x].numero;
                      final val = rod.toY.toInt();
                      return BarTooltipItem(
                        'Nº $num\n$val veces',
                        GoogleFonts.rajdhani(
                          color: theme.colorScheme.onSurface,
                          fontWeight: FontWeight.bold,
                        ),
                      );
                    },
                  ),
                ),
                titlesData: FlTitlesData(
                  show: true,
                  bottomTitles: AxisTitles(
                    sideTitles: SideTitles(
                      showTitles: true,
                      reservedSize: 28,
                      interval: 7,
                      getTitlesWidget: (value, meta) {
                        final num = stats[value.toInt()].numero;
                        return Text(
                          '$num',
                          style: GoogleFonts.spaceMono(fontSize: 14),
                        );
                      },
                    ),
                  ),
                  leftTitles: AxisTitles(
                    sideTitles: SideTitles(
                      showTitles: true,
                      reservedSize: 36,
                      getTitlesWidget: (value, meta) => Text(
                        '${value.toInt()}',
                        style: GoogleFonts.spaceMono(fontSize: 14),
                      ),
                    ),
                  ),
                  topTitles: const AxisTitles(
                      sideTitles: SideTitles(showTitles: false)),
                  rightTitles: const AxisTitles(
                      sideTitles: SideTitles(showTitles: false)),
                ),
                gridData: FlGridData(
                  show: true,
                  drawVerticalLine: false,
                  horizontalInterval: maxVal / 5,
                  getDrawingHorizontalLine: (v) => FlLine(
                    color: theme.colorScheme.onSurface.withValues(alpha: 0.05),
                    strokeWidth: 1,
                  ),
                ),
                borderData: FlBorderData(show: false),
                barGroups: stats.asMap().entries.map((entry) {
                  final i = entry.key;
                  final s = entry.value;
                  final val = valores[i];
                  Color barColor;
                  switch (s.clasificacion) {
                    case 'caliente':
                      barColor = const Color(0xFFFF6B35);
                      break;
                    case 'frio':
                      barColor = BonolotoTheme.colorInfo;
                      break;
                    default:
                      barColor = BonolotoTheme.verdeAccent;
                  }
                  return BarChartGroupData(
                    x: i,
                    barRods: [
                      BarChartRodData(
                        toY: val,
                        color: barColor,
                        width: 6,
                        borderRadius: const BorderRadius.vertical(
                            top: Radius.circular(3)),
                      ),
                    ],
                  );
                }).toList(),
              ),
            ),
          ),
        ),
      ],
    );
  }
}

// ═══════════════════════════════════════════════════════════
// TAB 2 — EVOLUCIÓN DEL ÍNDICE DE CONFIANZA
// ═══════════════════════════════════════════════════════════
class _TabConfianza extends ConsumerWidget {
  const _TabConfianza();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    ref.watch(appProvider);
    final provider = ref.read(appProvider.notifier);
    final historial = provider.historial
        .where((s) =>
            s.estado == EstadoCalculo.completado &&
            s.combinaciones.isNotEmpty)
        .toList()
        .reversed
        .toList();
    final theme = Theme.of(context);

    if (historial.isEmpty) {
      return _SinDatosWidget(
          mensaje:
              'Aún no hay predicciones.\nRealiza tu primer cálculo para ver la evolución de confianza.');
    }

    final spots = historial.asMap().entries.map((entry) {
      final i = entry.key;
      final sesion = entry.value;
      final maxConf = sesion.combinaciones
          .map((c) => c.indiceConfianza)
          .reduce((a, b) => a > b ? a : b);
      return FlSpot(i.toDouble(), maxConf);
    }).toList();

    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('EVOLUCIÓN DE CONFIANZA MÁXIMA',
              style: GoogleFonts.rajdhani(
                fontSize: 17,
                fontWeight: FontWeight.w700,
                letterSpacing: 1.5,
                color: BonolotoTheme.verdeAccent,
              )),
          Text(
            'Por sesión de cálculo',
            style: GoogleFonts.spaceMono(
              fontSize: 14,
              color: theme.colorScheme.onSurface.withValues(alpha: 0.5),
            ),
          ),
          const SizedBox(height: 20),
          Expanded(
            child: LineChart(
              LineChartData(
                lineTouchData: LineTouchData(
                  touchTooltipData: LineTouchTooltipData(
                    tooltipBgColor: theme.cardColor,
                    getTooltipItems: (touchedSpots) =>
                        touchedSpots.map((spot) {
                      return LineTooltipItem(
                        'Sesión ${spot.x.toInt() + 1}\n${spot.y.toStringAsFixed(1)}%',
                        GoogleFonts.rajdhani(
                          color: BonolotoTheme.amarillo,
                          fontWeight: FontWeight.bold,
                        ),
                      );
                    }).toList(),
                  ),
                ),
                gridData: FlGridData(
                  show: true,
                  drawVerticalLine: false,
                  getDrawingHorizontalLine: (v) => FlLine(
                    color: theme.colorScheme.onSurface.withValues(alpha: 0.05),
                    strokeWidth: 1,
                  ),
                ),
                titlesData: FlTitlesData(
                  bottomTitles: AxisTitles(
                    sideTitles: SideTitles(
                      showTitles: true,
                      getTitlesWidget: (value, _) => Text(
                        'S${value.toInt() + 1}',
                        style: GoogleFonts.spaceMono(fontSize: 14),
                      ),
                      interval: 1,
                    ),
                  ),
                  leftTitles: AxisTitles(
                    sideTitles: SideTitles(
                      showTitles: true,
                      reservedSize: 40,
                      getTitlesWidget: (value, _) => Text(
                        '${value.toInt()}%',
                        style: GoogleFonts.spaceMono(fontSize: 14),
                      ),
                    ),
                  ),
                  topTitles: const AxisTitles(
                      sideTitles: SideTitles(showTitles: false)),
                  rightTitles: const AxisTitles(
                      sideTitles: SideTitles(showTitles: false)),
                ),
                borderData: FlBorderData(show: false),
                minY: 0,
                maxY: 100,
                lineBarsData: [
                  LineChartBarData(
                    spots: spots,
                    isCurved: true,
                    color: BonolotoTheme.verdeAccent,
                    barWidth: 3,
                    isStrokeCapRound: true,
                    dotData: FlDotData(
                      show: true,
                      getDotPainter: (spot, _, __, ___) =>
                          FlDotCirclePainter(
                        radius: 5,
                        color: BonolotoTheme.amarillo,
                        strokeColor: BonolotoTheme.verdeAccent,
                        strokeWidth: 2,
                      ),
                    ),
                    belowBarData: BarAreaData(
                      show: true,
                      color:
                          BonolotoTheme.verdeAccent.withValues(alpha: 0.08),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// ═══════════════════════════════════════════════════════════
// TAB 3 — MAPA DE CALOR DE CO-OCURRENCIA
// ═══════════════════════════════════════════════════════════
class _TabMapaCalor extends ConsumerWidget {
  const _TabMapaCalor();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    ref.watch(appProvider);
    final provider = ref.read(appProvider.notifier);
    final stats = provider.estadisticas;
    final theme = Theme.of(context);

    if (stats.isEmpty) return _CargandoWidget();

    // Calcular co-ocurrencias top 10 pares
    final historial = provider.historial
        .where((s) => s.combinaciones.isNotEmpty)
        .toList();

    final Map<String, int> pares = {};
    for (final sesion in historial) {
      for (final combo in sesion.combinaciones) {
        final nums = combo.numeros..sort();
        for (int i = 0; i < nums.length; i++) {
          for (int j = i + 1; j < nums.length; j++) {
            final clave = '${nums[i]}-${nums[j]}';
            pares[clave] = (pares[clave] ?? 0) + 1;
          }
        }
      }
    }

    final topPares = pares.entries.toList()
      ..sort((a, b) => b.value.compareTo(a.value));
    final top10 = topPares.take(10).toList();

    if (top10.isEmpty) {
      return _SinDatosWidget(
          mensaje:
              'No hay datos suficientes.\nGenera más predicciones para ver el mapa de co-ocurrencias.');
    }

    final maxCooc = top10.first.value.toDouble();

    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('PARES MÁS FRECUENTES EN PREDICCIONES',
              style: GoogleFonts.rajdhani(
                fontSize: 17,
                fontWeight: FontWeight.w700,
                letterSpacing: 1.5,
                color: BonolotoTheme.verdeAccent,
              )),
          Text(
            'Números que aparecen juntos con más frecuencia',
            style: GoogleFonts.spaceMono(
              fontSize: 14,
              color: theme.colorScheme.onSurface.withValues(alpha: 0.5),
            ),
          ),
          const SizedBox(height: 16),
          Expanded(
            child: ListView.builder(
              itemCount: top10.length,
              itemBuilder: (ctx, i) {
                final par = top10[i];
                final nums = par.key.split('-');
                final porcentaje = par.value / maxCooc;

                return Container(
                  margin: const EdgeInsets.only(bottom: 10),
                  child: Row(
                    children: [
                      // Rank
                      Container(
                        width: 28,
                        height: 28,
                        decoration: BoxDecoration(
                          color: i < 3
                              ? BonolotoTheme.amarillo.withValues(alpha: 0.15)
                              : Colors.transparent,
                          borderRadius: BorderRadius.circular(6),
                        ),
                        child: Center(
                          child: Text(
                            '${i + 1}',
                            style: GoogleFonts.rajdhani(
                              fontSize: 16,
                              fontWeight: FontWeight.w700,
                              color: i < 3
                                  ? BonolotoTheme.amarillo
                                  : theme.colorScheme.onSurface
                                      .withValues(alpha: 0.5),
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(width: 10),

                      // Números del par
                      _BolaMini(numero: int.parse(nums[0])),
                      const SizedBox(width: 6),
                      _BolaMini(numero: int.parse(nums[1])),
                      const SizedBox(width: 12),

                      // Barra de calor
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            ClipRRect(
                              borderRadius: BorderRadius.circular(4),
                              child: LinearProgressIndicator(
                                value: porcentaje,
                                minHeight: 12,
                                backgroundColor: theme.colorScheme.onSurface
                                    .withValues(alpha: 0.07),
                                valueColor: AlwaysStoppedAnimation<Color>(
                                  Color.lerp(
                                    BonolotoTheme.colorInfo,
                                    const Color(0xFFFF6B35),
                                    porcentaje,
                                  )!,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(width: 10),

                      // Valor
                      Text(
                        '${par.value}x',
                        style: GoogleFonts.spaceMono(
                          fontSize: 15,
                          fontWeight: FontWeight.bold,
                          color:
                              theme.colorScheme.onSurface.withValues(alpha: 0.7),
                        ),
                      ),
                    ],
                  ),
                )
                    .animate()
                    .fadeIn(duration: 300.ms, delay: (i * 60).ms)
                    .slideX(begin: -0.1, end: 0);
              },
            ),
          ),
        ],
      ),
    );
  }
}

class _BolaMini extends ConsumerWidget {
  final int numero;
  const _BolaMini({required this.numero});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Container(
      width: 30,
      height: 30,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [BonolotoTheme.verdeAccent, BonolotoTheme.verdeOscuro],
        ),
        boxShadow: [
          BoxShadow(
            color: BonolotoTheme.verdeAccent.withValues(alpha: 0.3),
            blurRadius: 6,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Center(
        child: Text(
          '$numero',
          style: GoogleFonts.rajdhani(
            fontSize: 16,
            fontWeight: FontWeight.w700,
            color: Colors.white,
          ),
        ),
      ),
    );
  }
}

// ═══════════════════════════════════════════════════════════
// TAB 4 — RENDIMIENTO POR ALGORITMO
// ═══════════════════════════════════════════════════════════
class _TabRendimientoAlgoritmos extends ConsumerWidget {
  const _TabRendimientoAlgoritmos();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    ref.watch(appProvider);
    final provider = ref.read(appProvider.notifier);
    final algoritmos = provider.rendimientoAlgoritmos;
    final theme = Theme.of(context);

    if (algoritmos.isEmpty) return _CargandoWidget();

    final total = algoritmos.fold(0.0, (sum, a) => sum + a.pesoActual);

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('PESO DINÁMICO DE CADA ALGORITMO',
              style: GoogleFonts.rajdhani(
                fontSize: 17,
                fontWeight: FontWeight.w700,
                letterSpacing: 1.5,
                color: BonolotoTheme.verdeAccent,
              )),
          Text(
            'Ajustado automáticamente según rendimiento histórico',
            style: GoogleFonts.spaceMono(
              fontSize: 14,
              color: theme.colorScheme.onSurface.withValues(alpha: 0.5),
            ),
          ),
          const SizedBox(height: 20),

          // Gráfico de dona
          SizedBox(
            height: 200,
            child: PieChart(
              PieChartData(
                sectionsSpace: 2,
                centerSpaceRadius: 60,
                sections: algoritmos.asMap().entries.map((entry) {
                  final colores = [
                    BonolotoTheme.verdeAccent,
                    BonolotoTheme.amarillo,
                    BonolotoTheme.colorInfo,
                    const Color(0xFFFF6B35),
                    const Color(0xFFB84FFF),
                    const Color(0xFFFF4FA0),
                    const Color(0xFF00D4FF),
                    BonolotoTheme.colorExito,
                    const Color(0xFFFF8C00),
                    BonolotoTheme.verdeOscuro,
                    const Color(0xFF8B4513),
                  ];
                  final i = entry.key;
                  final alg = entry.value;
                  final pct = total > 0 ? (alg.pesoActual / total * 100) : 0.0;
                  return PieChartSectionData(
                    value: alg.pesoActual,
                    color: colores[i % colores.length],
                    radius: 35,
                    showTitle: pct > 5,
                    title: '${pct.toStringAsFixed(0)}%',
                    titleStyle: GoogleFonts.rajdhani(
                      fontSize: 14,
                      fontWeight: FontWeight.w700,
                      color: Colors.white,
                    ),
                  );
                }).toList(),
              ),
            ),
          ),

          const SizedBox(height: 20),

          // Lista detallada
          ...algoritmos.asMap().entries.map((entry) {
            final i = entry.key;
            final alg = entry.value;
            final pct = total > 0 ? (alg.pesoActual / total) : 0.0;
            final colores = [
              BonolotoTheme.verdeAccent,
              BonolotoTheme.amarillo,
              BonolotoTheme.colorInfo,
              const Color(0xFFFF6B35),
              const Color(0xFFB84FFF),
              const Color(0xFFFF4FA0),
              const Color(0xFF00D4FF),
              BonolotoTheme.colorExito,
              const Color(0xFFFF8C00),
              BonolotoTheme.verdeOscuro,
              const Color(0xFF8B4513),
            ];
            final color = colores[i % colores.length];

            return Container(
              margin: const EdgeInsets.only(bottom: 10),
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: color.withValues(alpha: 0.05),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: color.withValues(alpha: 0.2)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Container(
                        width: 10,
                        height: 10,
                        decoration: BoxDecoration(
                            color: color, shape: BoxShape.circle),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          alg.nombre,
                          style: GoogleFonts.rajdhani(
                            fontSize: 17,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ),
                      Text(
                        '${(pct * 100).toStringAsFixed(1)}% del peso',
                        style: GoogleFonts.spaceMono(
                          fontSize: 14,
                          color: color,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 6),
                  ClipRRect(
                    borderRadius: BorderRadius.circular(4),
                    child: LinearProgressIndicator(
                      value: pct,
                      minHeight: 6,
                      backgroundColor:
                          theme.colorScheme.onSurface.withValues(alpha: 0.07),
                      valueColor:
                          AlwaysStoppedAnimation<Color>(color),
                    ),
                  ),
                  const SizedBox(height: 4),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        'Tasa aciertos: ${(alg.tasaAciertosHistorica * 100).toStringAsFixed(1)}%',
                        style: GoogleFonts.spaceMono(fontSize: 14),
                      ),
                      Text(
                        '${alg.totalPredicciones} predicciones',
                        style: GoogleFonts.spaceMono(
                          fontSize: 14,
                          color: theme.colorScheme.onSurface.withValues(alpha: 0.5),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            )
                .animate()
                .fadeIn(duration: 300.ms, delay: (i * 60).ms)
                .slideX(begin: 0.1, end: 0);
          }).toList(),
        ],
      ),
    );
  }
}

// ═══════════════════════════════════════════════════════════
// WIDGETS AUXILIARES
// ═══════════════════════════════════════════════════════════
class _Leyenda extends ConsumerWidget {
  final Color color;
  final String etiqueta;
  const _Leyenda({required this.color, required this.etiqueta});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
            width: 10,
            height: 10,
            decoration:
                BoxDecoration(color: color, shape: BoxShape.circle)),
        const SizedBox(width: 4),
        Text(etiqueta,
            style:
                GoogleFonts.spaceMono(fontSize: 14)),
      ],
    );
  }
}

class _CargandoWidget extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return const Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          CircularProgressIndicator(color: BonolotoTheme.verdeAccent),
          SizedBox(height: 16),
          Text('Cargando estadísticas...'),
        ],
      ),
    );
  }
}

class _SinDatosWidget extends ConsumerWidget {
  final String mensaje;
  const _SinDatosWidget({required this.mensaje});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.bar_chart_rounded,
                color: BonolotoTheme.verdeAccent, size: 48),
            const SizedBox(height: 16),
            Text(
              mensaje,
              style: GoogleFonts.spaceMono(fontSize: 16),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }
}
