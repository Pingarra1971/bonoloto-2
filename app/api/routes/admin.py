"""
Endpoints de autenticación y administración.

POST /api/auth/token            → genera JWT a partir del secret compartido
GET  /api/health                → healthcheck profundo
POST /api/modelos/reentrenar    → registra un sorteo real e invalida cachés
GET  /api/algoritmos/rendimiento → pesos actuales del stacking
GET  /api/mejoras/estado        → estado de las 6 mejoras
"""

import hmac
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Body, status
from pydantic import BaseModel

from app.config import get_settings
from app.infrastructure.auth.jwt_auth import verificar_token, generar_token
from app.infrastructure.database import BaseDatos
from app.services.calculation.trabajos_repo import get_trabajos_repo
from app.domain.motor_ia import MotorIA
from app.domain.motor_mejorado import _cache_global, EnsembleStacking
from app.api.schemas.calculo import ResultadoSorteoEntrada, HealthResponse
from app import __version__

logger = logging.getLogger(__name__)

router_auth = APIRouter(prefix="/api/auth", tags=["auth"])
router_health = APIRouter(prefix="/api", tags=["health"])
router_admin = APIRouter(prefix="/api", tags=["admin"])


# ─────────────────────────────────────────────────────────
# AUTH
# ─────────────────────────────────────────────────────────


class GenerarTokenRequest(BaseModel):
    secret: str


@router_auth.post("/token")
async def generar_token_endpoint(req: GenerarTokenRequest = Body(...)):
    """
    Genera un JWT válido 30 días si el secret coincide con el del entorno.

    Comparación timing-safe vía hmac.compare_digest para evitar
    side-channel attacks.
    """
    settings = get_settings()
    if not hmac.compare_digest(req.secret.encode(), settings.jwt_secret.encode()):
        # Log warning sin revelar detalles
        logger.warning("Intento de generar token con secret inválido")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Secret inválido",
        )
    token = generar_token(
        payload={"sub": "bonoloto-app"},
        horas_validez=24 * 30,
    )
    return {"token": token, "expira_en_dias": 30}


# ─────────────────────────────────────────────────────────
# HEALTHCHECK
# ─────────────────────────────────────────────────────────


@router_health.get("/health", response_model=HealthResponse)
async def health():
    """Estado del servidor. Endpoint público (sin autenticación)."""
    repo = await get_trabajos_repo()
    activos = await repo.listar_activos()
    return HealthResponse(
        version=__version__,
        estado="ok",
        bd_conectada=BaseDatos._pool is not None,
        trabajos_activos=len(activos),
    )


@router_health.get("/metrics")
async def metrics():
    """Métricas operativas (JSON). Público para monitorización."""
    from app.infrastructure.observabilidad import metricas as m
    repo = await get_trabajos_repo()
    activos = await repo.listar_activos()
    snap = m.snapshot()
    snap["trabajos_activos_ahora"] = len(activos)
    snap["bd_conectada"] = BaseDatos._pool is not None
    return snap


# ─────────────────────────────────────────────────────────
# REENTRENAMIENTO
# ─────────────────────────────────────────────────────────


@router_admin.post("/modelos/reentrenar")
async def reentrenar_modelos(
    resultado: ResultadoSorteoEntrada,
    payload: dict = Depends(verificar_token),
):
    """
    Registra un sorteo real e invalida el caché global de scores.

    Esto fuerza recálculo en la siguiente petición con datos actualizados.
    El reentrenamiento real (pesos del stacking) ocurre durante el próximo
    cálculo cuando se procesan los walk-forward windows.
    """
    try:
        from datetime import datetime
        fecha = datetime.fromisoformat(resultado.fecha)
        await BaseDatos.insertar_sorteo(
            fecha=fecha,
            numeros=resultado.numeros,
            complementario=resultado.complementario,
            reintegro=resultado.reintegro,
            bote=resultado.bote,
        )
        _cache_global.invalidar()
        logger.info("Sorteo guardado y caché invalidada: %s", resultado.numeros)
        return {"estado": "reentrenamiento_iniciado", "cache_invalidada": True}
    except Exception as e:
        logger.error("Error reentrenando: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error reentrenando: {e}",
        )


