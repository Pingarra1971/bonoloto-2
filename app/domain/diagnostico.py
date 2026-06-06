"""
╔══════════════════════════════════════════════════════════════════════╗
║   BONOLOTO AI v3.0 — MÓDULO DE DIAGNÓSTICO ESTADÍSTICO             ║
║   Decide qué algoritmos activar según el estado del sistema         ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import math
import logging
import time
from collections import defaultdict
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field

import numpy as np

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════
# RESULTADO DEL DIAGNÓSTICO
# ═══════════════════════════════════════════════════════════════════════
@dataclass
class ResultadoDiagnostico:
    # Métricas estadísticas
    entropia_permutacion: float = 0.5
    chi2_pvalue: float = 0.5
    ks_pvalue: float = 0.5
    hurst: float = 0.5
    n_sorteos: int = 0
    ram_disponible_gb: float = 24.0

    # Flags de activación de algoritmos costosos
    activar_tda: bool = False
    activar_var: bool = False
    activar_hawkes: bool = False
    activar_regresion_simbolica: bool = False
    activar_copulas: bool = False
    activar_multifractal: bool = False
    activar_hmm: bool = False
    activar_esn: bool = False

    # Tiempo estimado total
    tiempo_estimado_min: float = 45.0

    # Descripción legible
    resumen: str = ""

    # Nivel de señal estadística detectada
    nivel_senal: str = "bajo"  # bajo, medio, alto

    def to_dict(self) -> dict:
        return {
            "entropia_permutacion": round(self.entropia_permutacion, 4),
            "chi2_pvalue": round(self.chi2_pvalue, 4),
            "ks_pvalue": round(self.ks_pvalue, 4),
            "hurst": round(self.hurst, 4),
            "n_sorteos": self.n_sorteos,
            "nivel_senal": self.nivel_senal,
            "algoritmos_extra_activos": {
                "tda": self.activar_tda,
                "var": self.activar_var,
                "hawkes": self.activar_hawkes,
                "regresion_simbolica": self.activar_regresion_simbolica,
                "copulas": self.activar_copulas,
                "multifractal": self.activar_multifractal,
                "hmm": self.activar_hmm,
                "esn": self.activar_esn,
            },
            "tiempo_estimado_min": round(self.tiempo_estimado_min, 1),
            "resumen": self.resumen,
        }


# ═══════════════════════════════════════════════════════════════════════
# MOTOR DE DIAGNÓSTICO
# ═══════════════════════════════════════════════════════════════════════
class MotorDiagnostico:
    """
    Ejecuta un diagnóstico estadístico completo del histórico en ~30s
    y decide qué algoritmos del Nivel 2 activar.
    """

    # Umbrales de activación (calibrados para ARM 24GB)
    UMBRAL_EP_TDA = 0.82        # Entropía permutación < 0.82 → activar TDA
    UMBRAL_EP_HAWKES = 0.88     # EP < 0.88 → activar Hawkes
    UMBRAL_SORTEOS_VAR = 500    # Mínimo sorteos para VAR multivariante
    UMBRAL_CHI2_SIMBOLICA = 0.05  # Chi2 p < 0.05 → activar regresión simbólica
    UMBRAL_KS_COPULAS = 0.10    # KS p < 0.10 → activar cópulas
    UMBRAL_HURST_MULTIFRACTAL = 0.55  # Hurst > 0.55 → activar multifractal DFA
    UMBRAL_EP_HMM = 0.90        # EP < 0.90 → activar HMM
    UMBRAL_SORTEOS_ESN = 200    # Mínimo sorteos para ESN

    # RAM estimada por algoritmo (GB)
    RAM_TDA = 4.5
    RAM_VAR = 2.5
    RAM_HAWKES = 1.5
    RAM_SIMBOLICA = 3.0
    RAM_COPULAS = 3.5
    RAM_MULTIFRACTAL = 0.8
    RAM_HMM = 1.5
    RAM_ESN = 1.5
    RAM_BASE = 12.0  # RAM para los 32 algoritmos core

    def __init__(self, historico: List[List[int]]):
        self.historico = historico
        self.n = len(historico)

    def ejecutar(self) -> ResultadoDiagnostico:
        """Ejecuta diagnóstico completo y devuelve decisión de activación."""
        resultado = ResultadoDiagnostico(n_sorteos=self.n)

        if self.n < 10:
            resultado.resumen = "Histórico insuficiente — solo algoritmos core activos"
            return resultado

        # 1. Entropía de Permutación
        resultado.entropia_permutacion = self._calcular_entropia_permutacion()

        # 2. Test Chi-cuadrado
        resultado.chi2_pvalue = self._test_chi2()

        # 3. Test Kolmogorov-Smirnov
        resultado.ks_pvalue = self._test_ks()

        # 4. Exponente de Hurst
        resultado.hurst = self._calcular_hurst()

        # 5. RAM disponible (estimada)
        resultado.ram_disponible_gb = self._estimar_ram_disponible()

        # 6. Nivel de señal global
        resultado.nivel_senal = self._evaluar_nivel_senal(resultado)

        # 7. Decisiones de activación
        self._decidir_activaciones(resultado)

        # 8. Tiempo estimado
        resultado.tiempo_estimado_min = self._estimar_tiempo(resultado)

        # 9. Resumen
        resultado.resumen = self._generar_resumen(resultado)

        logger.info(f"Diagnóstico: {resultado.resumen}")
        return resultado

    def _calcular_entropia_permutacion(self, orden: int = 3) -> float:
        """
        Entropía de Permutación sobre la serie de sumas de cada sorteo.
        Mide la complejidad dinámica del sistema.
        EP = 1.0 → máxima aleatoriedad
        EP < 0.85 → hay estructura predecible
        """
        sumas = [sum(s) for s in self.historico]
        n = len(sumas)
        if n < orden + 1:
            return 1.0

        # Contar patrones ordinales de longitud 'orden'
        patrones = defaultdict(int)
        total = 0
        for i in range(n - orden):
            ventana = sumas[i:i + orden]
            patron = tuple(sorted(range(orden), key=lambda x: ventana[x]))
            patrones[patron] += 1
            total += 1

        if total == 0:
            return 1.0

        # Entropía de Shannon normalizada
        h = 0.0
        for count in patrones.values():
            p = count / total
            if p > 0:
                h -= p * math.log2(p)

        max_h = math.log2(math.factorial(orden))
        return h / max_h if max_h > 0 else 1.0

    def _test_chi2(self) -> float:
        """
        Test Chi-cuadrado de bondad de ajuste.
        Compara frecuencias observadas vs esperadas (distribución uniforme).
        p < 0.05 → distribución significativamente no uniforme
        """
        frecuencias = defaultdict(int)
        for sorteo in self.historico:
            for n in sorteo:
                frecuencias[n] += 1

        total = sum(frecuencias.values())
        if total == 0:
            return 0.5   # sin datos, no podemos rechazar uniformidad
        esperada = total / 49
        if esperada <= 0:
            return 0.5

        chi2 = sum(
            (frecuencias.get(n, 0) - esperada) ** 2 / esperada
            for n in range(1, 50)
        )

        # p-valor aproximado usando distribución chi2 con 48 grados de libertad
        gl = 48
        z = ((chi2 / gl) ** (1/3) - (1 - 2/(9*gl))) / math.sqrt(2/(9*gl))

        # CDF normal estándar aproximada
        p_valor = 1 - self._cdf_normal(z)
        return max(0.001, min(0.999, p_valor))

    def _test_ks(self) -> float:
        """
        Test Kolmogorov-Smirnov entre ventana reciente y ventana anterior.
        Detecta si la distribución ha cambiado.
        p < 0.10 → distribuciones significativamente diferentes
        """
        if self.n < 200:
            return 0.5

        mitad = self.n // 2
        ventana1 = self.historico[:mitad]
        ventana2 = self.historico[mitad:]

        freq1 = defaultdict(int)
        freq2 = defaultdict(int)
        for s in ventana1:
            for n in s: freq1[n] += 1
        for s in ventana2:
            for n in s: freq2[n] += 1

        total1 = sum(freq1.values()) or 1
        total2 = sum(freq2.values()) or 1

        # Estadístico KS: máxima diferencia en CDFs empíricas
        d_max = max(
            abs(freq1.get(n, 0)/total1 - freq2.get(n, 0)/total2)
            for n in range(1, 50)
        )

        # Aproximación p-valor KS
        n_eff = (mitad * (self.n - mitad)) / self.n
        ks_stat = d_max * math.sqrt(n_eff)
        p_valor = 2 * math.exp(-2 * ks_stat ** 2)
        return max(0.001, min(0.999, p_valor))

    def _calcular_hurst(self) -> float:
        """
        Exponente de Hurst mediante análisis R/S simplificado.
        H > 0.5 → memoria persistente (tendencias)
        H = 0.5 → ruido blanco (aleatorio puro)
        H < 0.5 → antipersistencia (reversión a media)
        """
        if self.n < 50:
            return 0.5

        sumas = np.array([sum(s) for s in self.historico[:min(self.n, 500)]], dtype=float)
        n = len(sumas)

        # R/S en múltiples escalas
        escalas = [8, 16, 32, 64, 128]
        rs_values = []
        escala_validas = []

        for escala in escalas:
            if escala >= n:
                continue
            rs_lista = []
            for inicio in range(0, n - escala, escala):
                segmento = sumas[inicio:inicio + escala]
                media = np.mean(segmento)
                desviaciones = np.cumsum(segmento - media)
                R = np.max(desviaciones) - np.min(desviaciones)
                S = np.std(segmento)
                if S > 0:
                    rs_lista.append(R / S)
            if rs_lista:
                rs_values.append(np.mean(rs_lista))
                escala_validas.append(escala)

        if len(rs_values) < 2:
            return 0.5

        # Regresión log-log con protección
        try:
            esc_arr = np.array(escala_validas, dtype=float)
            rs_arr = np.array(rs_values, dtype=float)
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

    def _estimar_ram_disponible(self) -> float:
        """Estima RAM disponible consultando /proc/meminfo en Oracle Cloud."""
        try:
            with open('/proc/meminfo', 'r') as f:
                for line in f:
                    if 'MemAvailable' in line:
                        kb = int(line.split()[1])
                        return kb / (1024 * 1024)  # GB
        except Exception:
            pass
        return 20.0  # Conservador por defecto

    def _evaluar_nivel_senal(self, r: ResultadoDiagnostico) -> str:
        """Evalúa el nivel global de señal estadística detectable."""
        puntos = 0
        if r.entropia_permutacion < 0.85: puntos += 2
        if r.entropia_permutacion < 0.75: puntos += 2
        if r.chi2_pvalue < 0.05: puntos += 3
        if r.chi2_pvalue < 0.01: puntos += 2
        if r.ks_pvalue < 0.10: puntos += 2
        if abs(r.hurst - 0.5) > 0.1: puntos += 2
        if r.n_sorteos > 1000: puntos += 1
        if r.n_sorteos > 5000: puntos += 2

        if puntos >= 10: return "alto"
        if puntos >= 5:  return "medio"
        return "bajo"

    def _decidir_activaciones(self, r: ResultadoDiagnostico):
        """Decide qué algoritmos de Nivel 2 activar según diagnóstico."""
        ram_usada = self.RAM_BASE

        # TDA — requiere señal alta y EP baja
        if (r.entropia_permutacion < self.UMBRAL_EP_TDA and
                r.nivel_senal == "alto" and
                ram_usada + self.RAM_TDA <= r.ram_disponible_gb - 2):
            r.activar_tda = True
            ram_usada += self.RAM_TDA

        # HMM — requiere EP moderada
        if (r.entropia_permutacion < self.UMBRAL_EP_HMM and
                ram_usada + self.RAM_HMM <= r.ram_disponible_gb - 2):
            r.activar_hmm = True
            ram_usada += self.RAM_HMM

        # ESN — requiere mínimo histórico
        if (r.n_sorteos >= self.UMBRAL_SORTEOS_ESN and
                ram_usada + self.RAM_ESN <= r.ram_disponible_gb - 2):
            r.activar_esn = True
            ram_usada += self.RAM_ESN

        # VAR — requiere histórico amplio
        if (r.n_sorteos >= self.UMBRAL_SORTEOS_VAR and
                ram_usada + self.RAM_VAR <= r.ram_disponible_gb - 2):
            r.activar_var = True
            ram_usada += self.RAM_VAR

        # Cópulas — requiere distribución no homogénea
        if (r.ks_pvalue < self.UMBRAL_KS_COPULAS and
                ram_usada + self.RAM_COPULAS <= r.ram_disponible_gb - 2):
            r.activar_copulas = True
            ram_usada += self.RAM_COPULAS

        # Proceso de Hawkes — requiere EP baja
        if (r.entropia_permutacion < self.UMBRAL_EP_HAWKES and
                ram_usada + self.RAM_HAWKES <= r.ram_disponible_gb - 2):
            r.activar_hawkes = True
            ram_usada += self.RAM_HAWKES

        # Multifractal DFA — requiere Hurst elevado
        if (r.hurst > self.UMBRAL_HURST_MULTIFRACTAL and
                ram_usada + self.RAM_MULTIFRACTAL <= r.ram_disponible_gb - 2):
            r.activar_multifractal = True
            ram_usada += self.RAM_MULTIFRACTAL

        # Regresión Simbólica — requiere chi2 significativo
        if (r.chi2_pvalue < self.UMBRAL_CHI2_SIMBOLICA and
                r.nivel_senal in ["medio", "alto"] and
                ram_usada + self.RAM_SIMBOLICA <= r.ram_disponible_gb - 2):
            r.activar_regresion_simbolica = True
            ram_usada += self.RAM_SIMBOLICA

    def _estimar_tiempo(self, r: ResultadoDiagnostico) -> float:
        """Estima el tiempo total de cálculo en minutos."""
        tiempo = 30.0  # Base con 32 algoritmos core

        if r.activar_tda: tiempo += 60.0
        if r.activar_var: tiempo += 15.0
        if r.activar_hawkes: tiempo += 10.0
        if r.activar_regresion_simbolica: tiempo += 45.0
        if r.activar_copulas: tiempo += 20.0
        if r.activar_multifractal: tiempo += 8.0
        if r.activar_hmm: tiempo += 10.0
        if r.activar_esn: tiempo += 8.0

        return tiempo

    def _generar_resumen(self, r: ResultadoDiagnostico) -> str:
        extras = []
        if r.activar_tda: extras.append("TDA")
        if r.activar_var: extras.append("VAR")
        if r.activar_hawkes: extras.append("Hawkes")
        if r.activar_regresion_simbolica: extras.append("SymReg")
        if r.activar_copulas: extras.append("Cópulas")
        if r.activar_multifractal: extras.append("Multifractal")
        if r.activar_hmm: extras.append("HMM")
        if r.activar_esn: extras.append("ESN")

        n_total = 32 + len(extras)
        extra_str = f" + extras: {', '.join(extras)}" if extras else ""
        return (
            f"Señal: {r.nivel_senal} | EP={r.entropia_permutacion:.3f} "
            f"| Hurst={r.hurst:.3f} | {n_total} algoritmos{extra_str} "
            f"| ~{r.tiempo_estimado_min:.0f} min"
        )

    @staticmethod
    def _cdf_normal(x: float) -> float:
        """CDF normal estándar aproximada (error < 0.001)."""
        t = 1 / (1 + 0.2316419 * abs(x))
        poly = t * (0.319381530 + t * (-0.356563782 +
               t * (1.781477937 + t * (-1.821255978 + t * 1.330274429))))
        p = 1 - (1 / math.sqrt(2 * math.pi)) * math.exp(-x*x/2) * poly
        return p if x >= 0 else 1 - p
