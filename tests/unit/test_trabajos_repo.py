"""Tests del repositorio in-memory de trabajos (sesión 2 refactor)."""

import time
import asyncio
import pytest


@pytest.fixture
def repo():
    from app.services.calculation.trabajos_repo import TrabajosRepoMemoria
    return TrabajosRepoMemoria(max_terminados=5)


@pytest.mark.unit
class TestTrabajosRepoMemoria:
    def test_crear_y_obtener(self, repo):
        async def run():
            t = await repo.crear("abc", cantidad=3)
            assert t.trabajo_id == "abc"
            assert await repo.obtener("abc") is t
            assert await repo.existe("abc")
            assert not await repo.existe("xyz")
        asyncio.run(run())

    def test_crear_idempotente(self, repo):
        async def run():
            t1 = await repo.crear("abc", cantidad=3)
            t2 = await repo.crear("abc", cantidad=99)
            assert t1 is t2
            assert t1.cantidad == 3
        asyncio.run(run())

    def test_activos_filter(self, repo):
        async def run():
            await repo.crear("a1", cantidad=1)
            t = await repo.crear("a2", cantidad=1)
            t.estado = "completado"
            await repo.guardar(t)
            activos = await repo.listar_activos()
            assert len(activos) == 1
            assert activos[0].trabajo_id == "a1"
        asyncio.run(run())

    def test_cap_fifo_descarta_antiguos(self, repo):
        async def run():
            for i in range(5):
                t = await repo.crear(f"t{i}", cantidad=1)
                t.estado = "completado"
                t.creado = float(i)
                await repo.guardar(t)
            assert await repo.total() == 5

            t6 = await repo.crear("t6", cantidad=1)
            t6.estado = "completado"
            t6.creado = 100.0
            await repo.guardar(t6)
            # Trigger cleanup explícitamente (en producción ocurre al crear)
            repo._limpiar_si_excedido()

            assert await repo.total() == 5
            assert not await repo.existe("t0")
            assert await repo.existe("t6")
        asyncio.run(run())

    def test_activos_no_se_descartan_aunque_excedan(self, repo):
        async def run():
            for i in range(5):
                await repo.crear(f"activo{i}", cantidad=1)
            await repo.crear("activo5", cantidad=1)
            assert await repo.total() == 6
            for i in range(6):
                assert await repo.existe(f"activo{i}")
        asyncio.run(run())

    def test_to_dict(self, repo):
        async def run():
            t = await repo.crear("abc", cantidad=3)
            t.indice_confianza = 87.5
            t.iteracion = 12
            d = t.to_dict()
            assert d["trabajo_id"] == "abc"
            assert d["confianza_actual"] == 87.5
            assert d["iteracion_actual"] == 12
        asyncio.run(run())