# ─────────────────────────────────────────────────────────
# ESTADO DE ALGORITMOS Y MEJORAS
# ─────────────────────────────────────────────────────────


_NOMBRES_DISPLAY = {
    "entropia": "Entropía",
    "hot_cold_bias": "Hot/Cold Bias",
    "covarianza": "Covarianza",
    "fft": "FFT Periodicidad ⭐",
    "lstm": "LSTM",
    "transformer": "Transformer",
    "markov": "Markov",
    "bayesiano": "Bayesiano",
    "xgboost": "XGBoost",
    "reinforcement_learning": "Reinforcement Learning",
    "monte_carlo": "Monte Carlo",
    "algoritmo_genetico": "Algoritmo Genético (NSGA-II) ⭐",
}


@router_admin.get("/algoritmos/rendimiento")
async def obtener_rendimiento(payload: dict = Depends(verificar_token)):
    """Devuelve los pesos actuales del stacking."""
    sorteos = await BaseDatos.obtener_sorteos(limite=500)
    if not sorteos:
        from app.domain.fixtures import sorteos_simulados
        sorteos = sorteos_simulados(n=200)

    motor = MotorIA(sorteos)
    stacking = EnsembleStacking()

    todos_pesos = dict(motor.pesos)
    todos_pesos["fft"] = stacking.meta_pesos.get("fft", 0.085)

    algoritmos = [
        {
            "nombre": _NOMBRES_DISPLAY.get(alg, alg),
            "peso_actual": stacking.meta_pesos.get(alg, peso),
            "tasa_aciertos": 0.0,
            "total_predicciones": 0,
            "historial_pesos": [peso],
        }
        for alg, peso in todos_pesos.items()
    ]

    estado_st = stacking.estado()
    return {
        "algoritmos": algoritmos,
        "stacking_lider": estado_st.get("algoritmo_lider"),
        "n_actualizaciones_stacking": stacking.n_actualizaciones,
    }


class _SorteoNuevo(BaseModel):
    fecha: str
    numeros: list
    complementario: int = 0
    reintegro: int = 0
    bote: int = 0


@router_admin.get("/memoria/estado")
async def memoria_estado(payload: dict = Depends(verificar_token)):
    """Estado de la memoria de sorteos: cuántos hay y el más reciente."""
    from app.services.memoria.servicio_memoria import ServicioMemoriaSorteos
    servicio = ServicioMemoriaSorteos(BaseDatos)
    return await servicio.estado()


@router_admin.post("/memoria/sorteo")
async def memoria_registrar_sorteo(
    req: _SorteoNuevo,
    payload: dict = Depends(verificar_token),
):
    """
    Registra un sorteo nuevo en la memoria (idempotente). Llamar tras cada
    sorteo oficial para mantener la memoria actualizada.
    """
    from datetime import datetime
    from app.services.memoria.servicio_memoria import ServicioMemoriaSorteos

    if len(req.numeros) != 6 or len(set(req.numeros)) != 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="numeros debe tener 6 valores únicos",
        )
    if not all(1 <= n <= 49 for n in req.numeros):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="numeros deben estar en [1, 49]",
        )
    try:
        fecha = datetime.fromisoformat(req.fecha)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="fecha debe estar en formato ISO (YYYY-MM-DD)",
        )
    servicio = ServicioMemoriaSorteos(BaseDatos)
    ok = await servicio.registrar_sorteo_nuevo(
        fecha, req.numeros, req.complementario, req.reintegro, req.bote
    )
    estado = await servicio.estado()
    return {"registrado": ok, "memoria": estado}


@router_admin.post("/memoria/backfill")
async def memoria_backfill(
    sorteos: list = Body(...),
    payload: dict = Depends(verificar_token),
):
    """
    Carga masiva del histórico completo (idempotente). Cada elemento:
    {fecha, numeros, complementario, reintegro, bote}.
    """
    from datetime import datetime
    from app.services.memoria.servicio_memoria import ServicioMemoriaSorteos

    procesados = []
    for s in sorteos:
        try:
            s = dict(s)
            s["fecha"] = datetime.fromisoformat(s["fecha"])
            procesados.append(s)
        except (ValueError, KeyError, TypeError):
            continue  # saltar registros mal formados sin romper el lote
    servicio = ServicioMemoriaSorteos(BaseDatos)
    n = await servicio.backfill_completo(procesados)
    estado = await servicio.estado()
    return {"procesados": n, "recibidos": len(sorteos), "memoria": estado}


