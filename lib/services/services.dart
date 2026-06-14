import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart';
import '../models/models.dart';

// ═══════════════════════════════════════════════════════════
// SERVICIO LOTERIAS API
// ═══════════════════════════════════════════════════════════
class LoteriasApiService {
  final Credenciales _credenciales;
  // API actual: base /api/v1, autenticación por cabecera X-API-Key.
  static const String _baseUrl = 'https://api.loteriasapi.com/api/v1';

  LoteriasApiService(this._credenciales);

  Map<String, String> get _headers => {
        'Content-Type': 'application/json',
        'X-API-Key': _credenciales.loteriasApiKey,
      };

  static const Duration _timeout = Duration(seconds: 15);

  Future<ResultadoSorteo?> obtenerUltimoResultado() async {
    try {
      final response = await http.get(
        Uri.parse('$_baseUrl/results/bonoloto/latest'),
        headers: _headers,
      ).timeout(_timeout);

      if (response.statusCode == 200) {
        final decoded = jsonDecode(response.body);
        // La API envuelve el resultado en { "data": {...} }
        final data = (decoded is Map && decoded['data'] is Map)
            ? Map<String, dynamic>.from(decoded['data'])
            : (decoded is Map<String, dynamic> ? decoded : null);
        if (data != null) {
          return ResultadoSorteo.fromJson(data);
        }
        return null;
      }
    } catch (e) {
      return null;
    }
    return null;
  }

  Future<List<ResultadoSorteo>> obtenerHistoricoSorteos({int limite = 500}) async {
    try {
      final response = await http.get(
        Uri.parse('$_baseUrl/results/bonoloto/history?limit=$limite'),
        headers: _headers,
      ).timeout(_timeout);

      if (response.statusCode == 200) {
        final decoded = jsonDecode(response.body);
        // Puede venir como { "data": [...] } o como lista directa.
        final List sorteos = decoded is Map
            ? (decoded['data'] ?? decoded['sorteos'] ?? decoded['results'] ?? [])
            : (decoded is List ? decoded : []);
        return sorteos
            .whereType<Map>()
            .map((s) => ResultadoSorteo.fromJson(
                Map<String, dynamic>.from(s)))
            .toList();
      }
    } catch (e) {
      return [];
    }
    return [];
  }

  Future<List<EstadisticasNumero>> obtenerEstadisticas() async {
    try {
      final sorteos = await obtenerHistoricoSorteos(limite: 500);
      if (sorteos.isEmpty) return [];

      final Map<int, List<int>> apariciones = {};
      for (int n = 1; n <= 49; n++) {
        apariciones[n] = [];
      }

      for (int i = 0; i < sorteos.length; i++) {
        for (final num in sorteos[i].numeros) {
          if (num >= 1 && num <= 49) {
            apariciones[num]!.add(i);
          }
        }
      }

      final List<EstadisticasNumero> stats = [];
      final totalSorteos = sorteos.length;

      for (int n = 1; n <= 49; n++) {
        final aparic = apariciones[n]!;
        final frec50 = aparic.where((i) => i < 50).length;
        final frec100 = aparic.where((i) => i < 100).length;
        final frec500 = aparic.where((i) => i < 500).length;

        final frecRelativa = aparic.length / totalSorteos;
        final esperada = 6 / 49;
        String clasif;
        if (frecRelativa > esperada * 1.15) {
          clasif = 'caliente';
        } else if (frecRelativa < esperada * 0.85) {
          clasif = 'frio';
        } else {
          clasif = 'neutro';
        }

        stats.add(EstadisticasNumero(
          numero: n,
          frecuenciaTotal: aparic.length,
          frecuenciaUltimos50: frec50,
          frecuenciaUltimos100: frec100,
          frecuenciaUltimos500: frec500,
          ultimaAparicionHace: aparic.isNotEmpty ? aparic.first : null,
          clasificacion: clasif,
        ));
      }

      return stats;
    } catch (e) {
      return [];
    }
  }

  Future<bool> verificarApiKey() async {
    try {
      final response = await http.get(
        Uri.parse('$_baseUrl/results/bonoloto/latest'),
        headers: _headers,
      ).timeout(const Duration(seconds: 10));
      return response.statusCode == 200;
    } catch (e) {
      return false;
    }
  }
}

