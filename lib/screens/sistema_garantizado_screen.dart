import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';

import '../services/services.dart'
    show SistemasInfo, SistemaGarantizado, CategoriaPremio;
import '../state/app_notifier.dart';
import '../theme/app_theme.dart';
import '../widgets/widgets.dart';

/// Sistema con garantía: muestra los 3 niveles (Económico / Equilibrado /
/// Fuerte) y la probabilidad real de cada categoría de premio.
///
/// Honestidad: NO mejora la probabilidad del pleno (fija en 1/13.983.816).
/// Lo que hace es GARANTIZAR un premio menor si aciertas ciertos números de
/// tu grupo, y enseñar las probabilidades reales sin adornos.
class SistemaGarantizadoScreen extends ConsumerStatefulWidget {
  const SistemaGarantizadoScreen({super.key});

  @override
  ConsumerState<SistemaGarantizadoScreen> createState() =>
      _SistemaGarantizadoScreenState();
}

class _SistemaGarantizadoScreenState
    extends ConsumerState<SistemaGarantizadoScreen> {
  SistemasInfo? _info;
  bool _cargando = true;
  int _seleccion = 1; // 0=Económico, 1=Equilibrado, 2=Fuerte

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _cargar());
  }

  Future<void> _cargar() async {
    setState(() => _cargando = true);
    final info = await ref.read(appProvider.notifier).obtenerSistemas();
    if (!mounted) return;
    setState(() {
      _info = info;
      if (info != null && _seleccion >= info.sistemas.length) _seleccion = 0;
      _cargando = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      appBar: AppBar(
        title: Text('SISTEMA CON GARANTÍA',
            style: GoogleFonts.rajdhani(
                fontWeight: FontWeight.w700, letterSpacing: 2)),
        actions: [
          IconButton(
              icon: const Icon(Icons.refresh_rounded), onPressed: _cargar),
        ],
      ),
      body: _cargando
          ? const Center(child: CircularProgressIndicator())
          : (_info == null || _info!.sistemas.isEmpty)
              ? _vacio(theme)
              : RefreshIndicator(
                  onRefresh: _cargar,
                  child: ListView(
                    padding: const EdgeInsets.all(16),
                    children: [
                      _banner(theme),
                      const SizedBox(height: 16),
                      _selector(theme),
                      const SizedBox(height: 16),
                      _detalleSistema(theme, _info!.sistemas[_seleccion]),
                      const SizedBox(height: 16),
                      _tablaProbabilidades(theme),
                      const SizedBox(height: 16),
                      _notaHonesta(theme),
                      const SizedBox(height: 24),
                    ],
                  ),
                ),
    );
  }

  Widget _vacio(ThemeData theme) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Text(
          'Aún no hay sistemas en el JSON. Lanza la tarea diaria del backend y '
          'vuelve a entrar.',
          textAlign: TextAlign.center,
          style: GoogleFonts.rajdhani(fontSize: 16),
        ),
      ),
    );
  }

  Widget _banner(ThemeData theme) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: theme.colorScheme.primary.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
            color: theme.colorScheme.primary.withValues(alpha: 0.25)),
      ),
      child: Text(
        'Esto es lo único que mueve la aguja de verdad: no sube la opción del '
        'pleno, pero GARANTIZA un premio menor si aciertas ciertos números de '
        'tu grupo. Elige cuánto quieres jugar.',
        style: GoogleFonts.rajdhani(fontSize: 15, fontWeight: FontWeight.w600),
      ),
    );
  }

  Widget _selector(ThemeData theme) {
    return Row(
      children: [
        for (int i = 0; i < _info!.sistemas.length; i++)
          Expanded(
            child: Padding(
              padding: EdgeInsets.only(
                  right: i < _info!.sistemas.length - 1 ? 8 : 0),
              child: _chip(theme, _info!.sistemas[i].nombre, i),
            ),
          ),
      ],
    );
  }

  Widget _chip(ThemeData theme, String nombre, int i) {
    final activo = _seleccion == i;
    return InkWell(
      onTap: () => setState(() => _seleccion = i),
      borderRadius: BorderRadius.circular(10),
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 12),
        alignment: Alignment.center,
        decoration: BoxDecoration(
          color: activo
              ? theme.colorScheme.primary.withValues(alpha: 0.18)
              : theme.colorScheme.surface,
          borderRadius: BorderRadius.circular(10),
          border: Border.all(
            color: activo
                ? theme.colorScheme.primary
                : theme.colorScheme.onSurface.withValues(alpha: 0.12),
            width: activo ? 1.5 : 1,
          ),
        ),
        child: Text(
          nombre,
          style: GoogleFonts.rajdhani(
            fontSize: 15,
            fontWeight: FontWeight.w700,
            color: activo
                ? theme.colorScheme.primary
                : theme.colorScheme.onSurface.withValues(alpha: 0.7),
          ),
        ),
      ),
    );
  }

  Widget _detalleSistema(ThemeData theme, SistemaGarantizado s) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
            color: theme.colorScheme.onSurface.withValues(alpha: 0.08)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.verified_rounded,
                  color: BonolotoTheme.verdeAccent, size: 22),
              const SizedBox(width: 8),
              Expanded(
                child: Text(s.garantiaTexto,
                    style: GoogleFonts.rajdhani(
                        fontSize: 16, fontWeight: FontWeight.w700)),
              ),
            ],
          ),
          if (s.verificada) ...[
            const SizedBox(height: 6),
            Text('Garantía comprobada por fuerza bruta ✓',
                style: GoogleFonts.rajdhani(
                    fontSize: 13, color: BonolotoTheme.verdeAccent)),
          ],
          const SizedBox(height: 14),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceAround,
            children: [
              _mini('${s.nApuestas}', 'apuestas'),
              _mini('${s.costeEur.toStringAsFixed(2)} €', 'coste total'),
              _mini('${s.pool.length}', 'tus números'),
            ],
          ),
          const SizedBox(height: 14),
          Text('Premios esperados por sorteo (de media):',
              style: GoogleFonts.rajdhani(
                  fontSize: 14, fontWeight: FontWeight.w600)),
          const SizedBox(height: 4),
          Text(
            '3 aciertos: ${_fmt(s.esperadoPorSorteo['3'])}   ·   '
            '4 aciertos: ${_fmt(s.esperadoPorSorteo['4'])}',
            style: GoogleFonts.spaceMono(fontSize: 13),
          ),
          const SizedBox(height: 14),
          Row(
            children: [
              Text('Tus ${s.apuestas.length} apuestas',
                  style: GoogleFonts.rajdhani(
                      fontSize: 14, fontWeight: FontWeight.w700)),
              const Spacer(),
              TextButton.icon(
                onPressed: () => _copiar(s),
                icon: const Icon(Icons.copy_rounded, size: 18),
                label: const Text('Copiar'),
              ),
            ],
          ),
          const SizedBox(height: 6),
          ...s.apuestas.map((a) => Padding(
                padding: const EdgeInsets.symmetric(vertical: 4),
                child: Text(
                  a.map((n) => n.toString().padLeft(2, '0')).join('  '),
                  style: GoogleFonts.spaceMono(
                      fontSize: 15, letterSpacing: 1),
                ),
              )),
        ],
      ),
    );
  }

  Widget _mini(String valor, String etiqueta) {
    final theme = Theme.of(context);
    return Column(
      children: [
        Text(valor,
            style: GoogleFonts.spaceMono(
                fontSize: 20,
                fontWeight: FontWeight.bold,
                color: theme.colorScheme.primary)),
        const SizedBox(height: 2),
        Text(etiqueta,
            style: GoogleFonts.rajdhani(
                fontSize: 12,
                color: theme.colorScheme.onSurface.withValues(alpha: 0.6))),
      ],
    );
  }

  Widget _tablaProbabilidades(ThemeData theme) {
    const nombres = {
      '3': '3 aciertos',
      '4': '4 aciertos',
      '5': '5 aciertos',
      '5C': '5 + complementario',
      '6': 'Pleno (los 6)',
    };
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
            color: theme.colorScheme.onSurface.withValues(alpha: 0.08)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('PROBABILIDAD REAL POR APUESTA',
              style: GoogleFonts.rajdhani(
                  fontSize: 16,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 1.5,
                  color: theme.colorScheme.primary)),
          const SizedBox(height: 4),
          Text('Para una apuesta de 6 números. Es la misma para todos: el '
              'sorteo es puro azar.',
              style: GoogleFonts.rajdhani(fontSize: 13)),
          const SizedBox(height: 12),
          ..._info!.categorias.map((c) => Padding(
                padding: const EdgeInsets.symmetric(vertical: 5),
                child: Row(
                  children: [
                    Expanded(
                      child: Text(nombres[c.clave] ?? c.clave,
                          style: GoogleFonts.rajdhani(fontSize: 15)),
                    ),
                    Text('1 entre ${_miles(c.unaEntre)}',
                        style: GoogleFonts.spaceMono(
                            fontSize: 14,
                            fontWeight: FontWeight.w600,
                            color: c.clave == '6'
                                ? BonolotoTheme.colorError
                                : theme.colorScheme.onSurface)),
                  ],
                ),
              )),
        ],
      ),
    );
  }

  Widget _notaHonesta(ThemeData theme) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: BonolotoTheme.amarillo.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: BonolotoTheme.amarillo.withValues(alpha: 0.3)),
      ),
      child: Text(
        'Sin trampa: el sistema sube tu opción de un premio MENOR (un 3 o un 4) '
        'porque cubre más combinaciones. NO cambia la opción del pleno, que '
        'sigue siendo 1 entre 13.983.816. Jugar más cuesta más, en proporción.',
        style: GoogleFonts.rajdhani(fontSize: 14),
      ),
    );
  }

  String _fmt(double? v) => (v ?? 0).toStringAsFixed(3);

  String _miles(int n) {
    final s = n.toString();
    final buf = StringBuffer();
    for (int i = 0; i < s.length; i++) {
      if (i > 0 && (s.length - i) % 3 == 0) buf.write('.');
      buf.write(s[i]);
    }
    return buf.toString();
  }

  void _copiar(SistemaGarantizado s) {
    final texto = StringBuffer()
      ..writeln('Sistema ${s.nombre} — ${s.garantiaTexto}')
      ..writeln('${s.nApuestas} apuestas · ${s.costeEur.toStringAsFixed(2)} €')
      ..writeln('');
    for (final a in s.apuestas) {
      texto.writeln(a.map((n) => n.toString().padLeft(2, '0')).join(' '));
    }
    texto.writeln('');
    texto.writeln('Pingarra 2026 — la app analiza y observa, no hace ganar.');
    mostrarNotaParaCopiar(context, texto.toString());
  }
}
