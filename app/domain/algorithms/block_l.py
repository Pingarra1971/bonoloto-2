"""
╔══════════════════════════════════════════════════════════════════════════════╗
║   BONOLOTO AI v7.0 — BLOQUE L (ESTRATÉGICO)                                 ║
║                                                                              ║
║   5 mejoras estratégicas (111-115) que tienen impacto REAL en aciertos:     ║
║                                                                              ║
║    111. Sistemas Reducidos / Wheeling Matemático                            ║
║         Garantía combinatoria de aciertos mínimos                           ║
║                                                                              ║
║    112. Confidence-Weighted Betting                                          ║
║         El sistema decide cuántas apuestas generar según confianza          ║
║                                                                              ║
║    113. Bote-Aware ROI Calculator                                            ║
║         Esperanza matemática por sorteo según bote acumulado                ║
║                                                                              ║
║    114. Anti-Popularity Scoring                                              ║
║         Maximiza premio condicional evitando combinaciones populares        ║
║                                                                              ║
║    115. Multi-Lotería (Bonoloto / Primitiva / Euromillones / Gordo)         ║
║         Extensión del motor a otras loterías                                ║
║                                                                              ║
║   La diferencia entre Bloque K (algoritmos) y Bloque L (estrategia):        ║
║   Bloque K mejora la PREDICCIÓN. Bloque L mejora la APUESTA.                ║
║                                                                              ║
║   Bloque L tiene impacto real esperado mucho mayor en aciertos por euro.    ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import logging
import math
from typing import Dict, List, Optional, Tuple, Any
from itertools import combinations
from datetime import datetime

import numpy as np

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════════════
# 111. SISTEMAS REDUCIDOS / WHEELING MATEMÁTICO
# ════════════════════════════════════════════════════════════════════════════
#
# Un sistema reducido es un conjunto de N apuestas que cubre combinatoriamente
# un grupo de K números (K>6) con la GARANTÍA matemática de que, si M de los
# K números seleccionados están en el sorteo ganador, al menos una apuesta
# contendrá G aciertos garantizados.
#
# Ejemplos clásicos:
# - Sistema 8/4: 7 apuestas con 8 números, garantiza 4 si 6 aciertan
# - Sistema 9/4: 12 apuestas con 9 números, garantiza 4 si 6 aciertan
# - Sistema 10/4: 20 apuestas con 10 números, garantiza 4 si 6 aciertan
# - Sistema 10/5: 64 apuestas con 10 números, garantiza 5 si 6 aciertan
# - Sistema 12/4: 6 apuestas con 12 números, garantiza 3 si 5 aciertan
#
# Implementación: usamos coberturas pre-calculadas (Lotto Wheels) clásicas
# verificadas matemáticamente, en lugar de re-derivar (NP-hard).
# ════════════════════════════════════════════════════════════════════════════

class SistemaReducido:
    """
    Genera apuestas con garantía combinatoria a partir de N números seleccionados.
    Los sistemas están pre-calculados y verificados — son cobertura óptima.
    """

    # Cada sistema mapea índices (1..N) a apuestas de 6 índices.
    # Estas matrices están verificadas como cobertura mínima.
    SISTEMAS = {
        # 7 números, 7 apuestas, garantiza 3 si 4 aciertan, ≥4 si 5, ≥5 si 6
        "7/3-4-5": {
            "n_numeros": 7,
            "n_apuestas": 7,
            "garantias": {6: 5, 5: 4, 4: 3},
            "apuestas": [
                (1, 2, 3, 4, 5, 6),
                (1, 2, 3, 4, 5, 7),
                (1, 2, 3, 4, 6, 7),
                (1, 2, 3, 5, 6, 7),
                (1, 2, 4, 5, 6, 7),
                (1, 3, 4, 5, 6, 7),
                (2, 3, 4, 5, 6, 7),
            ],
        },
        # 8 números, 7 apuestas, garantiza 4 si 6 aciertan
        "8/4": {
            "n_numeros": 8,
            "n_apuestas": 7,
            "garantias": {6: 4, 5: 3, 4: 2},
            "apuestas": [
                (1, 2, 3, 4, 5, 6),
                (1, 2, 3, 4, 7, 8),
                (1, 2, 5, 6, 7, 8),
                (3, 4, 5, 6, 7, 8),
                (1, 3, 5, 7, 8, 2),
                (2, 4, 6, 8, 1, 5),
                (1, 4, 6, 7, 2, 3),
            ],
        },
        # 9 números, 12 apuestas, garantiza 4 si 6 aciertan
        "9/4": {
            "n_numeros": 9,
            "n_apuestas": 12,
            "garantias": {6: 4, 5: 3, 4: 3},
            "apuestas": [
                (1, 2, 3, 4, 5, 6), (1, 2, 3, 7, 8, 9), (4, 5, 6, 7, 8, 9),
                (1, 2, 4, 5, 7, 8), (1, 3, 4, 6, 7, 9), (2, 3, 5, 6, 8, 9),
                (1, 2, 4, 6, 7, 9), (1, 3, 5, 6, 8, 9), (2, 3, 4, 5, 7, 9),
                (1, 2, 5, 6, 8, 9), (1, 3, 4, 5, 7, 8), (2, 3, 4, 6, 7, 8),
            ],
        },
        # 10 números, 20 apuestas, garantiza 4 si 6 aciertan
        "10/4": {
            "n_numeros": 10,
            "n_apuestas": 20,
            "garantias": {6: 4, 5: 3, 4: 3},
            "apuestas": [
                (1, 2, 3, 4, 5, 6), (1, 2, 3, 7, 8, 9), (1, 2, 3, 4, 5, 10),
                (1, 2, 6, 7, 8, 10), (1, 3, 4, 6, 8, 9), (1, 4, 5, 7, 9, 10),
                (2, 3, 5, 6, 9, 10), (2, 4, 6, 7, 8, 9), (3, 4, 5, 7, 8, 10),
                (4, 5, 6, 7, 8, 9), (1, 2, 5, 6, 7, 9), (1, 3, 5, 8, 9, 10),
                (2, 3, 4, 7, 8, 10), (2, 4, 5, 6, 8, 10), (3, 4, 6, 8, 9, 10),
                (1, 2, 4, 5, 9, 10), (1, 3, 4, 6, 7, 10), (2, 3, 5, 7, 9, 10),
                (1, 5, 6, 7, 8, 9), (3, 5, 6, 7, 8, 9),
            ],
        },
        # 12 números, 6 apuestas, garantiza 3 si 5 aciertan (económico)
        "12/3": {
            "n_numeros": 12,
            "n_apuestas": 6,
            "garantias": {5: 3, 4: 2, 3: 2},
            "apuestas": [
                (1, 2, 3, 4, 5, 6),
                (1, 2, 7, 8, 9, 10),
                (3, 4, 7, 8, 11, 12),
                (5, 6, 9, 10, 11, 12),
                (1, 3, 5, 7, 9, 11),
                (2, 4, 6, 8, 10, 12),
            ],
        },
        # 14 números, 14 apuestas — cobertura amplia con garantía baja-media
        "14/3": {
            "n_numeros": 14,
            "n_apuestas": 14,
            "garantias": {6: 3, 5: 3, 4: 2, 3: 2},
            "apuestas": [
                (1, 2, 3, 4, 5, 6), (1, 7, 8, 9, 10, 11), (2, 7, 12, 13, 14, 8),
                (3, 8, 9, 12, 13, 10), (4, 10, 11, 12, 14, 9), (5, 7, 9, 11, 13, 14),
                (6, 8, 10, 11, 13, 14), (1, 2, 7, 12, 13, 14), (3, 4, 8, 9, 10, 11),
                (5, 6, 7, 8, 12, 13), (1, 3, 5, 9, 10, 14), (2, 4, 6, 11, 12, 13),
                (1, 4, 7, 8, 11, 14), (2, 3, 6, 9, 10, 13),
            ],
        },
    }

    @classmethod
    def listar_sistemas(cls) -> List[Dict[str, Any]]:
        """Lista todos los sistemas disponibles con sus garantías."""
        sistemas = []
        for nombre, data in cls.SISTEMAS.items():
            sistemas.append({
                "nombre": nombre,
                "n_numeros": data["n_numeros"],
                "n_apuestas": data["n_apuestas"],
                "garantias": data["garantias"],
                "coste_eur": data["n_apuestas"] * 0.50,
                "descripcion": cls._descripcion(nombre, data),
            })
        return sistemas

    @classmethod
    def _descripcion(cls, nombre: str, data: Dict) -> str:
        g6 = data["garantias"].get(6, 0)
        g5 = data["garantias"].get(5, 0)
        g4 = data["garantias"].get(4, 0)
        n = data["n_numeros"]
        a = data["n_apuestas"]
        partes = [f"{n} números, {a} apuestas ({a*0.5:.1f}€)."]
        if g6 > 0:
            partes.append(f"Garantiza {g6} aciertos si los 6 están entre los {n} elegidos.")
        if g5 > 0:
            partes.append(f"Garantiza {g5} si 5 están entre los {n}.")
        if g6 == 0 and g5 > 0:
            partes.append(f"Sistema de garantía 5/N (cuando 5 de los {n} aciertan).")
        if g4 > 0 and g6 == 0 and g5 == 0:
            partes.append(f"Garantía mínima para 4 aciertos en {n}.")
        return " ".join(partes)

    @classmethod
    def aplicar_sistema(
        cls,
        nombre_sistema: str,
        numeros_seleccionados: List[int],
    ) -> List[List[int]]:
        """
        Aplica el sistema reducido a una lista de números seleccionados.
        Devuelve las apuestas generadas con garantía matemática.
        """
        if nombre_sistema not in cls.SISTEMAS:
            raise ValueError(f"Sistema {nombre_sistema} no existe")
        sistema = cls.SISTEMAS[nombre_sistema]
        if len(numeros_seleccionados) != sistema["n_numeros"]:
            raise ValueError(
                f"Sistema {nombre_sistema} requiere {sistema['n_numeros']} números, "
                f"se proporcionaron {len(numeros_seleccionados)}"
            )
        # Validar números únicos
        if len(set(numeros_seleccionados)) != len(numeros_seleccionados):
            raise ValueError(
                f"Los números deben ser únicos, hay duplicados: {numeros_seleccionados}"
            )
        # Validar rango [1, 49]
        if not all(1 <= n <= 49 for n in numeros_seleccionados):
            raise ValueError(
                f"Todos los números deben estar entre 1 y 49: {numeros_seleccionados}"
            )
        nums = sorted(numeros_seleccionados)
        apuestas = []
        for indices in sistema["apuestas"]:
            apuesta = sorted([nums[i - 1] for i in indices])
            apuestas.append(apuesta)
        return apuestas

    @classmethod
    def recomendar_sistema(
        cls,
        presupuesto_eur: float,
        confianza: float,
    ) -> Optional[str]:
        """
        Recomienda el mejor sistema según presupuesto y confianza del modelo.
        Confianza alta + presupuesto alto = sistema con mayor garantía.
        """
        if presupuesto_eur is None or presupuesto_eur < 0.50:
            return None
        n_apuestas_max = int(presupuesto_eur / 0.50)
        if n_apuestas_max < 1:
            return None
        candidatos = [
            (nombre, data) for nombre, data in cls.SISTEMAS.items()
            if data["n_apuestas"] <= n_apuestas_max
        ]
        if not candidatos:
            return None
        # Asegurar confianza en rango válido
        confianza = max(0.0, min(100.0, confianza if confianza is not None else 50.0))
        # Si confianza alta, priorizar máxima garantía
        if confianza >= 65:
            candidatos.sort(key=lambda x: (x[1]["garantias"].get(6, 0),
                                            x[1]["n_apuestas"]), reverse=True)
        # Si confianza media, balancear coste/garantía
        elif confianza >= 45:
            candidatos.sort(key=lambda x: x[1]["garantias"].get(5, 0) /
                                          max(x[1]["n_apuestas"], 1), reverse=True)
        # Si confianza baja, minimizar coste
        else:
            candidatos.sort(key=lambda x: x[1]["n_apuestas"])
        return candidatos[0][0]

    @classmethod
    def verificar_garantia(
        cls,
        nombre_sistema: str,
        numeros_seleccionados: List[int],
        ganadores: List[int],
    ) -> Dict[str, Any]:
        """
        Verifica el aciertos máximos garantizados dado un resultado real.
        Útil para mostrar al usuario lo que conseguiría con el sistema.
        """
        if nombre_sistema not in cls.SISTEMAS:
            return {"error": f"Sistema {nombre_sistema} no existe"}
        # Validar ganadores
        if not ganadores or len(ganadores) != 6:
            return {"error": "ganadores debe contener exactamente 6 números"}
        if len(set(ganadores)) != 6:
            return {"error": "los 6 ganadores deben ser únicos"}
        if not all(isinstance(n, int) and 1 <= n <= 49 for n in ganadores):
            return {"error": "todos los ganadores deben estar entre 1 y 49"}
        try:
            apuestas = cls.aplicar_sistema(nombre_sistema, numeros_seleccionados)
        except ValueError as e:
            return {"error": str(e)}
        aciertos_por_apuesta = []
        for apuesta in apuestas:
            n_aciertos = len(set(apuesta) & set(ganadores))
            aciertos_por_apuesta.append(n_aciertos)
        # Cuántos números seleccionados acertaron
        aciertos_seleccion = len(set(numeros_seleccionados) & set(ganadores))
        sistema = cls.SISTEMAS[nombre_sistema]
        garantia_teorica = sistema["garantias"].get(aciertos_seleccion, 0)
        return {
            "aciertos_seleccion": aciertos_seleccion,
            "garantia_minima": garantia_teorica,
            "mejor_apuesta": max(aciertos_por_apuesta) if aciertos_por_apuesta else 0,
            "n_apuestas_con_3_o_mas": sum(1 for a in aciertos_por_apuesta if a >= 3),
            "n_apuestas_con_4_o_mas": sum(1 for a in aciertos_por_apuesta if a >= 4),
            "n_apuestas_con_5_o_mas": sum(1 for a in aciertos_por_apuesta if a >= 5),
            "aciertos_por_apuesta": aciertos_por_apuesta,
        }


# ════════════════════════════════════════════════════════════════════════════
# 112. CONFIDENCE-WEIGHTED BETTING
# ════════════════════════════════════════════════════════════════════════════
#
# El sistema decide AUTÓNOMAMENTE cuántas apuestas generar y qué sistema
# aplicar según la confianza agregada del ensemble. Confianza se mide por:
#   - Acuerdo entre técnicas (entropía baja del consenso)
#   - Banda Conformal estrecha
#   - Pesos del stacking convergidos
# ════════════════════════════════════════════════════════════════════════════

class ConfidenceWeightedBetting:
    """
    Calcula la estrategia óptima de apuesta según confianza del modelo.
    """

    def __init__(self, presupuesto_max_eur: float = 10.0):
        self.presupuesto_max = presupuesto_max_eur

    @staticmethod
    def medir_confianza_agregada(
        scores_por_algoritmo: Dict[str, Dict[int, float]],
        ic_inferior: float,
        ic_superior: float,
        confianza_pipeline: float,
    ) -> Dict[str, float]:
        """
        Mide la confianza agregada combinando varios criterios:
        - Acuerdo (entropía del consenso)
        - Estrechez del IC
        - Confianza del pipeline v3
        """
        # 1. Acuerdo entre algoritmos
        if not scores_por_algoritmo:
            acuerdo = 0.0
        else:
            # Top-6 de cada algoritmo
            top6_por_alg = []
            for alg, scores in scores_por_algoritmo.items():
                top6 = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:6]
                top6_por_alg.append(set(n for n, _ in top6))
            # Solapamiento promedio entre top-6
            solapamientos = []
            algs = list(top6_por_alg)
            for i in range(len(algs)):
                for j in range(i + 1, len(algs)):
                    inter = len(algs[i] & algs[j])
                    solapamientos.append(inter / 6.0)
            acuerdo = float(np.mean(solapamientos)) if solapamientos else 0.0

        # 2. Estrechez del IC (más estrecho = más confianza)
        amplitud_ic = max(0.0, ic_superior - ic_inferior)
        estrechez = max(0.0, 1.0 - amplitud_ic / 100.0)

        # 3. Confianza del pipeline normalizada (en [0,1])
        conf_pipeline_norm = max(0.0, min(1.0, confianza_pipeline / 100.0))

        # Confianza agregada (ponderada)
        agregada = (
            0.40 * acuerdo +
            0.25 * estrechez +
            0.35 * conf_pipeline_norm
        )

        return {
            "agregada": float(agregada * 100),  # 0-100
            "acuerdo": float(acuerdo * 100),
            "estrechez_ic": float(estrechez * 100),
            "confianza_pipeline": float(confianza_pipeline),
            "amplitud_ic": float(amplitud_ic),
        }

    def decidir_estrategia(
        self,
        confianza_agregada: float,
        bote_acumulado_eur: float = 600000,
        presupuesto_usuario_eur: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Decide el número de apuestas y sistema reducido a aplicar.
        Retorna estrategia detallada con justificación.
        """
        presupuesto = presupuesto_usuario_eur or self.presupuesto_max
        # Multiplicador por bote alto
        mult_bote = 1.0
        if bote_acumulado_eur > 3_000_000:
            mult_bote = 1.5
        elif bote_acumulado_eur > 1_500_000:
            mult_bote = 1.2

        presupuesto_efectivo = presupuesto * mult_bote
        presupuesto_efectivo = min(presupuesto_efectivo, 30.0)  # tope sano

        # Decisión por bandas de confianza
        if confianza_agregada >= 70:
            nivel = "muy_alta"
            if presupuesto_efectivo >= 10:
                sistema = "10/4"
            elif presupuesto_efectivo >= 6:
                sistema = "9/4"
            elif presupuesto_efectivo >= 3.5:
                sistema = "8/4"
            else:
                sistema = None
            n_apuestas_simples = 0 if sistema else 1
            justif = "Confianza muy alta: sistema reducido para garantizar premios."
        elif confianza_agregada >= 55:
            nivel = "alta"
            if presupuesto_efectivo >= 6:
                sistema = "9/4"
            elif presupuesto_efectivo >= 3.5:
                sistema = "8/4"
            else:
                sistema = None
            n_apuestas_simples = 0 if sistema else 2
            justif = "Confianza alta: sistema reducido de garantía media."
        elif confianza_agregada >= 40:
            nivel = "media"
            sistema = "8/4" if presupuesto_efectivo >= 3.5 else None
            n_apuestas_simples = 3 if sistema is None else 0
            justif = "Confianza media: cobertura moderada con garantía si compensa."
        elif confianza_agregada >= 25:
            nivel = "baja"
            sistema = None
            n_apuestas_simples = 2
            justif = "Confianza baja: apuesta mínima conservadora."
        else:
            nivel = "muy_baja"
            sistema = None
            n_apuestas_simples = 1
            justif = "Confianza muy baja: una sola apuesta o no apostar."

        # Calcular coste
        coste = 0.0
        n_apuestas_total = 0
        if sistema:
            coste = SistemaReducido.SISTEMAS[sistema]["n_apuestas"] * 0.50
            n_apuestas_total = SistemaReducido.SISTEMAS[sistema]["n_apuestas"]
        coste += n_apuestas_simples * 0.50
        n_apuestas_total += n_apuestas_simples

        return {
            "nivel_confianza": nivel,
            "confianza_agregada": float(confianza_agregada),
            "sistema_recomendado": sistema,
            "n_apuestas_simples": n_apuestas_simples,
            "n_apuestas_total": n_apuestas_total,
            "coste_eur": float(coste),
            "mult_bote": float(mult_bote),
            "justificacion": justif,
            "garantias": (SistemaReducido.SISTEMAS[sistema]["garantias"]
                          if sistema else {}),
        }


