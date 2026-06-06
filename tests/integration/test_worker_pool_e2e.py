"""
Test de integración del WorkerPool: ciclo completo enqueue → proceso → guardado.

Mockea PipelineV4 para que termine inmediatamente, así podemos validar
el flujo de orquestación (worker → servicio → repo) sin esperar 8-50 min.
"""

import asyncio
import time
import pytest


@pytest.mark.integration
class TestWorkerPoolE2E:
    def test_worker_consume_job_y_marca_completado(self):
        """
        Encolamos un job. Inyectamos un pipeline fake que termina en 0.5s.
        Verificamos que tras esperar, el trabajo queda 'completado'.
        """
        async def run():
            # Imports locales para no contaminar otros tests
            from app.services.calculation.worker_pool import WorkerPool, JobCalculo
            from app.services.calculation.trabajos_repo import TrabajosRepoMemoria
            from app.services.calculation import servicio_calculo as sc_mod

            # Mock del PipelineV4: devuelve un resultado dummy rápido
            class FakePipeline:
                def __init__(self, **kwargs):
                    self.callback = kwargs.get("callback_progreso")
                async def ejecutar(self, cantidad):
                    # Simular 3 ticks de progreso
                    if self.callback:
                        await self.callback({"alg1": "ok"}, 0.3, 50.0, 1, False)
                        await asyncio.sleep(0.05)
                        await self.callback({"alg1": "ok"}, 0.6, 70.0, 2, False)
                        await asyncio.sleep(0.05)
                        await self.callback({"alg1": "ok"}, 0.9, 85.0, 3, True)
                    return type("R", (), {
                        "combinaciones": [{"numeros": [1,2,3,4,5,6],
                                           "indice_confianza": 85.0}],
                        "mejoras_detalle": ["ok"],
                        "n_algoritmos_activos": 1,
                        "tiempo_total_seg": 0.2,
                        "bloque_l_sistema_reducido": None,
                        "bloque_l_apuestas_garantizadas": [],
                        "bloque_l_coste_total_eur": 0.0,
                        "bloque_l_recomendacion": None,
                        "bloque_l_analisis_roi": None,
                        "bloque_l_confianza_agregada": None,
                        "bloque_l_estrategia": None,
                        "confianza_maxima": 85.0,
                    })()

            # Mock de BaseDatos.obtener_sorteos → lista vacía → usa fixtures
            class FakeBD:
                @staticmethod
                async def obtener_sorteos(limite=500):
                    return []  # forzará fallback a sorteos_simulados

            # Patch tanto el PipelineV4 como el BaseDatos en servicio_calculo
            original_pipe = sc_mod.PipelineV4
            original_bd = sc_mod.BaseDatos
            sc_mod.PipelineV4 = FakePipeline
            sc_mod.BaseDatos = FakeBD
            try:
                repo = TrabajosRepoMemoria()
                pool = WorkerPool(repo=repo, n_workers=1, max_pendientes=5)
                await pool.iniciar()

                # Encolar
                await repo.crear("trab-e2e", cantidad=1)
                await pool.enqueue(JobCalculo(
                    trabajo_id="trab-e2e", cantidad=1,
                    presupuesto_eur=10.0, bote_acumulado_eur=0.0,
                    loteria="bonoloto", encolado_en=time.time(),
                ))

                # Esperar a que el worker termine (con timeout de seguridad)
                deadline = time.time() + 10.0
                while time.time() < deadline:
                    t = await repo.obtener("trab-e2e")
                    if t.terminado:
                        break
                    await asyncio.sleep(0.1)

                t = await repo.obtener("trab-e2e")
                assert t.estado == "completado", \
                    f"esperaba completado, está {t.estado}: {t.mensaje}"
                assert t.progreso == 1.0
                assert len(t.combinaciones) == 1
                assert t.n_algoritmos == 1

                await pool.detener(timeout=2.0)
            finally:
                sc_mod.PipelineV4 = original_pipe
                sc_mod.BaseDatos = original_bd
        asyncio.run(run())

    def test_worker_captura_excepcion_del_pipeline(self):
        """Si el pipeline falla, el trabajo debe quedar en estado 'error'."""
        async def run():
            from app.services.calculation.worker_pool import WorkerPool, JobCalculo
            from app.services.calculation.trabajos_repo import TrabajosRepoMemoria
            from app.services.calculation import servicio_calculo as sc_mod

            class PipelineQueExplota:
                def __init__(self, **kwargs): pass
                async def ejecutar(self, cantidad):
                    raise ValueError("BOOM error sintético")

            class FakeBD:
                @staticmethod
                async def obtener_sorteos(limite=500):
                    return []

            original_pipe = sc_mod.PipelineV4
            original_bd = sc_mod.BaseDatos
            sc_mod.PipelineV4 = PipelineQueExplota
            sc_mod.BaseDatos = FakeBD
            try:
                repo = TrabajosRepoMemoria()
                pool = WorkerPool(repo=repo, n_workers=1, max_pendientes=5)
                await pool.iniciar()

                await repo.crear("trab-err", cantidad=1)
                await pool.enqueue(JobCalculo(
                    trabajo_id="trab-err", cantidad=1,
                    presupuesto_eur=10.0, bote_acumulado_eur=0.0,
                    loteria="bonoloto", encolado_en=time.time(),
                ))

                deadline = time.time() + 5.0
                while time.time() < deadline:
                    t = await repo.obtener("trab-err")
                    if t.terminado:
                        break
                    await asyncio.sleep(0.05)

                t = await repo.obtener("trab-err")
                assert t.estado == "error"
                assert "BOOM" in (t.mensaje or "")

                # CRÍTICO: el worker sobrevivió al error y sigue vivo
                # Lanzar otro job que SÍ funcione para confirmar
                class PipelineOK:
                    def __init__(self, **kwargs): pass
                    async def ejecutar(self, cantidad):
                        return type("R", (), {
                            "combinaciones": [], "mejoras_detalle": [],
                            "n_algoritmos_activos": 0, "tiempo_total_seg": 0.1,
                            "bloque_l_sistema_reducido": None,
                            "bloque_l_apuestas_garantizadas": [],
                            "bloque_l_coste_total_eur": 0.0,
                            "bloque_l_recomendacion": None,
                            "bloque_l_analisis_roi": None,
                            "bloque_l_confianza_agregada": None,
                            "bloque_l_estrategia": None,
                            "confianza_maxima": 0.0,
                        })()
                sc_mod.PipelineV4 = PipelineOK

                await repo.crear("trab-ok", cantidad=1)
                await pool.enqueue(JobCalculo(
                    trabajo_id="trab-ok", cantidad=1,
                    presupuesto_eur=10.0, bote_acumulado_eur=0.0,
                    loteria="bonoloto", encolado_en=time.time(),
                ))

                deadline = time.time() + 5.0
                while time.time() < deadline:
                    t2 = await repo.obtener("trab-ok")
                    if t2.terminado:
                        break
                    await asyncio.sleep(0.05)
                assert (await repo.obtener("trab-ok")).estado == "completado", \
                    "worker debería seguir vivo tras error anterior"

                await pool.detener(timeout=2.0)
            finally:
                sc_mod.PipelineV4 = original_pipe
                sc_mod.BaseDatos = original_bd
        asyncio.run(run())
