"""
Endpoints estratégicos del Bloque L.

Aquí vive la única parte del proyecto con valor matemático real:
  - Sistemas reducidos con garantías combinatorias verificadas
  - Análisis de popularidad (anti-popularidad para reducir reparto si toca)
  - ROI bote-aware
  - Multi-loteria comparativa
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Body, Query, status
from pydantic import BaseModel, Field

from app.domain.algorithms.block_l import (
    SistemaReducido,
    BoteAwareROI,
    AntiPopularityScorer,
    MultiLoteria,
)
from app.infrastructure.auth.jwt_auth import verificar_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/bloque-l", tags=["bloque-l"])


# ── Pydantic schemas locales (no merece la pena moverlos a schemas/ aún)


class AplicarSistemaRequest(BaseModel):
    sistema: str
    numeros: List[int] = Field(..., min_length=6, max_length=20)


class AnalizarPopularidadRequest(BaseModel):
    combinacion: List[int] = Field(..., min_length=1, max_length=6)


# ── Endpoints


@router.get("/sistemas-reducidos")
async def listar_sistemas_reducidos(payload: dict = Depends(verificar_token)):
    """Lista todos los sistemas reducidos disponibles con sus garantías."""
    return {"sistemas": SistemaReducido.listar_sistemas()}


@router.post("/aplicar-sistema")
async def aplicar_sistema_reducido(
    req: AplicarSistemaRequest,
    payload: dict = Depends(verificar_token),
):
    """Aplica un sistema reducido a una lista de números seleccionados."""
    try:
        apuestas = SistemaReducido.aplicar_sistema(req.sistema, req.numeros)
        sis_info = SistemaReducido.SISTEMAS[req.sistema]
        return {
            "sistema": req.sistema,
            "numeros_input": sorted(req.numeros),
            "apuestas": apuestas,
            "n_apuestas": len(apuestas),
            "coste_eur": len(apuestas) * 0.50,
            "garantias": sis_info["garantias"],
        }
    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/roi")
async def calcular_roi(
    bote_eur: float = Query(default=600_000.0, ge=0),
    payload: dict = Depends(verificar_token),
):
    """Calcula EV y recomendación según el bote acumulado."""
    try:
        roi = BoteAwareROI()
        return roi.recomendacion(bote_eur)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/analizar-popularidad")
async def analizar_popularidad(
    req: AnalizarPopularidadRequest,
    payload: dict = Depends(verificar_token),
):
    """Analiza la popularidad de una combinación (cuánto compartiría premio)."""
    if any(n < 1 or n > 49 for n in req.combinacion):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Números fuera de rango [1, 49]",
        )
    try:
        pop = AntiPopularityScorer.calcular_popularidad(req.combinacion)
        compartidos = AntiPopularityScorer.estimar_compartidos(req.combinacion)
        return {
            "combinacion": sorted(req.combinacion),
            "popularidad": pop["popularidad"],
            "compartidos_estimados": compartidos,
            "es_geometria": pop["es_geometria"],
            "es_secuencia_natural": pop["es_secuencia_natural"],
            "n_pop_fuertes": pop["n_pop_fuertes"],
            "n_pop_debiles": pop["n_pop_debiles"],
            "proporcion_cumple": pop["proporcion_cumple"],
        }
    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/cobertura")
async def disenar_cobertura(
    k_numeros: int = Query(..., ge=6, le=15),
    garantia: int = Query(default=3, ge=2, le=5),
    t_aciertos: int = Query(default=4, ge=3, le=6),
    payload: dict = Depends(verificar_token),
):
    """
    Diseña una cobertura (wheeling) para k números con garantía verificada.

    Valor real y honesto: garantiza que si t de tus k números salen premiados,
    al menos una apuesta logra `garantia` aciertos. NO cambia la probabilidad
    de que tus números salgan — es gestión de riesgo combinatoria.
    """
    from app.domain.algorithms.covering import resumen_cobertura
    if t_aciertos > k_numeros:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="t_aciertos no puede superar k_numeros",
        )
    return resumen_cobertura(k_numeros, garantia, t_aciertos)


@router.post("/premio-esperado")
async def analizar_premio_esperado(
    combinaciones: List[List[int]] = Body(...),
    payload: dict = Depends(verificar_token),
):
    """
    Ordena combinaciones por premio esperado (anti-popularidad).

    Valor real y honesto: las combinaciones impopulares cobran más SI ganan
    (menos reparto del premio mutuo). NO mejora la probabilidad de ganar.
    """
    from app.domain.algorithms.premio_esperado import (
        optimizar_premio_esperado, analisis_completo,
    )
    # Validar
    for combo in combinaciones:
        if len(combo) != 6 or len(set(combo)) != 6 or not all(1 <= n <= 49 for n in combo):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Combinación inválida: {combo}",
            )
    ordenadas = optimizar_premio_esperado(combinaciones, top_n=len(combinaciones))
    return {
        "ordenadas_por_premio_esperado": [
            analisis_completo(combo) for combo, _ in ordenadas
        ],
        "nota": (
            "El orden refleja cuánto cobrarías si ganas, no la probabilidad "
            "de ganar (idéntica para todas las combinaciones)."
        ),
    }


@router.get("/loterias")
async def listar_loterias(payload: dict = Depends(verificar_token)):
    """Lista todas las loterías soportadas con su configuración."""
    return {"loterias": MultiLoteria.listar_loterias()}


@router.get("/kelly")
async def recomendacion_kelly(
    bankroll_eur: float = Query(..., ge=0),
    bote_eur: float = Query(default=400_000.0, ge=0),
    limite_mensual_eur: Optional[float] = Query(default=None),
    payload: dict = Depends(verificar_token),
):
    """
    Recomendación de gestión de bankroll vía criterio de Kelly.

    Honesto: con EV negativo (lo normal), Kelly dice no apostar; devolvemos
    una fracción de entretenimiento prudente. Con bote enorme (EV+), Kelly
    fraccional acotado.
    """
    from app.domain.algorithms.kelly import recomendar_bankroll
    rec = recomendar_bankroll(
        bankroll_eur=bankroll_eur,
        bote_eur=bote_eur,
        limite_perdida_mensual_eur=limite_mensual_eur,
    )
    return {
        "fraccion_kelly": rec.fraccion_kelly,
        "fraccion_aplicada": rec.fraccion_aplicada,
        "apuesta_recomendada_eur": rec.apuesta_recomendada_eur,
        "bankroll_eur": rec.bankroll_eur,
        "ev_apuesta_eur": rec.ev_apuesta,
        "es_ev_positivo": rec.es_ev_positivo,
        "mensaje": rec.mensaje,
    }
