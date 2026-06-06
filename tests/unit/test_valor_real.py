"""Tests de los algoritmos de valor real: cobertura y premio esperado."""

import pytest


@pytest.mark.unit
class TestCobertura:
    def test_cobertura_8_garantia_3(self):
        from app.domain.algorithms.covering import resumen_cobertura
        r = resumen_cobertura(k_numeros=8, garantia=3, t_aciertos=4)
        # La garantía real verificada debe cumplir la solicitada
        assert r["cumple_garantia"]
        assert r["garantia_real_verificada"] >= 3
        assert r["casos_fallidos"] == 0
        assert r["n_apuestas"] >= 1

    def test_cobertura_verificada_por_fuerza_bruta(self):
        from app.domain.algorithms.covering import (
            cobertura_greedy, verificar_cobertura,
        )
        apuestas = cobertura_greedy(k_numeros=9, garantia=3, t_aciertos=4)
        cumple, peor, fallidos = verificar_cobertura(apuestas, 9, 4, 3)
        assert cumple
        assert fallidos == 0

    def test_aplicar_cobertura_usa_numeros_reales(self):
        from app.domain.algorithms.covering import (
            cobertura_greedy, aplicar_cobertura,
        )
        idx = cobertura_greedy(k_numeros=7, garantia=3, t_aciertos=4)
        reales = [5, 12, 19, 23, 31, 38, 44]
        apuestas = aplicar_cobertura(idx, reales)
        for ap in apuestas:
            assert all(n in reales for n in ap)
            assert len(ap) == 6
            assert len(set(ap)) == 6

    def test_apuestas_validas(self):
        from app.domain.algorithms.covering import cobertura_greedy
        apuestas = cobertura_greedy(k_numeros=10, garantia=3, t_aciertos=4)
        for ap in apuestas:
            assert len(ap) == 6
            assert len(set(ap)) == 6
            assert all(1 <= n <= 10 for n in ap)


@pytest.mark.unit
class TestPremioEsperado:
    def test_secuencia_es_popular(self):
        from app.domain.algorithms.premio_esperado import popularidad_combinacion
        assert popularidad_combinacion([1, 2, 3, 4, 5, 6]) > 0.7

    def test_impopular_cobra_mas(self):
        from app.domain.algorithms.premio_esperado import premio_esperado_relativo
        popular = premio_esperado_relativo([1, 2, 3, 4, 5, 6])
        impopular = premio_esperado_relativo([13, 29, 37, 42, 46, 49])
        assert impopular > popular

    def test_premio_relativo_positivo(self):
        from app.domain.algorithms.premio_esperado import premio_esperado_relativo
        import random
        random.seed(3)
        for _ in range(20):
            combo = sorted(random.sample(range(1, 50), 6))
            assert premio_esperado_relativo(combo) > 0

    def test_optimizar_ordena_por_premio(self):
        from app.domain.algorithms.premio_esperado import optimizar_premio_esperado
        candidatas = [[1, 2, 3, 4, 5, 6], [13, 29, 37, 42, 46, 49]]
        top = optimizar_premio_esperado(candidatas, top_n=2)
        # El primero debe tener premio >= el segundo
        assert top[0][1] >= top[1][1]
        # El impopular debe ir primero
        assert top[0][0] == [13, 29, 37, 42, 46, 49]

    def test_analisis_completo_no_promete_ganar(self):
        from app.domain.algorithms.premio_esperado import analisis_completo
        a = analisis_completo([7, 19, 33, 41, 44, 48])
        # La interpretación debe aclarar que no cambia la probabilidad
        assert "no cambia tu probabilidad" in a["interpretacion"].lower()
