"""
Generador de diseños de cobertura (covering designs) para Bonoloto.

QUÉ HACE Y QUÉ NO HACE (honestidad estricta):

Lo que SÍ hace, con valor matemático demostrable:
  Si juegas un conjunto de K números repartidos en varias apuestas siguiendo
  un diseño de cobertura C(K, 6, t), se GARANTIZA que si t de tus K números
  salen premiados, al menos una de tus apuestas tendrá t aciertos. Esto es un
  teorema combinatorio, verificable por fuerza bruta, no una predicción.

Lo que NO hace:
  No aumenta la probabilidad de que tus K números sean los premiados. Esa
  probabilidad es exactamente la misma que jugando cualquier otro conjunto.
  La cobertura solo controla CÓMO se reparten los aciertos ENTRE tus apuestas
  una vez fijados tus números: convierte "quizás aciertos dispersos en varias
  apuestas sin premio" en "aciertos concentrados en una apuesta premiada".

Por qué tiene valor para el jugador:
  Si decides jugar N apuestas igualmente (decisión personal), un diseño de
  cobertura te garantiza un premio mínimo si aciertas t números, mientras que
  N apuestas al azar no garantizan nada. Es gestión de riesgo, no predicción.
"""

from itertools import combinations
from typing import List, Set, Tuple, Dict


def verificar_cobertura(
    apuestas: List[List[int]],
    k_numeros: int,
    t_aciertos: int,
    garantia: int,
) -> Tuple[bool, int, int]:
    """
    Verifica por fuerza bruta que un conjunto de apuestas cumple su garantía.

    Para TODO subconjunto de `t_aciertos` números (de los `k_numeros`
    seleccionados) que pudieran salir premiados, comprueba que al menos una
    apuesta logra >= `garantia` aciertos.

    Returns: (cumple, peor_caso, casos_fallidos)
    """
    numeros = list(range(1, k_numeros + 1))
    peor_caso = 6
    casos_fallidos = 0
    for ganadores in combinations(numeros, t_aciertos):
        gset = set(ganadores)
        mejor = max((len(set(ap) & gset) for ap in apuestas), default=0)
        peor_caso = min(peor_caso, mejor)
        if mejor < garantia:
            casos_fallidos += 1
    return (casos_fallidos == 0, peor_caso, casos_fallidos)


def cobertura_greedy(
    k_numeros: int,
    garantia: int = 3,
    t_aciertos: int = 4,
    max_apuestas: int = 100,
) -> List[List[int]]:
    """
    Construye un diseño de cobertura por algoritmo greedy.

    Selecciona apuestas (de 6 números de los k seleccionados) de forma que
    cada nueva apuesta cubra el máximo de subconjuntos-t aún no cubiertos.

    Esto produce coberturas cercanas al óptimo (no garantiza el mínimo
    absoluto de apuestas, que es un problema NP-difícil, pero es práctico
    y la garantía resultante se verifica por fuerza bruta).

    Args:
        k_numeros: cuántos números base seleccionas (ej. 9)
        garantia: aciertos mínimos garantizados (ej. 3)
        t_aciertos: si aciertas este nº de tus k números... (ej. 4)
        max_apuestas: tope de apuestas a generar

    Returns:
        Lista de apuestas (cada una lista de 6 índices en [1, k_numeros]).
    """
    numeros = list(range(1, k_numeros + 1))

    # Todos los subconjuntos de t_aciertos que hay que cubrir.
    # Un subconjunto S (|S|=t) está "cubierto" por una apuesta A (|A|=6) si
    # |A ∩ S| >= garantia.
    objetivos: Set[frozenset] = {
        frozenset(c) for c in combinations(numeros, t_aciertos)
    }
    # Todas las apuestas posibles (6 de k)
    apuestas_posibles = [set(c) for c in combinations(numeros, 6)]

    seleccionadas: List[List[int]] = []
    no_cubiertos = set(objetivos)

    while no_cubiertos and len(seleccionadas) < max_apuestas:
        mejor_apuesta = None
        mejor_cobertura = -1
        for ap in apuestas_posibles:
            # cuántos objetivos no cubiertos cubre esta apuesta
            cubre = 0
            for s in no_cubiertos:
                if len(ap & s) >= garantia:
                    cubre += 1
            if cubre > mejor_cobertura:
                mejor_cobertura = cubre
                mejor_apuesta = ap
        if mejor_apuesta is None or mejor_cobertura == 0:
            break
        seleccionadas.append(sorted(mejor_apuesta))
        # Actualizar no cubiertos
        no_cubiertos = {
            s for s in no_cubiertos if len(mejor_apuesta & s) < garantia
        }

    return seleccionadas


def aplicar_cobertura(
    apuestas_indices: List[List[int]],
    numeros_reales: List[int],
) -> List[List[int]]:
    """
    Mapea un diseño de cobertura (índices 1..k) a los números reales que
    el usuario eligió.

    Args:
        apuestas_indices: salida de cobertura_greedy (índices 1..k)
        numeros_reales: los k números reales del usuario (ej. [3,11,19,...])

    Returns:
        Apuestas con los números reales.
    """
    return [
        sorted(numeros_reales[i - 1] for i in apuesta)
        for apuesta in apuestas_indices
    ]


def resumen_cobertura(
    k_numeros: int,
    garantia: int,
    t_aciertos: int,
) -> Dict:
    """
    Genera un diseño y devuelve su resumen verificado, para mostrar al usuario
    cuántas apuestas necesita y qué garantía REAL obtiene.
    """
    apuestas = cobertura_greedy(k_numeros, garantia, t_aciertos)
    cumple, peor, fallidos = verificar_cobertura(
        apuestas, k_numeros, t_aciertos, garantia
    )
    coste = len(apuestas) * 0.5  # 0.50€ por apuesta simple
    return {
        "k_numeros": k_numeros,
        "n_apuestas": len(apuestas),
        "coste_eur": round(coste, 2),
        "garantia_solicitada": garantia,
        "t_aciertos": t_aciertos,
        "garantia_real_verificada": peor,
        "cumple_garantia": cumple,
        "casos_fallidos": fallidos,
        "apuestas_indices": apuestas,
        "explicacion": (
            f"Con {k_numeros} números en {len(apuestas)} apuestas "
            f"({coste:.2f}€): si {t_aciertos} de tus {k_numeros} números "
            f"salen premiados, garantizas al menos {peor} aciertos en una "
            f"apuesta. Esto NO cambia la probabilidad de que tus números "
            f"salgan — solo garantiza cómo se concentran los aciertos si salen."
        ),
    }
