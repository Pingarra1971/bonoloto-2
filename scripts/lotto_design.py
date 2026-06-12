"""
lotto_design.py — Wheels abreviados "t si p": diseños de loteria L(n,k,p,t)
============================================================================

Mejora sobre covering.py / la_jolla.py. Un diseno de cobertura C(v,6,t)
garantiza un acierto de t SOLO cuando salen exactamente t de tus numeros, y
para ello cubre TODOS los t-subconjuntos: gasta apuestas de mas.

Un diseno de loteria L(n,k,p,t) garantiza "un acierto de t si salen p de tus
numeros", con p >= t. Al pedir que salgan MAS numeros tuyos (p > t), hace falta
cubrir menos casos -> MUCHAS menos apuestas para la misma categoria de premio.
Es exactamente el "wheel abreviado" que usan los jugadores: p.ej. "4 si 5" en
12 numeros = te garantizan un 4 siempre que 5 de tus 12 salgan.

Semantica exacta (sobre tu pool de v numeros, k=6):
    Para CUALQUIER subconjunto P de p numeros de tu pool, existe una apuesta B
    con |B ∩ P| >= t.  -> si p de tus numeros salen, garantizas un acierto de t.
    (Si salen MAS de p, la garantia se mantiene.)

Trade-off honesto:
    - "t si t" (= covering): mas apuestas, pero la garantia se dispara con solo
      t aciertos -> probabilidad de dispararse MAS alta.
    - "t si p" con p>t: muchas menos apuestas, pero necesitas que salgan p de
      tus numeros -> probabilidad de dispararse MAS baja.
    El modulo te da ambos numeros para que elijas con criterio.

Construccion: greedy aleatorizado con reinicios (generaliza covering.py) y
verificacion por fuerza bruta. Solo libreria estandar.
"""

from __future__ import annotations
from itertools import combinations
from math import comb
import random
from dataclasses import dataclass


# --------------------------------------------------------------------------- #
# 1. Probabilidad de que la garantia se dispare (hipergeometrica)
# --------------------------------------------------------------------------- #

def _hipergeom(j: int, v: int, total: int = 49, draw: int = 6) -> float:
    if j < 0 or j > draw or j > v:
        return 0.0
    return comb(v, j) * comb(total - v, draw - j) / comb(total, draw)


def prob_p_de_v(v: int, p: int, total: int = 49) -> float:
    """P(al menos p de tus v numeros salgan entre los 6 -> la garantia 't si p' se dispara)."""
    return sum(_hipergeom(j, v, total) for j in range(p, 7))


# --------------------------------------------------------------------------- #
# 2. Generacion del wheel "t si p"
# --------------------------------------------------------------------------- #

def generar_wheel(
    numeros: list[int],
    t: int,
    p: int,
    k: int = 6,
    intentos: int = 200,
    semilla: int | None = 0,
) -> list[tuple[int, ...]]:
    """
    Genera un wheel que garantiza "acierto de t si salen p de tus numeros".
    Requiere t <= p <= 6 y t <= k <= v.
    """
    v = len(numeros)
    if not (1 <= t <= p <= 6):
        raise ValueError(f"Debe cumplirse 1 <= t({t}) <= p({p}) <= 6.")
    if not (t <= k <= v):
        raise ValueError(f"Debe cumplirse t({t}) <= k({k}) <= v({v}).")
    if semilla is not None:
        random.seed(semilla)

    idx = list(range(v))
    objetos = list(combinations(idx, p))          # p-subconjuntos a "cubrir"
    bloques = list(combinations(idx, k))          # apuestas candidatas

    # Para cada bloque, que objetos cubre (|B ∩ P| >= t).
    cobertura: dict[tuple, frozenset] = {}
    for b in bloques:
        sb = set(b)
        cubiertos = frozenset(
            i for i, o in enumerate(objetos) if len(sb.intersection(o)) >= t
        )
        cobertura[b] = cubiertos

    mejor: list[tuple] | None = None
    todos = set(range(len(objetos)))

    for _ in range(max(1, intentos)):
        pendientes = set(todos)
        seleccion: list[tuple] = []
        random.shuffle(bloques)
        while pendientes:
            mejor_b = max(bloques, key=lambda b: len(cobertura[b] & pendientes))
            ganancia = cobertura[mejor_b] & pendientes
            if not ganancia:
                break  # no deberia pasar si t<=p<=k
            seleccion.append(mejor_b)
            pendientes -= ganancia
        if not pendientes and (mejor is None or len(seleccion) < len(mejor)):
            mejor = seleccion

    if mejor is None:
        raise RuntimeError("No se pudo construir el wheel (parametros incompatibles).")

    return sorted(tuple(sorted(numeros[i] for i in b)) for b in mejor)


