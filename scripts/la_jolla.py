"""
la_jolla.py — Coberturas optimas demostradas (La Jolla) + cota de Schonheim
============================================================================

Mejora de covering.py: en vez de generar el sistema reducido con un greedy,
descarga el MEJOR diseño de cobertura conocido del repositorio de referencia
mundial (La Jolla Covering Repository, ljcr.dmgordon.org), lo remapea a TUS
numeros reales y verifica la garantia por fuerza bruta. Si no hay red o el
diseno no existe, cae limpiamente al greedy verificado de covering.py.

Por que importa: para muchos parametros, el repositorio tiene el diseno OPTIMO
demostrado (alcanza la cota inferior de Schonheim). Eso significa el minimo
absoluto de apuestas para una garantia dada -> menos coste por la misma garantia.

Formato del repositorio (endpoint show_cover.php?v=..&k=..&t=..):
    <lb> <= C(v,k,t) <= <ub>
    Method of Construction: ...
    Lower Bound: Schonheim
    <bloque 1: k enteros separados por espacio, indexados 1..v o 0..v-1>
    <bloque 2: ...>
    ...

NOTA: el fetch en vivo requiere conexion a internet (funciona en tu PC).
Solo usa la libreria estandar (urllib). Sin dependencias nuevas.
"""

from __future__ import annotations
from math import ceil
import json
import os
import re
import urllib.request
import urllib.error

# Reutilizamos el verificador y el fallback del modulo covering.
from covering import verificar_garantia, construir_sistema, SistemaReducido, prob_dispara_garantia


BASE_URL = "https://ljcr.dmgordon.org/show_cover.php"


# --------------------------------------------------------------------------- #
# 1. Cota inferior de Schonheim (cuanto es el minimo teorico de apuestas)
# --------------------------------------------------------------------------- #

def schonheim(v: int, k: int, t: int) -> int:
    """
    Cota inferior de Schonheim L(v,k,t) <= C(v,k,t): ningun sistema con esa
    garantia puede tener MENOS apuestas que este numero. Recursiva:
        L(v,k,1) = ceil(v/k)
        L(v,k,t) = ceil( v/k * L(v-1, k-1, t-1) )
    """
    if t <= 0:
        return 1
    if t == 1:
        return ceil(v / k)
    return ceil((v / k) * schonheim(v - 1, k - 1, t - 1))


# --------------------------------------------------------------------------- #
# 2. Parser del formato del repositorio
# --------------------------------------------------------------------------- #

def _parsear_pagina(texto: str, k: int) -> dict:
    """
    Extrae bloques y cotas del texto devuelto por show_cover.php.
    Devuelve {'bloques': [[int,...]], 'lb': int|None, 'ub': int|None,
              'indexado_desde': 0|1, 'metodo': str}.
    """
    lb = ub = None
    metodo = ""
    # Cabecera del tipo "43 <= C(20,14,7) <= 60" (el <= puede venir como unicode).
    m = re.search(r"(\d+)\s*(?:<=|≤|&le;)\s*C\(\d+,\d+,\d+\)\s*(?:<=|≤|&le;)\s*(\d+)", texto)
    if m:
        lb, ub = int(m.group(1)), int(m.group(2))
    mm = re.search(r"Method of Construction:\s*(.+)", texto)
    if mm:
        metodo = mm.group(1).strip()

    bloques: list[list[int]] = []
    for linea in texto.splitlines():
        linea = linea.strip()
        if not linea:
            continue
        # Una linea-bloque es solo enteros separados por espacios, exactamente k.
        if not re.fullmatch(r"(\d+\s+)*\d+", linea):
            continue
        nums = [int(x) for x in linea.split()]
        if len(nums) == k:
            bloques.append(nums)

    if not bloques:
        raise ValueError("No se encontraron bloques en la respuesta del repositorio.")

    indexado_desde = 0 if min(min(b) for b in bloques) == 0 else 1
    return {
        "bloques": bloques,
        "lb": lb,
        "ub": ub,
        "indexado_desde": indexado_desde,
        "metodo": metodo,
    }


# --------------------------------------------------------------------------- #
# 3. Descarga del diseno optimo conocido
# --------------------------------------------------------------------------- #

