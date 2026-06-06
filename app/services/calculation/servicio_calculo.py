"""
Servicio de cálculo: orquesta la ejecución del pipeline para un trabajo.

Cambios respecto a Sesión 1:
  - Usa RepoTrabajos (Protocol async), no TrabajosRepo concreto.
  - Guarda estado a través de repo.guardar() en cada cambio importante
    (no muta directamente). Esto activa la persistencia write-through si
    el repo es Oracle.
  - Throttling del callback: para no saturar la BD con un UPDATE por cada
    micro-tick de progreso, se guardan deltas relevantes (>1% progreso o
    cambio de estado_algoritmos).
"""

import logging
import time
from typing import Optional

from app.services.calculation.trabajos_repo import RepoTrabajos, Trabajo
from app.services.pipeline.pipeline_v4 import PipelineV4
from app.infrastructure.database import BaseDatos

logger = logging.getLogger(__name__)


class ServicioCalculo:
    """Orquesta un cálculo de combinaciones."""

    def __init__(
        self,
        repo: RepoTrabajos,
        bd: Optional[type] = None,
    ):
        self._repo = repo
        self._bd = bd or BaseDatos

    async def ejecutar(
        self,
        trabajo_id: str,
        cantidad: int,
        presupuesto_eur: float = 10.0,
        bote_acumulado_eur: float = 600_000.0,
        loteria: str = "bonoloto",
    ) -> None:
        """Ejecuta el pipeline completo. Actualiza el estado vía repo."""
        trabajo = await self._repo.obtener(trabajo_id)
        if trabajo is None:
            logger.warning("Trabajo %s no existe — abortando", trabajo_id)
            return

        trabajo.estado = "calculando"
        trabajo.progreso = 0.0
        await self._repo.guardar(trabajo)

        from app.infrastructure.observabilidad import metricas
        metricas.registrar_inicio()

        # Throttling del callback: persistir a BD solo si el delta es
        # significativo (>= 1% de progreso o cambio de iteración o de
        # estado_algoritmos). El progreso en RAM siempre se actualiza
        # (el SSE lo lee de RAM/cache directamente).
        ultimo_persistido = {"progreso": 0.0, "iteracion": 0,
                              "estado_algos_hash": None}
        ultima_persistencia_t = time.time()
        UMBRAL_PROGRESO = 0.01
        INTERVALO_MIN_SEG = 2.0  # como mínimo cada 2s aunque haya cambios

        async def callback(estado_algoritmos, progreso, confianza, iteracion, convergiendo):
            """Callback que el pipeline invoca para reportar progreso."""
            # Actualización in-memory siempre (para SSE/polling lectura rápida)
            trabajo.estado_algoritmos = dict(estado_algoritmos) if estado_algoritmos else {}
            trabajo.progreso = min(0.99, progreso)
            trabajo.indice_confianza = confianza
            trabajo.iteracion = iteracion
            trabajo.convergiendo = convergiendo

            # Decidir si persistimos
            nonlocal ultima_persistencia_t
            ahora = time.time()
            delta_progreso = trabajo.progreso - ultimo_persistido["progreso"]
            cambio_iter = iteracion != ultimo_persistido["iteracion"]
            algos_hash = hash(tuple(sorted(trabajo.estado_algoritmos.items())))
            cambio_algos = algos_hash != ultimo_persistido["estado_algos_hash"]

            debe_persistir = (
                delta_progreso >= UMBRAL_PROGRESO or
                cambio_iter or
                cambio_algos or
                (ahora - ultima_persistencia_t) >= INTERVALO_MIN_SEG * 5
            )
            # Throttle hard: como mínimo INTERVALO_MIN_SEG entre persistencias
            if debe_persistir and (ahora - ultima_persistencia_t) >= INTERVALO_MIN_SEG:
                try:
                    await self._repo.guardar(trabajo)
                    ultimo_persistido["progreso"] = trabajo.progreso
                    ultimo_persistido["iteracion"] = iteracion
                    ultimo_persistido["estado_algos_hash"] = algos_hash
                    ultima_persistencia_t = ahora
                except Exception as e:
                    # No-fatal: cache local sigue actualizada
                    logger.debug("Persistencia parcial falló: %s", e)

        try:
            # Usar toda la memoria disponible para máxima base estadística.
            # Tope alto (5000) para no degradar rendimiento si el histórico
            # creciera mucho; Bonoloto tiene ~varios miles de sorteos desde 1988.
            sorteos = await self._bd.obtener_sorteos(limite=5000)
            if not sorteos:
                from app.domain.fixtures import sorteos_simulados
                sorteos = sorteos_simulados()
                logger.warning(
                    "BD vacía. Trabajo %s usando sorteos simulados.", trabajo_id
                )
            else:
                logger.info(
                    "Trabajo %s usando %d sorteos de la memoria.",
                    trabajo_id, len(sorteos),
                )

            historico = [s["numeros"] for s in sorteos]

            pipeline = PipelineV4(
                historico=historico,
                sorteos_completos=sorteos,
                callback_progreso=callback,
                presupuesto_usuario_eur=presupuesto_eur,
                bote_acumulado_eur=bote_acumulado_eur,
                loteria=loteria,
            )

            resultado = await pipeline.ejecutar(cantidad)

            trabajo.estado = "completado"
            trabajo.combinaciones = resultado.combinaciones
            trabajo.progreso = 1.0
            # mejoras_detalle es un Dict descriptivo; mejoras_activas espera
            # una lista de strings legibles (contrato con el frontend). Bug #132.
            trabajo.mejoras_activas = self._formatear_mejoras(resultado.mejoras_detalle)
            trabajo.n_algoritmos = resultado.n_algoritmos_activos
            trabajo.tiempo_segundos = round(resultado.tiempo_total_seg, 1)
            trabajo.bloque_l_sistema = resultado.bloque_l_sistema_reducido
            trabajo.bloque_l_apuestas = resultado.bloque_l_apuestas_garantizadas
            trabajo.bloque_l_coste_eur = resultado.bloque_l_coste_total_eur
            trabajo.bloque_l_recomendacion = resultado.bloque_l_recomendacion
            trabajo.bloque_l_roi = resultado.bloque_l_analisis_roi
            trabajo.bloque_l_confianza = resultado.bloque_l_confianza_agregada
            trabajo.cobertura_garantizada = getattr(
                resultado, "cobertura_garantizada", None
            )
            trabajo.bloque_l_estrategia_completa = resultado.bloque_l_estrategia
            # Apuestas múltiples (7-11 números) desde las puntuaciones finales.
            try:
                from app.domain.apuesta_multiple import calcular_apuestas_multiples
                trabajo.apuestas_multiples = calcular_apuestas_multiples(
                    getattr(resultado, "scores_finales", {}) or {}
                )
            except Exception as e:
                logger.warning("No se pudieron calcular apuestas múltiples: %s", e)
                trabajo.apuestas_multiples = None
            trabajo.completado = time.time()

            await self._repo.guardar(trabajo)

            metricas.registrar_completado(resultado.tiempo_total_seg)

            # Registrar las combinaciones como PREDICCIONES para el backtest
            # honesto del dashboard. Esto permite comparar, tras el sorteo,
            # si el sistema acertó más que el azar.
            await self._registrar_predicciones_honestidad(
                trabajo_id, resultado.combinaciones,
            )

            logger.info(
                "Trabajo %s completado: %d combos + %d apuestas BL | "
                "conf %.2f%% | %d algoritmos | %.0fs",
                trabajo_id,
                len(resultado.combinaciones),
                len(resultado.bloque_l_apuestas_garantizadas),
                resultado.confianza_maxima,
                resultado.n_algoritmos_activos,
                resultado.tiempo_total_seg,
            )

        except Exception as e:
            logger.error("Error en trabajo %s: %s", trabajo_id, e, exc_info=True)
            trabajo.estado = "error"
            trabajo.mensaje = str(e)
            from app.infrastructure.observabilidad import metricas
            metricas.registrar_error()
            try:
                await self._repo.guardar(trabajo)
            except Exception:
                pass  # ya estamos en error path, no escalar

    @staticmethod
    def _formatear_mejoras(mejoras_detalle) -> list:
        """
        Convierte el dict de mejoras_detalle del pipeline en una lista de
        strings legibles para el frontend (que espera List[str]). Bug #132.
        """
        if isinstance(mejoras_detalle, list):
            return mejoras_detalle  # ya es lista
        if not isinstance(mejoras_detalle, dict):
            return []
        lista = []
        d = mejoras_detalle
        if d.get("isolation_forest"):
            lista.append(f"Isolation Forest: {d['isolation_forest']}")
        if d.get("nivel_senal"):
            lista.append(f"Señal estadística: {d['nivel_senal']}")
        if d.get("n_algoritmos"):
            lista.append(f"{d['n_algoritmos']} algoritmos activos")
        if d.get("stacking_lider"):
            lista.append(f"Stacking líder: {d['stacking_lider']}")
        if d.get("bloque_l_sistema"):
            lista.append(f"Bloque L: sistema {d['bloque_l_sistema']}")
        if d.get("total_tecnicas"):
            lista.append(f"{d['total_tecnicas']} técnicas totales")
        return lista

    async def _registrar_predicciones_honestidad(
        self, trabajo_id: str, combinaciones: list,
    ) -> None:
        """
        Registra las combinaciones generadas como predicciones en el servicio
        de honestidad, para que el backtest pueda evaluarlas tras el sorteo.

        No es crítico: si falla, el cálculo ya está completo y guardado. Solo
        afecta al dashboard de honestidad.
        """
        try:
            from app.services.honestidad.servicio_honestidad import (
                get_servicio_honestidad,
            )
            servicio = get_servicio_honestidad()
            for combo in combinaciones:
                # combo puede ser dict {'numeros': [...], 'indice_confianza': X}
                if isinstance(combo, dict):
                    numeros = combo.get("numeros") or combo.get("combinacion")
                    confianza = combo.get("indice_confianza", 0.0)
                else:
                    numeros = combo
                    confianza = 0.0
                if numeros and len(numeros) == 6:
                    await servicio.registrar_prediccion(
                        trabajo_id=trabajo_id,
                        numeros=numeros,
                        confianza=confianza,
                    )
        except Exception as e:
            logger.debug("No pude registrar predicciones para honestidad: %s", e)
