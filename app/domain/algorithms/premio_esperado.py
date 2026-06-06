"""
Optimizador del PREMIO ESPERADO mediante anti-popularidad.

HONESTIDAD ESTRICTA — esto es lo único matemáticamente real que un sistema
puede ofrecer para "ganar más", y conviene entender exactamente qué es:

En la Bonoloto los premios son a PARITY-MUTUEL: el bote de cada categoría se
reparte entre todos los acertantes. Si ganas con una combinación que mucha
gente también jugó, divides el premio entre muchos. Si ganas con una que casi
nadie jugó, te llevas una porción mayor.

Por tanto:
  - La PROBABILIDAD de ganar NO cambia (sigue siendo 1/13.983.816 para el 6).
  - El PREMIO ESPERADO *condicional a ganar* SÍ cambia: jugar combinaciones
    impopulares aumenta cuánto cobrarías si te toca.

Esto NO es predicción. No mejora tus opciones de acertar ni un ápice. Solo
optimiza el tamaño del premio en el escenario (improbable) de que aciertes.
Es la única "ventaja" matemáticamente honesta en lotería, y está documentada
en la literatura académica (Cook & Clotfelter, Simon, etc.).

LÍMITE DE HONESTIDAD: las cantidades concretas de "cuánta gente juega cada
combinación" no son públicas. Usamos heurísticas bien establecidas sobre qué
patrones sobre-juega la gente (cumpleaños, secuencias, geometrías). El efecto
es direccional y real, pero la magnitud exacta es una estimación.
"""

from typing import List, Dict, Tuple
from itertools import combinations


def popularidad_combinacion(combo: List[int]) -> float:
    """
    Estima cuán "popular" es una combinación (0 = nadie la juega, 1 = muchos).

    Basado en patrones documentados de sesgo humano:
      - Números <= 31 (fechas de calendario / cumpleaños)
      - Secuencias y progresiones aritméticas (líneas en el boleto)
      - Múltiplos y números "redondos"
      - Concentración en la parte baja del rango
    """
    nums = sorted(combo)
    score = 0.0

    # 1. Proporción de números <= 31 (cumpleaños). Máx penalización si todos.
    frac_cumple = sum(1 for n in nums if n <= 31) / len(nums)
    score += frac_cumple * 0.35

    # 2. Secuencia / progresión aritmética
    difs = [nums[i + 1] - nums[i] for i in range(len(nums) - 1)]
    if len(set(difs)) == 1:  # progresión aritmética perfecta
        score += 0.30
    else:
        # consecutivos parciales
        consecutivos = sum(1 for d in difs if d == 1)
        score += min(0.20, consecutivos * 0.05)

    # 3. Todos en la misma "mitad" del boleto (geometría)
    if all(n <= 25 for n in nums) or all(n >= 25 for n in nums):
        score += 0.15

    # 4. Múltiplos comunes (5, 7) — números "de la suerte"
    multiplos5 = sum(1 for n in nums if n % 5 == 0)
    if multiplos5 >= 4:
        score += 0.10

    # 5. Suma muy baja (típico de jugar números pequeños)
    if sum(nums) < 100:
        score += 0.10

    return min(1.0, score)


def estimar_compartidores(combo: List[int], base_jugadores: int = 1_000_000) -> float:
    """
    Estima con cuántos OTROS jugadores compartirías el premio si esta
    combinación ganara. Heurística direccional, no medición exacta.

    Una combinación de popularidad media reparte con ~base * factor jugadores.
    """
    pop = popularidad_combinacion(combo)
    # Una combinación popular puede multiplicar x5-x10 los compartidores
    factor = 0.5 + pop * 9.5  # de 0.5 (impopular) a ~10 (muy popular)
    # Probabilidad de que un jugador concreto juegue ESTA combinación exacta
    prob_combo = 1 / 13_983_816
    esperado = base_jugadores * prob_combo * factor
    return esperado


def premio_esperado_relativo(combo: List[int]) -> float:
    """
    Factor de premio esperado relativo (1.0 = combinación media).
    >1 significa que cobrarías más que la media si ganas (menos reparto).
    <1 significa que cobrarías menos (más reparto).

    NO afecta la probabilidad de ganar — solo el tamaño del premio si ganas.
    """
    compartidores = estimar_compartidores(combo)
    # Premio relativo = 1 / (1 + compartidores), normalizado a la media
    premio_combo = 1.0 / (1.0 + compartidores)
    # Media aproximada (combinación de popularidad 0.5)
    combo_medio_compartidores = estimar_compartidores([3, 17, 24, 31, 38, 45])
    premio_medio = 1.0 / (1.0 + combo_medio_compartidores)
    return premio_combo / premio_medio if premio_medio > 0 else 1.0


def optimizar_premio_esperado(
    candidatas: List[List[int]],
    top_n: int = 10,
) -> List[Tuple[List[int], float]]:
    """
    Ordena combinaciones candidatas por premio esperado (impopularidad).

    Args:
        candidatas: combinaciones a evaluar (todas con la MISMA prob de ganar)
        top_n: cuántas devolver

    Returns:
        Lista de (combinacion, factor_premio_esperado) ordenada de mayor a
        menor premio esperado relativo.
    """
    evaluadas = [
        (combo, premio_esperado_relativo(combo))
        for combo in candidatas
    ]
    evaluadas.sort(key=lambda x: x[1], reverse=True)
    return evaluadas[:top_n]


def analisis_completo(combo: List[int]) -> Dict:
    """Análisis honesto del premio esperado de una combinación."""
    pop = popularidad_combinacion(combo)
    compartidores = estimar_compartidores(combo)
    premio_rel = premio_esperado_relativo(combo)
    return {
        "combinacion": sorted(combo),
        "popularidad_estimada": round(pop, 3),
        "compartidores_estimados_si_gana": round(compartidores, 2),
        "premio_esperado_relativo": round(premio_rel, 3),
        "interpretacion": (
            f"Si esta combinación ganara, cobrarías aproximadamente "
            f"{premio_rel:.1f}x lo que cobrarías con una combinación media. "
            f"IMPORTANTE: esto no cambia tu probabilidad de ganar (idéntica a "
            f"cualquier combinación), solo el reparto del premio si aciertas."
        ),
    }