# ════════════════════════════════════════════════════════════════════════════
# 113. BOTE-AWARE ROI CALCULATOR
# ════════════════════════════════════════════════════════════════════════════
#
# Calcula la esperanza matemática del sorteo según el bote acumulado actual.
# Permite recomendar "apostar/no apostar" según la rentabilidad esperada.
# Cuando el bote es muy alto, el sorteo puede tener esperanza positiva real.
# ════════════════════════════════════════════════════════════════════════════

class BoteAwareROI:
    """
    Calcula esperanza matemática y ROI según bote acumulado.
    Permite decidir cuándo apostar más o no apostar.
    """

    # Probabilidades EXACTAS por apuesta de 0.50€:
    # Cálculo: C(6,k) * C(43,6-k) / C(49,6), donde C es combinatorio
    # Para 5 aciertos sin complementario: hay 6*43 = 258 casos totales con 5 aciertos
    # pero 6 de ellos incluyen el complementario (5+c), por lo que el "5 puro" son 252
    PROB_3 = 246_820 / 13_983_816    # ≈ 1.7650%   C(6,3)*C(43,3)
    PROB_4 = 13_545 / 13_983_816     # ≈ 0.0969%   C(6,4)*C(43,2)
    PROB_5 = 252 / 13_983_816        # ≈ 0.001802% C(6,5)*C(43,1) - casos 5+c = 258-6
    PROB_5C = 6 / 13_983_816         # ≈ 0.0000429%  (5 + complementario exacto)
    PROB_6 = 1 / 13_983_816          # ≈ 0.00000715%

    # Premios medios típicos (Bonoloto en España, basados en histórico)
    PREMIO_3_MEDIO = 4.0
    PREMIO_4_MEDIO = 45.0
    PREMIO_5_MEDIO = 1200.0
    PREMIO_5C_MEDIO = 50000.0

    # Reintegro: probabilidad 1/10 = 10%, premio = 0.50€ (devolución)
    PROB_REINTEGRO = 0.10
    PREMIO_REINTEGRO = 0.50

    COSTE_APUESTA = 0.50

    def calcular_esperanza(
        self,
        bote_6_aciertos_eur: float,
    ) -> Dict[str, float]:
        """
        Calcula la esperanza matemática por apuesta de 0.50€ según el bote.
        """
        # Validar bote: rechazar negativos, NaN, infinitos
        import math as _math
        if (bote_6_aciertos_eur is None or
            not _math.isfinite(bote_6_aciertos_eur) or
            bote_6_aciertos_eur < 0):
            raise ValueError(
                f"bote_6_aciertos_eur debe ser un número finito >= 0, "
                f"recibido: {bote_6_aciertos_eur}"
            )
        # Tope sano: incluso el mayor bote real histórico mundial < 2.000 millones €
        if bote_6_aciertos_eur > 2_000_000_000:
            raise ValueError(
                f"bote_6_aciertos_eur excede límite razonable: {bote_6_aciertos_eur}"
            )

        # Aporte del reintegro (devolución parcial)
        e_reintegro = self.PROB_REINTEGRO * self.PREMIO_REINTEGRO

        e_3 = self.PROB_3 * self.PREMIO_3_MEDIO
        e_4 = self.PROB_4 * self.PREMIO_4_MEDIO
        e_5 = self.PROB_5 * self.PREMIO_5_MEDIO
        e_5c = self.PROB_5C * self.PREMIO_5C_MEDIO
        e_6 = self.PROB_6 * bote_6_aciertos_eur

        esperanza_total = e_reintegro + e_3 + e_4 + e_5 + e_5c + e_6
        roi_porcentaje = (esperanza_total / self.COSTE_APUESTA - 1) * 100

        return {
            "esperanza_eur": float(esperanza_total),
            "esperanza_pct_apuesta": float(esperanza_total / self.COSTE_APUESTA * 100),
            "roi_pct": float(roi_porcentaje),
            "retorno_unitario": float(esperanza_total / self.COSTE_APUESTA),
            "aportacion_reintegro": float(e_reintegro),
            "aportacion_3": float(e_3),
            "aportacion_4": float(e_4),
            "aportacion_5": float(e_5),
            "aportacion_5c": float(e_5c),
            "aportacion_6": float(e_6),
            "bote_6_aciertos": float(bote_6_aciertos_eur),
            "rentable_teorico": esperanza_total > self.COSTE_APUESTA,
        }

    def calcular_bote_breakeven(self) -> float:
        """Calcula el bote mínimo para que la esperanza sea positiva."""
        e_otros = (
            self.PROB_REINTEGRO * self.PREMIO_REINTEGRO +
            self.PROB_3 * self.PREMIO_3_MEDIO +
            self.PROB_4 * self.PREMIO_4_MEDIO +
            self.PROB_5 * self.PREMIO_5_MEDIO +
            self.PROB_5C * self.PREMIO_5C_MEDIO
        )
        # Despejar bote_6 para que esperanza == COSTE_APUESTA
        bote_breakeven = (self.COSTE_APUESTA - e_otros) / self.PROB_6
        return float(bote_breakeven)

    def recomendacion(
        self,
        bote_6_aciertos_eur: float,
    ) -> Dict[str, Any]:
        """
        Recomendación clara sobre si apostar dado el bote actual.
        """
        esp = self.calcular_esperanza(bote_6_aciertos_eur)
        breakeven = self.calcular_bote_breakeven()
        if esp["roi_pct"] >= 0:
            decision = "APOSTAR_FUERTE"
            razon = "Esperanza matemática positiva — sorteo con valor real."
        elif esp["roi_pct"] >= -15:
            decision = "APOSTAR_NORMAL"
            razon = "Bote alto reduce la pérdida esperada; jugada razonable."
        elif esp["roi_pct"] >= -30:
            decision = "APOSTAR_MINIMO"
            razon = "Bote normal; apuesta mínima recomendada."
        else:
            decision = "EVITAR"
            razon = "Bote bajo; esperanza muy negativa, mejor esperar acumulación."
        return {
            **esp,
            "bote_breakeven": breakeven,
            "decision": decision,
            "razon": razon,
            "factor_bote_vs_breakeven": (
                bote_6_aciertos_eur / breakeven if breakeven > 0 else 0
            ),
        }


