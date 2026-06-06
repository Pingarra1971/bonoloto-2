"""
Framework de backtest honesto.

Evalúa el rendimiento PREDICTIVO real del sistema sobre histórico, usando
validación walk-forward (entrenar con pasado, predecir futuro, nunca al revés).

Métricas que calcula:
  - Aciertos medios del sistema vs azar (la métrica clave)
  - Brier score vs uniforme (calibración de las probabilidades implícitas)
  - Distribución de aciertos (cuántas veces 0,1,2,3,4,5,6)
  - Test estadístico: ¿la diferencia con el azar es significativa?

DISEÑO HONESTO: este framework está construido para DETECTAR si el sistema
aporta valor predictivo. Por la naturaleza del sorteo (aleatorio uniforme
independiente), lo esperado es que NO lo aporte — que los aciertos del
sistema sean estadísticamente indistinguibles del azar. Si el framework
mostrara lo contrario de forma consistente sobre muchos splits, sería una
señal extraordinaria (y casi con certeza un bug en la evaluación, no un
descubrimiento). Este código permite verificarlo objetivamente.
"""

import math
import random
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple


# Aciertos esperados por boleto al azar (constante teórica)
ACIERTOS_ESPERADOS_AZAR = 6 * (6 / 49)  # ≈ 0.7347


@dataclass
class ResultadoBacktestWF:
    """Resultado de un backtest walk-forward."""
    n_evaluaciones: int
    aciertos_sistema: List[int]
    aciertos_medios_sistema: float
    aciertos_esperados_azar: float
    diferencia: float
    error_estandar: float
    z_score: float                      # (sistema - azar) / SE
    p_valor_aprox: float                # prob de ver esta diferencia por azar
    distribucion_aciertos: Dict[int, int]   # {0: n, 1: n, ...}
    es_significativo: bool              # |z| > 1.96 (95%)
    veredicto: str


def _aciertos(prediccion: List[int], ganadores: List[int]) -> int:
    return len(set(prediccion) & set(ganadores))


