"""
Servicio del Dashboard de Honestidad.

Registra:
  - Apuestas reales del usuario (lo que de verdad jugó y gastó)
  - Predicciones del sistema (combinaciones generadas ANTES del sorteo)

Calcula KPIs honestos:
  - P&L: total apostado, total ganado, balance neto
  - EV teórico vs realidad
  - Backtest del sistema (¿supera al azar? casi seguro que no)
  - Coste de oportunidad

Diseño: repo abstraído (memoria o BD). Si no hay BD, funciona in-memory
(se pierde al reiniciar, pero permite usar el dashboard en dev).

NOTA: este servicio existe para mostrar la VERDAD al usuario, no para
optimizar nada. Es el cumplimiento del compromiso de transparencia.
"""

import logging
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Optional, Dict, Any

from app.domain import honestidad_math as hm
from app.infrastructure.database import BaseDatos

logger = logging.getLogger(__name__)


@dataclass
class Apuesta:
    """Una apuesta real registrada por el usuario."""
    id: str
    fecha: str                    # ISO date de cuándo se hizo
    numeros: List[int]
    coste_eur: float = 0.5
    origen: str = "manual"        # 'manual' | 'sistema' | 'bloque_l'
    sorteo_fecha: Optional[str] = None
    aciertos: Optional[int] = None
    premio_eur: Optional[float] = None
    evaluada: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Prediccion:
    """Una predicción del sistema, registrada antes del sorteo."""
    id: str
    trabajo_id: str
    fecha_generada: str
    numeros: List[int]
    confianza: float
    sorteo_fecha: Optional[str] = None
    aciertos: Optional[int] = None
    evaluada: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class EstadisticasHonestidad:
    """Snapshot completo de los KPIs de honestidad."""
    # P&L
    total_apostado_eur: float
    total_ganado_eur: float
    balance_neto_eur: float
    n_apuestas: int
    n_apuestas_evaluadas: int
    # EV
    ev_teorico_acumulado_eur: float   # lo que se esperaba perder
    diferencia_real_vs_teorico_eur: float
    # Aciertos
    aciertos_totales: int
    aciertos_medios: float
    tasa_premio_real: float           # fracción de apuestas con premio
    # Backtest del sistema
    backtest: Dict[str, Any]
    # Coste oportunidad
    coste_oportunidad: Dict[str, float]
    # EV actual (informativo)
    ev_apuesta_actual: Dict[str, Any]

    def to_dict(self) -> dict:
        return asdict(self)


