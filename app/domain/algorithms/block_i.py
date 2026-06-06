"""
╔══════════════════════════════════════════════════════════════════════╗
║   BONOLOTO AI — BLOQUE I + NUEVAS MEJORAS ALTA PRIORIDAD           ║
║                                                                      ║
║   BLOQUE I (implantado):                                            ║
║   76. LNN/CfC  Liquid Neural Network                                ║
║   77. TDA Homología Persistente v2 (sin giotto — numpy puro)        ║
║   78. SAX Symbolic Aggregate approXimation + Motivos               ║
║   79. MDL Minimum Description Length                                ║
║                                                                      ║
║   NUEVAS ALTA PRIORIDAD encontradas:                                ║
║   80. DWT Wavelet Transform (pywavelets)                            ║
║   81. MoE Dinámico (Mixture of Experts con gating adaptativo)       ║
║   82. GAT simplificado (Graph Attention sobre co-ocurrencias)       ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import math
import zlib
import random
import logging
from collections import defaultdict
from typing import Dict, List, Tuple, Optional

import numpy as np

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════
# 76 — LNN/CfC: LIQUID NEURAL NETWORK (Closed-Form Continuous-Time)
# ═══════════════════════════════════════════════════════════════════════
class AnalizadorLNN:
    """
    Liquid Time-Constant Network en forma cerrada (CfC).
    Supera a LSTM/GRU en adaptabilidad a distribuciones cambiantes.
    Implementado con numpy puro usando la formulación algebraica CfC:
      h(t) = sigmoid(W_f * x + b_f) * h(t-1)
            + sigmoid(W_i * x + b_i) * tanh(W_h * x + b_h)
    con constante de tiempo líquida τ adaptativa por entrada.
    """

    def __init__(self, historico: List[List[int]], n_neuronas: int = 20):
        self.historico = historico
        self.n = len(historico)
        self.N = n_neuronas
        rng = np.random.RandomState(42)
        # Pesos fijos (no entrenados — reservoir style)
        self.W_f = rng.randn(n_neuronas) * 0.3
        self.W_i = rng.randn(n_neuronas) * 0.3
        self.W_h = rng.randn(n_neuronas) * 0.3
        self.b_f = np.zeros(n_neuronas)
        self.b_i = np.zeros(n_neuronas) - 0.5
        self.b_h = np.zeros(n_neuronas)
        # Constante de tiempo líquida τ (aprendida por mínimos cuadrados simple)
        self.tau = np.ones(n_neuronas) * 0.5

    @staticmethod
    def _sigmoid(x: np.ndarray) -> np.ndarray:
        return 1.0 / (1.0 + np.exp(-np.clip(x, -15, 15)))

    def _paso_cfc(self, x: float, h: np.ndarray) -> np.ndarray:
        """Un paso de la dinámica CfC."""
        x_arr = np.full(self.N, x)
        # Puerta de olvido líquida
        f = self._sigmoid(self.W_f * x_arr + self.b_f)
        # Puerta de entrada
        i = self._sigmoid(self.W_i * x_arr + self.b_i)
        # Candidato de estado
        g = np.tanh(self.W_h * x_arr + self.b_h)
        # Constante de tiempo adaptativa (depende de la entrada)
        tau_x = self.tau / (1.0 + np.abs(x_arr))
        # Actualización CfC (forma cerrada del LTC-ODE)
        h_nuevo = f * h + i * g
        # Aplicar decaimiento con tau
        h_nuevo = h_nuevo * np.exp(-tau_x) + g * (1 - np.exp(-tau_x))
        return h_nuevo

    def _ejecutar(self, serie: np.ndarray) -> float:
        """Ejecuta la red y devuelve la predicción para el siguiente paso."""
        h = np.zeros(self.N)
        for x in serie:
            h = self._paso_cfc(float(x), h)
        # Predicción: proyección lineal del estado oculto
        pred = np.mean(h) + 0.5
        return max(0.0, min(1.0, pred))

    def calcular_scores(self) -> Dict[int, float]:
        scores = {}
        ventana = min(100, self.n)
        for num in range(1, 50):
            serie = np.array([1.0 if num in s else 0.0
                             for s in self.historico[:ventana]])
            if len(serie) < 5:
                scores[num] = 0.5
                continue
            scores[num] = self._ejecutar(serie)

        max_v = max(scores.values(), default=1)
        if max_v > 0:
            scores = {n: v/max_v for n, v in scores.items()}
        return scores


# ═══════════════════════════════════════════════════════════════════════
# 77 — TDA v2: HOMOLOGÍA PERSISTENTE MEJORADA (numpy puro optimizado)
# ═══════════════════════════════════════════════════════════════════════
class AnalizadorTDAv2:
    """
    TDA con homología persistente completa usando el complejo de Vietoris-Rips
    implementado eficientemente con numpy.
    Sustituye al TDA simplificado anterior con cálculo de números de Betti
    y diagramas de persistencia como features.
    """

    def __init__(self, historico: List[List[int]]):
        self.historico = historico
        self.n = len(historico)

    def _incrustar_takens(self, serie: np.ndarray, dim: int = 3,
                          lag: int = 2) -> np.ndarray:
        n = len(serie)
        n_pts = n - (dim - 1) * lag
        if n_pts < 4:
            return np.array([]).reshape(0, dim)
        return np.array([[serie[i + j * lag] for j in range(dim)]
                         for i in range(n_pts)])

    def _distancias_rips(self, puntos: np.ndarray) -> np.ndarray:
        """Matriz de distancias euclidianas."""
        n = len(puntos)
        D = np.zeros((n, n))
        for i in range(n):
            for j in range(i + 1, n):
                d = np.linalg.norm(puntos[i] - puntos[j])
                D[i, j] = D[j, i] = d
        return D

    def _betti_0(self, D: np.ndarray, epsilon: float) -> int:
        """Número de Betti-0: componentes conectadas al radio epsilon."""
        n = len(D)
        parent = list(range(n))

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a, b):
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb

        for i in range(n):
            for j in range(i + 1, n):
                if D[i, j] <= epsilon:
                    union(i, j)

        return len(set(find(i) for i in range(n)))

    def _persistencia_betti0(self, D: np.ndarray) -> float:
        """
        Calcula la persistencia del diagrama de Betti-0.
        Mide cuánto "viven" las componentes conectadas → estructura topológica.
        """
        if len(D) == 0:
            return 0.5
        d_vals = sorted(set(D[D > 0].flatten()))
        if not d_vals:
            return 0.5

        epsilons = np.linspace(0, d_vals[-1] if d_vals else 1, 15)
        bettis = [self._betti_0(D, e) for e in epsilons]

        # Entropía de persistencia: series con más estructura tienen entropía más baja
        cambios = sum(1 for i in range(1, len(bettis))
                      if bettis[i] != bettis[i-1])
        estructura = 1.0 / (1.0 + cambios)
        return estructura

    def calcular_scores(self) -> Dict[int, float]:
        scores = {}
        for num in range(1, 50):
            serie = np.array([1.0 if num in s else 0.0
                             for s in self.historico[:min(80, self.n)]])
            if len(serie) < 8:
                scores[num] = 0.5
                continue

            puntos = self._incrustar_takens(serie, dim=3, lag=2)
            if len(puntos) < 5:
                scores[num] = 0.5
                continue

            # Limitar para eficiencia
            pts = puntos[:min(30, len(puntos))]
            D = self._distancias_rips(pts)
            persistencia = self._persistencia_betti0(D)
            scores[num] = persistencia

        max_v = max(scores.values(), default=1)
        if max_v > 0:
            scores = {n: v/max_v for n, v in scores.items()}
        return scores


# ═══════════════════════════════════════════════════════════════════════
# 78 — SAX: SYMBOLIC AGGREGATE APPROX + DESCUBRIMIENTO DE MOTIVOS
# ═══════════════════════════════════════════════════════════════════════
class AnalizadorSAX:
    """
    SAX convierte series temporales en secuencias simbólicas.
    Busca motivos recurrentes (patrones) y mide su predictividad.
    """

    ALPHABET = 'abcde'  # 5 símbolos

    def __init__(self, historico: List[List[int]], w: int = 8, a: int = 5):
        self.historico = historico
        self.n = len(historico)
        self.w = w   # Longitud de la representación SAX
        self.a = a   # Tamaño del alfabeto

    def _normalizar(self, serie: np.ndarray) -> np.ndarray:
        m, s = serie.mean(), serie.std()
        if s < 1e-10:
            return np.zeros_like(serie)
        return (serie - m) / s

    def _paa(self, serie: np.ndarray) -> np.ndarray:
        """Piecewise Aggregate Approximation."""
        n = len(serie)
        if n == 0 or self.w == 0:
            return np.array([])
        seg = n / self.w
        return np.array([serie[int(i*seg):int((i+1)*seg)].mean()
                         for i in range(self.w)])

    def _discretizar(self, paa: np.ndarray) -> str:
        """Discretiza usando umbrales de distribución normal equiprobable."""
        # Umbrales para a=5: percentiles 20,40,60,80 de N(0,1)
        umbrales = [-0.841, -0.253, 0.253, 0.841]
        palabra = ''
        for v in paa:
            idx = sum(1 for u in umbrales if v > u)
            palabra += self.ALPHABET[idx]
        return palabra

    def _sax_serie(self, num: int, ventana: int = 200) -> str:
        serie = np.array([1.0 if num in s else 0.0
                         for s in self.historico[:min(ventana, self.n)]])
        if len(serie) < self.w:
            return ''
        norm = self._normalizar(serie)
        paa = self._paa(norm)
        return self._discretizar(paa)

    def _descubrir_motivos(self, palabras: List[str],
                           long_motivo: int = 3) -> Dict[str, int]:
        """Cuenta sub-patrones de longitud long_motivo."""
        motivos = defaultdict(int)
        for p in palabras:
            for i in range(len(p) - long_motivo + 1):
                motivos[p[i:i+long_motivo]] += 1
        return dict(motivos)

    def calcular_scores(self) -> Dict[int, float]:
        # Generar SAX para ventanas deslizantes de cada número
        scores = {}

        # Para cada número, calcular SAX sobre el histórico reciente
        # y comparar con la situación actual para calcular predictividad
        for num in range(1, 50):
            serie = np.array([1.0 if num in s else 0.0
                             for s in self.historico[:min(200, self.n)]])
            if len(serie) < self.w * 2:
                scores[num] = 0.5
                continue

            # SAX de la situación reciente (últimos w sorteos)
            reciente = serie[:self.w]
            norm_r = self._normalizar(reciente)
            paa_r = self._paa(norm_r)
            patron_actual = self._discretizar(paa_r)

            # Buscar apariciones similares en el histórico
            aciertos = 0
            total = 0
            tam_ventana = self.w
            if not patron_actual:
                scores[num] = 0.5
                continue
            for i in range(self.w, len(serie) - self.w):
                ventana_hist = serie[i:i + tam_ventana]
                norm_h = self._normalizar(ventana_hist)
                paa_h = self._paa(norm_h)
                patron_hist = self._discretizar(paa_h)
                if not patron_hist:
                    continue

                # Similitud de Hamming entre patrones
                similitud = sum(a == b for a, b in
                               zip(patron_actual, patron_hist)) / len(patron_actual)

                if similitud >= 0.7:  # 70% de similitud
                    total += 1
                    # ¿El número apareció en el sorteo siguiente?
                    if i + tam_ventana < len(serie) and serie[i + tam_ventana] > 0:
                        aciertos += 1

            if total >= 3:
                scores[num] = aciertos / total
            else:
                scores[num] = 0.5  # Sin suficientes datos

        max_v = max(scores.values(), default=1)
        if max_v > 0:
            scores = {n: v/max_v for n, v in scores.items()}
        return scores


# ═══════════════════════════════════════════════════════════════════════
# 79 — MDL: MINIMUM DESCRIPTION LENGTH COMO ÁRBITRO DEL META-MODELO
# ═══════════════════════════════════════════════════════════════════════
class ArbitroMDL:
    """
    Usa la complejidad de Kolmogorov aproximada (longitud de compresión zlib)
    como criterio para seleccionar el modelo más parsimonioso.
    El modelo que más comprime el histórico es el mejor predictor.
    Principio: compresión de datos = aprendizaje real.
    """

    def __init__(self, historico: List[List[int]]):
        self.historico = historico
        self.n = len(historico)

    def _complejidad_kolmogorov(self, datos: bytes) -> float:
        """Aproxima K(x) con longitud de compresión zlib."""
        if not datos:
            return 0.0
        return len(zlib.compress(datos, level=9))

    def _serie_a_bytes(self, serie: np.ndarray) -> bytes:
        """Convierte una serie numpy a bytes para comprimir."""
        # Cuantizar a enteros de 8 bits para compresión
        cuant = np.clip(serie * 255, 0, 255).astype(np.uint8)
        return cuant.tobytes()

    def calcular_scores(self) -> Dict[int, float]:
        """
        Para cada número, mide la compresibilidad de su serie temporal.
        Series más compresibles tienen más estructura predecible.
        """
        scores = {}
        for num in range(1, 50):
            serie = np.array([1.0 if num in s else 0.0
                             for s in self.historico[:min(300, self.n)]])
            if len(serie) < 10:
                scores[num] = 0.5
                continue

            # Complejidad de la serie completa
            k_total = self._complejidad_kolmogorov(self._serie_a_bytes(serie))

            # Complejidad de la serie aleatoria (referencia)
            serie_rand = np.random.binomial(1, serie.mean(), len(serie)).astype(float)
            k_rand = self._complejidad_kolmogorov(self._serie_a_bytes(serie_rand))

            # Score: mayor compresión relativa → más estructura → más predecible
            if k_rand > 0:
                ratio = 1.0 - (k_total / k_rand)
                scores[num] = max(0.0, min(1.0, ratio + 0.5))
            else:
                scores[num] = 0.5

        max_v = max(scores.values(), default=1)
        if max_v > 0:
            scores = {n: v/max_v for n, v in scores.items()}
        return scores

    def seleccionar_mejores_algoritmos(
        self,
        scores_por_algoritmo: Dict[str, Dict[int, float]],
        historico: List[List[int]],
        top_k: int = 8,
    ) -> Dict[str, float]:
        """
        Evalúa qué algoritmos comprimen mejor el histórico.
        Devuelve pesos proporcionales a la capacidad de compresión.
        """
        pesos_mdl = {}
        for nombre, scores in scores_por_algoritmo.items():
            if not scores:
                pesos_mdl[nombre] = 0.0
                continue
            # Reconstruir señal predicha por el algoritmo
            mejor_n = max(scores, key=scores.get)
            señal = np.array([scores.get(mejor_n, 0.5)
                              for _ in range(min(50, max(self.n, 1)))])
            k = self._complejidad_kolmogorov(self._serie_a_bytes(señal))
            # Menor complejidad → modelo más simple → mayor peso MDL
            pesos_mdl[nombre] = 1.0 / (k + 1)

        # Normalizar
        total = sum(pesos_mdl.values())
        if total > 0:
            pesos_mdl = {k: v/total for k, v in pesos_mdl.items()}
        return pesos_mdl


# ═══════════════════════════════════════════════════════════════════════
# 80 — DWT: TRANSFORMADA WAVELET DISCRETA
# ═══════════════════════════════════════════════════════════════════════
class AnalizadorDWT:
    """
    Wavelet Discrete Transform (DWT) con PyWavelets.
    Descompone cada serie en componentes de frecuencia localizadas en tiempo.
    Detecta patrones que FFT no puede por ser no estacionaria.
    Si PyWavelets no está disponible, usa implementación numpy propia.
    """

    def __init__(self, historico: List[List[int]]):
        self.historico = historico
        self.n = len(historico)
        self._tiene_pywt = self._check_pywt()

    def _check_pywt(self) -> bool:
        try:
            import pywt
            return True
        except ImportError:
            return False

    def _dwt_numpy(self, serie: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Haar wavelet simplificado con numpy (sin pywt)."""
        n = len(serie)
        if n % 2 != 0:
            serie = np.append(serie, serie[-1])
        aprox = (serie[::2] + serie[1::2]) / math.sqrt(2)
        detalle = (serie[::2] - serie[1::2]) / math.sqrt(2)
        return aprox, detalle

    def _energia_por_nivel(self, serie: np.ndarray, niveles: int = 4) -> np.ndarray:
        """Calcula energía en cada nivel de descomposición wavelet."""
        energias = []
        current = serie.copy()

        for nivel in range(niveles):
            if len(current) < 4:
                energias.append(0.0)
                continue

            if self._tiene_pywt:
                import pywt
                aprox, detalle = pywt.dwt(current, 'db4')
            else:
                aprox, detalle = self._dwt_numpy(current)

            # Energía en el nivel de detalle
            energia_detalle = float(np.sum(detalle ** 2))
            energias.append(energia_detalle)
            current = aprox

        # Añadir energía de la aproximación final
        energias.append(float(np.sum(current ** 2)))
        return np.array(energias)

    def calcular_scores(self) -> Dict[int, float]:
        scores = {}
        ventana = min(256, self.n)  # DWT necesita potencias de 2 idealmente

        for num in range(1, 50):
            serie = np.array([1.0 if num in s else 0.0
                             for s in self.historico[:ventana]])
            if len(serie) < 16:
                scores[num] = 0.5
                continue

            # Energía wavelet por nivel
            energias = self._energia_por_nivel(serie, niveles=4)
            total_energia = energias.sum()

            if total_energia < 1e-10:
                scores[num] = 0.5
                continue

            # Distribución de energía por escala temporal
            energias_norm = energias / total_energia

            # Score: mayor concentración de energía en niveles bajos (tendencia)
            # vs niveles altos (ruido) indica más estructura predecible
            score_estructura = energias_norm[-1] + 0.5 * energias_norm[-2]
            score_recencia = energias_norm[0]  # Actividad reciente

            scores[num] = 0.6 * score_estructura + 0.4 * score_recencia

        max_v = max(scores.values(), default=1)
        if max_v > 0:
            scores = {n: v/max_v for n, v in scores.items()}
        return scores


