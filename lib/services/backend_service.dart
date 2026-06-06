import 'dart:async';
import 'package:dio/dio.dart';

import '../models/models.dart';
import 'api_client.dart';
import 'sse_client.dart';

/// Servicio que habla con el backend Bonoloto 2.0 desplegado en Oracle Cloud.
///
/// Características:
///   - Usa dio + interceptors (no http crudo)
///   - Soporta SSE para progreso en tiempo real
///   - CancelToken para abortar llamadas en curso
///   - Todos los métodos devuelven datos tipados (no `Future<dynamic>`)
class BackendService {
  final ApiClient _api;
  CancelToken? _calculoCancel;

  BackendService(this._api);

  /// Actualiza el token JWT. Llamar después de obtenerlo del backend.
  set authToken(String? token) {
    _api.authToken = token;
  }

  /// Actualiza la base URL (e.g. cuando el usuario cambia de servidor).
  void updateBaseUrl(String url) => _api.updateBaseUrl(url);

  // ─────────────────────────────────────────────
  // CICLO DE VIDA DE CÁLCULO
  // ─────────────────────────────────────────────

  /// Inicia un cálculo nuevo. Devuelve el trabajo_id si todo OK.
  /// Lanza `BackendError` con detalle si falla.
  Future<String> iniciarCalculo({
    required int cantidad,
    required double presupuestoEur,
    required double boteAcumuladoEur,
    String loteria = 'bonoloto',
  }) async {
    final resp = await _api.post(
      '/api/calculo/iniciar',
      data: {
        'cantidad': cantidad,
        'presupuesto_eur': presupuestoEur,
        'bote_acumulado_eur': boteAcumuladoEur,
        'loteria': loteria,
      },
    );

    if (resp == null) {
      throw BackendError('Sin respuesta del servidor');
    }
    if (resp.statusCode != 200 && resp.statusCode != 201) {
      throw BackendError(
        'Error iniciando cálculo: HTTP ${resp.statusCode}',
        statusCode: resp.statusCode,
      );
    }

    final data = resp.data;
    if (data is! Map) {
      throw BackendError('Respuesta inesperada: ${resp.data}');
    }
    final trabajoId = data['trabajo_id'];
    if (trabajoId is! String || trabajoId.isEmpty) {
      throw BackendError('Respuesta sin trabajo_id válido');
    }
    return trabajoId;
  }

  /// Streaming de progreso vía SSE.
  ///
  /// Devuelve un Stream<ProgresoCalculo>. El stream se cierra automáticamente
  /// cuando el backend emite `event: completado` o `event: error`.
  ///
  /// Para cancelar antes: `stream.listen(...).cancel()`.
  Stream<ProgresoCalculo> streamProgreso(String trabajoId) {
    final baseUrl = _api.dio.options.baseUrl.replaceAll(RegExp(r'/$'), '');
    final url = Uri.parse('$baseUrl/api/calculo/stream/$trabajoId');

    final headers = <String, String>{};
    final token = _api.authToken;
    if (token != null && token.isNotEmpty) {
      headers['Authorization'] = 'Bearer $token';
    }

    final client = SseClient(url: url, headers: headers);
    final controller = StreamController<ProgresoCalculo>();

    late StreamSubscription sub;
    sub = client.connect().listen(
      (event) {
        // Eventos según protocolo del backend (Sesión 2)
        switch (event.type) {
          case 'progreso':
            final json = event.dataJson;
            if (json != null) {
              controller.add(ProgresoCalculo.fromJson(json));
            }
            break;
          case 'completado':
            // Emitir un progreso final marcando estado completado
            controller.add(const ProgresoCalculo(
              estado: EstadoCalculo.completado,
              progresoGeneral: 1.0,
              indiceConfianza: 0.0,
              iteracion: 0,
              convergiendo: false,
              estadoAlgoritmos: {},
              mensaje: 'completado',
            ));
            sub.cancel();
            controller.close();
            break;
          case 'error':
          case 'timeout':
            final json = event.dataJson;
            final msg = json?['error']?.toString() ?? event.data;
            controller.add(ProgresoCalculo(
              estado: EstadoCalculo.error,
              progresoGeneral: 0.0,
              indiceConfianza: 0.0,
              iteracion: 0,
              convergiendo: false,
              estadoAlgoritmos: const {},
              mensaje: msg,
            ));
            sub.cancel();
            controller.close();
            break;
        }
      },
      onError: (err) {
        controller.add(ProgresoCalculo(
          estado: EstadoCalculo.error,
          progresoGeneral: 0.0,
          indiceConfianza: 0.0,
          iteracion: 0,
          convergiendo: false,
          estadoAlgoritmos: const {},
          mensaje: 'Error conexión SSE: $err',
        ));
        controller.close();
      },
      onDone: () => controller.close(),
    );

    // Cuando el cliente del stream cancele, cerramos la conexión SSE
    controller.onCancel = () async {
      await sub.cancel();
      await client.close();
    };

    return controller.stream;
  }

