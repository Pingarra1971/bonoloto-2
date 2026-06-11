import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import '../state/app_notifier.dart';
import '../theme/app_theme.dart';
import '../models/models.dart';

/// Pantalla ÚLTIMO SORTEO.
///
/// Descarga el resultado oficial del último sorteo de Bonoloto (directamente
/// de loteriasapi.com con la API key) y lo compara al instante con las
/// combinaciones generadas por el usuario, resaltando los aciertos.
class UltimoSorteoScreen extends ConsumerStatefulWidget {
  const UltimoSorteoScreen({super.key});

  @override
  ConsumerState<UltimoSorteoScreen> createState() =>
      _UltimoSorteoScreenState();
}

class _UltimoSorteoScreenState extends ConsumerState<UltimoSorteoScreen> {
  Future<(ResultadoSorteo?, List<CombinacionBonoloto>)>? _futuro;

  @override
  void initState() {
    super.initState();
    _cargar();
  }

  void _cargar() {
    _futuro = ref.read(appProvider.notifier).obtenerSorteoConEvaluacion();
  }

  String _fecha(DateTime f) =>
      '${f.day.toString().padLeft(2, '0')}/'
      '${f.month.toString().padLeft(2, '0')}/${f.year}';

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final sinApiKey =
        ref.watch(appProvider).credenciales.loteriasApiKey.isEmpty;

    return Scaffold(
      appBar: AppBar(
        title: Text('ÚLTIMO SORTEO',
            style: GoogleFonts.rajdhani(
                fontWeight: FontWeight.w700, letterSpacing: 2)),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_rounded),
            tooltip: 'Actualizar',
            onPressed: () => setState(_cargar),
          ),
        ],
      ),
      body: sinApiKey
          ? _mensaje(
              theme,
              Icons.key_off_rounded,
              'Falta la API key',
              'Para ver el último sorteo, introduce tu API key de '
                  'loteriasapi.com en Ajustes → Credenciales.')
          : FutureBuilder<(ResultadoSorteo?, List<CombinacionBonoloto>)>(
              future: _futuro,
              builder: (ctx, snap) {
                if (snap.connectionState == ConnectionState.waiting) {
                  return const Center(child: CircularProgressIndicator());
                }
                final sorteo = snap.data?.$1;
                final evaluadas =
                    snap.data?.$2 ?? const <CombinacionBonoloto>[];
                if (sorteo == null) {
                  return _mensaje(
                    theme,
                    Icons.cloud_off_rounded,
                    'No se pudo obtener el sorteo',
                    'Comprueba tu conexión y tu API key. Pulsa el icono de '
                        'recargar para volver a intentarlo.',
                  );
                }
                return _contenido(theme, sorteo, evaluadas);
              },
            ),
    );
  }

  Widget _mensaje(ThemeData theme, IconData icono, String titulo, String texto) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icono,
                size: 60, color: BonolotoTheme.verdeAccent.withValues(alpha: 0.5)),
            const SizedBox(height: 18),
            Text(titulo,
                textAlign: TextAlign.center,
                style: GoogleFonts.rajdhani(
                    fontSize: 22, fontWeight: FontWeight.w700)),
            const SizedBox(height: 10),
            Text(texto,
                textAlign: TextAlign.center, style: theme.textTheme.bodyMedium),
          ],
        ),
      ),
    );
  }

  Widget _contenido(ThemeData theme, ResultadoSorteo sorteo,
      List<CombinacionBonoloto> combos) {
    final ganadores = sorteo.numeros.toSet();

    int mejor = 0;
    for (final c in combos) {
      final a = c.numeros.where(ganadores.contains).length;
      if (a > mejor) mejor = a;
    }

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        // Resultado oficial
        Container(
          padding: const EdgeInsets.all(18),
          decoration: BoxDecoration(
            color: Colors.white.withValues(alpha: 0.03),
            borderRadius: BorderRadius.circular(18),
            border: Border.all(
                color: BonolotoTheme.verdeAccent.withValues(alpha: 0.3)),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('RESULTADO OFICIAL',
                  style: GoogleFonts.rajdhani(
                      fontSize: 15,
                      fontWeight: FontWeight.w700,
                      letterSpacing: 1.5,
                      color: BonolotoTheme.verdeAccent)),
              const SizedBox(height: 2),
              Text('Sorteo del ${_fecha(sorteo.fecha)}',
                  style: theme.textTheme.bodyMedium),
              const SizedBox(height: 14),
              Center(child: _BolasComparadas(numeros: sorteo.numeros)),
              const SizedBox(height: 14),
              Row(
                children: [
                  _Etiqueta('Complementario', '${sorteo.complementario}'),
                  const SizedBox(width: 24),
                  _Etiqueta('Reintegro', '${sorteo.reintegro}'),
                ],
              ),
            ],
          ),
        ),
        const SizedBox(height: 22),

        Text('Combinaciones generadas para este sorteo',
            style: GoogleFonts.rajdhani(
                fontSize: 18, fontWeight: FontWeight.w700)),
        const SizedBox(height: 12),

        if (combos.isEmpty)
          Text(
            'Aún no hay combinaciones anteriores que comparar con este sorteo. '
            'Cuando se publique el próximo resultado, aquí verás cuántos '
            'números acertaron las combinaciones de hoy.',
            style: theme.textTheme.bodyMedium,
          )
        else ...[
          Container(
            padding: const EdgeInsets.all(14),
            margin: const EdgeInsets.only(bottom: 14),
            decoration: BoxDecoration(
              color: BonolotoTheme.amarillo.withValues(alpha: 0.08),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(
                  color: BonolotoTheme.amarillo.withValues(alpha: 0.3)),
            ),
            child: Row(
              children: [
                const Icon(Icons.emoji_events_outlined,
                    color: BonolotoTheme.amarillo, size: 22),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    mejor == 0
                        ? 'Las combinaciones no acertaron ningún número en este sorteo.'
                        : 'La mejor combinación acertó $mejor '
                            '${mejor == 1 ? "número" : "números"}.',
                    style: GoogleFonts.rajdhani(
                        fontSize: 16, fontWeight: FontWeight.w600),
                  ),
                ),
              ],
            ),
          ),
          ...List.generate(combos.length, (i) {
            final combo = combos[i];
            final aciertos = combo.numeros.where(ganadores.contains).length;
            return Container(
              margin: const EdgeInsets.only(bottom: 10),
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.03),
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text('Combinación ${i + 1}',
                          style: GoogleFonts.rajdhani(
                              fontSize: 14,
                              fontWeight: FontWeight.w600,
                              color: Colors.white70)),
                      Text(
                        '$aciertos ${aciertos == 1 ? "acierto" : "aciertos"}',
                        style: GoogleFonts.rajdhani(
                            fontSize: 16,
                            fontWeight: FontWeight.w700,
                            color: aciertos >= 3
                                ? BonolotoTheme.amarillo
                                : (aciertos > 0
                                    ? BonolotoTheme.verdeAccent
                                    : Colors.white38)),
                      ),
                    ],
                  ),
                  const SizedBox(height: 10),
                  _BolasComparadas(
                      numeros: combo.numeros, ganadores: ganadores),
                ],
              ),
            );
          }),
          const SizedBox(height: 8),
          Text(
            'Recuerda: acertar números es cuestión de azar. Que coincidan '
            'pocos o ninguno es lo más habitual y esperable.',
            style: theme.textTheme.bodySmall,
          ),
        ],
      ],
    );
  }
}

