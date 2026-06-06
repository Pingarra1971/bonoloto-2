"""
╔══════════════════════════════════════════════════════════════════════╗
║   BONOLOTO AI — ALGORITMOS AVANZADOS RONDA 2                       ║
║                                                                      ║
║   83. MaxEnt — Principio de Máxima Entropía                        ║
║   84. Shapley para atribución de algoritmos                         ║
║   85. N-BEATS simplificado (basis expansion)                        ║
║   86. Análisis de cuantiles extremos (tail risk)                    ║
║   87. Aprendizaje por curriculum (curriculum learning)              ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import math
import random
import logging
from collections import defaultdict
from typing import Dict, List, Tuple, Optional
from itertools import combinations

import numpy as np

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════
# 83 — MAXENT: PRINCIPIO DE MÁXIMA ENTROPÍA
# ═══════════════════════════════════════════════════════════════════════
class AnalizadorMaxEnt:
    """
    Principio de Máxima Entropía: de todas las distribuciones de
    probabilidad compatibles con las restricciones observadas del
    histórico, selecciona la que maximiza la entropía de Shannon.
    Es la distribución más honesta dado lo que sabemos.

    Restricciones usadas:
    - Frecuencia media de cada número (6/49 esperada)
    - Momentos de primer y segundo orden observados
    - Restricciones de co-ocurrencia significativas
    """

    def __init__(self, historico: List[List[int]]):
        self.historico = historico
        self.n = len(historico)

    def _calcular_restricciones(self) -> Dict[str, float]:
        """Extrae restricciones estadísticas del histórico."""
        restricciones = {}

        # Frecuencias observadas
        freq = defaultdict(int)
        for s in self.historico:
            for n in s:
                freq[n] += 1

        total = sum(freq.values())
        for n in range(1, 50):
            restricciones[f'freq_{n}'] = freq.get(n, 0) / max(total, 1)

        # Momento de segundo orden: suma media
        sumas = [sum(s) for s in self.historico]
        restricciones['suma_media'] = sum(sumas) / max(len(sumas), 1)
        restricciones['suma_var'] = (sum(x**2 for x in sumas) / max(len(sumas), 1)
                                     - restricciones['suma_media']**2)

        return restricciones

    def _distribucion_maxent(self, restricciones: Dict) -> Dict[int, float]:
        """
        Calcula distribución MaxEnt usando multiplicadores de Lagrange.
        Implementación iterativa (iterative scaling).
        """
        # Inicializar con distribución uniforme
        p = {n: 1.0/49 for n in range(1, 50)}
        freq_obj = {n: restricciones.get(f'freq_{n}', 6/49/6)
                    for n in range(1, 50)}
        suma_obj = restricciones.get('suma_media', 150)

        # Iterative proportional fitting (IPF) — 100 iteraciones
        for iteracion in range(100):
            # Ajustar según frecuencias observadas
            total_p = sum(p.values())
            if total_p <= 0:
                # Reset a distribución uniforme
                p = {n: 1.0 / 49 for n in range(1, 50)}
                total_p = 1.0
            for n in range(1, 50):
                # Factor de corrección: ratio objetivo/actual
                p_actual = p[n] / total_p
                objetivo = freq_obj[n]
                if p_actual > 1e-10:
                    factor = (objetivo / p_actual) ** 0.1  # Paso conservador
                    p[n] *= factor

            # Ajustar según restricción de suma
            suma_actual = sum(n * p[n] for n in range(1, 50))
            total_p = sum(p.values())
            if total_p > 0 and suma_actual > 0:
                # Corrección proporcional a la distancia del número a la media objetivo
                error_suma = suma_obj - suma_actual / total_p
                for n in range(1, 50):
                    # Números más cerca del objetivo de suma reciben más peso
                    dist_suma = abs(n - suma_obj / 6)
                    p[n] *= (1 + 0.001 * error_suma / (dist_suma + 1))

            # Renormalizar
            total_p = sum(p.values())
            if total_p > 0:
                p = {n: v/total_p for n, v in p.items()}

            # Verificar convergencia
            if iteracion > 20:
                entropia = -sum(v * math.log(v + 1e-10) for v in p.values())
                max_entropia = math.log(49)
                if abs(entropia - max_entropia) / max_entropia < 0.001:
                    break

        return p

    def calcular_scores(self) -> Dict[int, float]:
        """
        Scores MaxEnt: distribución de máxima entropía compatibles
        con las frecuencias históricas observadas.
        """
        restricciones = self._calcular_restricciones()
        p_maxent = self._distribucion_maxent(restricciones)

        # Comparar con distribución uniforme: números más probados que uniforme
        uniforme = 1.0 / 49
        scores = {}
        for n in range(1, 50):
            # Ratio respecto a uniforme
            scores[n] = p_maxent[n] / max(uniforme, 1e-10)

        max_v = max(scores.values(), default=1)
        if max_v > 0:
            scores = {n: v/max_v for n, v in scores.items()}
        return scores


# ═══════════════════════════════════════════════════════════════════════
# 84 — SHAPLEY PARA ATRIBUCIÓN DE ALGORITMOS
# ═══════════════════════════════════════════════════════════════════════
class AtribucionShapley:
    """
    Valores de Shapley para atribuir equitativamente qué algoritmos
    contribuyen más al consenso final.
    Sustituye al sistema de pesos estático con una asignación
    matemáticamente fundamentada en teoría de juegos cooperativos.

    Complejidad: O(2^n * n) — limitamos a subconjuntos muestreados.
    """

    def __init__(self, n_muestras: int = 500):
        self.n_muestras = n_muestras

    def _funcion_valor(
        self,
        subconjunto: List[str],
        scores_por_algoritmo: Dict[str, Dict[int, float]],
        resultado_real: Optional[List[int]] = None,
    ) -> float:
        """
        Función característica v(S): valor de la coalición S.
        Si hay resultado real: precisión de la predicción.
        Sin resultado: cohesión interna (varianza del consenso).
        """
        if not subconjunto:
            return 0.0

        # Consenso del subconjunto
        consenso = defaultdict(float)
        for alg in subconjunto:
            scores = scores_por_algoritmo.get(alg, {})
            for n, s in scores.items():
                consenso[n] += s / len(subconjunto)

        if resultado_real:
            # Precisión: qué porcentaje del top-15 predicho coincide con el real
            top_15 = sorted(consenso, key=consenso.get, reverse=True)[:15]
            return sum(1 for n in resultado_real if n in top_15) / max(len(resultado_real), 1)
        else:
            # Cohesión: inverso de la varianza (consenso fuerte = buena señal)
            vals = list(consenso.values())
            if not vals:
                return 0.0
            media = sum(vals) / len(vals)
            varianza = sum((v - media)**2 for v in vals) / len(vals)
            return 1.0 / (1.0 + varianza * 10)

    def calcular_shapley(
        self,
        scores_por_algoritmo: Dict[str, Dict[int, float]],
        resultado_real: Optional[List[int]] = None,
    ) -> Dict[str, float]:
        """
        Calcula valores de Shapley para cada algoritmo usando
        muestreo Monte Carlo (aproximación en O(n * n_muestras)).
        """
        algoritmos = list(scores_por_algoritmo.keys())
        n = len(algoritmos)
        if n == 0:
            return {}

        shapley_vals = defaultdict(float)

        for _ in range(self.n_muestras):
            # Permutación aleatoria de algoritmos
            perm = random.sample(algoritmos, n)
            coalicion = []

            for alg in perm:
                # Valor sin el algoritmo
                v_sin = self._funcion_valor(coalicion, scores_por_algoritmo, resultado_real)
                coalicion.append(alg)
                # Valor con el algoritmo
                v_con = self._funcion_valor(coalicion, scores_por_algoritmo, resultado_real)
                # Contribución marginal
                shapley_vals[alg] += (v_con - v_sin) / self.n_muestras

        # Normalizar para que sumen 1 (como pesos)
        total = sum(max(0, v) for v in shapley_vals.values())
        if total > 0:
            return {alg: max(0, v)/total for alg, v in shapley_vals.items()}
        return {alg: 1.0/n for alg in algoritmos}


# ═══════════════════════════════════════════════════════════════════════
# 85 — N-BEATS SIMPLIFICADO (Basis Expansion)
# ═══════════════════════════════════════════════════════════════════════
class AnalizadorNBEATS:
    """
    N-BEATS simplificado: descompone la serie temporal en bases
    de tendencia (polinomios) y estacionalidad (senos/cosenos).
    Arquitectura interpretable sin backprop — regresión lineal pura.
    """

    def __init__(self, historico: List[List[int]]):
        self.historico = historico
        self.n = len(historico)

    def _base_tendencia(self, n: int, grado: int = 3) -> np.ndarray:
        """Base polinomial para capturar tendencias."""
        t = np.linspace(0, 1, n)
        return np.column_stack([t**i for i in range(grado + 1)])

    def _base_estacionalidad(self, n: int, periodos: int = 4) -> np.ndarray:
        """Base sinusoidal para capturar estacionalidad."""
        t = np.linspace(0, 2 * np.pi, n)
        bases = []
        for k in range(1, periodos + 1):
            bases.append(np.sin(k * t))
            bases.append(np.cos(k * t))
        return np.column_stack(bases)

    def _ajustar_nbeats(self, serie: np.ndarray) -> Tuple[float, float]:
        """
        Ajusta N-BEATS y devuelve (pred_tendencia, pred_estacional).
        Usa mínimos cuadrados OLS — completamente lineal.
        """
        n = len(serie)
        if n < 10:
            return float(serie.mean()), 0.5

        # Stack de bases
        B_tend = self._base_tendencia(n, grado=2)
        B_seas = self._base_estacionalidad(n, periodos=3)
        B = np.hstack([B_tend, B_seas])

        try:
            # OLS: coef = (B'B)^{-1} B'y
            reg = 1e-4 * np.eye(B.shape[1])
            coef = np.linalg.solve(B.T @ B + reg, B.T @ serie)

            # Extrapolación para el siguiente punto
            t_next = np.array([[1.0, 1.0, 1.0,  # tendencia t=1
                                 np.sin(np.pi * 2),
                                 np.cos(np.pi * 2),
                                 np.sin(np.pi * 4),
                                 np.cos(np.pi * 4),
                                 np.sin(np.pi * 6),
                                 np.cos(np.pi * 6)]])

            pred = float(t_next @ coef[:t_next.shape[1]])
            return pred, float(np.mean(serie[-5:]))
        except Exception:
            return float(serie.mean()), 0.5

    def calcular_scores(self) -> Dict[int, float]:
        scores = {}
        ventana = min(150, self.n)

        for num in range(1, 50):
            serie = np.array([1.0 if num in s else 0.0
                             for s in self.historico[:ventana]])
            if len(serie) < 10:
                scores[num] = 0.5
                continue

            pred_global, pred_reciente = self._ajustar_nbeats(serie)
            # Combinar predicción global y reciente
            pred = 0.6 * pred_global + 0.4 * pred_reciente
            scores[num] = max(0.0, min(1.0, pred + 0.5))

        max_v = max(scores.values(), default=1)
        if max_v > 0:
            scores = {n: v/max_v for n, v in scores.items()}
        return scores


# ═══════════════════════════════════════════════════════════════════════
# 86 — ANÁLISIS DE CUANTILES EXTREMOS (Tail Risk)
# ═══════════════════════════════════════════════════════════════════════
class AnalizadorCuantilesExtremos:
    """
    Analiza el comportamiento en las colas de la distribución de
    apariciones de cada número. Un número cuya tasa de aparición
    reciente está en el percentil 95+ de su distribución histórica
    tiene una señal de "sobreactividad" estadística.
    """

    def __init__(self, historico: List[List[int]]):
        self.historico = historico
        self.n = len(historico)

    def _cuantiles_ventanas(self, num: int,
                             tam_ventana: int = 20) -> float:
        """
        Calcula la distribución de tasas de aparición por ventanas.
        Devuelve el percentil [0,1] que ocupa la tasa actual respecto al histórico.
        """
        if tam_ventana <= 0 or self.n < tam_ventana * 2:
            return 0.5
        tasas = []
        for i in range(0, self.n - tam_ventana, tam_ventana // 2):
            ventana = self.historico[i:i + tam_ventana]
            tasa = sum(1 for s in ventana if num in s) / tam_ventana
            tasas.append(tasa)

        if len(tasas) < 4:
            return 0.5

        # Tasa actual (última ventana, índice 0 = más reciente)
        tasa_actual = sum(1 for s in self.historico[:tam_ventana] if num in s) / tam_ventana

        # Score: qué percentil ocupa la tasa actual en la distribución histórica
        percentil = sum(1 for t in tasas if t <= tasa_actual) / max(len(tasas), 1)
        return percentil

    def calcular_scores(self) -> Dict[int, float]:
        scores = {}
        for num in range(1, 50):
            percentil = self._cuantiles_ventanas(num)
            # Números en percentil extremo bajo (muy fríos) o muy recientes
            # Penalizar los extremos y premiar los moderados
            if percentil < 0.10:
                # Muy frío — probabilidad alta de aparecer pronto
                scores[num] = 0.8
            elif percentil > 0.90:
                # Muy caliente — puede estar en racha pero también puede corregir
                scores[num] = 0.6
            else:
                # Normal — score proporcional
                scores[num] = 0.4 + 0.3 * percentil

        max_v = max(scores.values(), default=1)
        if max_v > 0:
            scores = {n: v/max_v for n, v in scores.items()}
        return scores


# ═══════════════════════════════════════════════════════════════════════
# 87 — CURRICULUM LEARNING ADAPTATIVO
# ═══════════════════════════════════════════════════════════════════════
class AnalizadorCurriculumLearning:
    """
    Curriculum Learning: entrena los modelos empezando por los sorteos
    más "fáciles" (más cercanos al comportamiento esperado) y progresando
    hacia los más difíciles (anómalos).

    Aplicado aquí: pesa los sorteos del histórico según su "dificultad"
    estadística. Los sorteos estadísticamente normales reciben más peso
    en las primeras épocas de aprendizaje; los anómalos se introducen
    gradualmente con menor peso global.
    """

    def __init__(self, historico: List[List[int]]):
        self.historico = historico
        self.n = len(historico)

    def _dificultad_sorteo(self, sorteo: List[int]) -> float:
        """
        Mide la "dificultad" de un sorteo:
        alta dificultad = muy diferente del promedio estadístico.
        """
        if not sorteo:
            return 1.0   # sorteo vacío = máxima dificultad
        suma = sum(sorteo)
        pares = sum(1 for n in sorteo if n % 2 == 0)
        decenas = len(set((n-1)//10 for n in sorteo if 1 <= n <= 49))

        # Valores esperados
        suma_esperada = 150  # (1+49)/2 * 6
        pares_esperados = 3  # 50% de 6
        decenas_esperadas = 4.5

        # Distancia normalizada del centroide estadístico
        diff_suma = abs(suma - suma_esperada) / 50
        diff_pares = abs(pares - pares_esperados) / 3
        diff_decenas = abs(decenas - decenas_esperadas) / 2.5

        dificultad = (diff_suma + diff_pares + diff_decenas) / 3
        return min(1.0, dificultad)

    def calcular_pesos_curriculum(self) -> np.ndarray:
        """
        Calcula pesos de curriculum para cada sorteo.
        Sorteos "fáciles" (normales) reciben más peso.
        """
        if not self.historico:
            return np.array([])
        dificultades = np.array([
            self._dificultad_sorteo(s)
            for s in self.historico
        ])

        # Peso inversamente proporcional a la dificultad
        # con suavizado para no eliminar los difíciles completamente
        pesos = np.exp(-dificultades * 2) + 0.1
        suma = pesos.sum()
        if suma > 0:
            pesos = pesos / suma
        else:
            pesos = np.ones(len(self.historico)) / len(self.historico)
        return pesos

    def calcular_scores(self) -> Dict[int, float]:
        """
        Scores ponderados por curriculum: los sorteos estadísticamente
        normales tienen más influencia en el aprendizaje.
        """
        if not self.historico:
            return {n: 0.5 for n in range(1, 50)}
        pesos = self.calcular_pesos_curriculum()
        scores = defaultdict(float)

        for i, (sorteo, peso) in enumerate(zip(self.historico, pesos)):
            # Penalizar sorteos recientes anómalos más que los históricos
            peso_temporal = math.exp(-i * 0.002)  # Decaimiento temporal
            peso_total = peso * peso_temporal
            for n in sorteo:
                if 1 <= n <= 49:
                    scores[n] += peso_total

        max_v = max(scores.values(), default=1)
        if max_v > 0:
            return {n: scores.get(n, 0)/max_v for n in range(1, 50)}
        return {n: 0.5 for n in range(1, 50)}
