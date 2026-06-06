"""
Base de datos SQLite (archivo local) — alternativa simple a Oracle ATP.

Implementa EXACTAMENTE la misma interfaz pública que
`app.infrastructure.database.oracle.BaseDatos`, de modo que el resto del
código (servicios, rutas, watchdog) funcione sin cambios. La única
diferencia es que persiste en un único archivo .db en disco, sin
necesidad de wallet, DSN ni configuración de Oracle.

Ventajas para el despliegue:
  - Sin dependencias extra: usa el módulo `sqlite3` de la stdlib.
  - Sin configuración: solo una ruta de archivo (SQLITE_PATH).
  - Misma estructura de tablas y mismos formatos de datos que Oracle.

Concurrencia: la app es asíncrona pero de bajísimo tráfico (un usuario,
unas pocas consultas al día). Cada operación abre una conexión breve en
un hilo aparte (asyncio.to_thread) con journal WAL, lo cual es de sobra
para esta carga. Mantener el tipo de los datos devueltos idéntico a
Oracle es lo que garantiza que sea "igual de potente".
"""

import asyncio
import logging
import os
import sqlite3
from datetime import date, datetime, timezone
from typing import List, Optional

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────
# Helpers de fechas (para igualar el comportamiento de Oracle)
# ──────────────────────────────────────────────────────────

def _ahora_iso() -> str:
    """Marca de tiempo actual en ISO (equivalente a CURRENT_TIMESTAMP)."""
    return datetime.now(timezone.utc).isoformat()


def _parse_fecha_iso(valor):
    """Parsea una fecha/hora ISO de forma robusta (acepta sufijo 'Z')."""
    if valor is None:
        return None
    if isinstance(valor, datetime):
        return valor
    if isinstance(valor, date):
        return datetime(valor.year, valor.month, valor.day)
    s = str(valor).strip()
    if not s:
        return None
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s)


def _a_fecha_dia(valor) -> Optional[str]:
    """
    Normaliza a 'YYYY-MM-DD' (solo día), igual que una columna DATE de
    Oracle usada para sorteos/apuestas. Devuelve None si vacío.
    """
    if valor is None:
        return None
    if isinstance(valor, datetime):
        return valor.date().isoformat()
    if isinstance(valor, date):
        return valor.isoformat()
    s = str(valor).strip()
    if not s:
        return None
    # Quedarse con la parte de fecha si viene con hora
    return _parse_fecha_iso(s).date().isoformat()


def _a_dt_iso(valor) -> Optional[str]:
    """Normaliza a ISO completo (con hora), para timestamps."""
    if valor is None:
        return None
    dt = _parse_fecha_iso(valor)
    return dt.isoformat() if dt else None


