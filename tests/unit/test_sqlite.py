"""
Pruebas de la base de datos de archivo (SQLite).

Verifican que el backend SQLite implementa la MISMA interfaz que Oracle
y con los mismos tipos de datos: persistencia real, idempotencia, orden
por fecha, tipos de fecha (date/datetime) que el resto del código espera,
y semántica COALESCE de los cálculos.
"""

import asyncio
import datetime
import os
import tempfile

from app.config import Settings
from app.infrastructure.database.sqlite import BaseDatos


def _settings_temporal():
    """Settings apuntando a un archivo SQLite temporal y aislado."""
    tmp = tempfile.mkdtemp()
    return Settings(
        jwt_secret="test-secret",
        db_backend="sqlite",
        sqlite_path=os.path.join(tmp, "test.db"),
    )


class TestSQLite:

    def test_persistencia_y_tipos(self):
        """Recorrido completo de las cuatro tablas con datos reales."""

        async def _run():
            ok = await BaseDatos.inicializar(_settings_temporal())
            assert ok is True
            assert BaseDatos._pool is not None

            # Sorteos: histórico en lote + alta individual + idempotencia
            await BaseDatos.insertar_sorteos_lote([
                {"fecha": "2024-01-01", "numeros": [1, 2, 3, 4, 5, 6],
                 "complementario": 7, "reintegro": 0, "bote": 100000},
                {"fecha": datetime.date(2024, 1, 3),
                 "numeros": [10, 20, 30, 40, 45, 49],
                 "complementario": 11, "reintegro": 5, "bote": 200000},
            ])
            await BaseDatos.insertar_sorteo("2024-01-05", [5, 6, 7, 8, 9, 10], 1, 2, 300000)
            # Reinsertar misma fecha debe ACTUALIZAR (no duplicar)
            await BaseDatos.insertar_sorteo("2024-01-05", [11, 12, 13, 14, 15, 16], 3, 4, 999999)

            assert await BaseDatos.contar_sorteos() == 3

            sorteos = await BaseDatos.obtener_sorteos()
            assert sorteos[0]["fecha"] == "2024-01-05"
            assert sorteos[0]["numeros"] == [11, 12, 13, 14, 15, 16]
            assert sorteos[0]["bote"] == 999999

            ultima = await BaseDatos.fecha_ultimo_sorteo()
            assert isinstance(ultima, datetime.date)
            assert ultima.isoformat() == "2024-01-05"

            # Cálculos: tipos datetime + COALESCE
            await BaseDatos.calculo_upsert("t1", "calculando", 10, 25.0)
            assert await BaseDatos.calculo_existe("t1") is True
            await BaseDatos.calculo_upsert("t1", "completado", 10, 100.0,
                                           resultado_json='{"x":1}')
            c = await BaseDatos.calculo_obtener("t1")
            assert c["estado"] == "completado"
            assert isinstance(c["creado"], datetime.datetime)
            assert isinstance(c["completado"], datetime.datetime)
            c["creado"].timestamp()
            await BaseDatos.calculo_upsert("t1", "completado", 10, 100.0)
            assert (await BaseDatos.calculo_obtener("t1"))["resultado_json"] == '{"x":1}'

            await BaseDatos.calculo_upsert("t2", "calculando", 5, 50.0)
            activos = await BaseDatos.calculos_listar_activos()
            assert len(activos) == 1 and activos[0]["trabajo_id"] == "t2"
            assert await BaseDatos.calculos_marcar_huerfanos_como_error() == 1
            assert await BaseDatos.calculos_total() == 2

            # Apuestas: upsert idempotente
            await BaseDatos.apuesta_upsert(
                {"id": "a1", "fecha": "2024-01-05",
                 "numeros": [1, 2, 3, 4, 5, 6], "origen": "manual"})
            await BaseDatos.apuesta_upsert(
                {"id": "a1", "fecha": "2024-01-05",
                 "numeros": [1, 2, 3, 4, 5, 6],
                 "aciertos": 3, "premio_eur": 8.0, "evaluada": True})
            aps = await BaseDatos.apuestas_listar()
            assert len(aps) == 1
            assert aps[0]["aciertos"] == 3 and aps[0]["evaluada"] == 1

            # Predicciones
            await BaseDatos.prediccion_upsert(
                {"id": "p1", "numeros": [7, 8, 9, 10, 11, 12],
                 "fecha_generada": datetime.datetime.now(), "confianza": 0.5})
            preds = await BaseDatos.predicciones_listar()
            assert len(preds) == 1 and preds[0]["numeros"] == [7, 8, 9, 10, 11, 12]

            await BaseDatos.cerrar()
            assert BaseDatos._pool is None

        asyncio.run(_run())

    def test_vacia_devuelve_listas_vacias(self):
        """Sin datos, las consultas devuelven vacío (no rompen)."""

        async def _run():
            await BaseDatos.inicializar(_settings_temporal())
            assert await BaseDatos.obtener_sorteos() == []
            assert await BaseDatos.contar_sorteos() == 0
            assert await BaseDatos.fecha_ultimo_sorteo() is None
            assert await BaseDatos.apuestas_listar() == []
            assert await BaseDatos.predicciones_listar() == []
            await BaseDatos.cerrar()

        asyncio.run(_run())
