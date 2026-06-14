import 'dart:async';
import 'dart:convert';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:timezone/timezone.dart' as tz;
import 'package:timezone/data/latest_all.dart' as tzdata;

import '../models/models.dart';
import '../services/backend_service.dart';
import '../services/api_client.dart';
import '../services/services.dart'
    show ExportService, BackupService, LoteriasApiService,
        DatosDiariosService, DatosDiarios, TrackRecord, SistemasInfo;
import 'app_state.dart';

/// StateNotifier global: reemplaza al `AppProvider` (ChangeNotifier) del v7.
///
/// Cambios funcionales vs v7:
///   1. Estado inmutable: cada `state = state.copyWith(...)` notifica.
///      Imposible olvidarse de `notifyListeners()` (no existe).
///   2. `mounted` ya no es necesario: Riverpod cancela suscripciones al
///      `dispose()` del notifier automáticamente. Bug #115 imposible.
///   3. Soporte SSE en el seguimiento de progreso (en lugar del Future-based
///      `iniciarCalculo` del v7 que abusaba de callbacks).
///   4. Timezone correcto (Europe/Madrid, no UTC+1 fijo). Bug #111 corregido.
class AppNotifier extends StateNotifier<AppState> {
  ApiClient? _apiClient;
  BackendService? _backendService;

  // Servicios secundarios: por simplicidad los dejamos como instancias
  // recreadas en `inicializar()`. Si crecen, los moveremos a providers
  // individuales en sesiones futuras.
  Timer? _timerSorteo;
  StreamSubscription<ProgresoCalculo>? _streamProgreso;

  // Caché en memoria de los datos del día (combinaciones, estadísticas, etc.)
  // descargados de GitHub. Evita descargas repetidas en pocos minutos.
  DatosDiarios? _datosDiariosCache;
  DateTime? _datosDiariosCacheTime;

  /// Descarga (o reutiliza) los datos del día publicados en GitHub.
  /// Cachea 10 minutos salvo que se fuerce.
  Future<DatosDiarios?> _obtenerDatosDiarios({bool forzar = false}) async {
    final cache = _datosDiariosCache;
    final t = _datosDiariosCacheTime;
    if (!forzar &&
        cache != null &&
        t != null &&
        DateTime.now().difference(t) < const Duration(minutes: 10)) {
      return cache;
    }
    final datos = await DatosDiariosService().descargar();
    if (datos != null) {
      _datosDiariosCache = datos;
      _datosDiariosCacheTime = DateTime.now();
    }
    return datos;
  }

  AppNotifier() : super(AppState.inicial);

  // ═══════════════════════════════════════════
  // GETTERS DE COMPATIBILIDAD
  //
  // Los screens migrados desde Provider esperan acceder a los campos
  // del estado vía `provider.xxx`. Como conservamos esa API, exponemos
  // getters que delegan al state. Riverpod sigue gobernando los rebuilds
  // (los screens hacen `ref.watch(appProvider)` para suscribirse al state).
  // ═══════════════════════════════════════════

  ConfiguracionApp get config => state.config;
  Credenciales get credenciales => state.credenciales;
  SesionPrediccion? get sesionActual => state.sesionActual;
  List<SesionPrediccion> get historial => state.historial;
  List<ResultadoSorteo> get resultadosOficiales =>
      state.resultadosOficiales;
  List<EstadisticasNumero> get estadisticas => state.estadisticas;
  List<RendimientoAlgoritmo> get rendimientoAlgoritmos =>
      state.rendimientoAlgoritmos;
  bool get cargando => state.cargando;
  String? get error => state.error;
  bool get sistemaInicializado => state.sistemaInicializado;

  // ═══════════════════════════════════════════
  // INICIALIZACIÓN
  // ═══════════════════════════════════════════

  Future<void> inicializar() async {
    state = state.copyWith(cargando: true, clearError: true);
    try {
      tzdata.initializeTimeZones();

      final config = await _cargarConfiguracion();
      final credenciales = await _cargarCredenciales();
      final historial = await _cargarHistorial();

      _construirServicios(credenciales);
      _iniciarTimerSorteo();

      state = state.copyWith(
        config: config,
        credenciales: credenciales,
        historial: historial,
        cargando: false,
        sistemaInicializado: true,
      );
    } catch (e) {
      state = state.copyWith(
        cargando: false,
        error: 'Error al inicializar: $e',
      );
    }
  }

