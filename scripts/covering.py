"""
covering.py — Sistemas reducidos (wheeling) con garantía combinatoria verificada
================================================================================

Para loterías tipo 6/49 (Bonoloto). Esto es lo ÚNICO del motor que cambia de
forma medible cuántos aciertos SECUNDARIOS (3, 4, 5) sacas: no toca la
probabilidad del pleno de 6, pero convierte parte de tu suerte en una GARANTÍA.

Idea clave (semántica de la garantía):
    Eliges v números (tu "pool"). Los repartes en B apuestas de 6.
    Un diseño de cobertura C(v, 6, t) cumple:
        "Si al menos t de tus v números salen entre los 6 ganadores,
         alguna de tus apuestas contiene esos t números
         -> tienes GARANTIZADO al menos un acierto de t."

Lo que este módulo hace mejor que un greedy ingenuo:
  1. Greedy aleatorizado con múltiples reinicios -> coberturas más pequeñas
     (menos apuestas = menos euros para la misma garantía).
  2. Verificación por fuerza bruta de que la garantía se cumple de verdad.
  3. Cálculo honesto de probabilidades reales (hipergeométrica): con qué
     probabilidad se "dispara" la garantía y cuántos aciertos esperas por euro.

NOTA HONESTA: por linealidad de la esperanza, el número ESPERADO de aciertos
por euro NO depende de la estructura del sistema (es B * pmf hipergeométrica).
Lo que el wheeling compra es la GARANTÍA condicional (reduce la varianza /
elimina el peor caso), no más esperanza por euro. Este módulo lo deja explícito.
"""

from __future__ import annotations
from itertools import combinations
from math import comb
import random
from dataclasses import dataclass, field


# --------------------------------------------------------------------------- #
# 1. Generación de coberturas (greedy aleatorizado con reinicios)
# --------------------------------------------------------------------------- #

def generar_cobertura(
    numeros: list[int],
    t: int,
    k: int = 6,
    intentos: int = 300,
    semilla: int | None = None,
) -> list[tuple[int, ...]]:
    """
    Genera un sistema reducido sobre `numeros` (tu pool de v números) tal que
    todo subconjunto de t números de tu pool quede contenido en alguna apuesta
    de tamaño k. Garantiza: "si t de tus números salen -> acierto de t".

    Devuelve la lista de apuestas (tuplas ordenadas de k números reales).
    Usa greedy aleatorizado con `intentos` reinicios y se queda con el más corto.
    """
    if semilla is not None:
        random.seed(semilla)

    v = len(numeros)
    if not (1 <= t <= k <= v):
        raise ValueError(f"Debe cumplirse 1 <= t({t}) <= k({k}) <= v({v}).")
    if t == k:
        # Caso trivial: cada t-subconjunto necesita su propia apuesta de tamaño k=t,
        # pero k debe ser 6 en Bonoloto, así que esto solo aplica si t==6.
        return sorted(tuple(sorted(c)) for c in combinations(numeros, k))

    # Trabajamos con índices 0..v-1 y traducimos al final.
    indices = list(range(v))
    todos_t = list(combinations(indices, t))           # subconjuntos a cubrir
    bloques_posibles = list(combinations(indices, k))   # apuestas candidatas

    # Pre-cálculo: para cada bloque, qué t-subconjuntos cubre (como frozenset).
    cobertura_de = {
        b: frozenset(combinations(b, t)) for b in bloques_posibles
    }

    mejor: list[tuple[int, ...]] | None = None

    for _ in range(max(1, intentos)):
        pendientes = set(todos_t)
        seleccion: list[tuple[int, ...]] = []
        # Orden aleatorio de candidatos para romper empates de forma distinta.
        random.shuffle(bloques_posibles)

        while pendientes:
            # Elegir el bloque que cubre más pendientes (greedy), con desempate aleatorio.
            mejor_bloque = max(
                bloques_posibles,
                key=lambda b: len(cobertura_de[b] & pendientes),
            )
            ganancia = cobertura_de[mejor_bloque] & pendientes
            if not ganancia:
                # No debería pasar, pero por seguridad cogemos cualquiera pendiente.
                falta = next(iter(pendientes))
                mejor_bloque = next(
                    b for b in bloques_posibles if falta in cobertura_de[b]
                )
                ganancia = cobertura_de[mejor_bloque] & pendientes
            seleccion.append(mejor_bloque)
            pendientes -= ganancia

        if mejor is None or len(seleccion) < len(mejor):
            mejor = seleccion

    # Traducir índices -> números reales y ordenar.
    apuestas = sorted(tuple(sorted(numeros[i] for i in b)) for b in mejor)
    return apuestas


# --------------------------------------------------------------------------- #
# 2. Verificación por fuerza bruta de la garantía
# --------------------------------------------------------------------------- #

def verificar_garantia(
    apuestas: list[tuple[int, ...]],
    numeros: list[int],
    t: int,
) -> dict:
    """
    Comprueba EXHAUSTIVAMENTE que el sistema garantiza un acierto de t cuando
    salen t de tus números. Recorre todos los t-subconjuntos del pool y verifica
    que cada uno está contenido en alguna apuesta.

    Devuelve {'cumple': bool, 'fallos': [t-subconjuntos no cubiertos]}.
    """
    conjuntos = [set(a) for a in apuestas]
    fallos = []
    for sub in combinations(sorted(numeros), t):
        s = set(sub)
        if not any(s <= a for a in conjuntos):
            fallos.append(sub)
    return {"cumple": len(fallos) == 0, "fallos": fallos}


