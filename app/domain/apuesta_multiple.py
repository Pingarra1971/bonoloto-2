"""
Apuestas múltiples de Bonoloto.

Una apuesta múltiple consiste en marcar MÁS de 6 números en un mismo boleto.
Equivale a jugar todas las combinaciones simples de 6 que se pueden formar
con esos números: C(K, 6). El coste es ese número de combinaciones por el
precio del boleto simple.

Valores OFICIALES de Bonoloto (precio por combinación simple = 0,50 €):

    Números | Combinaciones C(K,6) | Coste
    --------+----------------------+---------
       6    |          1           |   0,50 €
       7    |          7           |   3,50 €
       8    |         28           |  14,00 €
       9    |         84           |  42,00 €
      10    |        210           | 105,00 €
      11    |        462           | 231,00 €

IMPORTANTE (honestidad): una apuesta múltiple NO mejora la probabilidad por
euro gastado. Solo cubre más combinaciones a la vez pagando proporcionalmente
más. No aporta ninguna ventaja matemática frente a jugar esas mismas
combinaciones por separado.
"""

from math import comb
from typing import Dict, List

PRECIO_COMBINACION_EUR = 0.50

# Tamaños de apuesta múltiple permitidos en Bonoloto.
MIN_NUMEROS = 7
MAX_NUMEROS = 11


def combinaciones_de(k: int) -> int:
    """Número de combinaciones simples que cubre una apuesta de K números."""
    return comb(k, 6)


def coste_de(k: int) -> float:
    """Coste en euros de una apuesta múltiple de K números."""
    return round(combinaciones_de(k) * PRECIO_COMBINACION_EUR, 2)


def calcular_apuestas_multiples(
    scores_finales: Dict[int, float],
    minimo: int = MIN_NUMEROS,
    maximo: int = MAX_NUMEROS,
) -> Dict[str, dict]:
    """
    Construye TODAS las apuestas múltiples posibles (de `minimo` a `maximo`
    números) a partir de las puntuaciones finales por número del modelo.

    Para cada tamaño K se eligen los K números mejor puntuados. Como se toman
    prefijos de la misma lista ordenada, las apuestas están anidadas
    (la de 7 ⊂ la de 8 ⊂ ... ⊂ la de 11): al subir de tamaño solo se añade
    el siguiente mejor número.

    Devuelve un dict con clave el tamaño (como str, para JSON) y valor:
        {"numeros": [...], "combinaciones": int, "coste_eur": float}
    """
    if not scores_finales:
        return {}

    # Números ordenados por puntuación descendente (desempate por número asc).
    ordenados = sorted(
        scores_finales.items(),
        key=lambda kv: (-kv[1], kv[0]),
    )
    top: List[int] = [n for n, _ in ordenados]

    resultado: Dict[str, dict] = {}
    for k in range(minimo, maximo + 1):
        if len(top) < k:
            break
        numeros = sorted(top[:k])
        n_comb = combinaciones_de(k)
        resultado[str(k)] = {
            "numeros": numeros,
            "combinaciones": n_comb,
            "coste_eur": round(n_comb * PRECIO_COMBINACION_EUR, 2),
        }
    return resultado
