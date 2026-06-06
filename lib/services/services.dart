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
    buffer.writeln('⚡ Motor: Oracle Cloud | análisis estadístico');
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
    buffer.writeln('    Motor: Oracle Cloud | análisis estadístico');
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