/// Fila de bolas. Si se pasan `ganadores`, las bolas acertadas se resaltan
/// en amarillo y las no acertadas se atenúan.
class _BolasComparadas extends StatelessWidget {
  final List<int> numeros;
  final Set<int>? ganadores;

  const _BolasComparadas({required this.numeros, this.ganadores});

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: numeros.map((n) {
        final acierto = ganadores == null ? true : ganadores!.contains(n);
        return Container(
          width: 46,
          height: 46,
          alignment: Alignment.center,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: acierto
                ? BonolotoTheme.amarillo
                : Colors.transparent,
            border: Border.all(
              color: acierto
                  ? BonolotoTheme.amarillo
                  : Colors.white.withValues(alpha: 0.25),
              width: 2,
            ),
          ),
          child: Text(
            n.toString().padLeft(2, '0'),
            style: GoogleFonts.rajdhani(
              fontSize: 19,
              fontWeight: FontWeight.w700,
              color: acierto ? const Color(0xFF081209) : Colors.white54,
            ),
          ),
        );
      }).toList(),
    );
  }
}

class _Etiqueta extends StatelessWidget {
  final String titulo;
  final String valor;

  const _Etiqueta(this.titulo, this.valor);

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(titulo,
            style: GoogleFonts.rajdhani(
                fontSize: 13, color: Colors.white54, letterSpacing: 0.5)),
        const SizedBox(height: 2),
        Text(valor,
            style: GoogleFonts.rajdhani(
                fontSize: 22,
                fontWeight: FontWeight.w700,
                color: BonolotoTheme.colorInfo)),
      ],
    );
  }
}
