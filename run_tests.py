"""
Runner mínimo de tests para entornos sin pytest instalado.

Soporta:
  - Fixtures simples (devolvedoras directas, no generators)
  - monkeypatch básico
  - pytest.raises
  - asyncio.run para coroutines
  - setup_method / teardown_method por clase

Limitaciones (no es pytest):
  - No soporta @pytest.fixture con yield
  - No soporta scopes (todos son function-scope)
  - No paraleliza

Diseñado para correr nuestra suite hasta que pytest esté disponible
en el entorno de producción.
"""

import sys
import types
import traceback
import inspect
import importlib
import os
import asyncio


# ───── STUBS DE DEPENDENCIAS ─────────────────────────────────────────

def _setup_stubs():
    try:
        import pydantic  # noqa
    except ImportError:
        pyd = types.ModuleType("pydantic")
        class _BM:
            def __init__(self, **kw):
                for k, v in kw.items():
                    setattr(self, k, v)
        pyd.BaseModel = _BM
        pyd.Field = lambda d=None, **kw: d
        pyd.field_validator = lambda *a, **kw: (lambda fn: fn)
        sys.modules["pydantic"] = pyd

    try:
        import jwt  # noqa
    except ImportError:
        jm = types.ModuleType("jwt")
        jm.encode = lambda *a, **k: "x"
        jm.decode = lambda *a, **k: {}
        jm.ExpiredSignatureError = type("E", (Exception,), {})
        jm.InvalidTokenError = type("E", (Exception,), {})
        sys.modules["jwt"] = jm

    try:
        import oracledb  # noqa
    except ImportError:
        om = types.ModuleType("oracledb")
        om.create_pool_async = lambda **kw: None
        sys.modules["oracledb"] = om

    try:
        import fastapi  # noqa
    except ImportError:
        class _S:
            def __init__(self, *a, **kw): pass
            def __getattr__(self, _):
                def d(*a, **kw):
                    def i(fn): return fn
                    return i
                return d
        fm = types.ModuleType("fastapi")
        fm.FastAPI = _S
        fm.APIRouter = _S
        fm.HTTPException = type("H", (Exception,),
                                {"__init__": lambda s, **k: None})
        fm.Depends = lambda x=None: x
        fm.BackgroundTasks = type("BT", (),
                                  {"add_task": lambda s, *a, **kw: None})
        fm.Body = lambda *a, **kw: None
        fm.Query = lambda *a, **kw: None
        fm.status = types.SimpleNamespace(
            HTTP_400_BAD_REQUEST=400, HTTP_401_UNAUTHORIZED=401,
            HTTP_404_NOT_FOUND=404, HTTP_500_INTERNAL_SERVER_ERROR=500,
            HTTP_503_SERVICE_UNAVAILABLE=503,
        )
        sys.modules["fastapi"] = fm
        sys.modules["fastapi.middleware"] = types.ModuleType("fastapi.middleware")
        cors = types.ModuleType("fastapi.middleware.cors")
        cors.CORSMiddleware = type("CM", (), {})
        sys.modules["fastapi.middleware.cors"] = cors
        sec = types.ModuleType("fastapi.security")
        sec.HTTPBearer = type("HB", (), {"__init__": lambda s, **k: None})
        sec.HTTPAuthorizationCredentials = type("HAC", (), {})
        sys.modules["fastapi.security"] = sec
        rsp = types.ModuleType("fastapi.responses")
        rsp.StreamingResponse = type("SR", (), {})
        sys.modules["fastapi.responses"] = rsp

    if "pytest" not in sys.modules:
        pm = types.ModuleType("pytest")
        pm.fixture = lambda fn=None, **kw: (fn if fn else (lambda f: f))
        class _Mark:
            def __getattr__(self, name):
                def deco(target):
                    return target
                return deco
        pm.mark = _Mark()
        class _Raises:
            def __init__(self, exc):
                self.exc = exc
                self.value = None
            def __enter__(self):
                return self
            def __exit__(self, et, ev, tb):
                if et is None:
                    raise AssertionError(
                        f"Esperaba {self.exc.__name__}, no hubo excepción"
                    )
                self.value = ev
                return issubclass(et, self.exc)
        pm.raises = _Raises
        sys.modules["pytest"] = pm


# ───── FIXTURES & MONKEYPATCH ─────────────────────────────────────────


