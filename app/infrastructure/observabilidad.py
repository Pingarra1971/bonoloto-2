"""
Observabilidad: métricas operativas y healthcheck profundo.

No usa Prometheus (otra dependencia de infra) sino un endpoint JSON simple
con las métricas clave, suficiente para uso personal. Si más adelante quieres
Prometheus, este módulo es el punto donde añadir el exporter.
"""

import time
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class Metricas:
    """Contadores operativos en memoria."""
    inicio: float = field(default_factory=time.time)
    calculos_iniciados: int = 0
    calculos_completados: int = 0
    calculos_error: int = 0
    peticiones_totales: int = 0
    tiempo_calculo_total_seg: float = 0.0

    def registrar_inicio(self):
        self.calculos_iniciados += 1

    def registrar_completado(self, tiempo_seg: float):
        self.calculos_completados += 1
        self.tiempo_calculo_total_seg += tiempo_seg

    def registrar_error(self):
        self.calculos_error += 1

    def registrar_peticion(self):
        self.peticiones_totales += 1

    @property
    def uptime_seg(self) -> float:
        return time.time() - self.inicio

    @property
    def tiempo_medio_calculo_seg(self) -> float:
        if self.calculos_completados == 0:
            return 0.0
        return self.tiempo_calculo_total_seg / self.calculos_completados

    @property
    def tasa_exito(self) -> float:
        total = self.calculos_completados + self.calculos_error
        if total == 0:
            return 1.0
        return self.calculos_completados / total

    def snapshot(self) -> Dict:
        return {
            "uptime_segundos": round(self.uptime_seg, 1),
            "calculos_iniciados": self.calculos_iniciados,
            "calculos_completados": self.calculos_completados,
            "calculos_error": self.calculos_error,
            "peticiones_totales": self.peticiones_totales,
            "tiempo_medio_calculo_seg": round(self.tiempo_medio_calculo_seg, 1),
            "tasa_exito": round(self.tasa_exito, 4),
        }


# Singleton global de métricas
metricas = Metricas()
