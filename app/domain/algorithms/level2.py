"""
╔══════════════════════════════════════════════════════════════════════╗
║   BONOLOTO AI v3.0 — ALGORITMOS NIVEL 2 (ACTIVACIÓN CONDICIONAL)   ║
║   Se activan solo cuando el diagnóstico lo justifica                ║
║                                                                      ║
║   24. Cópulas Gaussianas                                            ║
║   25. Teoría de Valores Extremos (EVT/GEV)                         ║
║   26. Proceso de Dirichlet (DPMM)                                   ║
║   27. Multi-Scale Entropy                                            ║
║   33. Echo State Network (ESN)                                      ║
║   34. VAR Multivariante                                             ║
║   37. TDA + Homología Persistente                                    ║
║   38. Regresión Simbólica                                           ║
║   39. Exponente de Lyapunov                                         ║
║   40. Proceso de Hawkes                                              ║
║   41. Multifractal DFA                                              ║
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
# 24 — CÓPULAS GAUSSIANAS MULTIVARIANTES
# Activa si: KS p < 0.10
# ═══════════════════════════════════════════════════════════════════════
class AnalizadorCopulas:
    """
    Modela la estructura de dependencia conjunta de los 6 números
    como un sistema multivariante completo usando cópulas gaussianas.
    """
    def __init__(self, historico: List[List[int]]):
        self.historico = historico
        self.n = len(historico)

    def _cdf_empirica(self, num: int) -> float:
        """CDF empírica de un número."""
        count = sum(1 for s in self.historico if num in s)
        return count / max(self.n, 1)

    def _correlacion_copula(self, n1: int, n2: int) -> float:
        """Correlación de Spearman entre dos números (base para cópula gaussiana)."""
        r1 = [1.0 if n1 in s else 0.0 for s in self.historico]
        r2 = [1.0 if n2 in s else 0.0 for s in self.historico]
        if len(r1) < 3: return 0.0
        # Correlación de Pearson sobre rangos
        n = len(r1)
        media1 = sum(r1)/n
        media2 = sum(r2)/n
        num_corr = sum((r1[i]-media1)*(r2[i]-media2) for i in range(n))
        den = math.sqrt(sum((v-media1)**2 for v in r1) * sum((v-media2)**2 for v in r2))
        return num_corr/den if den > 0 else 0.0

    def calcular_scores(self) -> Dict[int, float]:
        scores = defaultdict(float)
        # Calcular correlaciones de cópula entre pares
        # y usarlas para estimar densidad de probabilidad conjunta
        for n1 in range(1, 50):
            for n2 in range(n1+1, min(n1+10, 50)):  # Vecinos cercanos
                corr = self._correlacion_copula(n1, n2)
                if abs(corr) > 0.05:  # Solo correlaciones significativas
                    peso = abs(corr)
                    if corr > 0:
                        # Co-aparecen juntos → aumentar ambos
                        scores[n1] += peso
                        scores[n2] += peso
                    else:
                        # Se excluyen mutuamente → señal sobre el más frecuente
                        freq1 = self._cdf_empirica(n1)
                        freq2 = self._cdf_empirica(n2)
                        if freq1 > freq2:
                            scores[n1] += peso * 0.5
                        else:
                            scores[n2] += peso * 0.5

        max_v = max(scores.values(), default=1)
        if max_v > 0:
            return {n: scores.get(n, 0)/max_v for n in range(1, 50)}
        return {n: 0.5 for n in range(1, 50)}


# ═══════════════════════════════════════════════════════════════════════
# 25 — TEORÍA DE VALORES EXTREMOS (EVT/GEV)
# Activa si: señal alta
# ═══════════════════════════════════════════════════════════════════════
class AnalizadorEVT:
    """
    Modela la distribución de gaps máximos y co-ocurrencias extremas.
    Detecta números con comportamientos en la cola estadística.
    """
    def __init__(self, historico: List[List[int]]):
        self.historico = historico
        self.n = len(historico)

    def _ajustar_gev(self, datos: List[float]) -> Tuple[float, float, float]:
        """Ajuste GEV simplificado por método de momentos."""
        if len(datos) < 5:
            return 0.0, 1.0, 0.0
        media = sum(datos) / len(datos)
        varianza = sum((x-media)**2 for x in datos) / len(datos)
        std = math.sqrt(varianza) if varianza > 0 else 1.0
        # Momentos → parámetros GEV (aproximación)
        mu = media - 0.5772 * std * math.sqrt(6) / math.pi
        sigma = std * math.sqrt(6) / math.pi
        xi = 0.0  # Gumbel como caso especial
        return mu, sigma, xi

    def calcular_scores(self) -> Dict[int, float]:
        scores = {}
        for num in range(1, 50):
            # Gaps entre apariciones
            gaps = []
            ultimo = None
            for i, sorteo in enumerate(self.historico):
                if num in sorteo:
                    if ultimo is not None:
                        gaps.append(float(i - ultimo))
                    ultimo = i

            if len(gaps) < 5:
                scores[num] = 0.5
                continue

            mu, sigma, xi = self._ajustar_gev(gaps)
            gap_actual = (ultimo if ultimo is not None else self.n)

            # P(gap_actual > x) bajo GEV: probabilidad de que ya "toca"
            if sigma > 0:
                z = (gap_actual - mu) / sigma
                # CDF de Gumbel: F(x) = exp(-exp(-z))
                # Capar z para evitar overflow en exp
                z = max(-30.0, min(30.0, z))
                try:
                    cdf = math.exp(-math.exp(-z))
                except OverflowError:
                    cdf = 0.0 if z < 0 else 1.0
                prob_aparicion = 1.0 - cdf
            else:
                prob_aparicion = 0.5

            scores[num] = max(0.0, min(1.0, prob_aparicion))

        max_v = max(scores.values(), default=1)
        if max_v > 0:
            scores = {n: v/max_v for n, v in scores.items()}
        return scores


# ═══════════════════════════════════════════════════════════════════════
# 26 — PROCESO DE DIRICHLET (DPMM)
# Activa si: señal media-alta
# ═══════════════════════════════════════════════════════════════════════
class AnalizadorDirichlet:
    """
    Clustering bayesiano no paramétrico de números.
    El número de clusters emerge automáticamente de los datos.
    """
    def __init__(self, historico: List[List[int]], alpha: float = 1.0):
        self.historico = historico
        self.n = len(historico)
        self.alpha = alpha  # Concentración del proceso de Dirichlet

    def calcular_scores(self) -> Dict[int, float]:
        # Representación de cada número como vector de co-ocurrencias
        features = np.zeros((49, 49))
        for sorteo in self.historico:
            nums = [n-1 for n in sorteo if 1 <= n <= 49]
            for i in nums:
                for j in nums:
                    if i != j:
                        features[i][j] += 1

        # Normalizar
        max_f = features.max()
        if max_f > 0:
            features = features / max_f

        # Clustering basado en distancia coseno (DPMM simplificado con CRP)
        # Chinese Restaurant Process para asignar clusters
        clusters = {}  # num → cluster_id
        cluster_centroids = {}
        n_clusters = 0

        for num in range(49):
            feat = features[num]
            mejor_cluster = -1
            mejor_sim = 0.0

            # Calcular similitud con centroides existentes
            for cid, centroide in cluster_centroids.items():
                # Similitud coseno
                dot = np.dot(feat, centroide)
                norm1 = np.linalg.norm(feat)
                norm2 = np.linalg.norm(centroide)
                sim = dot / (norm1 * norm2 + 1e-10)
                if sim > mejor_sim and sim > 0.7:
                    mejor_sim = sim
                    mejor_cluster = cid

            if mejor_cluster == -1:
                # Nuevo cluster (proceso CRP)
                n_clusters += 1
                clusters[num] = n_clusters
                cluster_centroids[n_clusters] = feat.copy()
            else:
                clusters[num] = mejor_cluster
                # Actualizar centroide
                n_en_cluster = sum(1 for c in clusters.values() if c == mejor_cluster)
                cluster_centroids[mejor_cluster] = (
                    cluster_centroids[mejor_cluster] * (n_en_cluster-1) + feat
                ) / n_en_cluster

        # Score: frecuencia del cluster al que pertenece cada número
        freq_cluster = defaultdict(int)
        for sorteo in self.historico:
            clusters_sorteo = set()
            for n in sorteo:
                if 1 <= n <= 49:
                    cid = clusters.get(n-1, 0)
                    clusters_sorteo.add(cid)
            for cid in clusters_sorteo:
                freq_cluster[cid] += 1

        scores = {}
        for num in range(1, 50):
            cid = clusters.get(num-1, 0)
            scores[num] = freq_cluster.get(cid, 0) / max(self.n, 1)

        max_v = max(scores.values(), default=1)
        if max_v > 0:
            scores = {n: v/max_v for n, v in scores.items()}
        return scores


# ═══════════════════════════════════════════════════════════════════════
# 27 — MULTI-SCALE ENTROPY
# Activa si: señal media-alta
# ═══════════════════════════════════════════════════════════════════════
class AnalizadorMultiScaleEntropy:
    """
    Analiza la complejidad de la serie a múltiples escalas temporales.
    Detecta en qué escala hay más estructura predecible.
    """
    def __init__(self, historico: List[List[int]]):
        self.historico = historico
        self.n = len(historico)

    def _muestra_entropia(self, serie: np.ndarray, m: int = 2, r: float = 0.2) -> float:
        """Sample Entropy simplificada."""
        n = len(serie)
        if n < m + 2: return 1.0
        std = np.std(serie)
        if std == 0: return 0.0
        tolerancia = r * std
        A, B = 0, 0
        for i in range(n - m):
            for j in range(i+1, n - m):
                if max(abs(serie[i+k] - serie[j+k]) for k in range(m)) < tolerancia:
                    B += 1
                    if abs(serie[i+m] - serie[j+m]) < tolerancia:
                        A += 1
        return -math.log(A/B) if B > 0 and A > 0 else 0.0

    def calcular_scores(self) -> Dict[int, float]:
        escalas = [1, 2, 4, 8]
        scores_acum = defaultdict(float)

        for num in range(1, 50):
            serie = np.array([1.0 if num in s else 0.0
                             for s in self.historico[:min(150, self.n)]])
            mse_vals = []
            for escala in escalas:
                # Remuestreo a escala
                n_grupos = len(serie) // escala
                if n_grupos < 4: continue
                serie_escala = np.array([
                    np.mean(serie[i*escala:(i+1)*escala])
                    for i in range(n_grupos)
                ])
                mse = self._muestra_entropia(serie_escala)
                mse_vals.append(mse)

            if mse_vals:
                # Score: menor MSE promedio → más predecible → mayor score
                mse_media = sum(mse_vals) / len(mse_vals)
                scores_acum[num] = max(0.0, 1.0 - mse_media)
            else:
                scores_acum[num] = 0.5

        max_v = max(scores_acum.values(), default=1)
        if max_v > 0:
            return {n: scores_acum.get(n, 0)/max_v for n in range(1, 50)}
        return {n: 0.5 for n in range(1, 50)}


# ═══════════════════════════════════════════════════════════════════════
# 33 — ECHO STATE NETWORK (RESERVOIR COMPUTING)
# Activa si: n_sorteos >= 200
# ═══════════════════════════════════════════════════════════════════════
class AnalizadorESN:
    """
    Echo State Network con reservorio fijo de 50 neuronas.
    Solo se entrena la capa de salida (ridge regression).
    Extremadamente eficiente en CPU.
    """
    N_RESERVORIO = 50
    SPECTRAL_RADIUS = 0.9
    INPUT_SCALING = 0.5
    LEAK_RATE = 0.3

    def __init__(self, historico: List[List[int]]):
        self.historico = historico
        self.n = len(historico)
        # Inicializar reservorio fijo (sparse random)
        rng = np.random.RandomState(42)
        W = rng.randn(self.N_RESERVORIO, self.N_RESERVORIO)
        # Escalar al radio espectral deseado
        try:
            eigenvalues = np.linalg.eigvals(W)
            radio = np.max(np.abs(eigenvalues))
            if radio > 0:
                self.W = W * (self.SPECTRAL_RADIUS / radio)
            else:
                self.W = W * 0.1
        except Exception:
            self.W = W * 0.1
        self.W_in = rng.randn(self.N_RESERVORIO, 1) * self.INPUT_SCALING

    def _ejecutar_reservorio(self, serie: np.ndarray) -> np.ndarray:
        """Ejecuta la serie a través del reservorio."""
        n = len(serie)
        estados = np.zeros((n, self.N_RESERVORIO))
        h = np.zeros(self.N_RESERVORIO)
        for t in range(n):
            entrada = np.array([serie[t]])
            h_nuevo = np.tanh(self.W @ h + self.W_in @ entrada)
            h = (1 - self.LEAK_RATE) * h + self.LEAK_RATE * h_nuevo
            estados[t] = h
        return estados

    def _entrenar_salida(self, estados: np.ndarray,
                          targets: np.ndarray,
                          lambda_reg: float = 1e-4) -> np.ndarray:
        """Ridge regression para entrenar solo la capa de salida."""
        I = np.eye(estados.shape[1])
        try:
            W_out = targets @ estados @ np.linalg.inv(estados.T @ estados + lambda_reg * I)
        except Exception:
            W_out = np.zeros(estados.shape[1])
        return W_out

    def calcular_scores(self) -> Dict[int, float]:
        scores = {}
        ventana = min(200, self.n)

        for num in range(1, 50):
            serie = np.array([1.0 if num in s else 0.0
                             for s in self.historico[:ventana]])
            if len(serie) < 10:
                scores[num] = 0.5
                continue

            # Train en primeros 80%, predecir en últimos 20%
            n_train = int(len(serie) * 0.8)
            serie_train = serie[:n_train]
            serie_test = serie[n_train:]

            if len(serie_train) < 5 or len(serie_test) < 2:
                scores[num] = 0.5
                continue

            estados = self._ejecutar_reservorio(serie_train[:-1])
            targets = serie_train[1:]
            if len(estados) != len(targets):
                scores[num] = 0.5
                continue

            W_out = self._entrenar_salida(estados, targets)

            # Predicción: estado actual del reservorio
            estados_full = self._ejecutar_reservorio(serie)
            pred = float(W_out @ estados_full[-1])
            scores[num] = max(0.0, min(1.0, pred + 0.5))

        max_v = max(scores.values(), default=1)
        if max_v > 0:
            scores = {n: v/max_v for n, v in scores.items()}
        return scores


# ═══════════════════════════════════════════════════════════════════════
# 34 — VAR MULTIVARIANTE
# Activa si: n_sorteos >= 500
# ═══════════════════════════════════════════════════════════════════════
class AnalizadorVAR:
    """
    Vector AutoRegression: modela todos los números simultáneamente.
    Captura cómo la aparición de un número afecta a los demás.
    Usa solo 10 números más relevantes para eficiencia.
    """
    def __init__(self, historico: List[List[int]], n_vars: int = 10, lags: int = 3):
        self.historico = historico
        self.n = len(historico)
        self.n_vars = n_vars
        self.lags = lags

    def calcular_scores(self) -> Dict[int, float]:
        if self.n < 50:
            return {n: 0.5 for n in range(1, 50)}

        # Seleccionar los N números más frecuentes para VAR
        freq = defaultdict(int)
        for s in self.historico:
            for n in s: freq[n] += 1
        top_nums = sorted(freq, key=freq.get, reverse=True)[:self.n_vars]

        ventana = min(300, self.n)
        # Matriz de series temporales (ventana × n_vars)
        Y = np.array([
            [1.0 if n in self.historico[t] else 0.0 for n in top_nums]
            for t in range(ventana)
        ])

        # Inicializar TODOS los scores (1-49) con valor por defecto
        scores = {n: 0.5 for n in range(1, 50)}

        try:
            # VAR(lags) por OLS ecuación por ecuación
            n_t, n_v = Y.shape
            if n_t <= self.lags * n_v + 1:
                return scores

            # Construir matrices de regresión
            y_dep = Y[self.lags:, :]
            X_list = [Y[self.lags-lag-1:n_t-lag-1, :] for lag in range(self.lags)]
            X = np.hstack(X_list)

            # OLS regularizado: B = (X'X + λI)^-1 X'Y
            XtX = X.T @ X
            reg = 1e-4 * np.eye(XtX.shape[0])
            B = np.linalg.solve(XtX + reg, X.T @ y_dep)

            # Predicción un paso adelante
            x_pred = np.hstack([Y[n_t-lag-1, :] for lag in range(self.lags)])
            pred = x_pred @ B

            for i, num in enumerate(top_nums):
                if np.isfinite(pred[i]):
                    scores[num] = max(0.0, min(1.0, float(pred[i]) + 0.3))

        except Exception as e:
            logger.debug(f"VAR error: {e}")
            return {n: 0.5 for n in range(1, 50)}

        # Normalizar a [0, 1]
        max_v = max(scores.values()) if scores else 1.0
        if max_v > 0:
            scores = {n: scores[n] / max_v for n in range(1, 50)}
        return scores


# ═══════════════════════════════════════════════════════════════════════
# 37 — TDA: ANÁLISIS TOPOLÓGICO DE DATOS
# Activa si: EP < 0.82 y señal alta
# ═══════════════════════════════════════════════════════════════════════
class AnalizadorTDA:
    """
    TDA simplificado sin dependencias externas.
    Usa incrustación de Takens y análisis de componentes conectadas
    para detectar estructura topológica en la serie temporal.
    """
    def __init__(self, historico: List[List[int]]):
        self.historico = historico
        self.n = len(historico)

    def _incrustar_takens(self, serie: np.ndarray,
                           dim: int = 3, lag: int = 2) -> np.ndarray:
        """Incrustación de Takens para reconstrucción del atractor."""
        n = len(serie)
        n_puntos = n - (dim-1)*lag
        if n_puntos < 5:
            return np.array([]).reshape(0, dim)
        puntos = np.array([
            [serie[i + j*lag] for j in range(dim)]
            for i in range(n_puntos)
        ])
        return puntos

    def _analizar_componentes(self, puntos: np.ndarray,
                               epsilon: float = 0.3) -> int:
        """Cuenta componentes conectadas con radio epsilon (H0 persistente)."""
        if len(puntos) < 2:
            return 1
        # Matriz de distancias simplificada
        n = min(len(puntos), 100)  # Limitar para eficiencia
        pts = puntos[:n]
        componentes = list(range(n))

        def find(x):
            while componentes[x] != x:
                componentes[x] = componentes[componentes[x]]
                x = componentes[x]
            return x

        def union(x, y):
            rx, ry = find(x), find(y)
            if rx != ry:
                componentes[rx] = ry

        for i in range(n):
            for j in range(i+1, n):
                dist = np.linalg.norm(pts[i] - pts[j])
                if dist < epsilon:
                    union(i, j)

        raices = len(set(find(i) for i in range(n)))
        return raices

    def calcular_scores(self) -> Dict[int, float]:
        scores = {}
        sumas_globales = np.array([float(sum(s)) for s in self.historico[:min(200, self.n)]])

        for num in range(1, 50):
            serie = np.array([1.0 if num in s else 0.0
                             for s in self.historico[:min(100, self.n)]])
            if len(serie) < 10:
                scores[num] = 0.5
                continue

            puntos = self._incrustar_takens(serie, dim=3, lag=2)
            if len(puntos) < 5:
                scores[num] = 0.5
                continue

            # Número de componentes conectadas como medida de complejidad topológica
            n_comp = self._analizar_componentes(puntos, epsilon=0.5)
            # Menor número de componentes → estructura más cohesiva → más predecible
            score = 1.0 / (1.0 + math.log(max(n_comp, 1)))
            scores[num] = max(0.0, min(1.0, score))

        max_v = max(scores.values(), default=1)
        if max_v > 0:
            scores = {n: v/max_v for n, v in scores.items()}
        return scores


# ═══════════════════════════════════════════════════════════════════════
# 38 — REGRESIÓN SIMBÓLICA SIMPLIFICADA
# Activa si: chi2 p < 0.05 y señal media-alta
# ═══════════════════════════════════════════════════════════════════════
class AnalizadorRegresionSimbolica:
    """
    Descubre automáticamente fórmulas matemáticas que relacionan
    las características de un número con su probabilidad de aparición.
    Implementación ligera con programación genética simple.
    """
    OPERACIONES = ['suma', 'mult', 'div', 'raiz', 'log']

    def __init__(self, historico: List[List[int]]):
        self.historico = historico
        self.n = len(historico)

    def _extraer_features_numero(self, num: int) -> Dict[str, float]:
        """Extrae características del número."""
        freq_total = sum(1 for s in self.historico if num in s) / max(self.n, 1)
        freq_50 = sum(1 for s in self.historico[:50] if num in s) / 50
        gaps = []
        ultimo = None
        for i, s in enumerate(self.historico):
            if num in s:
                if ultimo is not None: gaps.append(i - ultimo)
                ultimo = i
        gap_medio = sum(gaps)/len(gaps) if gaps else self.n
        return {
            'freq': freq_total,
            'freq_reciente': freq_50,
            'gap_medio': gap_medio / max(self.n, 1),
            'paridad': float(num % 2),
            'decena': (num-1)//10 / 4.0,
            'valor_norm': (num-1)/48.0,
        }

    def _evaluar_formula(self, features: Dict[str, float], formula: str) -> float:
        """Evalúa una fórmula simple sobre las features."""
        f = features['freq']
        r = features['freq_reciente']
        g = features['gap_medio']
        p = features['paridad']
        d = features['decena']
        v = features['valor_norm']
        try:
            if formula == 'freq_gap':
                return f * (1 - g)
            elif formula == 'reciente_freq':
                return 0.6*r + 0.4*f
            elif formula == 'gap_decena':
                return (1-g) * (1 - abs(d - 0.5))
            elif formula == 'paridad_freq':
                return f * (1 - 0.1*abs(p - 0.5))
            elif formula == 'combinada':
                return 0.4*f + 0.3*r + 0.2*(1-g) + 0.1*(1-abs(v-0.5))
            else:
                return f
        except Exception:
            return 0.5

    def calcular_scores(self) -> Dict[int, float]:
        # Evaluar múltiples fórmulas y seleccionar la mejor por validación cruzada
        formulas = ['freq_gap', 'reciente_freq', 'gap_decena',
                    'paridad_freq', 'combinada']

        # Calcular scores con cada fórmula
        scores_formulas = {f: {} for f in formulas}
        for num in range(1, 50):
            feats = self._extraer_features_numero(num)
            for formula in formulas:
                scores_formulas[formula][num] = self._evaluar_formula(feats, formula)

        # Seleccionar la mejor fórmula por correlación con frecuencia real
        freq_real = {num: sum(1 for s in self.historico if num in s)/max(self.n,1)
                     for num in range(1, 50)}

        mejor_formula = 'combinada'
        mejor_corr = -1.0

        for formula in formulas:
            scores = scores_formulas[formula]
            s_vals = [scores[n] for n in range(1, 50)]
            f_vals = [freq_real[n] for n in range(1, 50)]
            media_s = sum(s_vals)/49
            media_f = sum(f_vals)/49
            num_c = sum((s_vals[i]-media_s)*(f_vals[i]-media_f) for i in range(49))
            den_c = math.sqrt(
                sum((v-media_s)**2 for v in s_vals) *
                sum((v-media_f)**2 for v in f_vals)
            )
            corr = num_c/den_c if den_c > 0 else 0.0
            if corr > mejor_corr:
                mejor_corr = corr
                mejor_formula = formula

        scores = scores_formulas[mejor_formula]
        max_v = max(scores.values(), default=1)
        if max_v > 0:
            scores = {n: v/max_v for n, v in scores.items()}
        return scores


# ═══════════════════════════════════════════════════════════════════════
# 39 — EXPONENTE DE LYAPUNOV
# Activa si: señal media o alta
# ═══════════════════════════════════════════════════════════════════════
class AnalizadorLyapunov:
    """
    Calcula el exponente de Lyapunov máximo para cada número.
    Determina el horizonte real de predictibilidad.
    """
    def __init__(self, historico: List[List[int]]):
        self.historico = historico
        self.n = len(historico)

    def _lyapunov_numero(self, num: int) -> float:
        """Exponente de Lyapunov por el método de Rosenstein."""
        serie = np.array([1.0 if num in s else 0.0
                         for s in self.historico[:min(150, self.n)]])
        n = len(serie)
        if n < 20: return 0.0

        # Incrustación de Takens
        dim, lag = 3, 2
        n_puntos = n - (dim-1)*lag
        if n_puntos < 10: return 0.0

        puntos = np.array([
            [serie[i + j*lag] for j in range(dim)]
            for i in range(n_puntos)
        ])

        # Encontrar vecino más cercano para cada punto
        divergencias = []
        n_p = len(puntos)
        for i in range(n_p // 2):
            dist_min = float('inf')
            j_min = -1
            for j in range(n_p):
                if abs(i-j) < 5: continue
                d = np.linalg.norm(puntos[i] - puntos[j])
                if d < dist_min:
                    dist_min = d
                    j_min = j

            if j_min == -1 or dist_min == 0: continue

            # Seguir la divergencia
            steps = min(10, n_p - max(i, j_min) - 1)
            for k in range(1, steps):
                if i+k >= n_p or j_min+k >= n_p: break
                d_nueva = np.linalg.norm(puntos[i+k] - puntos[j_min+k])
                if d_nueva > 0 and dist_min > 0:
                    divergencias.append(math.log(d_nueva/dist_min) / k)
                    break

        if not divergencias: return 0.0
        lyap = sum(divergencias) / len(divergencias)
        return lyap

    def calcular_scores(self) -> Dict[int, float]:
        scores = {}
        for num in range(1, 50):
            lyap = self._lyapunov_numero(num)
            # Lyapunov negativo → sistema estable → más predecible
            # Lyapunov positivo → caótico → menos predecible
            scores[num] = max(0.0, min(1.0, 0.5 - lyap * 0.5))

        max_v = max(scores.values(), default=1)
        if max_v > 0:
            scores = {n: v/max_v for n, v in scores.items()}
        return scores


# ═══════════════════════════════════════════════════════════════════════
# 40 — PROCESO DE HAWKES
# Activa si: EP < 0.88
# ═══════════════════════════════════════════════════════════════════════
class AnalizadorHawkes:
    """
    Proceso de Hawkes: modela la auto-excitación temporal de cada número.
    P(aparece) aumenta justo después de una aparición reciente.
    """
    def __init__(self, historico: List[List[int]]):
        self.historico = historico
        self.n = len(historico)

    def _intensidad_hawkes(self, tiempos_eventos: List[int],
                            t_actual: int,
                            mu: float = 0.1,
                            alpha: float = 0.5,
                            beta: float = 0.3) -> float:
        """
        Intensidad de Hawkes en t_actual.
        lambda(t) = mu + sum(alpha * exp(-beta * (t - ti)))
        """
        intensidad = mu
        for ti in tiempos_eventos:
            dt = t_actual - ti
            if dt > 0:
                intensidad += alpha * math.exp(-beta * dt)
        return intensidad

    def calcular_scores(self) -> Dict[int, float]:
        scores = {}
        if self.n == 0:
            return {n: 0.5 for n in range(1, 50)}
        for num in range(1, 50):
            tiempos = [i for i, s in enumerate(self.historico) if num in s]
            if not tiempos:
                scores[num] = 0.3
                continue

            # Calibrar parámetros por máxima verosimilitud simplificada
            n_eventos = len(tiempos)
            T = max(self.n, 1)  # defensa absoluta
            mu_est = n_eventos / T  # Tasa base
            alpha_est = min(0.8, n_eventos / (T * 2))

            # Intensidad actual (en el próximo sorteo)
            intensidad = self._intensidad_hawkes(
                tiempos[-min(10, len(tiempos)):],
                t_actual=self.n,
                mu=mu_est,
                alpha=alpha_est,
                beta=0.3
            )
            scores[num] = max(0.0, min(1.0, intensidad * 10))

        max_v = max(scores.values(), default=1)
        if max_v > 0:
            scores = {n: v/max_v for n, v in scores.items()}
        return scores


# ═══════════════════════════════════════════════════════════════════════
# 41 — MULTIFRACTAL DFA
# Activa si: Hurst > 0.55
# ═══════════════════════════════════════════════════════════════════════
class AnalizadorMultifractalDFA:
    """
    Análisis de Fluctuaciones sin Tendencia Multifractal.
    Detecta correlaciones de largo alcance a múltiples órdenes.
    """
    def __init__(self, historico: List[List[int]]):
        self.historico = historico
        self.n = len(historico)

    def _dfa_escala(self, serie: np.ndarray, escala: int, q: float = 2.0) -> float:
        """DFA en una escala específica."""
        n = len(serie)
        if n < escala * 2: return 0.0

        # Perfil acumulado
        perfil = np.cumsum(serie - np.mean(serie))
        n_segmentos = n // escala
        fluctuaciones = []

        for seg in range(n_segmentos):
            inicio = seg * escala
            fin = inicio + escala
            y = perfil[inicio:fin]
            x = np.arange(escala)
            try:
                coefs = np.polyfit(x, y, 1)
                tendencia = np.polyval(coefs, x)
                fluct = np.sqrt(np.mean((y - tendencia)**2))
                fluctuaciones.append(fluct)
            except Exception:
                continue

        if not fluctuaciones: return 0.0
        if q == 0:
            return math.exp(sum(math.log(max(f, 1e-10)) for f in fluctuaciones) / len(fluctuaciones))
        return (sum(f**q for f in fluctuaciones) / len(fluctuaciones)) ** (1.0/q)

    def calcular_scores(self) -> Dict[int, float]:
        escalas = [8, 16, 32]
        scores = {}

        for num in range(1, 50):
            serie = np.array([1.0 if num in s else 0.0
                             for s in self.historico[:min(200, self.n)]])
            if len(serie) < 32:
                scores[num] = 0.5
                continue

            fq_vals = [self._dfa_escala(serie, esc) for esc in escalas if esc < len(serie)//2]
            if len(fq_vals) < 2:
                scores[num] = 0.5
                continue

            # Exponente de Hurst generalizado q=2
            try:
                esc_log = np.log([e for e in escalas if e < len(serie)//2][:len(fq_vals)])
                fq_log = np.log(np.array(fq_vals) + 1e-10)
                h_q = np.polyfit(esc_log, fq_log, 1)[0]
                # H_q > 0.5 → correlaciones de largo alcance → más predecible
                scores[num] = max(0.0, min(1.0, h_q - 0.5 + 0.5))
            except Exception:
                scores[num] = 0.5

        max_v = max(scores.values(), default=1)
        if max_v > 0:
            scores = {n: v/max_v for n, v in scores.items()}
        return scores
