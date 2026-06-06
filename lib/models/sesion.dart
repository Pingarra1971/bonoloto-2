import 'json_helpers.dart';
import 'combinacion.dart';
import 'estado.dart';

/// Una sesión de cálculo: solicitud + progreso + resultado final.
///
/// Es la unidad que se persiste en el historial.
class SesionPrediccion {
  final String id;
  final DateTime fechaSolicitud;
  final int cantidadSolicitada;
  final List<CombinacionBonoloto> combinaciones;
  final EstadoCalculo estado;
  final double progresoGeneral;
  final Map<String, EstadoAlgoritmo> estadoAlgoritmos;
  final double? indiceConfianzaActual;
  final int iteracion;
  /// Apuestas múltiples (7-11 números) calculadas por el servidor.
  /// Mapa {"7": {numeros, combinaciones, coste_eur}, ...} o null.
  final Map<String, dynamic>? apuestasMultiples;
  /// Fecha del sorteo para el que sirve esta predicción (si se quiere jugar).
  /// Se fija en el momento de calcular la predicción.
  final DateTime? fechaSorteoObjetivo;

  const SesionPrediccion({
    required this.id,
    required this.fechaSolicitud,
    required this.cantidadSolicitada,
    this.combinaciones = const [],
    this.estado = EstadoCalculo.iniciando,
    this.progresoGeneral = 0.0,
    this.estadoAlgoritmos = const {},
    this.indiceConfianzaActual,
    this.iteracion = 0,
    this.apuestasMultiples,
    this.fechaSorteoObjetivo,
  });

  /// Construye un estado inicial con los 16 algoritmos visibles pendientes.
  factory SesionPrediccion.inicial({
    required String id,
    required int cantidad,
  }) =>
      SesionPrediccion(
        id: id,
        fechaSolicitud: DateTime.now(),
        cantidadSolicitada: cantidad,
        estadoAlgoritmos: const {
          'Entropía': EstadoAlgoritmo.pendiente,
          'Hot/Cold Bias': EstadoAlgoritmo.pendiente,
          'Covarianza': EstadoAlgoritmo.pendiente,
          'LSTM': EstadoAlgoritmo.pendiente,
          'Transformer': EstadoAlgoritmo.pendiente,
          'Markov': EstadoAlgoritmo.pendiente,
          'Bayesiano': EstadoAlgoritmo.pendiente,
          'XGBoost': EstadoAlgoritmo.pendiente,
          'Reinforcement Learning': EstadoAlgoritmo.pendiente,
          'Monte Carlo': EstadoAlgoritmo.pendiente,
          'Algoritmo Genético (NSGA-II)': EstadoAlgoritmo.pendiente,
          'FFT Periodicidad': EstadoAlgoritmo.pendiente,
          'Isolation Forest': EstadoAlgoritmo.pendiente,
          'Walk-Forward': EstadoAlgoritmo.pendiente,
          'Caché Inteligente': EstadoAlgoritmo.pendiente,
          'Ensemble Stacking': EstadoAlgoritmo.pendiente,
        },
      );

  SesionPrediccion copyWith({
    String? id,
    DateTime? fechaSolicitud,
    int? cantidadSolicitada,
    List<CombinacionBonoloto>? combinaciones,
    EstadoCalculo? estado,
    double? progresoGeneral,
    Map<String, EstadoAlgoritmo>? estadoAlgoritmos,
    double? indiceConfianzaActual,
    int? iteracion,
    Map<String, dynamic>? apuestasMultiples,
    DateTime? fechaSorteoObjetivo,
  }) =>
      SesionPrediccion(
        id: id ?? this.id,
        fechaSolicitud: fechaSolicitud ?? this.fechaSolicitud,
        cantidadSolicitada: cantidadSolicitada ?? this.cantidadSolicitada,
        combinaciones: combinaciones ?? this.combinaciones,
        estado: estado ?? this.estado,
        progresoGeneral: progresoGeneral ?? this.progresoGeneral,
        estadoAlgoritmos: estadoAlgoritmos ?? this.estadoAlgoritmos,
        indiceConfianzaActual:
            indiceConfianzaActual ?? this.indiceConfianzaActual,
        iteracion: iteracion ?? this.iteracion,
        apuestasMultiples: apuestasMultiples ?? this.apuestasMultiples,
        fechaSorteoObjetivo: fechaSorteoObjetivo ?? this.fechaSorteoObjetivo,
      );

  /// Actualiza esta sesión con un snapshot de progreso (manteniendo
  /// los datos invariantes como id, fecha, cantidad, combinaciones).
  SesionPrediccion conProgreso(ProgresoCalculo p) => copyWith(
        estado: p.estado,
        progresoGeneral: p.progresoGeneral,
        estadoAlgoritmos: p.estadoAlgoritmos.isEmpty
            ? estadoAlgoritmos
            : p.estadoAlgoritmos,
        indiceConfianzaActual: p.indiceConfianza,
        iteracion: p.iteracion,
      );

