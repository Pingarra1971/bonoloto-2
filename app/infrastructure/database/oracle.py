"""
Conexión a Oracle Autonomous Database.

Extraído de main.py. Mejoras:
  - Configuración desde Settings, no de os.getenv esparcidos.
  - Manejo correcto de wallet con/sin password.
  - Operaciones SQL como métodos públicos (no dentro de _crear_tablas).
  - Fallback explícito a in-memory cuando no hay BD (para dev local).
"""

import logging
import os
from datetime import datetime
from typing import List, Optional

import oracledb

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)


def _parse_fecha_iso(valor):
    """
    Parsea una fecha ISO de forma robusta. Acepta el sufijo 'Z' (UTC) que
    datetime.fromisoformat no soporta en Python < 3.11, y devuelve el valor
    sin tocar si ya es datetime. Lanza ValueError solo si es irrecuperable.
    """
    if not isinstance(valor, str):
        return valor
    s = valor.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s)


class BaseDatos:
    """
    Wrapper del pool de conexiones a Oracle ATP.

    Si las credenciales no están configuradas (db_dsn vacío), el pool
    queda en None y los métodos devuelven datos vacíos/fallback. Esto
    permite que la API arranque en entornos de dev/test sin BD.
    """

    # OJO: no anotar como Optional[oracledb.AsyncConnectionPool] porque
    # eso requiere el módulo real al cargar; algunos entornos (CI ligero,
    # tests sin oracledb) usan stubs. Tipado dinámico aquí.
    _pool = None  # type: ignore

    @classmethod
    async def inicializar(cls, settings: Optional[Settings] = None) -> bool:
        """
        Inicializa el pool. Devuelve True si la BD está conectada, False
        si se opera en modo degradado (sin BD).
        """
        cfg = settings or get_settings()
        if not cfg.db_configurada:
            logger.warning(
                "BD no configurada (ORACLE_DSN/USER/PASSWORD vacíos). "
                "Operando en modo degradado: las consultas devolverán "
                "datos simulados."
            )
            return False

        try:
            kwargs = {
                "user": cfg.db_user,
                "password": cfg.db_password,
                "dsn": cfg.db_dsn,
                "min": cfg.db_pool_min,
                "max": cfg.db_pool_max,
                "increment": 1,
            }
            # Wallet (necesario para Autonomous DB)
            if cfg.db_wallet_location and os.path.isdir(cfg.db_wallet_location):
                kwargs["config_dir"] = cfg.db_wallet_location
                kwargs["wallet_location"] = cfg.db_wallet_location
                if cfg.db_wallet_password:
                    kwargs["wallet_password"] = cfg.db_wallet_password

            cls._pool = oracledb.create_pool_async(**kwargs)
            await cls._crear_tablas()
            logger.info("Pool Oracle inicializado (min=%d, max=%d)",
                        cfg.db_pool_min, cfg.db_pool_max)
            return True
        except Exception as e:
            logger.error("Error inicializando BD Oracle: %s", e)
            cls._pool = None
            return False

    @classmethod
    async def cerrar(cls):
        """Cierra el pool al apagar la app."""
        if cls._pool is not None:
            try:
                await cls._pool.close()
            except Exception as e:
                logger.error("Error cerrando pool: %s", e)
            finally:
                cls._pool = None

    @classmethod
    async def _crear_tablas(cls):
        """Crea tablas si no existen. Idempotente."""
        if cls._pool is None:
            return
        ddl_sorteos = """
        BEGIN
          EXECUTE IMMEDIATE 'CREATE TABLE sorteos (
            fecha          DATE PRIMARY KEY,
            numeros        VARCHAR2(50) NOT NULL,
            complementario NUMBER(2),
            reintegro      NUMBER(1),
            bote           NUMBER(15)
          )';
        EXCEPTION
          WHEN OTHERS THEN
            IF SQLCODE != -955 THEN RAISE; END IF;
        END;
        """
        ddl_calculos = """
        BEGIN
          EXECUTE IMMEDIATE 'CREATE TABLE calculos (
            trabajo_id     VARCHAR2(50) PRIMARY KEY,
            estado         VARCHAR2(20) NOT NULL,
            cantidad       NUMBER(3),
            progreso       NUMBER(5,2),
            resultado_json CLOB,
            error          VARCHAR2(2000),
            creado         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completado     TIMESTAMP
          )';
        EXCEPTION
          WHEN OTHERS THEN
            IF SQLCODE != -955 THEN RAISE; END IF;
        END;
        """
        # Tabla de apuestas reales del usuario (dashboard de honestidad).
        ddl_apuestas = """
        BEGIN
          EXECUTE IMMEDIATE 'CREATE TABLE apuestas (
            id             VARCHAR2(50) PRIMARY KEY,
            fecha          DATE NOT NULL,
            numeros        VARCHAR2(50) NOT NULL,
            coste_eur      NUMBER(8,2) DEFAULT 0.5,
            origen         VARCHAR2(20),
            sorteo_fecha   DATE,
            aciertos       NUMBER(2),
            premio_eur     NUMBER(12,2),
            evaluada       NUMBER(1) DEFAULT 0
          )';
        EXCEPTION
          WHEN OTHERS THEN
            IF SQLCODE != -955 THEN RAISE; END IF;
        END;
        """
        # Tabla de predicciones del sistema (para backtest honesto).
        # Se registra ANTES del sorteo; se evalúa DESPUÉS.
        ddl_predicciones = """
        BEGIN
          EXECUTE IMMEDIATE 'CREATE TABLE predicciones (
            id             VARCHAR2(50) PRIMARY KEY,
            trabajo_id     VARCHAR2(50),
            fecha_generada TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            numeros        VARCHAR2(50) NOT NULL,
            confianza      NUMBER(5,2),
            sorteo_fecha   DATE,
            aciertos       NUMBER(2),
            evaluada       NUMBER(1) DEFAULT 0
          )';
        EXCEPTION
          WHEN OTHERS THEN
            IF SQLCODE != -955 THEN RAISE; END IF;
        END;
        """
        async with cls._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(ddl_sorteos)
                await cur.execute(ddl_calculos)
                await cur.execute(ddl_apuestas)
                await cur.execute(ddl_predicciones)
                await conn.commit()

    @classmethod
    async def obtener_sorteos(cls, limite: Optional[int] = 500) -> List[dict]:
        """
        Devuelve sorteos ordenados por fecha desc. Si limite es None, devuelve
        TODO el histórico (para que los algoritmos usen toda la memoria).
        Si no hay BD, devuelve lista vacía (el caller usa sorteos_simulados).
        """
        if cls._pool is None:
            return []
        async with cls._pool.acquire() as conn:
            async with conn.cursor() as cur:
                if limite is None:
                    await cur.execute(
                        "SELECT fecha, numeros, complementario, reintegro, bote "
                        "FROM sorteos ORDER BY fecha DESC"
                    )
                else:
                    await cur.execute(
                        "SELECT fecha, numeros, complementario, reintegro, bote "
                        "FROM sorteos ORDER BY fecha DESC FETCH FIRST :n ROWS ONLY",
                        {"n": limite},
                    )
                rows = await cur.fetchall()
        resultado = []
        for r in rows:
            # Parseo robusto: un registro corrupto no debe romper toda la carga (#169)
            try:
                numeros = [int(x) for x in r[1].split(",") if x.strip()]
                if len(numeros) != 6:
                    continue
            except (ValueError, AttributeError):
                continue
            resultado.append({
                "fecha": r[0].isoformat() if r[0] else None,
                "numeros": numeros,
                "complementario": int(r[2]) if r[2] is not None else 0,
                "reintegro": int(r[3]) if r[3] is not None else 0,
                "bote": int(r[4]) if r[4] is not None else 0,
            })
        return resultado

    @classmethod
    async def insertar_sorteo(
        cls, fecha, numeros: List[int], complementario: int,
        reintegro: int, bote: int = 0,
    ):
        """
        Inserta o actualiza un sorteo (idempotente). Si la fecha ya existe,
        actualiza sus datos en vez de lanzar (#168). Esto permite reintentos
        y backfill sin romper ante duplicados.
        """
        if cls._pool is None:
            return
        nums_str = ",".join(str(n) for n in sorted(numeros))
        async with cls._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "MERGE INTO sorteos USING DUAL ON (fecha = :f) "
                    "WHEN MATCHED THEN UPDATE SET "
                    "  numeros = :n, complementario = :c, "
                    "  reintegro = :r, bote = :b "
                    "WHEN NOT MATCHED THEN INSERT "
                    "  (fecha, numeros, complementario, reintegro, bote) "
                    "  VALUES (:f, :n, :c, :r, :b)",
                    {"f": fecha, "n": nums_str, "c": complementario,
                     "r": reintegro, "b": bote},
                )
                await conn.commit()

    @classmethod
    async def insertar_sorteos_lote(cls, sorteos: List[dict]) -> int:
        """
        Inserta/actualiza muchos sorteos de una vez (backfill del histórico
        completo). Idempotente. Devuelve cuántos se procesaron.

        Cada sorteo es un dict con: fecha (date/datetime), numeros (List[int]),
        complementario (int), reintegro (int), bote (int).
        """
        if cls._pool is None or not sorteos:
            return 0
        filas = []
        vistas = set()
        # Deduplicar por fecha DENTRO del lote: executemany + MERGE puede
        # comportarse de forma indefinida si la misma clave aparece dos veces
        # en el mismo batch. Nos quedamos con la última ocurrencia.
        for s in reversed(sorteos):
            nums = s.get("numeros", [])
            if len(nums) != 6:
                continue
            fecha = s["fecha"]
            if fecha in vistas:
                continue
            vistas.add(fecha)
            filas.append({
                "f": fecha,
                "n": ",".join(str(n) for n in sorted(nums)),
                "c": s.get("complementario", 0),
                "r": s.get("reintegro", 0),
                "b": s.get("bote", 0),
            })
        if not filas:
            return 0
        async with cls._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.executemany(
                    "MERGE INTO sorteos USING DUAL ON (fecha = :f) "
                    "WHEN MATCHED THEN UPDATE SET "
                    "  numeros = :n, complementario = :c, "
                    "  reintegro = :r, bote = :b "
                    "WHEN NOT MATCHED THEN INSERT "
                    "  (fecha, numeros, complementario, reintegro, bote) "
                    "  VALUES (:f, :n, :c, :r, :b)",
                    filas,
                )
                await conn.commit()
        return len(filas)

    @classmethod
    async def contar_sorteos(cls) -> int:
        """Cuántos sorteos hay almacenados en la memoria."""
        if cls._pool is None:
            return 0
        async with cls._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT COUNT(*) FROM sorteos")
                row = await cur.fetchone()
                return int(row[0]) if row else 0

    @classmethod
    async def fecha_ultimo_sorteo(cls):
        """Fecha del sorteo más reciente almacenado, o None si vacío."""
        if cls._pool is None:
            return None
        async with cls._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT MAX(fecha) FROM sorteos")
                row = await cur.fetchone()
                return row[0] if row and row[0] else None

    # ──────────────────────────────────────────────────────────
    # CALCULOS — persistencia de trabajos del pipeline
    # ──────────────────────────────────────────────────────────

    @classmethod
    async def calculo_upsert(
        cls,
        trabajo_id: str,
        estado: str,
        cantidad: int,
        progreso: float = 0.0,
        resultado_json: Optional[str] = None,
        error: Optional[str] = None,
    ):
        """
        Inserta o actualiza un trabajo en la tabla `calculos`.
        Usa MERGE para idempotencia.
        """
        if cls._pool is None:
            return
        sql = """
        MERGE INTO calculos USING DUAL ON (trabajo_id = :tid)
        WHEN MATCHED THEN UPDATE SET
            estado = :est, progreso = :prg,
            resultado_json = COALESCE(:rj, resultado_json),
            error = :err,
            completado = CASE WHEN :est IN ('completado', 'error')
                              THEN CURRENT_TIMESTAMP ELSE completado END
        WHEN NOT MATCHED THEN INSERT
            (trabajo_id, estado, cantidad, progreso, resultado_json, error, creado)
        VALUES (:tid, :est, :cnt, :prg, :rj, :err, CURRENT_TIMESTAMP)
        """
        async with cls._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql, {
                    "tid": trabajo_id, "est": estado, "cnt": cantidad,
                    "prg": progreso, "rj": resultado_json, "err": error,
                })
                await conn.commit()

    @classmethod
    async def calculo_obtener(cls, trabajo_id: str) -> Optional[dict]:
        """Lee un trabajo de BD. None si no existe."""
        if cls._pool is None:
            return None
        async with cls._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT trabajo_id, estado, cantidad, progreso, "
                    "resultado_json, error, creado, completado "
                    "FROM calculos WHERE trabajo_id = :tid",
                    {"tid": trabajo_id},
                )
                row = await cur.fetchone()
                if row is None:
                    return None
                return {
                    "trabajo_id": row[0],
                    "estado": row[1],
                    "cantidad": row[2],
                    "progreso": float(row[3] or 0.0),
                    "resultado_json": row[4],
                    "error": row[5],
                    "creado": row[6],
                    "completado": row[7],
                }

    @classmethod
    async def calculo_existe(cls, trabajo_id: str) -> bool:
        if cls._pool is None:
            return False
        async with cls._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT 1 FROM calculos WHERE trabajo_id = :tid",
                    {"tid": trabajo_id},
                )
                return (await cur.fetchone()) is not None

    @classmethod
    async def calculos_listar_activos(cls) -> List[dict]:
        """Devuelve trabajos en estado iniciando/encolado/calculando."""
        if cls._pool is None:
            return []
        async with cls._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT trabajo_id, estado, cantidad, progreso, "
                    "resultado_json, error, creado "
                    "FROM calculos "
                    "WHERE estado IN ('iniciando', 'encolado', 'calculando') "
                    "ORDER BY creado ASC"
                )
                rows = await cur.fetchall()
        return [
            {"trabajo_id": r[0], "estado": r[1], "cantidad": r[2],
             "progreso": float(r[3] or 0.0), "resultado_json": r[4],
             "error": r[5], "creado": r[6]}
            for r in rows
        ]

    @classmethod
    async def calculos_total(cls) -> int:
        if cls._pool is None:
            return 0
        async with cls._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT COUNT(*) FROM calculos")
                row = await cur.fetchone()
                return int(row[0]) if row else 0

    @classmethod
    async def calculos_marcar_huerfanos_como_error(cls) -> int:
        """
        Tras un reinicio del backend, los trabajos que estaban en estado
        'calculando' quedaron huérfanos (su tarea async murió con el
        proceso). Los marcamos como 'error' para que el cliente sepa.
        Devuelve cuántas filas fueron afectadas.
        """
        if cls._pool is None:
            return 0
        async with cls._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "UPDATE calculos SET estado = 'error', "
                    "error = 'Proceso reiniciado durante cálculo', "
                    "completado = CURRENT_TIMESTAMP "
                    "WHERE estado IN ('iniciando', 'encolado', 'calculando')"
                )
                n = cur.rowcount
                await conn.commit()
                return n or 0

    @classmethod
    async def calculos_purgar_antiguos(cls, dias: int = 90) -> int:
        """Elimina trabajos terminados de hace > N días. Devuelve cuántos cayeron."""
        if cls._pool is None:
            return 0
        async with cls._pool.acquire() as conn:
            async with conn.cursor() as cur:
                # Oracle NO acepta bind variables en literales INTERVAL
                # (INTERVAL :d DAY es sintaxis inválida). Se usa
                # NUMTODSINTERVAL que sí admite bind variables.
                await cur.execute(
                    "DELETE FROM calculos "
                    "WHERE estado IN ('completado', 'error') "
                    "AND completado < CURRENT_TIMESTAMP - NUMTODSINTERVAL(:d, 'DAY')",
                    {"d": dias},
                )
                n = cur.rowcount
                await conn.commit()
                return n or 0

    # ──────────────────────────────────────────────────────────
    # APUESTAS — dashboard de honestidad
    # ──────────────────────────────────────────────────────────

    @classmethod
    async def apuesta_upsert(cls, d: dict):
        """Inserta o actualiza una apuesta."""
        if cls._pool is None:
            return
        nums = ",".join(str(n) for n in d["numeros"])
        fecha = d["fecha"]
        if isinstance(fecha, str):
            fecha = _parse_fecha_iso(fecha)
        sorteo_f = d.get("sorteo_fecha")
        if isinstance(sorteo_f, str):
            sorteo_f = _parse_fecha_iso(sorteo_f)
        sql = """
        MERGE INTO apuestas USING DUAL ON (id = :id)
        WHEN MATCHED THEN UPDATE SET
            aciertos = :ac, premio_eur = :pr,
            sorteo_fecha = :sf, evaluada = :ev
        WHEN NOT MATCHED THEN INSERT
            (id, fecha, numeros, coste_eur, origen, sorteo_fecha, aciertos, premio_eur, evaluada)
        VALUES (:id, :f, :n, :c, :o, :sf, :ac, :pr, :ev)
        """
        async with cls._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql, {
                    "id": d["id"], "f": fecha, "n": nums,
                    "c": d.get("coste_eur", 0.5), "o": d.get("origen", "manual"),
                    "sf": sorteo_f, "ac": d.get("aciertos"),
                    "pr": d.get("premio_eur"),
                    "ev": 1 if d.get("evaluada") else 0,
                })
                await conn.commit()

    @classmethod
    async def apuestas_listar(cls) -> List[dict]:
        if cls._pool is None:
            return []
        async with cls._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT id, fecha, numeros, coste_eur, origen, "
                    "sorteo_fecha, aciertos, premio_eur, evaluada FROM apuestas"
                )
                rows = await cur.fetchall()
        return [
            {
                "id": r[0],
                "fecha": r[1].isoformat() if r[1] else None,
                "numeros": [int(x) for x in r[2].split(",") if x.strip()],
                "coste_eur": float(r[3] or 0.5),
                "origen": r[4],
                "sorteo_fecha": r[5].isoformat() if r[5] else None,
                "aciertos": int(r[6]) if r[6] is not None else None,
                "premio_eur": float(r[7]) if r[7] is not None else None,
                "evaluada": int(r[8] or 0),
            }
            for r in rows
        ]

    # ──────────────────────────────────────────────────────────
    # PREDICCIONES — backtest del sistema
    # ──────────────────────────────────────────────────────────

    @classmethod
    async def prediccion_upsert(cls, d: dict):
        if cls._pool is None:
            return
        nums = ",".join(str(n) for n in d["numeros"])
        fg = d["fecha_generada"]
        if isinstance(fg, str):
            fg = _parse_fecha_iso(fg)
        sf = d.get("sorteo_fecha")
        if isinstance(sf, str):
            sf = _parse_fecha_iso(sf)
        sql = """
        MERGE INTO predicciones USING DUAL ON (id = :id)
        WHEN MATCHED THEN UPDATE SET
            aciertos = :ac, sorteo_fecha = :sf, evaluada = :ev
        WHEN NOT MATCHED THEN INSERT
            (id, trabajo_id, fecha_generada, numeros, confianza, sorteo_fecha, aciertos, evaluada)
        VALUES (:id, :tid, :fg, :n, :cf, :sf, :ac, :ev)
        """
        async with cls._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql, {
                    "id": d["id"], "tid": d.get("trabajo_id", ""),
                    "fg": fg, "n": nums, "cf": d.get("confianza", 0.0),
                    "sf": sf, "ac": d.get("aciertos"),
                    "ev": 1 if d.get("evaluada") else 0,
                })
                await conn.commit()

    @classmethod
    async def predicciones_listar(cls) -> List[dict]:
        if cls._pool is None:
            return []
        async with cls._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT id, trabajo_id, fecha_generada, numeros, "
                    "confianza, sorteo_fecha, aciertos, evaluada FROM predicciones"
                )
                rows = await cur.fetchall()
        return [
            {
                "id": r[0],
                "trabajo_id": r[1],
                "fecha_generada": r[2].isoformat() if r[2] else None,
                "numeros": [int(x) for x in r[3].split(",") if x.strip()],
                "confianza": float(r[4] or 0.0),
                "sorteo_fecha": r[5].isoformat() if r[5] else None,
                "aciertos": int(r[6]) if r[6] is not None else None,
                "evaluada": int(r[7] or 0),
            }
            for r in rows
        ]
