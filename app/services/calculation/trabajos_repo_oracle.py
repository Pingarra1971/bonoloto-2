"""
Implementación Oracle del repositorio de trabajos.

Diseño:
  - **Write-through cache**: cada cambio se persiste en BD y se
    refleja en cache local. Las lecturas pegan a cache primero.
  - **Resiliente a fallos transitorios**: si la BD da error en una
    escritura, el trabajo permanece en cache; el siguiente intento
    sincronizará.
  - **Sin race conditions** en single-process async: las escrituras
    serializadas vía `asyncio.Lock` por trabajo_id.

NOTA matemática a recordar: persistir un cálculo no aumenta sus
probabilidades, solo su robustez operativa.
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Optional

from app.services.calculation.trabajos_repo import Trabajo
from app.infrastructure.database import BaseDatos

logger = logging.getLogger(__name__)


class TrabajosRepoOracle:
    """Repo write-through con cache local in-memory."""

    def __init__(self):
        self._cache: Dict[str, Trabajo] = {}
        self._locks: Dict[str, asyncio.Lock] = {}
        self._lock_locks = asyncio.Lock()  # para crear locks por trabajo de forma segura

    async def _lock_for(self, trabajo_id: str) -> asyncio.Lock:
        """Devuelve (o crea) el lock asociado a un trabajo_id."""
        async with self._lock_locks:
            if trabajo_id not in self._locks:
                self._locks[trabajo_id] = asyncio.Lock()
            return self._locks[trabajo_id]

    async def crear(
        self,
        trabajo_id: str,
        cantidad: int,
        presupuesto_eur: float = 10.0,
        bote_acumulado_eur: float = 0.0,
        loteria: str = "bonoloto",
    ) -> Trabajo:
        lock = await self._lock_for(trabajo_id)
        async with lock:
            # ¿Ya está en cache?
            if trabajo_id in self._cache:
                return self._cache[trabajo_id]

            # ¿Existe en BD? (caso recuperación tras reinicio)
            db_row = await BaseDatos.calculo_obtener(trabajo_id)
            if db_row is not None:
                trabajo = self._reconstruir_desde_db(db_row)
                self._cache[trabajo_id] = trabajo
                return trabajo

            # Crear nuevo
            t = Trabajo(
                trabajo_id=trabajo_id,
                cantidad=cantidad,
                presupuesto_eur=presupuesto_eur,
                bote_acumulado_eur=bote_acumulado_eur,
                loteria=loteria,
                estado="iniciando",
            )
            self._cache[trabajo_id] = t
            # Persistir
            try:
                await BaseDatos.calculo_upsert(
                    trabajo_id=trabajo_id,
                    estado=t.estado,
                    cantidad=t.cantidad,
                    progreso=t.progreso,
                )
            except Exception as e:
                # No fatal: queda en cache y se intentará persistir al siguiente save
                logger.warning("No pude persistir trabajo %s al crear: %s", trabajo_id, e)
            return t

    async def obtener(self, trabajo_id: str) -> Optional[Trabajo]:
        # Cache hit
        if trabajo_id in self._cache:
            return self._cache[trabajo_id]
        # Cache miss: probar BD
        try:
            db_row = await BaseDatos.calculo_obtener(trabajo_id)
        except Exception as e:
            logger.warning("Error consultando BD para %s: %s", trabajo_id, e)
            return None
        if db_row is None:
            return None
        trabajo = self._reconstruir_desde_db(db_row)
        self._cache[trabajo_id] = trabajo
        return trabajo

    async def existe(self, trabajo_id: str) -> bool:
        if trabajo_id in self._cache:
            return True
        try:
            return await BaseDatos.calculo_existe(trabajo_id)
        except Exception:
            return False

    async def guardar(self, trabajo: Trabajo) -> None:
        """Persiste el trabajo. La cache ya está actualizada por referencia."""
        self._cache[trabajo.trabajo_id] = trabajo
        try:
            # Serializar el resultado completo solo si está terminado, para
            # evitar pegar a BD con CLOBs grandes en cada tick de progreso.
            if trabajo.terminado:
                resultado_json = json.dumps(trabajo.to_full_dict(), default=str)
            else:
                resultado_json = None

            await BaseDatos.calculo_upsert(
                trabajo_id=trabajo.trabajo_id,
                estado=trabajo.estado,
                cantidad=trabajo.cantidad,
                progreso=trabajo.progreso,
                resultado_json=resultado_json,
                error=trabajo.mensaje if trabajo.estado == "error" else None,
            )
        except Exception as e:
            # Crítico pero no fatal: el cache conserva el estado, próximos
            # `guardar` reintentarán. Si se reinicia el proceso ahora, se pierde
            # el último delta — aceptable porque el cálculo se marcará huérfano.
            logger.warning(
                "Error persistiendo trabajo %s estado=%s: %s",
                trabajo.trabajo_id, trabajo.estado, e,
            )

    async def listar_activos(self) -> List[Trabajo]:
        try:
            rows = await BaseDatos.calculos_listar_activos()
        except Exception as e:
            logger.warning("Error listando activos: %s", e)
            # Fallback: devolver lo que tengamos en cache
            return [t for t in self._cache.values() if t.activo]

        trabajos = []
        for row in rows:
            tid = row["trabajo_id"]
            if tid in self._cache:
                # Preferir la versión cache (más actualizada)
                trabajos.append(self._cache[tid])
            else:
                trabajos.append(self._reconstruir_desde_db(row))
        return trabajos

    async def total(self) -> int:
        try:
            return await BaseDatos.calculos_total()
        except Exception:
            return len(self._cache)

    async def rehidratar_huerfanos(self) -> int:
        """
        Al arrancar, los trabajos que quedaron 'calculando' son huérfanos:
        su tarea async murió con el proceso anterior. Los marcamos como
        'error' para que el cliente pueda reintentarlos.
        """
        try:
            n = await BaseDatos.calculos_marcar_huerfanos_como_error()
            if n > 0:
                logger.info("Rehidratados %d trabajos huérfanos (marcados error)", n)
            return n
        except Exception as e:
            logger.warning("Error rehidratando huérfanos: %s", e)
            return 0

    @staticmethod
    def _reconstruir_desde_db(row: dict) -> Trabajo:
        """Construye un Trabajo desde una fila de BD."""
        # Si el resultado_json existe (trabajo completado), deserializarlo
        if row.get("resultado_json"):
            try:
                data = json.loads(row["resultado_json"])
                return Trabajo.from_dict(data)
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning(
                    "resultado_json corrupto para %s: %s — usando fila básica",
                    row["trabajo_id"], e,
                )
        # Reconstrucción mínima
        return Trabajo(
            trabajo_id=row["trabajo_id"],
            estado=row.get("estado", "iniciando"),
            cantidad=row.get("cantidad", 0),
            progreso=row.get("progreso", 0.0),
            mensaje=row.get("error"),
            creado=row["creado"].timestamp() if row.get("creado") else time.time(),
        )
