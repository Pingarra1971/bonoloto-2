import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';

import 'state/app_notifier.dart';
import 'theme/app_theme.dart';
import 'screens/dashboard_screen.dart';
import 'screens/progreso_screen.dart';
import 'screens/estadisticas_screen.dart';
import 'screens/honestidad_screen.dart';
import 'screens/secondary_screens.dart';
import 'screens/apuesta_multiple_screen.dart';
import 'screens/ultimo_sorteo_screen.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  await SystemChrome.setPreferredOrientations([
    DeviceOrientation.portraitUp,
    DeviceOrientation.portraitDown,
  ]);

  runApp(
    const ProviderScope(
      child: _AppArranque(),
    ),
  );
}

/// Widget que dispara la inicialización del notifier en el primer build.
/// Riverpod no llama a métodos de un Notifier automáticamente al crearlo
/// (a diferencia de Provider que tiene `create: (_) => X()..inicializar()`).
class _AppArranque extends ConsumerStatefulWidget {
  const _AppArranque();

  @override
  ConsumerState<_AppArranque> createState() => _AppArranqueState();
}

class _AppArranqueState extends ConsumerState<_AppArranque> {
  @override
  void initState() {
    super.initState();
    // Disparar inicialización tras el primer frame para que el ProviderScope
    // esté listo cuando se ejecute. El estado de carga se refleja vía
    // `sistemaInicializado` en el provider, que la home del MaterialApp usa
    // para mostrar un splash mientras tanto.
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(appProvider.notifier).inicializar();
    });
  }

  @override
  Widget build(BuildContext context) {
    return const BonolotoApp();
  }
}

class BonolotoApp extends ConsumerWidget {
  const BonolotoApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final modoOscuro = ref.watch(
      appProvider.select((s) => s.config.modoOscuro),
    );

    return MaterialApp(
      title: 'Bonoloto 2.0',
      debugShowCheckedModeBanner: false,
      theme: BonolotoTheme.lightTheme,
      darkTheme: BonolotoTheme.darkTheme,
      themeMode: modoOscuro ? ThemeMode.dark : ThemeMode.light,
      initialRoute: '/',
      routes: {
        '/': (ctx) => const _ArranqueGate(),
        '/progreso': (ctx) => const ProgresoScreen(),
        '/estadisticas': (ctx) => const EstadisticasScreen(),
        '/honestidad': (ctx) => const HonestidadScreen(),
        '/historial': (ctx) => const HistorialScreen(),
        '/tutorial': (ctx) => const TutorialScreen(),
        '/ajustes': (ctx) => const AjustesScreen(),
        '/credenciales': (ctx) => const CredencialesScreen(),
        '/apuesta_multiple': (ctx) => const ApuestaMultipleScreen(),
        '/ultimo_sorteo': (ctx) => const UltimoSorteoScreen(),
      },
      builder: (context, child) {
        // textScaler reemplaza al textScaleFactor deprecado (Flutter 3.16+)
        return MediaQuery(
          data: MediaQuery.of(context).copyWith(
            textScaler: const TextScaler.linear(1.0),
          ),
          child: child!,
        );
      },
    );
  }
}

// ═══════════════════════════════════════════════════════════
// GATE DE ARRANQUE — splash mientras inicializa
// ═══════════════════════════════════════════════════════════
class _ArranqueGate extends ConsumerWidget {
  const _ArranqueGate();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final inicializado = ref.watch(
      appProvider.select((s) => s.sistemaInicializado),
    );

    if (!inicializado) {
      // Splash sencillo mientras se cargan config/credenciales/historial.
      final theme = Theme.of(context);
      return Scaffold(
        body: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(
                Icons.casino_rounded,
                size: 64,
                color: theme.colorScheme.primary,
              ),
              const SizedBox(height: 24),
              Text(
                'BONOLOTO 2.0',
                style: GoogleFonts.rajdhani(
                  fontSize: 24,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 4,
                ),
              ),
              const SizedBox(height: 24),
              const SizedBox(
                width: 28,
                height: 28,
                child: CircularProgressIndicator(strokeWidth: 3),
              ),
            ],
          ),
        ),
      );
    }

    return const MainNavigationWrapper();
  }
}