class BaseDatos:
    """
    Wrapper de SQLite con la MISMA interfaz que la versión Oracle.

    `_pool` se usa en el resto del código como "¿hay BD conectada?".
    Aquí guardamos la ruta del archivo (truthy) cuando está inicializada,
    y None cuando no, para conservar esa semántica.
    """

    _pool = None        # type: ignore  # sentinel de "conectada" (ruta o None)
    _db_path = None     # type: ignore

    # ──────────────────────────────────────────────────────
    # Infraestructura de conexión
    # ──────────────────────────────────────────────────────

    @classmethod
    def _con_conexion(cls, fn):
        """Abre una conexión breve, ejecuta fn(con), hace commit y cierra."""
        con = sqlite3.connect(cls._db_path, timeout=30)
        try:
            con.execute("PRAGMA journal_mode=WAL")
            con.execute("PRAGMA busy_timeout=30000")
            resultado = fn(con)
            con.commit()
            return resultado
        finally:
            con.close()

    @classmethod
    async def _ejecutar(cls, fn):
        """Ejecuta una operación de BD en un hilo aparte (no bloquea el loop)."""
        return await asyncio.to_thread(cls._con_conexion, fn)

    # ──────────────────────────────────────────────────────
    # Ciclo de vida
    # ──────────────────────────────────────────────────────

    @classmethod
    async def inicializar(cls, settings: Optional[Settings] = None) -> bool:
        """
        Inicializa la BD de archivo. Crea el directorio y las tablas si no
        existen. Devuelve True si quedó lista.
        """
        cfg = settings or get_settings()
        ruta = getattr(cfg, "sqlite_path", "") or "datos/bonoloto.db"
        # Asegurar que el directorio existe
        directorio = os.path.dirname(os.path.abspath(ruta))
        if directorio:
            os.makedirs(directorio, exist_ok=True)
        cls._db_path = ruta
        try:
            await cls._crear_tablas()
            cls._pool = ruta  # truthy → "conectada"
            logger.info("Base de datos SQLite inicializada en %s", ruta)
            return True
        except Exception as e:
            logger.error("Error inicializando SQLite: %s", e)
            cls._pool = None
            return False

    @classmethod
    async def cerrar(cls):
        """No hay pool persistente; solo marcamos como desconectada."""
        cls._pool = None

    @classmethod
    async def _crear_tablas(cls):
        """Crea las tablas si no existen. Idempotente."""
        def _fn(con):
            con.executescript(
                """
                CREATE TABLE IF NOT EXISTS sorteos (
                    fecha          TEXT PRIMARY KEY,
                    numeros        TEXT NOT NULL,
                    complementario INTEGER,
                    reintegro      INTEGER,
                    bote           INTEGER
                );
                CREATE TABLE IF NOT EXISTS calculos (
                    trabajo_id     TEXT PRIMARY KEY,
                    estado         TEXT NOT NULL,
                    cantidad       INTEGER,
                    progreso       REAL,
                    resultado_json TEXT,
                    error          TEXT,
                    creado         TEXT,
                    completado     TEXT
                );
                CREATE TABLE IF NOT EXISTS apuestas (
                    id           TEXT PRIMARY KEY,
                    fecha        TEXT NOT NULL,
                    numeros      TEXT NOT NULL,
                    coste_eur    REAL DEFAULT 0.5,
                    origen       TEXT,
                    sorteo_fecha TEXT,
                    aciertos     INTEGER,
                    premio_eur   REAL,
                    evaluada     INTEGER DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS predicciones (
                    id             TEXT PRIMARY KEY,
                    trabajo_id     TEXT,
                    fecha_generada TEXT,
                    numeros        TEXT NOT NULL,
                    confianza      REAL,
                    sorteo_fecha   TEXT,
                    aciertos       INTEGER,
                    evaluada       INTEGER DEFAULT 0
                );
                """
            )
        await cls._ejecutar(_fn)

    # ──────────────────────────────────────────────────────
    # SORTEOS — la "memoria"
    # ──────────────────────────────────────────────────────

    @classmethod
    async def obtener_sorteos(cls, limite: Optional[int] = 500) -> List[dict]:
        """Sorteos ordenados por fecha desc. limite=None → todo el histórico."""
        if cls._pool is None:
            return []

        def _fn(con):
            if limite is None:
                cur = con.execute(
                    "SELECT fecha, numeros, complementario, reintegro, bote "
                    "FROM sorteos ORDER BY fecha DESC"
                )
            else:
                cur = con.execute(
                    "SELECT fecha, numeros, complementario, reintegro, bote "
                    "FROM sorteos ORDER BY fecha DESC LIMIT :n",
                    {"n": limite},
                )
            return cur.fetchall()

        rows = await cls._ejecutar(_fn)
        resultado = []
        for r in rows:
            try:
                numeros = [int(x) for x in r[1].split(",") if str(x).strip()]
                if len(numeros) != 6:
                    continue
            except (ValueError, AttributeError):
                continue
            resultado.append({
                "fecha": r[0],  # ya es 'YYYY-MM-DD' (igual que .isoformat() de Oracle)
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
        """Inserta o actualiza un sorteo (idempotente por fecha)."""
        if cls._pool is None:
            return
        nums_str = ",".join(str(n) for n in sorted(numeros))
        f = _a_fecha_dia(fecha)

        def _fn(con):
            con.execute(
                "INSERT INTO sorteos (fecha, numeros, complementario, reintegro, bote) "
                "VALUES (:f, :n, :c, :r, :b) "
                "ON CONFLICT(fecha) DO UPDATE SET "
                "  numeros = excluded.numeros, "
                "  complementario = excluded.complementario, "
                "  reintegro = excluded.reintegro, "
                "  bote = excluded.bote",
                {"f": f, "n": nums_str, "c": complementario,
                 "r": reintegro, "b": bote},
            )

        await cls._ejecutar(_fn)

    @classmethod
    async def insertar_sorteos_lote(cls, sorteos: List[dict]) -> int:
        """
        Inserta/actualiza muchos sorteos de una vez (backfill del histórico).
        Idempotente. Deduplica por fecha dentro del lote (última ocurrencia).
        Devuelve cuántos se procesaron.
        """
        if cls._pool is None or not sorteos:
            return 0
        filas = []
        vistas = set()
        for s in reversed(sorteos):
            nums = s.get("numeros", [])
            if len(nums) != 6:
                continue
            f = _a_fecha_dia(s["fecha"])
            if f in vistas:
                continue
            vistas.add(f)
            filas.append({
                "f": f,
                "n": ",".join(str(n) for n in sorted(nums)),
                "c": s.get("complementario", 0),
                "r": s.get("reintegro", 0),
                "b": s.get("bote", 0),
            })
        if not filas:
            return 0

        def _fn(con):
            con.executemany(
                "INSERT INTO sorteos (fecha, numeros, complementario, reintegro, bote) "
                "VALUES (:f, :n, :c, :r, :b) "
                "ON CONFLICT(fecha) DO UPDATE SET "
                "  numeros = excluded.numeros, "
                "  complementario = excluded.complementario, "
                "  reintegro = excluded.reintegro, "
                "  bote = excluded.bote",
                filas,
            )

        await cls._ejecutar(_fn)
        return len(filas)

    @classmethod
    async def contar_sorteos(cls) -> int:
        if cls._pool is None:
            return 0

        def _fn(con):
            row = con.execute("SELECT COUNT(*) FROM sorteos").fetchone()
            return int(row[0]) if row else 0

        return await cls._ejecutar(_fn)

    @classmethod
    async def fecha_ultimo_sorteo(cls):
        """Fecha (objeto date) del sorteo más reciente, o None."""
        if cls._pool is None:
            return None

        def _fn(con):
            row = con.execute("SELECT MAX(fecha) FROM sorteos").fetchone()
            return row[0] if row and row[0] else None

        valor = await cls._ejecutar(_fn)
        if not valor:
            return None
        # Devolver un objeto date (el caller hace .isoformat()), igual que Oracle
        return date.fromisoformat(str(valor)[:10])

    # ──────────────────────────────────────────────────────
    # CALCULOS — persistencia de trabajos del pipeline
    # ──────────────────────────────────────────────────────

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
        """Inserta o actualiza un trabajo (misma semántica que el MERGE Oracle)."""
        if cls._pool is None:
            return
        ahora = _ahora_iso()
        completa = estado in ("completado", "error")

        def _fn(con):
            existe = con.execute(
                "SELECT resultado_json, completado FROM calculos WHERE trabajo_id = :t",
                {"t": trabajo_id},
            ).fetchone()
            if existe is None:
                con.execute(
                    "INSERT INTO calculos "
                    "(trabajo_id, estado, cantidad, progreso, resultado_json, "
                    " error, creado, completado) "
                    "VALUES (:t, :e, :c, :p, :rj, :err, :cr, :comp)",
                    {"t": trabajo_id, "e": estado, "c": cantidad, "p": progreso,
                     "rj": resultado_json, "err": error, "cr": ahora,
                     "comp": ahora if completa else None},
                )
            else:
                # COALESCE(:rj, resultado_json): si el nuevo es None, conserva el viejo
                rj_final = resultado_json if resultado_json is not None else existe[0]
                # completado: si pasa a completado/error, ahora; si no, conserva
                comp_final = ahora if completa else existe[1]
                con.execute(
                    "UPDATE calculos SET estado = :e, progreso = :p, "
                    "resultado_json = :rj, error = :err, completado = :comp "
                    "WHERE trabajo_id = :t",
                    {"t": trabajo_id, "e": estado, "p": progreso,
                     "rj": rj_final, "err": error, "comp": comp_final},
                )

        await cls._ejecutar(_fn)

    @classmethod
    async def calculo_obtener(cls, trabajo_id: str) -> Optional[dict]:
        """Lee un trabajo. None si no existe. Fechas como objetos datetime."""
        if cls._pool is None:
            return None

        def _fn(con):
            return con.execute(
                "SELECT trabajo_id, estado, cantidad, progreso, resultado_json, "
                "error, creado, completado FROM calculos WHERE trabajo_id = :t",
                {"t": trabajo_id},
            ).fetchone()

        row = await cls._ejecutar(_fn)
        if row is None:
            return None
        return {
            "trabajo_id": row[0],
            "estado": row[1],
            "cantidad": row[2],
            "progreso": float(row[3] or 0.0),
            "resultado_json": row[4],
            "error": row[5],
            "creado": _parse_fecha_iso(row[6]),       # datetime (el caller hace .timestamp())
            "completado": _parse_fecha_iso(row[7]),   # datetime o None
        }

    @classmethod
    async def calculo_existe(cls, trabajo_id: str) -> bool:
        if cls._pool is None:
            return False

        def _fn(con):
            return con.execute(
                "SELECT 1 FROM calculos WHERE trabajo_id = :t", {"t": trabajo_id}
            ).fetchone() is not None

        return await cls._ejecutar(_fn)

    @classmethod
    async def calculos_listar_activos(cls) -> List[dict]:
        """Trabajos en estado iniciando/encolado/calculando."""
        if cls._pool is None:
            return []

        def _fn(con):
            return con.execute(
                "SELECT trabajo_id, estado, cantidad, progreso, resultado_json, "
                "error, creado FROM calculos "
                "WHERE estado IN ('iniciando', 'encolado', 'calculando') "
                "ORDER BY creado ASC"
            ).fetchall()

        rows = await cls._ejecutar(_fn)
        return [
            {"trabajo_id": r[0], "estado": r[1], "cantidad": r[2],
             "progreso": float(r[3] or 0.0), "resultado_json": r[4],
             "error": r[5], "creado": _parse_fecha_iso(r[6])}
            for r in rows
        ]

    @classmethod
    async def calculos_total(cls) -> int:
        if cls._pool is None:
            return 0

        def _fn(con):
            row = con.execute("SELECT COUNT(*) FROM calculos").fetchone()
            return int(row[0]) if row else 0

        return await cls._ejecutar(_fn)

    @classmethod
    async def calculos_marcar_huerfanos_como_error(cls) -> int:
        """Marca como 'error' los trabajos que quedaron a medias tras un reinicio."""
        if cls._pool is None:
            return 0
        ahora = _ahora_iso()

        def _fn(con):
            cur = con.execute(
                "UPDATE calculos SET estado = 'error', "
                "error = 'Proceso reiniciado durante cálculo', completado = :c "
                "WHERE estado IN ('iniciando', 'encolado', 'calculando')",
                {"c": ahora},
            )
            return cur.rowcount or 0

        return await cls._ejecutar(_fn)

    @classmethod
    async def calculos_purgar_antiguos(cls, dias: int = 90) -> int:
        """Elimina trabajos terminados de hace > N días."""
        if cls._pool is None:
            return 0
        from datetime import timedelta
        corte = (datetime.now(timezone.utc) - timedelta(days=dias)).isoformat()

        def _fn(con):
            cur = con.execute(
                "DELETE FROM calculos "
                "WHERE estado IN ('completado', 'error') "
                "AND completado IS NOT NULL AND completado < :corte",
                {"corte": corte},
            )
            return cur.rowcount or 0

        return await cls._ejecutar(_fn)

    # ──────────────────────────────────────────────────────
    # APUESTAS — dashboard de honestidad
    # ──────────────────────────────────────────────────────

    @classmethod
    async def apuesta_upsert(cls, d: dict):
        """Inserta o actualiza una apuesta."""
        if cls._pool is None:
            return
        nums = ",".join(str(n) for n in d["numeros"])
        fecha = _a_fecha_dia(d["fecha"])
        sorteo_f = _a_fecha_dia(d.get("sorteo_fecha"))

        def _fn(con):
            con.execute(
                "INSERT INTO apuestas "
                "(id, fecha, numeros, coste_eur, origen, sorteo_fecha, "
                " aciertos, premio_eur, evaluada) "
                "VALUES (:id, :f, :n, :c, :o, :sf, :ac, :pr, :ev) "
                "ON CONFLICT(id) DO UPDATE SET "
                "  aciertos = excluded.aciertos, "
                "  premio_eur = excluded.premio_eur, "
                "  sorteo_fecha = excluded.sorteo_fecha, "
                "  evaluada = excluded.evaluada",
                {"id": d["id"], "f": fecha, "n": nums,
                 "c": d.get("coste_eur", 0.5), "o": d.get("origen", "manual"),
                 "sf": sorteo_f, "ac": d.get("aciertos"),
                 "pr": d.get("premio_eur"),
                 "ev": 1 if d.get("evaluada") else 0},
            )

        await cls._ejecutar(_fn)

    @classmethod
    async def apuestas_listar(cls) -> List[dict]:
        if cls._pool is None:
            return []

        def _fn(con):
            return con.execute(
                "SELECT id, fecha, numeros, coste_eur, origen, sorteo_fecha, "
                "aciertos, premio_eur, evaluada FROM apuestas"
            ).fetchall()

        rows = await cls._ejecutar(_fn)
        return [
            {
                "id": r[0],
                "fecha": r[1],
                "numeros": [int(x) for x in r[2].split(",") if str(x).strip()],
                "coste_eur": float(r[3] or 0.5),
                "origen": r[4],
                "sorteo_fecha": r[5],
                "aciertos": int(r[6]) if r[6] is not None else None,
                "premio_eur": float(r[7]) if r[7] is not None else None,
                "evaluada": int(r[8] or 0),
            }
            for r in rows
        ]

    # ──────────────────────────────────────────────────────
    # PREDICCIONES — backtest del sistema
    # ──────────────────────────────────────────────────────

    @classmethod
    async def prediccion_upsert(cls, d: dict):
        if cls._pool is None:
            return
        nums = ",".join(str(n) for n in d["numeros"])
        fg = _a_dt_iso(d["fecha_generada"])
        sf = _a_fecha_dia(d.get("sorteo_fecha"))

        def _fn(con):
            con.execute(
                "INSERT INTO predicciones "
                "(id, trabajo_id, fecha_generada, numeros, confianza, "
                " sorteo_fecha, aciertos, evaluada) "
                "VALUES (:id, :tid, :fg, :n, :cf, :sf, :ac, :ev) "
                "ON CONFLICT(id) DO UPDATE SET "
                "  aciertos = excluded.aciertos, "
                "  sorteo_fecha = excluded.sorteo_fecha, "
                "  evaluada = excluded.evaluada",
                {"id": d["id"], "tid": d.get("trabajo_id", ""),
                 "fg": fg, "n": nums, "cf": d.get("confianza", 0.0),
                 "sf": sf, "ac": d.get("aciertos"),
                 "ev": 1 if d.get("evaluada") else 0},
            )

        await cls._ejecutar(_fn)

    @classmethod
    async def predicciones_listar(cls) -> List[dict]:
        if cls._pool is None:
            return []

        def _fn(con):
            return con.execute(
                "SELECT id, trabajo_id, fecha_generada, numeros, confianza, "
                "sorteo_fecha, aciertos, evaluada FROM predicciones"
            ).fetchall()

        rows = await cls._ejecutar(_fn)
        return [
            {
                "id": r[0],
                "trabajo_id": r[1],
                "fecha_generada": r[2],
                "numeros": [int(x) for x in r[3].split(",") if str(x).strip()],
                "confianza": float(r[4] or 0.0),
                "sorteo_fecha": r[5],
                "aciertos": int(r[6]) if r[6] is not None else None,
                "evaluada": int(r[7] or 0),
            }
            for r in rows
        ]
