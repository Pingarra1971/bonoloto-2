import '../models/models.dart';

/// Estado global de la app, inmutable.
///
/// Reemplaza los campos mutables del `AppProvider` (ChangeNotifier) por una
/// estructura inmutable que se reemplaza atómicamente. Esto:
///   - Elimina race conditions en updates parciales
///   - Hace que `==` sea coherente (necesario para rebuilds eficientes en Riverpod)
///   - Facilita debugging (puedes loguear el state como string)
class AppState {
  final ConfiguracionApp config;
  final Credenciales credenciales;
  final SesionPrediccion? sesionActual;
  final List<SesionPrediccion> historial;
  final List<ResultadoSorteo> resultadosOficiales;
  final List<EstadisticasNumero> estadisticas;
  final List<RendimientoAlgoritmo> rendimientoAlgoritmos;
  final bool cargando;
  final String? error;
  final bool sistemaInicializado;

  const AppState({
    this.config = const ConfiguracionApp(),
    this.credenciales = const Credenciales(),
    this.sesionActual,
    this.historial = const [],
    this.resultadosOficiales = const [],
    this.estadisticas = const [],
    this.rendimientoAlgoritmos = const [],
    this.cargando = false,
    this.error,
    this.sistemaInicializado = false,
  });

  /// Estado inicial: nada cargado, configuración por defecto.
  static const AppState inicial = AppState();

  AppState copyWith({
    ConfiguracionApp? config,
    Credenciales? credenciales,
    SesionPrediccion? sesionActual,
    bool clearSesionActual = false,
    List<SesionPrediccion>? historial,
    List<ResultadoSorteo>? resultadosOficiales,
    List<EstadisticasNumero>? estadisticas,
    List<RendimientoAlgoritmo>? rendimientoAlgoritmos,
    bool? cargando,
    String? error,
    bool clearError = false,
    bool? sistemaInicializado,
  }) =>
      AppState(
        config: config ?? this.config,
        credenciales: credenciales ?? this.credenciales,
        sesionActual: clearSesionActual ? null : (sesionActual ?? this.sesionActual),
        historial: historial ?? this.historial,
        resultadosOficiales: resultadosOficiales ?? this.resultadosOficiales,
        estadisticas: estadisticas ?? this.estadisticas,
        rendimientoAlgoritmos:
            rendimientoAlgoritmos ?? this.rendimientoAlgoritmos,
        cargando: cargando ?? this.cargando,
        error: clearError ? null : (error ?? this.error),
        sistemaInicializado: sistemaInicializado ?? this.sistemaInicializado,
      );
}
