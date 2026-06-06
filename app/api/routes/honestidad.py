"""
Endpoints del Dashboard de Honestidad.

POST /api/honestidad/apuesta          → registra una apuesta real
POST /api/honestidad/prediccion       → registra una predicción del sistema
POST /api/honestidad/evaluar-sorteo   → evalúa pendientes contra un resultado
GET  /api/honestidad/estadisticas     → snapshot completo de KPIs
GET  /api/honestidad/ev               → EV de una apuesta dado el bote
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator

from app.infrastructure.auth.jwt_auth import verificar_token
from app.services.honestidad.servicio_honestidad import get_servicio_honestidad
from app.domain import honestidad_math as hm

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/honestidad", tags=["honestidad"])


# ── Schemas


class RegistrarApuestaRequest(BaseModel):
    numeros: List[int] = Field(..., min_length=6, max_length=6)
    coste_eur: float = Field(default=0.5, ge=0.0)
    origen: str = "manual"
    fecha: Optional[str] = None

    @field_validator("numeros")
    @classmethod
    def numeros_validos(cls, v):
        if len(set(v)) != 6:
            raise ValueError("Deben ser 6 números únicos")
        if not all(1 <= n <= 49 for n in v):
            raise ValueError("Números en [1,49]")
        return sorted(v)


class RegistrarPrediccionRequest(BaseModel):
    trabajo_id: str
    numeros: List[int] = Field(..., min_length=6, max_length=6)
    confianza: float = Field(default=0.0, ge=0.0, le=100.0)


class EvaluarSorteoRequest(BaseModel):
    sorteo_fecha: str
    numeros_ganadores: List[int] = Field(..., min_length=6, max_length=6)
    complementario: Optional[int] = Field(default=None, ge=1, le=49)
    # Premios opcionales para precisión
    premio_6: Optional[float] = None
    premio_5: Optional[float] = None
    premio_4: Optional[float] = None
    premio_3: Optional[float] = None


# ── Endpoints


@router.post("/apuesta")
async def registrar_apuesta(
    req: RegistrarApuestaRequest,
    payload: dict = Depends(verificar_token),
):
    """Registra una apuesta real que el usuario va a jugar."""
    servicio = get_servicio_honestidad()
    ap = await servicio.registrar_apuesta(
        numeros=req.numeros,
        coste_eur=req.coste_eur,
        origen=req.origen,
        fecha=req.fecha,
    )
    return {"id": ap.id, "registrada": True}


@router.post("/prediccion")
async def registrar_prediccion(
    req: RegistrarPrediccionRequest,
    payload: dict = Depends(verificar_token),
):
    """Registra una predicción del sistema (para el backtest honesto)."""
    servicio = get_servicio_honestidad()
    pred = await servicio.registrar_prediccion(
        trabajo_id=req.trabajo_id,
        numeros=req.numeros,
        confianza=req.confianza,
    )
    return {"id": pred.id, "registrada": True}


@router.post("/evaluar-sorteo")
async def evaluar_sorteo(
    req: EvaluarSorteoRequest,
    payload: dict = Depends(verificar_token),
):
    """Evalúa apuestas y predicciones pendientes contra un resultado real."""
    if len(set(req.numeros_ganadores)) != 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="numeros_ganadores debe tener 6 valores únicos",
        )
    if not all(1 <= n <= 49 for n in req.numeros_ganadores):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="numeros_ganadores deben estar en el rango [1, 49]",
        )
    servicio = get_servicio_honestidad()
    # Tabla de premios con overrides si vienen
    tabla = hm.TablaPremios()
    if req.premio_6 is not None:
        tabla.premio_6 = req.premio_6
    if req.premio_5 is not None:
        tabla.premio_5 = req.premio_5
    if req.premio_4 is not None:
        tabla.premio_4 = req.premio_4
    if req.premio_3 is not None:
        tabla.premio_3 = req.premio_3

    resultado = await servicio.evaluar_sorteo(
        sorteo_fecha=req.sorteo_fecha,
        numeros_ganadores=req.numeros_ganadores,
        tabla_premios=tabla,
        complementario=req.complementario,
    )
    return resultado


@router.get("/estadisticas")
async def obtener_estadisticas(
    bote_eur: float = Query(default=400_000.0, ge=0),
    payload: dict = Depends(verificar_token),
):
    """Snapshot completo de KPIs honestos."""
    servicio = get_servicio_honestidad()
    stats = await servicio.calcular_estadisticas(bote_actual_eur=bote_eur)
    return stats.to_dict()


@router.get("/ev")
async def calcular_ev(
    bote_eur: float = Query(default=400_000.0, ge=0),
    payload: dict = Depends(verificar_token),
):
    """EV de una apuesta dado el bote. Educativo: casi siempre negativo."""
    ev = hm.ev_con_bote(bote_eur)
    return {
        "ev_eur": round(ev.ev_por_apuesta_eur, 4),
        "ev_porcentaje": round(ev.ev_porcentaje * 100, 1),
        "coste_apuesta_eur": ev.coste_apuesta_eur,
        "retorno_esperado_eur": round(ev.retorno_esperado_eur, 4),
        "perdida_esperada_eur": round(ev.perdida_esperada_eur, 4),
        "es_favorable": ev.es_favorable,
        "probabilidad_jackpot": f"1 entre {hm.TOTAL_COMBINACIONES:,}",
        "mensaje": (
            "Favorable en teoría por el bote, pero la probabilidad de "
            "acertar 6 sigue siendo 1 entre 14 millones."
            if ev.es_favorable else
            "Valor esperado negativo: en promedio se pierde dinero. "
            "Esto es estructural de la lotería, ningún sistema lo cambia."
        ),
    }
