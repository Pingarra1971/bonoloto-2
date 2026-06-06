"""Tests del repo async in-memory y del WorkerPool."""

import asyncio
import time
import pytest


@pytest.mark.unit
class TestTrabajosRepoMemoria:
    def setup_method(self):
        from app.services.calculation.trabajos_repo import TrabajosRepoMemoria
        self.repo = TrabajosRepoMemoria(max_terminados=5)

    def test_crear_y_obtener(self):
        async def run():
            t = await self.repo.crear("abc", cantidad=3)
            assert t.trabajo_id == "abc"
            t2 = await self.repo.obtener("abc")
            assert t2 is t
        asyncio.run(run())

    def test_existe(self):
        async def run():
            assert not await self.repo.existe("xyz")
            await self.repo.crear("xyz", cantidad=1)
            assert await self.repo.existe("xyz")
        asyncio.run(run())

    def test_guardar_actualiza_estado(self):
        async def run():
            t = await self.repo.crear("abc", cantidad=1)
            t.progreso = 0.5
            t.estado = "calculando"
            await self.repo.guardar(t)
            t2 = await self.repo.obtener("abc")
            assert t2.progreso == 0.5
            assert t2.estado == "calculando"
        asyncio.run(run())

    def test_listar_activos(self):
        async def run():
            t1 = await self.repo.crear("a1", cantidad=1)
            t2 = await self.repo.crear("a2", cantidad=1)
            t2.estado = "completado"
            await self.repo.guardar(t2)
            activos = await self.repo.listar_activos()
            assert len(activos) == 1
            assert activos[0].trabajo_id == "a1"
        asyncio.run(run())

    def test_rehidratar_huerfanos_devuelve_0_in_memory(self):
        async def run():
            n = await self.repo.rehidratar_huerfanos()
            assert n == 0
        asyncio.run(run())

    def test_estado_encolado_es_activo(self):
        from app.services.calculation.trabajos_repo import Trabajo
        t = Trabajo(trabajo_id="x", estado="encolado")
        assert t.activo
        assert not t.terminado

    def test_estado_terminado(self):
        from app.services.calculation.trabajos_repo import Trabajo
        t = Trabajo(trabajo_id="x", estado="completado")
        assert not t.activo
        assert t.terminado

    def test_protocol_conformance(self):
        from app.services.calculation.trabajos_repo import (
            RepoTrabajos, TrabajosRepoMemoria
        )
        repo = TrabajosRepoMemoria()
        assert isinstance(repo, RepoTrabajos)


@pytest.mark.unit
class TestWorkerPool:
    def test_inicia_y_detiene_limpio(self):
        from app.services.calculation.worker_pool import WorkerPool
        from app.services.calculation.trabajos_repo import TrabajosRepoMemoria

        async def run():
            repo = TrabajosRepoMemoria()
            pool = WorkerPool(repo=repo, n_workers=2, max_pendientes=10)
            await pool.iniciar()
            assert pool.n_workers == 2
            assert pool.n_pendientes == 0
            assert pool.n_ejecutando == 0
            await pool.detener(timeout=2.0)
            # Tras detener, todos los workers terminaron
        asyncio.run(run())

    def test_enqueue_marca_estado_encolado(self):
        from app.services.calculation.worker_pool import WorkerPool, JobCalculo
        from app.services.calculation.trabajos_repo import TrabajosRepoMemoria

        async def run():
            repo = TrabajosRepoMemoria()
            await repo.crear("test-1", cantidad=2)
            pool = WorkerPool(repo=repo, n_workers=0, max_pendientes=5)
            # n_workers=0 → enqueue funciona pero no se procesa
            # (excepto que iniciar() lanza 0 workers, lo cual es legal)
            await pool.iniciar()
            await pool.enqueue(JobCalculo(
                trabajo_id="test-1", cantidad=2,
                presupuesto_eur=10.0, bote_acumulado_eur=0.0,
                loteria="bonoloto", encolado_en=time.time(),
            ))
            t = await repo.obtener("test-1")
            assert t.estado == "encolado"
            await pool.detener(timeout=2.0)
        asyncio.run(run())

    def test_enqueue_full_lanza_excepcion(self):
        from app.services.calculation.worker_pool import WorkerPool, JobCalculo
        from app.services.calculation.trabajos_repo import TrabajosRepoMemoria

        async def run():
            repo = TrabajosRepoMemoria()
            pool = WorkerPool(repo=repo, n_workers=0, max_pendientes=2)
            await pool.iniciar()
            # Llenar la cola (sin workers consumiendo)
            for i in range(2):
                await repo.crear(f"t{i}", cantidad=1)
                await pool.enqueue(JobCalculo(
                    trabajo_id=f"t{i}", cantidad=1,
                    presupuesto_eur=1.0, bote_acumulado_eur=0.0,
                    loteria="bonoloto", encolado_en=time.time(),
                ))
            # El siguiente debe fallar con QueueFull
            await repo.crear("t99", cantidad=1)
            with pytest.raises(asyncio.QueueFull):
                await pool.enqueue(JobCalculo(
                    trabajo_id="t99", cantidad=1,
                    presupuesto_eur=1.0, bote_acumulado_eur=0.0,
                    loteria="bonoloto", encolado_en=time.time(),
                ))
            await pool.detener(timeout=2.0)
        asyncio.run(run())

    def test_enqueue_durante_cierre_lanza_runtime_error(self):
        from app.services.calculation.worker_pool import WorkerPool, JobCalculo
        from app.services.calculation.trabajos_repo import TrabajosRepoMemoria

        async def run():
            repo = TrabajosRepoMemoria()
            pool = WorkerPool(repo=repo, n_workers=1)
            await pool.iniciar()
            pool._cerrando = True  # simular cierre
            with pytest.raises(RuntimeError):
                await pool.enqueue(JobCalculo(
                    trabajo_id="x", cantidad=1,
                    presupuesto_eur=1.0, bote_acumulado_eur=0.0,
                    loteria="bonoloto", encolado_en=time.time(),
                ))
            pool._cerrando = False
            await pool.detener(timeout=2.0)
        asyncio.run(run())