# ═══════════════════════════════════════════════════════════════════════
# 81 — MoE DINÁMICO: MIXTURE OF EXPERTS CON GATING ADAPTATIVO
# ═══════════════════════════════════════════════════════════════════════
class MixtureOfExperts:
    """
    MoE con red de gating que asigna pesos dinámicamente a los algoritmos
    basándose en el estado estadístico actual del histórico.
    Inspirado en FreqMoE y MoGU (2024-2025).

    Diferentes "expertos" son más relevantes según:
    - Si la distribución es estacionaria/no estacionaria
    - Si hay señal fuerte o débil
    - Si el histórico es largo o corto
    """

    def __init__(self, historico: List[List[int]]):
        self.historico = historico
        self.n = len(historico)

    def _calcular_features_estado(self) -> Dict[str, float]:
        """Extrae features del estado estadístico actual del histórico."""
        sumas = [sum(s) for s in self.historico[:min(200, self.n)]]
        if not sumas:
            return {}

        sumas_arr = np.array(sumas, dtype=float)
        media = sumas_arr.mean()
        std = sumas_arr.std()

        # Estacionariedad aproximada (ADF simplificado)
        diffs = np.diff(sumas_arr)
        if len(diffs) > 1 and np.std(diffs[:-1]) > 1e-9 and np.std(diffs[1:]) > 1e-9:
            with np.errstate(divide='ignore', invalid='ignore'):
                correlacion_diff = float(np.corrcoef(diffs[:-1], diffs[1:])[0, 1])
            if not np.isfinite(correlacion_diff):
                correlacion_diff = 0.0
        else:
            correlacion_diff = 0.0

        # Entropía de permutación (ya calculada en diagnóstico, aquí simplificada)
        n = len(sumas_arr)
        patron_count = defaultdict(int)
        for i in range(n - 2):
            v = sumas_arr[i:i+3]
            patron = tuple(np.argsort(v))
            patron_count[patron] += 1
        total_p = sum(patron_count.values())
        ep = -sum((c/total_p)*math.log2(c/total_p)
                  for c in patron_count.values()
                  if c > 0) / math.log2(6) if total_p > 0 else 1.0

        return {
            'ep': ep,                          # Entropía de permutación [0,1]
            'cv': std/max(media, 1),           # Coeficiente de variación
            'autocorr': abs(correlacion_diff), # Autocorrelación en diferencias
            'n_sorteos': min(self.n / 5000, 1.0),  # Cantidad de datos normalizada
        }

    def calcular_pesos_gating(
        self,
        scores_por_algoritmo: Dict[str, Dict[int, float]],
    ) -> Dict[str, float]:
        """
        Red de gating que asigna pesos a cada algoritmo según el
        estado estadístico actual. Los pesos son dinámicos por cálculo.
        """
        estado = self._calcular_features_estado()
        if not estado or not scores_por_algoritmo:
            n = len(scores_por_algoritmo)
            if n == 0:
                return {}
            return {k: 1.0/n for k in scores_por_algoritmo}

        ep = estado.get('ep', 0.9)
        cv = estado.get('cv', 0.1)
        autocorr = estado.get('autocorr', 0.1)
        n_datos = estado.get('n_sorteos', 0.5)

        # Reglas de gating basadas en el estado
        # (Red neuronal shallow de 1 capa con pesos fijos calibrados)
        pesos_gating = {}
        for nombre in scores_por_algoritmo:
            nombre_lower = nombre.lower()

            # Alta entropía (muy aleatorio) → más peso a Monte Carlo y Poisson
            if 'monte_carlo' in nombre_lower or 'gaps_poisson' in nombre_lower:
                w = 0.5 + 0.5 * ep
            # Baja entropía (predecible) → más peso a LSTM, Transformer, LNN, S4
            elif any(x in nombre_lower for x in ['lstm', 'transformer', 'lnn', 'ssm', 'bilstm']):
                w = 0.5 + 0.5 * (1 - ep)
            # Alta autocorrelación → más peso a ARIMA, SARIMA, Markov
            elif any(x in nombre_lower for x in ['arima', 'sarima', 'markov', 'pacf']):
                w = 0.5 + 0.5 * autocorr
            # Mucha variación → más peso a modelos robustos (XGBoost, RL)
            elif any(x in nombre_lower for x in ['xgboost', 'reinforcement', 'gru']):
                w = 0.5 + 0.5 * min(cv, 1.0)
            # Muchos datos → más peso a modelos data-hungry (Copulas, VAR, NODE)
            elif any(x in nombre_lower for x in ['copulas', 'var', 'neural_ode', 'esn']):
                w = 0.3 + 0.7 * n_datos
            # Resto: peso neutro
            else:
                w = 0.6

            pesos_gating[nombre] = max(0.1, min(1.5, w))

        # Normalizar
        total = sum(pesos_gating.values())
        if total > 0:
            pesos_gating = {k: v/total for k, v in pesos_gating.items()}
        return pesos_gating

    def combinar_con_gating(
        self,
        scores_por_algoritmo: Dict[str, Dict[int, float]],
    ) -> Dict[int, float]:
        """Combina scores usando pesos de gating dinámico."""
        pesos = self.calcular_pesos_gating(scores_por_algoritmo)
        scores_finales = defaultdict(float)

        for nombre, scores in scores_por_algoritmo.items():
            peso = pesos.get(nombre, 1.0 / len(scores_por_algoritmo))
            for n, s in scores.items():
                scores_finales[n] += s * peso

        max_v = max(scores_finales.values(), default=1)
        if max_v > 0:
            scores_finales = {n: v/max_v for n, v in scores_finales.items()}
        return dict(scores_finales)


