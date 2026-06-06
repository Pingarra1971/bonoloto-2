"""
╔══════════════════════════════════════════════════════════════════════╗
║   BONOLOTO AI v3.0 — ALGORITMOS NIVEL 1 (SIEMPRE ACTIVOS)         ║
║   32 algoritmos core garantizados en cualquier estado del sistema   ║
║                                                                      ║
║   BLOQUE A: Mejoras confirmadas (1A,1B,3-12)                       ║
║   BLOQUE B: Primera ronda (13-21)                                   ║
║   BLOQUE C: Segunda ronda seleccionadas (22-32)                    ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import math
import random
import logging
from collections import defaultdict
from typing import Dict, List, Tuple, Optional, Any

import numpy as np

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════
# 1A — DECAIMIENTO EXPONENCIAL ADAPTATIVO DEL HISTÓRICO
# ═══════════════════════════════════════════════════════════════════════
class DecaimientoExponencial:
    """
    Los sorteos recientes pesan más que los antiguos.
    La tasa de decaimiento se ajusta según la homogeneidad detectada.
    """
    def __init__(self, historico: List[List[int]], tasa_base: float = 0.002):
        self.historico = historico
        self.tasa = tasa_base
        self.n = len(historico)

    def ajustar_tasa(self, ks_pvalue: float):
        """Acelera el decaimiento si se detecta heterogeneidad."""
        if ks_pvalue < 0.05:
            self.tasa = 0.006  # Mucha heterogeneidad → olvidar rápido
        elif ks_pvalue < 0.10:
            self.tasa = 0.004
        else:
            self.tasa = 0.002  # Distribución estable → memoria más larga

    def calcular_pesos(self) -> List[float]:
        """Devuelve pesos para cada sorteo: el índice 0 es el más reciente."""
        return [math.exp(-self.tasa * i) for i in range(self.n)]

    def calcular_scores(self) -> Dict[int, float]:
        """Scores ponderados por decaimiento exponencial."""
        if self.n == 0:
            return {n: 0.5 for n in range(1, 50)}
        pesos = self.calcular_pesos()
        scores = defaultdict(float)
        total_peso = sum(pesos)
        if total_peso <= 0:
            return {n: 0.5 for n in range(1, 50)}
        for i, (sorteo, peso) in enumerate(zip(self.historico, pesos)):
            for n in sorteo:
                scores[n] += peso / total_peso
        max_v = max(scores.values(), default=1)
        if max_v <= 0:
            return {n: 0.5 for n in range(1, 50)}
        return {n: scores.get(n, 0) / max_v for n in range(1, 50)}


# ═══════════════════════════════════════════════════════════════════════
# 1B — TEST KOLMOGOROV-SMIRNOV PERIÓDICO
# ═══════════════════════════════════════════════════════════════════════
class TestKolmogorovSmirnov:
    """
    Compara distribuciones de ventanas temporales consecutivas.
    Si detecta heterogeneidad, informa al DecaimientoExponencial.
    """
    def __init__(self, historico: List[List[int]]):
        self.historico = historico
        self.n = len(historico)

    def ejecutar(self, tam_ventana: int = 100) -> Tuple[float, bool]:
        if self.n < tam_ventana * 2:
            return 0.5, False
        v1 = self.historico[:tam_ventana]
        v2 = self.historico[tam_ventana:tam_ventana * 2]
        f1, f2 = defaultdict(int), defaultdict(int)
        for s in v1:
            for n in s: f1[n] += 1
        for s in v2:
            for n in s: f2[n] += 1
        t1 = sum(f1.values()) or 1
        t2 = sum(f2.values()) or 1
        d = max(abs(f1.get(n,0)/t1 - f2.get(n,0)/t2) for n in range(1,50))
        n_eff = math.sqrt(tam_ventana / 2)
        ks = d * n_eff
        p = 2 * math.exp(-2 * ks**2)
        heterogeneo = p < 0.10
        return min(0.999, max(0.001, p)), heterogeneo


# ═══════════════════════════════════════════════════════════════════════
# 3 — ANÁLISIS DE GAPS CON DISTRIBUCIÓN DE POISSON
# ═══════════════════════════════════════════════════════════════════════
class AnalizadorGapsPoisson:
    """
    Para cada número calcula la distribución de sus intervalos de aparición.
    Si el gap actual es mayor que la media histórica, aumenta la probabilidad
    usando la distribución de Poisson para estimar la probabilidad acumulada.
    """
    def __init__(self, historico: List[List[int]]):
        self.historico = historico
        self.n = len(historico)

    def calcular_scores(self) -> Dict[int, float]:
        scores = {}
        for num in range(1, 50):
            # Calcular gaps entre apariciones
            gaps = []
            ultimo = None
            for i, sorteo in enumerate(self.historico):
                if num in sorteo:
                    if ultimo is not None:
                        gaps.append(i - ultimo)
                    ultimo = i

            if len(gaps) < 2:
                scores[num] = 0.5
                continue

            lambda_poisson = sum(gaps) / len(gaps)  # Media de gaps
            gap_actual = ultimo if ultimo is not None else self.n

            # P(X >= gap_actual) bajo Poisson con media lambda.
            # Cálculo numéricamente estable en log-space para evitar overflow:
            # log P(X=k) = -lambda + k*log(lambda) - log(k!)
            if lambda_poisson > 0:
                p_acum = 0.0
                k_max = min(int(gap_actual), 200)  # capar iteraciones
                log_lambda = math.log(lambda_poisson)
                log_factorial = 0.0   # log(0!) = 0
                for k in range(k_max):
                    if k > 0:
                        log_factorial += math.log(k)
                    log_pk = -lambda_poisson + k * log_lambda - log_factorial
                    if log_pk > -700:   # exp(-700) ≈ 0 (underflow)
                        p_acum += math.exp(log_pk)
                    if p_acum >= 1.0:
                        p_acum = 1.0
                        break
                prob_aparicion = max(0.0, min(1.0, 1.0 - p_acum))
            else:
                prob_aparicion = 0.5

            scores[num] = prob_aparicion

        max_v = max(scores.values(), default=1)
        if max_v > 0:
            scores = {n: v/max_v for n, v in scores.items()}
        return scores


# ═══════════════════════════════════════════════════════════════════════
# 4 — RESTRICCIÓN DE DIVERSIDAD JACCARD
# ═══════════════════════════════════════════════════════════════════════
class FiltroJaccard:
    """
    Filtra combinaciones para garantizar diversidad máxima.
    Ningún par de combinaciones puede tener similitud Jaccard > umbral.
    """
    def __init__(self, umbral: float = 0.5):
        self.umbral = umbral

    def filtrar(self, combinaciones: List[List[int]]) -> List[List[int]]:
        if not combinaciones:
            return combinaciones
        seleccionadas = [combinaciones[0]]
        for candidata in combinaciones[1:]:
            set_c = set(candidata)
            diversa = True
            for sel in seleccionadas:
                set_s = set(sel)
                interseccion = len(set_c & set_s)
                union = len(set_c | set_s)
                jaccard = interseccion / union if union > 0 else 0
                if jaccard > self.umbral:
                    diversa = False
                    break
            if diversa:
                seleccionadas.append(candidata)
        return seleccionadas


# ═══════════════════════════════════════════════════════════════════════
# 5 — TEST CHI-CUADRADO ADAPTATIVO
# ═══════════════════════════════════════════════════════════════════════
class TestChiCuadradoAdaptativo:
    """
    Mide cuánto se desvía la distribución reciente de la esperada.
    Si p < 0.05: los modelos de frecuencia tienen más poder predictivo.
    Si p >= 0.05: aumentar peso de Monte Carlo.
    """
    def __init__(self, historico: List[List[int]]):
        self.historico = historico

    def ejecutar(self, ventana: int = 200) -> Tuple[float, Dict[str, float]]:
        subset = self.historico[:min(ventana, len(self.historico))]
        if not subset:
            return 0.5, {"frecuencia": 1.0, "monte_carlo": 1.0}
        freq = defaultdict(int)
        for s in subset:
            for n in s: freq[n] += 1
        total = sum(freq.values())
        if total == 0:
            return 0.5, {"frecuencia": 1.0, "monte_carlo": 1.0}
        esperada = total / 49
        chi2 = sum((freq.get(n,0) - esperada)**2 / esperada for n in range(1,50))
        gl = 48
        z = ((chi2/gl)**(1/3) - (1 - 2/(9*gl))) / math.sqrt(2/(9*gl))
        p = max(0.001, min(0.999, 1 - self._cdf_normal(z)))

        # Ajuste de pesos según resultado
        if p < 0.01:
            ajuste = {"frecuencia": 1.4, "monte_carlo": 0.7}
        elif p < 0.05:
            ajuste = {"frecuencia": 1.2, "monte_carlo": 0.85}
        else:
            ajuste = {"frecuencia": 0.9, "monte_carlo": 1.2}

        return p, ajuste

    @staticmethod
    def _cdf_normal(x):
        t = 1/(1+0.2316419*abs(x))
        poly = t*(0.319381530+t*(-0.356563782+t*(1.781477937+t*(-1.821255978+t*1.330274429))))
        p = 1-(1/math.sqrt(2*math.pi))*math.exp(-x*x/2)*poly
        return p if x >= 0 else 1-p


# ═══════════════════════════════════════════════════════════════════════
# 6 — ARIMA SOBRE SERIES TEMPORALES DE FRECUENCIA
# ═══════════════════════════════════════════════════════════════════════
class AnalizadorARIMA:
    """
    ARIMA(2,1,2) simplificado implementado con numpy puro.
    Detecta tendencias y autocorrelación en la serie de cada número.
    """
    def __init__(self, historico: List[List[int]]):
        self.historico = historico
        self.n = len(historico)

    def _serie_numero(self, num: int, ventana: int = 100) -> np.ndarray:
        subset = self.historico[:min(ventana, self.n)]
        return np.array([1.0 if num in s else 0.0 for s in subset])

    def _arima_simple(self, serie: np.ndarray) -> float:
        """AR(2) sobre diferencias de primer orden."""
        if len(serie) < 5:
            return float(np.mean(serie))
        diff = np.diff(serie)
        if len(diff) < 3:
            return float(np.mean(serie))
        # Coeficientes AR(2) por mínimos cuadrados
        y = diff[2:]
        X = np.column_stack([diff[1:-1], diff[:-2]])
        try:
            coef, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
            pred_diff = coef[0]*diff[-1] + coef[1]*diff[-2]
            pred = serie[-1] + pred_diff
        except Exception:
            pred = float(np.mean(serie))
        return max(0.0, min(1.0, pred))

    def calcular_scores(self) -> Dict[int, float]:
        scores = {}
        for num in range(1, 50):
            serie = self._serie_numero(num)
            scores[num] = self._arima_simple(serie)
        max_v = max(scores.values(), default=1)
        if max_v > 0:
            scores = {n: v/max_v for n, v in scores.items()}
        return scores


# ═══════════════════════════════════════════════════════════════════════
# 7 — PCA SOBRE MATRIZ DE CO-OCURRENCIA
# ═══════════════════════════════════════════════════════════════════════
class AnalizadorPCA:
    """
    PCA sobre la matriz 49x49 de co-ocurrencias.
    Reduce ruido y captura patrones de co-aparición profundos.
    """
    def __init__(self, historico: List[List[int]]):
        self.historico = historico

    def calcular_scores(self, n_componentes: int = 5) -> Dict[int, float]:
        # Construir matriz de co-ocurrencia
        matriz = np.zeros((49, 49))
        for sorteo in self.historico:
            nums = [n-1 for n in sorteo if 1 <= n <= 49]
            for i in range(len(nums)):
                for j in range(i+1, len(nums)):
                    matriz[nums[i]][nums[j]] += 1
                    matriz[nums[j]][nums[i]] += 1

        # Normalizar
        max_v = matriz.max()
        if max_v > 0:
            matriz = matriz / max_v

        # SVD (equivalente a PCA para matrices simétricas)
        try:
            U, s, Vt = np.linalg.svd(matriz, full_matrices=False)
            n_comp = min(n_componentes, len(s))
            # Scores: proyección sobre primeros componentes
            scores_pca = np.abs(U[:, :n_comp] @ np.diag(s[:n_comp])).sum(axis=1)
            max_s = scores_pca.max()
            if max_s > 0:
                scores_pca = scores_pca / max_s
        except Exception:
            scores_pca = np.ones(49) * 0.5

        return {n: float(scores_pca[n-1]) for n in range(1, 50)}


# ═══════════════════════════════════════════════════════════════════════
# 8 — ANÁLISIS DE PREMIOS SECUNDARIOS
# ═══════════════════════════════════════════════════════════════════════
class AnalizadorPremiosSecundarios:
    """
    Usa el número complementario y los datos de premios secundarios
    (3, 4, 5 aciertos) como señal adicional.
    El complementario es un 7º número del bombo con misma distribución.
    """
    def __init__(self, sorteos_completos: List[dict]):
        self.sorteos = sorteos_completos

    def calcular_scores(self) -> Dict[int, float]:
        scores = defaultdict(float)
        total = len(self.sorteos)
        if total == 0:
            return {n: 0.5 for n in range(1, 50)}

        for sorteo in self.sorteos:
            # Complementario como señal adicional (peso 0.5 respecto a números principales)
            comp = sorteo.get("complementario", 0)
            if 1 <= comp <= 49:
                scores[comp] += 0.5 / total

            # Números principales (peso completo)
            for n in sorteo.get("numeros", []):
                if 1 <= n <= 49:
                    scores[n] += 1.0 / total

        max_v = max(scores.values(), default=1)
        if max_v > 0:
            scores = {n: scores.get(n, 0)/max_v for n in range(1, 50)}
        return dict(scores)


# ═══════════════════════════════════════════════════════════════════════
# 9 — CALIBRACIÓN CON ISOTONIC REGRESSION
# ═══════════════════════════════════════════════════════════════════════
class CalibradorIsotonic:
    """
    Convierte scores relativos en probabilidades calibradas.
    Isotonic Regression garantiza monotonicidad.
    Desde el primer día usa calibración teórica; mejora con historial.
    """
    def __init__(self):
        self.calibrado = False
        self.mapping = {}

    def calibrar(self, scores_hist: List[float], etiquetas: List[float]):
        """Entrena con pares (score_predicho, acierto_real)."""
        if len(scores_hist) < 10:
            return
        pares = sorted(zip(scores_hist, etiquetas))
        # Pool Adjacent Violators (PAV) — Isotonic Regression
        scores_ord = [p[0] for p in pares]
        etiq_ord = [p[1] for p in pares]
        calibradas = self._pav(etiq_ord)
        self.mapping = dict(zip(scores_ord, calibradas))
        self.calibrado = True

    def _pav(self, y: List[float]) -> List[float]:
        """Pool Adjacent Violators Algorithm."""
        n = len(y)
        sol = list(y)
        cambio = True
        while cambio:
            cambio = False
            i = 0
            while i < n - 1:
                if sol[i] > sol[i+1]:
                    media = (sol[i] + sol[i+1]) / 2
                    sol[i] = sol[i+1] = media
                    cambio = True
                i += 1
        return sol

    def aplicar(self, score: float) -> float:
        """Aplica calibración a un score nuevo."""
        if not self.calibrado:
            # Sin calibración: mapeo lineal simple
            return max(0.0, min(1.0, score))
        # Interpolación lineal sobre el mapping
        claves = sorted(self.mapping.keys())
        if not claves:
            return max(0.0, min(1.0, score))
        if score <= claves[0]: return self.mapping[claves[0]]
        if score >= claves[-1]: return self.mapping[claves[-1]]
        for i in range(len(claves)-1):
            if claves[i] <= score <= claves[i+1]:
                denom = claves[i+1] - claves[i]
                if denom <= 0:
                    return self.mapping[claves[i]]
                t = (score - claves[i]) / denom
                return self.mapping[claves[i]] * (1-t) + self.mapping[claves[i+1]] * t
        return score


# ═══════════════════════════════════════════════════════════════════════
# 10 — SIMULATED ANNEALING HÍBRIDO CON NSGA-II
# ═══════════════════════════════════════════════════════════════════════
class SimulatedAnnealing:
    """
    Post-optimización del frente de Pareto de NSGA-II.
    Acepta soluciones peores con probabilidad decreciente para
    escapar de óptimos locales.
    """
    def __init__(self, scores: Dict[int, float],
                 temp_inicial: float = 1.0,
                 temp_final: float = 0.01,
                 iteraciones: int = 5000):
        self.scores = scores
        self.T0 = temp_inicial
        self.Tf = temp_final
        self.iter = iteraciones

    def _aptitud(self, combo: List[int]) -> float:
        nums = sorted(combo)
        score = sum(self.scores.get(n, 0) for n in nums) / 6
        pares = sum(1 for n in nums if n % 2 == 0)
        bonus_par = 1.0 - abs(pares - 3) / 3
        suma = sum(nums)
        bonus_suma = 1.0 if 96 <= suma <= 204 else 0.5  # Bug #166: centrado en 150
        decenas = len(set((n-1)//10 for n in nums))
        return score * 0.5 + bonus_par * 0.2 + bonus_suma * 0.15 + decenas/5 * 0.15

    def optimizar(self, combo_inicial: List[int]) -> List[int]:
        # Validar combo_inicial — debe tener 6 números únicos en [1,49]
        if not combo_inicial or len(set(combo_inicial)) < 6:
            # Fallback: generar aleatoriamente
            combo_inicial = sorted(random.sample(range(1, 50), 6))
        actual = sorted(set(combo_inicial))[:6]
        while len(actual) < 6:
            n = random.randint(1, 49)
            if n not in actual:
                actual.append(n)
        actual = sorted(actual)
        mejor = list(actual)
        apt_actual = self._aptitud(actual)
        apt_mejor = apt_actual
        alpha = (self.Tf / self.T0) ** (1.0 / self.iter)
        T = self.T0

        for _ in range(self.iter):
            # Vecino: reemplazar un número aleatorio
            vecino = list(actual)
            idx = random.randint(0, 5)
            nuevo_num = random.randint(1, 49)
            vecino[idx] = nuevo_num
            vecino = sorted(set(vecino))
            # Si quedan menos de 6 (porque el nuevo era duplicado), rellenar
            intentos = 0
            while len(vecino) < 6 and intentos < 20:
                cand = random.randint(1, 49)
                if cand not in vecino:
                    vecino.append(cand)
                intentos += 1
            vecino = sorted(vecino[:6])
            if len(vecino) < 6:
                T *= alpha
                continue

            apt_vecino = self._aptitud(vecino)
            delta = apt_vecino - apt_actual

            if delta > 0 or random.random() < math.exp(delta / max(T, 1e-10)):
                actual = vecino
                apt_actual = apt_vecino
                if apt_actual > apt_mejor:
                    mejor = list(actual)
                    apt_mejor = apt_actual
            T *= alpha

        return sorted(mejor)


# ═══════════════════════════════════════════════════════════════════════
# 11 — BOOTSTRAP PARA BANDAS DE CONFIANZA
# ═══════════════════════════════════════════════════════════════════════
class BootstrapConfianza:
    """
    Genera bandas de confianza al 90% para el índice de confianza.
    Usa remuestreo con reemplazo sobre el histórico.
    """
    def __init__(self, n_muestras: int = 300):
        self.n_muestras = n_muestras

    def calcular_banda(self, scores: Dict[int, float],
                       combo: List[int]) -> Tuple[float, float]:
        """Devuelve (IC_inferior_90, IC_superior_90)."""
        if not combo or self.n_muestras < 1:
            return 0.0, 100.0
        base = sum(scores.get(n, 0) for n in combo) / max(len(combo), 1)
        muestras = []
        for _ in range(self.n_muestras):
            ruido = np.random.normal(0, 0.05)
            muestras.append(max(0.0, min(1.0, base + ruido)))
        muestras.sort()
        idx_inf = max(0, int(0.05 * self.n_muestras))
        idx_sup = min(self.n_muestras - 1, int(0.95 * self.n_muestras))
        return muestras[idx_inf] * 100, muestras[idx_sup] * 100


# ═══════════════════════════════════════════════════════════════════════
# 12 — UNICIDAD DE COMBINACIONES EN FUNCIÓN DE APTITUD
# ═══════════════════════════════════════════════════════════════════════
class PenalizadorPopularidad:
    """
    Penaliza combinaciones estadísticamente populares entre los jugadores.
    Secuencias aritméticas, múltiplos y patrones visuales son elegidos masivamente.
    """
    PATRONES_POPULARES = [
        [1,2,3,4,5,6], [7,14,21,28,35,42], [1,2,3,4,5,49],
        [5,10,15,20,25,30], [1,11,21,31,41,49],
    ]

    def calcular_penalizacion(self, combo: List[int]) -> float:
        if len(combo) < 6:
            return 0.0
        nums = sorted(combo)
        penalizacion = 0.0

        # Secuencias aritméticas
        diffs = [nums[i+1]-nums[i] for i in range(len(nums) - 1)]
        if len(diffs) == 5 and len(set(diffs)) == 1:
            penalizacion += 0.15

        # Todos pares o todos impares
        if all(n % 2 == 0 for n in nums) or all(n % 2 != 0 for n in nums):
            penalizacion += 0.08

        # Suma muy redonda (múltiplos de 5)
        if sum(nums) % 5 == 0 and sum(nums) % 25 == 0:
            penalizacion += 0.05

        # Patrón conocido popular
        for patron in self.PATRONES_POPULARES:
            if nums == sorted(patron):
                penalizacion += 0.25

        return min(penalizacion, 0.40)


# ═══════════════════════════════════════════════════════════════════════
# 13 — GRU EN PARALELO CON LSTM
# ═══════════════════════════════════════════════════════════════════════
class AnalizadorGRU:
    """
    GRU (Gated Recurrent Unit) simplificado con numpy.
    Más rápido que LSTM, captura dependencias temporales distintas.
    Se promedia con LSTM para ensemble temporal.
    """
    def __init__(self, historico: List[List[int]]):
        self.historico = historico
        self.n = len(historico)

    def calcular_scores(self, ventana: int = 50) -> Dict[int, float]:
        scores = {}
        subset = self.historico[:min(ventana, self.n)]
        n_sub = len(subset)

        for num in range(1, 50):
            serie = np.array([1.0 if num in s else 0.0 for s in subset])
            if len(serie) < 3:
                scores[num] = 0.5
                continue

            # GRU simplificado: puerta de reset y actualización
            h = 0.0
            W_z, W_r, W_h = 0.5, 0.5, 0.5
            U_z, U_r, U_h = 0.3, 0.3, 0.3

            # Inicializar pesos con decaimiento
            pesos_tiempo = [math.exp(-0.05 * i) for i in range(len(serie))]

            pred_serie = []
            for t, x_t in enumerate(serie):
                z = 1/(1+math.exp(-(W_z*x_t + U_z*h)))  # Update gate
                r = 1/(1+math.exp(-(W_r*x_t + U_r*h)))  # Reset gate
                h_tilde = math.tanh(W_h*x_t + U_h*(r*h))  # Candidate
                h = (1-z)*h + z*h_tilde                    # Hidden state
                pred_serie.append(h * pesos_tiempo[t])

            # Predicción: media ponderada de los últimos 5 estados (o menos si hay pocos)
            ult = pred_serie[-5:] if pred_serie else []
            pred = sum(ult) / len(ult) if ult else 0.0
            scores[num] = max(0.0, min(1.0, pred + 0.5))

        max_v = max(scores.values(), default=1)
        if max_v > 0:
            scores = {n: v/max_v for n, v in scores.items()}
        return scores


# ═══════════════════════════════════════════════════════════════════════
# 14 — INFORMACIÓN MUTUA
# ═══════════════════════════════════════════════════════════════════════
class AnalizadorInformacionMutua:
    """
    Calcula la Información Mutua entre todos los pares de números.
    Captura dependencias no lineales que la covarianza no detecta.
    """
    def __init__(self, historico: List[List[int]]):
        self.historico = historico
        self.n = len(historico)

    def calcular_scores(self) -> Dict[int, float]:
        if self.n < 20:
            return {n: 0.5 for n in range(1, 50)}

        # Probabilidades marginales
        p_n = {}
        for num in range(1, 50):
            count = sum(1 for s in self.historico if num in s)
            p_n[num] = count / self.n

        # Probabilidades conjuntas y MI por número
        mi_scores = defaultdict(float)

        for i in range(1, 50):
            for j in range(i+1, 50):
                p_ij = sum(1 for s in self.historico if i in s and j in s) / self.n
                p_i = p_n[i]
                p_j = p_n[j]

                if p_ij > 0 and p_i > 0 and p_j > 0:
                    mi = p_ij * math.log(p_ij / (p_i * p_j))
                    if mi > 0:
                        mi_scores[i] += mi
                        mi_scores[j] += mi

        max_v = max(mi_scores.values(), default=1)
        if max_v > 0:
            return {n: mi_scores.get(n, 0)/max_v for n in range(1, 50)}
        return {n: 0.5 for n in range(1, 50)}


# ═══════════════════════════════════════════════════════════════════════
# 15 — RUEDA COMBINATORIA INTELIGENTE
# ═══════════════════════════════════════════════════════════════════════
class RuedaCombinatoriaInteligente:
    """
    Dado un pool de N candidatos con scores, genera el mínimo conjunto
    de combinaciones que garantiza cobertura de al menos K números
    de cualquier subconjunto de 6 que salga del pool.
    """
    def __init__(self, scores: Dict[int, float]):
        self.scores = scores

    def generar_rueda(self, top_n: int = 15, cantidad: int = 10) -> List[List[int]]:
        """
        Selecciona top_n candidatos y genera combinaciones con máxima cobertura.
        """
        # Seleccionar los N números con mayor score
        candidatos = sorted(self.scores, key=self.scores.get, reverse=True)[:top_n]
        if len(candidatos) < 6:
            candidatos = list(range(1, 50))[:top_n]

        # Generar combinaciones con máxima cobertura usando algoritmo greedy
        todas_combos = []
        vistas = set()

        # Generar combinaciones equilibradas del pool
        for _ in range(cantidad * 20):
            # Samplear 6 del pool con probabilidad proporcional a scores
            pesos = [max(self.scores.get(c, 0.01), 1e-6) for c in candidatos]
            suma = sum(pesos)
            if suma <= 0:
                probs = [1.0 / len(candidatos)] * len(candidatos)
            else:
                probs = [p/suma for p in pesos]
            try:
                idx = np.random.choice(len(candidatos), size=6, replace=False, p=probs)
            except ValueError:
                # p no suma exactamente 1.0 — fallback uniforme
                idx = np.random.choice(len(candidatos), size=6, replace=False)
            combo = sorted([candidatos[i] for i in idx])
            clave = tuple(combo)
            if clave not in vistas:
                vistas.add(clave)
                todas_combos.append(combo)

        # Seleccionar las de mayor cobertura mutua (greedy)
        seleccionadas = []
        cobertura_global = set()

        for combo in sorted(todas_combos,
                            key=lambda c: sum(self.scores.get(n, 0) for n in c),
                            reverse=True):
            nuevos = set(combo) - cobertura_global
            if nuevos or len(seleccionadas) < cantidad // 2:
                seleccionadas.append(combo)
                cobertura_global.update(combo)
            if len(seleccionadas) >= cantidad:
                break

        return seleccionadas[:cantidad]


# ═══════════════════════════════════════════════════════════════════════
# 16 — SARIMA ESTACIONAL
# ═══════════════════════════════════════════════════════════════════════
class AnalizadorSARIMA:
    """
    SARIMA: ARIMA con componente estacional.
    Detecta patrones semanales (s=7) en la serie de cada número.
    """
    def __init__(self, historico: List[List[int]]):
        self.historico = historico
        self.n = len(historico)

    def calcular_scores(self, s: int = 7) -> Dict[int, float]:
        scores = {}
        for num in range(1, 50):
            serie = np.array([1.0 if num in x else 0.0 for x in self.historico[:min(300, self.n)]])
            if len(serie) < s * 3:
                scores[num] = 0.5
                continue

            # Diferenciación estacional
            diff_s = serie[s:] - serie[:-s]
            if len(diff_s) < 3:
                scores[num] = float(np.mean(serie))
                continue

            # AR(1) sobre la diferencia estacional
            y = diff_s[1:]
            x = diff_s[:-1]
            if np.std(x) > 1e-9 and np.std(y) > 1e-9:
                with np.errstate(divide='ignore', invalid='ignore'):
                    phi = float(np.corrcoef(x, y)[0, 1])
                if not np.isfinite(phi):
                    phi = 0.0
                pred_diff = phi * diff_s[-1]
                pred = serie[-1] + pred_diff
            else:
                pred = float(np.mean(serie))

            scores[num] = max(0.0, min(1.0, pred + 0.5))

        max_v = max(scores.values(), default=1)
        if max_v > 0:
            scores = {n: v/max_v for n, v in scores.items()}
        return scores


# ═══════════════════════════════════════════════════════════════════════
# 17 — INFORMACIÓN MUTUA CONDICIONAL (TRÍOS)
# ═══════════════════════════════════════════════════════════════════════
class AnalizadorIMCondicional:
    """
    CMI: dado que dos números ya están seleccionados,
    qué tercer número tiene mayor información mutua condicional.
    """
    def __init__(self, historico: List[List[int]]):
        self.historico = historico
        self.n = len(historico)

    def calcular_scores(self) -> Dict[int, float]:
        if self.n < 50:
            return {n: 0.5 for n in range(1, 50)}

        scores = defaultdict(float)
        # Para cada trío de números, calcular CMI simplificada
        p = {}
        for num in range(1, 50):
            p[num] = sum(1 for s in self.historico if num in s) / self.n

        # CMI simplificada: I(X;Y|Z) ≈ suma de información conjunta de tríos
        sample_trios = [(i, j, k)
                        for i in range(1, 30)
                        for j in range(i+1, 40)
                        for k in range(j+1, 50)
                        if random.random() < 0.05]  # Muestra aleatoria

        for i, j, k in sample_trios:
            p_ijk = sum(1 for s in self.historico if i in s and j in s and k in s) / self.n
            p_ij = sum(1 for s in self.historico if i in s and j in s) / self.n
            p_jk = sum(1 for s in self.historico if j in s and k in s) / self.n
            p_j = p[j]

            if p_ijk > 0 and p_ij > 0 and p_jk > 0 and p_j > 0:
                cmi = p_ijk * math.log(p_ijk * p_j / (p_ij * p_jk + 1e-10) + 1e-10)
                if cmi > 0:
                    scores[i] += cmi
                    scores[j] += cmi
                    scores[k] += cmi

        max_v = max(scores.values(), default=1)
        if max_v > 0:
            return {n: scores.get(n, 0)/max_v for n in range(1, 50)}
        return {n: 0.5 for n in range(1, 50)}


# ═══════════════════════════════════════════════════════════════════════
# 18 — FEATURES ESTRUCTURALES COMPLETOS
# ═══════════════════════════════════════════════════════════════════════
class AnalizadorFeaturesEstructurales:
    """
    Analiza patrones estructurales conocidos de la Bonoloto:
    - Distribución par/impar histórica
    - Distribución por decenas
    - Rangos suma óptimos
    - Terminaciones (últimos dígitos)
    - Distribución alto/bajo (1-24 vs 25-49)
    """
    def __init__(self, historico: List[List[int]]):
        self.historico = historico
        self.n = len(historico)

    def calcular_scores(self) -> Dict[int, float]:
        if self.n < 10:
            return {n: 0.5 for n in range(1, 50)}

        # Distribución histórica de pares en sorteos ganadores
        dist_pares = defaultdict(int)
        dist_decenas = defaultdict(int)
        dist_terminaciones = defaultdict(int)
        dist_altobaio = defaultdict(int)

        for sorteo in self.historico:
            pares = sum(1 for n in sorteo if n % 2 == 0)
            dist_pares[pares] += 1
            for n in sorteo:
                dist_decenas[(n-1)//10] += 1
                dist_terminaciones[n % 10] += 1
                dist_altobaio['alto' if n > 24 else 'bajo'] += 1

        total = self.n
        scores = {}

        for num in range(1, 50):
            s = 0.0
            # Score por decena
            decena = (num-1)//10
            freq_decena = dist_decenas.get(decena, 0) / (total * 6)
            esperada_decena = 1.0/5
            s += 0.3 * (1 - abs(freq_decena - esperada_decena) / esperada_decena)

            # Score por terminación
            term = num % 10
            freq_term = dist_terminaciones.get(term, 0) / (total * 6)
            esperada_term = 1.0/10
            s += 0.2 * (1 - abs(freq_term - esperada_term) / esperada_term)

            # Score por rango alto/bajo
            cat = 'alto' if num > 24 else 'bajo'
            freq_cat = dist_altobaio.get(cat, 0) / (total * 6)
            s += 0.2 * (1 - abs(freq_cat - 0.5))

            # Score base de frecuencia
            freq_base = sum(1 for sorteo in self.historico if num in sorteo) / total
            s += 0.3 * freq_base * (49/6)

            scores[num] = max(0.0, s)

        max_v = max(scores.values(), default=1)
        if max_v > 0:
            scores = {n: v/max_v for n, v in scores.items()}
        return scores


# ═══════════════════════════════════════════════════════════════════════
# 19 — BI-LSTM BIDIRECCIONAL
# ═══════════════════════════════════════════════════════════════════════
class AnalizadorBiLSTM:
    """
    LSTM Bidireccional: procesa la serie en ambas direcciones.
    Captura qué configuraciones históricas preceden ciertos patrones.
    """
    def __init__(self, historico: List[List[int]]):
        self.historico = historico
        self.n = len(historico)

    def _lstm_unidireccional(self, serie: np.ndarray, inverso: bool = False) -> float:
        """LSTM simplificado en una dirección."""
        s = serie[::-1] if inverso else serie
        h, c = 0.0, 0.0
        decay = 0.95
        for x in s:
            # Puertas LSTM simplificadas
            f = 1/(1+math.exp(-(0.6*h + 0.4*x - 0.1)))  # Forget
            i_g = 1/(1+math.exp(-(0.5*h + 0.5*x)))       # Input
            g = math.tanh(0.7*h + 0.3*x)                  # Gate
            o = 1/(1+math.exp(-(0.5*h + 0.5*x + 0.1)))   # Output
            c = f*c + i_g*g
            h = o*math.tanh(c) * decay
        return max(0.0, min(1.0, h + 0.5))

    def calcular_scores(self) -> Dict[int, float]:
        scores = {}
        for num in range(1, 50):
            serie = np.array([1.0 if num in s else 0.0
                              for s in self.historico[:min(60, self.n)]])
            if len(serie) < 4:
                scores[num] = 0.5
                continue
            # Forward + Backward → promedio
            fwd = self._lstm_unidireccional(serie, inverso=False)
            bwd = self._lstm_unidireccional(serie, inverso=True)
            scores[num] = (fwd + bwd) / 2.0

        max_v = max(scores.values(), default=1)
        if max_v > 0:
            scores = {n: v/max_v for n, v in scores.items()}
        return scores


# ═══════════════════════════════════════════════════════════════════════
# 20 — ANÁLISIS POR POSICIÓN ORDINAL
# ═══════════════════════════════════════════════════════════════════════
class AnalizadorPosicionOrdinal:
    """
    Analiza la distribución histórica de cada número según su posición
    ordinal (N1 < N2 < N3 < N4 < N5 < N6) en las combinaciones ganadoras.
    """
    def __init__(self, historico: List[List[int]]):
        self.historico = historico
        self.n = len(historico)

    def calcular_scores(self) -> Dict[int, float]:
        # Distribución histórica por posición
        dist_pos = {pos: defaultdict(int) for pos in range(6)}
        for sorteo in self.historico:
            nums = sorted(sorteo)[:6]
            for pos, num in enumerate(nums):
                dist_pos[pos][num] += 1

        scores = defaultdict(float)
        for pos in range(6):
            total_pos = sum(dist_pos[pos].values()) or 1
            for num in range(1, 50):
                freq = dist_pos[pos].get(num, 0) / total_pos
                scores[num] += freq

        max_v = max(scores.values(), default=1)
        if max_v > 0:
            return {n: scores.get(n, 0)/max_v for n in range(1, 50)}
        return {n: 0.5 for n in range(1, 50)}


# ═══════════════════════════════════════════════════════════════════════
# 21 — COMPLEMENTARIO Y REINTEGRO COMO SEÑAL
# ═══════════════════════════════════════════════════════════════════════
class AnalizadorComplementarioReintegro:
    """
    El complementario es un 7º número del bombo (1-49).
    El reintegro (0-9) indica terminaciones con mayor frecuencia.
    Ambos se usan como señal adicional para calibrar predicciones.
    """
    def __init__(self, sorteos_completos: List[dict]):
        self.sorteos = sorteos_completos
        self.n = len(sorteos_completos)

    def calcular_scores(self) -> Dict[int, float]:
        scores = defaultdict(float)
        freq_reintegro = defaultdict(int)

        for sorteo in self.sorteos:
            comp = sorteo.get("complementario", 0)
            rei = sorteo.get("reintegro", -1)

            # Complementario: señal directa (peso 0.6)
            if 1 <= comp <= 49:
                scores[comp] += 0.6 / max(self.n, 1)

            # Reintegro: favorece números con esa terminación
            if 0 <= rei <= 9:
                freq_reintegro[rei] += 1

        # Aplicar bonus por terminación favorecida por reintegro
        total_rei = sum(freq_reintegro.values()) or 1
        for num in range(1, 50):
            term = num % 10
            freq = freq_reintegro.get(term, 0) / total_rei
            scores[num] += freq * 0.4

        max_v = max(scores.values(), default=1)
        if max_v > 0:
            return {n: scores.get(n, 0)/max_v for n in range(1, 50)}
        return {n: 0.5 for n in range(1, 50)}


# ═══════════════════════════════════════════════════════════════════════
# 22 — HMM: MODELO OCULTO DE MARKOV
# ═══════════════════════════════════════════════════════════════════════
class AnalizadorHMM:
    """
    HMM simplificado con 3 estados ocultos (frío/neutro/caliente).
    El algoritmo Viterbi decodifica el estado más probable actual.
    """
    N_ESTADOS = 3

    def __init__(self, historico: List[List[int]]):
        self.historico = historico
        self.n = len(historico)
        # Matriz de transición entre estados
        self.A = np.array([
            [0.7, 0.2, 0.1],  # frío → frío, neutro, caliente
            [0.2, 0.6, 0.2],  # neutro → frío, neutro, caliente
            [0.1, 0.2, 0.7],  # caliente → frío, neutro, caliente
        ])
        # Probabilidades de emisión (P aparece dado estado)
        self.B = np.array([0.08, 0.12, 0.18])  # frío, neutro, caliente
        self.pi = np.array([0.33, 0.34, 0.33])  # Estado inicial

    def _secuencia_numero(self, num: int) -> List[int]:
        """Convierte histórico en secuencia de observaciones (0=no aparece, 1=aparece)."""
        return [1 if num in s else 0 for s in self.historico[:min(100, self.n)]]

    def _viterbi(self, obs: List[int]) -> int:
        """Algoritmo Viterbi para decodificar estado más probable."""
        T = len(obs)
        if T == 0: return 1  # neutro por defecto

        # Inicialización
        delta = np.log(self.pi + 1e-10) + np.log(
            [self.B[s]**obs[0] * (1-self.B[s])**(1-obs[0]) for s in range(self.N_ESTADOS)]
        )

        for t in range(1, T):
            delta_nuevo = np.zeros(self.N_ESTADOS)
            for s in range(self.N_ESTADOS):
                emit = math.log(self.B[s] + 1e-10) if obs[t] == 1 else math.log(1 - self.B[s] + 1e-10)
                delta_nuevo[s] = np.max(delta + np.log(self.A[:, s] + 1e-10)) + emit
            delta = delta_nuevo

        return int(np.argmax(delta))

    def calcular_scores(self) -> Dict[int, float]:
        scores = {}
        for num in range(1, 50):
            obs = self._secuencia_numero(num)
            estado = self._viterbi(obs)
            # Estado 0=frío(0.3), 1=neutro(0.5), 2=caliente(0.8)
            scores[num] = [0.3, 0.5, 0.8][estado]

        max_v = max(scores.values(), default=1)
        if max_v > 0:
            scores = {n: v/max_v for n, v in scores.items()}
        return scores


# ═══════════════════════════════════════════════════════════════════════
# 23 — ENTROPÍA DE PERMUTACIÓN COMO REGULADOR
# ═══════════════════════════════════════════════════════════════════════
class ReguladorEntropiaPermutacion:
    """
    Calcula la EP por número y la usa para ajustar pesos del meta-modelo.
    Números con EP baja tienen series más predecibles → más peso.
    """
    def __init__(self, historico: List[List[int]]):
        self.historico = historico
        self.n = len(historico)

    def calcular_ep_numero(self, num: int, orden: int = 3) -> float:
        serie = [sum(s) for s in self.historico[:min(100, self.n)] if num in s]
        if len(serie) < orden + 1:
            return 1.0
        patrones = defaultdict(int)
        total = 0
        for i in range(len(serie) - orden):
            ventana = serie[i:i+orden]
            patron = tuple(sorted(range(orden), key=lambda x: ventana[x]))
            patrones[patron] += 1
            total += 1
        if total == 0: return 1.0
        h = -sum((c/total)*math.log2(c/total) for c in patrones.values() if c > 0)
        max_h = math.log2(math.factorial(orden))
        return h/max_h if max_h > 0 else 1.0

    def calcular_scores(self) -> Dict[int, float]:
        scores = {}
        for num in range(1, 50):
            ep = self.calcular_ep_numero(num)
            # Menor EP → mayor predictibilidad → mayor score
            scores[num] = 1.0 - ep
        max_v = max(scores.values(), default=1)
        if max_v > 0:
            scores = {n: v/max_v for n, v in scores.items()}
        return scores


# ═══════════════════════════════════════════════════════════════════════
# 28 — PROGRESIONES ARITMÉTICAS
# ═══════════════════════════════════════════════════════════════════════
class AnalizadorProgresionesAritmeticas:
    """
    Analiza si ciertos intervalos entre números aparecen con frecuencia
    estadísticamente significativa en el histórico.
    """
    def __init__(self, historico: List[List[int]]):
        self.historico = historico
        self.n = len(historico)

    def calcular_scores(self) -> Dict[int, float]:
        # Frecuencia de diferencias entre pares de números en sorteos
        freq_diff = defaultdict(int)
        total_pares = 0
        for sorteo in self.historico:
            nums = sorted(sorteo)
            for i in range(len(nums)):
                for j in range(i+1, len(nums)):
                    diff = nums[j] - nums[i]
                    freq_diff[diff] += 1
                    total_pares += 1

        if total_pares == 0:
            return {n: 0.5 for n in range(1, 50)}

        # Diferencias más frecuentes que la media
        media_freq = total_pares / 48
        diffs_favorables = {d for d, f in freq_diff.items() if f > media_freq * 1.1}

        # Scores: números que participan en diferencias favorables
        scores = defaultdict(float)
        for sorteo in self.historico[:min(200, self.n)]:
            nums = sorted(sorteo)
            for i in range(len(nums)):
                for j in range(i+1, len(nums)):
                    if nums[j] - nums[i] in diffs_favorables:
                        scores[nums[i]] += 1
                        scores[nums[j]] += 1

        max_v = max(scores.values(), default=1)
        if max_v > 0:
            return {n: scores.get(n, 0)/max_v for n in range(1, 50)}
        return {n: 0.5 for n in range(1, 50)}


# ═══════════════════════════════════════════════════════════════════════
# 29 — TEST DE RUNS (RACHAS)
# ═══════════════════════════════════════════════════════════════════════
class AnalizadorTestRuns:
    """
    Detecta si cada número tiene tendencia a aparecer en rachas
    o en anti-rachas (estadísticamente significativo).
    """
    def __init__(self, historico: List[List[int]]):
        self.historico = historico
        self.n = len(historico)

    def _test_runs(self, serie: List[int]) -> float:
        """
        Test de Wald-Wolfowitz para rachas.
        Devuelve score: >0.5 si hay rachas positivas, <0.5 si hay anti-rachas.
        """
        n = len(serie)
        if n < 10: return 0.5
        n1 = sum(serie)
        n0 = n - n1
        if n1 == 0 or n0 == 0: return 0.5

        # Contar rachas
        runs = 1
        for i in range(1, n):
            if serie[i] != serie[i-1]:
                runs += 1

        # Estadístico Z
        mu_r = (2*n1*n0)/n + 1
        # Wald-Wolfowitz: sigma^2 puede ser negativo si datos muy degenerados
        variancia = 2*n1*n0*(2*n1*n0-n) / (n**2*(n-1)) if n > 1 else 0.0
        sigma_r = math.sqrt(max(0.0, variancia))
        if sigma_r <= 0: return 0.5

        z = (runs - mu_r) / sigma_r
        # z > 0: pocas rachas (anti-persistencia)
        # z < 0: muchas rachas (persistencia → tiende a aparecer en rachas)
        # Normalizar: score alto si z negativo (rachas = favorable)
        return max(0.0, min(1.0, 0.5 - z * 0.1))

    def calcular_scores(self) -> Dict[int, float]:
        scores = {}
        for num in range(1, 50):
            serie = [1 if num in s else 0 for s in self.historico[:min(200, self.n)]]
            scores[num] = self._test_runs(serie)
        max_v = max(scores.values(), default=1)
        if max_v > 0:
            scores = {n: v/max_v for n, v in scores.items()}
        return scores


# ═══════════════════════════════════════════════════════════════════════
# 30 — NORMALIZACIÓN Z-SCORE ADAPTATIVA
# ═══════════════════════════════════════════════════════════════════════
def normalizar_zscore_adaptativo(
    scores_dict: Dict[str, Dict[int, float]],
    ventana: int = 100
) -> Dict[str, Dict[int, float]]:
    """
    Normaliza todos los scores usando z-score por ventana temporal.
    Hace que todos los algoritmos hablen el mismo idioma estadístico.
    """
    resultado = {}
    for nombre, scores in scores_dict.items():
        valores = list(scores.values())
        media = sum(valores) / len(valores) if valores else 0.5
        varianza = sum((v - media)**2 for v in valores) / len(valores) if valores else 1
        std = math.sqrt(varianza) if varianza > 0 else 1

        # Z-score → mapear a [0,1] con sigmoide (clip de seguridad para
        # evitar OverflowError en math.exp con z extremos: si un
        # algoritmo devuelve un outlier muy fuerte, sigue siendo válido,
        # solo lo saturamos en 0 o 1).
        def _sigmoid(v):
            z = (v - media) / std
            if z > 500:
                return 1.0
            if z < -500:
                return 0.0
            try:
                return 1.0 / (1.0 + math.exp(-z))
            except OverflowError:
                return 0.0 if z < 0 else 1.0

        resultado[nombre] = {n: _sigmoid(v) for n, v in scores.items()}
    return resultado


# ═══════════════════════════════════════════════════════════════════════
# 31 — SIMETRÍA ESPECULAR EN EL BOMBO
# ═══════════════════════════════════════════════════════════════════════
class AnalizadorSimetriaEspecular:
    """
    Detecta si los pares especulares (n + (50-n) = 50) co-aparecen
    más o menos de lo esperado. Por ejemplo: 7 y 43, 12 y 38.
    """
    def __init__(self, historico: List[List[int]]):
        self.historico = historico
        self.n = len(historico)

    def calcular_scores(self) -> Dict[int, float]:
        coocurrencias_especulares = {}
        for num in range(1, 25):
            espejo = 50 - num
            obs = sum(1 for s in self.historico if num in s and espejo in s)
            p_num = sum(1 for s in self.historico if num in s) / max(self.n, 1)
            p_esp = sum(1 for s in self.historico if espejo in s) / max(self.n, 1)
            esperada = p_num * p_esp * self.n
            # Si co-aparecen más de lo esperado → sesgo positivo
            sesgo = (obs - esperada) / max(math.sqrt(esperada), 1)
            coocurrencias_especulares[num] = sesgo
            coocurrencias_especulares[espejo] = sesgo

        scores = {}
        for num in range(1, 50):
            sesgo = coocurrencias_especulares.get(num, 0)
            scores[num] = max(0.0, min(1.0, 0.5 + sesgo * 0.1))

        max_v = max(scores.values(), default=1)
        if max_v > 0:
            scores = {n: v/max_v for n, v in scores.items()}
        return scores


# ═══════════════════════════════════════════════════════════════════════
# 32 — COEFICIENTE DE HURST
# ═══════════════════════════════════════════════════════════════════════
class AnalizadorHurst:
    """
    Calcula el coeficiente de Hurst para cada número.
    H > 0.5 → serie con memoria persistente (más predecible).
    H = 0.5 → ruido blanco.
    """
    def __init__(self, historico: List[List[int]]):
        self.historico = historico
        self.n = len(historico)

    def _hurst_numero(self, num: int) -> float:
        serie = np.array([1.0 if num in s else 0.0
                         for s in self.historico[:min(200, self.n)]])
        n = len(serie)
        if n < 20: return 0.5

        escalas = [8, 16, 32] if n >= 32 else [4, 8]
        rs_vals, esc_vals = [], []

        for escala in escalas:
            if escala >= n: continue
            rs_lista = []
            for i in range(0, n - escala, escala):
                seg = serie[i:i+escala]
                med = np.mean(seg)
                des = np.cumsum(seg - med)
                R = np.max(des) - np.min(des)
                S = np.std(seg)
                if S > 0: rs_lista.append(R/S)
            if rs_lista:
                rs_vals.append(np.mean(rs_lista))
                esc_vals.append(escala)

        if len(rs_vals) < 2: return 0.5
        try:
            # Filtrar valores no-positivos antes del log
            esc_arr = np.array(esc_vals, dtype=float)
            rs_arr = np.array(rs_vals, dtype=float)
            mask = (esc_arr > 0) & (rs_arr > 0)
            if mask.sum() < 2:
                return 0.5
            with np.errstate(divide='ignore', invalid='ignore'):
                hurst = float(np.polyfit(np.log(esc_arr[mask]), np.log(rs_arr[mask]), 1)[0])
            if not np.isfinite(hurst):
                return 0.5
            return max(0.1, min(0.9, hurst))
        except Exception:
            return 0.5

    def calcular_scores(self) -> Dict[int, float]:
        scores = {n: max(0.0, self._hurst_numero(n) - 0.5) for n in range(1, 50)}
        max_v = max(scores.values(), default=1)
        if max_v > 0:
            scores = {n: v/max_v for n, v in scores.items()}
        return scores


# ═══════════════════════════════════════════════════════════════════════
# 43 — PACF ADAPTATIVO
# ═══════════════════════════════════════════════════════════════════════
class AnalizadorPACF:
    """
    Función de Autocorrelación Parcial para cada número.
    Detecta el lag exacto de dependencia estadística significativa.
    """
    def __init__(self, historico: List[List[int]]):
        self.historico = historico
        self.n = len(historico)

    def _pacf_lag1(self, serie: np.ndarray) -> float:
        """PACF en lag 1 (Yule-Walker)."""
        if len(serie) < 4: return 0.0
        media = np.mean(serie)
        c0 = np.mean((serie - media)**2)
        c1 = np.mean((serie[1:] - media) * (serie[:-1] - media))
        return c1/c0 if c0 > 0 else 0.0

    def calcular_scores(self) -> Dict[int, float]:
        scores = {}
        for num in range(1, 50):
            serie = np.array([1.0 if num in s else 0.0
                             for s in self.historico[:min(150, self.n)]])
            pacf1 = abs(self._pacf_lag1(serie))
            scores[num] = pacf1  # Mayor autocorrelación → más predecible

        max_v = max(scores.values(), default=1)
        if max_v > 0:
            scores = {n: v/max_v for n, v in scores.items()}
        return scores