// ═══════════════════════════════════════════════════════════
// SERVICIO DATOS DIARIOS (GitHub)
//
// El cálculo ya NO se hace en un servidor en vivo. Cada día, una tarea
// automática (GitHub Actions) genera las combinaciones y las publica en un
// fichero JSON público. La app solo tiene que descargarlo. Sin servidor, sin
// login, sin clave de API.
// ═══════════════════════════════════════════════════════════

/// Resumen honesto de cuánto acierta la app a lo largo del tiempo (track
/// record), calculado por el backend a partir de la comparación de cada
/// sorteo. 'referenciaAzar' es lo que se acertaría por puro azar: sirve para
/// ver, sin trampa, que la app ronda el azar.
class TrackRecord {
  final int nSorteos;
  final double mediaMejor;
  final int mejorHistorico;
  final double referenciaAzar;
  final Map<String, int> distribucion;
  final List<int> serieMejor;

  const TrackRecord({
    required this.nSorteos,
    required this.mediaMejor,
    required this.mejorHistorico,
    required this.referenciaAzar,
    required this.distribucion,
    this.serieMejor = const [],
  });

  static TrackRecord? fromJson(Map<String, dynamic> j) {
    final n = (j['n_sorteos'] as num?)?.toInt() ?? 0;
    if (n <= 0) return null;
    final dist = <String, int>{};
    if (j['distribucion'] is Map) {
      (j['distribucion'] as Map).forEach((k, v) {
        dist[k.toString()] = (v as num?)?.toInt() ?? 0;
      });
    }
    final serie = (j['registros'] as List? ?? [])
        .whereType<Map>()
        .map((r) => (r['mejor'] as num?)?.toInt() ?? 0)
        .toList();
    return TrackRecord(
      nSorteos: n,
      mediaMejor: (j['media_mejor'] as num?)?.toDouble() ?? 0,
      mejorHistorico: (j['mejor_historico'] as num?)?.toInt() ?? 0,
      referenciaAzar: (j['referencia_azar'] as num?)?.toDouble() ?? 0,
      distribucion: dist,
      serieMejor: serie,
    );
  }
}

/// Una categoría de premio de la Bonoloto con su probabilidad real por
/// apuesta (hipergeométrica exacta; no depende de qué números elijas).
class CategoriaPremio {
  final String clave; // "3", "4", "5", "5C", "6"
  final int unaEntre;
  final double prob;
  const CategoriaPremio(this.clave, this.unaEntre, this.prob);
}

/// Un nivel de sistema con garantía combinatoria verificada
/// (Económico / Equilibrado / Fuerte).
class SistemaGarantizado {
  final String nombre;
  final String descripcion;
  final int garantiaT;
  final int garantiaP;
  final String garantiaTexto;
  final List<int> pool;
  final int nApuestas;
  final double costeEur;
  final bool verificada;
  final List<List<int>> apuestas;
  final Map<String, double> esperadoPorSorteo;

  const SistemaGarantizado({
    required this.nombre,
    required this.descripcion,
    required this.garantiaT,
    required this.garantiaP,
    required this.garantiaTexto,
    required this.pool,
    required this.nApuestas,
    required this.costeEur,
    required this.verificada,
    required this.apuestas,
    required this.esperadoPorSorteo,
  });

  static SistemaGarantizado fromJson(Map<String, dynamic> j) {
    final g = (j['garantia'] is Map)
        ? Map<String, dynamic>.from(j['garantia'])
        : <String, dynamic>{};
    final apuestas = (j['apuestas'] as List? ?? []).map<List<int>>((a) {
      final m = a is Map ? Map<String, dynamic>.from(a) : <String, dynamic>{};
      return (m['numeros'] as List? ?? [])
          .map((n) => (n as num).toInt())
          .toList();
    }).toList();
    final esperado = <String, double>{};
    if (j['esperado_por_sorteo'] is Map) {
      (j['esperado_por_sorteo'] as Map).forEach((k, v) {
        esperado[k.toString()] = (v as num?)?.toDouble() ?? 0;
      });
    }
    return SistemaGarantizado(
      nombre: (j['nombre'] ?? '').toString(),
      descripcion: (j['descripcion'] ?? '').toString(),
      garantiaT: (g['t'] as num?)?.toInt() ?? 0,
      garantiaP: (g['p'] as num?)?.toInt() ?? 0,
      garantiaTexto: (g['texto'] ?? '').toString(),
      pool: (j['pool'] as List? ?? []).map((n) => (n as num).toInt()).toList(),
      nApuestas: (j['n_apuestas'] as num?)?.toInt() ?? apuestas.length,
      costeEur: (j['coste_eur'] as num?)?.toDouble() ?? 0,
      verificada: j['verificada_fuerza_bruta'] == true,
      apuestas: apuestas,
      esperadoPorSorteo: esperado,
    );
  }
}

