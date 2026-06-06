"""
Matemática honesta de la Bonoloto.

Este módulo calcula las probabilidades y valores esperados REALES de la
Bonoloto. No hay "mejora" posible sobre estos números: son propiedades
del sorteo, no del sistema de predicción.

Fórmulas verificables:
  - Combinaciones totales: C(49,6) = 13.983.816
  - P(6 aciertos) = 1 / C(49,6)
  - P(k aciertos) = [C(6,k) * C(43,6-k)] / C(49,6)  (sin complementario)

Premios: la Bonoloto reparte por categorías. Los importes son variables
(dependen de recaudación y ganadores), pero hay valores medios históricos
que usamos como referencia. El usuario puede sobrescribirlos.

NOTA IMPORTANTE: El propósito de este módulo es mostrar la VERDAD al
usuario, no optimizar nada. El EV de la Bonoloto es estructuralmente
negativo (~-45% sin bote). Ningún algoritmo lo cambia.
"""

import math
from dataclasses import dataclass
from typing import Dict, List, Optional


def combinaciones(n: int, k: int) -> int:
    """C(n, k) — coeficiente binomial."""
    if k < 0 or k > n:
        return 0
    return math.comb(n, k)


# Constante fundamental
TOTAL_COMBINACIONES = combinaciones(49, 6)  # 13.983.816
PRECIO_APUESTA_EUR = 0.50  # precio de una apuesta simple de Bonoloto


def probabilidad_aciertos(k: int) -> float:
    """
    Probabilidad de acertar exactamente k números (de 6) en una apuesta simple.

    P(k) = C(6,k) * C(43, 6-k) / C(49,6)

    Esto NO incluye el complementario (que en Bonoloto sube la categoría
    de 5 a "5+C"). Para el cálculo de EV usamos las categorías principales.
    """
    if k < 0 or k > 6:
        return 0.0
    favorables = combinaciones(6, k) * combinaciones(43, 6 - k)
    return favorables / TOTAL_COMBINACIONES


# Probabilidades exactas (calculadas una vez)
P_ACIERTOS = {k: probabilidad_aciertos(k) for k in range(7)}


@dataclass
class TablaPremios:
    """
    Premios medios por categoría (€). Valores por defecto calibrados para
    aproximar el RTP real de Bonoloto (~55%), basados en históricos típicos.
    El usuario puede sobrescribirlos.

    Categorías de Bonoloto:
      6 → primera (bote, muy variable)
      5+C → segunda (5 aciertos + complementario)
      5 → tercera
      4 → cuarta
      3 → quinta (premio fijo pequeño)
      reintegro → devuelve la apuesta (prob 1/10)
      <3 → sin premio

    Nota: estos importes producen un RTP aproximado. El RTP oficial de
    Bonoloto es ~55% incluyendo reintegro y la categoría 5+C. Como
    simplificación modelamos las categorías principales y el reintegro.
    """
    premio_6: float = 400_000.0   # variable según bote
    premio_5c: float = 50_000.0   # 5 + complementario (2ª categoría)
    premio_5: float = 1_500.0
    premio_4: float = 30.0
    premio_3: float = 4.0
    # Reintegro: devuelve la apuesta (0.50€) con prob 1/10
    incluye_reintegro: bool = True

    def premio_para(self, k: int, mas_complementario: bool = False) -> float:
        """
        Premio para k aciertos. Si k==5 y mas_complementario, aplica la
        2ª categoría (5+C), que en Bonoloto paga bastante más que un 5 simple.
        """
        if k == 5 and mas_complementario:
            return self.premio_5c
        return {
            6: self.premio_6,
            5: self.premio_5,
            4: self.premio_4,
            3: self.premio_3,
        }.get(k, 0.0)


@dataclass
class AnalisisEV:
    """Resultado del análisis de valor esperado."""
    ev_por_apuesta_eur: float        # valor esperado neto de UNA apuesta
    ev_porcentaje: float              # EV / precio (ej. -0.45 = -45%)
    coste_apuesta_eur: float
    retorno_esperado_eur: float       # parte positiva (premios esperados)
    perdida_esperada_eur: float       # |ev| si es negativo
    desglose_por_categoria: Dict[int, float]  # contribución de cada k al retorno
    es_favorable: bool                # True solo si EV > 0 (raro, bote enorme)


