import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:google_fonts/google_fonts.dart';
import '../state/app_notifier.dart';
import '../theme/app_theme.dart';
import '../models/models.dart';
import '../widgets/widgets.dart';
import 'sistema_garantizado_screen.dart';

class DashboardScreen extends ConsumerStatefulWidget {
  const DashboardScreen({super.key});

  @override
  ConsumerState<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends ConsumerState<DashboardScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
        ref.read(appProvider.notifier).cargarEstadisticas();
    });
  }

  @override
  Widget build(BuildContext context) {
    ref.watch(appProvider);
    final provider = ref.read(appProvider.notifier);
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    return Scaffold(
      body: CustomScrollView(
        slivers: [
          // ─── APP BAR ───
          SliverAppBar(
            expandedHeight: 120,
            floating: false,
            pinned: true,
            flexibleSpace: FlexibleSpaceBar(
              title: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Container(
                    width: 28,
                    height: 28,
                    decoration: BoxDecoration(
                      color: BonolotoTheme.amarillo,
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: const Icon(Icons.casino_rounded,
                        color: Colors.black, size: 18),
                  ),
                  const SizedBox(width: 10),
                  Text(
                    'BONOLOTO 2.0',
                    style: GoogleFonts.rajdhani(
                      fontWeight: FontWeight.w700,
                      fontSize: 22,
                      letterSpacing: 2,
                      color: Colors.white,
                    ),
                  ),
                ],
              ),
              centerTitle: true,
              background: Container(
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: isDark
                        ? [
                            const Color(0xFF0A2010),
                            const Color(0xFF003318),
                          ]
                        : [
                            BonolotoTheme.verdeOscuro,
                            BonolotoTheme.verdeMedio,
                          ],
                  ),
                ),
              ),
            ),
            actions: [
              IconButton(
                icon: Icon(
                  isDark ? Icons.light_mode_rounded : Icons.dark_mode_rounded,
                  color: BonolotoTheme.amarillo,
                ),
                onPressed: () => provider.toggleTema(),
              ),
            ],
          ),

          // ─── CONTENIDO ───
          SliverPadding(
            padding: const EdgeInsets.all(16),
            sliver: SliverList(
              delegate: SliverChildListDelegate([
                // Estado del sistema
                _TarjetaEstadoSistema(provider: provider)
                    .animate()
                    .fadeIn(duration: 400.ms)
                    .slideY(begin: 0.2, end: 0),

                const SizedBox(height: 16),

                // Próximo sorteo
                _TarjetaProximoSorteo()
                    .animate()
                    .fadeIn(duration: 400.ms, delay: 100.ms)
                    .slideY(begin: 0.2, end: 0),

                const SizedBox(height: 16),

                // Última predicción
                if (provider.historial.isNotEmpty)
                  _TarjetaUltimaPrediccion(
                    sesion: provider.historial.first,
                    provider: provider,
                  )
                      .animate()
                      .fadeIn(duration: 400.ms, delay: 200.ms)
                      .slideY(begin: 0.2, end: 0),

                const SizedBox(height: 16),

                // Botón calcular
                _BotonCalcular(provider: provider)
                    .animate()
                    .fadeIn(duration: 400.ms, delay: 300.ms)
                    .slideY(begin: 0.2, end: 0),

                const SizedBox(height: 16),

                // Sistema con garantía (premios menores reales)
                _TarjetaSistemaGarantia()
                    .animate()
                    .fadeIn(duration: 400.ms, delay: 350.ms)
                    .slideY(begin: 0.2, end: 0),

                const SizedBox(height: 16),

                // Acceso rápido estadísticas
                _AccesoRapido()
                    .animate()
                    .fadeIn(duration: 400.ms, delay: 400.ms)
                    .slideY(begin: 0.2, end: 0),

                const SizedBox(height: 32),
              ]),
            ),
          ),
        ],
      ),
    );
  }
}