class MonkeyPatch:
    """Stub básico de pytest.monkeypatch."""

    def __init__(self):
        self.saved = {}

    def setenv(self, k, v):
        self.saved[k] = os.environ.get(k)
        os.environ[k] = v

    def delenv(self, k, raising=True):
        self.saved[k] = os.environ.get(k)
        os.environ.pop(k, None)

    def restore(self):
        for k, v in self.saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def _discover_fixtures(mod):
    """
    Busca en el módulo las funciones decoradas con @pytest.fixture
    (en nuestro runner son funciones top-level que devuelven valores).
    """
    fixtures = {}
    for name in dir(mod):
        obj = getattr(mod, name)
        if callable(obj) and not name.startswith("_") and not inspect.isclass(obj):
            # Heurística: cualquier callable top-level sin underscore
            # con argumentos opcionales que devuelva algo es candidato a fixture.
            # Pero acotamos a los nombres comunes:
            if name in ("sorteos_dummy", "motor", "repo", "datos",
                        "sorteos_aleatorios"):
                fixtures[name] = obj
    return fixtures


def _resolve_param(param_name, fixtures, fixture_cache, monkeypatches):
    """Resuelve un parámetro de test desde fixtures/monkeypatch."""
    if param_name == "monkeypatch":
        mp = MonkeyPatch()
        monkeypatches.append(mp)
        return mp
    if param_name in fixture_cache:
        return fixture_cache[param_name]
    if param_name in fixtures:
        # Fixture puede depender de otras: resolver recursivamente
        fx_fn = fixtures[param_name]
        sig = inspect.signature(fx_fn)
        sub_args = {}
        for sub_name in sig.parameters:
            sub_args[sub_name] = _resolve_param(
                sub_name, fixtures, fixture_cache, monkeypatches
            )
        val = fx_fn(**sub_args)
        fixture_cache[param_name] = val
        return val
    raise RuntimeError(f"Fixture no encontrada: {param_name}")


def run_module(modname):
    """Ejecuta los tests de un módulo. Devuelve (n_pass, n_fail, [failures])."""
    n_pass = n_fail = 0
    failures = []
    try:
        mod = importlib.import_module(modname)
    except Exception as e:
        return 0, 1, [f"{modname}: ERROR de carga: {e}"]

    fixtures = _discover_fixtures(mod)

    for cls_name in dir(mod):
        if not cls_name.startswith("Test"):
            continue
        cls = getattr(mod, cls_name)
        for m_name in dir(cls):
            if not m_name.startswith("test_"):
                continue
            inst = cls()
            mp_list = []
            fixture_cache = {}
            try:
                if hasattr(inst, "setup_method"):
                    inst.setup_method()
                method = getattr(inst, m_name)
                sig = inspect.signature(method)
                kwargs = {}
                for pname in sig.parameters:
                    kwargs[pname] = _resolve_param(
                        pname, fixtures, fixture_cache, mp_list
                    )
                result = method(**kwargs)
                # Si el test devuelve una coroutine, ejecutarla
                if asyncio.iscoroutine(result):
                    asyncio.run(result)
                if hasattr(inst, "teardown_method"):
                    inst.teardown_method()
                n_pass += 1
            except AssertionError as e:
                n_fail += 1
                failures.append(f"{modname}.{cls_name}.{m_name}: AssertionError: {e}")
            except Exception as e:
                n_fail += 1
                failures.append(
                    f"{modname}.{cls_name}.{m_name}: {type(e).__name__}: {e}"
                )
            finally:
                for mp in mp_list:
                    mp.restore()

    return n_pass, n_fail, failures


def main(modules=None):
    _setup_stubs()
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    if modules is None:
        modules = [
            "tests.unit.test_trabajos_repo",
            "tests.unit.test_config",
            "tests.unit.test_motor_ia",
            "tests.unit.test_worker_pool",
            "tests.integration.test_worker_pool_e2e",
            "tests.unit.test_honestidad",
            "tests.unit.test_sistemas_reducidos",
            "tests.unit.test_kelly_popularidad",
            "tests.unit.test_integridad_algoritmos",
            "tests.unit.test_backtest_framework",
            "tests.unit.test_contrato_frontend",
            "tests.unit.test_calibracion_suma",
            "tests.unit.test_valor_real",
            "tests.unit.test_memoria",
            "tests.unit.test_sqlite",
            "tests.unit.test_apuesta_multiple",
        ]

    total_p = total_f = 0
    all_failures = []
    print("=" * 60)
    print("RUNNER DE TESTS (sin pytest)")
    print("=" * 60)
    for mod in modules:
        p, f, fails = run_module(mod)
        total_p += p
        total_f += f
        all_failures.extend(fails)
        status = "OK" if f == 0 else "FAIL"
        print(f"  [{status}] {mod}: {p} pass, {f} fail")

    if all_failures:
        print("\n--- FALLOS ---")
        for x in all_failures:
            print(f"  {x}")

    print("\n" + "=" * 60)
    print(f"TOTAL: {total_p} pass, {total_f} fail")
    print("=" * 60)
    return 0 if total_f == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