// ═══════════════════════════════════════════════════════════
// NAVEGACIÓN PRINCIPAL
// ═══════════════════════════════════════════════════════════
class MainNavigationWrapper extends ConsumerStatefulWidget {
  const MainNavigationWrapper({super.key});

  @override
  ConsumerState<MainNavigationWrapper> createState() =>
      _MainNavigationWrapperState();
}

class _MainNavigationWrapperState extends ConsumerState<MainNavigationWrapper> {
  int _indiceActual = 0;
  // Bug #142: el aviso de credenciales debe mostrarse UNA vez, no en cada
  // rebuild del wrapper (que ocurre ante cualquier cambio de estado).
  bool _avisoCredencialesMostrado = false;

  final List<Widget> _pantallas = const [
    DashboardScreen(),
    EstadisticasScreen(),
    HonestidadScreen(),
    HistorialScreen(),
    AjustesScreen(),
  ];

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(appProvider);
    final theme = Theme.of(context);

    if (state.sistemaInicializado &&
        !state.credenciales.estaConfigurado &&
        _indiceActual == 0 &&
        !_avisoCredencialesMostrado) {
      _avisoCredencialesMostrado = true;
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) _mostrarAvisoCredenciales();
      });
    }

    return Scaffold(
      body: IndexedStack(
        index: _indiceActual,
        children: _pantallas,
      ),
      bottomNavigationBar: Container(
        decoration: BoxDecoration(
          border: Border(
            top: BorderSide(
              color: theme.colorScheme.onSurface.withValues(alpha: 0.08),
            ),
          ),
        ),
        child: BottomNavigationBar(
          currentIndex: _indiceActual,
          onTap: (i) => setState(() => _indiceActual = i),
          type: BottomNavigationBarType.fixed,
          selectedFontSize: 11,
          unselectedFontSize: 11,
          items: [
            BottomNavigationBarItem(
              icon: _NavIcon(
                icono: Icons.dashboard_rounded,
                activo: _indiceActual == 0,
              ),
              label: 'Inicio',
            ),
            BottomNavigationBarItem(
              icon: _NavIcon(
                icono: Icons.bar_chart_rounded,
                activo: _indiceActual == 1,
              ),
              label: 'Estadísticas',
            ),
            BottomNavigationBarItem(
              icon: _NavIcon(
                icono: Icons.balance_rounded,
                activo: _indiceActual == 2,
              ),
              label: 'Rendimiento',
            ),
            BottomNavigationBarItem(
              icon: _NavIcon(
                icono: Icons.history_rounded,
                activo: _indiceActual == 3,
              ),
              label: 'Historial',
            ),
            BottomNavigationBarItem(
              icon: _NavIcon(
                icono: Icons.settings_rounded,
                activo: _indiceActual == 4,
              ),
              label: 'Ajustes',
            ),
          ],
        ),
      ),
    );
  }

  void _mostrarAvisoCredenciales() {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Row(
          children: [
            const Icon(Icons.warning_rounded,
                color: Colors.black, size: 18),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                'Configura las credenciales para activar el sistema',
                style: GoogleFonts.rajdhani(
                  fontWeight: FontWeight.w600,
                  color: Colors.black,
                ),
              ),
            ),
          ],
        ),
        backgroundColor: BonolotoTheme.amarillo,
        action: SnackBarAction(
          label: 'CONFIGURAR',
          textColor: Colors.black,
          onPressed: () =>
              Navigator.pushNamed(context, '/credenciales'),
        ),
        duration: const Duration(seconds: 5),
      ),
    );
  }
}

class _NavIcon extends StatelessWidget {
  final IconData icono;
  final bool activo;

  const _NavIcon({required this.icono, required this.activo});

  @override
  Widget build(BuildContext context) {
    return AnimatedContainer(
      duration: const Duration(milliseconds: 200),
      padding: EdgeInsets.all(activo ? 6 : 0),
      decoration: BoxDecoration(
        color: activo
            ? BonolotoTheme.amarillo.withValues(alpha: 0.15)
            : Colors.transparent,
        borderRadius: BorderRadius.circular(10),
      ),
      child: Icon(icono),
    );
  }
}