def obtener_cobertura_la_jolla(v: int, k: int, t: int, timeout: float = 15.0,
                               cache_dir: str | None = None) -> dict:
    """
    Descarga y parsea el mejor diseno (v,k,t) conocido del repositorio.
    Devuelve dict con 'bloques' (indices base 1) y cotas. Lanza excepcion
    si no hay red o el diseno no existe.

    Si `cache_dir` se indica, guarda/lee el diseño en
    `cache_dir/{v}_{k}_{t}.json`, de modo que tras la primera vez ya no se
    depende del sitio externo (determinismo y robustez).
    """
    cache_path = None
    if cache_dir:
        cache_path = os.path.join(cache_dir, f"{v}_{k}_{t}.json")
        if os.path.exists(cache_path):
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    info = json.load(f)
                if info.get("bloques"):
                    info["origen_cache"] = True
                    return info
            except (ValueError, OSError):
                pass  # caché corrupta: la regeneramos desde la red

    url = f"{BASE_URL}?v={v}&k={k}&t={t}"
    req = urllib.request.Request(url, headers={"User-Agent": "bonoloto-covering/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        texto = resp.read().decode("utf-8", errors="replace")
    info = _parsear_pagina(texto, k)
    # Normalizamos a base 1 (1..v) internamente.
    if info["indexado_desde"] == 0:
        info["bloques"] = [[x + 1 for x in b] for b in info["bloques"]]
    info["url"] = url
    info["origen_cache"] = False

    if cache_path:
        try:
            os.makedirs(cache_dir, exist_ok=True)
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(info, f, ensure_ascii=False, indent=2)
        except OSError:
            pass  # si no se puede cachear, no pasa nada

    return info


# --------------------------------------------------------------------------- #
# 4. Sistema OPTIMO sobre tus numeros (con fallback verificado)
# --------------------------------------------------------------------------- #

def construir_sistema_optimo(
    numeros: list[int],
    t: int,
    k: int = 6,
    precio_apuesta: float = 0.50,
    permitir_red: bool = True,
    intentos_fallback: int = 300,
    cache_dir: str | None = None,
) -> SistemaReducido:
    """
    Construye el sistema reducido sobre `numeros` usando el mejor diseno conocido
    de La Jolla; si no hay red o falla, usa el greedy verificado de covering.py.
    En ambos casos la garantia se VERIFICA por fuerza bruta antes de devolverla.

    Si `cache_dir` se indica, el diseño de La Jolla se cachea en disco para no
    depender del sitio externo en cada ejecución.

    El objeto resultante lleva atributos extra de procedencia:
      .fuente           -> 'la_jolla' | 'greedy_local'
      .schonheim        -> cota inferior teorica de apuestas
      .optimo_demostrado-> True si nº de apuestas == cota de Schonheim
    """
    v = len(numeros)
    pool = sorted(numeros)
    sistema: SistemaReducido | None = None
    fuente = "greedy_local"

    if permitir_red:
        try:
            info = obtener_cobertura_la_jolla(v, k, t, cache_dir=cache_dir)
            # Remapear puntos 1..v del diseno -> tus numeros reales (ordenados).
            apuestas = sorted(
                tuple(sorted(pool[i - 1] for i in bloque))
                for bloque in info["bloques"]
            )
            chk = verificar_garantia(apuestas, pool, t)
            if chk["cumple"]:
                sistema = SistemaReducido(
                    pool=pool, t=t, apuestas=apuestas,
                    cumple_garantia=True, n_apuestas=len(apuestas),
                    coste=len(apuestas) * precio_apuesta,
                    prob_garantia=prob_dispara_garantia(v, t),
                )
                fuente = "la_jolla"
        except (urllib.error.URLError, ValueError, TimeoutError, OSError):
            sistema = None  # caemos al fallback

    if sistema is None:
        sistema = construir_sistema(
            pool, t=t, precio_apuesta=precio_apuesta, intentos=intentos_fallback
        )

    # Anotaciones de procedencia y optimalidad.
    # Schönheim es una COTA INFERIOR: cualquier cobertura válida cumple
    # n_apuestas >= schonheim. Por tanto "óptimo demostrado" es exactamente
    # alcanzar esa cota (igualdad), no "menor o igual".
    sch = schonheim(v, k, t)
    sistema.fuente = fuente                         # type: ignore[attr-defined]
    sistema.schonheim = sch                         # type: ignore[attr-defined]
    sistema.optimo_demostrado = sistema.n_apuestas == sch  # type: ignore[attr-defined]
    return sistema


# --------------------------------------------------------------------------- #
# 5. Demo / auto-test (parser y Schonheim offline; fetch se prueba en tu PC)
# --------------------------------------------------------------------------- #

_SAMPLE = """43 ≤ C(20,14,7) ≤ 60
Method of Construction: dynamic programming covering
Lower Bound: Schonheim
1 2 3 4 5 6 7 8 9 10 12 13 15 17
1 2 3 4 5 6 7 8 9 10 14 15 16 17
1 2 3 4 5 6 7 8 9 10 13 14 15 18
1 2 3 4 5 6 7 8 9 10 11 12 19 20"""

if __name__ == "__main__":
    print("=" * 70)
    print("DEMO la_jolla.py")
    print("=" * 70)

    print("\n[1] Parser sobre muestra real del repositorio:")
    info = _parsear_pagina(_SAMPLE, k=14)
    print(f"  Cotas: {info['lb']} <= C <= {info['ub']} | metodo: {info['metodo']}")
    print(f"  Bloques parseados: {len(info['bloques'])} (indexado desde {info['indexado_desde']})")
    print(f"  Primer bloque: {info['bloques'][0]}")

    print("\n[2] Cota de Schonheim para wheels tipicos de Bonoloto (k=6):")
    print(f"  {'pool v':>7} {'t':>3} {'min. apuestas (Schonheim)':>26}")
    for v in (7, 8, 9, 10, 12, 14):
        for t in (2, 3, 4):
            if t <= v:
                print(f"  {v:>7} {t:>3} {schonheim(v, 6, t):>26}")

    print("\n[3] Construir sistema optimo (intenta La Jolla, si no -> greedy):")
    s = construir_sistema_optimo([3, 11, 17, 24, 29, 33, 41, 45], t=3, permitir_red=True)
    print(f"  Fuente: {s.fuente} | apuestas: {s.n_apuestas} | "
          f"Schonheim: {s.schonheim} | optimo: {s.optimo_demostrado}")
    print(f"  Garantia verificada: {s.cumple_garantia} | coste: {s.coste:.2f} EUR")
    for ap in s.apuestas:
        print(f"    {ap}")