  void _construirServicios(Credenciales c) {
    if (c.oracleCloudUrl.isEmpty) {
      _apiClient = null;
      _backendService = null;
      return;
    }
    _apiClient = ApiClient(
      baseUrl: c.oracleCloudUrl,
      authToken: c.oracleCloudToken.isNotEmpty ? c.oracleCloudToken : null,
    );
    _backendService = BackendService(_apiClient!);
  }

  // ═══════════════════════════════════════════
  // PERSISTENCIA
  // ═══════════════════════════════════════════

  Future<ConfiguracionApp> _cargarConfiguracion() async {
    final prefs = await SharedPreferences.getInstance();
    final json = prefs.getString('config');
    if (json == null) return const ConfiguracionApp();
    try {
      return ConfiguracionApp.fromJson(jsonDecode(json));
    } catch (_) {
      return const ConfiguracionApp();
    }
  }

  Future<Credenciales> _cargarCredenciales() async {
    final prefs = await SharedPreferences.getInstance();
    final json = prefs.getString('credenciales');
    if (json == null) return const Credenciales();
    try {
      return Credenciales.fromJson(jsonDecode(json));
    } catch (_) {
      return const Credenciales();
    }
  }

  Future<List<SesionPrediccion>> _cargarHistorial() async {
    final prefs = await SharedPreferences.getInstance();
    final json = prefs.getString('historial');
    if (json == null) return const [];
    try {
      final lista = jsonDecode(json) as List;
      return lista
          .whereType<Map>()
          .map((m) => SesionPrediccion.fromJson(Map<String, dynamic>.from(m)))
          .toList();
    } catch (_) {
      return const [];
    }
  }

  // Tope del historial guardado en SharedPreferences. Bug #117 fix de Sesión 1.
  static const int _maxSesionesHistorial = 200;

  Future<void> _guardarHistorial() async {
    final prefs = await SharedPreferences.getInstance();
    final truncado = state.historial.length > _maxSesionesHistorial
        ? state.historial.sublist(0, _maxSesionesHistorial)
        : state.historial;
    final json = jsonEncode(truncado.map((s) => s.toJson()).toList());
    await prefs.setString('historial', json);
    if (truncado.length != state.historial.length) {
      state = state.copyWith(historial: truncado);
    }
  }

