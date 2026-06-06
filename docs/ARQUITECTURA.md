# Arquitectura Bonoloto 2.0

## Resumen ejecutivo

El proyecto pasó de **1300 líneas de `main.py` monolítico** a **11 módulos especializados** organizados en capas. El acoplamiento circular `pipeline_v4 → main → MotorIA` está roto. El backend ahora es importable, testeable y mantenible.

## Estructura de carpetas

```
bonoloto_2/
├── app/
│   ├── __init__.py              versión, docstring
│   ├── main.py                  entrypoint FastAPI (89 líneas)
│   ├── config.py                Settings centralizado, validación de env vars
│   │
│   ├── api/
│   │   ├── routes/              endpoints HTTP agrupados por dominio
│   │   │   ├── calculo.py       /api/calculo/{iniciar,progreso,resultado}
│   │   │   ├── bloque_l.py      /api/bloque-l/*
│   │   │   └── admin.py         /api/{health,auth,modelos,algoritmos,mejoras}
│   │   ├── schemas/             Pydantic v2 request/response
│   │   │   └── calculo.py
│   │   └── dependencies/        deps de FastAPI (vacío por ahora)
│   │
│   ├── domain/                  lógica pura, sin frameworks
│   │   ├── motor_ia.py          11 algoritmos base (extraído de main.py)
│   │   ├── motor_mejorado.py    NSGA-II, stacking, walk-forward
│   │   ├── diagnostico.py       diagnóstico previo del cálculo
│   │   ├── fixtures.py          sorteos simulados para dev/test
│   │   └── algorithms/          110 algoritmos por bloques
│   │       ├── level1.py        bloques A-D (entropía, gaps, GRU, ...)
│   │       ├── level2.py        bloques E-F (cópulas, EVT, Hawkes, ...)
│   │       ├── advanced.py      MaxEnt, NBEATS, Shapley
│   │       ├── block_i.py       LNN, TDA, SAX, MDL, ...
│   │       ├── block_j.py       SSA, VMD, BOCPD, EMD, ...
│   │       ├── block_k.py       NG-RC, DMD, KAN, RBM, SOM, HDC, ...
│   │       └── block_l.py       sistemas reducidos, anti-popularidad, ROI
│   │
│   ├── services/                orquestación de dominio
│   │   ├── pipeline/
│   │   │   └── pipeline_v4.py   pipeline de cálculo principal
│   │   ├── calculation/
│   │   │   ├── trabajos_repo.py repositorio in-memory (→ Redis en Sesión 2)
│   │   │   └── servicio_calculo.py orquestador del pipeline
│   │   └── calibration/         (Sesión 6: framework de backtest)
│   │
│   └── infrastructure/          adaptadores externos
│       ├── auth/
│       │   └── jwt_auth.py      generar/verificar JWT
│       ├── database/
│       │   └── oracle.py        pool async a Oracle ATP
│       ├── scheduler/
│       │   └── watchdog.py      APScheduler para actualización post-sorteo
│       └── storage/             (Sesión 4: backup a Object Storage)
│
├── tests/
│   ├── conftest.py              stubs para fastapi/jwt/oracledb/pydantic
│   ├── unit/
│   │   ├── test_motor_ia.py     12 tests del motor extraído
│   │   ├── test_trabajos_repo.py 6 tests del repo
│   │   └── test_config.py       5 tests de Settings
│   └── integration/             (Sesión 2: tests con TestClient)
│
├── install/
│   ├── bonoloto-2.service       systemd unit actualizado
│   └── bonoloto-watchdog.service
│
├── docs/
│   └── ARQUITECTURA.md          este archivo
│
├── requirements.txt             runtime deps
├── requirements-dev.txt         dev deps (pytest, ruff, mypy)
└── pytest.ini                   configuración de pytest
```

## Cambios clave respecto a v7.0

### 1. Acoplamiento circular roto