# --------------------------------------------------------------------------- #
# 3. Probabilidades reales (hipergeométrica) — honestas
# --------------------------------------------------------------------------- #

def _hipergeom_pmf(aciertos: int, pool: int, total: int = 49, extraidos: int = 6) -> float:
    """P(exactamente `aciertos` de tu pool entre los `extraidos` ganadores)."""
    if aciertos < 0 or aciertos > extraidos or aciertos > pool:
        return 0.0
    return comb(pool, aciertos) * comb(total - pool, extraidos - aciertos) / comb(total, extraidos)


def prob_dispara_garantia(pool_size: int, t: int, total: int = 49) -> float:
    """
    Probabilidad de que la garantía se "active": que al menos t de tus
    `pool_size` números salgan entre los 6 ganadores.
    """
    return sum(_hipergeom_pmf(j, pool_size, total) for j in range(t, 7))


def esperanza_aciertos_por_euro(
    n_apuestas: int,
    precio_apuesta: float = 0.50,
    total: int = 49,
) -> dict:
    """
    Número ESPERADO de apuestas que logran cada categoría (3,4,5,6) y por euro.
    Por linealidad NO depende del diseño, solo del nº de apuestas: es la base
    honesta para presupuestar (el wheeling añade GARANTÍA, no esperanza/euro).
    """
    pmf = {r: _hipergeom_pmf(r, 6, total) for r in (3, 4, 5, 6)}  # pool de la apuesta = 6
    coste = n_apuestas * precio_apuesta
    esperados = {r: n_apuestas * p for r, p in pmf.items()}
    por_euro = {r: (e / coste if coste else 0.0) for r, e in esperados.items()}
    return {
        "coste_total": round(coste, 2),
        "esperados_por_categoria": {r: round(v, 6) for r, v in esperados.items()},
        "esperados_por_euro": {r: round(v, 8) for r, v in por_euro.items()},
    }


# --------------------------------------------------------------------------- #
# 4. Recomendador / tabla de trade-off por presupuesto
# --------------------------------------------------------------------------- #

@dataclass
class SistemaReducido:
    pool: list[int]
    t: int
    apuestas: list[tuple[int, ...]] = field(default_factory=list)
    cumple_garantia: bool = False
    n_apuestas: int = 0
    coste: float = 0.0
    prob_garantia: float = 0.0  # P(salen >= t de tus números)

    def resumen(self) -> str:
        v = len(self.pool)
        ok = "✓ verificada" if self.cumple_garantia else "✗ NO se cumple"
        return (
            f"Pool v={v} numeros {self.pool} | garantia: si salen >={self.t} "
            f"de los tuyos -> acierto de {self.t} ({ok})\n"
            f"  Apuestas: {self.n_apuestas} | Coste: {self.coste:.2f} EUR | "
            f"P(se dispara la garantia)= {self.prob_garantia*100:.3f}%"
        )


def construir_sistema(
    numeros: list[int],
    t: int,
    precio_apuesta: float = 0.50,
    intentos: int = 300,
    semilla: int | None = 0,
) -> SistemaReducido:
    """Construye, verifica y caracteriza un sistema reducido de una sola llamada."""
    apuestas = generar_cobertura(numeros, t=t, intentos=intentos, semilla=semilla)
    chk = verificar_garantia(apuestas, numeros, t)
    return SistemaReducido(
        pool=sorted(numeros),
        t=t,
        apuestas=apuestas,
        cumple_garantia=chk["cumple"],
        n_apuestas=len(apuestas),
        coste=len(apuestas) * precio_apuesta,
        prob_garantia=prob_dispara_garantia(len(numeros), t),
    )


def tabla_trade_off(
    numeros: list[int],
    ts: tuple[int, ...] = (2, 3, 4),
    precio_apuesta: float = 0.50,
    intentos: int = 200,
) -> list[SistemaReducido]:
    """
    Devuelve, para un mismo pool, varios niveles de garantía t y su coste,
    para que decidas según presupuesto. Ordenado de más barato a más caro.
    """
    sistemas = [
        construir_sistema(numeros, t=t, precio_apuesta=precio_apuesta, intentos=intentos)
        for t in ts
        if t <= len(numeros)
    ]
    return sorted(sistemas, key=lambda s: s.coste)


# --------------------------------------------------------------------------- #
# 5. Demo / auto-test
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    print("=" * 70)
    print("DEMO covering.py — sistemas reducidos con garantia verificada")
    print("=" * 70)

    pool = [3, 11, 17, 24, 29, 33, 41, 45]  # 8 numeros elegidos
    print(f"\nPool de ejemplo (v=8): {pool}\n")

    for s in tabla_trade_off(pool, ts=(2, 3, 4)):
        print(s.resumen())
        print()

    # Garantia clasica "8 numeros, si salen 4 -> un 4 garantizado"
    print("-" * 70)
    print("Detalle del sistema t=4 (si salen 4 de tus 8 -> acierto de 4):")
    s4 = construir_sistema(pool, t=4)
    for i, ap in enumerate(s4.apuestas, 1):
        print(f"  Apuesta {i:2d}: {ap}")
    print(f"\nGarantia verificada por fuerza bruta: {s4.cumple_garantia}")

    print("\nEsperanza de aciertos por euro (no depende del diseño):")
    import json
    print(json.dumps(esperanza_aciertos_por_euro(s4.n_apuestas), indent=2))
