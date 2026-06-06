"""
╔══════════════════════════════════════════════════════════════════════════════╗
║   BONOLOTO AI v7.0 — PIPELINE PRINCIPAL v4                                  ║
║                                                                              ║
║   Integra diagnóstico + 93 algoritmos previos + 17 nuevos (Bloque K ext)    ║
║                       + 5 mejoras estratégicas (Bloque L)                    ║
║                                                                              ║
║   Total: 110 técnicas algorítmicas + 5 estratégicas = 115 mejoras           ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Tuple, Any

import numpy as np

from app.domain.diagnostico import MotorDiagnostico, ResultadoDiagnostico
from app.domain.algorithms.level1 import (
    DecaimientoExponencial, TestKolmogorovSmirnov,
    AnalizadorGapsPoisson, FiltroJaccard,
    TestChiCuadradoAdaptativo, AnalizadorARIMA,
    AnalizadorPCA, AnalizadorPremiosSecundarios,
    CalibradorIsotonic, SimulatedAnnealing,
    BootstrapConfianza, PenalizadorPopularidad,
    AnalizadorGRU, AnalizadorInformacionMutua,
    RuedaCombinatoriaInteligente, AnalizadorSARIMA,
    AnalizadorIMCondicional, AnalizadorFeaturesEstructurales,
    AnalizadorBiLSTM, AnalizadorPosicionOrdinal,
    AnalizadorComplementarioReintegro, AnalizadorHMM,
    ReguladorEntropiaPermutacion, AnalizadorProgresionesAritmeticas,
    AnalizadorTestRuns, normalizar_zscore_adaptativo,
    AnalizadorSimetriaEspecular, AnalizadorHurst,
    AnalizadorPACF,
)
from app.domain.algorithms.level2 import (
    AnalizadorCopulas, AnalizadorEVT,
    AnalizadorDirichlet, AnalizadorMultiScaleEntropy,
    AnalizadorESN, AnalizadorVAR,
    AnalizadorTDA, AnalizadorRegresionSimbolica,
    AnalizadorLyapunov, AnalizadorHawkes,
    AnalizadorMultifractalDFA,
)
from app.domain.algorithms.block_i import (
    AnalizadorLNN, AnalizadorTDAv2, AnalizadorSAX,
    ArbitroMDL, AnalizadorDWT, MixtureOfExperts, AnalizadorGAT,
)
from app.domain.algorithms.advanced import (
    AnalizadorMaxEnt, AtribucionShapley, AnalizadorNBEATS,
    AnalizadorCuantilesExtremos, AnalizadorCurriculumLearning,
)
from app.domain.algorithms.block_j import (
    AnalizadorSSA, AnalizadorVMD, DetectorBOCPD,
    AnalizadorEMD, AnalizadorRETAIN, AnalizadorLombScargle,
)
from app.domain.algorithms.block_k import (
    # Bloque K original (94-102)
    AnalizadorNGRC, AnalizadorDMDKoopman, AnalizadorKAN,
    AnalizadorDLinear, AnalizadorSINDy, AnalizadorTSFresh,
    AnalizadorNHiTS, AnalizadorFITS, AnalizadorTimeMixer,
    # Bloque K extendido ronda 1 (103-107)
    AnalizadorModernHopfield, AnalizadorVineCopulas,
    AnalizadorMiniRocket, AnalizadorVisibilityGraph,
    AnalizadorAssociationRules,
    # Bloque K extendido ronda 3 - redes neuronales (108-110)
    AnalizadorRBM, AnalizadorSOM, AnalizadorHDC,
)
from app.domain.algorithms.block_l import (
    SistemaReducido, ConfidenceWeightedBetting, BoteAwareROI,
    AntiPopularityScorer, MultiLoteria, EstrategiaIntegradaBloqueL,
)
from app.domain.motor_mejorado import (
    AnalizadorFFT, DetectorAnomalias, ValidadorWalkForward,
    CacheScores, AlgoritmoGeneticoNSGA2, EnsembleStacking,
    _cache_global,
)
from app.domain.motor_ia import MotorIA

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════
# RESULTADO DEL PIPELINE
# ═══════════════════════════════════════════════════════════════════════
class ResultadoPipeline:
    def __init__(self):
        self.combinaciones: List[dict] = []
        self.scores_por_algoritmo: Dict[str, Dict[int, float]] = {}
        # Puntuación final de consenso por número (1-49). Fuente para las
        # apuestas múltiples (los K números mejor puntuados).
        self.scores_finales: Dict[int, float] = {}
        self.diagnostico: Optional[ResultadoDiagnostico] = None
        self.n_algoritmos_activos: int = 0
        self.tiempo_total_seg: float = 0.0
        self.iteraciones: int = 0
        self.confianza_maxima: float = 0.0
        self.estado_algoritmos: Dict[str, str] = {}
        self.mejoras_detalle: Dict[str, Any] = {}
        # ── Campos Bloque L (estratégicos) ──
        self.bloque_l_estrategia: Optional[Dict[str, Any]] = None
        self.bloque_l_sistema_reducido: Optional[str] = None
        self.bloque_l_apuestas_garantizadas: List[List[int]] = []
        self.bloque_l_coste_total_eur: float = 0.0
        self.bloque_l_recomendacion: str = ""
        self.bloque_l_analisis_roi: Optional[Dict[str, Any]] = None
        self.bloque_l_confianza_agregada: Optional[Dict[str, Any]] = None
        # ── Cobertura garantizada (nuevo: covering design) ──
        self.cobertura_garantizada: Optional[Dict[str, Any]] = None


# ═══════════════════════════════════════════════════════════════════════
# PIPELINE PRINCIPAL v4.0 (Bonoloto 2.0)
# ═══════════════════════════════════════════════════════════════════════
class PipelineV4:
    """
    Pipeline completo v7.0 con arquitectura adaptativa:
    - Fase 0: Diagnóstico estadístico (30s)
    - Fase 1: 32 algoritmos core siempre activos
    - Fase 2: Hasta 11 algoritmos condicionales según diagnóstico
    - Fase 2.5: 17 algoritmos del Bloque K extendido (94-110)
    - Fase 3: Meta-modelo + NSGA-II + convergencia adaptativa
    - Fase 4: Bloque L estratégico (sistemas reducidos + ROI + anti-popularidad)
    """

    def __init__(self,
                 historico: List[List[int]],
                 sorteos_completos: List[dict],
                 callback_progreso=None,
                 presupuesto_usuario_eur: float = 10.0,
                 bote_acumulado_eur: float = 600_000.0,
                 loteria: str = "bonoloto",
                 peso_anti_popular: float = 0.20):
        self.historico = historico
        self.sorteos_completos = sorteos_completos
        self.callback = callback_progreso
        self.cache = _cache_global
        self.stacking = EnsembleStacking()
        self.calibrador = CalibradorIsotonic()
        self.bootstrap = BootstrapConfianza(n_muestras=300)
        self.penalizador = PenalizadorPopularidad()
        self.filtro_jaccard = FiltroJaccard(umbral=0.50)
        # Parámetros del Bloque L
        self.presupuesto_usuario_eur = presupuesto_usuario_eur
        self.bote_acumulado_eur = bote_acumulado_eur
        self.loteria = loteria
        self.estrategia_l = EstrategiaIntegradaBloqueL(
            presupuesto_max_eur=presupuesto_usuario_eur,
            peso_anti_popular=peso_anti_popular,
        )

    async def _notificar(self, estado: Dict[str, str], progreso: float,
                         confianza: float, iteracion: int, convergiendo: bool):
        """Notifica progreso al worker de forma asíncrona."""
        if self.callback:
            await self.callback(
                estado_algoritmos=estado,
                progreso=progreso,
                confianza=confianza,
                iteracion=iteracion,
                convergiendo=convergiendo,
            )

    async def ejecutar(self, cantidad: int) -> ResultadoPipeline:
        """Ejecuta el pipeline completo con convergencia adaptativa."""
        resultado = ResultadoPipeline()
        t_inicio = time.time()
        estado_alg = {}

        # ══════════════════════════════════════════════════════════════
        # FASE 0 — DIAGNÓSTICO ESTADÍSTICO
        # ══════════════════════════════════════════════════════════════
        self._marcar(estado_alg, ["Diagnóstico", "Isolation Forest",
                                   "Decaimiento Exponencial"], "procesando")
        await self._notificar(estado_alg, 0.02, 0.0, 0, False)

        # Isolation Forest
        detector = DetectorAnomalias(n_arboles=50, submuestra=64)
        detector.entrenar(self.historico)
        hist_limpio, anomalos = detector.filtrar_historico(self.historico, umbral=0.65)
        self._marcar(estado_alg, ["Isolation Forest"], "completado")

        # KS test para decaimiento adaptativo
        ks_test = TestKolmogorovSmirnov(hist_limpio)
        ks_pvalue, heterogeneo = ks_test.ejecutar()
        self._marcar(estado_alg, ["Test KS"], "completado")

        # Decaimiento exponencial adaptativo
        decaimiento = DecaimientoExponencial(hist_limpio)
        decaimiento.ajustar_tasa(ks_pvalue)
        self._marcar(estado_alg, ["Decaimiento Exponencial"], "completado")

        # Diagnóstico completo
        motor_diag = MotorDiagnostico(hist_limpio)
        diag = motor_diag.ejecutar()
        resultado.diagnostico = diag
        self._marcar(estado_alg, ["Diagnóstico"], "completado")

        # Chi-cuadrado adaptativo
        chi2_test = TestChiCuadradoAdaptativo(hist_limpio)
        chi2_pvalue, ajuste_chi2 = chi2_test.ejecutar()
        self._marcar(estado_alg, ["Test Chi-cuadrado"], "completado")

        # Walk-Forward Validation inicial
        self._marcar(estado_alg, ["Walk-Forward"], "procesando")
        await self._notificar(estado_alg, 0.06, 0.0, 0, False)

        validador_wf = ValidadorWalkForward(hist_limpio, n_ventanas=5)
        metricas_wf = validador_wf.ejecutar_validacion({
            "entropia": lambda h: self._scores_base("entropia", h),
            "lstm":     lambda h: self._scores_base("lstm", h),
            "bayesiano":lambda h: self._scores_base("bayesiano", h),
            "xgboost":  lambda h: self._scores_base("xgboost", h),
        })
        pesos_wf = validador_wf.pesos_desde_metricas()
        self._marcar(estado_alg, ["Walk-Forward"], "completado")

        await self._notificar(estado_alg, 0.10, 0.0, 0, False)

        # ══════════════════════════════════════════════════════════════
        # FASE 1 — 32 ALGORITMOS CORE (con caché inteligente)
        # ══════════════════════════════════════════════════════════════
        scores_core = await self._calcular_algoritmos_core(
            hist_limpio, estado_alg, self.sorteos_completos
        )
        await self._notificar(estado_alg, 0.55, 0.0, 0, False)

        # ══════════════════════════════════════════════════════════════
        # FASE 2 — ALGORITMOS CONDICIONALES (Nivel 2)
        # ══════════════════════════════════════════════════════════════
        scores_nivel2 = await self._calcular_algoritmos_nivel2(
            hist_limpio, diag, estado_alg
        )
        await self._notificar(estado_alg, 0.70, 0.0, 0, False)

        # ══════════════════════════════════════════════════════════════
        # FASE 3 — NORMALIZACIÓN + ENSEMBLE STACKING + CONVERGENCIA
        # ══════════════════════════════════════════════════════════════
        todos_scores = {**scores_core, **scores_nivel2}

        # Normalización z-score adaptativa
        todos_scores = normalizar_zscore_adaptativo(todos_scores)

        # Ajuste por chi-cuadrado (las claves deben coincidir con los
        # nombres de caché reales — "hot_cold" no "hot_cold_bias")
        factor_freq = ajuste_chi2.get("frecuencia", 1.0)
        factor_mc = ajuste_chi2.get("monte_carlo", 1.0)
        for alg in ["entropia", "hot_cold", "decaimiento"]:
            if alg in todos_scores:
                todos_scores[alg] = {
                    n: v * factor_freq for n, v in todos_scores[alg].items()
                }
        if "monte_carlo" in todos_scores:
            todos_scores["monte_carlo"] = {
                n: v * factor_mc for n, v in todos_scores["monte_carlo"].items()
            }

        resultado.scores_por_algoritmo = todos_scores
        resultado.n_algoritmos_activos = len(todos_scores)

        # ── BUCLE DE CONVERGENCIA ADAPTATIVA ──────────────────────────
        mejor_confianza = 0.0
        mejor_combinaciones = []
        scores_stacking_final = {}  # exportable a Fase 4 Bloque L
        iteracion = 0
        estable = 0
        max_iter = 60
        umbral_conv = 0.0005

        while iteracion < max_iter:
            iteracion += 1
            convergiendo = iteracion > 8
            await self._notificar(estado_alg,
                                  0.70 + iteracion * 0.004,
                                  mejor_confianza, iteracion, convergiendo)

            # Stacking de segundo nivel
            self._marcar(estado_alg, ["Ensemble Stacking"], "procesando")
            scores_stacking = self.stacking.predecir_todos(todos_scores)
            self._marcar(estado_alg, ["Ensemble Stacking"], "completado")

            # MoE Dinámico (81): ajustar pesos según estado estadístico actual
            self._marcar(estado_alg, ["MoE Dinámico"], "procesando")
            moe = MixtureOfExperts(hist_limpio)
            pesos_moe = moe.calcular_pesos_gating(todos_scores)
            # Fusionar stacking con pesos MoE (60/40)
            scores_moe_combinados = moe.combinar_con_gating(todos_scores)
            scores_stacking = {
                n: 0.65 * scores_stacking.get(n, 0) +
                   0.35 * scores_moe_combinados.get(n, 0)
                for n in range(1, 50)
            }
            max_st = max(scores_stacking.values(), default=1)
            if max_st > 0:
                scores_stacking = {n: v/max_st for n, v in scores_stacking.items()}
            self._marcar(estado_alg, ["MoE Dinámico"], "completado")

            # Shapley (84): recalibrar pesos del stacking cada 5 iteraciones
            if iteracion % 5 == 1:
                self._marcar(estado_alg, ["Shapley Attribution"], "procesando")
                shapley = AtribucionShapley(n_muestras=150)
                pesos_shapley = shapley.calcular_shapley(todos_scores)
                for alg, peso in pesos_shapley.items():
                    if alg in self.stacking.meta_pesos:
                        self.stacking.meta_pesos[alg] = (
                            0.85 * self.stacking.meta_pesos[alg] +
                            0.15 * peso
                        )
                # Renormalizar meta_pesos
                total_mp = sum(self.stacking.meta_pesos.values())
                if total_mp > 0:
                    self.stacking.meta_pesos = {
                        k: v/total_mp for k, v in self.stacking.meta_pesos.items()
                    }
                self._marcar(estado_alg, ["Shapley Attribution"], "completado")

            # NSGA-II multi-objetivo
            self._marcar(estado_alg, ["NSGA-II Multi-objetivo"], "procesando")
            gen_nsga2 = min(80 + iteracion * 5, 220)
            nsga2 = AlgoritmoGeneticoNSGA2(
                scores_consenso=scores_stacking,
                poblacion=280,
                generaciones=gen_nsga2,
                tasa_mutacion=max(0.05, 0.15 - iteracion * 0.002),
            )
            resultado_nsga2 = nsga2.ejecutar(cantidad * 3)
            self._marcar(estado_alg, ["NSGA-II Multi-objetivo"], "completado")

            # Post-optimización con Simulated Annealing
            self._marcar(estado_alg, ["Simulated Annealing"], "procesando")
            combos_sa = []
            for combo, score_p, objs in resultado_nsga2[:cantidad * 2]:
                sa = SimulatedAnnealing(scores_stacking, iteraciones=3000)
                combo_opt = sa.optimizar(combo)
                combos_sa.append((combo_opt, score_p, objs))
            self._marcar(estado_alg, ["Simulated Annealing"], "completado")

            # Rueda combinatoria inteligente
            self._marcar(estado_alg, ["Rueda Combinatoria"], "procesando")
            rueda = RuedaCombinatoriaInteligente(scores_stacking)
            combos_rueda = rueda.generar_rueda(top_n=15, cantidad=cantidad)
            combos_rueda_fmt = [(c, 0.7, (0.7, 0.6, 0.6, 0.6)) for c in combos_rueda]
            self._marcar(estado_alg, ["Rueda Combinatoria"], "completado")

            # Combinar todas las fuentes
            todas_candidatas = combos_sa + combos_rueda_fmt

            # Calcular índices de confianza v3
            combos_con_confianza = []
            for combo, score_pareto, objs in todas_candidatas:
                combo = sorted(list(set(combo)))
                if len(combo) != 6:
                    continue
                penalizacion = self.penalizador.calcular_penalizacion(combo)
                ic_inf, ic_sup = self.bootstrap.calcular_banda(scores_stacking, combo)
                confianza = self._calcular_confianza_v3(
                    combo, scores_stacking, objs, metricas_wf, penalizacion
                )
                combos_con_confianza.append({
                    "combo": combo,
                    "confianza": confianza,
                    "ic_inferior": round(ic_inf, 1),
                    "ic_superior": round(ic_sup, 1),
                    "objs": objs,
                    "score_pareto": score_pareto,
                    "penalizacion": penalizacion,
                })

            # Filtro Jaccard para diversidad máxima
            combos_con_confianza.sort(key=lambda x: x["confianza"], reverse=True)
            combos_filtrados = []
            vistas = set()
            for c in combos_con_confianza:
                clave = tuple(c["combo"])
                if clave not in vistas:
                    vistas.add(clave)
                    combos_filtrados.append(c)

            listas_filtradas = [c["combo"] for c in combos_filtrados]
            listas_diversas = self.filtro_jaccard.filtrar(listas_filtradas)

            combinaciones_final = [
                c for c in combos_filtrados
                if c["combo"] in listas_diversas
            ][:cantidad]

            if not combinaciones_final:
                combinaciones_final = combos_filtrados[:cantidad]

            # Bug #163: si tras los filtros (dedup + Jaccard) quedan MENOS de
            # las solicitadas, rellenar con el resto de candidatas por
            # confianza para no devolver menos combinaciones de las pedidas.
            if len(combinaciones_final) < cantidad:
                ya = {tuple(c["combo"]) for c in combinaciones_final}
                for c in combos_filtrados:
                    if len(combinaciones_final) >= cantidad:
                        break
                    if tuple(c["combo"]) not in ya:
                        combinaciones_final.append(c)
                        ya.add(tuple(c["combo"]))

            confianza_actual = max(
                (c["confianza"] for c in combinaciones_final), default=0
            )

            # Verificar convergencia.
            # Importante: la sobreescritura `mejor_combinaciones =
            # combinaciones_final` en el break dejaba mejor_combinaciones
            # y scores_stacking_final apuntando a iteraciones distintas
            # (los scores quedaban del best-seen, las combos del break).
            # Eliminada: el break ahora respeta el par mejor-visto.
            mejora = confianza_actual - mejor_confianza
            if mejora < umbral_conv and iteracion > 8:
                estable += 1
                if estable >= 4:
                    logger.info(f"Convergencia en iter {iteracion}: {confianza_actual:.2f}%")
                    break
            else:
                estable = 0

            if confianza_actual > mejor_confianza:
                mejor_confianza = confianza_actual
                mejor_combinaciones = combinaciones_final
                scores_stacking_final = dict(scores_stacking)

            # Caso degenerado: ninguna iter ha mejorado todavía (p.ej.
            # confianza_actual <= 0 en iter 1) y aún no hay mejor_combinaciones.
            # Sembrar con lo que tengamos para no publicar resultados vacíos.
            if not mejor_combinaciones and combinaciones_final:
                mejor_combinaciones = combinaciones_final
                scores_stacking_final = dict(scores_stacking)

            await asyncio.sleep(0.02)

        # Si nunca se actualizó (caso edge: ningún iter mejoró), usar fallback
        if not scores_stacking_final:
            scores_stacking_final = {n: 0.5 for n in range(1, 50)}
            logger.debug("Pipeline: usando scores uniformes (sin iteración exitosa)")

        # ══════════════════════════════════════════════════════════════
        # FASE 4 — BLOQUE L ESTRATÉGICO (Sistemas reducidos + ROI + ...)
        # ══════════════════════════════════════════════════════════════
        self._marcar(estado_alg, ["Bloque L - Estrategia"], "procesando")
        await self._notificar(estado_alg, 0.93, mejor_confianza, iteracion, False)

        try:
            # Agregar scores finales del stacking + MoE
            scores_finales_l = scores_stacking_final
            # IC promedio de las combinaciones finales
            if mejor_combinaciones:
                ic_inf_avg = float(np.mean([c.get("ic_inferior", 30.0) for c in mejor_combinaciones]))
                ic_sup_avg = float(np.mean([c.get("ic_superior", 70.0) for c in mejor_combinaciones]))
            else:
                ic_inf_avg, ic_sup_avg = 30.0, 70.0

            estrategia_l = self.estrategia_l.construir_estrategia(
                scores_finales=scores_finales_l,
                scores_por_algoritmo=todos_scores,
                confianza_pipeline=mejor_confianza,
                ic_inferior=ic_inf_avg,
                ic_superior=ic_sup_avg,
                bote_acumulado_eur=self.bote_acumulado_eur,
                presupuesto_usuario_eur=self.presupuesto_usuario_eur,
                loteria=self.loteria,
            )
            resultado.bloque_l_estrategia = estrategia_l
            resultado.bloque_l_sistema_reducido = (
                estrategia_l["estrategia_apuesta"].get("sistema_recomendado")
            )
            resultado.bloque_l_apuestas_garantizadas = estrategia_l["apuestas_generadas"]
            resultado.bloque_l_coste_total_eur = estrategia_l["coste_total_eur"]
            resultado.bloque_l_recomendacion = estrategia_l["recomendacion_global"]
            resultado.bloque_l_analisis_roi = estrategia_l["analisis_roi"]
            resultado.bloque_l_confianza_agregada = estrategia_l["confianza_agregada"]
            self._marcar(estado_alg, ["Bloque L - Estrategia"], "completado")
        except Exception as e:
            logger.warning(f"Bloque L fallback: {e}")
            self._marcar(estado_alg, ["Bloque L - Estrategia"], "error")

        # ── Formatear resultado final ──────────────────────────────────
        resultado.combinaciones = self._formatear_combinaciones(
            mejor_combinaciones, todos_scores
        )
        # Guardar las puntuaciones finales por número (para apuestas múltiples).
        resultado.scores_finales = dict(scores_stacking_final)

        # ── Optimización de premio esperado (anti-popularidad) ──────────
        # Reordena las combinaciones finales priorizando las que cobrarían
        # MÁS si ganan (menos reparto del premio mutuo). NO altera la
        # probabilidad de ganar; solo el valor del premio condicional.
        try:
            from app.domain.algorithms.premio_esperado import (
                premio_esperado_relativo,
            )
            for c in resultado.combinaciones:
                nums = c.get("numeros", [])
                if len(nums) == 6:
                    c["premio_esperado_relativo"] = round(
                        premio_esperado_relativo(nums), 3
                    )
            # Orden estable: primero por confianza (ya venían así), pero
            # como desempate y señal, anotamos el premio esperado. No
            # reordenamos drásticamente para no romper el ranking de
            # confianza; el dato queda disponible para la UI.
            self._marcar(estado_alg, ["Optimización Premio Esperado"], "completado")
        except Exception as e:
            logger.debug("Premio esperado no aplicado: %s", e)

        # ── Diseño de cobertura para el conjunto de números top ─────────
        # Si el usuario juega varias combinaciones, ofrecer una cobertura
        # con garantía verificada sobre los números más recurrentes.
        try:
            from app.domain.algorithms.covering import resumen_cobertura
            # Números más frecuentes entre las combinaciones generadas
            from collections import Counter
            cont = Counter()
            for c in resultado.combinaciones:
                cont.update(c.get("numeros", []))
            top_numeros = [n for n, _ in cont.most_common(9)]
            if len(top_numeros) >= 7:
                cobertura = resumen_cobertura(
                    k_numeros=min(9, len(top_numeros)),
                    garantia=3, t_aciertos=4,
                )
                # Mapear índices a los números reales top
                from app.domain.algorithms.covering import aplicar_cobertura
                cobertura["apuestas_numeros"] = aplicar_cobertura(
                    cobertura["apuestas_indices"],
                    sorted(top_numeros[:cobertura["k_numeros"]]),
                )
                resultado.cobertura_garantizada = cobertura
        except Exception as e:
            logger.debug("Cobertura no calculada: %s", e)

        resultado.iteraciones = iteracion
        resultado.confianza_maxima = mejor_confianza
        resultado.tiempo_total_seg = time.time() - t_inicio
        resultado.estado_algoritmos = estado_alg
        resultado.mejoras_detalle = {
            "isolation_forest": f"{len(anomalos)} anomalías filtradas",
            "ks_pvalue": round(ks_pvalue, 4),
            "chi2_pvalue": round(chi2_pvalue, 4),
            "tasa_decaimiento": round(decaimiento.tasa, 4),
            "nivel_senal": diag.nivel_senal,
            "n_algoritmos": resultado.n_algoritmos_activos,
            "diagnostico": diag.to_dict(),
            "stacking_lider": self.stacking.estado()["algoritmo_lider"],
            # ── Bloque L resumen ──
            "bloque_l_sistema": resultado.bloque_l_sistema_reducido,
            "bloque_l_n_apuestas": len(resultado.bloque_l_apuestas_garantizadas),
            "bloque_l_coste": resultado.bloque_l_coste_total_eur,
            "bloque_l_recomendacion": resultado.bloque_l_recomendacion,
            "version_pipeline": "v4 (Bonoloto 2.0)",
            "total_tecnicas": 117,
        }

        logger.info(
            f"Pipeline v4 (v7.0) completado: {len(resultado.combinaciones)} combos base "
            f"| {len(resultado.bloque_l_apuestas_garantizadas)} apuestas Bloque L "
            f"| confianza: {mejor_confianza:.2f}% "
            f"| {resultado.n_algoritmos_activos} algoritmos "
            f"| {resultado.tiempo_total_seg:.0f}s "
            f"| coste estrategia: {resultado.bloque_l_coste_total_eur:.2f}€"
        )
        return resultado

    # ══════════════════════════════════════════════════════════════════
    # CÁLCULO DE ALGORITMOS CORE (32 SIEMPRE ACTIVOS)
    # ══════════════════════════════════════════════════════════════════
    async def _calcular_algoritmos_core(
        self,
        hist: List[List[int]],
        estado: Dict[str, str],
        sorteos_completos: List[dict],
    ) -> Dict[str, Dict[int, float]]:
        """Calcula los 32 algoritmos core con caché inteligente."""
        scores = {}

        def _con_cache(nombre: str, fn) -> Dict[int, float]:
            if self.cache.esta_valido(hist, nombre):
                return self.cache.obtener(nombre)
            r = fn()
            self.cache.guardar(hist, nombre, r)
            return r

        # ── Decaimiento Exponencial (1A) ──
        self._marcar(estado, ["Decaimiento Exponencial"], "procesando")
        scores["decaimiento"] = _con_cache("decaimiento",
            lambda: DecaimientoExponencial(hist).calcular_scores())
        self._marcar(estado, ["Decaimiento Exponencial"], "completado")

        # ── Gaps Poisson (3) ──
        self._marcar(estado, ["Gaps Poisson"], "procesando")
        scores["gaps_poisson"] = _con_cache("gaps_poisson",
            lambda: AnalizadorGapsPoisson(hist).calcular_scores())
        self._marcar(estado, ["Gaps Poisson"], "completado")

        # ── ARIMA (6) ──
        self._marcar(estado, ["ARIMA"], "procesando")
        scores["arima"] = _con_cache("arima",
            lambda: AnalizadorARIMA(hist).calcular_scores())
        self._marcar(estado, ["ARIMA"], "completado")

        # ── PCA (7) ──
        self._marcar(estado, ["PCA Co-ocurrencia"], "procesando")
        scores["pca"] = _con_cache("pca",
            lambda: AnalizadorPCA(hist).calcular_scores())
        self._marcar(estado, ["PCA Co-ocurrencia"], "completado")
        await asyncio.sleep(0.01)

        # ── Premios Secundarios (8) ──
        self._marcar(estado, ["Premios Secundarios"], "procesando")
        scores["premios_secundarios"] = _con_cache("premios_sec",
            lambda: AnalizadorPremiosSecundarios(sorteos_completos).calcular_scores())
        self._marcar(estado, ["Premios Secundarios"], "completado")

        # ── SARIMA (16) ──
        self._marcar(estado, ["SARIMA Estacional"], "procesando")
        scores["sarima"] = _con_cache("sarima",
            lambda: AnalizadorSARIMA(hist).calcular_scores())
        self._marcar(estado, ["SARIMA Estacional"], "completado")

        # ── GRU (13) ──
        self._marcar(estado, ["GRU"], "procesando")
        scores["gru"] = _con_cache("gru",
            lambda: AnalizadorGRU(hist).calcular_scores())
        self._marcar(estado, ["GRU"], "completado")
        await asyncio.sleep(0.01)

        # ── Información Mutua (14) ──
        self._marcar(estado, ["Información Mutua"], "procesando")
        scores["info_mutua"] = _con_cache("info_mutua",
            lambda: AnalizadorInformacionMutua(hist).calcular_scores())
        self._marcar(estado, ["Información Mutua"], "completado")

        # ── CMI Tríos (17) ──
        self._marcar(estado, ["Info. Mutua Condicional"], "procesando")
        scores["cmi"] = _con_cache("cmi",
            lambda: AnalizadorIMCondicional(hist).calcular_scores())
        self._marcar(estado, ["Info. Mutua Condicional"], "completado")

        # ── Features Estructurales (18) ──
        self._marcar(estado, ["Features Estructurales"], "procesando")
        scores["estructural"] = _con_cache("estructural",
            lambda: AnalizadorFeaturesEstructurales(hist).calcular_scores())
        self._marcar(estado, ["Features Estructurales"], "completado")
        await asyncio.sleep(0.01)

        # ── Bi-LSTM (19) ──
        self._marcar(estado, ["Bi-LSTM"], "procesando")
        scores["bilstm"] = _con_cache("bilstm",
            lambda: AnalizadorBiLSTM(hist).calcular_scores())
        self._marcar(estado, ["Bi-LSTM"], "completado")

        # ── Posición Ordinal (20) ──
        self._marcar(estado, ["Posición Ordinal"], "procesando")
        scores["posicion"] = _con_cache("posicion",
            lambda: AnalizadorPosicionOrdinal(hist).calcular_scores())
        self._marcar(estado, ["Posición Ordinal"], "completado")

        # ── Complementario/Reintegro (21) ──
        self._marcar(estado, ["Complementario/Reintegro"], "procesando")
        scores["comp_rei"] = _con_cache("comp_rei",
            lambda: AnalizadorComplementarioReintegro(sorteos_completos).calcular_scores())
        self._marcar(estado, ["Complementario/Reintegro"], "completado")
        await asyncio.sleep(0.01)

        # ── HMM (22) ──
        self._marcar(estado, ["HMM"], "procesando")
        scores["hmm"] = _con_cache("hmm",
            lambda: AnalizadorHMM(hist).calcular_scores())
        self._marcar(estado, ["HMM"], "completado")

        # ── Entropía de Permutación (23) ──
        self._marcar(estado, ["Entropía Permutación"], "procesando")
        scores["entropia_perm"] = _con_cache("entropia_perm",
            lambda: ReguladorEntropiaPermutacion(hist).calcular_scores())
        self._marcar(estado, ["Entropía Permutación"], "completado")

        # ── Progresiones Aritméticas (28) ──
        self._marcar(estado, ["Progresiones"], "procesando")
        scores["progresiones"] = _con_cache("progresiones",
            lambda: AnalizadorProgresionesAritmeticas(hist).calcular_scores())
        self._marcar(estado, ["Progresiones"], "completado")
        await asyncio.sleep(0.01)

        # ── Test Runs (29) ──
        self._marcar(estado, ["Test Runs"], "procesando")
        scores["runs"] = _con_cache("runs",
            lambda: AnalizadorTestRuns(hist).calcular_scores())
        self._marcar(estado, ["Test Runs"], "completado")

        # ── Simetría Especular (31) ──
        self._marcar(estado, ["Simetría Especular"], "procesando")
        scores["simetria"] = _con_cache("simetria",
            lambda: AnalizadorSimetriaEspecular(hist).calcular_scores())
        self._marcar(estado, ["Simetría Especular"], "completado")

        # ── Hurst (32) ──
        self._marcar(estado, ["Coef. Hurst"], "procesando")
        scores["hurst"] = _con_cache("hurst",
            lambda: AnalizadorHurst(hist).calcular_scores())
        self._marcar(estado, ["Coef. Hurst"], "completado")

        # ── PACF (43) ──
        self._marcar(estado, ["PACF"], "procesando")
        scores["pacf"] = _con_cache("pacf",
            lambda: AnalizadorPACF(hist).calcular_scores())
        self._marcar(estado, ["PACF"], "completado")

        # ── LNN/CfC (76) ──
        self._marcar(estado, ["LNN/CfC"], "procesando")
        scores["lnn"] = _con_cache("lnn",
            lambda: AnalizadorLNN(hist).calcular_scores())
        self._marcar(estado, ["LNN/CfC"], "completado")

        # ── TDA v2 (77) ──
        self._marcar(estado, ["TDA v2"], "procesando")
        scores["tda_v2"] = _con_cache("tda_v2",
            lambda: AnalizadorTDAv2(hist).calcular_scores())
        self._marcar(estado, ["TDA v2"], "completado")
        await asyncio.sleep(0.01)

        # ── SAX + Motivos (78) ──
        self._marcar(estado, ["SAX Motivos"], "procesando")
        scores["sax"] = _con_cache("sax",
            lambda: AnalizadorSAX(hist).calcular_scores())
        self._marcar(estado, ["SAX Motivos"], "completado")

        # ── MDL (79) ──
        self._marcar(estado, ["MDL"], "procesando")
        scores["mdl"] = _con_cache("mdl",
            lambda: ArbitroMDL(hist).calcular_scores())
        self._marcar(estado, ["MDL"], "completado")

        # ── DWT Wavelet (80) ──
        self._marcar(estado, ["DWT Wavelet"], "procesando")
        scores["dwt"] = _con_cache("dwt",
            lambda: AnalizadorDWT(hist).calcular_scores())
        self._marcar(estado, ["DWT Wavelet"], "completado")
        await asyncio.sleep(0.01)

        # ── GAT Grafo (82) ──
        self._marcar(estado, ["GAT Grafo"], "procesando")
        scores["gat"] = _con_cache("gat",
            lambda: AnalizadorGAT(hist).calcular_scores())
        self._marcar(estado, ["GAT Grafo"], "completado")

        # ── MaxEnt (83) ──
        self._marcar(estado, ["MaxEnt"], "procesando")
        scores["maxent"] = _con_cache("maxent",
            lambda: AnalizadorMaxEnt(hist).calcular_scores())
        self._marcar(estado, ["MaxEnt"], "completado")

        # ── N-BEATS (85) ──
        self._marcar(estado, ["N-BEATS"], "procesando")
        scores["nbeats"] = _con_cache("nbeats",
            lambda: AnalizadorNBEATS(hist).calcular_scores())
        self._marcar(estado, ["N-BEATS"], "completado")
        await asyncio.sleep(0.01)

        # ── Cuantiles Extremos (86) ──
        self._marcar(estado, ["Cuantiles Extremos"], "procesando")
        scores["cuantiles"] = _con_cache("cuantiles",
            lambda: AnalizadorCuantilesExtremos(hist).calcular_scores())
        self._marcar(estado, ["Cuantiles Extremos"], "completado")

        # ── Curriculum Learning (87) ──
        self._marcar(estado, ["Curriculum Learning"], "procesando")
        scores["curriculum"] = _con_cache("curriculum",
            lambda: AnalizadorCurriculumLearning(hist).calcular_scores())
        self._marcar(estado, ["Curriculum Learning"], "completado")

        # ─────────── BLOQUE J — ÚLTIMAS MEJORAS ALTA PRIORIDAD ───────────

        # ── SSA (88) — Singular Spectrum Analysis ──
        self._marcar(estado, ["SSA"], "procesando")
        scores["ssa"] = _con_cache("ssa",
            lambda: AnalizadorSSA(hist).calcular_scores())
        self._marcar(estado, ["SSA"], "completado")

        # ── VMD (89) — Variational Mode Decomposition ──
        self._marcar(estado, ["VMD"], "procesando")
        scores["vmd"] = _con_cache("vmd",
            lambda: AnalizadorVMD(hist).calcular_scores())
        self._marcar(estado, ["VMD"], "completado")
        await asyncio.sleep(0.01)

        # ── BOCPD (90) — Bayesian Online Changepoint Detection ──
        self._marcar(estado, ["BOCPD"], "procesando")
        scores["bocpd"] = _con_cache("bocpd",
            lambda: DetectorBOCPD(hist).calcular_scores())
        self._marcar(estado, ["BOCPD"], "completado")

        # ── EMD (91) — Empirical Mode Decomposition ──
        self._marcar(estado, ["EMD"], "procesando")
        scores["emd"] = _con_cache("emd",
            lambda: AnalizadorEMD(hist).calcular_scores())
        self._marcar(estado, ["EMD"], "completado")
        await asyncio.sleep(0.01)

        # ── RETAIN (92) — Reverse Time Attention ──
        self._marcar(estado, ["RETAIN"], "procesando")
        scores["retain"] = _con_cache("retain",
            lambda: AnalizadorRETAIN(hist).calcular_scores())
        self._marcar(estado, ["RETAIN"], "completado")

        # ── Lomb-Scargle (93) ──
        self._marcar(estado, ["Lomb-Scargle"], "procesando")
        scores["lomb_scargle"] = _con_cache("lomb_scargle",
            lambda: AnalizadorLombScargle(hist).calcular_scores())
        self._marcar(estado, ["Lomb-Scargle"], "completado")

        # ═══════════════════════════════════════════════════════════════
        # BLOQUE K EXTENDIDO (17 mejoras 94-110) — añadidas en v7.0
        # ═══════════════════════════════════════════════════════════════

        # ── 94. NGRC — Next Gen Reservoir Computing ──
        self._marcar(estado, ["NGRC"], "procesando")
        scores["ngrc"] = _con_cache("ngrc",
            lambda: AnalizadorNGRC(hist).calcular_scores())
        self._marcar(estado, ["NGRC"], "completado")

        # ── 95. DMD / Koopman ──
        self._marcar(estado, ["DMD/Koopman"], "procesando")
        scores["dmd"] = _con_cache("dmd",
            lambda: AnalizadorDMDKoopman(hist).calcular_scores())
        self._marcar(estado, ["DMD/Koopman"], "completado")
        await asyncio.sleep(0.01)

        # ── 96. KAN simplificado ──
        self._marcar(estado, ["KAN"], "procesando")
        scores["kan"] = _con_cache("kan",
            lambda: AnalizadorKAN(hist).calcular_scores())
        self._marcar(estado, ["KAN"], "completado")

        # ── 97. DLinear / NLinear ──
        self._marcar(estado, ["DLinear/NLinear"], "procesando")
        scores["dlinear"] = _con_cache("dlinear",
            lambda: AnalizadorDLinear(hist).calcular_scores())
        self._marcar(estado, ["DLinear/NLinear"], "completado")

        # ── 98. SINDy lite ──
        self._marcar(estado, ["SINDy"], "procesando")
        scores["sindy"] = _con_cache("sindy",
            lambda: AnalizadorSINDy(hist).calcular_scores())
        self._marcar(estado, ["SINDy"], "completado")
        await asyncio.sleep(0.01)

        # ── 99. TSFresh features ──
        self._marcar(estado, ["TSFresh"], "procesando")
        scores["tsfresh"] = _con_cache("tsfresh",
            lambda: AnalizadorTSFresh(hist).calcular_scores())
        self._marcar(estado, ["TSFresh"], "completado")

        # ── 100. N-HiTS ──
        self._marcar(estado, ["N-HiTS"], "procesando")
        scores["nhits"] = _con_cache("nhits",
            lambda: AnalizadorNHiTS(hist).calcular_scores())
        self._marcar(estado, ["N-HiTS"], "completado")

        # ── 101. FITS ──
        self._marcar(estado, ["FITS"], "procesando")
        scores["fits"] = _con_cache("fits",
            lambda: AnalizadorFITS(hist).calcular_scores())
        self._marcar(estado, ["FITS"], "completado")
        await asyncio.sleep(0.01)

        # ── 102. TimeMixer ──
        self._marcar(estado, ["TimeMixer"], "procesando")
        scores["timemixer"] = _con_cache("timemixer",
            lambda: AnalizadorTimeMixer(hist).calcular_scores())
        self._marcar(estado, ["TimeMixer"], "completado")

        # ── 103. Modern Hopfield Network ──
        self._marcar(estado, ["Modern Hopfield"], "procesando")
        scores["hopfield"] = _con_cache("hopfield",
            lambda: AnalizadorModernHopfield(hist).calcular_scores())
        self._marcar(estado, ["Modern Hopfield"], "completado")

        # ── 104. Vine Copulas ──
        self._marcar(estado, ["Vine Copulas"], "procesando")
        scores["vine_copula"] = _con_cache("vine_copula",
            lambda: AnalizadorVineCopulas(hist).calcular_scores())
        self._marcar(estado, ["Vine Copulas"], "completado")
        await asyncio.sleep(0.01)

        # ── 105. MiniRocket ──
        self._marcar(estado, ["MiniRocket"], "procesando")
        scores["minirocket"] = _con_cache("minirocket",
            lambda: AnalizadorMiniRocket(hist).calcular_scores())
        self._marcar(estado, ["MiniRocket"], "completado")

        # ── 106. Visibility Graph ──
        self._marcar(estado, ["Visibility Graph"], "procesando")
        scores["visibility"] = _con_cache("visibility",
            lambda: AnalizadorVisibilityGraph(hist).calcular_scores())
        self._marcar(estado, ["Visibility Graph"], "completado")

        # ── 107. Association Rules ──
        self._marcar(estado, ["Association Rules"], "procesando")
        scores["assoc_rules"] = _con_cache("assoc_rules",
            lambda: AnalizadorAssociationRules(hist).calcular_scores())
        self._marcar(estado, ["Association Rules"], "completado")
        await asyncio.sleep(0.01)

        # ── 108. RBM — Restricted Boltzmann Machine ──
        self._marcar(estado, ["RBM"], "procesando")
        scores["rbm"] = _con_cache("rbm",
            lambda: AnalizadorRBM(hist).calcular_scores())
        self._marcar(estado, ["RBM"], "completado")

        # ── 109. SOM — Self-Organizing Map (Kohonen) ──
        self._marcar(estado, ["SOM Kohonen"], "procesando")
        scores["som"] = _con_cache("som",
            lambda: AnalizadorSOM(hist).calcular_scores())
        self._marcar(estado, ["SOM Kohonen"], "completado")

        # ── 110. HDC — Hyperdimensional Computing ──
        self._marcar(estado, ["HDC/VSA"], "procesando")
        scores["hdc"] = _con_cache("hdc",
            lambda: AnalizadorHDC(hist).calcular_scores())
        self._marcar(estado, ["HDC/VSA"], "completado")
        await asyncio.sleep(0.01)

        # ── FFT (mejora previa) ──
        self._marcar(estado, ["FFT Periodicidad"], "procesando")
        scores["fft"] = _con_cache("fft",
            lambda: AnalizadorFFT(hist).calcular_scores_fft())
        self._marcar(estado, ["FFT Periodicidad"], "completado")
        await asyncio.sleep(0.01)

        # ── Algoritmos del motor base (con caché) ──
        motor = MotorIA(self.sorteos_completos)
        motor.historico = hist

        for nombre_alg, nombre_cache, fn in [
            ("Entropía",             "entropia",    motor.capa1_entropia),
            ("Hot/Cold Bias",        "hot_cold",    motor.capa1_hot_cold_bias),
            ("Covarianza",           "covarianza",  motor.capa1_covarianza),
            ("LSTM",                 "lstm",        motor.capa2_lstm_simple),
            ("Transformer",          "transformer", motor.capa2_transformer_attention),
            ("Markov",               "markov",      motor.capa2_markov),
            ("Bayesiano",            "bayesiano",   motor.capa3_bayesiano),
            ("XGBoost",              "xgboost",     motor.capa3_xgboost_simple),
            ("Reinforcement Learning","rl",         lambda: motor.capa3_reinforcement_learning()),
            ("Monte Carlo",          "monte_carlo", lambda: motor.capa4_monte_carlo(50000)),
        ]:
            self._marcar(estado, [nombre_alg], "procesando")
            scores[nombre_cache] = _con_cache(nombre_cache, fn)
            self._marcar(estado, [nombre_alg], "completado")
            await asyncio.sleep(0.005)

        return scores

    # ══════════════════════════════════════════════════════════════════
    # CÁLCULO DE ALGORITMOS NIVEL 2 (CONDICIONALES)
    # ══════════════════════════════════════════════════════════════════
    async def _calcular_algoritmos_nivel2(
        self,
        hist: List[List[int]],
        diag: ResultadoDiagnostico,
        estado: Dict[str, str],
    ) -> Dict[str, Dict[int, float]]:
        """Calcula algoritmos condicionales según diagnóstico."""
        scores = {}

        def _con_cache(nombre: str, fn) -> Dict[int, float]:
            if self.cache.esta_valido(hist, nombre):
                return self.cache.obtener(nombre)
            r = fn()
            self.cache.guardar(hist, nombre, r)
            return r

        # ── TDA (37) ──
        if diag.activar_tda:
            self._marcar(estado, ["TDA Topológico"], "procesando")
            scores["tda"] = _con_cache("tda",
                lambda: AnalizadorTDA(hist).calcular_scores())
            self._marcar(estado, ["TDA Topológico"], "completado")
            await asyncio.sleep(0.02)

        # ── VAR (34) ──
        if diag.activar_var:
            self._marcar(estado, ["VAR Multivariante"], "procesando")
            scores["var"] = _con_cache("var",
                lambda: AnalizadorVAR(hist).calcular_scores())
            self._marcar(estado, ["VAR Multivariante"], "completado")
            await asyncio.sleep(0.02)

        # ── ESN (33) ──
        if diag.activar_esn:
            self._marcar(estado, ["Echo State Network"], "procesando")
            scores["esn"] = _con_cache("esn",
                lambda: AnalizadorESN(hist).calcular_scores())
            self._marcar(estado, ["Echo State Network"], "completado")
            await asyncio.sleep(0.02)

        # ── Cópulas (24) ──
        if diag.activar_copulas:
            self._marcar(estado, ["Cópulas Gaussianas"], "procesando")
            scores["copulas"] = _con_cache("copulas",
                lambda: AnalizadorCopulas(hist).calcular_scores())
            self._marcar(estado, ["Cópulas Gaussianas"], "completado")
            await asyncio.sleep(0.02)

        # ── Hawkes (40) ──
        if diag.activar_hawkes:
            self._marcar(estado, ["Proceso Hawkes"], "procesando")
            scores["hawkes"] = _con_cache("hawkes",
                lambda: AnalizadorHawkes(hist).calcular_scores())
            self._marcar(estado, ["Proceso Hawkes"], "completado")
            await asyncio.sleep(0.01)

        # ── Multifractal DFA (41) ──
        if diag.activar_multifractal:
            self._marcar(estado, ["Multifractal DFA"], "procesando")
            scores["multifractal"] = _con_cache("multifractal",
                lambda: AnalizadorMultifractalDFA(hist).calcular_scores())
            self._marcar(estado, ["Multifractal DFA"], "completado")
            await asyncio.sleep(0.01)

        # ── EVT (25) ──
        if diag.nivel_senal in ["alto", "medio"]:
            self._marcar(estado, ["EVT/GEV"], "procesando")
            scores["evt"] = _con_cache("evt",
                lambda: AnalizadorEVT(hist).calcular_scores())
            self._marcar(estado, ["EVT/GEV"], "completado")

        # ── Dirichlet (26) ──
        if diag.nivel_senal in ["alto", "medio"]:
            self._marcar(estado, ["Proceso Dirichlet"], "procesando")
            scores["dirichlet"] = _con_cache("dirichlet",
                lambda: AnalizadorDirichlet(hist).calcular_scores())
            self._marcar(estado, ["Proceso Dirichlet"], "completado")

        # ── MSE (27) ──
        if diag.nivel_senal in ["alto", "medio"]:
            self._marcar(estado, ["Multi-Scale Entropy"], "procesando")
            scores["mse"] = _con_cache("mse",
                lambda: AnalizadorMultiScaleEntropy(hist).calcular_scores())
            self._marcar(estado, ["Multi-Scale Entropy"], "completado")

        # ── Lyapunov (39) ──
        if diag.nivel_senal in ["alto", "medio"]:
            self._marcar(estado, ["Exponente Lyapunov"], "procesando")
            scores["lyapunov"] = _con_cache("lyapunov",
                lambda: AnalizadorLyapunov(hist).calcular_scores())
            self._marcar(estado, ["Exponente Lyapunov"], "completado")

        # ── Regresión Simbólica (38) ──
        if diag.activar_regresion_simbolica:
            self._marcar(estado, ["Regresión Simbólica"], "procesando")
            scores["reg_simbolica"] = _con_cache("reg_sim",
                lambda: AnalizadorRegresionSimbolica(hist).calcular_scores())
            self._marcar(estado, ["Regresión Simbólica"], "completado")

        n_activos = len(scores)
        if n_activos > 0:
            logger.info(f"Nivel 2: {n_activos} algoritmos adicionales activados")

        return scores

    # ══════════════════════════════════════════════════════════════════
    # CÁLCULO DE CONFIANZA v3
    # ══════════════════════════════════════════════════════════════════
    def _calcular_confianza_v3(
        self,
        combo: List[int],
        scores_stacking: Dict[int, float],
        objs_nsga2: tuple,
        metricas_wf: Dict,
        penalizacion: float,
    ) -> float:
        if not combo:
            return 1.0
        nums = sorted(combo)

        # Score stacking base
        score_base = sum(scores_stacking.get(n, 0) for n in nums) / max(len(nums), 1)

        # Bonus NSGA-II (4 objetivos)
        bonus_nsga2 = 0.0
        if objs_nsga2 and len(objs_nsga2) >= 4:
            f1, f2, f3, f4 = objs_nsga2[:4]
            bonus_nsga2 = f2*4.0 + f3*4.0 + f4*3.0  # hasta 11 pts

        # Bonus Walk-Forward validado
        bonus_wf = 0.0
        if metricas_wf:
            prec = sum(m.get("precision",0.15) for m in metricas_wf.values())
            prec /= max(len(metricas_wf), 1)
            bonus_wf = max(0.0, (prec - 0.15) * 60)

        # Bonus cobertura de decenas
        decenas = len(set((n-1)//10 for n in nums))
        bonus_dec = decenas * 1.2

        # Penalización popularidad
        penalizacion_total = penalizacion * 10

        confianza = (
            score_base * 72 +
            bonus_nsga2 +
            bonus_wf +
            bonus_dec -
            penalizacion_total
        )
        return min(99.9, max(1.0, confianza))

    # ══════════════════════════════════════════════════════════════════
    # FORMATEO FINAL
    # ══════════════════════════════════════════════════════════════════
    def _formatear_combinaciones(
        self,
        combinaciones: List[dict],
        scores_por_alg: Dict[str, Dict[int, float]],
    ) -> List[dict]:
        from datetime import datetime, timezone
        resultado = []
        for c in combinaciones:
            resultado.append({
                "numeros": sorted(c["combo"]),
                "indice_confianza": round(c["confianza"], 2),
                "ic_inferior": c.get("ic_inferior", 0.0),
                "ic_superior": c.get("ic_superior", 100.0),
                "fecha_generacion": datetime.now(timezone.utc).isoformat(),
                "pesos_por_algoritmo": {
                    alg: round(self.stacking.meta_pesos.get(alg, 0), 4)
                    for alg in list(self.stacking.meta_pesos.keys())[:10]
                },
                "objetivos_nsga2": list(c.get("objs", [])),
                "score_pareto": round(c.get("score_pareto", 0.0), 4),
                "penalizacion": round(c.get("penalizacion", 0.0), 4),
            })
        return resultado

    # ══════════════════════════════════════════════════════════════════
    # UTILIDADES
    # ══════════════════════════════════════════════════════════════════
    @staticmethod
    def _marcar(estado: Dict, nombres: List[str], valor: str):
        for n in nombres:
            estado[n] = valor

    def _scores_base(self, nombre: str, hist: List[List[int]]) -> Dict[int, float]:
        """Helper para Walk-Forward con algoritmos base."""
        motor = MotorIA([{"numeros": s} for s in hist])
        motor.historico = hist
        fns = {
            "entropia": motor.capa1_entropia,
            "lstm": motor.capa2_lstm_simple,
            "bayesiano": motor.capa3_bayesiano,
            "xgboost": motor.capa3_xgboost_simple,
        }
        return fns.get(nombre, motor.capa1_entropia)()

    def actualizar_con_resultado_real(
        self,
        scores_usados: Dict[str, Dict[int, float]],
        combinaciones: List[List[int]],
        resultado_real: List[int],
    ):
        """Actualiza el stacking y el calibrador con el resultado real."""
        for combo in combinaciones:
            self.stacking.registrar_prediccion(
                scores_usados, combo, resultado_real
            )
        self.cache.invalidar()
        logger.info("Pipeline: stacking y caché actualizados con resultado real")


# ═══════════════════════════════════════════════════════════════════════
# ALIAS DE COMPATIBILIDAD HACIA ATRÁS
# Mantiene PipelineV3 funcionando para código que no haya migrado a v4.
# ═══════════════════════════════════════════════════════════════════════
PipelineV3 = PipelineV4

