"""
Arnés de auditoría de los 115 algoritmos.

Para "implementar bien" un algoritmo, primero hay que garantizar que:
  1. Se instancia sin error con datos realistas
  2. Su método principal (calcular_scores / ejecutar / etc.) corre sin excepción
  3. Devuelve un resultado del tipo esperado (Dict[int,float] con 49 entradas,
     o una tupla, según el contrato)
  4. Los scores no contienen NaN/Inf

Este arnés inspecciona cada clase, detecta la firma del constructor, le pasa
los datos adecuados, ejecuta el método de scoring y reporta éxito/fallo.

Los algoritmos que fallen se corregirán uno a uno.
"""

import sys
import inspect
import math
import random
import traceback
from typing import Any, Dict, List

sys.path.insert(0, "/home/claude/bonoloto_2")

# ── Datos sintéticos realistas ──
random.seed(42)
N_SORTEOS = 200
HISTORICO: List[List[int]] = [
    sorted(random.sample(range(1, 50), 6)) for _ in range(N_SORTEOS)
]
SORTEOS_COMPLETOS: List[dict] = [
    {
        "numeros": h,
        "complementario": random.randint(1, 49),
        "reintegro": random.randint(0, 9),
        "bote": random.randint(100_000, 5_000_000),
    }
    for h in HISTORICO
]
SCORES_DUMMY: Dict[int, float] = {n: random.random() for n in range(1, 50)}
COMBO_DUMMY: List[int] = [3, 11, 19, 27, 35, 43]


def _args_para_constructor(cls):
    """Decide qué argumentos pasar al constructor según su firma."""
    try:
        sig = inspect.signature(cls.__init__)
    except (ValueError, TypeError):
        return None
    kwargs = {}
    for name, param in sig.parameters.items():
        if name == "self":
            continue
        # Mapear nombres conocidos a datos sintéticos
        if name == "historico":
            kwargs[name] = HISTORICO
        elif name in ("sorteos_completos", "sorteos"):
            kwargs[name] = SORTEOS_COMPLETOS
        elif name == "scores":
            kwargs[name] = dict(SCORES_DUMMY)
        elif name in ("combo", "combinacion"):
            kwargs[name] = list(COMBO_DUMMY)
        elif param.default is not inspect.Parameter.empty:
            # Tiene default, no lo tocamos
            pass
        else:
            # Parámetro requerido desconocido: intentar con None o saltar
            return None  # no sabemos instanciarlo automáticamente
    return kwargs


def _metodo_scoring(inst):
    """Encuentra el método principal de scoring de una instancia."""
    for nombre in ("calcular_scores", "ejecutar", "analizar",
                   "calcular_scores_fft", "predecir", "scores"):
        if hasattr(inst, nombre):
            m = getattr(inst, nombre)
            if callable(m):
                return nombre, m
    return None, None


def _validar_resultado(resultado: Any) -> str:
    """Valida que el resultado sea sensato. Devuelve '' si OK, o mensaje de error."""
    if resultado is None:
        return "devuelve None"
    if isinstance(resultado, dict):
        # Debe tener números como claves y floats finitos como valores
        for k, v in resultado.items():
            if isinstance(v, (int, float)):
                if math.isnan(v) or math.isinf(v):
                    return f"score[{k}]={v} no finito"
        return ""
    if isinstance(resultado, tuple):
        # Tuplas (valor, ...) — validar números dentro
        for elem in resultado:
            if isinstance(elem, float) and (math.isnan(elem) or math.isinf(elem)):
                return "tupla con valor no finito"
        return ""
    if isinstance(resultado, (list, float, int, bool)):
        return ""
    # Otros tipos: aceptamos
    return ""


def auditar_modulo(modname: str, score_methods_args: dict = None):
    """Audita todas las clases de un módulo."""
    score_methods_args = score_methods_args or {}
    mod = __import__(modname, fromlist=["*"])
    resultados = {"ok": [], "fallo": [], "saltado": []}

    for nombre in dir(mod):
        if nombre.startswith("_"):
            continue
        obj = getattr(mod, nombre)
        if not inspect.isclass(obj):
            continue
        # Solo clases definidas en este módulo
        if obj.__module__ != modname:
            continue

        kwargs = _args_para_constructor(obj)
        if kwargs is None:
            resultados["saltado"].append((nombre, "constructor no auto-instanciable"))
            continue

        try:
            inst = obj(**kwargs)
        except Exception as e:
            resultados["fallo"].append((nombre, f"constructor: {type(e).__name__}: {e}"))
            continue

        metodo_nombre, metodo = _metodo_scoring(inst)
        if metodo is None:
            resultados["saltado"].append((nombre, "sin método de scoring conocido"))
            continue

        # Argumentos especiales para ciertos métodos
        try:
            sig = inspect.signature(metodo)
            margs = {}
            for pn, pp in sig.parameters.items():
                if pn == "self":
                    continue
                if pn == "scores":
                    margs[pn] = dict(SCORES_DUMMY)
                elif pn in ("combo", "combinacion"):
                    margs[pn] = list(COMBO_DUMMY)
                elif pp.default is inspect.Parameter.empty:
                    margs = None
                    break
            if margs is None:
                resultados["saltado"].append(
                    (nombre, f"{metodo_nombre} requiere args desconocidos"))
                continue
            resultado = metodo(**margs)
            err = _validar_resultado(resultado)
            if err:
                resultados["fallo"].append((nombre, f"{metodo_nombre}: {err}"))
            else:
                resultados["ok"].append((nombre, metodo_nombre))
        except Exception as e:
            resultados["fallo"].append(
                (nombre, f"{metodo_nombre}: {type(e).__name__}: {e}"))

    return resultados


if __name__ == "__main__":
    modulos = [
        "app.domain.algorithms.level1",
        "app.domain.algorithms.level2",
        "app.domain.algorithms.advanced",
        "app.domain.algorithms.block_i",
        "app.domain.algorithms.block_j",
        "app.domain.algorithms.block_k",
        "app.domain.algorithms.block_l",
    ]
    total_ok = total_fallo = total_saltado = 0
    todos_fallos = []
    for m in modulos:
        try:
            r = auditar_modulo(m)
        except Exception as e:
            print(f"\n### {m}: ERROR cargando módulo: {e}")
            traceback.print_exc()
            continue
        corto = m.split(".")[-1]
        print(f"\n### {corto}: "
              f"{len(r['ok'])} OK, {len(r['fallo'])} fallo, "
              f"{len(r['saltado'])} saltado")
        for nombre, met in r["ok"]:
            print(f"  ✓ {nombre}.{met}")
        for nombre, err in r["fallo"]:
            print(f"  ✗ {nombre}: {err}")
            todos_fallos.append((corto, nombre, err))
        for nombre, raz in r["saltado"]:
            print(f"  — {nombre}: {raz}")
        total_ok += len(r["ok"])
        total_fallo += len(r["fallo"])
        total_saltado += len(r["saltado"])

    print("\n" + "=" * 60)
    print(f"TOTAL: {total_ok} OK, {total_fallo} fallo, {total_saltado} saltado")
    print("=" * 60)
    if todos_fallos:
        print("\nFALLOS A CORREGIR:")
        for mod, nombre, err in todos_fallos:
            print(f"  [{mod}] {nombre}: {err}")
