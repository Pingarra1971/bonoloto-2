import 'json_helpers.dart';

/// KPIs del dashboard de honestidad, recibidos del backend.
class EstadisticasHonestidad {
  final double totalApostadoEur;
  final double totalGanadoEur;
  final double balanceNetoEur;
  final int nApuestas;
  final int nApuestasEvaluadas;
  final double evTeoricoAcumuladoEur;
  final double diferenciaRealVsTeoricoEur;
  final int aciertosTotales;
  final double aciertosMedios;
  final double tasaPremioReal;
  final BacktestSistema backtest;
  final CosteOportunidad costeOportunidad;
  final EvApuesta evApuestaActual;

  const EstadisticasHonestidad({
    required this.totalApostadoEur,
    required this.totalGanadoEur,
    required this.balanceNetoEur,
    required this.nApuestas,
    required this.nApuestasEvaluadas,
    required this.evTeoricoAcumuladoEur,
    required this.diferenciaRealVsTeoricoEur,
    required this.aciertosTotales,
    required this.aciertosMedios,
    required this.tasaPremioReal,
    required this.backtest,
    required this.costeOportunidad,
    required this.evApuestaActual,
  });

  /// True si el balance es positivo (raro a largo plazo).
  bool get balancePositivo => balanceNetoEur > 0;

  factory EstadisticasHonestidad.fromJson(Map<String, dynamic> json) =>
      EstadisticasHonestidad(
        totalApostadoEur: asDouble(json['total_apostado_eur']),
        totalGanadoEur: asDouble(json['total_ganado_eur']),
        balanceNetoEur: asDouble(json['balance_neto_eur']),
        nApuestas: asInt(json['n_apuestas']),
        nApuestasEvaluadas: asInt(json['n_apuestas_evaluadas']),
        evTeoricoAcumuladoEur: asDouble(json['ev_teorico_acumulado_eur']),
        diferenciaRealVsTeoricoEur:
            asDouble(json['diferencia_real_vs_teorico_eur']),
        aciertosTotales: asInt(json['aciertos_totales']),
        aciertosMedios: asDouble(json['aciertos_medios']),
        tasaPremioReal: asDouble(json['tasa_premio_real']),
        backtest: BacktestSistema.fromJson(
            (json['backtest'] as Map?)?.cast<String, dynamic>() ?? {}),
        costeOportunidad: CosteOportunidad.fromJson(
            (json['coste_oportunidad'] as Map?)?.cast<String, dynamic>() ?? {}),
        evApuestaActual: EvApuesta.fromJson(
            (json['ev_apuesta_actual'] as Map?)?.cast<String, dynamic>() ?? {}),
      );

  /// Estado vacío para mostrar antes de cargar.
  static const EstadisticasHonestidad vacio = EstadisticasHonestidad(
    totalApostadoEur: 0,
    totalGanadoEur: 0,
    balanceNetoEur: 0,
    nApuestas: 0,
    nApuestasEvaluadas: 0,
    evTeoricoAcumuladoEur: 0,
    diferenciaRealVsTeoricoEur: 0,
    aciertosTotales: 0,
    aciertosMedios: 0,
    tasaPremioReal: 0,
    backtest: BacktestSistema.vacio,
    costeOportunidad: CosteOportunidad.vacio,
    evApuestaActual: EvApuesta.vacio,
  );
}

class BacktestSistema {
  final int nPredicciones;
  final int nSorteos;
  final double aciertosMediosSistema;
  final double aciertosEsperadosAzar;
  final double diferencia;
  final int premiosConseguidos;
  final double premiosEsperadosAzar;
  final String veredicto;

  const BacktestSistema({
    required this.nPredicciones,
    required this.nSorteos,
    required this.aciertosMediosSistema,
    required this.aciertosEsperadosAzar,
    required this.diferencia,
    required this.premiosConseguidos,
    required this.premiosEsperadosAzar,
    required this.veredicto,
  });

  static const BacktestSistema vacio = BacktestSistema(
    nPredicciones: 0,
    nSorteos: 0,
    aciertosMediosSistema: 0,
    aciertosEsperadosAzar: 0.7347,
    diferencia: 0,
    premiosConseguidos: 0,
    premiosEsperadosAzar: 0,
    veredicto: 'Sin datos todavía.',
  );

  factory BacktestSistema.fromJson(Map<String, dynamic> json) =>
      BacktestSistema(
        nPredicciones: asInt(json['n_predicciones']),
        nSorteos: asInt(json['n_sorteos']),
        aciertosMediosSistema: asDouble(json['aciertos_medios_sistema']),
        aciertosEsperadosAzar:
            asDouble(json['aciertos_esperados_azar'], 0.7347),
        diferencia: asDouble(json['diferencia']),
        premiosConseguidos: asInt(json['premios_conseguidos']),
        premiosEsperadosAzar: asDouble(json['premios_esperados_azar']),
        veredicto: asString(json['veredicto'], 'Sin datos.'),
      );
}

class CosteOportunidad {
  final double valorSiInvertidoEur;
  final double gananciaAlternativaEur;
  final double rendimientoUsado;
  final double meses;

  const CosteOportunidad({
    required this.valorSiInvertidoEur,
    required this.gananciaAlternativaEur,
    required this.rendimientoUsado,
    required this.meses,
  });

  static const CosteOportunidad vacio = CosteOportunidad(
    valorSiInvertidoEur: 0,
    gananciaAlternativaEur: 0,
    rendimientoUsado: 0.07,
    meses: 0,
  );

  factory CosteOportunidad.fromJson(Map<String, dynamic> json) =>
      CosteOportunidad(
        valorSiInvertidoEur: asDouble(json['valor_si_invertido_eur']),
        gananciaAlternativaEur: asDouble(json['ganancia_alternativa_eur']),
        rendimientoUsado: asDouble(json['rendimiento_usado'], 0.07),
        meses: asDouble(json['meses']),
      );
}

class EvApuesta {
  final double evEur;
  final double evPorcentaje;
  final bool esFavorable;
  final double boteUsado;

  const EvApuesta({
    required this.evEur,
    required this.evPorcentaje,
    required this.esFavorable,
    required this.boteUsado,
  });

  static const EvApuesta vacio = EvApuesta(
    evEur: 0,
    evPorcentaje: 0,
    esFavorable: false,
    boteUsado: 0,
  );

  factory EvApuesta.fromJson(Map<String, dynamic> json) => EvApuesta(
        evEur: asDouble(json['ev_eur']),
        evPorcentaje: asDouble(json['ev_porcentaje']),
        esFavorable: asBool(json['es_favorable']),
        boteUsado: asDouble(json['bote_usado']),
      );
}