// ─────────────────────────────────────────────
class _TarjetaEstadoSistema extends ConsumerWidget {
  final AppNotifier provider;
  const _TarjetaEstadoSistema({required this.provider});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final conectado = provider.sistemaInicializado;
    final theme = Theme.of(context);

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.memory_rounded,
                    color: BonolotoTheme.verdeAccent, size: 20),
                const SizedBox(width: 8),
                Flexible(
                  child: Text('ESTADO DEL SISTEMA',
                      overflow: TextOverflow.ellipsis,
                      style: theme.textTheme.labelLarge?.copyWith(
                        letterSpacing: 1.5,
                        color: BonolotoTheme.verdeAccent,
                      )),
                ),
                const Spacer(),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: conectado
                        ? BonolotoTheme.verdeAccent.withValues(alpha: 0.15)
                        : BonolotoTheme.colorError.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(
                      color: conectado
                          ? BonolotoTheme.verdeAccent
                          : BonolotoTheme.colorError,
                      width: 1,
                    ),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Container(
                        width: 6,
                        height: 6,
                        decoration: BoxDecoration(
                          color: conectado
                              ? BonolotoTheme.verdeAccent
                              : BonolotoTheme.colorError,
                          shape: BoxShape.circle,
                        ),
                      ),
                      const SizedBox(width: 6),
                      Text(
                        conectado ? 'ACTIVO' : 'DESCONECTADO',
                        style: GoogleFonts.spaceMono(
                          fontSize: 14,
                          color: conectado
                              ? BonolotoTheme.verdeAccent
                              : BonolotoTheme.colorError,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                _ItemEstado(
                  icono: Icons.cloud_done_rounded,
                  etiqueta: 'Sistema',
                  valor: 'Automático',
                  activo: conectado,
                ),
                const SizedBox(width: 12),
                _ItemEstado(
                  icono: Icons.psychology_rounded,
                  etiqueta: 'Algoritmos',
                  valor: '11 activos',
                  activo: conectado,
                ),
                const SizedBox(width: 12),
                _ItemEstado(
                  icono: Icons.dataset_rounded,
                  etiqueta: 'Sorteos',
                  valor: '${provider.resultadosOficiales.length} cargados',
                  activo: conectado,
                ),
              ],
            ),
            if (!provider.credenciales.estaConfigurado) ...[
              const SizedBox(height: 12),
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: BonolotoTheme.amarillo.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(
                      color: BonolotoTheme.amarillo.withValues(alpha: 0.3)),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.warning_amber_rounded,
                        color: BonolotoTheme.amarillo, size: 16),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        'Configura las credenciales para activar el sistema',
                        style: GoogleFonts.spaceMono(
                          fontSize: 15,
                          color: BonolotoTheme.amarillo,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _ItemEstado extends ConsumerWidget {
  final IconData icono;
  final String etiqueta;
  final String valor;
  final bool activo;

  const _ItemEstado({
    required this.icono,
    required this.etiqueta,
    required this.valor,
    required this.activo,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    return Expanded(
      child: Container(
        padding: const EdgeInsets.all(10),
        decoration: BoxDecoration(
          color: theme.colorScheme.surface.withValues(alpha: 0.5),
          borderRadius: BorderRadius.circular(10),
          border: Border.all(
            color: theme.colorScheme.onSurface.withValues(alpha: 0.05),
          ),
        ),
        child: Column(
          children: [
            Icon(icono,
                size: 20,
                color: activo
                    ? BonolotoTheme.verdeAccent
                    : theme.colorScheme.onSurface.withValues(alpha: 0.3)),
            const SizedBox(height: 4),
            Text(
              valor,
              style: GoogleFonts.rajdhani(
                fontSize: 16,
                fontWeight: FontWeight.w700,
                color: activo
                    ? theme.colorScheme.onSurface
                    : theme.colorScheme.onSurface.withValues(alpha: 0.4),
              ),
              textAlign: TextAlign.center,
            ),
            Text(
              etiqueta,
              style: GoogleFonts.spaceMono(
                fontSize: 14,
                color: theme.colorScheme.onSurface.withValues(alpha: 0.5),
              ),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }
}

// ─────────────────────────────────────────────
class _TarjetaProximoSorteo extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    final ahora = DateTime.now();
    final sorteoHoy = DateTime(ahora.year, ahora.month, ahora.day, 21, 30);
    final falta = sorteoHoy.difference(ahora);
    final yaPaso = falta.isNegative;

    const diasSemana = [
      'Lunes', 'Martes', 'Miércoles', 'Jueves',
      'Viernes', 'Sábado', 'Domingo'
    ];
    final diaActual = diasSemana[ahora.weekday - 1];

    return Card(
      child: Container(
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(16),
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [
              BonolotoTheme.verdeOscuro.withValues(alpha: 0.3),
              BonolotoTheme.verdeMedio.withValues(alpha: 0.1),
            ],
          ),
        ),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            children: [
              Container(
                width: 56,
                height: 56,
                decoration: BoxDecoration(
                  color: BonolotoTheme.amarillo,
                  borderRadius: BorderRadius.circular(14),
                ),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Text(
                      ahora.day.toString(),
                      style: GoogleFonts.rajdhani(
                        fontSize: 22,
                        fontWeight: FontWeight.w700,
                        color: Colors.black,
                        height: 1,
                      ),
                    ),
                    Text(
                      diaActual.substring(0, 3).toUpperCase(),
                      style: GoogleFonts.rajdhani(
                        fontSize: 15,
                        fontWeight: FontWeight.w600,
                        color: Colors.black54,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'PRÓXIMO SORTEO',
                      style: GoogleFonts.rajdhani(
                        fontSize: 16,
                        fontWeight: FontWeight.w600,
                        letterSpacing: 1.5,
                        color: BonolotoTheme.verdeAccent,
                      ),
                    ),
                    Text(
                      'Hoy a las 21:30h',
                      style: theme.textTheme.headlineSmall,
                    ),
                    Text(
                      yaPaso
                          ? 'Sorteo ya celebrado — Mañana: ${diasSemana[ahora.weekday % 7]}'
                          : 'Faltan ${falta.inHours}h ${falta.inMinutes % 60}m',
                      style: GoogleFonts.spaceMono(
                        fontSize: 15,
                        color: yaPaso
                            ? BonolotoTheme.colorInfo
                            : BonolotoTheme.amarillo,
                      ),
                    ),
                  ],
                ),
              ),
              Icon(
                Icons.calendar_today_rounded,
                color: BonolotoTheme.verdeAccent.withValues(alpha: 0.5),
                size: 28,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// ─────────────────────────────────────────────
class _TarjetaUltimaPrediccion extends ConsumerWidget {
  final SesionPrediccion sesion;
  final AppNotifier provider;
  const _TarjetaUltimaPrediccion(
      {required this.sesion, required this.provider});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    final combo = sesion.combinaciones.isNotEmpty
        ? sesion.combinaciones.first
        : null;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.history_rounded,
                    color: BonolotoTheme.verdeAccent, size: 20),
                const SizedBox(width: 8),
                Flexible(
                  child: Text('ÚLTIMAS COMBINACIONES',
                      overflow: TextOverflow.ellipsis,
                      style: theme.textTheme.labelLarge?.copyWith(
                        letterSpacing: 1.5,
                        color: BonolotoTheme.verdeAccent,
                      )),
                ),
                const Spacer(),
                Text(
                  '${sesion.fechaSolicitud.day}/${sesion.fechaSolicitud.month}/${sesion.fechaSolicitud.year}',
                  style: GoogleFonts.spaceMono(
                    fontSize: 15,
                    color: theme.colorScheme.onSurface.withValues(alpha: 0.5),
                  ),
                ),
              ],
            ),
            if (combo != null) ...[
              const SizedBox(height: 12),
              BolasNumerosWidget(numeros: combo.numeros, tamano: 36),
              const SizedBox(height: 8),
              Row(
                children: [
                  Expanded(
                    child: BarraConfianzaWidget(valor: combo.indiceConfianza),
                  ),
                  const SizedBox(width: 8),
                  Text(
                    '${combo.indiceConfianza.toStringAsFixed(1)}%',
                    style: GoogleFonts.rajdhani(
                      fontSize: 17,
                      fontWeight: FontWeight.w700,
                      color: _colorConfianza(combo.indiceConfianza),
                    ),
                  ),
                  if (combo.aciertos != null) ...[
                    const Spacer(),
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 8, vertical: 3),
                      decoration: BoxDecoration(
                        color: BonolotoTheme.amarillo.withValues(alpha: 0.15),
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(
                            color: BonolotoTheme.amarillo.withValues(alpha: 0.4)),
                      ),
                      child: Text(
                        '${combo.aciertos} aciertos',
                        style: GoogleFonts.rajdhani(
                          fontSize: 16,
                          fontWeight: FontWeight.w700,
                          color: BonolotoTheme.amarillo,
                        ),
                      ),
                    ),
                  ],
                ],
              ),
            ],
            if (sesion.combinaciones.length > 1) ...[
              const SizedBox(height: 8),
              Text(
                '+${sesion.combinaciones.length - 1} combinaciones más',
                style: GoogleFonts.spaceMono(
                  fontSize: 15,
                  color: BonolotoTheme.verdeAccent,
                ),
              ),
            ],
            if (sesion.combinaciones.isNotEmpty) ...[
              const SizedBox(height: 6),
              Text(
                'Coste: ${sesion.costeTotalEur.toStringAsFixed(2)} €  '
                '(${sesion.combinaciones.length} × 0,50 €)',
                style: GoogleFonts.rajdhani(
                  fontSize: 14,
                  fontWeight: FontWeight.w600,
                  color: BonolotoTheme.amarillo,
                ),
              ),
            ],
            if (sesion.fechaSorteoTexto != null) ...[
              const SizedBox(height: 4),
              Text(
                'Para el sorteo del ${sesion.fechaSorteoTexto}',
                style: GoogleFonts.rajdhani(
                  fontSize: 14,
                  fontWeight: FontWeight.w600,
                  color: BonolotoTheme.verdeAccent,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Color _colorConfianza(double valor) {
    if (valor >= 70) return BonolotoTheme.colorExito;
    if (valor >= 40) return BonolotoTheme.amarillo;
    return BonolotoTheme.colorInfo;
  }
}

// ─────────────────────────────────────────────
class _BotonCalcular extends ConsumerWidget {
  final AppNotifier provider;
  const _BotonCalcular({required this.provider});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final bloqueado = provider.calculoBloqueado;
    final calculando = provider.sesionActual?.estado == EstadoCalculo.calculando ||
        provider.sesionActual?.estado == EstadoCalculo.convergiendo;

    return Container(
      width: double.infinity,
      height: 64,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(16),
        gradient: bloqueado
            ? null
            : const LinearGradient(
                colors: [BonolotoTheme.verdeOscuro, BonolotoTheme.verdeAccent],
              ),
        color: bloqueado ? Colors.grey.withValues(alpha: 0.2) : null,
        border: Border.all(
          color: bloqueado
              ? Colors.grey.withValues(alpha: 0.3)
              : BonolotoTheme.verdeAccent,
          width: 1,
        ),
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          borderRadius: BorderRadius.circular(16),
          onTap: bloqueado || calculando
              ? null
              : () => _mostrarDialogoCalcular(context, provider),
          child: Center(
            child: calculando
                ? Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      SizedBox(
                        width: 20,
                        height: 20,
                        child: CircularProgressIndicator(
                          color: BonolotoTheme.amarillo,
                          strokeWidth: 2,
                        ),
                      ),
                      const SizedBox(width: 12),
                      Text(
                        'CALCULANDO...',
                        style: GoogleFonts.rajdhani(
                          fontSize: 18,
                          fontWeight: FontWeight.w700,
                          letterSpacing: 2,
                          color: BonolotoTheme.amarillo,
                        ),
                      ),
                    ],
                  )
                : bloqueado
                    ? Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              const Icon(Icons.lock_rounded,
                                  color: Colors.grey, size: 18),
                              const SizedBox(width: 8),
                              Text(
                                'BLOQUEADO HASTA EL PRÓXIMO SORTEO',
                                style: GoogleFonts.rajdhani(
                                  fontSize: 16,
                                  fontWeight: FontWeight.w600,
                                  letterSpacing: 1,
                                  color: Colors.grey,
                                ),
                              ),
                            ],
                          ),
                          Text(
                            provider.mensajeBloqueo,
                            style: GoogleFonts.spaceMono(
                              fontSize: 14,
                              color: Colors.grey.withValues(alpha: 0.7),
                            ),
                          ),
                        ],
                      )
                    : Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          const Icon(Icons.auto_awesome_rounded,
                              color: BonolotoTheme.amarillo, size: 22),
                          const SizedBox(width: 10),
                          Text(
                            'CALCULAR COMBINACIONES',
                            style: GoogleFonts.rajdhani(
                              fontSize: 18,
                              fontWeight: FontWeight.w700,
                              letterSpacing: 2,
                              color: Colors.white,
                            ),
                          ),
                        ],
                      ),
          ),
        ),
      ),
    );
  }

  void _mostrarDialogoCalcular(BuildContext context, AppNotifier provider) {
    int cantidad = 5;
    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setState) => AlertDialog(
          backgroundColor: Theme.of(context).cardColor,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(20),
            side: const BorderSide(color: BonolotoTheme.verdeAccent, width: 1),
          ),
          title: Text(
            '¿CUÁNTAS COMBINACIONES?',
            style: GoogleFonts.rajdhani(
              fontSize: 18,
              fontWeight: FontWeight.w700,
              letterSpacing: 1,
            ),
          ),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                'Se descargarán las combinaciones del día, generadas automáticamente con el análisis estadístico del histórico.',
                style: GoogleFonts.spaceMono(fontSize: 15),
              ),
              const SizedBox(height: 20),
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  IconButton(
                    onPressed: cantidad > 1
                        ? () => setState(() => cantidad--)
                        : null,
                    icon: const Icon(Icons.remove_circle_rounded,
                        color: BonolotoTheme.verdeAccent),
                  ),
                  Container(
                    width: 70,
                    alignment: Alignment.center,
                    child: Text(
                      cantidad.toString(),
                      style: GoogleFonts.rajdhani(
                        fontSize: 40,
                        fontWeight: FontWeight.w700,
                        color: BonolotoTheme.amarillo,
                      ),
                    ),
                  ),
                  IconButton(
                    onPressed: cantidad < 20
                        ? () => setState(() => cantidad++)
                        : null,
                    icon: const Icon(Icons.add_circle_rounded,
                        color: BonolotoTheme.verdeAccent),
                  ),
                ],
              ),
              Text(
                'combinaciones a generar',
                style: GoogleFonts.spaceMono(
                  fontSize: 15,
                  color: Theme.of(context)
                      .colorScheme
                      .onSurface
                      .withValues(alpha: 0.5),
                ),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: Text('CANCELAR',
                  style: GoogleFonts.rajdhani(color: Colors.grey)),
            ),
            ElevatedButton(
              onPressed: () {
                Navigator.pop(ctx);
                provider.iniciarCalculo(cantidad: cantidad);
                // Navegar a pantalla de progreso
                Navigator.pushNamed(context, '/progreso');
              },
              child: Text('INICIAR', style: GoogleFonts.rajdhani()),
            ),
          ],
        ),
      ),
    );
  }
}

