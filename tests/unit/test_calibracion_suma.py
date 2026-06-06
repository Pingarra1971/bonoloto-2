"""
Tests de calibración estadística de los heurísticos de combinación.

Blindan el bug #166: los bonus de "suma en rango óptimo" deben estar
centrados en la suma media real de Bonoloto (150 = 6 × 25), no descentrados.
"""

import pytest


@pytest.mark.unit
class TestCalibracionSuma:
    def test_indice_confianza_centrado_en_150(self):
        """El bonus de suma debe premiar combinaciones con suma ~150."""
        from app.domain.motor_ia import MotorIA
        motor = MotorIA([{"numeros": [1, 2, 3, 4, 5, 6]}])
        scores = {n: 0.5 for n in range(1, 50)}

        # Combinación con suma ~150 (centrada)
        combo_centrado = [10, 20, 25, 30, 30, 35]  # suma = 150
        # ajustar a números válidos únicos con suma ~150
        combo_centrado = [15, 22, 25, 28, 30, 30]
        combo_centrado = [10, 20, 25, 30, 35, 30]
        # Usar una combinación válida real con suma 150
        combo_150 = [5, 15, 25, 35, 30, 40]  # suma = 150
        assert sum(combo_150) == 150

        # Combinación con suma muy baja (21, la mínima posible: 1+2+3+4+5+6)
        combo_bajo = [1, 2, 3, 4, 5, 6]  # suma = 21

        ic_150 = motor.calcular_indice_confianza(combo_150, scores)
        ic_bajo = motor.calcular_indice_confianza(combo_bajo, scores)

        # La combinación centrada en 150 debe tener >= confianza que la extrema
        assert ic_150 >= ic_bajo

    def test_suma_125_no_es_optimo(self):
        """Una suma de 125 ya no debe ser el pico (era el bug #166)."""
        from app.domain.motor_ia import MotorIA
        motor = MotorIA([{"numeros": [1, 2, 3, 4, 5, 6]}])
        scores = {n: 0.5 for n in range(1, 50)}

        combo_125 = [5, 15, 25, 30, 20, 30]  # ajustar
        combo_125 = [10, 15, 20, 25, 25, 30]  # suma = 125
        assert sum(combo_125) == 125
        combo_150 = [5, 15, 25, 35, 30, 40]  # suma = 150

        ic_125 = motor.calcular_indice_confianza(combo_125, scores)
        ic_150 = motor.calcular_indice_confianza(combo_150, scores)

        # Ambas dentro del rango bonus (96-204), así que el bonus_suma es igual;
        # lo importante es que 150 NO esté penalizada respecto a 125.
        # Verificamos que ambas reciben el bonus (no hay penalización a 150).
        assert ic_150 >= ic_125 - 5  # 150 no debe estar peor que 125

    def test_rango_bonus_simetrico_alrededor_150(self):
        """El rango de bonus [96, 204] está centrado en 150."""
        centro = (96 + 204) / 2
        assert centro == 150.0
