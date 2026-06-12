"""
popularidad.py — Anti-popularidad: maximizar lo que COBRAS si ganas
====================================================================

La Bonoloto reparte a parimutuel: el premio de cada categoria se divide entre
los acertantes. Elegir combinaciones poco populares NO sube tu probabilidad de
ganar (es fija), pero SI reduce con cuanta gente repartirias -> tu premio
esperado por euro sube de forma real.

Este modulo:
  1. Modelo HEURISTICO de popularidad basado en sesgos documentados de los
     jugadores (cumpleanos, secuencias, patrones del boleto, copiar ganadores...).
  2. Hook de CALIBRACION EMPIRICA: si le pasas el histgrico de "numero de
     acertantes por sorteo" (la Bonoloto lo publica), ajusta los pesos por
     regresion para que el modelo deje de ser heuristico y pase a estar basado
     en datos reales de tu pais.
  3. Premio esperado relativo de una combinacion: factor >1 = cobrarias mas que
     la media; <1 = menos.

Convencion: una combinacion es una lista/conjunto de 6 enteros 1..49.
"""

from __future__ import annotations
from dataclasses import dataclass, field


# --------------------------------------------------------------------------- #
# 1. Caracteristicas de "popularidad" de una combinacion
# --------------------------------------------------------------------------- #

def features_popularidad(combo: list[int]) -> dict[str, float]:
    """
    Extrae rasgos que correlacionan con que MUCHA gente juegue esa combinacion.
    Cada rasgo en [0,1] aprox; mayor = mas popular (= peor para el reparto).
    """
    c = sorted(combo)
    n = len(c)

    # a) Sesgo de cumpleanos: numeros <= 31 (dias) y <= 12 (meses).
    prop_dias = sum(1 for x in c if x <= 31) / n
    prop_meses = sum(1 for x in c if x <= 12) / n

    # b) Numeros consecutivos (la gente juega rachas tipo 1-2-3).
    consecutivos = sum(1 for i in range(n - 1) if c[i + 1] - c[i] == 1)
    prop_consec = consecutivos / (n - 1)

    # c) Progresion aritmetica perfecta (5,10,15,20,25,30...) muy jugada.
    difs = {c[i + 1] - c[i] for i in range(n - 1)}
    es_progresion = 1.0 if len(difs) == 1 else 0.0

    # d) Multiplos / terminaciones iguales (5,10,15.. o todos acabados en 7).
    term = [x % 10 for x in c]
    max_misma_term = max(term.count(t) for t in set(term)) / n
    todos_multiplos_5 = 1.0 if all(x % 5 == 0 for x in c) else 0.0

    # e) Suma muy central (la gente evita extremos -> centro mas concurrido).
    suma = sum(c)
    # suma media de 6/49 = 150; normaliza distancia inversa.
    centralidad = max(0.0, 1.0 - abs(suma - 150) / 150)

    # f) Patron "primera columna/diagonal" del boleto: muchos numeros bajos.
    prop_bajos = sum(1 for x in c if x <= 10) / n

    return {
        "cumpleanos_dias": prop_dias,
        "cumpleanos_meses": prop_meses,
        "consecutivos": prop_consec,
        "progresion": es_progresion,
        "misma_terminacion": max_misma_term,
        "multiplos_5": todos_multiplos_5,
        "centralidad_suma": centralidad,
        "numeros_bajos": prop_bajos,
    }


# Pesos heuristicos por defecto (mayor peso = sesgo mas fuerte de los jugadores).
PESOS_HEURISTICOS = {
    "cumpleanos_dias": 1.0,
    "cumpleanos_meses": 0.6,
    "consecutivos": 0.8,
    "progresion": 1.2,
    "misma_terminacion": 0.7,
    "multiplos_5": 1.0,
    "centralidad_suma": 0.5,
    "numeros_bajos": 0.9,
}


# --------------------------------------------------------------------------- #
# 2. Indice de popularidad y premio esperado relativo
# --------------------------------------------------------------------------- #