def analizar_ev(tabla: TablaPremios) -> AnalisisEV:
    """
    Calcula el valor esperado de UNA apuesta simple dada la tabla de premios.

    EV = Σ P(k) * premio(k) + P(reintegro)*precio - precio_apuesta

    Si EV < 0 (lo normal), el jugador pierde en expectativa.
    Si EV > 0 (solo con botes muy grandes), es "favorable" en teoría,
    pero la varianza sigue siendo brutal: la probabilidad de tocar el 6
    es 1 en 14 millones.
    """
    retorno = 0.0
    desglose: Dict[int, float] = {}
    for k in range(3, 7):  # solo categorías premiadas (3,4,5,6)
        contrib = P_ACIERTOS[k] * tabla.premio_para(k)
        desglose[k] = contrib
        retorno += contrib

    # Reintegro: con prob 1/10 se devuelve el importe de la apuesta.
    if tabla.incluye_reintegro:
        contrib_reintegro = 0.1 * PRECIO_APUESTA_EUR
        desglose[-1] = contrib_reintegro  # clave -1 = reintegro
        retorno += contrib_reintegro

    ev = retorno - PRECIO_APUESTA_EUR
    return AnalisisEV(
        ev_por_apuesta_eur=ev,
        ev_porcentaje=ev / PRECIO_APUESTA_EUR,
        coste_apuesta_eur=PRECIO_APUESTA_EUR,
        retorno_esperado_eur=retorno,
        perdida_esperada_eur=max(0.0, -ev),
        desglose_por_categoria=desglose,
        es_favorable=ev > 0,
    )


def ev_con_bote(bote_eur: float) -> AnalisisEV:
    """
    EV ajustado al bote acumulado actual. El bote infla `premio_6`.

    OJO: incluso con bote grande, el EV rara vez supera 0 porque la
    probabilidad de acertar 6 es minúscula. Y aunque fuera +EV, habría
    que compartir el bote con otros acertantes, lo que reduce el premio
    efectivo. Este cálculo es OPTIMISTA (asume ganador único).
    """
    tabla = TablaPremios(premio_6=bote_eur)
    return analizar_ev(tabla)


# ─────────────────────────────────────────────
# BACKTEST DEL SISTEMA
# ─────────────────────────────────────────────


# Aciertos esperados por boleto si se juega AL AZAR:
# E[aciertos] = 6 * (6/49) = 36/49 ≈ 0.7347 por boleto de 6 números
# (cada número del boleto tiene prob 6/49 de estar entre los 6 ganadores)
ACIERTOS_ESPERADOS_POR_BOLETO_AZAR = 6 * (6 / 49)  # ≈ 0.7347

# Probabilidad de que un boleto concreto acierte >= 3 (premio):
PROB_PREMIO_POR_BOLETO = sum(P_ACIERTOS[k] for k in range(3, 7))  # ≈ 0.0186


@dataclass
class ResultadoBacktest:
    """
    Compara el rendimiento real del sistema vs el azar.

    La hipótesis nula (H0) es: "el sistema no es mejor que el azar".
    Si tras muchos sorteos la tasa de aciertos del sistema NO supera
    significativamente la del azar, H0 no se rechaza — es decir, el
    sistema no aporta poder predictivo (que es lo matemáticamente esperado).
    """
    n_predicciones: int               # cuántas combinaciones se evaluaron
    n_sorteos_evaluados: int
    aciertos_totales_sistema: int     # suma de aciertos de todas las predicciones
    aciertos_medios_sistema: float    # por boleto
    aciertos_esperados_azar: float    # por boleto (constante teórica)
    diferencia: float                 # sistema - azar (>0 sugiere ventaja; casi siempre ~0)
    premios_conseguidos: int          # cuántas predicciones lograron >=3 aciertos
    premios_esperados_azar: float     # cuántos premios esperaríamos al azar
    veredicto: str                    # texto interpretativo honesto


