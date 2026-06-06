"""
Endpoints del ciclo de vida de cálculo.

POST /api/calculo/iniciar          → encola un trabajo en el WorkerPool
GET  /api/calculo/progreso/{id}    → polling clásico (compat frontend legacy)
GET  /api/calculo/stream/{id}      → Server-Sent Events streaming (nuevo, sesión 2)
GET  /api/calculo/resultado/{id}   → resultado final
"""

import asyncio
import json
import logging
import time
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from app.api.schemas.calculo import SolicitudCalculo, IniciarCalculoResponse
from app.infrastructure.auth.jwt_auth import verificar_token
from app.services.calculation.worker_pool import get_worker_pool, JobCalculo
from app.services.calculation.trabajos_repo import get_trabajos_repo

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/calculo", tags=["calculo"])


# Lista de algoritmos visibles para el cliente en el panel de progreso.
ALGORITMOS_VISIBLES = [
    "Entropía", "Hot/Cold Bias", "Covarianza",
    "LSTM", "Transformer", "Markov",
    "Bayesiano", "XGBoost", "Reinforcement Learning",
    "Monte Carlo", "Algoritmo Genético (NSGA-II)",
    "FFT Periodicidad", "Isolation Forest",
    "Walk-Forward", "Caché Inteligente",
    "Ensemble Stacking",
]


# ─────────────────────────────────────────────────────────
# POST /iniciar
# ─────────────────────────────────────────────────────────


@router.post("/iniciar", response_model=IniciarCalculoResponse)
async def iniciar_calculo(
    solicitud: SolicitudCalculo,
    payload: dict = Depends(verificar_token),
):
    """
    Arranca un cálculo nuevo: lo persiste como 'iniciando' y lo encola en
    el WorkerPool. La ejecución es asíncrona; usar polling o SSE para
    seguir el progreso.

    Errores:
      503 — cola saturada (demasiados cálculos pendientes)
    """
    repo = await get_trabajos_repo()
    pool = await get_worker_pool()

    trabajo_id = str(uuid.uuid4())
    trabajo = await repo.crear(
        trabajo_id=trabajo_id,
        cantidad=solicitud.cantidad,
        presupuesto_eur=solicitud.presupuesto_eur,
        bote_acumulado_eur=solicitud.bote_acumulado_eur,
        loteria=solicitud.loteria,
    )
    trabajo.estado_algoritmos = {alg: "pendiente" for alg in ALGORITMOS_VISIBLES}
    await repo.guardar(trabajo)

    job = JobCalculo(
        trabajo_id=trabajo_id,
        cantidad=solicitud.cantidad,
        presupuesto_eur=solicitud.presupuesto_eur,
        bote_acumulado_eur=solicitud.bote_acumulado_eur,
        loteria=solicitud.loteria,
        encolado_en=time.time(),
    )
    try:
        await pool.enqueue(job)
    except asyncio.QueueFull:
        trabajo.estado = "error"
        trabajo.mensaje = "Cola saturada — vuelve a intentarlo en unos minutos"
        await repo.guardar(trabajo)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Demasiados cálculos en cola, reintenta en unos minutos",
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )

    return IniciarCalculoResponse(
        trabajo_id=trabajo_id,
        estado="encolado",
        mensaje=f"Encolado (posición ~{pool.n_pendientes}, en ejecución {pool.n_ejecutando})",
    )


# ─────────────────────────────────────────────────────────
# GET /progreso/{id}  — polling clásico (compat)
# ─────────────────────────────────────────────────────────


@router.get("/progreso/{trabajo_id}")
async def obtener_progreso(
    trabajo_id: str,
    payload: dict = Depends(verificar_token),
):
    """
    Polling clásico. Mantenido para compatibilidad con el frontend Flutter
    actual. Sesión 3 lo migrará a SSE.
    """
    repo = await get_trabajos_repo()
    trabajo = await repo.obtener(trabajo_id)
    if trabajo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trabajo no encontrado",
        )
    return {
        "estado": trabajo.estado,
        "progresoGeneral": trabajo.progreso,
        "indiceConfianza": trabajo.indice_confianza,
        "iteracion": trabajo.iteracion,
        "convergiendo": trabajo.convergiendo,
        "estadoAlgoritmos": trabajo.estado_algoritmos,
        "mejoras_activas": trabajo.mejoras_activas,
        "mensaje": trabajo.mensaje or "",
    }


# ─────────────────────────────────────────────────────────
# GET /stream/{id}  — Server-Sent Events
# ─────────────────────────────────────────────────────────


# Configuración del stream SSE:
#   - Ping cada 15s para mantener viva la conexión (proxies pueden cortar a 30-60s)
#   - Lectura del estado cada 1s (más rápido que el polling de 3s del legacy)
#   - Auto-cierre cuando el trabajo termine (completado o error)
#   - Timeout duro a 1h para que no se queden colgadas conexiones zombi

SSE_INTERVALO_LECTURA_S = 1.0
SSE_INTERVALO_PING_S = 15.0
SSE_TIMEOUT_TOTAL_S = 3600.0


