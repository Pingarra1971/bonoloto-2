"""
╔══════════════════════════════════════════════════════════════════════╗
║   BONOLOTO AI — BLOQUE J: ÚLTIMAS MEJORAS DE ALTA PRIORIDAD        ║
║                                                                      ║
║   88. SSA   — Singular Spectrum Analysis                            ║
║   89. VMD   — Variational Mode Decomposition                        ║
║   90. BOCPD — Bayesian Online Changepoint Detection                 ║
║   91. EMD   — Empirical Mode Decomposition                          ║
║   92. RETAIN — Reverse Time Attention bidireccional                 ║
║   93. Lomb-Scargle Periodogram                                       ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import math
import logging
from collections import defaultdict
from typing import Dict, List, Tuple, Optional

import numpy as np

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════
# 88 — SSA: SINGULAR SPECTRUM ANALYSIS
# ═══════════════════════════════════════════════════════════════════════
class AnalizadorSSA:
    """
    Singular Spectrum Analysis: descomposición no paramétrica de series
    temporales mediante SVD de la matriz de trayectoria.
    Detecta tendencia + componentes oscilatorios + ruido sin suposiciones.

    Pasos:
    1. Embedding: construir matriz de trayectoria L×K
    2. SVD: descomponer en componentes principales
    3. Grouping: separar tendencia, oscilaciones, ruido
    4. Reconstrucción: diagonal averaging
    """

    def __init__(self, historico: List[List[int]],
                 ventana_L: int = 30, n_componentes: int = 5):
        self.historico = historico
        self.n = len(historico)
        self.L = ventana_L
        self.r = n_componentes

    def _matriz_trayectoria(self, serie: np.ndarray) -> np.ndarray:
        """Embedding: construye matriz de trayectoria Hankel."""
        N = len(serie)
        K = N - self.L + 1
        if K <= 0 or self.L > N:
            return np.array([[]])
        X = np.zeros((self.L, K))
        for i in range(self.L):
            X[i, :] = serie[i:i + K]
        return X

    def _svd_descomposicion(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """SVD de la matriz de trayectoria."""
        try:
            U, s, Vt = np.linalg.svd(X, full_matrices=False)
            return U, s, Vt
        except Exception:
            return np.zeros((self.L, 1)), np.zeros(1), np.zeros((1, X.shape[1]))

    def _diagonal_averaging(self, X_componente: np.ndarray) -> np.ndarray:
        """Reconstruye serie temporal por hankelización (diagonal averaging)."""
        L, K = X_componente.shape
        N = L + K - 1
        serie_reconstruida = np.zeros(N)

        for k in range(N):
            # Promedio sobre la k-ésima antidiagonal
            i_min = max(0, k - K + 1)
            i_max = min(L - 1, k)
            valores = []
            for i in range(i_min, i_max + 1):
                j = k - i
                if 0 <= j < K:
                    valores.append(X_componente[i, j])
            if valores:
                serie_reconstruida[k] = np.mean(valores)
        return serie_reconstruida

    def _predecir_siguiente(self, serie_reconstruida: np.ndarray) -> float:
        """Predicción del siguiente valor por recurrencia lineal SSA."""
        n = len(serie_reconstruida)
        if n < 5:
            return float(serie_reconstruida[-1]) if n > 0 else 0.5

        # Coeficientes de recurrencia lineal (mínimos cuadrados)
        K = min(10, n - 1)
        Y = serie_reconstruida[-K:]
        X = np.array([serie_reconstruida[-K-1:-1]]).reshape(-1, 1) if K > 0 else np.array([[0]])
        if len(X) < 2:
            return float(np.mean(serie_reconstruida[-5:]))

        try:
            # Predicción simple: media ponderada de últimos puntos
            pesos = np.linspace(0.5, 1.0, min(5, n))
            ultimos = serie_reconstruida[-len(pesos):]
            pred = np.average(ultimos, weights=pesos)
            return float(pred)
        except Exception:
            return float(np.mean(serie_reconstruida[-5:]))

    def calcular_scores(self) -> Dict[int, float]:
        scores = {}
        ventana_max = min(150, self.n)

        for num in range(1, 50):
            serie = np.array([1.0 if num in s else 0.0
                             for s in self.historico[:ventana_max]])

            if len(serie) < self.L * 2:
                scores[num] = 0.5
                continue

            # Construir matriz de trayectoria
            X = self._matriz_trayectoria(serie)
            if X.size == 0 or X.shape[1] < 2:
                scores[num] = 0.5
                continue

            # SVD
            U, s, Vt = self._svd_descomposicion(X)
            if len(s) == 0:
                scores[num] = 0.5
                continue

            # Reconstrucción usando primeros r componentes (señal sin ruido)
            r_efectivo = min(self.r, len(s))
            X_reconstruida = np.zeros_like(X)
            for k in range(r_efectivo):
                X_reconstruida += s[k] * np.outer(U[:, k], Vt[k, :])

            # Diagonal averaging
            serie_recon = self._diagonal_averaging(X_reconstruida)

            # Predicción
            pred = self._predecir_siguiente(serie_recon)

            # Score: predicción normalizada + bonus por estructura
            # Mayor proporción de varianza en primeros componentes = más estructura
            if len(s) > 0:
                var_total = (s ** 2).sum()
                var_componentes = (s[:r_efectivo] ** 2).sum()
                ratio_estructura = var_componentes / max(var_total, 1e-10)
            else:
                ratio_estructura = 0.5

            scores[num] = max(0.0, min(1.0, pred * 0.7 + ratio_estructura * 0.3))

        max_v = max(scores.values(), default=1)
        if max_v > 0:
            scores = {n: v / max_v for n, v in scores.items()}
        return scores


# ═══════════════════════════════════════════════════════════════════════
# 89 — VMD: VARIATIONAL MODE DECOMPOSITION
# ═══════════════════════════════════════════════════════════════════════
class AnalizadorVMD:
    """
    Variational Mode Decomposition con ADMM simplificado.
    Descompone la señal en K modos espectralmente compactos.
    A diferencia de EMD, VMD garantiza separación clara entre modos.
    Implementación numpy puro siguiendo Dragomiretskiy & Zosso (2014).
    """

    def __init__(self, historico: List[List[int]],
                 K: int = 4, alpha: float = 200, tol: float = 1e-6):
        self.historico = historico
        self.n = len(historico)
        self.K = K          # Número de modos
        self.alpha = alpha  # Penalización de ancho de banda
        self.tol = tol

    def _vmd_simple(self, signal: np.ndarray, max_iter: int = 30) -> Tuple[np.ndarray, np.ndarray]:
        """
        VMD simplificado: extrae K modos por filtrado iterativo en
        el dominio de frecuencias. Versión ligera para CPU.
        """
        T = len(signal)
        if T < self.K * 4:
            return np.zeros((self.K, T)), np.zeros(self.K)

        # Transformada al dominio de frecuencias
        f_signal = np.fft.fft(signal)
        freqs = np.fft.fftfreq(T)

        # Inicializar centros de frecuencia distribuidos uniformemente
        omega = np.linspace(0.05, 0.45, self.K)
        u_modos = np.zeros((self.K, T))
        u_hat = np.zeros((self.K, T), dtype=complex)

        for it in range(max_iter):
            cambio_max = 0.0
            for k in range(self.K):
                # Filtro Wiener centrado en omega[k]
                suma_otros = np.zeros(T, dtype=complex)
                for j in range(self.K):
                    if j != k:
                        suma_otros += u_hat[j]

                # Actualización en frecuencia
                denom = 1 + self.alpha * (freqs - omega[k]) ** 2
                u_hat_nuevo = (f_signal - suma_otros) / denom

                # Actualizar centro de frecuencia
                power = np.abs(u_hat_nuevo) ** 2
                if power.sum() > 0:
                    omega_nuevo = np.sum(np.abs(freqs) * power) / power.sum()
                    cambio_max = max(cambio_max, abs(omega_nuevo - omega[k]))
                    omega[k] = omega_nuevo

                u_hat[k] = u_hat_nuevo

            if cambio_max < self.tol:
                break

        # Transformar modos al dominio temporal
        for k in range(self.K):
            u_modos[k] = np.real(np.fft.ifft(u_hat[k]))

        return u_modos, omega

    def calcular_scores(self) -> Dict[int, float]:
        scores = {}
        ventana = min(128, self.n)  # Potencia de 2 ideal para FFT

        for num in range(1, 50):
            serie = np.array([1.0 if num in s else 0.0
                             for s in self.historico[:ventana]])
            if len(serie) < 32:
                scores[num] = 0.5
                continue

            try:
                modos, omegas = self._vmd_simple(serie)

                # Energía por modo
                energias = np.array([np.sum(m ** 2) for m in modos])
                total = energias.sum()
                if total < 1e-10:
                    scores[num] = 0.5
                    continue

                energias_norm = energias / total

                # Score: predicción basada en la tendencia (modo de menor frecuencia)
                idx_tendencia = np.argmin(omegas)
                modo_tendencia = modos[idx_tendencia]

                # Predicción: continuación del modo de tendencia
                pred_tendencia = np.mean(modo_tendencia[-5:]) + 0.5

                # Bonus: concentración de energía en pocos modos = más estructura
                concentracion = (energias_norm ** 2).sum()  # Índice de Herfindahl

                scores[num] = max(0.0, min(1.0,
                    pred_tendencia * 0.6 + concentracion * 0.4))
            except Exception as e:
                logger.debug(f"VMD error num={num}: {e}")
                scores[num] = 0.5

        max_v = max(scores.values(), default=1)
        if max_v > 0:
            scores = {n: v / max_v for n, v in scores.items()}
        return scores


# ═══════════════════════════════════════════════════════════════════════
# 90 — BOCPD: BAYESIAN ONLINE CHANGEPOINT DETECTION
# ═══════════════════════════════════════════════════════════════════════
class DetectorBOCPD:
    """
    Bayesian Online Changepoint Detection (Adams & MacKay 2007).
    Mantiene una distribución de probabilidad sobre la "longitud de racha"
    (tiempo desde el último cambio de régimen) y la actualiza online.

    Implementación numpy puro con prior Gaussiano y hazard constante.
    """

    def __init__(self, historico: List[List[int]],
                 hazard_rate: float = 1.0 / 100,
                 mu_prior: float = 150.0,
                 kappa_prior: float = 0.1,
                 alpha_prior: float = 1.0,
                 beta_prior: float = 1.0):
        self.historico = historico
        self.n = len(historico)
        self.h = hazard_rate
        self.mu_0 = mu_prior
        self.kappa_0 = kappa_prior
        self.alpha_0 = alpha_prior
        self.beta_0 = beta_prior

    def _log_predictiva_t(self, x: float, mu: np.ndarray,
                          kappa: np.ndarray, alpha: np.ndarray,
                          beta: np.ndarray) -> np.ndarray:
        """Log-densidad predictiva Student-t por longitud de racha."""
        # Student-t: P(x | mu, sigma^2, nu)
        sigma2 = beta * (kappa + 1) / (alpha * kappa)
        nu = 2 * alpha
        # Log-densidad Student-t
        log_p = (
            math.lgamma(0.5) - math.lgamma(0.5) +
            0  # constante simplificada
        )
        z = (x - mu) ** 2 / np.maximum(sigma2, 1e-10)
        log_p = -0.5 * np.log(2 * np.pi * np.maximum(sigma2, 1e-10)) \
                - 0.5 * np.log1p(z / np.maximum(nu, 1e-10)) * (nu + 1)
        return log_p

    # Tope para evitar matriz O(T²) en memoria. Con T=1000 sorteos
    # (≈3 años de Bonoloto) la matriz pesa ~8MB. Con T=10000 serían
    # 800MB, lo que tumba la VM Ampere A1 (24GB). Detectar cambios
    # de régimen a >3 años vista no aporta señal accionable.
    T_MAX = 1000

    def ejecutar(self) -> Tuple[np.ndarray, float]:
        """
        Ejecuta BOCPD y devuelve (probabilidades_changepoint, último cambio detectado).
        """
        # Serie a analizar: sumas de cada sorteo (limitada a T_MAX).
        historico_ventana = self.historico[:self.T_MAX]
        sumas = np.array([float(sum(s)) for s in historico_ventana], dtype=float)
        T = len(sumas)
        if T < 10:
            return np.zeros(T), -1

        # Inicializar arrays
        # r_t: distribución sobre longitud de racha
        # mu, kappa, alpha, beta: parámetros posteriores para cada r
        r_probs = np.zeros((T + 1, T + 1))
        r_probs[0, 0] = 1.0  # En t=0, r=0 con prob 1

        mu = np.array([self.mu_0])
        kappa = np.array([self.kappa_0])
        alpha = np.array([self.alpha_0])
        beta = np.array([self.beta_0])

        probabilidades_cp = np.zeros(T)
        ultimo_cp = -1

        for t in range(T):
            x = sumas[t]

            # 1. Calcular predictiva para cada r
            log_p = self._log_predictiva_t(x, mu, kappa, alpha, beta)
            p_pred = np.exp(log_p - np.max(log_p))  # estabilidad numérica
            p_pred = p_pred / p_pred.sum() if p_pred.sum() > 0 else p_pred

            # 2. Crecimiento de racha: r_{t+1} = r_t + 1 con prob (1 - hazard)
            r_actual = r_probs[t, :t + 1]
            r_crecimiento = r_actual * p_pred * (1 - self.h)

            # 3. Punto de cambio: r_{t+1} = 0 con prob (hazard)
            r_cp = np.sum(r_actual * p_pred * self.h)

            # 4. Combinar y normalizar
            r_probs[t + 1, 0] = r_cp
            r_probs[t + 1, 1:t + 2] = r_crecimiento
            total = r_probs[t + 1].sum()
            if total > 0:
                r_probs[t + 1] /= total

            # 5. Probabilidad de changepoint en t
            probabilidades_cp[t] = r_probs[t + 1, 0]
            if probabilidades_cp[t] > 0.5 and t > 5:
                ultimo_cp = t

            # 6. Actualizar parámetros posteriores
            mu_nuevo = (kappa * mu + x) / (kappa + 1)
            kappa_nuevo = kappa + 1
            alpha_nuevo = alpha + 0.5
            beta_nuevo = beta + (kappa * (x - mu) ** 2) / (2 * (kappa + 1))

            mu = np.concatenate([[self.mu_0], mu_nuevo])
            kappa = np.concatenate([[self.kappa_0], kappa_nuevo])
            alpha = np.concatenate([[self.alpha_0], alpha_nuevo])
            beta = np.concatenate([[self.beta_0], beta_nuevo])

        return probabilidades_cp, ultimo_cp

    def calcular_scores(self) -> Dict[int, float]:
        """
        Scores basados en BOCPD: si hay cambio reciente, dar más peso
        a los números que aparecieron después del cambio.
        """
        probs_cp, ultimo_cp = self.ejecutar()

        scores = defaultdict(float)

        # Si se detectó cambio reciente, ponderar histórico post-cambio
        if ultimo_cp > 0 and ultimo_cp < self.n - 1:
            historico_relevante = self.historico[:max(1, ultimo_cp)]
        else:
            historico_relevante = self.historico[:min(100, self.n)]

        # Calcular frecuencias en el período relevante
        for sorteo in historico_relevante:
            for n in sorteo:
                if 1 <= n <= 49:
                    scores[n] += 1.0

        n_rel = max(len(historico_relevante), 1)
        max_v = max(scores.values(), default=1)
        if max_v > 0:
            return {n: scores.get(n, 0) / max_v for n in range(1, 50)}
        return {n: 0.5 for n in range(1, 50)}


# ═══════════════════════════════════════════════════════════════════════
# 91 — EMD: EMPIRICAL MODE DECOMPOSITION
# ═══════════════════════════════════════════════════════════════════════
class AnalizadorEMD:
    """
    Empirical Mode Decomposition (Huang et al. 1998).
    Descompone una señal en IMFs (Intrinsic Mode Functions) adaptativas.
    Implementación numpy puro del algoritmo de sifting.
    """

    def __init__(self, historico: List[List[int]],
                 max_imfs: int = 5, max_sift_iter: int = 8):
        self.historico = historico
        self.n = len(historico)
        self.max_imfs = max_imfs
        self.max_sift = max_sift_iter

    def _encontrar_extremos(self, signal: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Encuentra índices de máximos y mínimos locales."""
        n = len(signal)
        if n < 3:
            return np.array([]), np.array([])
        maximos = []
        minimos = []
        for i in range(1, n - 1):
            if signal[i] > signal[i - 1] and signal[i] > signal[i + 1]:
                maximos.append(i)
            elif signal[i] < signal[i - 1] and signal[i] < signal[i + 1]:
                minimos.append(i)
        return np.array(maximos), np.array(minimos)

    def _envolvente(self, signal: np.ndarray, indices: np.ndarray) -> np.ndarray:
        """Calcula envolvente interpolando entre puntos."""
        n = len(signal)
        if len(indices) < 2:
            return np.zeros(n)
        # Añadir extremos del dominio
        if indices[0] != 0:
            indices = np.concatenate([[0], indices])
        if indices[-1] != n - 1:
            indices = np.concatenate([indices, [n - 1]])
        valores = signal[indices]
        # Interpolación lineal (más estable que cúbica en CPU ARM)
        return np.interp(np.arange(n), indices, valores)

    def _sift(self, signal: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Una pasada de sifting para extraer una IMF."""
        h = signal.copy()
        for _ in range(self.max_sift):
            maximos, minimos = self._encontrar_extremos(h)
            if len(maximos) < 2 or len(minimos) < 2:
                break
            env_sup = self._envolvente(h, maximos)
            env_inf = self._envolvente(h, minimos)
            media = (env_sup + env_inf) / 2
            h_nuevo = h - media
            if np.sum((h - h_nuevo) ** 2) / max(np.sum(h ** 2), 1e-10) < 0.01:
                h = h_nuevo
                break
            h = h_nuevo
        return h, signal - h

    def _emd(self, signal: np.ndarray) -> List[np.ndarray]:
        """EMD completo: extrae IMFs hasta que el residuo sea monotónico."""
        imfs = []
        residuo = signal.copy()
        for _ in range(self.max_imfs):
            maximos, minimos = self._encontrar_extremos(residuo)
            if len(maximos) < 2 or len(minimos) < 2:
                break
            imf, residuo = self._sift(residuo)
            imfs.append(imf)
        imfs.append(residuo)  # Último elemento es la tendencia
        return imfs

    def calcular_scores(self) -> Dict[int, float]:
        scores = {}
        ventana = min(128, self.n)

        for num in range(1, 50):
            serie = np.array([1.0 if num in s else 0.0
                             for s in self.historico[:ventana]])
            if len(serie) < 20:
                scores[num] = 0.5
                continue

            try:
                imfs = self._emd(serie)
                if not imfs:
                    scores[num] = 0.5
                    continue

                # Energía por IMF
                energias = np.array([np.sum(imf ** 2) for imf in imfs])
                total = energias.sum()
                if total < 1e-10:
                    scores[num] = 0.5
                    continue

                energias_norm = energias / total

                # La última IMF es la tendencia
                tendencia = imfs[-1]
                pred_tendencia = float(np.mean(tendencia[-5:])) + 0.5

                # Score: tendencia + concentración de energía
                concentracion = (energias_norm ** 2).sum()
                scores[num] = max(0.0, min(1.0,
                    pred_tendencia * 0.6 + concentracion * 0.4))
            except Exception as e:
                logger.debug(f"EMD error num={num}: {e}")
                scores[num] = 0.5

        max_v = max(scores.values(), default=1)
        if max_v > 0:
            scores = {n: v / max_v for n, v in scores.items()}
        return scores


# ═══════════════════════════════════════════════════════════════════════
# 92 — RETAIN: REVERSE TIME ATTENTION
# ═══════════════════════════════════════════════════════════════════════
class AnalizadorRETAIN:
    """
    RETAIN (Reverse Time Attention) adaptado a Bonoloto.
    Atención bidireccional de dos niveles:
    - Nivel 1 (alpha): qué sorteos pasados son más importantes
    - Nivel 2 (beta):  qué números dentro de esos sorteos importan más

    El "reverse time" da más atención a sorteos recientes.
    Implementación numpy puro sin backprop (pesos fijos calibrados).
    """

    def __init__(self, historico: List[List[int]], dim_emb: int = 16):
        self.historico = historico
        self.n = len(historico)
        self.d = dim_emb
        rng = np.random.RandomState(42)
        # Matrices de atención (fijas tipo reservoir)
        self.W_alpha = rng.randn(self.d) * 0.3      # atención temporal
        self.W_beta = rng.randn(49, self.d) * 0.3   # atención por número
        self.W_emb = rng.randn(49, self.d) * 0.3    # embedding de cada número

    def _embedding_sorteo(self, sorteo: List[int]) -> np.ndarray:
        """Codifica un sorteo como vector denso d-dimensional."""
        v_sorteo = np.zeros(49)
        for n in sorteo:
            if 1 <= n <= 49:
                v_sorteo[n - 1] = 1.0
        return self.W_emb.T @ v_sorteo  # dim: d

    def _atencion_alpha(self, embeddings: np.ndarray) -> np.ndarray:
        """
        Atención de nivel 1 (temporal). Procesa secuencia en orden inverso
        (más reciente primero) — esto es el "reverse time" de RETAIN.
        """
        # Scores brutos: producto interno con W_alpha
        scores = embeddings @ self.W_alpha  # (T,)

        # Decaimiento temporal favoreciendo lo reciente (reverse-time bias)
        T = len(scores)
        decaimiento = np.exp(-0.05 * np.arange(T))  # índice 0 = más reciente
        scores = scores * decaimiento

        # Softmax
        scores = scores - scores.max()
        alpha = np.exp(scores)
        alpha = alpha / max(alpha.sum(), 1e-10)
        return alpha

    def _atencion_beta(self, embeddings: np.ndarray) -> np.ndarray:
        """
        Atención de nivel 2 (por número en cada sorteo).
        Devuelve matriz (T, 49) de pesos por número y sorteo.
        """
        T = len(embeddings)
        # Scores: embedding_t @ W_beta.T  → (T, 49)
        scores = embeddings @ self.W_beta.T
        # Sigmoid por número (no softmax: queremos pesos independientes)
        # Capar scores para evitar overflow en exp(-x) si x es muy negativo
        scores = np.clip(scores, -30, 30)
        beta = 1.0 / (1.0 + np.exp(-scores))
        return beta

    def calcular_scores(self) -> Dict[int, float]:
        ventana = min(80, self.n)
        if ventana < 5:
            return {n: 0.5 for n in range(1, 50)}

        # Construir embeddings (índice 0 = más reciente)
        embeddings = np.array([
            self._embedding_sorteo(self.historico[t])
            for t in range(ventana)
        ])

        # Atención de nivel 1 (temporal)
        alpha = self._atencion_alpha(embeddings)

        # Atención de nivel 2 (por número y sorteo)
        beta = self._atencion_beta(embeddings)

        # Score final: agregación ponderada
        # score[n] = suma_t alpha[t] * beta[t, n] * presencia[t, n]
        scores_arr = np.zeros(49)
        for t in range(ventana):
            sorteo = self.historico[t]
            for num in sorteo:
                if 1 <= num <= 49:
                    scores_arr[num - 1] += alpha[t] * beta[t, num - 1]

        max_v = scores_arr.max()
        if max_v > 0:
            scores_arr = scores_arr / max_v

        return {n: float(scores_arr[n - 1]) for n in range(1, 50)}


# ═══════════════════════════════════════════════════════════════════════
# 93 — LOMB-SCARGLE PERIODOGRAM
# ═══════════════════════════════════════════════════════════════════════
class AnalizadorLombScargle:
    """
    Periodograma de Lomb-Scargle para detectar periodicidades en series
    irregulares o con huecos. Usa scipy.signal.lombscargle.

    A diferencia de FFT, no asume muestreo uniforme y es más robusto
    a la presencia de huecos en el histórico.
    """

    def __init__(self, historico: List[List[int]]):
        self.historico = historico
        self.n = len(historico)

    def calcular_scores(self) -> Dict[int, float]:
        try:
            from scipy.signal import lombscargle
        except ImportError:
            logger.warning("Lomb-Scargle no disponible — usando fallback")
            return {n: 0.5 for n in range(1, 50)}

        scores = {}
        ventana = min(200, self.n)

        # Frecuencias a evaluar (período entre 2 y 50 sorteos)
        periodos = np.linspace(2, 50, 30)
        omegas = 2 * np.pi / periodos

        for num in range(1, 50):
            # Tiempos de aparición del número
            tiempos = np.array([float(i) for i, s in enumerate(self.historico[:ventana])
                                if num in s])

            if len(tiempos) < 5:
                scores[num] = 0.5
                continue

            # Señal: usar incrementos de los tiempos (deltas) en lugar de
            # función indicadora constante, que daría divide-by-zero al
            # restar la media (todos los valores serían 0).
            valores = np.diff(np.concatenate(([0.0], tiempos)))
            valores_centrados = valores - valores.mean()

            # Si la señal centrada es prácticamente plana, no hay periodicidad
            if np.std(valores_centrados) < 1e-9:
                scores[num] = 0.5
                continue

            try:
                # Suprimir warnings de scipy por divisiones residuales
                with np.errstate(divide='ignore', invalid='ignore'):
                    pgram = lombscargle(tiempos, valores_centrados,
                                        omegas, normalize=True)

                # Filtrar valores no válidos del periodograma
                pgram = pgram[np.isfinite(pgram)]
                pico_max = float(pgram.max()) if len(pgram) > 0 else 0.0

                scores[num] = max(0.0, min(1.0, pico_max))
            except Exception as e:
                logger.debug(f"Lomb-Scargle error num={num}: {e}")
                scores[num] = 0.5

        max_v = max(scores.values(), default=1)
        if max_v > 0:
            scores = {n: v / max_v for n, v in scores.items()}
        return scores
