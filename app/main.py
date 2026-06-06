"""
Bonoloto 2.0 — entrypoint FastAPI.

Sesión 2 añadió:
  - WorkerPool en el lifespan (arranque + parada limpia)
  - Endpoint SSE /api/calculo/stream/{id}
  - Persistencia de trabajos en BD (Oracle write-through)
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.config import get_settings
from app.infrastructure.database import BaseDatos
from app.services.calculation.worker_pool import get_worker_pool
from app.api.routes.calculo import router as router_calculo
from app.api.routes.bloque_l import router as router_bloque_l
from app.api.routes.honestidad import router as router_honestidad
from app.api.routes.admin import router_auth, router_health, router_admin

_settings = get_settings()
logging.basicConfig(
    level=getattr(logging, _settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ciclo de vida: arranque y apagado limpio."""
    logger.info("Bonoloto 2.0 v%s arrancando...", __version__)
    settings = get_settings()

    # 1. BD
    bd_ok = await BaseDatos.inicializar(settings)
    if bd_ok:
        logger.info("BD Oracle conectada")
    else:
        logger.warning("BD no disponible — operando en modo degradado (in-memory)")

    # 2. WorkerPool (rehidrata huérfanos internamente)
    pool = await get_worker_pool()
    await pool.iniciar()

    yield

    # Apagado
    logger.info("Bonoloto 2.0 apagándose...")
    await pool.detener(timeout=5.0)
    await BaseDatos.cerrar()


app = FastAPI(
    title="Bonoloto 2.0",
    version=__version__,
    description=(
        "Sistema cuantitativo de análisis aplicado a la Bonoloto. "
        "Las combinaciones generadas NO aumentan la probabilidad de acertar "
        "(matemáticamente imposible en un sorteo uniforme independiente). "
        "El sistema sí optimiza varianza vía anti-popularidad y sistemas reducidos "
        "con garantías combinatorias."
    ),
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(router_health)
app.include_router(router_auth)
app.include_router(router_calculo)
app.include_router(router_bloque_l)
app.include_router(router_honestidad)
app.include_router(router_admin)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=_settings.host,
        port=_settings.port,
        workers=1,
        reload=False,
    )
