"""
Verificación exhaustiva de las garantías de los sistemas reducidos.

Estos tests son la PRUEBA matemática de que cada sistema cumple lo que
promete. Si alguien edita una matriz de apuestas y rompe la cobertura,
estos tests fallan. Es la garantía de integridad del Bloque L.

Método: fuerza bruta. Para un sistema con N números que afirma "garantía G
si aciertan K", se comprueba que para TODO subconjunto de K números (de los
N seleccionados) que pudieran salir premiados, al menos una apuesta del
sistema logra >= G aciertos.
"""

from itertools import combinations
import pytest


def _garantia_real(sistema, k_aciertan):
    """Devuelve la garantía real (peor caso) para k aciertos en la selección."""
    N = sistema["n_numeros"]
    apuestas = sistema["apuestas"]
    numeros = list(range(1, N + 1))
    peor_caso = 6
    for ganadores_idx in combinations(numeros, k_aciertan):
        gset = set(ganadores_idx)
        mejor = max(len(set(ap) & gset) for ap in apuestas)
        peor_caso = min(peor_caso, mejor)
    return peor_caso


@pytest.mark.unit
class TestSistemasReducidos:
    def setup_method(self):
        from app.domain.algorithms.block_l import SistemaReducido
        self.sistemas = SistemaReducido.SISTEMAS

    def test_n_apuestas_declarado_coincide(self):
        for nombre, s in self.sistemas.items():
            assert len(s["apuestas"]) == s["n_apuestas"], (
                f"{nombre}: declara {s['n_apuestas']} apuestas pero hay "
                f"{len(s['apuestas'])}"
            )

    def test_apuestas_tienen_6_indices_validos(self):
        for nombre, s in self.sistemas.items():
            N = s["n_numeros"]
            for i, ap in enumerate(s["apuestas"]):
                assert len(ap) == 6, f"{nombre} apuesta {i}: no tiene 6 números"
                assert len(set(ap)) == 6, f"{nombre} apuesta {i}: duplicados {ap}"
                assert all(1 <= x <= N for x in ap), (
                    f"{nombre} apuesta {i}: índice fuera de [1,{N}]: {ap}"
                )

    def test_garantias_declaradas_se_cumplen(self):
        """El test crítico: cada garantía declarada debe ser real."""
        fallos = []
        for nombre, s in self.sistemas.items():
            for k, g_declarado in s["garantias"].items():
                if k > s["n_numeros"]:
                    continue
                g_real = _garantia_real(s, k)
                if g_real < g_declarado:
                    fallos.append(
                        f"{nombre}: declara ≥{g_declarado} si aciertan {k}, "
                        f"pero la garantía real es ≥{g_real}"
                    )
        assert not fallos, "Garantías falsas:\n" + "\n".join(fallos)

    def test_sistema_7_garantia_especifica(self):
        """Verificación puntual: 7/3-4-5 garantiza 3 si aciertan 4."""
        s = self.sistemas["7/3-4-5"]
        assert _garantia_real(s, 4) >= 3

    def test_aplicar_sistema_produce_apuestas_validas(self):
        from app.domain.algorithms.block_l import SistemaReducido
        # 7 números reales
        seleccion = [5, 12, 19, 23, 31, 38, 44]
        apuestas = SistemaReducido.aplicar_sistema("7/3-4-5", seleccion)
        assert len(apuestas) == 7
        for ap in apuestas:
            assert len(ap) == 6
            assert len(set(ap)) == 6
            assert all(n in seleccion for n in ap)

    def test_verificar_garantia_con_resultado_real(self):
        from app.domain.algorithms.block_l import SistemaReducido
        seleccion = [5, 12, 19, 23, 31, 38, 44]
        # Ganadores que incluyen 4 de la selección
        ganadores = [5, 12, 19, 23, 1, 2]
        res = SistemaReducido.verificar_garantia(
            "7/3-4-5", seleccion, ganadores,
        )
        assert res["aciertos_seleccion"] == 4
        # Debe haber al menos una apuesta con >= 3 aciertos (garantía)
        assert res["mejor_apuesta"] >= 3