# --------------------------------------------------------------------------- #
# 3. Verificacion por fuerza bruta
# --------------------------------------------------------------------------- #

def verificar_wheel(
    apuestas: list[tuple[int, ...]],
    numeros: list[int],
    t: int,
    p: int,
) -> dict:
    """Comprueba que TODO p-subconjunto del pool corta alguna apuesta en >= t."""
    conjuntos = [set(a) for a in apuestas]
    fallos = []
    for P in combinations(sorted(numeros), p):
        sP = set(P)
        if not any(len(b & sP) >= t for b in conjuntos):
            fallos.append(P)
    return {"cumple": len(fallos) == 0, "fallos": fallos}


# --------------------------------------------------------------------------- #
# 4. Comparador de garantias por presupuesto
# --------------------------------------------------------------------------- #

@dataclass
class Wheel:
    pool: list[int]
    t: int
    p: int
    apuestas: list[tuple[int, ...]]
    cumple: bool
    n_apuestas: int
    coste: float
    prob_dispara: float

    def resumen(self) -> str:
        ok = "✓" if self.cumple else "✗"
        return (
            f"  '{self.t} si {self.p}'  apuestas={self.n_apuestas:>3}  "
            f"coste={self.coste:>6.2f} EUR  P(se dispara)={self.prob_dispara*100:>6.3f}%  [{ok}]"
        )


def construir_wheel(numeros, t, p, precio=0.50, intentos=200) -> Wheel:
    ap = generar_wheel(numeros, t=t, p=p, intentos=intentos)
    chk = verificar_wheel(ap, numeros, t, p)
    return Wheel(
        pool=sorted(numeros), t=t, p=p, apuestas=ap, cumple=chk["cumple"],
        n_apuestas=len(ap), coste=len(ap) * precio,
        prob_dispara=prob_p_de_v(len(numeros), p),
    )


def tabla_comparativa(numeros, t, precio=0.50, intentos=150) -> list[Wheel]:
    """
    Para una categoria de premio t fija, compara "t si t" (covering) frente a
    "t si p" con p creciente: ves como caen las apuestas (y la probabilidad).
    """
    wheels = []
    for p in range(t, 7):
        try:
            wheels.append(construir_wheel(numeros, t=t, p=p, precio=precio, intentos=intentos))
        except Exception:
            pass
    return wheels


# --------------------------------------------------------------------------- #
# 5. Demo / auto-test
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    print("=" * 70)
    print("DEMO lotto_design.py — wheels abreviados 't si p'")
    print("=" * 70)

    pool = [2, 9, 14, 19, 23, 27, 31, 38, 42, 47, 11, 35]  # v=12
    pool = sorted(pool)
    print(f"\nPool de ejemplo (v={len(pool)}): {pool}")

    for t in (3, 4):
        print(f"\nGarantia de un {t} — coste segun cuantos numeros exijas que salgan:")
        for w in tabla_comparativa(pool, t=t):
            print(w.resumen())

    print("\nLectura: 'un 3 si 3' (covering) cuesta mucho mas que 'un 3 si 5',")
    print("pero se dispara con mas frecuencia. Eliges segun presupuesto y gusto.")

    print("\nDetalle de un wheel '4 si 5' (v=12):")
    w = construir_wheel(pool, t=4, p=5)
    print(f"  apuestas={w.n_apuestas}  garantia verificada={w.cumple}")
    for ap in w.apuestas:
        print(f"    {ap}")