@dataclass
class ModeloPopularidad:
    pesos: dict[str, float] = field(default_factory=lambda: dict(PESOS_HEURISTICOS))

    def indice(self, combo: list[int]) -> float:
        """Indice de popularidad en [0,1] (0 = muy impopular, ideal)."""
        f = features_popularidad(combo)
        bruto = sum(self.pesos.get(k, 0.0) * v for k, v in f.items())
        max_posible = sum(abs(w) for w in self.pesos.values()) or 1.0
        return max(0.0, min(1.0, bruto / max_posible))

    def acertantes_esperados_relativo(self, combo: list[int]) -> float:
        """
        Estimacion relativa de con cuanta gente repartirias.
        1.0 = media; >1 = mas gente (peor); <1 = menos gente (mejor).
        """
        # Una combinacion media tiene indice ~0.5; escalamos alrededor de eso.
        return 0.5 + self.indice(combo)

    def premio_esperado_relativo(self, combo: list[int]) -> float:
        """
        Factor de premio esperado por la via del reparto (NO de probabilidad).
        >1 = cobrarias mas que la media si ganas; <1 = menos.
        """
        rel = self.acertantes_esperados_relativo(combo)
        return 1.0 / rel if rel > 0 else 1.0

    def ordenar_por_premio(self, combinaciones: list[list[int]]) -> list[tuple[list[int], float]]:
        """
        Ordena candidatas (TODAS con la MISMA probabilidad de ganar) de mejor a
        peor premio esperado por reparto. Esta es la decision con efecto real.
        """
        valoradas = [(c, self.premio_esperado_relativo(c)) for c in combinaciones]
        return sorted(valoradas, key=lambda t: t[1], reverse=True)


# --------------------------------------------------------------------------- #
# 3. Calibracion empirica (opcional, con datos reales de acertantes)
# --------------------------------------------------------------------------- #

def calibrar_con_acertantes(
    historico_combos: list[list[int]],
    acertantes: list[float],
    l2: float = 1.0,
) -> ModeloPopularidad:
    """
    Ajusta los pesos por minimos cuadrados (ridge) usando el numero REAL de
    acertantes de categoria alta de cada sorteo pasado. Convierte el modelo
    heuristico en uno basado en datos de TU loteria.

    historico_combos: combinaciones ganadoras (o las mas jugadas) pasadas.
    acertantes:       nº de acertantes asociado a cada una (misma longitud).
    Devuelve un ModeloPopularidad con pesos ajustados.

    Solo usa numpy (que ya tienes en el motor).
    """
    import numpy as np

    if len(historico_combos) != len(acertantes):
        raise ValueError("historico_combos y acertantes deben tener igual longitud.")

    claves = list(PESOS_HEURISTICOS.keys())
    X = np.array([[features_popularidad(c)[k] for k in claves] for c in historico_combos])
    y = np.array(acertantes, dtype=float)
    # Normalizamos y (log para domar colas largas de acertantes).
    y = np.log1p(y)

    # Ridge: w = (X'X + l2 I)^-1 X'y
    XtX = X.T @ X + l2 * np.eye(X.shape[1])
    w = np.linalg.solve(XtX, X.T @ y)
    # Forzamos pesos no negativos (la popularidad no "resta") y normalizamos.
    w = np.maximum(w, 0.0)
    if w.sum() > 0:
        w = w / w.sum() * sum(PESOS_HEURISTICOS.values())

    return ModeloPopularidad(pesos={k: float(wi) for k, wi in zip(claves, w)})


# --------------------------------------------------------------------------- #
# 4. Demo / auto-test
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    print("=" * 70)
    print("DEMO popularidad.py — anti-popularidad / premio esperado")
    print("=" * 70)

    modelo = ModeloPopularidad()

    ejemplos = {
        "muy popular (cumpleanos)": [3, 7, 12, 19, 24, 31],
        "progresion 5-10-..-30":    [5, 10, 15, 20, 25, 30],
        "consecutivos 1-2-3-4-5-6": [1, 2, 3, 4, 5, 6],
        "impopular (altos disperso)": [13, 29, 34, 41, 44, 48],
        "muy impopular":            [27, 33, 38, 42, 46, 49],
    }

    print(f"\n{'combinacion':30s} {'popularidad':>11s} {'premio_esp':>11s}")
    for nombre, combo in ejemplos.items():
        idx = modelo.indice(combo)
        pe = modelo.premio_esperado_relativo(combo)
        print(f"  {nombre:28s} {idx:>11.3f} {pe:>11.3f}")

    print("\nOrden recomendado (mejor premio esperado primero):")
    candidatas = list(ejemplos.values())
    for combo, pe in modelo.ordenar_por_premio(candidatas):
        print(f"  premio_esp={pe:.3f}  ->  {combo}")

    print("\nRecuerda: el premio esperado NO cambia la probabilidad de ganar,")
    print("solo con cuanta gente repartirias el premio si ganas.")
