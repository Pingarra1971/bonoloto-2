"""
Configuración de pytest: stubs para módulos opcionales.

Permite ejecutar la suite sin tener fastapi/oracledb/jwt/pydantic instalados
en el entorno (útil para CI ligero y para validación local rápida). Los
tests de integración que sí necesitan estos módulos están marcados con
@pytest.mark.integration y se saltan automáticamente cuando falta la dep.
"""

import sys
import types
import pytest


def _stub_module(name: str, **attrs):
    """Crea un módulo stub vacío con los atributos dados."""
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    sys.modules[name] = mod
    return mod


def _ensure_optional_deps():
    """Stubea fastapi/jwt/oracledb/pydantic si no están instalados."""
    # pydantic
    try:
        import pydantic  # noqa
    except ImportError:
        class _BaseModel:
            def __init__(self, **kw):
                for k, v in kw.items():
                    setattr(self, k, v)
            def model_dump(self):
                return self.__dict__.copy()
            @classmethod
            def model_validate(cls, d):
                return cls(**d)
        pyd = types.ModuleType("pydantic")
        pyd.BaseModel = _BaseModel
        pyd.Field = lambda default=None, **kw: default
        pyd.field_validator = lambda *a, **kw: (lambda fn: fn)
        sys.modules["pydantic"] = pyd

    # jwt
    try:
        import jwt  # noqa
    except ImportError:
        jwt_mod = types.ModuleType("jwt")
        jwt_mod.encode = lambda *a, **k: "stub_token"
        jwt_mod.decode = lambda *a, **k: {}
        jwt_mod.ExpiredSignatureError = type("ExpiredSignatureError", (Exception,), {})
        jwt_mod.InvalidTokenError = type("InvalidTokenError", (Exception,), {})
        sys.modules["jwt"] = jwt_mod

    # oracledb
    try:
        import oracledb  # noqa
    except ImportError:
        oracledb_mod = types.ModuleType("oracledb")
        oracledb_mod.create_pool_async = lambda **kw: None
        oracledb_mod.create_pool = lambda **kw: None
        oracledb_mod.AsyncConnectionPool = type("AsyncConnectionPool", (), {})
        sys.modules["oracledb"] = oracledb_mod

    # fastapi (más complejo; stub permisivo)
    try:
        import fastapi  # noqa
    except ImportError:
        class _Stub:
            def __init__(self, *a, **kw): pass
            def __getattr__(self, _):
                def d(*a, **kw):
                    def i(fn): return fn
                    return i
                return d
            def __call__(self, *a, **kw):
                return self
        fastapi_mod = types.ModuleType("fastapi")
        fastapi_mod.FastAPI = _Stub
        fastapi_mod.HTTPException = type(
            "HTTPException", (Exception,),
            {"__init__": lambda self, **k: None}
        )
        fastapi_mod.Depends = lambda x=None: x
        fastapi_mod.BackgroundTasks = type(
            "BackgroundTasks", (),
            {"add_task": lambda self, *a, **kw: None}
        )
        fastapi_mod.APIRouter = _Stub
        fastapi_mod.Body = lambda *a, **kw: None
        fastapi_mod.Query = lambda *a, **kw: None
        fastapi_mod.status = types.SimpleNamespace(
            HTTP_400_BAD_REQUEST=400,
            HTTP_401_UNAUTHORIZED=401,
            HTTP_404_NOT_FOUND=404,
            HTTP_500_INTERNAL_SERVER_ERROR=500,
        )
        sys.modules["fastapi"] = fastapi_mod

        cors_mod = types.ModuleType("fastapi.middleware.cors")
        cors_mod.CORSMiddleware = type("CORSMiddleware", (), {})
        sys.modules["fastapi.middleware"] = types.ModuleType("fastapi.middleware")
        sys.modules["fastapi.middleware.cors"] = cors_mod

        sec_mod = types.ModuleType("fastapi.security")
        sec_mod.HTTPBearer = type(
            "HTTPBearer", (),
            {"__init__": lambda self, **k: None}
        )
        sec_mod.HTTPAuthorizationCredentials = type(
            "HTTPAuthorizationCredentials", (), {}
        )
        sys.modules["fastapi.security"] = sec_mod


# Ejecutar al import time (antes de que cualquier test importe app.*)
_ensure_optional_deps()


# ── Path manipulation: añadir raíz del proyecto al sys.path ──
import pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
