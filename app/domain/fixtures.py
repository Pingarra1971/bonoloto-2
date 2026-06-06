"""
Fixtures de datos para desarrollo y testing.

Estos sorteos simulados se usan cuando la BD no está disponible (modo dev)
o cuando los tests necesitan datos reproducibles.
"""

import random
from datetime import datetime
from typing import List


def sorteos_simulados(n: int = 2000, seed: int = 42) -> List[dict]:
    """
    Genera N sorteos históricos simulados con semilla determinista.

    Útil para:
      - Modo demo sin BD configurada
      - Tests reproducibles
      - Benchmarks del pipeline

    OJO: estos sorteos son completamente aleatorios. Cualquier algoritmo
    que "detecte patrón" en ellos está sobreajustando ruido. Util para
    validar que el pipeline corre, NO para validar predicciones.
    """
    rng = random.Random(seed)
    sorteos: List[dict] = []
    base_date = datetime(2000, 1, 1)
    for _ in range(n):
        nums = sorted(rng.sample(range(1, 50), 6))
        sorteos.append({
            "fecha": base_date,
            "numeros": nums,
            "complementario": rng.randint(1, 49),
            "reintegro": rng.randint(0, 9),
            "bote": rng.randint(100_000, 10_000_000),
        })
        base_date = datetime.fromtimestamp(
            base_date.timestamp() + 86400 * rng.choice([1, 2, 3])
        )
    return sorteos