  /// Precio de las combinaciones generadas.
  /// Cada apuesta simple de 6 números cuesta 0,50 € en Bonoloto.
  static const double precioCombinacionEur = 0.50;
  double get costeTotalEur => combinaciones.length * precioCombinacionEur;

  /// Fecha del sorteo objetivo formateada ("sábado 7 de junio de 2026"),
  /// o null si la predicción no tiene fecha de sorteo asociada.
  String? get fechaSorteoTexto {
    final f = fechaSorteoObjetivo;
    if (f == null) return null;
    const dias = [
      'lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo'
    ];
    const meses = [
      'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
      'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'
    ];
    return '${dias[f.weekday - 1]} ${f.day} de '
        '${meses[f.month - 1]} de ${f.year}';
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'fechaSolicitud': fechaSolicitud.toIso8601String(),
        'cantidadSolicitada': cantidadSolicitada,
        'combinaciones': combinaciones.map((c) => c.toJson()).toList(),
        'estado': estado.name,
        'progresoGeneral': progresoGeneral,
        'indiceConfianzaActual': indiceConfianzaActual,
        'iteracion': iteracion,
        'apuestasMultiples': apuestasMultiples,
        'fechaSorteoObjetivo': fechaSorteoObjetivo?.toIso8601String(),
      };

  factory SesionPrediccion.fromJson(Map<String, dynamic> json) =>
      SesionPrediccion(
        id: asString(json['id']),
        fechaSolicitud:
            asDateTime(json['fechaSolicitud']) ?? DateTime.now(),
        cantidadSolicitada: asInt(json['cantidadSolicitada']),
        combinaciones: (json['combinaciones'] as List? ?? [])
            .whereType<Map>()
            .map((c) => CombinacionBonoloto.fromJson(
                Map<String, dynamic>.from(c)))
            .toList(),
        estado: parseEstadoCalculo(json['estado']),
        progresoGeneral: asDouble(json['progresoGeneral']),
        indiceConfianzaActual: json['indiceConfianzaActual'] != null
            ? asDouble(json['indiceConfianzaActual'])
            : null,
        iteracion: asInt(json['iteracion']),
        apuestasMultiples: json['apuestasMultiples'] is Map
            ? Map<String, dynamic>.from(json['apuestasMultiples'])
            : null,
        fechaSorteoObjetivo: asDateTime(json['fechaSorteoObjetivo']),
      );
}

/// Configuración general de la app (modo oscuro, defaults, etc.).
class ConfiguracionApp {
  final bool modoOscuro;
  final int cantidadCombinacionesDefecto;
  final DateTime? ultimoBackup;
  final DateTime? ultimoSorteo;
  final bool notificacionesActivas;
  final bool telegramActivo;
  /// Modo incógnito: si está activo, los cálculos no se persisten en historial
  /// ni se reflejan en el tracker de honestidad (Sesión 4).
  final bool modoIncognito;

  const ConfiguracionApp({
    this.modoOscuro = true,
    this.cantidadCombinacionesDefecto = 5,
    this.ultimoBackup,
    this.ultimoSorteo,
    this.notificacionesActivas = true,
    this.telegramActivo = true,
    this.modoIncognito = false,
  });

  ConfiguracionApp copyWith({
    bool? modoOscuro,
    int? cantidadCombinacionesDefecto,
    DateTime? ultimoBackup,
    DateTime? ultimoSorteo,
    bool? notificacionesActivas,
    bool? telegramActivo,
    bool? modoIncognito,
  }) =>
      ConfiguracionApp(
        modoOscuro: modoOscuro ?? this.modoOscuro,
        cantidadCombinacionesDefecto:
            cantidadCombinacionesDefecto ?? this.cantidadCombinacionesDefecto,
        ultimoBackup: ultimoBackup ?? this.ultimoBackup,
        ultimoSorteo: ultimoSorteo ?? this.ultimoSorteo,
        notificacionesActivas:
            notificacionesActivas ?? this.notificacionesActivas,
        telegramActivo: telegramActivo ?? this.telegramActivo,
        modoIncognito: modoIncognito ?? this.modoIncognito,
      );

  Map<String, dynamic> toJson() => {
        'modoOscuro': modoOscuro,
        'cantidadCombinacionesDefecto': cantidadCombinacionesDefecto,
        'ultimoBackup': ultimoBackup?.toIso8601String(),
        'ultimoSorteo': ultimoSorteo?.toIso8601String(),
        'notificacionesActivas': notificacionesActivas,
        'telegramActivo': telegramActivo,
        'modoIncognito': modoIncognito,
      };

  factory ConfiguracionApp.fromJson(Map<String, dynamic> json) =>
      ConfiguracionApp(
        modoOscuro: asBool(json['modoOscuro'], true),
        cantidadCombinacionesDefecto:
            asInt(json['cantidadCombinacionesDefecto'], 5),
        ultimoBackup: asDateTime(json['ultimoBackup']),
        ultimoSorteo: asDateTime(json['ultimoSorteo']),
        notificacionesActivas: asBool(json['notificacionesActivas'], true),
        telegramActivo: asBool(json['telegramActivo'], true),
        modoIncognito: asBool(json['modoIncognito'], false),
      );
}
