"""
╔══════════════════════════════════════════════════════════════════════════════╗
║   BONOLOTO AI v7.0 — BLOQUE K (EXTENDIDO COMPLETO)                          ║
║                                                                              ║
║   17 mejoras adicionales (94-110):                                          ║
║                                                                              ║
║   BLOQUE K ORIGINAL (9):                                                    ║
║     94. NGRC — Next Generation Reservoir Computing                          ║
║     95. DMD/Koopman Operator                                                ║
║     96. KAN simplificado (Kolmogorov-Arnold Networks con B-splines)         ║
║     97. DLinear / NLinear (AAAI 2023)                                       ║
║     98. SINDy lite — Sparse Identification of Nonlinear Dynamics            ║
║     99. TSFresh — 794 features automáticas                                  ║
║    100. N-HiTS — Hierarchical Interpolation Time Series                     ║
║    101. FITS — Frequency Interpolation Time Series                          ║
║    102. TimeMixer simplificado (ICLR 2024)                                  ║
║                                                                              ║
║   BLOQUE K EXTENDIDO RONDA 1 (5):                                           ║
║    103. Modern Hopfield Network (Ramsauer 2020)                             ║
║    104. Vine Copulas D-vine/C-vine                                          ║
║    105. MiniRocket — Random Convolutional Kernels                           ║
║    106. Visibility Graph (Lacasa)                                           ║
║    107. Association Rule Mining (Apriori/FP-Growth)                         ║
║                                                                              ║
║   BLOQUE K EXTENDIDO RONDA 3 — REDES NEURONALES (3):                        ║
║    108. RBM — Restricted Boltzmann Machine                                  ║
║    109. SOM — Self-Organizing Map (Kohonen)                                 ║
║    110. HDC/VSA — Hyperdimensional Computing                                ║
║                                                                              ║
║   Todas las técnicas son: CPU puro, sin GPU, sin PyTorch/TF,                ║
║   compatibles con Oracle Cloud ARM Ampere A1.                               ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import logging
from typing import Dict, List, Optional, Tuple
import numpy as np
from scipy import signal as scipy_signal
from scipy.stats import norm, rankdata
from scipy.linalg import lstsq, svd, pinv
from itertools import combinations

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════════════
#  UTILIDADES INTERNAS DEL BLOQUE K
# ════════════════════════════════════════════════════════════════════════════
def _to_freq_matrix(historico: List[List[int]], n_max: int = 49) -> np.ndarray:
    """Convierte el histórico en una matriz binaria T x 49 (1 si la bola salió)."""
    T = len(historico)
    M = np.zeros((T, n_max), dtype=np.float32)
    for t, sorteo in enumerate(historico):
        for n in sorteo:
            if 1 <= n <= n_max:
                M[t, n - 1] = 1.0
    return M


def _to_count_series(historico: List[List[int]], n_max: int = 49,
                     ventana: int = 20) -> np.ndarray:
    """Devuelve una serie temporal T x 49 con frecuencia móvil por ventana."""
    M = _to_freq_matrix(historico, n_max)
    if M.shape[0] < ventana:
        return M
    out = np.zeros_like(M)
    for t in range(M.shape[0]):
        i0 = max(0, t - ventana + 1)
        out[t] = M[i0:t + 1].mean(axis=0)
    return out


def _normalizar_scores(scores: Dict[int, float]) -> Dict[int, float]:
    """Normaliza scores al rango [0, 1]."""
    if not scores:
        return {n: 0.0 for n in range(1, 50)}
    vals = np.array(list(scores.values()), dtype=np.float64)
    vmin, vmax = vals.min(), vals.max()
    if vmax - vmin < 1e-9:
        return {n: 0.5 for n in scores}
    return {n: float((v - vmin) / (vmax - vmin)) for n, v in scores.items()}


def _scores_uniformes() -> Dict[int, float]:
    """Devuelve scores uniformes (fallback en caso de error)."""
    return {n: 0.5 for n in range(1, 50)}


# ════════════════════════════════════════════════════════════════════════════
#  94. NGRC — Next Generation Reservoir Computing (numpy puro)
#  Gauthier et al. Nat. Commun. 2021
# ════════════════════════════════════════════════════════════════════════════
class AnalizadorNGRC:
    """
    Sustituto moderno de ESN sin reservoir oculto: usa lags lineales y
    productos cuadráticos no lineales con regresión ridge. Más rápido y
    estable que ESN clásico, según Gauthier 2021.
    """

    def __init__(self, historico: List[List[int]], k_lags: int = 4,
                 ridge: float = 2.5e-4):
        self.hist = historico
        self.k = k_lags
        self.ridge = ridge

    def _features(self, M: np.ndarray, t: int) -> np.ndarray:
        # Vector lineal: lags concatenados
        lin = np.concatenate([M[t - i] for i in range(1, self.k + 1)])
        # Vector cuadrático: productos cruzados (sub-muestra para no explotar dim)
        n = len(lin)
        # tomamos sólo combinaciones consecutivas para mantener O(n)
        cuad = lin[:-1] * lin[1:]
        return np.concatenate([lin, cuad, [1.0]])

    def calcular_scores(self) -> Dict[int, float]:
        try:
            M = _to_freq_matrix(self.hist)
            T = M.shape[0]
            if T < self.k + 30:
                return _scores_uniformes()
            X, Y = [], []
            for t in range(self.k, T - 1):
                X.append(self._features(M, t))
                Y.append(M[t + 1])
            X = np.array(X)
            Y = np.array(Y)
            # Regresión ridge cerrada
            XtX = X.T @ X + self.ridge * np.eye(X.shape[1])
            W = np.linalg.solve(XtX, X.T @ Y)
            # Predicción del siguiente sorteo
            x_last = self._features(M, T - 1).reshape(1, -1)
            y_pred = (x_last @ W).flatten()
            y_pred = np.clip(y_pred, 0.0, 1.0)
            return _normalizar_scores({n + 1: float(y_pred[n]) for n in range(49)})
        except Exception as e:
            logger.warning(f"NGRC fallback: {e}")
            return _scores_uniformes()


# ════════════════════════════════════════════════════════════════════════════
#  95. DMD / Koopman Operator
#  Identifica modos espacio-temporales coherentes del histórico
# ════════════════════════════════════════════════════════════════════════════
class AnalizadorDMDKoopman:
    """
    Dynamic Mode Decomposition: descompone el histórico en modos coherentes
    de evolución temporal mediante el operador lineal de Koopman.
    """

    def __init__(self, historico: List[List[int]], rango: int = 12):
        self.hist = historico
        self.r = rango

    def calcular_scores(self) -> Dict[int, float]:
        try:
            M = _to_freq_matrix(self.hist)
            if M.shape[0] < 30:
                return _scores_uniformes()
            X = M[:-1].T   # 49 x (T-1)
            Y = M[1:].T    # 49 x (T-1)
            U, S, Vt = svd(X, full_matrices=False)
            # Filtrar valores singulares casi cero
            tol = max(S[0] * 1e-10, 1e-12) if len(S) > 0 else 1e-12
            S_valid = S[S > tol]
            r = min(self.r, len(S_valid))
            if r < 1:
                return _scores_uniformes()
            U_r = U[:, :r]
            S_r_inv = np.diag(1.0 / S_valid[:r])  # inverso directo (más estable)
            V_r = Vt[:r, :].T
            A_tilde = U_r.T @ Y @ V_r @ S_r_inv
            eigvals, eigvecs = np.linalg.eig(A_tilde)
            phi = Y @ V_r @ S_r_inv @ eigvecs
            energia = np.zeros(49)
            for i in range(r):
                peso = float(abs(eigvals[i]))
                energia += peso * np.abs(phi[:, i].real)
            scores = {n + 1: float(energia[n]) for n in range(49)}
            return _normalizar_scores(scores)
        except Exception as e:
            logger.warning(f"DMD/Koopman fallback: {e}")
            return _scores_uniformes()


# ════════════════════════════════════════════════════════════════════════════
#  96. KAN simplificado — Kolmogorov-Arnold Networks (scipy B-splines)
# ════════════════════════════════════════════════════════════════════════════
class AnalizadorKAN:
    """
    Kolmogorov-Arnold Network simplificado: combinación de funciones
    univariadas aprendidas con B-splines en lugar de pesos lineales.
    """

    def __init__(self, historico: List[List[int]], n_knots: int = 8,
                 grado: int = 3):
        self.hist = historico
        self.n_knots = n_knots
        self.grado = grado

    def _spline_basis(self, x: np.ndarray) -> np.ndarray:
        """Genera matriz de base spline manual (B-splines uniformes)."""
        knots = np.linspace(0.0, 1.0, self.n_knots)
        basis = np.zeros((len(x), self.n_knots))
        sigma = 1.0 / self.n_knots
        for i, k in enumerate(knots):
            basis[:, i] = np.exp(-((x - k) ** 2) / (2 * sigma ** 2))
        return basis

    def calcular_scores(self) -> Dict[int, float]:
        try:
            M = _to_count_series(self.hist, ventana=15)
            if M.shape[0] < 40:
                return _scores_uniformes()
            X = M[:-1]
            Y = M[1:]
            scores = np.zeros(49)
            for n in range(49):
                xn = X[:, n]
                yn = Y[:, n]
                B = self._spline_basis(xn)
                # Regresión sobre base spline
                coef, *_ = lstsq(B, yn)
                x_last = np.array([M[-1, n]])
                pred = (self._spline_basis(x_last) @ coef)[0]
                scores[n] = max(0.0, min(1.0, float(pred)))
            return _normalizar_scores({n + 1: float(scores[n]) for n in range(49)})
        except Exception as e:
            logger.warning(f"KAN fallback: {e}")
            return _scores_uniformes()


# ════════════════════════════════════════════════════════════════════════════
#  97. DLinear / NLinear — Modelos lineales potentes (AAAI 2023)
# ════════════════════════════════════════════════════════════════════════════
class AnalizadorDLinear:
    """
    DLinear: descomposición tendencia/estacional + capa lineal sobre cada
    componente. Sorprendentemente potente vs Transformers (Zeng 2023).
    NLinear añade normalización por valor de inicio.
    """

    def __init__(self, historico: List[List[int]], lookback: int = 30):
        self.hist = historico
        self.lookback = lookback

    def _descomp(self, x: np.ndarray, kernel: int = 7) -> Tuple[np.ndarray, np.ndarray]:
        """Descompone en tendencia móvil y estacional residual."""
        if len(x) < kernel:
            return x, np.zeros_like(x)
        trend = np.convolve(x, np.ones(kernel) / kernel, mode='same')
        seasonal = x - trend
        return trend, seasonal

    def calcular_scores(self) -> Dict[int, float]:
        try:
            M = _to_count_series(self.hist, ventana=12)
            T = M.shape[0]
            if T < self.lookback + 5:
                return _scores_uniformes()
            scores = np.zeros(49)
            L = self.lookback
            for n in range(49):
                serie = M[-L:, n]
                trend, seasonal = self._descomp(serie)
                # Regresión lineal sobre cada componente
                t_idx = np.arange(L)
                with np.errstate(divide='ignore', invalid='ignore'):
                    try:
                        p_trend = np.polyfit(t_idx, trend, 1) if np.std(trend) > 1e-9 else [0.0, float(trend.mean())]
                        p_seas = np.polyfit(t_idx, seasonal, 1) if np.std(seasonal) > 1e-9 else [0.0, 0.0]
                    except (np.linalg.LinAlgError, ValueError):
                        p_trend = [0.0, float(serie.mean())]
                        p_seas = [0.0, 0.0]
                pred_trend = np.polyval(p_trend, L)
                pred_seas = np.polyval(p_seas, L)
                pred = pred_trend + pred_seas
                scores[n] = max(0.0, min(1.0, float(pred)))
            return _normalizar_scores({n + 1: float(scores[n]) for n in range(49)})
        except Exception as e:
            logger.warning(f"DLinear fallback: {e}")
            return _scores_uniformes()


# ════════════════════════════════════════════════════════════════════════════
#  98. SINDy lite — Sparse Identification of Nonlinear Dynamics
# ════════════════════════════════════════════════════════════════════════════
class AnalizadorSINDy:
    """
    Identifica ecuaciones diferenciales discretas sparse mediante una
    biblioteca de funciones candidatas + Lasso (Brunton 2016).
    """

    def __init__(self, historico: List[List[int]], lambda_l1: float = 0.05):
        self.hist = historico
        self.lambda_l1 = lambda_l1

    def _library(self, X: np.ndarray) -> np.ndarray:
        """Genera biblioteca de candidatos: x, x^2, x*x_lag, 1."""
        T, n = X.shape
        lib = [np.ones(T), X.mean(axis=1)]
        lib.append((X ** 2).mean(axis=1))
        if T > 1:
            shifted = np.roll(X, 1, axis=0)
            shifted[0] = 0
            lib.append((X * shifted).mean(axis=1))
        return np.array(lib).T   # T x 4

    def _soft_threshold(self, x: np.ndarray, lam: float) -> np.ndarray:
        return np.sign(x) * np.maximum(np.abs(x) - lam, 0)

    def calcular_scores(self) -> Dict[int, float]:
        try:
            M = _to_count_series(self.hist, ventana=10)
            if M.shape[0] < 25:
                return _scores_uniformes()
            X = M[:-1]
            Y = M[1:]
            L = self._library(X)
            # Generar features del último estado para predicción
            L_last = self._library(M[-2:])  # devolvemos 2 muestras y tomamos la última
            scores = np.zeros(49)
            for n in range(49):
                # Regresión iterativa con sparsificación (STLSQ)
                yn = Y[:, n]
                coef, *_ = lstsq(L, yn)
                for _ in range(8):
                    coef = self._soft_threshold(coef, self.lambda_l1)
                    mask = np.abs(coef) > 1e-6
                    if mask.sum() == 0:
                        break
                    coef_new, *_ = lstsq(L[:, mask], yn)
                    coef = np.zeros_like(coef)
                    coef[mask] = coef_new
                # Predicción usando la última fila de features
                pred = float(L_last[-1] @ coef)
                scores[n] = max(0.0, min(1.0, pred))
            return _normalizar_scores({n + 1: float(scores[n]) for n in range(49)})
        except Exception as e:
            logger.warning(f"SINDy fallback: {e}")
            return _scores_uniformes()


# ════════════════════════════════════════════════════════════════════════════
#  99. TSFresh — Features automáticas (compatible con CPU, sin GPU)
# ════════════════════════════════════════════════════════════════════════════
class AnalizadorTSFresh:
    """
    Extracción automática de features estadísticas (versión interna ligera
    sin depender de tsfresh por temas de instalación; calcula ~30 features
    clásicas predictivas).
    """

    def __init__(self, historico: List[List[int]]):
        self.hist = historico

    def _features_serie(self, x: np.ndarray) -> np.ndarray:
        """Calcula ~30 features estadísticas para una serie."""
        if len(x) < 3:
            return np.zeros(30)
        f = []
        f.append(np.mean(x))
        f.append(np.std(x))
        f.append(np.max(x) - np.min(x))
        f.append(np.median(x))
        f.append(np.percentile(x, 25))
        f.append(np.percentile(x, 75))
        f.append(np.sum(np.diff(x) > 0) / max(len(x) - 1, 1))     # ascensos
        f.append(np.sum(np.abs(np.diff(x))))                       # variación
        f.append(np.mean(np.abs(x - np.mean(x))))                  # MAD
        f.append(np.std(np.diff(x)) if len(x) > 1 else 0)
        # Autocorrelaciones
        for lag in [1, 2, 3, 5, 10]:
            if len(x) > lag:
                a = x[:-lag] - np.mean(x[:-lag])
                b = x[lag:] - np.mean(x[lag:])
                denom = np.std(a) * np.std(b) * len(a)
                f.append(np.dot(a, b) / denom if denom > 0 else 0)
            else:
                f.append(0)
        # Momentos
        for k in [3, 4]:
            mean = np.mean(x)
            std = np.std(x) + 1e-9
            f.append(np.mean(((x - mean) / std) ** k))
        # Counts arriba/abajo de la media
        m = np.mean(x)
        f.append(np.sum(x > m) / len(x))
        f.append(np.sum(x < m) / len(x))
        # Energía y entropía discreta
        f.append(np.sum(x ** 2))
        hist, _ = np.histogram(x, bins=5)
        p = hist / max(hist.sum(), 1)
        ent = -np.sum(p * np.log(p + 1e-12))
        f.append(ent)
        # Forecasting trivial: tendencia
        if len(x) > 1 and np.std(x) > 1e-9:
            t = np.arange(len(x))
            with np.errstate(divide='ignore', invalid='ignore'):
                try:
                    slope = float(np.polyfit(t, x, 1)[0])
                    if not np.isfinite(slope):
                        slope = 0.0
                except (np.linalg.LinAlgError, ValueError):
                    slope = 0.0
            f.append(slope)
        else:
            f.append(0)
        # rellenar hasta 30
        while len(f) < 30:
            f.append(0)
        return np.array(f[:30])

    def calcular_scores(self) -> Dict[int, float]:
        try:
            M = _to_count_series(self.hist, ventana=15)
            if M.shape[0] < 20:
                return _scores_uniformes()
            # Features por número
            feat = np.zeros((49, 30))
            for n in range(49):
                feat[n] = self._features_serie(M[:, n])
            # Score = combinación lineal simple de features estandarizadas
            mu = feat.mean(axis=0)
            sd = feat.std(axis=0) + 1e-9
            z = (feat - mu) / sd
            # Pesos heurísticos: priorizamos tendencia (índice 29) y media reciente
            pesos = np.zeros(30)
            pesos[0] = 0.20    # media
            pesos[1] = -0.10   # std
            pesos[6] = 0.15    # ascensos
            pesos[10] = 0.15   # AC lag 1
            pesos[29] = 0.30   # tendencia
            score_arr = z @ pesos
            # Clip antes de sigmoid para evitar overflow en exp(-x) si x muy negativo
            score_arr = np.clip(score_arr, -30, 30)
            score_arr = 1 / (1 + np.exp(-score_arr))   # sigmoid
            return _normalizar_scores({n + 1: float(score_arr[n]) for n in range(49)})
        except Exception as e:
            logger.warning(f"TSFresh fallback: {e}")
            return _scores_uniformes()


# ════════════════════════════════════════════════════════════════════════════
# 100. N-HiTS — Neural Hierarchical Interpolation (numpy puro)
# ════════════════════════════════════════════════════════════════════════════
class AnalizadorNHiTS:
    """
    Versión simplificada de N-HiTS (Challu 2023): descomposición multi-escala
    con pooling jerárquico y predicción por interpolación.
    """

    def __init__(self, historico: List[List[int]], escalas: List[int] = None):
        self.hist = historico
        self.escalas = escalas or [1, 3, 7]

    def calcular_scores(self) -> Dict[int, float]:
        try:
            M = _to_count_series(self.hist, ventana=12)
            if M.shape[0] < 30:
                return _scores_uniformes()
            scores = np.zeros(49)
            for n in range(49):
                serie = M[:, n]
                preds = []
                for esc in self.escalas:
                    # Pooling (promedio en ventanas de tamaño esc)
                    L = len(serie)
                    if L < esc * 4:
                        continue
                    n_blocks = L // esc
                    pooled = serie[:n_blocks * esc].reshape(n_blocks, esc).mean(axis=1)
                    if len(pooled) < 4:
                        continue
                    # AR(1) sobre serie pooled
                    x = pooled[:-1]
                    y = pooled[1:]
                    if np.std(x) < 1e-9 or np.std(y) < 1e-9:
                        continue
                    with np.errstate(divide='ignore', invalid='ignore'):
                        corr_mat = np.corrcoef(x, y)
                    rho = float(corr_mat[0, 1])
                    if not np.isfinite(rho):
                        rho = 0.0
                    pred_pool = pooled[-1] * rho + pooled.mean() * (1 - rho)
                    if np.isfinite(pred_pool):
                        preds.append(float(pred_pool))
                # Combinación jerárquica
                if preds:
                    scores[n] = float(np.mean(preds))
                else:
                    scores[n] = float(serie.mean())
            return _normalizar_scores({n + 1: float(scores[n]) for n in range(49)})
        except Exception as e:
            logger.warning(f"N-HiTS fallback: {e}")
            return _scores_uniformes()


# ════════════════════════════════════════════════════════════════════════════
# 101. FITS — Frequency Interpolation Time Series (ICLR 2024)
# ════════════════════════════════════════════════════════════════════════════
class AnalizadorFITS:
    """
    FITS: predicción mediante interpolación en el dominio de frecuencia.
    Aprende una capa lineal compleja en el dominio de la FFT.
    """

    def __init__(self, historico: List[List[int]], cutoff: int = 10):
        self.hist = historico
        self.cutoff = cutoff

    def calcular_scores(self) -> Dict[int, float]:
        try:
            M = _to_count_series(self.hist, ventana=10)
            T = M.shape[0]
            if T < 32:
                return _scores_uniformes()
            scores = np.zeros(49)
            for n in range(49):
                serie = M[:, n]
                F = np.fft.rfft(serie)
                # Mantener solo las frecuencias bajas (filtro pasa-bajos)
                F_filtered = F.copy()
                if len(F) > self.cutoff:
                    F_filtered[self.cutoff:] = 0
                # Extrapolación: replicar señal y predecir un paso más
                serie_recon = np.fft.irfft(F_filtered, n=T)
                # Predicción siguiente
                if len(serie_recon) >= 3:
                    delta = serie_recon[-1] - serie_recon[-2]
                    pred = serie_recon[-1] + delta
                else:
                    pred = serie_recon[-1] if len(serie_recon) > 0 else 0.5
                scores[n] = max(0.0, min(1.0, float(pred)))
            return _normalizar_scores({n + 1: float(scores[n]) for n in range(49)})
        except Exception as e:
            logger.warning(f"FITS fallback: {e}")
            return _scores_uniformes()


# ════════════════════════════════════════════════════════════════════════════
# 102. TimeMixer simplificado (ICLR 2024)
# ════════════════════════════════════════════════════════════════════════════
class AnalizadorTimeMixer:
    """
    Mezcla información multi-escala (past-decomposable-mixing): pool a varias
    escalas y mezcla lineal con pesos aprendidos por reconstrucción.
    """

    def __init__(self, historico: List[List[int]], escalas: List[int] = None):
        self.hist = historico
        self.escalas = escalas or [1, 2, 4, 8]

    def calcular_scores(self) -> Dict[int, float]:
        try:
            M = _to_count_series(self.hist, ventana=10)
            T = M.shape[0]
            if T < 40:
                return _scores_uniformes()
            scores = np.zeros(49)
            for n in range(49):
                serie = M[:, n]
                # Pirámide de escalas
                pyramid = []
                for esc in self.escalas:
                    if T >= esc * 3:
                        n_blocks = T // esc
                        pooled = serie[:n_blocks * esc].reshape(n_blocks, esc).mean(axis=1)
                        pyramid.append(pooled)
                if not pyramid:
                    scores[n] = float(serie.mean())
                    continue
                # Mezcla bottom-up: cada nivel aporta una predicción
                preds = []
                for niv in pyramid:
                    if len(niv) >= 2:
                        preds.append(niv[-1] * 0.7 + niv[-2] * 0.3)
                    else:
                        preds.append(niv[-1])
                # Pesos exponenciales decrecientes (más peso a escala fina)
                pesos = np.array([0.5 ** i for i in range(len(preds))])
                pesos /= pesos.sum()
                pred = sum(p * w for p, w in zip(preds, pesos))
                scores[n] = max(0.0, min(1.0, float(pred)))
            return _normalizar_scores({n + 1: float(scores[n]) for n in range(49)})
        except Exception as e:
            logger.warning(f"TimeMixer fallback: {e}")
            return _scores_uniformes()


# ════════════════════════════════════════════════════════════════════════════
# 103. Modern Hopfield Network (Ramsauer 2020) — Energía exponencial
# ════════════════════════════════════════════════════════════════════════════
class AnalizadorModernHopfield:
    """
    Modern Hopfield Network con capacidad exponencial: cada sorteo histórico
    se almacena como patrón. El estado de consulta recupera el patrón más
    parecido mediante softmax(beta · K^T q).
    """

    def __init__(self, historico: List[List[int]], beta: float = 5.0,
                 ventana: int = 60):
        self.hist = historico
        self.beta = beta
        self.ventana = ventana

    def calcular_scores(self) -> Dict[int, float]:
        try:
            M = _to_freq_matrix(self.hist)
            if M.shape[0] < 10:
                return _scores_uniformes()
            # Patrones almacenados: últimos `ventana` sorteos
            patrones = M[-self.ventana:]
            # Consulta: promedio reciente como prior
            query = M[-5:].mean(axis=0) if M.shape[0] >= 5 else M.mean(axis=0)
            # Energía: softmax(beta · K^T q)
            logits = self.beta * (patrones @ query)
            logits -= logits.max()  # estabilidad
            attn = np.exp(logits) / np.sum(np.exp(logits))
            # Patrón recuperado
            recovered = attn @ patrones
            scores = {n + 1: float(recovered[n]) for n in range(49)}
            return _normalizar_scores(scores)
        except Exception as e:
            logger.warning(f"Modern Hopfield fallback: {e}")
            return _scores_uniformes()


# ════════════════════════════════════════════════════════════════════════════
# 104. Vine Copulas — Dependencias asimétricas multivariantes
# ════════════════════════════════════════════════════════════════════════════
class AnalizadorVineCopulas:
    """
    D-vine copula simplificada con cópulas bivariadas en cadena:
    captura dependencias asimétricas entre pares de números frecuentes.
    """

    def __init__(self, historico: List[List[int]], top_k: int = 10):
        self.hist = historico
        self.top_k = top_k

    def _kendall_tau(self, x: np.ndarray, y: np.ndarray) -> float:
        """Tau de Kendall entre dos series, vectorizado con scipy."""
        if len(x) < 4:
            return 0.0
        try:
            from scipy.stats import kendalltau
            tau, _ = kendalltau(x, y)
            return float(tau) if np.isfinite(tau) else 0.0
        except Exception:
            # Fallback: implementación O(n²) si scipy falla
            n = len(x)
            rx = rankdata(x)
            ry = rankdata(y)
            c = 0
            d = 0
            for i in range(n - 1):
                for j in range(i + 1, n):
                    dx = rx[j] - rx[i]
                    dy = ry[j] - ry[i]
                    if dx * dy > 0:
                        c += 1
                    elif dx * dy < 0:
                        d += 1
            total = c + d
            return (c - d) / max(total, 1)

    def calcular_scores(self) -> Dict[int, float]:
        try:
            M = _to_freq_matrix(self.hist)
            if M.shape[0] < 30:
                return _scores_uniformes()
            # Top-k números más frecuentes
            freqs = M.sum(axis=0)
            top = np.argsort(freqs)[-self.top_k:][::-1]
            top_set = set(int(t) for t in top)   # set para 'in' rápido y correcto
            # Calcular taus de Kendall entre pares consecutivos (D-vine)
            taus = []
            for i in range(len(top) - 1):
                tau = self._kendall_tau(M[:, top[i]], M[:, top[i + 1]])
                taus.append(tau)
            # Score por número: suma de taus con sus vecinos top-k
            scores = np.zeros(49)
            for i, n in enumerate(top):
                vecinos = 0.0
                if i > 0:
                    vecinos += taus[i - 1]
                if i < len(top) - 1:
                    vecinos += taus[i]
                scores[int(n)] = vecinos
            # Para números no-top, score basado en correlación con top medio
            top_avg = M[:, top].mean(axis=1)
            for n in range(49):
                if n not in top_set:
                    if np.std(M[:, n]) > 1e-9 and np.std(top_avg) > 1e-9:
                        with np.errstate(divide='ignore', invalid='ignore'):
                            corr = float(np.corrcoef(M[:, n], top_avg)[0, 1])
                        if np.isfinite(corr):
                            scores[n] = corr * 0.5
            return _normalizar_scores({n + 1: float(scores[n]) for n in range(49)})
        except Exception as e:
            logger.warning(f"Vine Copulas fallback: {e}")
            return _scores_uniformes()


# ════════════════════════════════════════════════════════════════════════════
# 105. MiniRocket — Random Convolutional Kernels (Dempster 2021)
# ════════════════════════════════════════════════════════════════════════════
class AnalizadorMiniRocket:
    """
    Convoluciones aleatorias predefinidas + PPV (proportion of positive values)
    como feature. Muy rápido, sin gradientes, alta precisión en TSC.
    """

    def __init__(self, historico: List[List[int]], n_kernels: int = 84):
        self.hist = historico
        self.n_kernels = n_kernels

    def _generate_kernels(self) -> List[np.ndarray]:
        """Genera kernels de tamaño 9 con valores {-1, 2}."""
        rng = np.random.RandomState(42)
        kernels = []
        for _ in range(self.n_kernels):
            k = rng.choice([-1, 2], size=9, p=[6/9, 3/9])
            kernels.append(k.astype(np.float32))
        return kernels

    def _ppv(self, x: np.ndarray) -> float:
        """Proportion of Positive Values."""
        return float(np.mean(x > 0))

    def calcular_scores(self) -> Dict[int, float]:
        try:
            M = _to_count_series(self.hist, ventana=8)
            if M.shape[0] < 20:
                return _scores_uniformes()
            kernels = self._generate_kernels()
            scores = np.zeros(49)
            for n in range(49):
                serie = M[:, n] - M[:, n].mean()
                feats = []
                for k in kernels:
                    if len(serie) >= len(k):
                        conv = np.convolve(serie, k, mode='valid')
                        feats.append(self._ppv(conv))
                if feats:
                    # Score = media de PPVs (más alto = más activo)
                    scores[n] = float(np.mean(feats))
            return _normalizar_scores({n + 1: float(scores[n]) for n in range(49)})
        except Exception as e:
            logger.warning(f"MiniRocket fallback: {e}")
            return _scores_uniformes()


# ════════════════════════════════════════════════════════════════════════════
# 106. Visibility Graph — Lacasa 2008
# ════════════════════════════════════════════════════════════════════════════
class AnalizadorVisibilityGraph:
    """
    Construye un grafo de visibilidad: dos puntos del tiempo están conectados
    si pueden 'verse' por encima de los demás. Centralidad = importancia.
    """

    def __init__(self, historico: List[List[int]]):
        self.hist = historico

    def _grado_visibilidad(self, x: np.ndarray) -> np.ndarray:
        """Calcula el grado de cada nodo en el grafo de visibilidad."""
        n = len(x)
        if n < 3:
            return np.zeros(n)
        grado = np.zeros(n)
        for i in range(n - 1):
            for j in range(i + 1, n):
                if j == i + 1:
                    grado[i] += 1
                    grado[j] += 1
                    continue
                # Comprobar visibilidad
                slope = (x[j] - x[i]) / (j - i)
                visible = True
                for k in range(i + 1, j):
                    altura = x[i] + slope * (k - i)
                    if x[k] >= altura:
                        visible = False
                        break
                if visible:
                    grado[i] += 1
                    grado[j] += 1
        return grado

    def calcular_scores(self) -> Dict[int, float]:
        try:
            M = _to_count_series(self.hist, ventana=10)
            T = M.shape[0]
            if T < 15:
                return _scores_uniformes()
            scores = np.zeros(49)
            # Para no explotar el cálculo, sólo últimas 30 muestras
            L = min(T, 30)
            for n in range(49):
                serie = M[-L:, n]
                grados = self._grado_visibilidad(serie)
                if len(grados) > 0:
                    # Score = grado del último nodo (importancia actual)
                    scores[n] = float(grados[-1])
            return _normalizar_scores({n + 1: float(scores[n]) for n in range(49)})
        except Exception as e:
            logger.warning(f"Visibility Graph fallback: {e}")
            return _scores_uniformes()


# ════════════════════════════════════════════════════════════════════════════
# 107. Association Rule Mining — Apriori interno simplificado
# ════════════════════════════════════════════════════════════════════════════
class AnalizadorAssociationRules:
    """
    Minería de reglas de asociación frecuentes (X => Y) sobre los sorteos.
    Identifica números cuya presencia eleva la probabilidad de otros.
    """

    def __init__(self, historico: List[List[int]], min_support: float = 0.04,
                 min_confidence: float = 0.15):
        self.hist = historico
        self.min_support = min_support
        self.min_confidence = min_confidence

    def calcular_scores(self) -> Dict[int, float]:
        try:
            n_sorteos = len(self.hist)
            if n_sorteos < 30:
                return _scores_uniformes()
            # Soporte de números individuales
            soporte = np.zeros(49)
            for s in self.hist:
                for x in s:
                    if 1 <= x <= 49:
                        soporte[x - 1] += 1
            soporte /= n_sorteos
            frec = np.where(soporte >= self.min_support)[0]
            if len(frec) == 0:
                return _scores_uniformes()
            # Soporte de pares
            sop_pares = np.zeros((49, 49))
            for s in self.hist:
                for a, b in combinations(sorted(s), 2):
                    if 1 <= a <= 49 and 1 <= b <= 49:
                        sop_pares[a - 1, b - 1] += 1
                        sop_pares[b - 1, a - 1] += 1
            sop_pares /= n_sorteos
            # Reglas: confianza(a => b) = sop(a,b) / sop(a)
            scores = np.zeros(49)
            for a in frec:
                for b in frec:
                    if a == b:
                        continue
                    if soporte[a] > 0:
                        conf = sop_pares[a, b] / soporte[a]
                        if conf >= self.min_confidence:
                            # Lift: confianza / sop(b)
                            lift = conf / soporte[b] if soporte[b] > 0 else 0
                            scores[b] += lift * conf
            return _normalizar_scores({n + 1: float(scores[n]) for n in range(49)})
        except Exception as e:
            logger.warning(f"Association Rules fallback: {e}")
            return _scores_uniformes()


# ════════════════════════════════════════════════════════════════════════════
# 108. RBM — Restricted Boltzmann Machine (sklearn-compatible interno)
# ════════════════════════════════════════════════════════════════════════════
class AnalizadorRBM:
    """
    RBM bipartito (visible-hidden) entrenado con Contrastive Divergence k=1.
    Aprende distribución de probabilidad latente sobre sorteos.
    """

    def __init__(self, historico: List[List[int]], n_hidden: int = 24,
                 lr: float = 0.05, n_iter: int = 25):
        self.hist = historico
        self.n_hidden = n_hidden
        self.lr = lr
        self.n_iter = n_iter

    def _sigmoid(self, x: np.ndarray) -> np.ndarray:
        x = np.clip(x, -30, 30)
        return 1.0 / (1.0 + np.exp(-x))

    def calcular_scores(self) -> Dict[int, float]:
        try:
            V = _to_freq_matrix(self.hist)
            T, n_vis = V.shape
            if T < 25:
                return _scores_uniformes()
            rng = np.random.RandomState(7)
            W = rng.normal(0, 0.05, size=(n_vis, self.n_hidden))
            b_v = np.zeros(n_vis)
            b_h = np.zeros(self.n_hidden)
            # CD-1
            for it in range(self.n_iter):
                # Positive phase
                p_h = self._sigmoid(V @ W + b_h)
                h_sample = (p_h > rng.random(p_h.shape)).astype(np.float32)
                pos_grad = V.T @ p_h
                # Negative phase
                p_v_neg = self._sigmoid(h_sample @ W.T + b_v)
                p_h_neg = self._sigmoid(p_v_neg @ W + b_h)
                neg_grad = p_v_neg.T @ p_h_neg
                # Actualizar
                W += self.lr * (pos_grad - neg_grad) / T
                b_v += self.lr * (V - p_v_neg).mean(axis=0)
                b_h += self.lr * (p_h - p_h_neg).mean(axis=0)
            # Generar muestra a partir del estado reciente
            v_query = V[-5:].mean(axis=0)
            p_h = self._sigmoid(v_query @ W + b_h)
            v_pred = self._sigmoid(p_h @ W.T + b_v)
            return _normalizar_scores({n + 1: float(v_pred[n]) for n in range(49)})
        except Exception as e:
            logger.warning(f"RBM fallback: {e}")
            return _scores_uniformes()


# ════════════════════════════════════════════════════════════════════════════
# 109. SOM — Self-Organizing Map (Kohonen)
# ════════════════════════════════════════════════════════════════════════════
class AnalizadorSOM:
    """
    Mapa de Kohonen 2D 8x8: aprendizaje competitivo sin backprop.
    Cada sorteo se mapea a una neurona ganadora (BMU).
    """

    def __init__(self, historico: List[List[int]], grid: int = 8,
                 sigma0: float = 3.0, lr0: float = 0.5, n_iter: int = 1500):
        self.hist = historico
        self.grid = grid
        self.sigma0 = sigma0
        self.lr0 = lr0
        self.n_iter = n_iter

    def calcular_scores(self) -> Dict[int, float]:
        try:
            V = _to_freq_matrix(self.hist)
            T, n_vis = V.shape
            if T < 25:
                return _scores_uniformes()
            G = self.grid
            rng = np.random.RandomState(11)
            # Inicialización aleatoria de pesos de neuronas
            W = rng.uniform(0, 0.3, size=(G, G, n_vis))
            # Coordenadas de neuronas en el plano
            coords = np.array([[i, j] for i in range(G) for j in range(G)]).reshape(G, G, 2)
            for it in range(self.n_iter):
                idx = rng.randint(T)
                x = V[idx]
                # Distancia a todas las neuronas
                d = np.linalg.norm(W - x, axis=2)
                bmu = np.unravel_index(np.argmin(d), d.shape)
                # Tasas decrecientes
                decay = np.exp(-it / self.n_iter)
                sigma_t = self.sigma0 * decay
                lr_t = self.lr0 * decay
                # Vecindad gaussiana
                bmu_coord = np.array(bmu)
                dist2 = np.sum((coords - bmu_coord) ** 2, axis=2)
                influence = np.exp(-dist2 / (2 * sigma_t ** 2 + 1e-9))
                # Actualizar pesos
                W += lr_t * influence[..., None] * (x - W)
            # Score por número: media de pesos en la BMU del último sorteo
            x_last = V[-5:].mean(axis=0) if T >= 5 else V.mean(axis=0)
            d = np.linalg.norm(W - x_last, axis=2)
            bmu = np.unravel_index(np.argmin(d), d.shape)
            # Score = pesos de la BMU y sus 4 vecinos
            i0, j0 = bmu
            preds = []
            for di in [-1, 0, 1]:
                for dj in [-1, 0, 1]:
                    ni, nj = i0 + di, j0 + dj
                    if 0 <= ni < G and 0 <= nj < G:
                        preds.append(W[ni, nj])
            score_arr = np.mean(preds, axis=0)
            return _normalizar_scores({n + 1: float(score_arr[n]) for n in range(49)})
        except Exception as e:
            logger.warning(f"SOM fallback: {e}")
            return _scores_uniformes()


# ════════════════════════════════════════════════════════════════════════════
# 110. HDC/VSA — Hyperdimensional Computing (Vector Symbolic Architecture)
# ════════════════════════════════════════════════════════════════════════════
class AnalizadorHDC:
    """
    Hyperdimensional Computing: cada número se representa como hipervector
    aleatorio bipolar {-1,+1} de dimensión D=10000. Sorteos se componen
    mediante bundling (suma). Memoria asociativa por similitud coseno.
    """

    def __init__(self, historico: List[List[int]], D: int = 10000):
        self.hist = historico
        self.D = D

    def _bundle(self, hvs: List[np.ndarray]) -> np.ndarray:
        """Bundling: suma y signo."""
        s = np.sum(hvs, axis=0)
        return np.sign(s).astype(np.int8)

    def calcular_scores(self) -> Dict[int, float]:
        try:
            n_sorteos = len(self.hist)
            if n_sorteos < 15:
                return _scores_uniformes()
            rng = np.random.RandomState(13)
            # Hipervectores por número (49), float32 para evitar overflow int8
            HV = rng.choice([-1.0, 1.0], size=(50, self.D)).astype(np.float32)
            # Hipervectores de posición temporal
            HV_pos = rng.choice([-1.0, 1.0], size=(n_sorteos + 1, self.D)).astype(np.float32)
            # Bundle del histórico ponderado por recencia
            memoria = np.zeros(self.D, dtype=np.float32)
            for t, sorteo in enumerate(self.hist):
                if not sorteo:
                    continue
                peso = float(np.exp(-(n_sorteos - t - 1) / 30))
                sorteo_hv = np.zeros(self.D, dtype=np.float32)
                for n in sorteo:
                    if 1 <= n <= 49:
                        # Binding: número * posición (producto element-wise)
                        sorteo_hv += HV[n] * HV_pos[t]
                # Bundling: normalizar a hipervector bipolar antes de acumular
                sig = np.sign(sorteo_hv)
                memoria += peso * sig
            # Normalizar memoria final
            memoria_sig = np.sign(memoria)
            memoria_sig[memoria_sig == 0] = 1.0  # tie-break
            # Query: usar el hipervector de la posición "siguiente" (t = n_sorteos)
            # para hacer unbinding y recuperar lo que más se asemeja
            query_pos = HV_pos[n_sorteos]
            query = memoria_sig * query_pos
            # Similitud coseno con cada número
            scores = np.zeros(49)
            for n in range(1, 50):
                sim = float(np.dot(query, HV[n])) / self.D
                scores[n - 1] = max(0.0, sim)
            return _normalizar_scores({n + 1: float(scores[n]) for n in range(49)})
        except Exception as e:
            logger.warning(f"HDC fallback: {e}")
            return _scores_uniformes()


# ════════════════════════════════════════════════════════════════════════════
#  EXPORTAR TODOS LOS ANALIZADORES DEL BLOQUE K
# ════════════════════════════════════════════════════════════════════════════
__all__ = [
    # Bloque K original
    "AnalizadorNGRC",            # 94
    "AnalizadorDMDKoopman",      # 95
    "AnalizadorKAN",             # 96
    "AnalizadorDLinear",         # 97
    "AnalizadorSINDy",           # 98
    "AnalizadorTSFresh",         # 99
    "AnalizadorNHiTS",           # 100
    "AnalizadorFITS",            # 101
    "AnalizadorTimeMixer",       # 102
    # Bloque K extendido ronda 1
    "AnalizadorModernHopfield",  # 103
    "AnalizadorVineCopulas",     # 104
    "AnalizadorMiniRocket",      # 105
    "AnalizadorVisibilityGraph", # 106
    "AnalizadorAssociationRules",# 107
    # Bloque K extendido ronda 3 (redes neuronales)
    "AnalizadorRBM",             # 108
    "AnalizadorSOM",             # 109
    "AnalizadorHDC",             # 110
]