/// Los 3 niveles de sistema con garantía + la tabla de probabilidades por
/// categoría de premio. Es lo único con efecto REAL: mejora la opción de un
/// premio menor (garantía) y enseña la probabilidad de cada categoría.
class SistemasInfo {
  final List<SistemaGarantizado> sistemas;
  final List<CategoriaPremio> categorias;
  const SistemasInfo({this.sistemas = const [], this.categorias = const []});

  static SistemasInfo? fromJson(dynamic sistemasJson, dynamic probsJson) {
    if (sistemasJson is! List || sistemasJson.isEmpty) return null;
    final sistemas = sistemasJson
        .whereType<Map>()
        .map((m) => SistemaGarantizado.fromJson(Map<String, dynamic>.from(m)))
        .toList();
    final categorias = <CategoriaPremio>[];
    if (probsJson is Map) {
      for (final clave in const ['3', '4', '5', '5C', '6']) {
        if (probsJson[clave] is Map) {
          final c = Map<String, dynamic>.from(probsJson[clave]);
          categorias.add(CategoriaPremio(
            clave,
            (c['una_entre'] as num?)?.toInt() ?? 0,
            (c['prob'] as num?)?.toDouble() ?? 0,
          ));
        }
      }
    }
    return SistemasInfo(sistemas: sistemas, categorias: categorias);
  }
}

/// Datos del día ya parseados: combinaciones, apuestas múltiples, último
/// sorteo, estadísticas y rendimiento aproximado por algoritmo.
class DatosDiarios {
  final List<CombinacionBonoloto> combinaciones;
  final Map<String, dynamic>? apuestasMultiples;
  final ResultadoSorteo? ultimoSorteo;
  final List<EstadisticasNumero> estadisticas;
  final List<RendimientoAlgoritmo> rendimientoAlgoritmos;
  final List<String> mejorasActivas;
  final DateTime? fechaSorteo;
  final int totalHistorico;
  final TrackRecord? trackRecord;
  final SistemasInfo? sistemasInfo;

  /// Predicción que se hizo PARA el último sorteo (la de "ayer"), ya con los
  /// aciertos calculados contra el resultado real. Vacía si no hay nada que
  /// comparar todavía.
  final List<CombinacionBonoloto> prediccionEvaluada;

  const DatosDiarios({
    this.combinaciones = const [],
    this.apuestasMultiples,
    this.ultimoSorteo,
    this.estadisticas = const [],
    this.rendimientoAlgoritmos = const [],
    this.mejorasActivas = const [],
    this.fechaSorteo,
    this.totalHistorico = 0,
    this.trackRecord,
    this.sistemasInfo,
    this.prediccionEvaluada = const [],
  });
}

class DatosDiariosService {
  /// URL pública del JSON que genera GitHub Actions cada día.
  /// Si algún día cambias de repositorio, solo hay que cambiar esta línea.
  static const String urlJson =
      'https://raw.githubusercontent.com/Pingarra1971/bonoloto-2/main/docs/combinaciones.json';

  static const Duration _timeout = Duration(seconds: 20);

