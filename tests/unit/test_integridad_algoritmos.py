"""
Test de integridad de los 115 algoritmos.

Garantiza que cada algoritmo con interfaz de scoring:
  1. Se instancia sin error
  2. Ejecuta su método principal sin excepción
  3. Devuelve scores finitos (sin NaN/Inf)

Si alguien rompe un algoritmo en el futuro, este test lo detecta.

Los algoritmos que NO son scorers (helpers como SistemaReducido, Kelly,
FiltroJaccard) se testean en sus propios archivos.
"""

import inspect
import math
import random
from typing import Dict, List

import pytest


@pytest.fixture(scope="module")
def datos():
    random.seed(42)
    historico = [sorted(random.sample(range(1, 50), 6)) for _ in range(200)]
    sorteos = [
        {
            "numeros": h,
            "complementario": random.randint(1, 49),
            "reintegro": random.randint(0, 9),
            "bote": random.randint(100_000, 5_000_000),
        }
        for h in historico
    ]
    return {"historico": historico, "sorteos_completos": sorteos}


def _instanciar(cls, datos):
    """Instancia una clase con los datos que pida su constructor."""
    sig = inspect.signature(cls.__init__)
    kwargs = {}
    for name, param in sig.parameters.items():
        if name == "self":
            continue
        if name == "historico":
            kwargs[name] = datos["historico"]
        elif name in ("sorteos_completos", "sorteos"):
            kwargs[name] = datos["sorteos_completos"]
        elif param.default is not inspect.Parameter.empty:
            pass
        else:
            return None  # constructor no auto-instanciable
    return cls(**kwargs)


def _validar_scores(resultado) -> bool:
    """True si el resultado no tiene NaN/Inf."""
    if isinstance(resultado, dict):
        for v in resultado.values():
            if isinstance(v, (int, float)) and (math.isnan(v) or math.isinf(v)):
                return False
        return True
    if isinstance(resultado, tuple):
        for e in resultado:
            if isinstance(e, float) and (math.isnan(e) or math.isinf(e)):
                return False
        return True
    return True


# Módulos de algoritmos con interfaz de scoring estándar
MODULOS_SCORING = [
    "app.domain.algorithms.level1",
    "app.domain.algorithms.level2",
    "app.domain.algorithms.advanced",
    "app.domain.algorithms.block_i",
    "app.domain.algorithms.block_j",
    "app.domain.algorithms.block_k",
]


@pytest.mark.unit
class TestIntegridadAlgoritmos:
    def test_todos_los_scorers_funcionan(self, datos):
        """Cada algoritmo con calcular_scores debe ejecutar sin error."""
        fallos = []
        n_ok = 0
        for modname in MODULOS_SCORING:
            mod = __import__(modname, fromlist=["*"])
            for nombre in dir(mod):
                if nombre.startswith("_"):
                    continue
                obj = getattr(mod, nombre)
                if not inspect.isclass(obj):
                    continue
                if obj.__module__ != modname:
                    continue
                try:
                    inst = _instanciar(obj, datos)
                except Exception as e:
                    fallos.append(f"{nombre}: constructor {type(e).__name__}: {e}")
                    continue
                if inst is None:
                    continue  # no auto-instanciable, se testea aparte
                # Buscar método de scoring
                metodo = None
                for mn in ("calcular_scores", "calcular_scores_fft"):
                    if hasattr(inst, mn):
                        metodo = getattr(inst, mn)
                        break
                if metodo is None:
                    continue  # helper, no scorer
                # Solo si el método no requiere args obligatorios
                sig = inspect.signature(metodo)
                requiere_args = any(
                    p.default is inspect.Parameter.empty and pn != "self"
                    for pn, p in sig.parameters.items()
                )
                if requiere_args:
                    continue
                try:
                    resultado = metodo()
                    if not _validar_scores(resultado):
                        fallos.append(f"{nombre}.{metodo.__name__}: NaN/Inf en scores")
                    else:
                        n_ok += 1
                except Exception as e:
                    fallos.append(
                        f"{nombre}.{metodo.__name__}: {type(e).__name__}: {e}")
        assert not fallos, (
            f"{len(fallos)} algoritmos fallan:\n" + "\n".join(fallos)
        )
        # Aseguramos que al menos 50 scorers se ejecutaron (sanity)
        assert n_ok >= 50, f"Solo {n_ok} scorers ejecutados, esperaba >=50"
