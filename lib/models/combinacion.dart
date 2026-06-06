import 'json_helpers.dart';

/// Combinación de 6 números generada por el sistema.
///
/// Inmutable salvo `aciertos` (se rellena tras conocer el resultado del sorteo).
class CombinacionBonoloto {
  final List<int> numeros;
  final double indiceConfianza;
  final DateTime fechaGeneracion;
  final Map<String, double> pesosPorAlgoritmo;
  final int? aciertos;
  final double? icInferior;
  final double? icSuperior;
  /// Información estratégica del Bloque L si la combinación viene de él.
  /// Ej: 'anti_popular', 'sistema_reducido_8_3'.
  final String? estrategia;
  final Map<String, dynamic>? metricas;

  const CombinacionBonoloto({
    required this.numeros,
    required this.indiceConfianza,
    required this.fechaGeneracion,
    required this.pesosPorAlgoritmo,
    this.aciertos,
    this.icInferior,
    this.icSuperior,
    this.estrategia,
    this.metricas,
  });

  /// Formateado típico: "03 - 11 - 19 - 27 - 35 - 43".
  String get numerosFormateados =>
      numeros.map((n) => n.toString().padLeft(2, '0')).join(' - ');

  /// True si los 6 números son válidos (1-49, sin repetidos).
  bool get esValida =>
      numeros.length == 6 &&
      numeros.toSet().length == 6 &&
      numeros.every((n) => n >= 1 && n <= 49);

  CombinacionBonoloto copyWith({
    List<int>? numeros,
    double? indiceConfianza,
    DateTime? fechaGeneracion,
    Map<String, double>? pesosPorAlgoritmo,
    int? aciertos,
    double? icInferior,
    double? icSuperior,
    String? estrategia,
    Map<String, dynamic>? metricas,
  }) =>
      CombinacionBonoloto(
        numeros: numeros ?? this.numeros,
        indiceConfianza: indiceConfianza ?? this.indiceConfianza,
        fechaGeneracion: fechaGeneracion ?? this.fechaGeneracion,
        pesosPorAlgoritmo: pesosPorAlgoritmo ?? this.pesosPorAlgoritmo,
        aciertos: aciertos ?? this.aciertos,
        icInferior: icInferior ?? this.icInferior,
        icSuperior: icSuperior ?? this.icSuperior,
        estrategia: estrategia ?? this.estrategia,
        metricas: metricas ?? this.metricas,
      );

  Map<String, dynamic> toJson() => {
        'numeros': numeros,
        'indiceConfianza': indiceConfianza,
        'fechaGeneracion': fechaGeneracion.toIso8601String(),
        'pesosPorAlgoritmo': pesosPorAlgoritmo,
        'aciertos': aciertos,
        'icInferior': icInferior,
        'icSuperior': icSuperior,
        'estrategia': estrategia,
        'metricas': metricas,
      };

  factory CombinacionBonoloto.fromJson(Map<String, dynamic> json) =>
      CombinacionBonoloto(
        numeros: asIntList(json['numeros']),
        indiceConfianza: asDouble(json['indiceConfianza']
            ?? json['indice_confianza']),  // backend usa snake_case
        fechaGeneracion: asDateTime(
              json['fechaGeneracion'] ?? json['fecha_generacion'],
            ) ??
            DateTime.now(),
        pesosPorAlgoritmo: asStringDoubleMap(
            json['pesosPorAlgoritmo'] ?? json['pesos_por_algoritmo']),
        aciertos: json['aciertos'] != null ? asInt(json['aciertos']) : null,
        icInferior: json['icInferior'] != null
            ? asDouble(json['icInferior'])
            : (json['ic_inferior'] != null
                ? asDouble(json['ic_inferior'])
                : null),
        icSuperior: json['icSuperior'] != null
            ? asDouble(json['icSuperior'])
            : (json['ic_superior'] != null
                ? asDouble(json['ic_superior'])
                : null),
        estrategia: json['estrategia'] != null
            ? asString(json['estrategia'])
            : null,
        metricas: json['metricas'] is Map
            ? Map<String, dynamic>.from(json['metricas'])
            : null,
      );

  @override
  String toString() =>
      'CombinacionBonoloto($numerosFormateados, conf=${indiceConfianza.toStringAsFixed(1)}%)';
}