  /// Polling clásico (fallback si SSE no funciona).
  Future<ProgresoCalculo?> obtenerProgreso(String trabajoId) async {
    final resp = await _api.get('/api/calculo/progreso/$trabajoId');
    if (resp == null || resp.statusCode != 200) return null;
    if (resp.data is! Map) return null;
    return ProgresoCalculo.fromJson(Map<String, dynamic>.from(resp.data));
  }

  /// Obtiene el resultado final de un trabajo completado.
  Future<ResultadoCalculo> obtenerResultado(String trabajoId) async {
    final resp = await _api.get('/api/calculo/resultado/$trabajoId');
    if (resp == null) {
      throw BackendError('Sin respuesta del servidor');
    }
    if (resp.statusCode != 200) {
      throw BackendError(
        'Error obteniendo resultado: HTTP ${resp.statusCode}',
        statusCode: resp.statusCode,
      );
    }
    if (resp.data is! Map) {
      throw BackendError('Respuesta inesperada: ${resp.data}');
    }
    return ResultadoCalculo.fromJson(Map<String, dynamic>.from(resp.data));
  }

  /// Estado de la cola de trabajos (cuántos pendientes, en ejecución).
  /// Nuevo en Sesión 2.
  Future<Map<String, dynamic>?> estadoCola() async {
    final resp = await _api.get('/api/calculo/estado-cola');
    if (resp == null || resp.statusCode != 200) return null;
    if (resp.data is Map) {
      return Map<String, dynamic>.from(resp.data);
    }
    return null;
  }

