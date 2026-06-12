#!/usr/bin/env python3
"""
sistema_garantizado.py — Pieza de integración (Fase A, Bonoloto 2.0)
====================================================================

Une los módulos nuevos (popularidad, lotto_design, covering, la_jolla) para
producir, cada día, el bloque `sistema` + `apuestas` + `honestidad` del JSON
diario (esquema v2), SIN tocar nada del esquema v1 que ya consume la app.

Qué hace, en orden:
  1. Elige un POOL de números "anti-popular" (números que la gente jueg​a
     menos; si ganas, repartes con menos gente). Determinista: la fecha del
     sorteo es la semilla → misma fecha = mismo pool = mismo sistema.
  2. Construye un sistema de apuestas con GARANTÍA combinatoria:
       - p > t  → wheel abreviado (lotto_design), p. ej. "un 4 si salen 5".
       - p == t → cobertura clásica (covering) verificada, con la cota de
                  Schönheim como referencia de optimalidad (sin red).
  3. VERIFICA la garantía por fuerza bruta. Si no se cumple, ABORTA con
     exit != 0: el workflow debe fallar antes que publicar humo.
  4. Ordena las apuestas por premio esperado relativo (reparto parimutuel).

HONESTIDAD (innegociable): nada de esto cambia la probabilidad del pleno
(1/13.983.816). Las garantías son sobre premios secundarios y el premio
esperado solo refleja con cuánta gente repartirías si ganases.

Solo stdlib + los módulos del paquete (que a su vez usan solo stdlib).
"""
from __future__ import annotations

import os
import random
import sys
from itertools import combinations

# Los módulos del paquete viven en esta misma carpeta (scripts/).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import lotto_design  # noqa: E402
import covering      # noqa: E402
import la_jolla      # noqa: E402  (solo usamos schonheim(); no hace red)
from popularidad import ModeloPopularidad  # noqa: E402

# Parámetros del preset (configurables por variable de entorno).
POOL_SIZE = int(os.getenv("SISTEMA_POOL", "12"))
GARANTIA_T = int(os.getenv("SISTEMA_T", "4"))
GARANTIA_P = int(os.getenv("SISTEMA_P", "5"))
PRECIO = float(os.getenv("PRECIO_APUESTA", "0.50"))

# Carpeta de caché de coberturas óptimas de La Jolla (dentro del repo).
RAIZ_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.getenv(
    "COBERTURAS_CACHE_DIR",
    os.path.join(RAIZ_REPO, "data", "coberturas_cache"),
)

NOTA_HONESTIDAD = (
    "Ningún sistema cambia la probabilidad del pleno (1 entre 13.983.816). "
    "Las garantías son combinatorias sobre premios secundarios; el premio "
    "esperado refleja el reparto parimutuel."
)


def _semilla_de_fecha(fecha: str) -> int:
    """Semilla entera y estable a partir de 'AAAA-MM-DD' (determinismo)."""
    return int("".join(ch for ch in fecha if ch.isdigit()) or "0")


def elegir_pool_antipopular(fecha: str, tam: int = POOL_SIZE,
                            candidatos: int = 300, muestras: int = 40):
    """Elige `tam` números cuyo pool genere combinaciones poco populares.

    Sortea `candidatos` pools al azar (con semilla = fecha), puntúa cada uno
    por el índice medio de popularidad de una muestra de sus combinaciones,
    y se queda con el menos popular. Determinista para una misma fecha.
    """
    rng = random.Random(_semilla_de_fecha(fecha))
    modelo = ModeloPopularidad()
    mejor_pool, mejor_indice = None, float("inf")
    for _ in range(candidatos):
        pool = sorted(rng.sample(range(1, 50), tam))
        total = 0.0
        for _ in range(muestras):
            combo = sorted(rng.sample(pool, 6))
            total += modelo.indice(combo)
        media = total / muestras
        if media < mejor_indice:
            mejor_indice, mejor_pool = media, pool
    return mejor_pool