  Future<void> _guardarConfiguracion() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('config', jsonEncode(state.config.toJson()));
  }

  Future<void> _guardarCredenciales() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(
      'credenciales',
      jsonEncode(state.credenciales.toJson()),
    );
  }

  // ═══════════════════════════════════════════
  // ACCIONES PÚBLICAS
  // ═══════════════════════════════════════════

  Future<void> actualizarCredenciales(Credenciales nuevas) async {
    state = state.copyWith(credenciales: nuevas);
    _construirServicios(nuevas);
    await _guardarCredenciales();
  }

  Future<void> actualizarConfiguracion(ConfiguracionApp nueva) async {
    state = state.copyWith(config: nueva);
    await _guardarConfiguracion();
  }

  /// Alias por compatibilidad con screens que llaman actualizarConfig. Bug #145.
  Future<void> actualizarConfig(ConfiguracionApp nueva) =>
      actualizarConfiguracion(nueva);

  /// Alterna el modo oscuro/claro. Bug #144 (los screens llaman toggleTema).
  Future<void> toggleTema() async {
    final nueva = state.config.copyWith(modoOscuro: !state.config.modoOscuro);
    await actualizarConfiguracion(nueva);
  }

  /// Exporta una lista de combinaciones al formato indicado (pdf/csv/txt).
  /// Bug #146/#156: ahora delega en el ExportService real en vez de ser stub.
  Future<bool> exportarCombinaciones(
    List<CombinacionBonoloto> combinaciones,
    String formato,
  ) async {
    if (combinaciones.isEmpty) return false;
    try {
      await ExportService().exportar(combinaciones, formato);
      return true;
    } catch (e) {
      state = state.copyWith(error: 'Error exportando: $e');
      return false;
    }
  }

  /// Descarga (guarda) las combinaciones como archivo en el dispositivo, sin
  /// pasar por el menú de compartir. Devuelve la RUTA donde se guardó, o null
  /// si hubo un error o la lista estaba vacía.
  Future<String?> descargarCombinaciones(
    List<CombinacionBonoloto> combinaciones,
    String formato,
  ) async {
    if (combinaciones.isEmpty) return null;
    try {
      return await ExportService()
          .descargarEnDispositivo(combinaciones, formato);
    } catch (e) {
      state = state.copyWith(error: 'Error al descargar: $e');
      return null;
    }
  }

  /// Texto plano de las combinaciones, listo para copiar y pegar en otra app.
  String notaCombinaciones(List<CombinacionBonoloto> combinaciones) =>
      ExportService().construirNota(combinaciones);

  /// Backup manual. Bug #147 (los screens llaman realizarBackup). Alias de hacerBackup.
  Future<bool> realizarBackup() => hacerBackup();

  /// Prueba la conexión completa: comprueba que el servidor responde y que
  /// la clave de la API de loterías funciona. Devuelve un resultado legible
  /// para mostrar al usuario en la pantalla de Ajustes.
  Future<ResultadoPrueba> probarConexion() async {
    // 1. ¿Se descargan las combinaciones del día desde GitHub?
    bool servidorOk = false;
    try {
      final datos = await _obtenerDatosDiarios(forzar: true);
      servidorOk = datos != null && datos.combinaciones.isNotEmpty;
    } catch (_) {
      servidorOk = false;
    }
    if (!servidorOk) {
      return const ResultadoPrueba(
        servidorOk: false,
        apiOk: false,
        mensaje: 'No se pudieron descargar las combinaciones del día. '
            'Revisa tu conexión a internet.',
      );
    }

    // 2. La clave de la API de loterías es opcional (solo respaldo).
    bool apiOk = false;
    if (state.credenciales.loteriasApiKey.isNotEmpty) {
      try {
        apiOk = await LoteriasApiService(state.credenciales).verificarApiKey();
      } catch (_) {
        apiOk = false;
      }
    }

    final msg = StringBuffer('Combinaciones del día descargadas ✓');
    if (state.credenciales.loteriasApiKey.isEmpty) {
      msg.write('\nNo necesitas clave de API: los datos llegan solos.');
    } else if (apiOk) {
      msg.write('\nAPI de loterías conectada ✓ (respaldo)');
    } else {
      msg.write('\nAPI de loterías: la clave no responde (no es necesaria).');
    }

    return ResultadoPrueba(
      servidorOk: servidorOk,
      apiOk: apiOk,
      mensaje: msg.toString(),
    );
  }

  Future<void> activarModoIncognito(bool activo) async {
    await actualizarConfiguracion(state.config.copyWith(modoIncognito: activo));
  }

  /// "Calcula" las combinaciones del día. Ahora NO hay servidor en vivo: las
  /// combinaciones ya están generadas por la tarea automática de GitHub, así
  /// que esto las DESCARGA y rellena la sesión actual (más estadísticas y
  /// último sorteo, que vienen en el mismo fichero).
  ///
  /// Mantiene la firma anterior por compatibilidad con las pantallas.
  Future<String?> iniciarCalculo({
    required int cantidad,
    double presupuestoEur = 10.0,
    double boteAcumuladoEur = 600000.0,
  }) async {
    if (calculoBloqueado) {
      state = state.copyWith(error: mensajeBloqueo);
      return null;
    }

    // Cancelar cualquier stream previo (por si quedara alguno del flujo viejo).
    await _streamProgreso?.cancel();
    _streamProgreso = null;

    final id = DateTime.now().millisecondsSinceEpoch.toString();
    // Sesión "calculando" para que la pantalla de progreso muestre algo
    // mientras se descarga (suele ser un instante).
    final inicial = SesionPrediccion.inicial(id: id, cantidad: cantidad)
        .copyWith(estado: EstadoCalculo.calculando, progresoGeneral: 0.35);
    state = state.copyWith(sesionActual: inicial, clearError: true);

    try {
      final datos = await _obtenerDatosDiarios(forzar: true);

      if (datos == null || datos.combinaciones.isEmpty) {
        state = state.copyWith(
          sesionActual: inicial.copyWith(estado: EstadoCalculo.error),
          error: 'No se pudieron descargar las combinaciones del día. '
              'Revisa tu conexión a internet e inténtalo de nuevo.',
        );
        return null;
      }

      // Recortar a la cantidad que ha pedido el usuario.
      final combos = datos.combinaciones.length > cantidad
          ? datos.combinaciones.sublist(0, cantidad)
          : datos.combinaciones;

      final completa = inicial.copyWith(
        estado: EstadoCalculo.completado,
        progresoGeneral: 1.0,
        combinaciones: combos,
        apuestasMultiples: datos.apuestasMultiples,
        indiceConfianzaActual:
            combos.isNotEmpty ? combos.first.indiceConfianza : null,
        fechaSorteoObjetivo: datos.fechaSorteo ?? proximaFechaSorteo(),
      );

      var nuevoHistorial = state.historial;
      if (!state.config.modoIncognito) {
        final yaExiste = state.historial.any((s) => s.id == completa.id);
        if (!yaExiste) {
          nuevoHistorial = [completa, ...state.historial];
        }
      }

      state = state.copyWith(
        sesionActual: completa,
        historial: nuevoHistorial,
        estadisticas: datos.estadisticas.isNotEmpty
            ? datos.estadisticas
            : state.estadisticas,
        rendimientoAlgoritmos: datos.rendimientoAlgoritmos.isNotEmpty
            ? datos.rendimientoAlgoritmos
            : state.rendimientoAlgoritmos,
        resultadosOficiales: datos.ultimoSorteo != null
            ? [datos.ultimoSorteo!]
            : state.resultadosOficiales,
      );
      await _guardarHistorial();
      return id;
    } catch (e) {
      state = state.copyWith(
        sesionActual: inicial.copyWith(estado: EstadoCalculo.error),
        error: 'Error descargando combinaciones: $e',
      );
      return null;
    }
  }

  /// Cancela el cálculo en curso.
  Future<void> cancelarCalculo() async {
    await _streamProgreso?.cancel();
    _streamProgreso = null;
    state = state.copyWith(clearSesionActual: true);
  }

  // ═══════════════════════════════════════════
  // MÉTODOS DE DATOS
  // ═══════════════════════════════════════════

  /// Carga estadísticas (frecuencias por número) y el rendimiento aproximado
  /// por algoritmo, ambos desde el fichero diario de GitHub.
  Future<void> cargarEstadisticas() async {
    try {
      final datos = await _obtenerDatosDiarios();
      if (datos == null) return;
      state = state.copyWith(
        estadisticas: datos.estadisticas.isNotEmpty
            ? datos.estadisticas
            : state.estadisticas,
        rendimientoAlgoritmos: datos.rendimientoAlgoritmos.isNotEmpty
            ? datos.rendimientoAlgoritmos
            : state.rendimientoAlgoritmos,
        resultadosOficiales: datos.ultimoSorteo != null
            ? [datos.ultimoSorteo!]
            : state.resultadosOficiales,
      );
    } catch (e) {
      // Silencioso: si falla, dejamos las estadísticas como estaban.
    }
  }

  /// Alias por compatibilidad con screens legacy.
  Future<void> cargarRendimientoAlgoritmos() => cargarEstadisticas();

  /// Carga los KPIs del dashboard de honestidad desde el backend.
  Future<EstadisticasHonestidad?> cargarHonestidad({
    double boteEur = 400000.0,
  }) async {
    if (_backendService == null) return null;
    try {
      return await _backendService!
          .obtenerEstadisticasHonestidad(boteEur: boteEur);
    } catch (e) {
      return null;
    }
  }

  /// Registra una apuesta real en el tracker de honestidad.
  Future<bool> registrarApuesta(List<int> numeros,
      {double costeEur = 0.5, String origen = 'manual'}) async {
    if (_backendService == null) return false;
    // En modo incógnito no registramos nada
    if (state.config.modoIncognito) return false;
    try {
      return await _backendService!.registrarApuesta(
        numeros: numeros, costeEur: costeEur, origen: origen,
      );
    } catch (_) {
      return false;
    }
  }

  /// Resultado del ÚLTIMO sorteo oficial. Ahora viene en el fichero diario de
  /// GitHub (no necesita clave de API). Si por lo que fuera no estuviera, se
  /// intenta como respaldo la API de loterías (si hay clave configurada).
  Future<ResultadoSorteo?> obtenerUltimoSorteo() async {
    try {
      final datos = await _obtenerDatosDiarios();
      if (datos?.ultimoSorteo != null) {
        return datos!.ultimoSorteo;
      }
    } catch (_) {
      // seguimos al respaldo
    }
    if (state.credenciales.loteriasApiKey.isNotEmpty) {
      try {
        return await LoteriasApiService(state.credenciales)
            .obtenerUltimoResultado();
      } catch (_) {
        return null;
      }
    }
    return null;
  }

  /// Devuelve el último sorteo oficial JUNTO CON la predicción que se hizo
  /// para ese mismo sorteo (la de "ayer"), ya con sus aciertos. Si todavía no
  /// hay predicción anterior que comparar, la lista va vacía.
  /// Los 3 niveles de sistema con garantía + la tabla de probabilidades por
  /// categoría de premio. Devuelve null si aún no están en el JSON.
  Future<SistemasInfo?> obtenerSistemas() async {
    try {
      final datos = await _obtenerDatosDiarios();
      return datos?.sistemasInfo;
    } catch (_) {
      return null;
    }
  }

  /// Track record honesto: resumen de cuánto acierta la app a lo largo del
  /// tiempo (lo calcula el backend). Devuelve null si aún no hay datos.
  Future<TrackRecord?> obtenerTrackRecord() async {
    try {
      final datos = await _obtenerDatosDiarios();
      return datos?.trackRecord;
    } catch (_) {
      return null;
    }
  }

  Future<(ResultadoSorteo?, List<CombinacionBonoloto>)>
      obtenerSorteoConEvaluacion() async {
    ResultadoSorteo? sorteo;
    List<CombinacionBonoloto> evaluadas = const [];
    try {
      final datos = await _obtenerDatosDiarios();
      sorteo = datos?.ultimoSorteo;
      evaluadas = datos?.prediccionEvaluada ?? const [];
    } catch (_) {
      // seguimos al respaldo
    }
    if (sorteo == null && state.credenciales.loteriasApiKey.isNotEmpty) {
      try {
        sorteo = await LoteriasApiService(state.credenciales)
            .obtenerUltimoResultado();
      } catch (_) {
        // sin respaldo
      }
    }
    return (sorteo, evaluadas);
  }

  /// Lee los últimos N sorteos oficiales vía LoteriasApiService si hay API
  /// key configurada, y los guarda en el estado. Si no hay key o la API
  /// falla, devuelve lo que ya hubiera (sin error).
  ///
  /// Nota: la API gratuita de loterías puede no estar disponible; en ese
  /// caso esto devuelve la lista existente sin romper nada.
  Future<List<ResultadoSorteo>> obtenerUltimosSorteos({int limite = 50}) async {
    if (state.credenciales.loteriasApiKey.isEmpty) {
      return state.resultadosOficiales;
    }
    try {
      final servicio = LoteriasApiService(state.credenciales);
      final sorteos = await servicio.obtenerHistoricoSorteos(limite: limite);
      if (sorteos.isNotEmpty) {
        state = state.copyWith(resultadosOficiales: sorteos);
      }
      return state.resultadosOficiales;
    } catch (e) {
      return state.resultadosOficiales;
    }
  }

  /// Elimina una sesión del historial.
  Future<void> eliminarSesion(String id) async {
    final nuevo = state.historial.where((s) => s.id != id).toList();
    state = state.copyWith(historial: nuevo);
    await _guardarHistorial();
  }

  /// Backup a fichero compartible (JSON). Bug #147/#156: ahora usa el
  /// BackupService real en vez de devolver false siempre.
  Future<bool> hacerBackup() async {
    try {
      final servicio = BackupService(state.config);
      await servicio.realizarBackup(
        historial: state.historial,
        configuracion: state.config,
        credenciales: state.credenciales,
      );
      // Registrar fecha de último backup
      state = state.copyWith(
        config: state.config.copyWith(ultimoBackup: DateTime.now()),
      );
      await _guardarConfiguracion();
      return true;
    } catch (e) {
      state = state.copyWith(error: 'Error en backup: $e');
      return false;
    }
  }

  /// Restaurar desde backup. Stub: la restauración requiere selector de
  /// fichero (file_picker), que se añadirá cuando se integre esa dependencia.
  Future<bool> restaurarBackup() async {
    return false;
  }

  // ═══════════════════════════════════════════
  // LÓGICA DE BLOQUEO TEMPORAL
  // (con timezone Europe/Madrid — fix #111 sesión 1)
  // ═══════════════════════════════════════════

  tz.TZDateTime _ahoraEspana() {
    final madrid = tz.getLocation('Europe/Madrid');
    return tz.TZDateTime.now(madrid);
  }

  /// Fecha del próximo sorteo de Bonoloto para el que serviría una predicción.
  /// La Bonoloto se sortea TODOS los días (lunes a domingo) a las 21:30.
  /// Si ya pasó la hora de corte de hoy, apunta al sorteo de mañana.
  DateTime proximaFechaSorteo() {
    final madrid = tz.getLocation('Europe/Madrid');
    final ahora = _ahoraEspana();
    final corteHoy =
        tz.TZDateTime(madrid, ahora.year, ahora.month, ahora.day, 21, 30);
    final f = ahora.isAfter(corteHoy)
        ? ahora.add(const Duration(days: 1))
        : ahora;
    return DateTime(f.year, f.month, f.day);
  }

  bool get calculoBloqueado {
    final s = state.sesionActual;
    if (s != null &&
        (s.estado == EstadoCalculo.calculando ||
            s.estado == EstadoCalculo.convergiendo ||
            s.estado == EstadoCalculo.encolado ||
            s.estado == EstadoCalculo.iniciando)) {
      return true;
    }
    final ahora = _ahoraEspana();
    final ultimoSorteo = state.config.ultimoSorteo;
    if (ultimoSorteo == null) return false;

    final madrid = tz.getLocation('Europe/Madrid');
    final proximoSorteo = tz.TZDateTime(
      madrid, ahora.year, ahora.month, ahora.day, 21, 30,
    );

    return ahora.isBefore(proximoSorteo) &&
        ultimoSorteo.day == ahora.day &&
        ultimoSorteo.month == ahora.month &&
        ultimoSorteo.year == ahora.year;
  }

  String get mensajeBloqueo {
    final ahora = _ahoraEspana();
    final madrid = tz.getLocation('Europe/Madrid');
    var proximo = tz.TZDateTime(
      madrid, ahora.year, ahora.month, ahora.day, 21, 30,
    );
    if (proximo.isBefore(ahora)) {
      proximo = tz.TZDateTime(
        madrid, ahora.year, ahora.month, ahora.day + 1, 21, 30,
      );
    }
    final diff = proximo.difference(ahora);
    return 'Próximo sorteo en ${diff.inHours}h ${diff.inMinutes % 60}m';
  }

  // ═══════════════════════════════════════════
  // SORTEO DIARIO (timer)
  // ═══════════════════════════════════════════

  void _iniciarTimerSorteo() {
    _timerSorteo?.cancel();
    // Comprueba cada 5 min si ha pasado el sorteo del día
    _timerSorteo = Timer.periodic(const Duration(minutes: 5), (_) {
      _verificarNuevoSorteo();
    });
  }

  Future<void> _verificarNuevoSorteo() async {
    if (!state.credenciales.estaConfigurado) return;
    final ahora = _ahoraEspana();
    final madrid = tz.getLocation('Europe/Madrid');
    final horaSorteo = tz.TZDateTime(
      madrid, ahora.year, ahora.month, ahora.day, 21, 30,
    );
    if (!ahora.isAfter(horaSorteo.add(const Duration(minutes: 5)))) return;
    final ultimo = state.config.ultimoSorteo;
    if (ultimo != null &&
        ultimo.day == ahora.day &&
        ultimo.month == ahora.month) {
      return;
    }
    // En sesión 1 había `_procesarNuevoSorteo()` con varios pasos
    // (obtener último, reentrenar, notificar). Lo dejamos pendiente para
    // la sesión 4 (dashboard de honestidad), donde encaja mejor el flujo
    // de comparar predicciones vs resultado real.
  }

  @override
  void dispose() {
    _timerSorteo?.cancel();
    _streamProgreso?.cancel();
    super.dispose();
  }
}