class ServicioHonestidad:
    """
    Gestiona el registro y cálculo del dashboard de honestidad.

    En esta sesión usa repo in-memory + persistencia opcional a BD.
    """

    def __init__(self):
        # Cache in-memory (también es el almacén si no hay BD)
        self._apuestas: Dict[str, Apuesta] = {}
        self._predicciones: Dict[str, Prediccion] = {}
        self._fecha_primera_apuesta: Optional[datetime] = None

    # ─────────────────────────────────────────────
    # REGISTRO
    # ─────────────────────────────────────────────

    async def registrar_apuesta(
        self,
        numeros: List[int],
        coste_eur: float = 0.5,
        origen: str = "manual",
        fecha: Optional[str] = None,
    ) -> Apuesta:
        """Registra una apuesta real que el usuario va a jugar."""
        ap = Apuesta(
            id=str(uuid.uuid4()),
            fecha=fecha or datetime.now().isoformat(),
            numeros=sorted(numeros),
            coste_eur=coste_eur,
            origen=origen,
        )
        self._apuestas[ap.id] = ap
        self._actualizar_fecha_primera(ap.fecha)
        await self._persistir_apuesta(ap)
        return ap

    async def registrar_prediccion(
        self,
        trabajo_id: str,
        numeros: List[int],
        confianza: float,
    ) -> Prediccion:
        """Registra una predicción del sistema (antes del sorteo)."""
        pred = Prediccion(
            id=str(uuid.uuid4()),
            trabajo_id=trabajo_id,
            fecha_generada=datetime.now().isoformat(),
            numeros=sorted(numeros),
            confianza=confianza,
        )
        self._predicciones[pred.id] = pred
        await self._persistir_prediccion(pred)
        return pred

    async def evaluar_sorteo(
        self,
        sorteo_fecha: str,
        numeros_ganadores: List[int],
        tabla_premios: Optional[hm.TablaPremios] = None,
        complementario: Optional[int] = None,
    ) -> Dict[str, int]:
        """
        Evalúa todas las apuestas y predicciones pendientes contra el
        resultado de un sorteo. Calcula aciertos y premios.

        Si se pasa `complementario`, distingue la 2ª categoría (5+C), que
        paga más que un 5 simple en Bonoloto.

        Devuelve cuántas apuestas y predicciones se evaluaron.
        """
        ganadores = set(numeros_ganadores)
        tabla = tabla_premios or hm.TablaPremios()

        n_ap = 0
        for ap in self._apuestas.values():
            if ap.evaluada:
                continue
            aciertos = len(set(ap.numeros) & ganadores)
            # 5+C: 5 aciertos y además el complementario está en la apuesta
            tiene_comp = (
                complementario is not None
                and aciertos == 5
                and complementario in set(ap.numeros)
            )
            ap.aciertos = aciertos
            ap.premio_eur = tabla.premio_para(aciertos, mas_complementario=tiene_comp)
            ap.sorteo_fecha = sorteo_fecha
            ap.evaluada = True
            await self._persistir_apuesta(ap)
            n_ap += 1

        n_pred = 0
        for pred in self._predicciones.values():
            if pred.evaluada:
                continue
            aciertos = len(set(pred.numeros) & ganadores)
            pred.aciertos = aciertos
            pred.sorteo_fecha = sorteo_fecha
            pred.evaluada = True
            await self._persistir_prediccion(pred)
            n_pred += 1

        logger.info(
            "Sorteo %s evaluado: %d apuestas, %d predicciones",
            sorteo_fecha, n_ap, n_pred,
        )
        return {"apuestas_evaluadas": n_ap, "predicciones_evaluadas": n_pred}

    # ─────────────────────────────────────────────
    # KPIs
    # ─────────────────────────────────────────────

    async def calcular_estadisticas(
        self,
        bote_actual_eur: float = 400_000.0,
    ) -> EstadisticasHonestidad:
        """Calcula el snapshot completo de KPIs honestos."""
        await self._cargar_desde_bd_si_vacio()

        apuestas = list(self._apuestas.values())
        evaluadas = [a for a in apuestas if a.evaluada]

        total_apostado = sum(a.coste_eur for a in apuestas)
        total_ganado = sum((a.premio_eur or 0.0) for a in evaluadas)
        balance = total_ganado - total_apostado

        # EV teórico: lo que se esperaba perder dado lo apostado
        ev_analisis = hm.analizar_ev(hm.TablaPremios())
        # ev_por_apuesta es negativo; multiplicado por nº de apuestas
        n_apuestas = len(apuestas)
        ev_teorico_acumulado = ev_analisis.ev_por_apuesta_eur * n_apuestas
        diferencia = balance - ev_teorico_acumulado

        # Aciertos
        aciertos_totales = sum((a.aciertos or 0) for a in evaluadas)
        aciertos_medios = (
            aciertos_totales / len(evaluadas) if evaluadas else 0.0
        )
        con_premio = sum(
            1 for a in evaluadas if (a.aciertos or 0) >= 3
        )
        tasa_premio = con_premio / len(evaluadas) if evaluadas else 0.0

        # Backtest del sistema (basado en predicciones evaluadas)
        preds_eval = [
            p for p in self._predicciones.values() if p.evaluada
        ]
        aciertos_pred = [p.aciertos or 0 for p in preds_eval]
        sorteos_distintos = len(
            {p.sorteo_fecha for p in preds_eval if p.sorteo_fecha}
        )
        bt = hm.backtest_sistema(aciertos_pred, n_sorteos=sorteos_distintos)

        # Coste oportunidad
        meses = self._meses_desde_primera_apuesta()
        co = hm.coste_oportunidad(total_apostado, meses)

        # EV de la apuesta actual con bote
        ev_actual = hm.ev_con_bote(bote_actual_eur)

        return EstadisticasHonestidad(
            total_apostado_eur=round(total_apostado, 2),
            total_ganado_eur=round(total_ganado, 2),
            balance_neto_eur=round(balance, 2),
            n_apuestas=n_apuestas,
            n_apuestas_evaluadas=len(evaluadas),
            ev_teorico_acumulado_eur=round(ev_teorico_acumulado, 2),
            diferencia_real_vs_teorico_eur=round(diferencia, 2),
            aciertos_totales=aciertos_totales,
            aciertos_medios=round(aciertos_medios, 4),
            tasa_premio_real=round(tasa_premio, 4),
            backtest={
                "n_predicciones": bt.n_predicciones,
                "n_sorteos": bt.n_sorteos_evaluados,
                "aciertos_medios_sistema": round(bt.aciertos_medios_sistema, 4),
                "aciertos_esperados_azar": round(bt.aciertos_esperados_azar, 4),
                "diferencia": round(bt.diferencia, 4),
                "premios_conseguidos": bt.premios_conseguidos,
                "premios_esperados_azar": round(bt.premios_esperados_azar, 2),
                "veredicto": bt.veredicto,
            },
            coste_oportunidad={
                "valor_si_invertido_eur":
                    round(co["valor_si_invertido_eur"], 2),
                "ganancia_alternativa_eur":
                    round(co["ganancia_alternativa_eur"], 2),
                "rendimiento_usado": co["rendimiento_usado"],
                "meses": round(meses, 1),
            },
            ev_apuesta_actual={
                "ev_eur": round(ev_actual.ev_por_apuesta_eur, 4),
                "ev_porcentaje": round(ev_actual.ev_porcentaje * 100, 1),
                "es_favorable": ev_actual.es_favorable,
                "bote_usado": bote_actual_eur,
            },
        )

    # ─────────────────────────────────────────────
    # HELPERS
    # ─────────────────────────────────────────────

    def _actualizar_fecha_primera(self, fecha_iso: str):
        try:
            f = datetime.fromisoformat(fecha_iso)
            if self._fecha_primera_apuesta is None or f < self._fecha_primera_apuesta:
                self._fecha_primera_apuesta = f
        except (ValueError, TypeError):
            pass

    def _meses_desde_primera_apuesta(self) -> float:
        if self._fecha_primera_apuesta is None:
            return 0.0
        delta = datetime.now() - self._fecha_primera_apuesta
        return max(0.0, delta.days / 30.44)

    async def _persistir_apuesta(self, ap: Apuesta):
        if BaseDatos._pool is None:
            return
        try:
            await BaseDatos.apuesta_upsert(ap.to_dict())
        except Exception as e:
            logger.debug("No pude persistir apuesta: %s", e)

    async def _persistir_prediccion(self, pred: Prediccion):
        if BaseDatos._pool is None:
            return
        try:
            await BaseDatos.prediccion_upsert(pred.to_dict())
        except Exception as e:
            logger.debug("No pude persistir predicción: %s", e)

    async def _cargar_desde_bd_si_vacio(self):
        """Carga apuestas/predicciones de BD si el cache está vacío."""
        if BaseDatos._pool is None:
            return
        if self._apuestas or self._predicciones:
            return  # ya hay datos en cache
        try:
            apuestas = await BaseDatos.apuestas_listar()
            for d in apuestas:
                ap = Apuesta(
                    id=d["id"], fecha=d["fecha"], numeros=d["numeros"],
                    coste_eur=d["coste_eur"], origen=d.get("origen", "manual"),
                    sorteo_fecha=d.get("sorteo_fecha"),
                    aciertos=d.get("aciertos"), premio_eur=d.get("premio_eur"),
                    evaluada=bool(d.get("evaluada", 0)),
                )
                self._apuestas[ap.id] = ap
                self._actualizar_fecha_primera(ap.fecha)
            preds = await BaseDatos.predicciones_listar()
            for d in preds:
                pred = Prediccion(
                    id=d["id"], trabajo_id=d.get("trabajo_id", ""),
                    fecha_generada=d["fecha_generada"], numeros=d["numeros"],
                    confianza=d.get("confianza", 0.0),
                    sorteo_fecha=d.get("sorteo_fecha"),
                    aciertos=d.get("aciertos"),
                    evaluada=bool(d.get("evaluada", 0)),
                )
                self._predicciones[pred.id] = pred
        except Exception as e:
            logger.warning("Error cargando honestidad desde BD: %s", e)


# Singleton
_servicio_global: Optional[ServicioHonestidad] = None


def get_servicio_honestidad() -> ServicioHonestidad:
    global _servicio_global
    if _servicio_global is None:
        _servicio_global = ServicioHonestidad()
    return _servicio_global


def reset_servicio_honestidad():
    """Para tests."""
    global _servicio_global
    _servicio_global = None
