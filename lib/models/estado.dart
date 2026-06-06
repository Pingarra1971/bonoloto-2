import 'json_helpers.dart';

/// Estado global del cálculo en curso.
enum EstadoCalculo {
  iniciando,
  encolado,    // nuevo en sesión 2: el trabajo está en la cola del WorkerPool
  calculando,
  convergiendo,
  completado,
  error,
  bloqueado,
}

/// Estado de un algoritmo concreto dentro del panel de progreso.
enum EstadoAlgoritmo {
  pendiente,
  procesando,
  completado,
  error,
}

/// Convierte una cadena del backend a EstadoCalculo (defensa frente a
/// estados desconocidos: caemos a `completado` para no bloquear la UI).
EstadoCalculo parseEstadoCalculo(dynamic raw) {
  final s = asString(raw).toLowerCase();
  switch (s) {
    case 'iniciando':
      return EstadoCalculo.iniciando;
    case 'encolado':
      return EstadoCalculo.encolado;
    case 'calculando':
      return EstadoCalculo.calculando;
    case 'convergiendo':
      return EstadoCalculo.convergiendo;
    case 'completado':
      return EstadoCalculo.completado;
    case 'error':
      return EstadoCalculo.error;
    case 'bloqueado':
      return EstadoCalculo.bloqueado;
    default:
      return EstadoCalculo.completado;
  }
}

EstadoAlgoritmo parseEstadoAlgoritmo(dynamic raw) {
  final s = asString(raw).toLowerCase();
  switch (s) {
    case 'pendiente':
      return EstadoAlgoritmo.pendiente;
    case 'procesando':
      return EstadoAlgoritmo.procesando;
    case 'completado':
      return EstadoAlgoritmo.completado;
    case 'error':
      return EstadoAlgoritmo.error;
    default:
      return EstadoAlgoritmo.pendiente;
  }
}

/// Snapshot del progreso de un cálculo en curso.
/// Tipo de evento que llega por SSE o se construye desde el polling.
class ProgresoCalculo {
  final EstadoCalculo estado;
  final double progresoGeneral; // 0.0 - 1.0
  final double indiceConfianza; // 0.0 - 100.0
  final int iteracion;
  final bool convergiendo;
  final Map<String, EstadoAlgoritmo> estadoAlgoritmos;
  final String mensaje;

  const ProgresoCalculo({
    required this.estado,
    required this.progresoGeneral,
    required this.indiceConfianza,
    required this.iteracion,
    required this.convergiendo,
    required this.estadoAlgoritmos,
    this.mensaje = '',
  });

  /// True si el trabajo ya no avanza (completado o error).
  bool get terminado =>
      estado == EstadoCalculo.completado || estado == EstadoCalculo.error;

  /// Construye un ProgresoCalculo "vacío" para el inicio del cálculo.
  static const ProgresoCalculo vacio = ProgresoCalculo(
    estado: EstadoCalculo.iniciando,
    progresoGeneral: 0.0,
    indiceConfianza: 0.0,
    iteracion: 0,
    convergiendo: false,
    estadoAlgoritmos: {},
    mensaje: '',
  );

  factory ProgresoCalculo.fromJson(Map<String, dynamic> json) {
    final algos = <String, EstadoAlgoritmo>{};
    final rawAlgos = json['estadoAlgoritmos'] ?? json['algoritmos_estado'];
    if (rawAlgos is Map) {
      rawAlgos.forEach((k, v) {
        algos[k.toString()] = parseEstadoAlgoritmo(v);
      });
    }
    return ProgresoCalculo(
      estado: parseEstadoCalculo(json['estado']),
      progresoGeneral: asDouble(
          json['progresoGeneral'] ?? json['progreso']),
      indiceConfianza: asDouble(
          json['indiceConfianza'] ?? json['confianza_actual']),
      iteracion: asInt(
          json['iteracion'] ?? json['iteracion_actual']),
      convergiendo: asBool(json['convergiendo']),
      estadoAlgoritmos: algos,
      mensaje: asString(json['mensaje']),
    );
  }
}
