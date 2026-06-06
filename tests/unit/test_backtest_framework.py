"""Tests del framework de backtest honesto."""

import random
import pytest


@pytest.fixture
def sorteos_aleatorios():
    rng = random.Random(123)
    return [sorted(rng.sample(range(1, 50), 6)) for _ in range(400)]


@pytest.mark.unit
class TestBacktestFramework:
    def test_aciertos_esperados_azar_constante(self):
        from app.services.calibration.backtest_framework import (
            ACIERTOS_ESPERADOS_AZAR,
        )
        assert abs(ACIERTOS_ESPERADOS_AZAR - 36 / 49) < 1e-9

    def test_prediccion_frecuencias_no_supera_azar(self, sorteos_aleatorios):
        """
        Un predictor basado en frecuencias (los más sorteados) NO debe
        superar al azar de forma significativa sobre datos aleatorios.
        Esto es la prueba empírica de la tesis central del proyecto.
        """
        from app.services.calibration.backtest_framework import (
            backtest_walk_forward,
        )
        from collections import Counter

        def predictor_frecuencias(historico):
            # Los 6 números más frecuentes en el histórico
            c = Counter()
            for sorteo in historico:
                c.update(sorteo)
            return [n for n, _ in c.most_common(6)]

        res = backtest_walk_forward(
            sorteos_aleatorios, predictor_frecuencias,
            ventana_min=100, max_evaluaciones=200,
        )
        assert res.n_evaluaciones > 0
        # NO debe ser significativamente mejor que el azar
        assert not (res.es_significativo and res.diferencia > 0), (
            f"El predictor de frecuencias parece superar al azar "
            f"(z={res.z_score}), lo cual indicaría data leakage. "
            f"Veredicto: {res.veredicto}"
        )

    def test_comparar_con_azar(self, sorteos_aleatorios):
        from app.services.calibration.backtest_framework import comparar_con_azar
        from collections import Counter

        def predictor(historico):
            c = Counter()
            for s in historico:
                c.update(s)
            return [n for n, _ in c.most_common(6)]

        res = comparar_con_azar(
            sorteos_aleatorios, predictor,
            ventana_min=100, max_evaluaciones=150,
        )
        assert "sistema" in res
        assert "azar_control" in res
        # Ambos deben tener medias cercanas al valor teórico
        assert abs(res["sistema"].aciertos_medios_sistema - 0.7347) < 0.4
        assert abs(res["azar_control"].aciertos_medios_sistema - 0.7347) < 0.4

    def test_distribucion_aciertos_suma_n(self, sorteos_aleatorios):
        from app.services.calibration.backtest_framework import (
            backtest_walk_forward,
        )

        def pred(h):
            return [1, 2, 3, 4, 5, 6]

        res = backtest_walk_forward(
            sorteos_aleatorios, pred, ventana_min=100, max_evaluaciones=100,
        )
        assert sum(res.distribucion_aciertos.values()) == res.n_evaluaciones

    def test_sin_evaluaciones(self):
        from app.services.calibration.backtest_framework import (
            backtest_walk_forward,
        )
        res = backtest_walk_forward([], lambda h: [1, 2, 3, 4, 5, 6])
        assert res.n_evaluaciones == 0
        assert "Sin evaluaciones" in res.veredicto