@router_admin.get("/estadisticas/numeros")
async def estadisticas_numeros(payload: dict = Depends(verificar_token)):
    """
    Frecuencias por número (1-49) sobre el histórico, con cortes a últimos
    50/100/500 y total. Alimenta la pantalla de estadísticas del frontend
    (que esperaba estos datos y antes nunca los recibía — bug #152).
    """
    sorteos = await BaseDatos.obtener_sorteos(limite=1000)
    if not sorteos:
        from app.domain.fixtures import sorteos_simulados
        sorteos = sorteos_simulados(n=500)

    # sorteos viene ordenado por fecha DESC (más reciente primero)
    combos = [s["numeros"] for s in sorteos]

    def _freq(lista_combos):
        cont = {n: 0 for n in range(1, 50)}
        for c in lista_combos:
            for n in c:
                if 1 <= n <= 49:
                    cont[n] += 1
        return cont

    freq_total = _freq(combos)
    freq_50 = _freq(combos[:50])
    freq_100 = _freq(combos[:100])
    freq_500 = _freq(combos[:500])

    # Última aparición (índice del sorteo más reciente donde salió; 0 = más reciente)
    ultima_aparicion = {}
    for idx, c in enumerate(combos):
        for n in c:
            if n not in ultima_aparicion:
                ultima_aparicion[n] = idx

    # Clasificación caliente/frío por frecuencia en últimos 100
    valores_100 = sorted(freq_100.values())
    if valores_100:
        umbral_alto = valores_100[min(len(valores_100) - 1, int(len(valores_100) * 0.7))]
        umbral_bajo = valores_100[int(len(valores_100) * 0.3)]
    else:
        umbral_alto = umbral_bajo = 0

    numeros = []
    for n in range(1, 50):
        f100 = freq_100[n]
        if f100 >= umbral_alto and umbral_alto > 0:
            clasif = "caliente"
        elif f100 <= umbral_bajo:
            clasif = "frio"
        else:
            clasif = "neutro"
        numeros.append({
            "numero": n,
            "frecuencia_total": freq_total[n],
            "frecuencia_ultimos_50": freq_50[n],
            "frecuencia_ultimos_100": freq_100[n],
            "frecuencia_ultimos_500": freq_500[n],
            "ultima_aparicion_hace": ultima_aparicion.get(n),
            "clasificacion": clasif,
        })

    return {"numeros": numeros, "n_sorteos": len(combos)}


@router_admin.get("/mejoras/estado")
async def estado_mejoras(payload: dict = Depends(verificar_token)):
    """Estado de las 6 mejoras estructurales (FFT, IF, WF, Caché, NSGA-II, Stacking)."""
    stacking = EnsembleStacking()
    estado_st = stacking.estado()
    return {
        "mejora_1_fft": {
            "nombre": "Detección de ciclos FFT",
            "estado": "activa",
            "descripcion": "Transformada de Fourier sobre series temporales de cada número",
        },
        "mejora_2_isolation_forest": {
            "nombre": "Isolation Forest",
            "estado": "activa",
            "descripcion": "Detección y filtrado de sorteos estadísticamente anómalos",
        },
        "mejora_3_walk_forward": {
            "nombre": "Walk-Forward Validation",
            "estado": "activa",
            "descripcion": "Validación cruzada temporal con 5 ventanas",
        },
        "mejora_4_cache": {
            "nombre": "Caché Inteligente",
            "estado": "activa",
            "descripcion": "Reutilización de scores sin cambios en el histórico",
            "stats": _cache_global.stats(),
        },
        "mejora_5_nsga2": {
            "nombre": "NSGA-II Multi-objetivo",
            "estado": "activa",
            "descripcion": "Optimización simultánea de 4 objetivos con frontera de Pareto",
        },
        "mejora_6_stacking": {
            "nombre": "Ensemble Stacking v2",
            "estado": "activa",
            "descripcion": "Meta-modelo de regresión con SGD + Ridge",
            "algoritmo_lider": estado_st.get("algoritmo_lider", "n/a"),
            "n_actualizaciones": stacking.n_actualizaciones,
        },
    }