// ═══════════════════════════════════════════
// PROVIDERS
// ═══════════════════════════════════════════

/// Provider global del estado de la app.
/// Acceso desde widgets:
///   final state = ref.watch(appProvider);
///   ref.read(appProvider.notifier).iniciarCalculo(cantidad: 5);
final appProvider = StateNotifierProvider<AppNotifier, AppState>((ref) {
  return AppNotifier();
});

/// Convenience provider: solo el estado de la sesión actual.
final sesionActualProvider = Provider<SesionPrediccion?>((ref) {
  return ref.watch(appProvider.select((s) => s.sesionActual));
});

/// Convenience provider: si está bloqueado el cálculo.
final calculoBloqueadoProvider = Provider<bool>((ref) {
  // Lectura de ahora para que reaccione a cambios de sesión
  ref.watch(appProvider);
  return ref.read(appProvider.notifier).calculoBloqueado;
});

/// Resultado de probar la conexión (servidor + API de loterías).
class ResultadoPrueba {
  final bool servidorOk;
  final bool apiOk;
  final String mensaje;

  const ResultadoPrueba({
    required this.servidorOk,
    required this.apiOk,
    required this.mensaje,
  });

  /// True si al menos el servidor responde (lo esencial).
  bool get correcto => servidorOk;
}