async def _generador_sse(trabajo_id: str):
    """
    Generador async que produce eventos SSE.

    Formato SSE:
      event: <tipo>\n
      data: <json>\n
      \n
    """
    repo = await get_trabajos_repo()
    inicio = time.time()
    ultimo_ping = inicio
    ultimo_payload_hash: int = -1

    # Verificar existencia antes de empezar el stream
    if not await repo.existe(trabajo_id):
        yield f"event: error\ndata: {json.dumps({'error': 'Trabajo no encontrado'})}\n\n"
        return

    while True:
        # Timeout total
        if time.time() - inicio > SSE_TIMEOUT_TOTAL_S:
            yield f"event: timeout\ndata: {json.dumps({'razon': 'timeout_servidor'})}\n\n"
            return

        trabajo = await repo.obtener(trabajo_id)
        if trabajo is None:
            yield f"event: error\ndata: {json.dumps({'error': 'Trabajo desapareció'})}\n\n"
            return

        # Construir payload
        payload = {
            "estado": trabajo.estado,
            "progresoGeneral": trabajo.progreso,
            "indiceConfianza": trabajo.indice_confianza,
            "iteracion": trabajo.iteracion,
            "convergiendo": trabajo.convergiendo,
            "estadoAlgoritmos": trabajo.estado_algoritmos,
            "mensaje": trabajo.mensaje or "",
        }
        # Solo enviar si hay cambio (evita spam de eventos idénticos)
        payload_hash = hash(json.dumps(payload, sort_keys=True, default=str))
        if payload_hash != ultimo_payload_hash:
            yield f"event: progreso\ndata: {json.dumps(payload)}\n\n"
            ultimo_payload_hash = payload_hash
            ultimo_ping = time.time()

        # Si terminó, enviar evento final y cerrar
        if trabajo.terminado:
            if trabajo.estado == "completado":
                evento_final = {
                    "estado": "completado",
                    "n_combinaciones": len(trabajo.combinaciones),
                    "n_apuestas_bl": len(trabajo.bloque_l_apuestas),
                }
                yield f"event: completado\ndata: {json.dumps(evento_final)}\n\n"
            else:
                yield f"event: error\ndata: {json.dumps({'error': trabajo.mensaje or 'desconocido'})}\n\n"
            return

        # Ping keepalive
        ahora = time.time()
        if ahora - ultimo_ping >= SSE_INTERVALO_PING_S:
            yield f": ping {int(ahora)}\n\n"   # comentario SSE = keepalive
            ultimo_ping = ahora

        await asyncio.sleep(SSE_INTERVALO_LECTURA_S)


@router.get("/stream/{trabajo_id}")
async def stream_progreso(
    trabajo_id: str,
    payload: dict = Depends(verificar_token),
):
    """
    Server-Sent Events: streaming de progreso sin polling.

    El cliente abre la conexión y recibe eventos `progreso`, `completado`,
    `error` o `timeout` hasta que el cálculo termine o la conexión se cierre.

    Mantenido junto a /progreso (polling) hasta Sesión 3, cuando el
    frontend migre a este endpoint.
    """
    repo = await get_trabajos_repo()
    if not await repo.existe(trabajo_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trabajo no encontrado",
        )
    return StreamingResponse(
        _generador_sse(trabajo_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # nginx: desactivar buffering
            "Connection": "keep-alive",
        },
    )


# ─────────────────────────────────────────────────────────
# GET /resultado/{id}
# ─────────────────────────────────────────────────────────


@router.get("/resultado/{trabajo_id}")
async def obtener_resultado(
    trabajo_id: str,
    payload: dict = Depends(verificar_token),
):
    """Devuelve el resultado completo de un cálculo terminado."""
    repo = await get_trabajos_repo()
    trabajo = await repo.obtener(trabajo_id)
    if trabajo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trabajo no encontrado",
        )
    if trabajo.estado != "completado":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cálculo no completado (estado: {trabajo.estado})",
        )

    return {
        "combinaciones": trabajo.combinaciones,
        "mejoras_activas": trabajo.mejoras_activas,
        "bloque_l": {
            "sistema_reducido": trabajo.bloque_l_sistema,
            "apuestas_garantizadas": trabajo.bloque_l_apuestas,
            "coste_total_eur": trabajo.bloque_l_coste_eur,
            "recomendacion": trabajo.bloque_l_recomendacion,
            "analisis_roi": trabajo.bloque_l_roi,
            "confianza_agregada": trabajo.bloque_l_confianza,
            "estrategia_completa": trabajo.bloque_l_estrategia_completa,
        },
        "cobertura_garantizada": trabajo.cobertura_garantizada,
        "apuestas_multiples": trabajo.apuestas_multiples,
    }


# ─────────────────────────────────────────────────────────
# GET /estado-cola
# ─────────────────────────────────────────────────────────


@router.get("/estado-cola")
async def estado_cola(payload: dict = Depends(verificar_token)):
    """Estado del WorkerPool: capacidad, jobs pendientes, jobs en ejecución."""
    pool = await get_worker_pool()
    return {
        "n_workers": pool.n_workers,
        "n_pendientes": pool.n_pendientes,
        "n_ejecutando": pool.n_ejecutando,
    }
