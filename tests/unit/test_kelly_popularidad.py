"""Tests del criterio de Kelly y el scoring anti-popularidad."""

import pytest


@pytest.mark.unit
class TestKelly:
    def test_kelly_ev_negativo_no_apuesta(self):
        from app.domain.algorithms.kelly import recomendar_bankroll
        r = recomendar_bankroll(bankroll_eur=1000, bote_eur=400_000)
        # Con EV negativo, la fracción Kelly teórica es <= 0
        assert r.fraccion_kelly <= 0
        assert not r.es_ev_positivo

    def test_kelly_fraccion_entretenimiento_acotada(self):
        from app.domain.algorithms.kelly import recomendar_bankroll
        r = recomendar_bankroll(bankroll_eur=1000, bote_eur=400_000)
        # La apuesta recomendada no debe exceder ~1% del bankroll
        assert r.apuesta_recomendada_eur <= 1000 * 0.01 + 0.5

    def test_kelly_respeta_limite_mensual(self):
        from app.domain.algorithms.kelly import recomendar_bankroll
        r = recomendar_bankroll(
            bankroll_eur=10000, bote_eur=400_000,
            limite_perdida_mensual_eur=3.0,
        )
        assert r.apuesta_recomendada_eur <= 3.0

    def test_kelly_apuesta_multiplo_de_050(self):
        from app.domain.algorithms.kelly import recomendar_bankroll
        r = recomendar_bankroll(bankroll_eur=1000, bote_eur=400_000)
        # La apuesta debe ser múltiplo de 0.50€
        assert abs((r.apuesta_recomendada_eur / 0.5) -
                   round(r.apuesta_recomendada_eur / 0.5)) < 1e-9

    def test_kelly_formula_teorica(self):
        from app.domain.algorithms.kelly import fraccion_kelly_teorica
        # Apuesta justa (b=1, p=0.5): Kelly = 0
        assert abs(fraccion_kelly_teorica(0.5, 1.0)) < 1e-9
        # Ventaja (b=1, p=0.6): Kelly = 0.2
        assert abs(fraccion_kelly_teorica(0.6, 1.0) - 0.2) < 1e-9
        # Desventaja (b=1, p=0.4): Kelly negativo
        assert fraccion_kelly_teorica(0.4, 1.0) < 0


@pytest.mark.unit
class TestAntiPopularidad:
    def test_secuencia_consecutiva_es_popular(self):
        from app.domain.algorithms.block_l import AntiPopularityScorer
        pop = AntiPopularityScorer.calcular_popularidad([1, 2, 3, 4, 5, 6])
        # Secuencia 1-6: muy popular (secuencia + todos cumpleaños)
        assert pop["popularidad"] > 0.5
        assert pop["es_secuencia_natural"]

    def test_numeros_altos_es_impopular(self):
        from app.domain.algorithms.block_l import AntiPopularityScorer
        pop = AntiPopularityScorer.calcular_popularidad([38, 41, 43, 45, 47, 49])
        # Todos altos, sin patrón: impopular
        assert pop["popularidad"] < 0.3

    def test_cumpleanos_aumenta_popularidad(self):
        from app.domain.algorithms.block_l import AntiPopularityScorer
        # Todos <= 31 (cumpleaños)
        pop_cumple = AntiPopularityScorer.calcular_popularidad([3, 8, 12, 19, 24, 28])
        # Mezcla con altos
        pop_mixto = AntiPopularityScorer.calcular_popularidad([3, 8, 12, 38, 44, 48])
        assert pop_cumple["popularidad"] > pop_mixto["popularidad"]

    def test_geometria_detectada(self):
        from app.domain.algorithms.block_l import AntiPopularityScorer
        # Progresión aritmética (línea en el boleto)
        pop = AntiPopularityScorer.calcular_popularidad([5, 10, 15, 20, 25, 30])
        assert pop["es_geometria"]

    def test_estimar_compartidos_popular_vs_impopular(self):
        from app.domain.algorithms.block_l import AntiPopularityScorer
        compartidos_pop = AntiPopularityScorer.estimar_compartidos([1, 2, 3, 4, 5, 6])
        compartidos_impop = AntiPopularityScorer.estimar_compartidos(
            [32, 37, 41, 44, 47, 49])
        # Una combinación popular se compartiría con más gente
        assert compartidos_pop >= compartidos_impop

    def test_popularidad_en_rango(self):
        from app.domain.algorithms.block_l import AntiPopularityScorer
        import random
        random.seed(7)
        for _ in range(50):
            combo = sorted(random.sample(range(1, 50), 6))
            pop = AntiPopularityScorer.calcular_popularidad(combo)
            assert 0.0 <= pop["popularidad"] <= 1.0
