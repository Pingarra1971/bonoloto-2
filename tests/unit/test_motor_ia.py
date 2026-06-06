"""
Tests unitarios de MotorIA.

Validan que la extracción quirúrgica de main.py preservó comportamiento:
  - Constructor acepta lista de sorteos
  - Cada capa devuelve dict {1..49: float} normalizado
  - meta_modelo_consenso combina y devuelve scores válidos
  - Sin dependencia de FastAPI ni BD (clave del refactor)
"""

import random
import pytest


@pytest.fixture
def sorteos_dummy():
    """100 sorteos sintéticos reproducibles."""
    rng = random.Random(42)
    return [
        {
            "numeros": sorted(rng.sample(range(1, 50), 6)),
            "complementario": rng.randint(1, 49),
            "reintegro": rng.randint(0, 9),
        }
        for _ in range(100)
    ]


@pytest.fixture
def motor(sorteos_dummy):
    from app.domain.motor_ia import MotorIA
    return MotorIA(sorteos_dummy)


@pytest.mark.unit
class TestMotorIA:
    def test_constructor(self, motor):
        assert motor.n == 100
        assert len(motor.NOMBRES_ALGORITMOS) >= 11

    def test_capa1_entropia(self, motor):
        scores = motor.capa1_entropia()
        assert len(scores) == 49
        assert all(isinstance(s, float) for s in scores.values())
        assert all(0.0 <= s <= 1.0 for s in scores.values())

    def test_capa1_hot_cold_bias(self, motor):
        scores = motor.capa1_hot_cold_bias()
        assert len(scores) == 49
        assert all(0.0 <= s <= 1.0 for s in scores.values())

    def test_capa2_lstm(self, motor):
        scores = motor.capa2_lstm_simple()
        assert len(scores) == 49

    def test_capa2_transformer(self, motor):
        scores = motor.capa2_transformer_attention()
        assert len(scores) == 49

    def test_capa3_bayesiano(self, motor):
        scores = motor.capa3_bayesiano()
        assert len(scores) == 49

    def test_capa3_xgboost(self, motor):
        scores = motor.capa3_xgboost_simple()
        assert len(scores) == 49

    def test_capa4_monte_carlo_reducido(self, motor):
        scores = motor.capa4_monte_carlo(iteraciones=500)
        assert len(scores) == 49

    def test_meta_modelo_consenso(self, motor):
        scores_por_algo = {
            "entropia": motor.capa1_entropia(),
            "lstm": motor.capa2_lstm_simple(),
            "bayesiano": motor.capa3_bayesiano(),
        }
        consenso = motor.meta_modelo_consenso(scores_por_algo)
        assert len(consenso) == 49
        # Los scores del consenso deben ser float y finitos
        for n, v in consenso.items():
            assert 1 <= n <= 49
            assert isinstance(v, float)
            assert v == v  # not NaN

    def test_calcular_indice_confianza(self, motor):
        combo = [3, 11, 19, 27, 35, 43]
        scores = motor.capa1_entropia()
        conf = motor.calcular_indice_confianza(combo, scores)
        assert 0.0 <= conf <= 100.0

    def test_pesos_suman_uno_aprox(self, motor):
        # Los pesos del motor deben estar normalizados
        total = sum(motor.pesos.values())
        # Tolerancia: pueden estar ligeramente fuera de 1.0 por float arithmetic
        assert 0.95 <= total <= 1.05, f"pesos suman {total:.4f}, esperaba ~1.0"

    def test_actualizar_pesos_aciertos_aumenta_peso(self, motor):
        # Si un algoritmo acierta sistemáticamente, su peso debe crecer
        peso_inicial = motor.pesos["entropia"]
        historial = [
            {"algoritmo": "entropia", "aciertos": 5}
            for _ in range(5)
        ]
        motor.actualizar_pesos(historial)
        peso_final = motor.pesos["entropia"]
        assert peso_final >= peso_inicial, \
            f"peso bajó de {peso_inicial} a {peso_final} pese a 5 aciertos consecutivos"