def generar_sistema_diario(fecha: str,
                           pool_size: int = POOL_SIZE,
                           t: int = GARANTIA_T,
                           p: int = GARANTIA_P,
                           precio: float = PRECIO) -> dict:
    """Devuelve {'sistema': ..., 'apuestas': ..., 'honestidad': ...}.

    ABORTA el proceso (SystemExit) si la verificación por fuerza bruta
    falla: el workflow diario debe ponerse en rojo antes que publicar un
    sistema sin garantía real.
    """
    if pool_size > 16:
        raise SystemExit(
            f"ERROR: pool de {pool_size} números no permitido (máx. 16): "
            "el coste combinatorio crece demasiado."
        )
    if not (3 <= t <= p <= 6):
        raise SystemExit(f"ERROR: garantía '{t} si {p}' no válida.")

    pool = elegir_pool_antipopular(fecha, tam=pool_size)

    if p > t:
        # Wheel abreviado "t si p" (mucho más barato que la cobertura plena).
        wheel = lotto_design.construir_wheel(pool, t=t, p=p, precio=precio)
        apuestas = [list(a) for a in wheel.apuestas]
        verificada = bool(wheel.cumple)
        n_apuestas = wheel.n_apuestas
        coste = wheel.coste
        prob_dispara = wheel.prob_dispara
        tipo, fuente, schonheim, optimo = ("wheel_abreviado", "greedy_local",
                                           None, False)
    else:
        # Cobertura clásica "t si t": óptimo demostrado de La Jolla (con caché
        # en disco) y, si no hay red, fallback al greedy verificado. La garantía
        # se verifica por fuerza bruta en ambos casos dentro del módulo.
        sistema = la_jolla.construir_sistema_optimo(
            pool, t=t, precio_apuesta=precio, cache_dir=CACHE_DIR
        )
        apuestas = [list(a) for a in sistema.apuestas]
        verificada = bool(sistema.cumple_garantia)
        n_apuestas = sistema.n_apuestas
        coste = sistema.coste
        prob_dispara = sistema.prob_garantia
        tipo = "cobertura_optima"
        fuente = getattr(sistema, "fuente", "greedy_local")
        schonheim = getattr(sistema, "schonheim", None)
        optimo = bool(getattr(sistema, "optimo_demostrado", False))

    # Regla 3 del prompt: la verificación NUNCA se omite ni se perdona.
    if not verificada:
        raise SystemExit(
            "ERROR CRÍTICO: la garantía del sistema NO pasó la verificación "
            "por fuerza bruta. No se publica nada."
        )

    # Ordenar por premio esperado relativo (mejor reparto primero).
    modelo = ModeloPopularidad()
    ordenadas = modelo.ordenar_por_premio(apuestas)
    apuestas_json = [
        {"numeros": list(c), "premio_esperado_rel": round(v, 3)}
        for c, v in ordenadas
    ]

    return {
        "sistema": {
            "tipo": tipo,
            "fuente": fuente,
            "pool": list(pool),
            "garantia": {
                "t": t,
                "p": p,
                "texto": (f"Un acierto de {t} garantizado si salen {p} "
                          f"de tus {len(pool)} números"),
            },
            "verificada_fuerza_bruta": verificada,
            "n_apuestas": n_apuestas,
            "coste_eur": round(coste, 2),
            "prob_dispara_garantia": round(prob_dispara, 6),
            "schonheim": schonheim,
            "optimo_demostrado": optimo,
        },
        "apuestas": apuestas_json,
        "honestidad": {
            "nota": NOTA_HONESTIDAD,
            "backtest_ultima_fecha": None,   # se rellenará en la Fase C
            "scorers_superan_azar": [],      # se rellenará en la Fase C
        },
    }


if __name__ == "__main__":
    # Demo / auto-test: genera el sistema para una fecha fija y comprueba
    # el determinismo (misma fecha ⇒ mismo sistema).
    import json

    fecha = sys.argv[1] if len(sys.argv) > 1 else "2026-06-10"
    print(f"Generando sistema para el sorteo del {fecha} "
          f"(pool {POOL_SIZE}, garantía '{GARANTIA_T} si {GARANTIA_P}')...")
    r1 = generar_sistema_diario(fecha)
    r2 = generar_sistema_diario(fecha)
    assert r1 == r2, "FALLO: el sistema no es determinista"
    s = r1["sistema"]
    print(json.dumps(s, ensure_ascii=False, indent=2))
    print(f"\nApuestas ({len(r1['apuestas'])}), mejores primero:")
    for a in r1["apuestas"][:5]:
        print(f"  {a['numeros']}  premio_esp x{a['premio_esperado_rel']}")
    print("\n✓ Determinismo comprobado (dos ejecuciones idénticas).")
    print("✓ Garantía verificada por fuerza bruta:",
          s["verificada_fuerza_bruta"])
