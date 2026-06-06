"""
Servicio de memoria de sorteos históricos.

Mantiene la base de datos de sorteos de Bonoloto que alimenta a los
algoritmos estadísticos. Cuanto más completo el histórico, más precisas son
las mediciones (frecuencias, sumas, gaps...) — aunque, por la naturaleza
independiente del sorteo, más histórico NO aumenta la probabilidad de acertar
el siguiente. La memoria mejora la calidad de las estadísticas, no el poder
predictivo (que es nulo por diseño del sorteo).

Responsabilidades:
  - Backfill: cargar todo el histórico disponible de una fuente.
  - Actualización incremental: añadir cada sorteo nuevo idempotentemente.
  - Lectura: servir el histórico (completo o recortado) a los algoritmos.
"""

import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class ServicioMemoriaSorteos:
    """Orquesta la persistencia y actualización del histórico de sorteos."""

    def __init__(self, base_datos, loterias_api=None):
        """
        Args:
            base_datos: clase/instancia BaseDatos (acceso a tabla sorteos).
            loterias_api: fuente opcional para obtener sorteos nuevos/históricos.
        """
        self._bd = base_datos
        self._api = loterias_api

    async def estado(self) -> Dict:
        """Resumen del estado de la memoria."""
        n = await self._bd.contar_sorteos()
        ultima = await self._bd.fecha_ultimo_sorteo()
        return {
            "sorteos_almacenados": n,
            "fecha_ultimo_sorteo": ultima.isoformat() if ultima else None,
            "memoria_activa": n > 0,
        }

    async def backfill_completo(self, sorteos: List[Dict]) -> int:
        """
        Carga masiva del histórico completo (idempotente). Se usa para
        sembrar la memoria con todos los sorteos posibles de una fuente.

        Returns: número de sorteos procesados.
        """
        if not sorteos:
            return 0
        n = await self._bd.insertar_sorteos_lote(sorteos)
        logger.info("Backfill de memoria: %d sorteos procesados", n)
        return n

    async def registrar_sorteo_nuevo(
        self, fecha, numeros: List[int], complementario: int = 0,
        reintegro: int = 0, bote: int = 0,
    ) -> bool:
        """
        Añade (o actualiza) un sorteo nuevo a la memoria. Idempotente:
        si ya existía esa fecha, actualiza sus datos sin error.

        Returns: True si se registró correctamente.
        """
        if len(numeros) != 6 or len(set(numeros)) != 6:
            logger.warning("Sorteo inválido ignorado: %s", numeros)
            return False
        if not all(1 <= n <= 49 for n in numeros):
            logger.warning("Sorteo con números fuera de rango: %s", numeros)
            return False
        await self._bd.insertar_sorteo(
            fecha, numeros, complementario, reintegro, bote
        )
        logger.info("Sorteo registrado en memoria: %s -> %s", fecha, sorted(numeros))
        return True

    async def sincronizar_desde_api(self, limite: int = 500) -> int:
        """
        Sincroniza la memoria con la fuente externa: trae los últimos sorteos
        y los inserta idempotentemente. Solo añade los que falten.

        Returns: número de sorteos nuevos/actualizados.
        """
        if self._api is None:
            logger.info("Sin fuente API configurada; memoria sin sincronizar.")
            return 0
        try:
            sorteos = await self._api.obtener_historico(limite=limite)
        except Exception as e:
            logger.warning("No se pudo sincronizar desde API: %s", e)
            return 0
        return await self.backfill_completo(sorteos)

    async def obtener_para_algoritmos(
        self, limite: Optional[int] = None
    ) -> List[Dict]:
        """
        Devuelve el histórico para alimentar a los algoritmos. Por defecto
        (limite=None) devuelve TODO el histórico almacenado, para que los
        algoritmos tengan la máxima base estadística.
        """
        return await self._bd.obtener_sorteos(limite=limite)
