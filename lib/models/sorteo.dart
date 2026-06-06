import 'json_helpers.dart';

/// Resultado oficial de un sorteo de Bonoloto.
class ResultadoSorteo {
  final DateTime fecha;
  final List<int> numeros;
  final int complementario;
  final int reintegro;
  final int bote;

  const ResultadoSorteo({
    required this.fecha,
    required this.numeros,
    required this.complementario,
    required this.reintegro,
    required this.bote,
  });

  Map<String, dynamic> toJson() => {
        'fecha': fecha.toIso8601String(),
        'numeros': numeros,
        'complementario': complementario,
        'reintegro': reintegro,
        'bote': bote,
      };

  factory ResultadoSorteo.fromJson(Map<String, dynamic> json) {
    // La API actual (loteriasapi.com /api/v1) usa:
    //   combination: [n,n,...]  drawDate: "YYYY-MM-DD"
    //   resultData: { complementario, reintegro }  jackpot/jackpotFormatted
    // Mantenemos también los nombres antiguos por compatibilidad.
    final resultData = (json['resultData'] is Map)
        ? Map<String, dynamic>.from(json['resultData'])
        : <String, dynamic>{};

    return ResultadoSorteo(
      fecha: asDateTime(json['drawDate'] ?? json['fecha']) ?? DateTime.now(),
      numeros: asIntList(
          json['combination'] ?? json['numeros'] ?? json['combinacion']),
      complementario: asInt(
          json['complementario'] ?? resultData['complementario']),
      reintegro: asInt(
          json['reintegro'] ?? resultData['reintegro']),
      bote: asInt(json['jackpot'] ?? json['bote']),
    );
  }
}

/// Estadísticas históricas de un número del 1 al 49.
class EstadisticasNumero {
  final int numero;
  final int frecuenciaTotal;
  final int frecuenciaUltimos50;
  final int frecuenciaUltimos100;
  final int frecuenciaUltimos500;
  /// Hace cuántos sorteos apareció por última vez (0 = el más reciente).
  /// null si no ha aparecido en el histórico cargado.
  final int? ultimaAparicionHace;
  final String clasificacion; // 'caliente' | 'frio' | 'neutro'

  const EstadisticasNumero({
    required this.numero,
    required this.frecuenciaTotal,
    required this.frecuenciaUltimos50,
    required this.frecuenciaUltimos100,
    required this.frecuenciaUltimos500,
    this.ultimaAparicionHace,
    required this.clasificacion,
  });

  factory EstadisticasNumero.fromJson(Map<String, dynamic> json) =>
      EstadisticasNumero(
        numero: asInt(json['numero']),
        frecuenciaTotal: asInt(json['frecuencia_total']),
        frecuenciaUltimos50: asInt(json['frecuencia_ultimos_50']),
        frecuenciaUltimos100: asInt(json['frecuencia_ultimos_100']),
        frecuenciaUltimos500: asInt(json['frecuencia_ultimos_500']),
        ultimaAparicionHace: json['ultima_aparicion_hace'] != null
            ? asInt(json['ultima_aparicion_hace'])
            : null,
        clasificacion: asString(json['clasificacion'], 'neutro'),
      );
}

/// Rendimiento de un algoritmo individual (panel "Algoritmos").
class RendimientoAlgoritmo {
  final String nombre;
  final double pesoActual;
  final double tasaAciertosHistorica;
  final int totalPredicciones;
  final List<double> historialPesos;

  const RendimientoAlgoritmo({
    required this.nombre,
    required this.pesoActual,
    required this.tasaAciertosHistorica,
    required this.totalPredicciones,
    required this.historialPesos,
  });

  factory RendimientoAlgoritmo.fromJson(Map<String, dynamic> json) =>
      RendimientoAlgoritmo(
        nombre: asString(json['nombre']),
        pesoActual: asDouble(json['peso_actual'] ?? json['pesoActual']),
        tasaAciertosHistorica: asDouble(
            json['tasa_aciertos'] ?? json['tasaAciertosHistorica']),
        totalPredicciones: asInt(
            json['total_predicciones'] ?? json['totalPredicciones']),
        historialPesos: asDoubleList(
            json['historial_pesos'] ?? json['historialPesos']),
      );
}