**Antes:**
```python
# pipeline_v4.py
def _calcular_algoritmos_core(...):
    from main import MotorIA   # ← import diferido para evitar circular
    motor = MotorIA(...)
```

Esto forzaba que tests del pipeline necesitaran toda la cadena (fastapi, jwt, oracledb).

**Ahora:**
```python
# pipeline_v4.py
from app.domain.motor_ia import MotorIA  # ← import limpio al top

class PipelineV4:
    ...
```

`MotorIA` vive en su propio módulo `app/domain/motor_ia.py` (552 líneas autocontenidas). Tests pueden importar MotorIA sin levantar nada más.

### 2. Configuración centralizada

**Antes:** `os.getenv(...)` esparcido en main.py con defaults inseguros (p.ej. `JWT_SECRET="bonoloto-ai-secret-key-oracle-cloud"` — secreto público en el repo).

**Ahora:** `app/config.py` con dataclass `Settings`. Si `JWT_SECRET` no está definido, se genera uno aleatorio efímero con warning explícito. Esto es preferible a un secreto público.

### 3. Estado de trabajos abstraído

**Antes:** dict global `trabajos: Dict[str, dict]` en main.py, mutado desde múltiples sitios.

**Ahora:** `TrabajosRepo` clase con interfaz limpia (`crear`, `obtener`, `existe`, `activos`). Cap FIFO documentado. Misma implementación in-memory hoy, pero la interfaz permite swap a Redis en Sesión 2 sin tocar el resto del código.

### 4. Servicio de cálculo testeable

**Antes:** función global `ejecutar_calculo(trabajo_id, cantidad, ...)` que accedía a `trabajos` global y `BaseDatos.obtener_sorteos()` directamente.

**Ahora:** clase `ServicioCalculo(repo, bd)` con dependencias inyectadas. Mockear `repo` y `bd` permite tests sin BD real.

### 5. Routers separados por dominio

**Antes:** todos los endpoints (~14) en main.py mezclados.

**Ahora:**
- `app/api/routes/calculo.py` — lifecycle de cálculo
- `app/api/routes/bloque_l.py` — endpoints estratégicos
- `app/api/routes/admin.py` — auth, health, reentrenamiento, estado

main.py se reduce a 89 líneas de wiring puro.

### 6. Bug latente corregido al pasar

`BaseDatos` en v7.0 usaba `oracledb.create_pool` (sync) dentro de funciones async, y `with self._pool.acquire()` (sync). Resultado: **cada query bloquea el event loop**. Bajo carga, esto serializa todas las peticiones HTTP.

`app/infrastructure/database/oracle.py` ahora usa `oracledb.create_pool_async` y `async with`. Esto se documentará como Bug #126 en el changelog general.

### 7. Tests sin dependencias externas

`tests/conftest.py` stub-ea fastapi/jwt/oracledb/pydantic si no están instalados. Permite ejecutar tests unitarios en cualquier entorno básico (3 archivos × 23 tests, todos pasan).

## Camino hacia v2.1 (Sesiones siguientes)

| Sesión | Foco | Estado |
|---|---|---|
| 1 | Refactor estructural, MotorIA extraído | ✅ COMPLETA |
| 2 | Task queue (Dramatiq + Redis), persistencia trabajos en BD, SSE | pendiente |
| 3 | Migración Flutter a Riverpod + freezed + dio | pendiente |
| 4 | Dashboard de honestidad (P&L tracker, backtest) | pendiente |
| 5 | Bloque L reforzado (anti-popularidad calibrada, sistemas verificados) | pendiente |
| 6 | Poda de algoritmos, framework de backtest serio | pendiente |
| 7-8 | Observabilidad, CI/CD, revisión final de bugs | pendiente |

## Comandos útiles

```bash
# Arrancar servidor en dev (desde la raíz del proyecto)
uvicorn app.main:app --reload

# Tests unitarios
pytest tests/unit/ -v

# Tests con cobertura
pytest --cov=app --cov-report=term-missing

# Lint
ruff check app/
black --check app/
mypy app/
```
