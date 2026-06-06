"""
Tests del contrato backend ↔ frontend.

Blindan los bugs #131 y #132: las claves que el backend produce deben
coincidir con las que el frontend Dart espera. Si alguien renombra una
clave en el pipeline sin actualizar el frontend, estos tests fallan.
"""

import pytest


@pytest.mark.unit
class TestContratoFormateoMejoras:
    def test_formatear_mejoras_dict_a_lista(self):
        """#132: mejoras_detalle (dict) → mejoras_activas (list[str])."""
        from app.services.calculation.servicio_calculo import ServicioCalculo
        detalle = {
            "isolation_forest": "3 anomalías filtradas",
            "nivel_senal": "moderada",
            "n_algoritmos": 42,
            "stacking_lider": "markov",
            "bloque_l_sistema": "7/3-4-5",
            "total_tecnicas": 115,
        }
        resultado = ServicioCalculo._formatear_mejoras(detalle)
        assert isinstance(resultado, list)
        assert all(isinstance(x, str) for x in resultado)
        assert len(resultado) >= 4
        # Debe mencionar el nº de algoritmos y las técnicas
        texto = " ".join(resultado)
        assert "42" in texto
        assert "115" in texto

    def test_formatear_mejoras_lista_passthrough(self):
        """Si ya es lista, se devuelve tal cual."""
        from app.services.calculation.servicio_calculo import ServicioCalculo
        entrada = ["mejora A", "mejora B"]
        assert ServicioCalculo._formatear_mejoras(entrada) == entrada

    def test_formatear_mejoras_none_seguro(self):
        """None u otros tipos → lista vacía, sin crashear."""
        from app.services.calculation.servicio_calculo import ServicioCalculo
        assert ServicioCalculo._formatear_mejoras(None) == []
        assert ServicioCalculo._formatear_mejoras(42) == []


@pytest.mark.unit
class TestContratoClavesCombinacion:
    def test_clave_pesos_por_algoritmo(self):
        """
        #131: el pipeline debe producir 'pesos_por_algoritmo' (no
        'pesos_algoritmos'), que es lo que el frontend Dart lee.
        """
        import inspect
        from app.services.pipeline import pipeline_v4
        fuente = inspect.getsource(pipeline_v4.PipelineV4._formatear_combinaciones)
        assert '"pesos_por_algoritmo"' in fuente, (
            "El pipeline debe usar la clave 'pesos_por_algoritmo' para "
            "coincidir con el frontend (bug #131)"
        )
        assert '"pesos_algoritmos"' not in fuente, (
            "La clave antigua 'pesos_algoritmos' no debe reaparecer (bug #131)"
        )