  Future<DatosDiarios?> descargar() async {
    try {
      final response =
          await http.get(Uri.parse(urlJson)).timeout(_timeout);
      if (response.statusCode != 200) return null;

      final decoded = jsonDecode(utf8.decode(response.bodyBytes));
      if (decoded is! Map) return null;
      final json = Map<String, dynamic>.from(decoded);

      final combinaciones = (json['combinaciones'] as List? ?? [])
          .whereType<Map>()
          .map((c) =>
              CombinacionBonoloto.fromJson(Map<String, dynamic>.from(c)))
          .toList();

      ResultadoSorteo? ultimo;
      if (json['ultimo_sorteo'] is Map) {
        final us = Map<String, dynamic>.from(json['ultimo_sorteo']);
        // El "bote" llega en céntimos desde la API; lo pasamos a euros.
        if (us['bote'] is num) {
          us['bote'] = (us['bote'] as num) ~/ 100;
        }
        ultimo = ResultadoSorteo.fromJson(us);
      }

      final estadisticas = (json['estadisticas'] as List? ?? [])
          .whereType<Map>()
          .map((m) =>
              EstadisticasNumero.fromJson(Map<String, dynamic>.from(m)))
          .toList();

      final mejoras = (json['mejoras_activas'] as List? ?? [])
          .map((e) => e.toString())
          .toList();

      // Predicción del día anterior (la que se hizo PARA el último sorteo),
      // con los aciertos ya calculados por el backend.
      List<CombinacionBonoloto> prediccionEvaluada = const [];
      if (json['evaluacion'] is Map) {
        final ev = Map<String, dynamic>.from(json['evaluacion']);
        prediccionEvaluada = (ev['predicciones'] as List? ?? [])
            .whereType<Map>()
            .map((p) =>
                CombinacionBonoloto.fromJson(Map<String, dynamic>.from(p)))
            .toList();
      }

      return DatosDiarios(
        combinaciones: combinaciones,
        apuestasMultiples: json['apuestas_multiples'] is Map
            ? Map<String, dynamic>.from(json['apuestas_multiples'])
            : null,
        ultimoSorteo: ultimo,
        estadisticas: estadisticas,
        rendimientoAlgoritmos: _derivarRendimiento(combinaciones),
        mejorasActivas: mejoras,
        fechaSorteo: json['fecha_sorteo'] != null
            ? DateTime.tryParse(json['fecha_sorteo'].toString())
            : null,
        totalHistorico: (json['total_historico'] is num)
            ? (json['total_historico'] as num).toInt()
            : 0,
        trackRecord: json['track_record'] is Map
            ? TrackRecord.fromJson(
                Map<String, dynamic>.from(json['track_record']))
            : null,
        sistemasInfo: SistemasInfo.fromJson(
            json['sistemas'], json['probabilidades_categoria']),
        prediccionEvaluada: prediccionEvaluada,
      );
    } catch (e) {
      return null;
    }
  }

  /// Rendimiento aproximado por algoritmo: el peso medio que tuvo cada uno en
  /// las combinaciones del día. Sirve para que el panel "Algoritmos" muestre
  /// algo coherente sin depender de un servidor.
  List<RendimientoAlgoritmo> _derivarRendimiento(
      List<CombinacionBonoloto> combos) {
    if (combos.isEmpty) return const [];
    final Map<String, List<double>> pesos = {};
    for (final c in combos) {
      c.pesosPorAlgoritmo.forEach((k, v) {
        (pesos[k] ??= <double>[]).add(v);
      });
    }
    const nombres = {
      'entropia': 'Entropía',
      'hot_cold_bias': 'Hot/Cold Bias',
      'covarianza': 'Covarianza',
      'lstm': 'LSTM',
      'transformer': 'Transformer',
      'markov': 'Markov',
      'bayesiano': 'Bayesiano',
      'xgboost': 'XGBoost',
      'reinforcement_learning': 'Reinforcement Learning',
      'monte_carlo': 'Monte Carlo',
    };
    final lista = <RendimientoAlgoritmo>[];
    pesos.forEach((clave, valores) {
      final media =
          valores.fold<double>(0.0, (a, b) => a + b) / valores.length;
      lista.add(RendimientoAlgoritmo(
        nombre: nombres[clave] ?? clave,
        pesoActual: media,
        tasaAciertosHistorica: 0.0,
        totalPredicciones: combos.length,
        historialPesos: valores,
      ));
    });
    lista.sort((a, b) => b.pesoActual.compareTo(a.pesoActual));
    return lista;
  }
}