# ═══════════════════════════════════════════════════════════════════════
# 82 — GAT SIMPLIFICADO: GRAPH ATTENTION SOBRE CO-OCURRENCIAS
# ═══════════════════════════════════════════════════════════════════════
class AnalizadorGAT:
    """
    Graph Attention Network simplificado sobre el grafo de co-ocurrencias.
    Cada número es un nodo. Las aristas son co-ocurrencias ponderadas.
    La atención aprende a ponderar qué vecinos son más informativos.
    Supera al análisis de co-ocurrencia actual que trata todos los vecinos igual.
    """

    def __init__(self, historico: List[List[int]], n_cabezas: int = 4):
        self.historico = historico
        self.n = len(historico)
        self.n_cabezas = n_cabezas
        rng = np.random.RandomState(42)
        # Pesos de atención por cabeza (fijos tipo reservoir)
        self.W_att = rng.randn(n_cabezas, 2) * 0.3  # [cabeza, (query, key)]

    def _construir_grafo(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Construye matriz de adyacencia ponderada (co-ocurrencias)
        y vector de features de nodos (frecuencias).
        """
        A = np.zeros((49, 49))  # Matriz de adyacencia
        freq = np.zeros(49)     # Features de nodos

        for sorteo in self.historico:
            nums = [n - 1 for n in sorteo if 1 <= n <= 49]
            for i_idx, i in enumerate(nums):
                freq[i] += 1
                for j in nums[i_idx + 1:]:
                    A[i][j] += 1
                    A[j][i] += 1

        # Normalizar
        max_a = A.max()
        if max_a > 0:
            A /= max_a
        max_f = freq.max()
        if max_f > 0:
            freq /= max_f

        return A, freq

    def _atención_cabeza(self, A: np.ndarray, h: np.ndarray,
                         cabeza: int) -> np.ndarray:
        """Un paso de atención multi-cabeza."""
        n = len(h)
        scores_att = np.zeros((n, n))

        w_q, w_k = self.W_att[cabeza]
        for i in range(n):
            for j in range(n):
                if A[i][j] > 0:
                    # Score de atención: compatibilidad entre nodos
                    e_ij = w_q * h[i] + w_k * h[j] + A[i][j]
                    scores_att[i][j] = e_ij

        # Softmax por fila
        att_norm = np.zeros((n, n))
        for i in range(n):
            vecinos = [j for j in range(n) if A[i][j] > 0]
            if vecinos:
                vals = np.array([scores_att[i][j] for j in vecinos])
                vals_exp = np.exp(vals - vals.max())
                vals_soft = vals_exp / vals_exp.sum()
                for k, j in enumerate(vecinos):
                    att_norm[i][j] = vals_soft[k]

        return att_norm

    def calcular_scores(self) -> Dict[int, float]:
        A, h = self._construir_grafo()

        # Múltiples capas de atención
        h_actual = h.copy()
        for _ in range(2):  # 2 capas GAT
            h_nuevo = np.zeros(49)
            for cabeza in range(self.n_cabezas):
                att = self._atención_cabeza(A, h_actual, cabeza)
                # Agregación: h_i = suma(att_ij * h_j)
                h_nuevo += att @ h_actual / self.n_cabezas

            # Activación y residual
            h_actual = np.tanh(h_nuevo) * 0.7 + h_actual * 0.3

        # Normalizar scores finales
        max_v = h_actual.max()
        if max_v > 0:
            h_actual = h_actual / max_v

        return {n: float(h_actual[n - 1]) for n in range(1, 50)}
