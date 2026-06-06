"""
Worker pool async para procesar cálculos.

Reemplaza `BackgroundTasks` de FastAPI con un patrón productor-consumidor:

  - El endpoint POST /api/calculo/iniciar **encola** un job (sin esperar).
  - Un pool de N workers async **consume** la cola y ejecuta los cálculos.
  - Cada cambio de estado se **persiste** vía RepoTrabajos.

Ventajas sobre BackgroundTasks:
  1. **Throttling**: límite controlado de cálculos concurrentes (sin saturar CPU).
  2. **Cola**: si llegan 10 peticiones, las 7 últimas esperan en cola, no se mata
     la VM intentando ejecutarlas todas a la vez.
  3. **Backpressure**: si la cola excede max_pendientes, se rechaza con 503.
  4. **Persistencia**: combinado con TrabajosRepoOracle, el estado sobrevive
     a reinicios (con marca de error para cálculos huérfanos).

Por qué NO Dramatiq+Redis en esta sesión:
  - Suma una dependencia de infraestructura (Redis) que para uso personal con
    1-2 cálculos simultáneos no aporta. La interfaz Worker.enqueue() ya está
    abstraída: si en el futuro escalas, swap a Dramatiq es local a este archivo.
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Optional, List

from app.config import get_settings
from app.services.calculation.trabajos_repo import RepoTrabajos, Trabajo

logger = logging.getLogger(__name__)


@dataclass
class JobCalculo:
    """Trabajo encolado para ejecución."""
    trabajo_id: str
    cantidad: int
    presupuesto_eur: float
    bote_acumulado_eur: float
    loteria: str
    encolado_en: float


class WorkerPool:
    """
    Pool de N workers async que procesan jobs de una cola FIFO.

    Uso:
        pool = WorkerPool(repo=mi_repo, n_workers=2)
        await pool.iniciar()
        await pool.enqueue(JobCalculo(...))
        # ... eventualmente:
        await pool.detener()
    """

    def __init__(
        self,
        repo: RepoTrabajos,
        n_workers: int = 2,
        max_pendientes: int = 20,
    ):
        self._repo = repo
        self._n_workers = max(1, n_workers)
        self._max_pendientes = max_pendientes
        self._cola: asyncio.Queue[Optional[JobCalculo]] = asyncio.Queue(
            maxsize=max_pendientes
        )
        self._workers: List[asyncio.Task] = []
        self._activos = 0   # cuántos workers están ejecutando un cálculo ahora mismo
        self._lock_activos = asyncio.Lock()
        self._cerrando = False

    @property
    def n_workers(self) -> int:
        return self._n_workers

    @property
    def n_pendientes(self) -> int:
        """Cuántos jobs hay esperando en la cola (sin contar los en ejecución)."""
        return self._cola.qsize()

    @property
    def n_ejecutando(self) -> int:
        return self._activos

    async def iniciar(self):
        """Lanza los workers. Llamar en el lifespan startup de FastAPI."""
        if self._workers:
            logger.warning("WorkerPool ya estaba iniciado")
            return

        # Rehidratar huérfanos antes de aceptar trabajos nuevos
        n_huerfanos = await self._repo.rehidratar_huerfanos()
        if n_huerfanos > 0:
            logger.info("Rehidratados %d trabajos huérfanos al arrancar", n_huerfanos)

        self._cerrando = False
        for i in range(self._n_workers):
            t = asyncio.create_task(self._loop_worker(worker_id=i))
            self._workers.append(t)
        logger.info("WorkerPool iniciado con %d workers", self._n_workers)

    async def detener(self, timeout: float = 5.0):
        """
        Cierre limpio: marca cerrando, envía centinelas, espera con timeout.
        Si los workers están ejecutando un cálculo largo (8-50 min), no
        esperamos a que terminen — los cancelamos. Sus trabajos quedarán
        en estado 'calculando' y serán rehidratados al siguiente arranque.
        """
        if not self._workers:
            return
        self._cerrando = True
        # Drenar jobs pendientes que aún no empezaron, para hacer sitio a los
        # centinelas. Los jobs drenados no se han ejecutado: quedan en su
        # estado previo en el repo y serán rehidratados al siguiente arranque.
        # Sin esto, si la cola está llena, los centinelas no caben (#138) y el
        # cierre degrada innecesariamente a cancelación forzosa.
        while True:
            try:
                self._cola.get_nowait()
                self._cola.task_done()
            except asyncio.QueueEmpty:
                break

        # Centinelas: uno por worker para que cada uno salga de su loop
        for _ in self._workers:
            try:
                self._cola.put_nowait(None)
            except asyncio.QueueFull:
                pass

        try:
            await asyncio.wait_for(
                asyncio.gather(*self._workers, return_exceptions=True),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            logger.warning("Workers no terminaron en %.1fs, cancelando", timeout)
            for w in self._workers:
                if not w.done():
                    w.cancel()
            await asyncio.gather(*self._workers, return_exceptions=True)
        finally:
            self._workers.clear()
            logger.info("WorkerPool detenido")

    async def enqueue(self, job: JobCalculo) -> None:
        """
        Encola un job. Lanza `asyncio.QueueFull` si se excede max_pendientes
        (el caller debe traducir a HTTP 503).
        """
        if self._cerrando:
            raise RuntimeError("WorkerPool en cierre, no acepta jobs")
        # Marcar trabajo como encolado en el repo
        t = await self._repo.obtener(job.trabajo_id)
        if t is not None:
            t.estado = "encolado"
            await self._repo.guardar(t)
        # put_nowait lanza QueueFull si la cola está saturada → backpressure
        self._cola.put_nowait(job)
        logger.info(
            "Encolado trabajo %s | cola=%d pendientes | ejecutando=%d",
            job.trabajo_id, self._cola.qsize(), self._activos,
        )

    async def _loop_worker(self, worker_id: int):
        """Loop de consumidor. Toma jobs de la cola y los procesa."""
        logger.info("Worker %d arrancado", worker_id)
        try:
            while True:
                job = await self._cola.get()
                if job is None:
                    # Centinela: salir del loop
                    return
                try:
                    async with self._lock_activos:
                        self._activos += 1
                    await self._procesar_job(job)
                except Exception as e:
                    # No tirar el worker por un job malo
                    logger.error(
                        "Worker %d: job %s falló: %s",
                        worker_id, job.trabajo_id, e, exc_info=True,
                    )
                finally:
                    async with self._lock_activos:
                        self._activos -= 1
        except asyncio.CancelledError:
            logger.info("Worker %d cancelado", worker_id)
            raise

    async def _procesar_job(self, job: JobCalculo):
        """Ejecuta un job: instancia el ServicioCalculo y lo corre."""
        # Import diferido para evitar dependencia circular en arranque
        from app.services.calculation.servicio_calculo import ServicioCalculo

        tiempo_en_cola = time.time() - job.encolado_en
        if tiempo_en_cola > 5.0:
            logger.info(
                "Job %s esperó %.1fs en cola",
                job.trabajo_id, tiempo_en_cola,
            )

        servicio = ServicioCalculo(repo=self._repo)
        await servicio.ejecutar(
            trabajo_id=job.trabajo_id,
            cantidad=job.cantidad,
            presupuesto_eur=job.presupuesto_eur,
            bote_acumulado_eur=job.bote_acumulado_eur,
            loteria=job.loteria,
        )


# ─────────────────────────────────────────────────────────
# Singleton
# ─────────────────────────────────────────────────────────


_pool_global: Optional[WorkerPool] = None


def reset_pool_global():
    """Para tests."""
    global _pool_global
    _pool_global = None


async def get_worker_pool() -> WorkerPool:
    """
    Devuelve el WorkerPool singleton.
    Debe haber sido iniciado en el lifespan startup.
    """
    global _pool_global
    if _pool_global is None:
        from app.services.calculation.trabajos_repo import get_trabajos_repo
        repo = await get_trabajos_repo()
        settings = get_settings()
        # Para uso personal con cálculos de 8-50 min: 2 workers es suficiente
        # y evita saturar la VM. Configurable vía env si quieres.
        _pool_global = WorkerPool(
            repo=repo,
            n_workers=2,
            max_pendientes=settings.max_trabajos_memoria,
        )
    return _pool_global