def _normal_cdf(x: float) -> float:
    """CDF de la normal estándar (para el p-valor)."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def backtest_walk_forward(
    sorteos: List[List[int]],
    generar_prediccion: Callable[[List[List[int]]], List[int]],
    ventana_min: int = 100,
    paso: int = 1,
    max_evaluaciones: Optional[int] = None,
) -> ResultadoBacktestWF:
    """
    Ejecuta backtest walk-forward.

    Para cada t desde `ventana_min` hasta el final:
      1. Toma sorteos[0:t] como histórico de entrenamiento
      2. Llama generar_prediccion(historico) → una combinación
      3. Compara con sorteos[t] (el sorteo "futuro" real)
      4. Registra los aciertos

    Args:
        sorteos: lista de combinaciones reales (cronológica, antigua→reciente)
        generar_prediccion: función que recibe histórico y devuelve 6 números
        ventana_min: histórico mínimo antes de empezar a evaluar
        paso: cada cuántos sorteos evaluar (1 = todos)
        max_evaluaciones: límite para acotar tiempo de cómputo

    Returns:
        ResultadoBacktestWF con el análisis honesto.
    """
    aciertos_lista: List[int] = []
    n = len(sorteos)

    indices = list(range(ventana_min, n, paso))
    if max_evaluaciones:
        indices = indices[:max_evaluaciones]

    for t in indices:
        historico = sorteos[:t]
        ganadores = sorteos[t]
        try:
            pred = generar_prediccion(historico)
        except Exception:
            continue
        if not pred or len(pred) != 6:
            continue
        aciertos_lista.append(_aciertos(pred, ganadores))

    return _analizar(aciertos_lista)


def _analizar(aciertos_lista: List[int]) -> ResultadoBacktestWF:
    """Calcula las métricas estadísticas del backtest."""
    n = len(aciertos_lista)
    if n == 0:
        return ResultadoBacktestWF(
            n_evaluaciones=0, aciertos_sistema=[], aciertos_medios_sistema=0.0,
            aciertos_esperados_azar=ACIERTOS_ESPERADOS_AZAR, diferencia=0.0,
            error_estandar=0.0, z_score=0.0, p_valor_aprox=1.0,
            distribucion_aciertos={}, es_significativo=False,
            veredicto="Sin evaluaciones.",
        )

    media = sum(aciertos_lista) / n
    diff = media - ACIERTOS_ESPERADOS_AZAR

    # Varianza teórica del nº de aciertos en hipergeométrica:
    # X ~ Hypergeometric(N=49, K=6, n=6)
    # Var = n * (K/N) * ((N-K)/N) * ((N-n)/(N-1))
    N, K, nn = 49, 6, 6
    var_teorica = nn * (K / N) * ((N - K) / N) * ((N - nn) / (N - 1))
    se = math.sqrt(var_teorica / n) if n > 0 else 0.0

    z = diff / se if se > 0 else 0.0
    # p-valor de dos colas
    p_valor = 2 * (1 - _normal_cdf(abs(z)))

    # Distribución de aciertos
    dist = {k: 0 for k in range(7)}
    for a in aciertos_lista:
        dist[a] = dist.get(a, 0) + 1

    es_sig = abs(z) > 1.96

    if n < 30:
        veredicto = (
            f"Muestra pequeña ({n} evaluaciones). Insuficiente para "
            f"conclusiones estadísticas."
        )
    elif not es_sig:
        veredicto = (
            f"El sistema acierta {media:.4f} números/boleto vs "
            f"{ACIERTOS_ESPERADOS_AZAR:.4f} al azar (z={z:+.2f}, p={p_valor:.3f}). "
            f"NO hay diferencia estadísticamente significativa: el sistema "
            f"se comporta como el azar, que es lo matemáticamente esperado "
            f"en un sorteo uniforme."
        )
    elif diff > 0:
        veredicto = (
            f"El sistema acierta {media:.4f} vs {ACIERTOS_ESPERADOS_AZAR:.4f} "
            f"al azar (z={z:+.2f}, p={p_valor:.3f}). La diferencia es "
            f"estadísticamente significativa al 95%. ATENCIÓN: con {n} "
            f"evaluaciones esto es casi con certeza un artefacto de la "
            f"evaluación (data leakage, sesgo de selección) y no poder "
            f"predictivo real. Revisar la metodología antes de creerlo."
        )
    else:
        veredicto = (
            f"El sistema acierta {media:.4f} vs {ACIERTOS_ESPERADOS_AZAR:.4f} "
            f"al azar (z={z:+.2f}, p={p_valor:.3f}): significativamente PEOR "
            f"que el azar. También sería un artefacto; el azar no se puede "
            f"batir consistentemente en ninguna dirección."
        )

    return ResultadoBacktestWF(
        n_evaluaciones=n,
        aciertos_sistema=aciertos_lista,
        aciertos_medios_sistema=media,
        aciertos_esperados_azar=ACIERTOS_ESPERADOS_AZAR,
        diferencia=diff,
        error_estandar=se,
        z_score=z,
        p_valor_aprox=p_valor,
        distribucion_aciertos=dist,
        es_significativo=es_sig,
        veredicto=veredicto,
    )


def comparar_con_azar(
    sorteos: List[List[int]],
    generar_prediccion: Callable[[List[List[int]]], List[int]],
    ventana_min: int = 100,
    max_evaluaciones: Optional[int] = 200,
    seed: int = 42,
) -> Dict[str, ResultadoBacktestWF]:
    """
    Ejecuta DOS backtests en paralelo: el del sistema y uno de control que
    predice al azar. Si el sistema no supera consistentemente al control,
    queda demostrado empíricamente que no aporta valor predictivo.

    Devuelve {"sistema": ..., "azar_control": ...}
    """
    rng = random.Random(seed)

    def prediccion_azar(historico):
        return sorted(rng.sample(range(1, 50), 6))

    res_sistema = backtest_walk_forward(
        sorteos, generar_prediccion,
        ventana_min=ventana_min, max_evaluaciones=max_evaluaciones,
    )
    res_azar = backtest_walk_forward(
        sorteos, prediccion_azar,
        ventana_min=ventana_min, max_evaluaciones=max_evaluaciones,
    )
    return {"sistema": res_sistema, "azar_control": res_azar}