  /// Comprueba si el servidor responde (endpoint de salud).
  /// Devuelve true si el servidor está accesible y sano.
  Future<bool> comprobarSalud() async {
    try {
      final resp = await _api.get('/api/health');
      return resp != null && resp.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  // ─────────────────────────────────────────────
  // REENTRENAMIENTO Y ESTADO
  // ─────────────────────────────────────────────

  Future<bool> reentrenarConSorteo(ResultadoSorteo sorteo) async {
    final resp = await _api.post(
      '/api/modelos/reentrenar',
      data: {
        'fecha': sorteo.fecha.toIso8601String(),
        'numeros': sorteo.numeros,
        'complementario': sorteo.complementario,
        'reintegro': sorteo.reintegro,
        'bote': sorteo.bote,
      },
    );
    return resp != null && resp.statusCode == 200;
  }

  Future<List<RendimientoAlgoritmo>> obtenerRendimientoAlgoritmos() async {
    final resp = await _api.get('/api/algoritmos/rendimiento');
    if (resp == null || resp.statusCode != 200) return const [];
    if (resp.data is! Map) return const [];
    final algos = (resp.data['algoritmos'] as List?) ?? const [];
    return algos
        .whereType<Map>()
        .map((m) =>
            RendimientoAlgoritmo.fromJson(Map<String, dynamic>.from(m)))
        .toList();
  }

  /// Frecuencias por número (1-49) del histórico. Bug #152.
  Future<List<EstadisticasNumero>> obtenerEstadisticasNumeros() async {
    final resp = await _api.get('/api/estadisticas/numeros');
    if (resp == null || resp.statusCode != 200) return const [];
    if (resp.data is! Map) return const [];
    final nums = (resp.data['numeros'] as List?) ?? const [];
    return nums
        .whereType<Map>()
        .map((m) =>
            EstadisticasNumero.fromJson(Map<String, dynamic>.from(m)))
        .toList();
  }

  // ─────────────────────────────────────────────
  // BLOQUE L
  // ─────────────────────────────────────────────

  Future<Map<String, dynamic>?> calcularROI(double boteEur) async {
    final resp = await _api.get(
      '/api/bloque-l/roi',
      queryParameters: {'bote_eur': boteEur},
    );
    if (resp == null || resp.statusCode != 200) return null;
    if (resp.data is Map) {
      return Map<String, dynamic>.from(resp.data);
    }
    return null;
  }

  Future<bool> verificarConexion() async {
    final resp = await _api.get('/api/health');
    return resp != null && resp.statusCode == 200;
  }

  // ─────────────────────────────────────────────
  // DASHBOARD DE HONESTIDAD
  // ─────────────────────────────────────────────

  Future<EstadisticasHonestidad?> obtenerEstadisticasHonestidad({
    double boteEur = 400000.0,
  }) async {
    final resp = await _api.get(
      '/api/honestidad/estadisticas',
      queryParameters: {'bote_eur': boteEur},
    );
    if (resp == null || resp.statusCode != 200) return null;
    if (resp.data is! Map) return null;
    return EstadisticasHonestidad.fromJson(
        Map<String, dynamic>.from(resp.data));
  }

  Future<bool> registrarApuesta({
    required List<int> numeros,
    double costeEur = 0.5,
    String origen = 'manual',
  }) async {
    final resp = await _api.post(
      '/api/honestidad/apuesta',
      data: {
        'numeros': numeros,
        'coste_eur': costeEur,
        'origen': origen,
      },
    );
    return resp != null && resp.statusCode == 200;
  }

  Future<bool> registrarPrediccion({
    required String trabajoId,
    required List<int> numeros,
    required double confianza,
  }) async {
    final resp = await _api.post(
      '/api/honestidad/prediccion',
      data: {
        'trabajo_id': trabajoId,
        'numeros': numeros,
        'confianza': confianza,
      },
    );
    return resp != null && resp.statusCode == 200;
  }

  Future<Map<String, dynamic>?> evaluarSorteo({
    required String sorteoFecha,
    required List<int> numerosGanadores,
  }) async {
    final resp = await _api.post(
      '/api/honestidad/evaluar-sorteo',
      data: {
        'sorteo_fecha': sorteoFecha,
        'numeros_ganadores': numerosGanadores,
      },
    );
    if (resp == null || resp.statusCode != 200) return null;
    if (resp.data is Map) return Map<String, dynamic>.from(resp.data);
    return null;
  }
}

/// Excepción tipada para errores del backend.
class BackendError implements Exception {
  final String message;
  final int? statusCode;
  BackendError(this.message, {this.statusCode});

  @override
  String toString() => statusCode != null
      ? 'BackendError($statusCode): $message'
      : 'BackendError: $message';
}

/// Resultado completo de un cálculo: combinaciones + estrategia Bloque L.
class ResultadoCalculo {
  final List<CombinacionBonoloto> combinaciones;
  final List<String> mejorasActivas;
  final BloqueLResultado? bloqueL;
  /// Apuestas múltiples (7-11) calculadas por el servidor, o null.
  final Map<String, dynamic>? apuestasMultiples;

  const ResultadoCalculo({
    required this.combinaciones,
    this.mejorasActivas = const [],
    this.bloqueL,
    this.apuestasMultiples,
  });

  factory ResultadoCalculo.fromJson(Map<String, dynamic> json) {
    final combos = (json['combinaciones'] as List? ?? [])
        .whereType<Map>()
        .map((c) =>
            CombinacionBonoloto.fromJson(Map<String, dynamic>.from(c)))
        .toList();
    final mejoras = (json['mejoras_activas'] as List? ?? [])
        .map((e) => e.toString())
        .toList();
    BloqueLResultado? bl;
    if (json['bloque_l'] is Map) {
      bl = BloqueLResultado.fromJson(
          Map<String, dynamic>.from(json['bloque_l']));
    }
    return ResultadoCalculo(
      combinaciones: combos,
      mejorasActivas: mejoras,
      bloqueL: bl,
      apuestasMultiples: json['apuestas_multiples'] is Map
          ? Map<String, dynamic>.from(json['apuestas_multiples'])
          : null,
    );
  }
}

/// Resultado estratégico del Bloque L (la parte con valor matemático real).
class BloqueLResultado {
  final String? sistemaReducido;
  final List<Map<String, dynamic>> apuestasGarantizadas;
  final double costeTotalEur;
  final String? recomendacion;
  final Map<String, dynamic>? analisisRoi;
  final double? confianzaAgregada;
  final Map<String, dynamic>? estrategiaCompleta;

  const BloqueLResultado({
    this.sistemaReducido,
    this.apuestasGarantizadas = const [],
    this.costeTotalEur = 0.0,
    this.recomendacion,
    this.analisisRoi,
    this.confianzaAgregada,
    this.estrategiaCompleta,
  });

  factory BloqueLResultado.fromJson(Map<String, dynamic> json) =>
      BloqueLResultado(
        sistemaReducido: json['sistema_reducido']?.toString(),
        apuestasGarantizadas: (json['apuestas_garantizadas'] as List? ?? [])
            .whereType<Map>()
            .map((m) => Map<String, dynamic>.from(m))
            .toList(),
        costeTotalEur: asDouble(json['coste_total_eur']),
        recomendacion: json['recomendacion']?.toString(),
        analisisRoi: json['analisis_roi'] is Map
            ? Map<String, dynamic>.from(json['analisis_roi'])
            : null,
        confianzaAgregada: json['confianza_agregada'] != null
            ? asDouble(json['confianza_agregada'])
            : null,
        estrategiaCompleta: json['estrategia_completa'] is Map
            ? Map<String, dynamic>.from(json['estrategia_completa'])
            : null,
      );
}
