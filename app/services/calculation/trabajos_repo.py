"""
Repositorio de trabajos de cálculo.

Interfaz abstracta (Protocol) + dos implementaciones intercambiables:
  - `TrabajosRepoMemoria`: in-memory con cap FIFO. Para dev y fallback.
  - `TrabajosRepoOracle`: persistente en BD Oracle. Sobrevive a reinicios.

La factory `get_trabajos_repo()` elige automáticamente según haya BD o no.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────
# DATA MODEL
# ─────────────────────────────────────────────────────────


@dataclass
class Trabajo:
    """Estado de un cálculo individual."""
    trabajo_id: str
    estado: str = "iniciando"        # iniciando | encolado | calculando | completado | error
    cantidad: int = 0
    presupuesto_eur: float = 10.0
    bote_acumulado_eur: float = 0.0
    loteria: str = "bonoloto"
    progreso: float = 0.0             # 0.0 - 1.0
    iteracion: int = 0
    indice_confianza: float = 0.0
    convergiendo: bool = False
    estado_algoritmos: Dict[str, str] = field(default_factory=dict)
    mensaje: Optional[str] = None
    creado: float = field(default_factory=time.time)
    completado: Optional[float] = None
    # Resultado (rellenado al completar)
    combinaciones: List[Any] = field(default_factory=list)
    bloque_l_sistema: Optional[str] = None
    bloque_l_apuestas: List[Any] = field(default_factory=list)
    bloque_l_coste_eur: float = 0.0
    bloque_l_recomendacion: Optional[str] = None
    bloque_l_roi: Optional[dict] = None
    bloque_l_confianza: Optional[float] = None
    bloque_l_estrategia_completa: Optional[dict] = None
    cobertura_garantizada: Optional[dict] = None
    # Apuestas múltiples (7-11 números) calculadas desde las puntuaciones
    # finales. Dict {"7": {numeros, combinaciones, coste_eur}, ...} o None.
    apuestas_multiples: Optional[dict] = None
    mejoras_activas: List[str] = field(default_factory=list)
    n_algoritmos: int = 0
    tiempo_segundos: float = 0.0

    @property
    def activo(self) -> bool:
        return self.estado in ("iniciando", "encolado", "calculando")

    @property
    def terminado(self) -> bool:
        return self.estado in ("completado", "error")

    def to_dict(self) -> dict:
        """Serializa el trabajo a dict para respuestas API."""
        return {
            "trabajo_id": self.trabajo_id,
            "estado": self.estado,
            "progreso": self.progreso,
            "iteracion_actual": self.iteracion,
            "confianza_actual": self.indice_confianza,
            "convergiendo": self.convergiendo,
            "algoritmos_estado": self.estado_algoritmos,
            "mensaje": self.mensaje,
        }

    def to_full_dict(self) -> dict:
        """Serializa el trabajo COMPLETO (con resultado) para BD."""
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Trabajo":
        """Reconstruye un Trabajo desde un dict (deserialización BD)."""
        # Filtrar claves que no son del dataclass para resiliencia ante esquemas viejos
        campos_validos = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in d.items() if k in campos_validos})


# ─────────────────────────────────────────────────────────
# INTERFAZ (Protocol)
# ─────────────────────────────────────────────────────────


@runtime_checkable
class RepoTrabajos(Protocol):
    """
    Contrato común para repositorios de trabajos.

    Las implementaciones (memoria, Oracle, Redis...) deben implementar
    estos métodos. La capa de servicio sólo conoce esta interfaz.
    """

    async def crear(
        self,
        trabajo_id: str,
        cantidad: int,
        presupuesto_eur: float = 10.0,
        bote_acumulado_eur: float = 0.0,
        loteria: str = "bonoloto",
    ) -> Trabajo: ...

    async def obtener(self, trabajo_id: str) -> Optional[Trabajo]: ...

    async def existe(self, trabajo_id: str) -> bool: ...

    async def guardar(self, trabajo: Trabajo) -> None:
        """Persiste cambios en el trabajo (estado, progreso, resultado)."""
        ...

    async def listar_activos(self) -> List[Trabajo]: ...

    async def total(self) -> int: ...

    async def rehidratar_huerfanos(self) -> int:
        """
        Al arrancar el proceso, marca como 'error' los trabajos que
        quedaron en estado 'calculando' (porque el proceso anterior murió).
        Devuelve cuántos se rehidrataron.
        Sólo aplica a repos persistentes; in-memory devuelve 0.
        """
        ...


# ─────────────────────────────────────────────────────────
# IMPLEMENTACIÓN IN-MEMORY (fallback / dev)
# ─────────────────────────────────────────────────────────


class TrabajosRepoMemoria:
    """
    Repositorio in-memory con tope FIFO de trabajos terminados.

    Thread-safe en asyncio single-thread porque las ops sobre dict son atómicas.
    Para multi-worker hay que migrar a la implementación Oracle/Redis.
    """

    def __init__(self, max_terminados: int = 50):
        self._trabajos: Dict[str, Trabajo] = {}
        self._max_terminados = max_terminados
        self._lock = asyncio.Lock()

    async def crear(
        self,
        trabajo_id: str,
        cantidad: int,
        presupuesto_eur: float = 10.0,
        bote_acumulado_eur: float = 0.0,
        loteria: str = "bonoloto",
    ) -> Trabajo:
        if trabajo_id in self._trabajos:
            return self._trabajos[trabajo_id]
        t = Trabajo(
            trabajo_id=trabajo_id,
            cantidad=cantidad,
            presupuesto_eur=presupuesto_eur,
            bote_acumulado_eur=bote_acumulado_eur,
            loteria=loteria,
        )
        self._trabajos[trabajo_id] = t
        self._limpiar_si_excedido()
        return t

    async def obtener(self, trabajo_id: str) -> Optional[Trabajo]:
        return self._trabajos.get(trabajo_id)

    async def existe(self, trabajo_id: str) -> bool:
        return trabajo_id in self._trabajos

    async def guardar(self, trabajo: Trabajo) -> None:
        # In-memory: el Trabajo es mutado in-place, no hay nada que persistir
        # pero registramos por si hay limpieza necesaria
        self._trabajos[trabajo.trabajo_id] = trabajo

    async def listar_activos(self) -> List[Trabajo]:
        return [t for t in self._trabajos.values() if t.activo]

    async def total(self) -> int:
        return len(self._trabajos)

    async def rehidratar_huerfanos(self) -> int:
        # No aplica: in-memory pierde todo al reiniciar
        return 0

    # Sincrónico — usado por listar_activos del modo legacy
    @property
    def activos(self) -> List[Trabajo]:
        return [t for t in self._trabajos.values() if t.activo]

    def _limpiar_si_excedido(self):
        if len(self._trabajos) <= self._max_terminados:
            return
        activos = {k: v for k, v in self._trabajos.items() if v.activo}
        terminados = [(k, v) for k, v in self._trabajos.items() if not v.activo]
        terminados.sort(key=lambda kv: kv[1].creado, reverse=True)
        n_keep = max(0, self._max_terminados - len(activos))
        a_mantener = dict(terminados[:n_keep])
        a_mantener.update(activos)
        n_desc = len(self._trabajos) - len(a_mantener)
        if n_desc > 0:
            logger.info("TrabajosRepoMemoria: descartados %d antiguos", n_desc)
        self._trabajos.clear()
        self._trabajos.update(a_mantener)


# ─────────────────────────────────────────────────────────
# FACTORY (singleton)
# ─────────────────────────────────────────────────────────


_repo_global: Optional[RepoTrabajos] = None


def reset_repo_global():
    """Para tests: fuerza recreación del singleton."""
    global _repo_global
    _repo_global = None


async def get_trabajos_repo() -> RepoTrabajos:
    """
    Devuelve el singleton del repo.

    Lazy init: en la primera llamada, decide la implementación según
    haya BD disponible:
      - Si BaseDatos._pool != None → TrabajosRepoOracle
      - Si no → TrabajosRepoMemoria (modo degradado)
    """
    global _repo_global
    if _repo_global is not None:
        return _repo_global

    from app.config import get_settings
    from app.infrastructure.database import BaseDatos

    settings = get_settings()
    if BaseDatos._pool is not None:
        from app.services.calculation.trabajos_repo_oracle import TrabajosRepoOracle
        repo = TrabajosRepoOracle()
        logger.info("Repo de trabajos: Oracle (persistente)")
    else:
        repo = TrabajosRepoMemoria(max_terminados=settings.max_trabajos_memoria)
        logger.info("Repo de trabajos: in-memory (no persistente)")

    _repo_global = repo
    return repo


# Compat con tests sesión 1 (uso síncrono — devuelve memoria por defecto)
def get_trabajos_repo_sync() -> TrabajosRepoMemoria:
    """
    DEPRECADO: variante síncrona que devuelve siempre TrabajosRepoMemoria.
    Usado por código legacy de Sesión 1; se eliminará cuando todo el código
    use `await get_trabajos_repo()`.
    """
    global _repo_global
    if isinstance(_repo_global, TrabajosRepoMemoria):
        return _repo_global
    from app.config import get_settings
    repo = TrabajosRepoMemoria(max_terminados=get_settings().max_trabajos_memoria)
    if _repo_global is None:
        _repo_global = repo
    return repo
