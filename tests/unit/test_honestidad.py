"""Tests del módulo de honestidad: matemática + servicio."""

import asyncio
import pytest


@pytest.mark.unit
class TestHonestidadMath:
    def test_total_combinaciones(self):
        from app.domain.honestidad_math import TOTAL_COMBINACIONES
        assert TOTAL_COMBINACIONES == 13_983_816

    def test_probabilidades_suman_uno(self):
        from app.domain.honestidad_math import P_ACIERTOS
        suma = sum(P_ACIERTOS.values())
        assert abs(suma - 1.0) < 1e-9

    def test_prob_jackpot(self):
        from app.domain.honestidad_math import P_ACIERTOS, TOTAL_COMBINACIONES
        assert abs(P_ACIERTOS[6] - 1 / TOTAL_COMBINACIONES) < 1e-15

    def test_aciertos_esperados_azar(self):
        from app.domain.honestidad_math import ACIERTOS_ESPERADOS_POR_BOLETO_AZAR
        # 6 * 6/49 = 36/49
        assert abs(ACIERTOS_ESPERADOS_POR_BOLETO_AZAR - 36 / 49) < 1e-9

    def test_ev_sin_bote_es_negativo(self):
        from app.domain.honestidad_math import analizar_ev, TablaPremios
        ev = analizar_ev(TablaPremios())
        assert ev.ev_por_apuesta_eur < 0, "EV sin bote debe ser negativo"
        assert not ev.es_favorable

    def test_ev_con_bote_enorme_puede_ser_favorable(self):
        from app.domain.honestidad_math import ev_con_bote
        ev = ev_con_bote(50_000_000)
        # Con bote de 50M el EV teórico se vuelve positivo
        assert ev.es_favorable

    def test_backtest_sin_datos(self):
        from app.domain.honestidad_math import backtest_sistema
        bt = backtest_sistema([], n_sorteos=0)
        assert bt.n_predicciones == 0
        assert "Sin datos" in bt.veredicto

    def test_backtest_muestra_pequena(self):
        from app.domain.honestidad_math import backtest_sistema
        bt = backtest_sistema([1, 0, 2, 1, 0], n_sorteos=1)
        assert bt.n_predicciones == 5
        assert "pequeña" in bt.veredicto.lower()

    def test_backtest_muestra_grande_cerca_del_azar(self):
        from app.domain.honestidad_math import (
            backtest_sistema, ACIERTOS_ESPERADOS_POR_BOLETO_AZAR,
        )
        import random
        random.seed(42)
        # Simular 200 boletos al azar contra un sorteo
        ganadores = set(random.sample(range(1, 50), 6))
        aciertos = []
        for _ in range(200):
            b = set(random.sample(range(1, 50), 6))
            aciertos.append(len(b & ganadores))
        bt = backtest_sistema(aciertos, n_sorteos=1)
        # La media debe estar cerca del valor teórico del azar
        assert abs(bt.aciertos_medios_sistema -
                   ACIERTOS_ESPERADOS_POR_BOLETO_AZAR) < 0.3

    def test_coste_oportunidad(self):
        from app.domain.honestidad_math import coste_oportunidad
        co = coste_oportunidad(1000.0, meses=12, rendimiento_anual_alternativo=0.10)
        # 1000 al 10% un año = 1100
        assert abs(co["valor_si_invertido_eur"] - 1100.0) < 1.0
        assert abs(co["ganancia_alternativa_eur"] - 100.0) < 1.0

    def test_coste_oportunidad_sin_tiempo(self):
        from app.domain.honestidad_math import coste_oportunidad
        co = coste_oportunidad(500.0, meses=0)
        assert co["valor_si_invertido_eur"] == 500.0
        assert co["ganancia_alternativa_eur"] == 0.0


@pytest.mark.unit
class TestServicioHonestidad:
    def setup_method(self):
        from app.services.honestidad.servicio_honestidad import (
            reset_servicio_honestidad,
        )
        reset_servicio_honestidad()

    def test_registrar_apuesta(self):
        async def run():
            from app.services.honestidad.servicio_honestidad import (
                ServicioHonestidad,
            )
            s = ServicioHonestidad()
            ap = await s.registrar_apuesta([3, 11, 19, 27, 35, 43], coste_eur=0.5)
            assert ap.numeros == [3, 11, 19, 27, 35, 43]
            assert not ap.evaluada
        asyncio.run(run())

    def test_evaluar_sorteo_calcula_aciertos(self):
        async def run():
            from app.services.honestidad.servicio_honestidad import (
                ServicioHonestidad,
            )
            s = ServicioHonestidad()
            await s.registrar_apuesta([1, 2, 3, 4, 5, 6])
            await s.registrar_apuesta([1, 2, 3, 40, 41, 42])
            # Sorteo ganador: 1,2,3,4,5,6 → primera apuesta 6 aciertos, segunda 3
            res = await s.evaluar_sorteo("2026-01-01", [1, 2, 3, 4, 5, 6])
            assert res["apuestas_evaluadas"] == 2
            apuestas = list(s._apuestas.values())
            aciertos = sorted(a.aciertos for a in apuestas)
            assert aciertos == [3, 6]
        asyncio.run(run())

    def test_estadisticas_pyl(self):
        async def run():
            from app.services.honestidad.servicio_honestidad import (
                ServicioHonestidad,
            )
            from app.domain.honestidad_math import TablaPremios
            s = ServicioHonestidad()
            # 2 apuestas de 0.50 = 1.00 apostado
            await s.registrar_apuesta([1, 2, 3, 4, 5, 6])
            await s.registrar_apuesta([10, 11, 12, 13, 14, 15])
            # Evaluar: primera saca 3 aciertos (premio 4€), segunda 0
            await s.evaluar_sorteo(
                "2026-01-01", [1, 2, 3, 40, 41, 42],
                tabla_premios=TablaPremios(premio_3=4.0),
            )
            stats = await s.calcular_estadisticas()
            assert stats.total_apostado_eur == 1.0
            assert stats.total_ganado_eur == 4.0  # premio de 3 aciertos
            assert stats.balance_neto_eur == 3.0
            assert stats.n_apuestas == 2
            assert stats.n_apuestas_evaluadas == 2
        asyncio.run(run())

    def test_backtest_con_predicciones(self):
        async def run():
            from app.services.honestidad.servicio_honestidad import (
                ServicioHonestidad,
            )
            s = ServicioHonestidad()
            await s.registrar_prediccion("t1", [1, 2, 3, 4, 5, 6], 85.0)
            await s.registrar_prediccion("t1", [7, 8, 9, 10, 11, 12], 80.0)
            await s.evaluar_sorteo("2026-01-01", [1, 2, 3, 4, 5, 6])
            stats = await s.calcular_estadisticas()
            # primera predicción: 6 aciertos, segunda: 0 → total 6, media 3
            assert stats.backtest["n_predicciones"] == 2
            assert stats.backtest["aciertos_medios_sistema"] == 3.0
        asyncio.run(run())
