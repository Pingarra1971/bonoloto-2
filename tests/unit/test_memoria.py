"""Tests del servicio de memoria de sorteos."""

import pytest
from datetime import datetime


class _BDMemoriaMock:
    """Mock de BaseDatos con almacenamiento en dict (idempotente)."""
    def __init__(self):
        self.sorteos = {}

    async def contar_sorteos(self):
        return len(self.sorteos)

    async def fecha_ultimo_sorteo(self):
        return max(self.sorteos.keys()) if self.sorteos else None

    async def insertar_sorteo(self, fecha, numeros, comp, reint, bote=0):
        self.sorteos[fecha] = sorted(numeros)

    async def insertar_sorteos_lote(self, lista):
        n = 0
        for s in lista:
            if len(s.get("numeros", [])) == 6:
                self.sorteos[s["fecha"]] = sorted(s["numeros"])
                n += 1
        return n

    async def obtener_sorteos(self, limite=None):
        items = sorted(self.sorteos.items(), reverse=True)
        if limite:
            items = items[:limite]
        return [
            {"fecha": f, "numeros": n, "complementario": 0,
             "reintegro": 0, "bote": 0}
            for f, n in items
        ]


@pytest.mark.unit
class TestMemoriaSorteos:
    def _servicio(self):
        from app.services.memoria.servicio_memoria import ServicioMemoriaSorteos
        return ServicioMemoriaSorteos(_BDMemoriaMock())

    @pytest.mark.asyncio
    async def test_estado_inicial_vacio(self):
        mem = self._servicio()
        e = await mem.estado()
        assert e["sorteos_almacenados"] == 0
        assert not e["memoria_activa"]

    @pytest.mark.asyncio
    async def test_registrar_e_idempotencia(self):
        mem = self._servicio()
        ok = await mem.registrar_sorteo_nuevo(
            datetime(2024, 1, 1), [3, 11, 19, 27, 35, 43], 7, 2
        )
        assert ok
        # Registrar misma fecha no duplica
        await mem.registrar_sorteo_nuevo(
            datetime(2024, 1, 1), [3, 11, 19, 27, 35, 43], 7, 2
        )
        e = await mem.estado()
        assert e["sorteos_almacenados"] == 1

    @pytest.mark.asyncio
    async def test_rechaza_sorteo_invalido(self):
        mem = self._servicio()
        assert not await mem.registrar_sorteo_nuevo(
            datetime(2024, 1, 2), [1, 2, 3], 0, 0
        )
        assert not await mem.registrar_sorteo_nuevo(
            datetime(2024, 1, 2), [1, 2, 3, 4, 5, 99], 0, 0
        )
        assert not await mem.registrar_sorteo_nuevo(
            datetime(2024, 1, 2), [1, 1, 2, 3, 4, 5], 0, 0  # duplicado
        )

    @pytest.mark.asyncio
    async def test_backfill_masivo(self):
        mem = self._servicio()
        lote = [
            {"fecha": datetime(2024, 1, d),
             "numeros": [d, d + 1, d + 2, d + 3, d + 4, d + 5],
             "complementario": 0, "reintegro": 0, "bote": 0}
            for d in range(2, 12)
        ]
        n = await mem.backfill_completo(lote)
        assert n == 10
        e = await mem.estado()
        assert e["sorteos_almacenados"] == 10

    @pytest.mark.asyncio
    async def test_obtener_para_algoritmos_devuelve_todo(self):
        mem = self._servicio()
        lote = [
            {"fecha": datetime(2024, 2, d),
             "numeros": [1, 2, 3, 4, 5, 6],
             "complementario": 0, "reintegro": 0, "bote": 0}
            for d in range(1, 6)
        ]
        await mem.backfill_completo(lote)
        todos = await mem.obtener_para_algoritmos()
        assert len(todos) == 5