def backtest_sistema(
    aciertos_por_prediccion: List[int],
    n_sorteos: int,
) -> ResultadoBacktest:
    """
    Evalúa el rendimiento del sistema.

    Args:
        aciertos_por_prediccion: lista con los aciertos (0-6) de cada
            combinación que el sistema generó ANTES de un sorteo y que
            luego se comparó con el resultado real.
        n_sorteos: número de sorteos distintos cubiertos.

    Returns:
        ResultadoBacktest con la comparación honesta.
    """
    n = len(aciertos_por_prediccion)
    if n == 0:
        return ResultadoBacktest(
            n_predicciones=0, n_sorteos_evaluados=0,
            aciertos_totales_sistema=0, aciertos_medios_sistema=0.0,
            aciertos_esperados_azar=ACIERTOS_ESPERADOS_POR_BOLETO_AZAR,
            diferencia=0.0, premios_conseguidos=0, premios_esperados_azar=0.0,
            veredicto="Sin datos todavía. Registra predicciones y resultados "
                      "para ver si el sistema supera al azar.",
        )

    total = sum(aciertos_por_prediccion)
    medios = total / n
    premios = sum(1 for a in aciertos_por_prediccion if a >= 3)
    premios_esperados = n * PROB_PREMIO_POR_BOLETO
    diff = medios - ACIERTOS_ESPERADOS_POR_BOLETO_AZAR

    # Veredicto honesto basado en el tamaño de muestra y la diferencia
    if n < 30:
        veredicto = (
            f"Muestra pequeña ({n} predicciones). Aún no se pueden sacar "
            f"conclusiones estadísticas. Necesitas ~100+ para que el ruido "
            f"se promedie."
        )
    elif abs(diff) < 0.05:
        veredicto = (
            f"El sistema acierta {medios:.3f} números/boleto frente a "
            f"{ACIERTOS_ESPERADOS_POR_BOLETO_AZAR:.3f} esperados al azar. "
            f"La diferencia ({diff:+.3f}) es indistinguible de cero: el "
            f"sistema NO supera al azar, como predice la matemática."
        )
    elif diff > 0:
        veredicto = (
            f"El sistema acierta {medios:.3f} números/boleto vs "
            f"{ACIERTOS_ESPERADOS_POR_BOLETO_AZAR:.3f} al azar (+{diff:.3f}). "
            f"Con {n} predicciones esto PODRÍA ser ruido afortunado. "
            f"Mantén el registro: con más datos la diferencia tenderá a cero."
        )
    else:
        veredicto = (
            f"El sistema acierta {medios:.3f} números/boleto vs "
            f"{ACIERTOS_ESPERADOS_POR_BOLETO_AZAR:.3f} al azar ({diff:.3f}). "
            f"Está por debajo del azar — también es ruido esperable."
        )

    return ResultadoBacktest(
        n_predicciones=n,
        n_sorteos_evaluados=n_sorteos,
        aciertos_totales_sistema=total,
        aciertos_medios_sistema=medios,
        aciertos_esperados_azar=ACIERTOS_ESPERADOS_POR_BOLETO_AZAR,
        diferencia=diff,
        premios_conseguidos=premios,
        premios_esperados_azar=premios_esperados,
        veredicto=veredicto,
    )


# ─────────────────────────────────────────────
# COSTE DE OPORTUNIDAD
# ─────────────────────────────────────────────


def coste_oportunidad(
    total_apostado_eur: float,
    meses: float,
    rendimiento_anual_alternativo: float = 0.07,  # 7% ≈ MSCI World histórico
) -> Dict[str, float]:
    """
    Calcula cuánto habría valido el dinero apostado si se hubiera invertido
    en un índice diversificado (referencia: MSCI World ~7% anual histórico).

    NO es consejo financiero — es solo un dato de contexto. El usuario decide.
    """
    if meses <= 0 or total_apostado_eur <= 0:
        return {
            "valor_si_invertido_eur": total_apostado_eur,
            "ganancia_alternativa_eur": 0.0,
            "rendimiento_usado": rendimiento_anual_alternativo,
        }
    anios = meses / 12.0
    # Interés compuesto sobre el total (simplificación: asume aportación única)
    valor_futuro = total_apostado_eur * ((1 + rendimiento_anual_alternativo) ** anios)
    return {
        "valor_si_invertido_eur": valor_futuro,
        "ganancia_alternativa_eur": valor_futuro - total_apostado_eur,
        "rendimiento_usado": rendimiento_anual_alternativo,
    }
