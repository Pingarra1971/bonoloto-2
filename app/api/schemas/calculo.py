"""
Schemas Pydantic v2 para validación de request/response de la API.

Antes estos schemas vivían dentro de main.py mezclados con los endpoints.
Ahora están aquí, son testeables aisladamente, y se importan desde routes/.
"""

from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


# ─────────────────────────────────────────────────────────
# REQUEST SCHEMAS
# ─────────────────────────────────────────────────────────


class ConfiguracionCalculo(BaseModel):
    """Configuración avanzada opcional del cálculo."""
    convergencia_automatica: bool = True
    algoritmos: List[str] = Field(default_factory=list)
    meta_modelo: str = "consenso_dinamico"
    umbral_convergencia: float = Field(default=0.001, ge=0.0001, le=0.1)


class SolicitudCalculo(BaseModel):
    """Body del POST /api/calculo/iniciar."""
    cantidad: int = Field(..., ge=1, le=20, description="Número de combinaciones a generar")
    presupuesto_eur: float = Field(default=10.0, ge=0.5, le=1000.0)
    bote_acumulado_eur: float = Field(default=600_000.0, ge=0.0)
    loteria: str = Field(default="bonoloto")
    configuracion: Optional[ConfiguracionCalculo] = None

    @field_validator("loteria")
    @classmethod
    def loteria_valida(cls, v: str) -> str:
        permitidas = {"bonoloto", "primitiva", "euromillones", "gordo"}
        if v.lower() not in permitidas:
            raise ValueError(f"loteria debe ser una de {permitidas}")
        return v.lower()


class ResultadoSorteoEntrada(BaseModel):
    """Body del POST /api/modelos/reentrenar — sorteo real con el que reentrenar."""
    fecha: str
    numeros: List[int] = Field(..., min_length=6, max_length=6)
    complementario: int = Field(..., ge=1, le=49)
    reintegro: int = Field(..., ge=0, le=9)
    bote: int = Field(default=0, ge=0)

    @field_validator("numeros")
    @classmethod
    def numeros_validos(cls, v: List[int]) -> List[int]:
        if len(set(v)) != 6:
            raise ValueError("numeros debe contener 6 valores únicos")
        if not all(1 <= n <= 49 for n in v):
            raise ValueError("numeros deben estar en [1, 49]")
        return sorted(v)


# ─────────────────────────────────────────────────────────
# RESPONSE SCHEMAS
# ─────────────────────────────────────────────────────────


class CombinacionResponse(BaseModel):
    """Combinación generada por el sistema."""
    numeros: List[int]
    reintegro: Optional[int] = None
    complementario: Optional[int] = None
    indice_confianza: float = Field(..., ge=0.0, le=100.0)
    estrategia: Optional[str] = None
    metricas: Optional[dict] = None


class ProgresoResponse(BaseModel):
    """Estado de progreso de un trabajo. progreso en escala 0.0-1.0."""
    trabajo_id: str
    estado: str
    progreso: float = Field(..., ge=0.0, le=1.0)
    mensaje: Optional[str] = None
    iteracion_actual: Optional[int] = None
    confianza_actual: Optional[float] = None
    algoritmos_estado: Optional[dict] = None


class ResultadoResponse(BaseModel):
    """Resultado final de un cálculo completado."""
    trabajo_id: str
    estado: str
    combinaciones: List[CombinacionResponse]
    confianza_maxima: float
    iteraciones: int
    n_algoritmos_activos: int
    bloque_l_sistema_reducido: Optional[str] = None
    bloque_l_apuestas_garantizadas: List[dict] = Field(default_factory=list)
    bloque_l_coste_total_eur: float = 0.0
    bloque_l_garantia: Optional[str] = None


class IniciarCalculoResponse(BaseModel):
    """Respuesta del POST /api/calculo/iniciar."""
    trabajo_id: str
    estado: str = "iniciando"
    mensaje: str = "Cálculo iniciado correctamente"


class HealthResponse(BaseModel):
    version: str
    estado: str
    bd_conectada: bool
    trabajos_activos: int