// ═══════════════════════════════════════════════════════════
// SERVICIO TELEGRAM
// ═══════════════════════════════════════════════════════════
class TelegramService {
  final Credenciales _credenciales;

  TelegramService(this._credenciales);

  String get _apiUrl =>
      'https://api.telegram.org/bot${_credenciales.telegramBotToken}';

  Future<bool> enviarMensaje(String mensaje) async {
    try {
      final response = await http.post(
        Uri.parse('$_apiUrl/sendMessage'),
        body: {
          'chat_id': _credenciales.telegramChatId,
          'text': mensaje,
          'parse_mode': 'HTML',
        },
      ).timeout(const Duration(seconds: 15));
      return response.statusCode == 200;
    } catch (e) {
      return false;
    }
  }

  Future<void> enviarCombinaciones(
    List<CombinacionBonoloto> combinaciones,
    DateTime fecha,
  ) async {
    final buffer = StringBuffer();
    buffer.writeln('🍀 <b>BONOLOTO 2.0</b>');
    buffer.writeln('📅 ${_formatearFecha(fecha)}');
    buffer.writeln('━━━━━━━━━━━━━━━━━━━━━━');
    buffer.writeln('');

    for (int i = 0; i < combinaciones.length; i++) {
      final combo = combinaciones[i];
      buffer.writeln(
          '<b>Combinación ${i + 1}</b> — Confianza: ${combo.indiceConfianza.toStringAsFixed(1)}%');
      buffer.writeln('🎱 ${combo.numerosFormateados}');
      buffer.writeln('');
    }

    buffer.writeln('━━━━━━━━━━━━━━━━━━━━━━');
    buffer.writeln('⚡ Análisis estadístico automático');
    buffer.writeln('🕘 Sorteo: 21:30h hora peninsular');

    await enviarMensaje(buffer.toString());
  }

  Future<bool> verificarConexion() async {
    try {
      final response = await http
          .get(Uri.parse('$_apiUrl/getMe'))
          .timeout(const Duration(seconds: 10));
      return response.statusCode == 200;
    } catch (e) {
      return false;
    }
  }

  String _formatearFecha(DateTime fecha) {
    const dias = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'];
    const meses = [
      'Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun',
      'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'
    ];
    return '${dias[fecha.weekday - 1]} ${fecha.day} ${meses[fecha.month - 1]} ${fecha.year}';
  }
}

// ═══════════════════════════════════════════════════════════
// SERVICIO EXPORTACIÓN
// ═══════════════════════════════════════════════════════════
class ExportService {
  Future<void> exportar(
    List<CombinacionBonoloto> combinaciones,
    String formato,
  ) async {
    switch (formato.toLowerCase()) {
      case 'pdf':
        await _exportarPDF(combinaciones);
        break;
      case 'excel':
      case 'csv':
        await _exportarCSV(combinaciones);
        break;
      case 'txt':
        await _exportarTXT(combinaciones);
        break;
    }
  }

  Future<void> _exportarPDF(List<CombinacionBonoloto> combinaciones) async {
    final dir = await getTemporaryDirectory();
    final archivo = File('${dir.path}/bonoloto_predicciones.txt');
    // PDF generación usando el paquete pdf en implementación completa
    // Por ahora exportar como texto formateado
    await _escribirContenido(archivo, combinaciones);
    await Share.shareXFiles([XFile(archivo.path)],
        subject: 'Bonoloto 2.0 — Combinaciones');
  }

  Future<void> _exportarCSV(List<CombinacionBonoloto> combinaciones) async {
    final dir = await getTemporaryDirectory();
    final archivo = File('${dir.path}/bonoloto_predicciones.csv');
    final buffer = StringBuffer();
    buffer.writeln('N1,N2,N3,N4,N5,N6,Confianza(%),Fecha,Aciertos');
    for (final combo in combinaciones) {
      buffer.writeln(
          '${combo.numeros.join(",")},${combo.indiceConfianza.toStringAsFixed(1)},${combo.fechaGeneracion.toIso8601String()},${combo.aciertos ?? "-"}');
    }
    await archivo.writeAsString(buffer.toString());
    await Share.shareXFiles([XFile(archivo.path)],
        subject: 'Bonoloto 2.0 — Combinaciones CSV');
  }