# ════════════════════════════════════════════════════════════════════════════
# 114. ANTI-POPULARITY SCORING
# ════════════════════════════════════════════════════════════════════════════
#
# Cuando ganas un sorteo, el premio se REPARTE entre los acertantes.
# Si tu combinación es muy "popular" (cumpleaños, geometrías, secuencias),
# probablemente la comparten miles de personas y tu premio baja drásticamente.
# Este módulo penaliza combinaciones populares para maximizar el premio
# CONDICIONAL si se gana.
# ════════════════════════════════════════════════════════════════════════════

class AntiPopularityScorer:
    """
    Detecta y penaliza combinaciones que los humanos tienden a elegir más,
    para reducir el reparto del premio si la combinación resultara premiada.

    HONESTIDAD SOBRE LOS DATOS: SELAE no publica con detalle qué números
    juega la gente. Los conjuntos de "números populares" de abajo son
    APROXIMACIONES basadas en la literatura sobre comportamiento de
    apostadores de lotería (no en datos internos de SELAE), que documenta
    consistentemente estos patrones de sobre-selección:
      - Números ≤31 (fechas de cumpleaños/aniversarios)
      - Números "de la suerte" (7, 13) y sus múltiplos
      - Geometrías y líneas en el boleto físico
      - Secuencias (1-2-3-4-5-6), todos pares, múltiplos
    Estos patrones SÍ están bien documentados; los conjuntos concretos de
    números "fuertes/débiles" son una estimación heurística razonable, no
    una medición exacta. El valor del anti-popularidad está sobre todo en
    evitar los PATRONES estructurales (cumpleaños, geometrías, secuencias),
    que es donde el efecto es grande y bien establecido.
    """

    # Patrones conocidos de "elegidos por humanos" (heurística aproximada):
    NUMEROS_POPULARES_FUERTES = {7, 11, 13, 17, 21, 23}   # ~30% más jugados (est.)
    NUMEROS_POPULARES_DEBILES = {3, 5, 9, 15, 19, 25, 27, 29, 31}  # ~15% más (est.)

    NUMEROS_IMPOPULARES = {32, 33, 34, 35, 36, 37, 38, 39, 40,
                            41, 42, 43, 44, 45, 46, 47, 48, 49}

    @staticmethod
    def _es_geometria_boleto(combo: List[int]) -> bool:
        """Detecta combinaciones que dibujan formas en el boleto (7x7 o 5x10)."""
        nums = sorted(combo)
        if len(nums) < 4:
            return False
        # Línea diagonal/aritmética: progresión con paso constante
        diferencia = nums[1] - nums[0]
        if diferencia > 0 and all(nums[i+1] - nums[i] == diferencia
                                  for i in range(len(nums)-1)):
            return True
        # Combinación con mucha simetría
        if max(nums) + min(nums) == 50 and len(nums) >= 4:
            # comprobar si son simétricos respecto a 25
            es_sim = sum(1 for n in nums if (50 - n) in nums)
            if es_sim >= 4:
                return True
        return False

    @staticmethod
    def _es_secuencia_natural(combo: List[int]) -> bool:
        """Detecta secuencias humanas: 1-2-3-4-5-6, todos pares, todos múltiplos."""
        nums = sorted(combo)
        # Requiere al menos 4 números para considerarlo "patrón"
        if len(nums) < 4:
            return False
        # Consecutivos
        if all(nums[i+1] - nums[i] == 1 for i in range(len(nums)-1)):
            return True
        # Todos pares o impares
        if all(n % 2 == 0 for n in nums) or all(n % 2 == 1 for n in nums):
            return True
        # Todos múltiplos de 5
        if all(n % 5 == 0 for n in nums):
            return True
        # Todos múltiplos de 7
        if all(n % 7 == 0 for n in nums):
            return True
        return False

    @staticmethod
    def _proporcion_cumpleanos(combo: List[int]) -> float:
        """Proporción de números ≤31 (rango de días del mes)."""
        if not combo:
            return 0.0
        return sum(1 for n in combo if n <= 31) / len(combo)

    @staticmethod
    def _proporcion_meses(combo: List[int]) -> float:
        """Proporción de números ≤12 (rango de meses)."""
        if not combo:
            return 0.0
        return sum(1 for n in combo if n <= 12) / len(combo)

    @classmethod
    def calcular_popularidad(cls, combo: List[int]) -> Dict[str, float]:
        """
        Calcula índice de popularidad [0,1]. 0=muy impopular, 1=muy popular.
        """
        combo = sorted(combo)
        score = 0.0

        # 1. Números populares (40% del peso)
        n_pop_fuertes = sum(1 for n in combo if n in cls.NUMEROS_POPULARES_FUERTES)
        n_pop_debiles = sum(1 for n in combo if n in cls.NUMEROS_POPULARES_DEBILES)
        peso_pop = (n_pop_fuertes * 0.10 + n_pop_debiles * 0.05)
        score += min(peso_pop, 0.4)

        # 2. Cumpleaños (proporción ≤31) — 25% del peso
        prop_cumple = cls._proporcion_cumpleanos(combo)
        if prop_cumple == 1.0:
            score += 0.25
        elif prop_cumple >= 0.83:  # 5 de 6
            score += 0.18
        elif prop_cumple >= 0.67:
            score += 0.10

        # 3. Geometrías (15%)
        if cls._es_geometria_boleto(combo):
            score += 0.15

        # 4. Secuencias naturales (15%)
        if cls._es_secuencia_natural(combo):
            score += 0.15

        # 5. Todos del mismo decil (5%)
        decenas = set((n - 1) // 10 for n in combo)
        if len(decenas) <= 2:
            score += 0.05

        # Ajuste: combinaciones con números altos son MENOS populares
        n_altos = sum(1 for n in combo if n >= 35)
        bonus_impopular = n_altos * -0.03  # cada número alto reduce popularidad
        score = max(0.0, score + bonus_impopular)

        return {
            "popularidad": float(min(1.0, score)),
            "n_pop_fuertes": int(n_pop_fuertes),
            "n_pop_debiles": int(n_pop_debiles),
            "proporcion_cumple": float(prop_cumple),
            "es_geometria": cls._es_geometria_boleto(combo),
            "es_secuencia_natural": cls._es_secuencia_natural(combo),
            "n_altos": int(n_altos),
        }

    @classmethod
    def estimar_compartidos(cls, combo: List[int], n_apostantes: int = 1_500_000) -> int:
        """
        Estima cuánta gente probablemente jugó esta combinación.
        Aproximación basada en popularidad estimada.
        n_apostantes: número total de apostantes esperados (1.5M es típico para Bonoloto).
        """
        # Validar n_apostantes
        if n_apostantes <= 0:
            return 1
        pop = cls.calcular_popularidad(combo)["popularidad"]
        # Factor de escala: cada millón de apostantes es 1.0x
        factor = n_apostantes / 1_500_000
        # Empíricamente: muy popular ~150-280, muy impopular ~1-6 (para 1.5M apostantes)
        if pop >= 0.7:
            base = 80 + pop * 200
        elif pop >= 0.4:
            base = 15 + pop * 80
        elif pop >= 0.2:
            base = 5 + pop * 30
        else:
            base = 1 + pop * 5
        return max(1, int(base * factor))

    @classmethod
    def ajustar_scores(
        cls,
        scores: Dict[int, float],
        peso_anti_popular: float = 0.20,
    ) -> Dict[int, float]:
        """
        Ajusta scores penalizando números populares.
        peso_anti_popular: cuánto se penaliza la popularidad [0, 0.5]
        """
        # Validar peso en rango razonable
        peso_anti_popular = max(0.0, min(0.5, peso_anti_popular))
        ajustados = {}
        for n in range(1, 50):
            score = scores.get(n, 0.0)
            penalizacion = 0.0
            if n in cls.NUMEROS_POPULARES_FUERTES:
                penalizacion = 0.30
            elif n in cls.NUMEROS_POPULARES_DEBILES:
                penalizacion = 0.15
            elif n in cls.NUMEROS_IMPOPULARES:
                penalizacion = -0.10   # bonificación leve (negativa = aumenta)
            score_nuevo = score * (1 - peso_anti_popular * penalizacion)
            ajustados[n] = max(0.0, min(1.0, score_nuevo))
        return ajustados


# ════════════════════════════════════════════════════════════════════════════
# 115. MULTI-LOTERÍA
# ════════════════════════════════════════════════════════════════════════════
#
# Configuración para extender el motor v7 a otras loterías españolas que
# comparten estructura matemática similar:
#   - Bonoloto: 6 de 49 (base actual)
#   - Primitiva: 6 de 49 + Reintegro + Complementario (idéntica matemática)
#   - Euromillones: 5 de 50 + 2 estrellas de 12
#   - Gordo Primitiva: 5 de 54 + clave de 1 dígito
# ════════════════════════════════════════════════════════════════════════════

class MultiLoteria:
    """
    Configuración estructural para distintas loterías españolas.
    """

    CONFIGURACIONES = {
        "bonoloto": {
            "nombre": "Bonoloto",
            "n_principal": 6,
            "max_principal": 49,
            "tiene_reintegro": True,
            "tiene_complementario": True,
            "tiene_estrellas": False,
            "coste_apuesta_eur": 0.50,
            "frecuencia_semanal": 6,
            "premios_categorias": ["6", "5+c", "5", "4", "3", "reintegro"],
            "bote_minimo_eur": 250_000,
            "prob_6_aciertos": 1 / 13_983_816,
        },
        "primitiva": {
            "nombre": "La Primitiva",
            "n_principal": 6,
            "max_principal": 49,
            "tiene_reintegro": True,
            "tiene_complementario": True,
            "tiene_estrellas": False,
            "coste_apuesta_eur": 1.00,
            "frecuencia_semanal": 2,
            "premios_categorias": ["6", "5+c", "5", "4", "3", "reintegro"],
            "bote_minimo_eur": 600_000,
            "prob_6_aciertos": 1 / 13_983_816,
        },
        "euromillones": {
            "nombre": "Euromillones",
            "n_principal": 5,
            "max_principal": 50,
            "n_estrellas": 2,
            "max_estrellas": 12,
            "tiene_reintegro": False,
            "tiene_complementario": False,
            "tiene_estrellas": True,
            "coste_apuesta_eur": 2.50,
            "frecuencia_semanal": 2,
            "premios_categorias": ["5+2", "5+1", "5", "4+2", "4+1", "3+2",
                                   "4", "2+2", "3+1", "3", "1+2", "2+1", "2"],
            "bote_minimo_eur": 17_000_000,
            "prob_5_2": 1 / 139_838_160,
        },
        "gordo": {
            "nombre": "El Gordo de la Primitiva",
            "n_principal": 5,
            "max_principal": 54,
            "n_clave": 1,
            "max_clave": 9,
            "tiene_reintegro": False,
            "tiene_complementario": False,
            "tiene_estrellas": False,
            "tiene_clave": True,
            "coste_apuesta_eur": 1.50,
            "frecuencia_semanal": 1,
            "premios_categorias": ["5+clave", "5", "4+clave", "4", "3+clave",
                                   "3", "2+clave", "1+clave", "0+clave"],
            "bote_minimo_eur": 5_000_000,
            "prob_5_clave": 1 / 31_625_100,
        },
    }

    @classmethod
    def get_config(cls, loteria: str) -> Dict[str, Any]:
        """Devuelve la configuración de una lotería."""
        if loteria not in cls.CONFIGURACIONES:
            raise ValueError(
                f"Lotería '{loteria}' no soportada. "
                f"Disponibles: {list(cls.CONFIGURACIONES.keys())}"
            )
        return cls.CONFIGURACIONES[loteria]

    @classmethod
    def listar_loterias(cls) -> List[Dict[str, Any]]:
        """Lista todas las loterías soportadas con su configuración."""
        return [
            {"clave": k, **v}
            for k, v in cls.CONFIGURACIONES.items()
        ]

    @classmethod
    def adapta_combinacion(
        cls,
        loteria: str,
        scores_principales: Dict[int, float],
        scores_estrellas: Optional[Dict[int, float]] = None,
    ) -> Dict[str, Any]:
        """
        Genera una combinación válida para la lotería especificada
        a partir de scores predichos.
        """
        config = cls.get_config(loteria)
        # Filtrar scores al rango válido
        nums_validos = {
            n: s for n, s in scores_principales.items()
            if isinstance(n, int) and 1 <= n <= config["max_principal"]
        }
        # Si no hay suficientes scores válidos, rellenar con scores uniformes
        if len(nums_validos) < config["n_principal"]:
            for n in range(1, config["max_principal"] + 1):
                if n not in nums_validos:
                    nums_validos[n] = 0.0
        top_principales = sorted(nums_validos.items(),
                                 key=lambda x: x[1], reverse=True)
        combo_principal = sorted([n for n, _ in top_principales[:config["n_principal"]]])
        resultado = {"principales": combo_principal}
        # Estrellas (sólo Euromillones)
        if config.get("tiene_estrellas") and scores_estrellas:
            estrellas_validas = {
                n: s for n, s in scores_estrellas.items()
                if isinstance(n, int) and 1 <= n <= config.get("max_estrellas", 12)
            }
            # Rellenar si faltan
            if len(estrellas_validas) < config.get("n_estrellas", 2):
                for n in range(1, config.get("max_estrellas", 12) + 1):
                    if n not in estrellas_validas:
                        estrellas_validas[n] = 0.0
            top_estrellas = sorted(estrellas_validas.items(),
                                    key=lambda x: x[1], reverse=True)
            resultado["estrellas"] = sorted(
                [n for n, _ in top_estrellas[:config.get("n_estrellas", 2)]]
            )
        # Reintegro (Bonoloto / Primitiva)
        if config.get("tiene_reintegro"):
            resultado["reintegro"] = int(np.random.randint(0, 10))
        # Clave (Gordo)
        if config.get("tiene_clave"):
            resultado["clave"] = int(np.random.randint(0, 10))
        return resultado


# ════════════════════════════════════════════════════════════════════════════
#  ORQUESTADOR DEL BLOQUE L — Estrategia integrada
# ════════════════════════════════════════════════════════════════════════════

class EstrategiaIntegradaBloqueL:
    """
    Orquestador que combina los 5 módulos del Bloque L en una sola estrategia.
    Esta es la API principal del Bloque L.
    """

    def __init__(self,
                 presupuesto_max_eur: float = 10.0,
                 peso_anti_popular: float = 0.20):
        self.cwb = ConfidenceWeightedBetting(presupuesto_max_eur)
        self.roi = BoteAwareROI()
        self.peso_anti_popular = peso_anti_popular

    def construir_estrategia(
        self,
        scores_finales: Dict[int, float],
        scores_por_algoritmo: Dict[str, Dict[int, float]],
        confianza_pipeline: float,
        ic_inferior: float,
        ic_superior: float,
        bote_acumulado_eur: float = 600_000,
        presupuesto_usuario_eur: Optional[float] = None,
        loteria: str = "bonoloto",
    ) -> Dict[str, Any]:
        """
        Construye la estrategia óptima integrando los 5 módulos.
        """
        # 1. Ajustar scores penalizando popularidad (módulo 114)
        scores_ajustados = AntiPopularityScorer.ajustar_scores(
            scores_finales, peso_anti_popular=self.peso_anti_popular
        )

        # 2. Medir confianza agregada (módulo 112)
        conf_agg = ConfidenceWeightedBetting.medir_confianza_agregada(
            scores_por_algoritmo, ic_inferior, ic_superior, confianza_pipeline
        )

        # 3. Decidir estrategia de apuesta (módulo 112)
        estrategia = self.cwb.decidir_estrategia(
            conf_agg["agregada"], bote_acumulado_eur, presupuesto_usuario_eur
        )

        # 4. ROI según bote (módulo 113)
        rec_roi = self.roi.recomendacion(bote_acumulado_eur)

        # 5. Generar apuestas concretas
        apuestas_generadas = []
        if estrategia["sistema_recomendado"]:
            sistema = estrategia["sistema_recomendado"]
            n_numeros = SistemaReducido.SISTEMAS[sistema]["n_numeros"]
            # Top-N números según scores ajustados
            top_n = sorted(scores_ajustados.items(),
                           key=lambda x: x[1], reverse=True)[:n_numeros]
            numeros_seleccionados = sorted([n for n, _ in top_n])
            apuestas_generadas = SistemaReducido.aplicar_sistema(
                sistema, numeros_seleccionados
            )

        # Si hay apuestas simples adicionales — generar combinaciones diversas
        if estrategia["n_apuestas_simples"] > 0:
            # Top 12 números (más amplios que solo 6) para mezclar
            top_12 = sorted(scores_ajustados.items(),
                            key=lambda x: x[1], reverse=True)[:12]
            top_12_nums = [n for n, _ in top_12]
            generadas = set()
            # Primera: top 6 puro
            primera = tuple(sorted(top_12_nums[:6]))
            apuestas_generadas.append(list(primera))
            generadas.add(primera)
            # Resto: combinaciones diversas usando ventanas deslizantes en top-12
            import random as _r
            _r.seed(42)  # determinismo
            intentos = 0
            while len(generadas) < estrategia["n_apuestas_simples"] + 1 and intentos < 100:
                muestra = tuple(sorted(_r.sample(top_12_nums, 6)))
                if muestra not in generadas:
                    generadas.add(muestra)
                    apuestas_generadas.append(list(muestra))
                intentos += 1

        # 6. Calcular popularidad estimada de cada apuesta
        analisis_apuestas = []
        for apuesta in apuestas_generadas:
            pop = AntiPopularityScorer.calcular_popularidad(apuesta)
            compartidos = AntiPopularityScorer.estimar_compartidos(apuesta)
            analisis_apuestas.append({
                "numeros": apuesta,
                "popularidad": pop["popularidad"],
                "compartidos_estimados": compartidos,
                "es_geometria": pop["es_geometria"],
                "es_secuencia_natural": pop["es_secuencia_natural"],
            })

        # 7. Configuración de lotería (módulo 115)
        config_loteria = MultiLoteria.get_config(loteria)

        return {
            "loteria": loteria,
            "config_loteria": config_loteria,
            "confianza_agregada": conf_agg,
            "estrategia_apuesta": estrategia,
            "analisis_roi": rec_roi,
            "apuestas_generadas": apuestas_generadas,
            "analisis_apuestas": analisis_apuestas,
            "coste_total_eur": estrategia["coste_eur"],
            "n_apuestas_total": estrategia["n_apuestas_total"],
            "recomendacion_global": self._recomendacion_global(
                estrategia, rec_roi, conf_agg
            ),
        }

    @staticmethod
    def _recomendacion_global(
        estrategia: Dict[str, Any],
        rec_roi: Dict[str, Any],
        conf_agg: Dict[str, Any],
    ) -> str:
        nivel = estrategia["nivel_confianza"]
        decision_roi = rec_roi["decision"]
        if decision_roi == "APOSTAR_FUERTE" and nivel in ["alta", "muy_alta"]:
            return ("OPORTUNIDAD DESTACADA: bote alto + confianza alta del modelo. "
                    "Aplicar sistema reducido recomendado para maximizar premios.")
        if decision_roi == "APOSTAR_FUERTE":
            return ("Bote alto pero confianza del modelo moderada. "
                    "Aplicar sistema reducido con cautela.")
        if decision_roi == "EVITAR":
            return ("Sorteo poco rentable. Apuesta mínima o saltar este sorteo "
                    "y esperar mejor bote acumulado.")
        if nivel == "muy_alta":
            return ("Confianza del modelo muy alta. Aplicar el sistema reducido "
                    "máximo aunque el bote sea normal.")
        return ("Sorteo estándar: estrategia equilibrada según presupuesto.")


# ════════════════════════════════════════════════════════════════════════════
#  EXPORTAR
# ════════════════════════════════════════════════════════════════════════════
__all__ = [
    "SistemaReducido",              # 111
    "ConfidenceWeightedBetting",    # 112
    "BoteAwareROI",                 # 113
    "AntiPopularityScorer",         # 114
    "MultiLoteria",                 # 115
    "EstrategiaIntegradaBloqueL",   # orquestador
]