// ─────────────────────────────────────────────
class _AccesoRapido extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final items = [
      _AccesoItem(
          icono: Icons.bar_chart_rounded,
          etiqueta: 'Estadísticas',
          ruta: '/estadisticas'),
      _AccesoItem(
          icono: Icons.history_rounded,
          etiqueta: 'Historial',
          ruta: '/historial'),
      _AccesoItem(
          icono: Icons.dashboard_customize_rounded,
          etiqueta: 'Múltiple',
          ruta: '/apuesta_multiple'),
      _AccesoItem(
          icono: Icons.confirmation_number_rounded,
          etiqueta: 'Sorteo',
          ruta: '/ultimo_sorteo'),
      _AccesoItem(
          icono: Icons.school_rounded,
          etiqueta: 'Tutorial',
          ruta: '/tutorial'),
      _AccesoItem(
          icono: Icons.settings_rounded,
          etiqueta: 'Ajustes',
          ruta: '/ajustes'),
    ];

    // Repartimos los accesos en filas de 3 para que quepan con holgura.
    const porFila = 3;
    final filas = <Widget>[];
    for (var i = 0; i < items.length; i += porFila) {
      final fin = (i + porFila) < items.length ? (i + porFila) : items.length;
      final grupo = items.sublist(i, fin);
      final hijos = <Widget>[];
      for (final item in grupo) {
        hijos.add(Expanded(
          child: Padding(
            padding: const EdgeInsets.all(4),
            child: _TarjetaAccesoRapido(item: item),
          ),
        ));
      }
      for (var k = grupo.length; k < porFila; k++) {
        hijos.add(const Expanded(child: SizedBox()));
      }
      filas.add(Row(children: hijos));
    }

    return Column(children: filas);
  }
}