  Future<void> _exportarTXT(List<CombinacionBonoloto> combinaciones) async {
    final dir = await getTemporaryDirectory();
    final archivo = File('${dir.path}/bonoloto_predicciones.txt');
    await _escribirContenido(archivo, combinaciones);
    await Share.shareXFiles([XFile(archivo.path)],
        subject: 'Bonoloto 2.0 — Combinaciones TXT');
  }

  Future<void> _escribirContenido(
    File archivo,
    List<CombinacionBonoloto> combinaciones,
  ) async {
    final buffer = StringBuffer();
    buffer.writeln('═══════════════════════════════════════');
    buffer.writeln('    BONOLOTO 2.0');
    buffer.writeln('    Análisis estadístico automático');
    buffer.writeln('═══════════════════════════════════════\n');

    for (int i = 0; i < combinaciones.length; i++) {
      final combo = combinaciones[i];
      buffer.writeln('Combinación ${i + 1}:');
      buffer.writeln('  Números: ${combo.numerosFormateados}');
      buffer.writeln(
          '  Confianza: ${combo.indiceConfianza.toStringAsFixed(1)}%');
      buffer.writeln(
          '  Generada: ${combo.fechaGeneracion.day}/${combo.fechaGeneracion.month}/${combo.fechaGeneracion.year}');
      if (combo.aciertos != null) {
        buffer.writeln('  Aciertos: ${combo.aciertos}');
      }
      buffer.writeln('');
    }
    await archivo.writeAsString(buffer.toString());
  }

  // ─────────────────────────────────────────────────────────
  // DESCARGA DIRECTA (sin menú de compartir) — guarda el archivo en el
  // dispositivo y devuelve la ruta donde quedó guardado.
  // ─────────────────────────────────────────────────────────
  Future<String> descargarEnDispositivo(
    List<CombinacionBonoloto> combinaciones,
    String formato,
  ) async {
    final fmt = formato.toLowerCase();
    final ext = fmt == 'csv' ? 'csv' : 'txt';
    final marca = DateTime.now().millisecondsSinceEpoch;
    final nombre = 'bonoloto_combinaciones_$marca.$ext';
    final contenido =
        fmt == 'csv' ? _contenidoCsv(combinaciones) : _contenidoTxt(combinaciones);

    final destino = await _directorioDescargas();
    final archivo = File('${destino.path}/$nombre');
    await archivo.writeAsString(contenido);
    return archivo.path;
  }

  /// Elige dónde guardar: primero la carpeta pública de Descargas (visible en
  /// el explorador de archivos); si no es accesible (Android moderno), usa un
  /// directorio propio de la app que SIEMPRE es escribible sin permisos.
  Future<Directory> _directorioDescargas() async {
    try {
      final publica = Directory('/storage/emulated/0/Download');
      if (await publica.exists()) {
        // Comprobamos que realmente podemos escribir ahí.
        final prueba = File('${publica.path}/.bonoloto_w');
        await prueba.writeAsString('ok');
        await prueba.delete();
        return publica;
      }
    } catch (_) {
      // Sin acceso a la carpeta pública: caemos al almacenamiento de la app.
    }
    final externo = await getExternalStorageDirectory();
    if (externo != null) return externo;
    return getApplicationDocumentsDirectory();
  }

  String _contenidoCsv(List<CombinacionBonoloto> combinaciones) {
    final buffer = StringBuffer();
    buffer.writeln('N1,N2,N3,N4,N5,N6,Confianza(%),Fecha,Aciertos');
    for (final combo in combinaciones) {
      buffer.writeln(
          '${combo.numeros.join(",")},${combo.indiceConfianza.toStringAsFixed(1)},${combo.fechaGeneracion.toIso8601String()},${combo.aciertos ?? "-"}');
    }
    return buffer.toString();
  }

