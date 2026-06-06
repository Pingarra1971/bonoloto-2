"""Pruebas del cálculo de apuestas múltiples (7-11 números)."""

from app.domain.apuesta_multiple import (
    calcular_apuestas_multiples, combinaciones_de, coste_de,
)


class TestApuestaMultiple:

    def test_tabla_oficial_bonoloto(self):
        oficial = {6: (1, 0.5), 7: (7, 3.5), 8: (28, 14.0),
                   9: (84, 42.0), 10: (210, 105.0), 11: (462, 231.0)}
        for k, (comb, eur) in oficial.items():
            assert combinaciones_de(k) == comb
            assert coste_de(k) == eur

    def test_seleccion_top_k_y_anidamiento(self):
        scores = {n: float(n) for n in range(1, 50)}  # el mejor es el 49
        am = calcular_apuestas_multiples(scores)
        assert sorted(am.keys()) == ['10', '11', '7', '8', '9']
        assert am['7']['numeros'] == [43, 44, 45, 46, 47, 48, 49]
        assert am['7']['combinaciones'] == 7 and am['7']['coste_eur'] == 3.5
        assert am['11']['numeros'] == list(range(39, 50))
        assert am['11']['combinaciones'] == 462 and am['11']['coste_eur'] == 231.0
        for k in range(7, 11):
            assert set(am[str(k)]['numeros']).issubset(set(am[str(k + 1)]['numeros']))

    def test_sin_datos_devuelve_vacio(self):
        assert calcular_apuestas_multiples({}) == {}