class _AccesoItem {
  final IconData icono;
  final String etiqueta;
  final String ruta;
  _AccesoItem(
      {required this.icono, required this.etiqueta, required this.ruta});
}

class _TarjetaAccesoRapido extends ConsumerWidget {
  final _AccesoItem item;
  const _TarjetaAccesoRapido({required this.item});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    return Card(
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: () => Navigator.pushNamed(context, item.ruta),
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 8),
          child: Column(
            children: [
              Icon(item.icono, color: BonolotoTheme.verdeAccent, size: 24),
              const SizedBox(height: 6),
              Text(
                item.etiqueta,
                style: GoogleFonts.rajdhani(
                  fontSize: 15,
                  fontWeight: FontWeight.w600,
                  color: theme.colorScheme.onSurface,
                ),
                textAlign: TextAlign.center,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// ─────────────────────────────────────────────
// Tarjeta de acceso al Sistema con garantía (mejoras 1 y 2).
class _TarjetaSistemaGarantia extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return InkWell(
      onTap: () => Navigator.push(
        context,
        MaterialPageRoute(
            builder: (_) => const SistemaGarantizadoScreen()),
      ),
      borderRadius: BorderRadius.circular(16),
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: theme.colorScheme.surface,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
              color: BonolotoTheme.verdeAccent.withValues(alpha: 0.35)),
        ),
        child: Row(
          children: [
            Icon(Icons.verified_rounded,
                color: BonolotoTheme.verdeAccent, size: 28),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('SISTEMA CON GARANTÍA',
                      style: GoogleFonts.rajdhani(
                          fontSize: 16,
                          fontWeight: FontWeight.w700,
                          letterSpacing: 1.2,
                          color: BonolotoTheme.verdeAccent)),
                  const SizedBox(height: 2),
                  Text(
                      'Garantiza un premio menor y enseña las probabilidades '
                      'reales de cada categoría.',
                      style: GoogleFonts.rajdhani(fontSize: 14)),
                ],
              ),
            ),
            Icon(Icons.chevron_right_rounded,
                color: theme.colorScheme.onSurface.withValues(alpha: 0.4)),
          ],
        ),
      ),
    );
  }
}