  String _contenidoTxt(List<CombinacionBonoloto> combinaciones) {
    final buffer = StringBuffer();
    buffer.writeln('═══════════════════════════════════════');
    buffer.writeln('    BONOLOTO 2.0');
    buffer.writeln('    Análisis estadístico automático');
    buffer.writeln('═══════════════════════════════════════\n');
    for (int i = 0; i < combinaciones.length; i++) {
      final combo = combinaciones[i];
      buffer.writeln('Combinación ${i + 1}:');
      buffer.writeln('  Números: ${combo.numerosFormateados}');
      buffer.writeln(
          '  Confianza: ${combo.indiceConfianza.toStringAsFixed(1)}%');
      buffer.writeln(
          '  Generada: ${combo.fechaGeneracion.day}/${combo.fechaGeneracion.month}/${combo.fechaGeneracion.year}');
      if (combo.aciertos != null) {
        buffer.writeln('  Aciertos: ${combo.aciertos}');
      }
      buffer.writeln('');
    }
    buffer.writeln('Recuerda: jugar es azar. La probabilidad del pleno es '
        '1 entre 13.983.816 para cualquier combinación.');
    return buffer.toString();
  }

  // ─────────────────────────────────────────────────────────
  // NOTA EN TEXTO PLANO — pensada para copiar y pegar en otra app
  // (WhatsApp, Notas, correo...). Compacta y clara.
  // ─────────────────────────────────────────────────────────
  String construirNota(List<CombinacionBonoloto> combinaciones) {
    final buffer = StringBuffer();
    final f = DateTime.now();
    final fecha = '${f.day.toString().padLeft(2, '0')}/'
        '${f.month.toString().padLeft(2, '0')}/${f.year}';
    buffer.writeln('Bonoloto 2.0 — Combinaciones');
    buffer.writeln(fecha);
    buffer.writeln('');
    for (int i = 0; i < combinaciones.length; i++) {
      final nums = combinaciones[i]
          .numeros
          .map((n) => n.toString().padLeft(2, '0'))
          .join(' - ');
      buffer.writeln('${i + 1}) $nums');
    }
    buffer.writeln('');
    buffer.write('Recuerda: jugar es azar. La probabilidad del pleno es '
        '1 entre 13.983.816 para cualquier combinación.');
    return buffer.toString();
  }
}

// ═══════════════════════════════════════════════════════════
// SERVICIO BACKUP
// ═══════════════════════════════════════════════════════════
class BackupService {
  final ConfiguracionApp _config;
  BackupService(this._config);

  Future<void> realizarBackup({
    required List<SesionPrediccion> historial,
    required ConfiguracionApp configuracion,
    required Credenciales credenciales,
  }) async {
    final dir = await getApplicationDocumentsDirectory();
    final archivo = File('${dir.path}/bonoloto_backup_${DateTime.now().millisecondsSinceEpoch}.json');

    final backup = {
      'version': '1.0.0',
      'fecha': DateTime.now().toIso8601String(),
      'historial': historial.map((s) => s.toJson()).toList(),
      'configuracion': configuracion.toJson(),
    };

    await archivo.writeAsString(jsonEncode(backup));
    await Share.shareXFiles(
      [XFile(archivo.path)],
      subject: 'Bonoloto 2.0 — Backup ${DateTime.now().day}/${DateTime.now().month}/${DateTime.now().year}',
    );
  }
}

// ═══════════════════════════════════════════════════════════
// SERVICIO NOTIFICACIONES
// ═══════════════════════════════════════════════════════════
// Nota: las notificaciones locales están temporalmente desactivadas.
// La librería flutter_local_notifications 16.x tiene un bug de compilación
// en Android moderno (issue #2329, método bigLargeIcon ambiguo). Como las
// notificaciones no son esenciales para el uso de la app (observar las
// combinaciones), se ha dejado este servicio como un stub sin dependencias.
// Para reactivarlas en el futuro: actualizar flutter_local_notifications a
// una versión >= 17.2.2 en pubspec.yaml y restaurar la implementación real.
class NotificationService {
  Future<void> inicializar() async {
    // Sin operación: notificaciones desactivadas por ahora.
  }

  Future<void> mostrarNotificacion({
    required String titulo,
    required String cuerpo,
  }) async {
    // Sin operación: notificaciones desactivadas por ahora.
    // El título y el cuerpo se ignoran de forma intencionada.
  }
}
