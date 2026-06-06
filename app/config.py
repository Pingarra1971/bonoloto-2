"""
Configuración centralizada de Bonoloto 2.0.

Antes esto estaba esparcido como `os.getenv()` calls por todo main.py
con valores por defecto inseguros (p.ej. JWT_SECRET="bonoloto-ai-secret-key").
Ahora hay una sola fuente de verdad, validación al arranque, y los
defaults inseguros lanzan warnings o errores explícitos.
"""

import logging
import os
import secrets
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


# Valores por defecto seguros para arranque local; en producción deben
# venir del entorno. Si JWT_SECRET no está, generamos uno aleatorio,
# pero advertimos: en producción esto invalida tokens entre reinicios.
_DEFAULT_DEV_DB_DSN = ""


def _get_or_warn(name: str, default: str = "") -> str:
    """Lee variable de entorno; loguea warning si está vacía y no había default."""
    val = os.getenv(name, default)
    if not val and default:
        logger.warning(
            "Variable de entorno %s no definida; usando default. "
            "En producción esto debe configurarse explícitamente.",
            name,
        )
    return val


@dataclass(frozen=True)
class Settings:
    """Configuración inmutable. Construida una vez al arranque."""

    # ── Autenticación ──
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 24

    # ── Base de datos ──
    # db_backend: "sqlite" (archivo local, por defecto y sin configuración) u
    # "oracle" (Autonomous Database). Si se deja en "auto", se usa Oracle solo
    # cuando hay credenciales Oracle; en caso contrario, sqlite.
    db_backend: str = "auto"
    sqlite_path: str = "datos/bonoloto.db"
    # ── Base de datos Oracle (opcional) ──
    db_user: str = ""
    db_password: str = ""
    db_dsn: str = ""
    db_wallet_location: str = ""
    db_wallet_password: str = ""
    db_pool_min: int = 2
    db_pool_max: int = 10

    # ── Servidor ──
    host: str = "0.0.0.0"
    port: int = 8000

    # ── Cálculo ──
    max_trabajos_memoria: int = 50
    timeout_calculo_segundos: int = 3600

    # ── Logging ──
    log_level: str = "INFO"

    @property
    def db_configurada(self) -> bool:
        """True si hay credenciales de BD válidas."""
        return bool(self.db_dsn and self.db_user and self.db_password)


def cargar_settings() -> Settings:
    """
    Carga la configuración desde variables de entorno.

    Compatibilidad: acepta tanto los nombres v7 (ORACLE_*) como los legacy (DB_*).
    Para el JWT: si no se define JWT_SECRET, se genera uno aleatorio en cada
    arranque. Esto INVALIDA los tokens existentes — está OK para dev pero
    en producción hay que configurarlo en /etc/bonoloto-2.env.
    """
    jwt_secret = os.getenv("JWT_SECRET")
    if not jwt_secret:
        # En el sistema legacy había un default literal "bonoloto-ai-secret-key-oracle-cloud"
        # — un secreto público en git es peor que un secreto aleatorio efímero.
        jwt_secret = secrets.token_urlsafe(64)
        logger.warning(
            "JWT_SECRET no definido. Generado aleatorio efímero. "
            "Los tokens existentes serán inválidos. "
            "Para producción define JWT_SECRET en /etc/bonoloto-2.env."
        )

    return Settings(
        jwt_secret=jwt_secret,
        jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
        jwt_expire_hours=int(os.getenv("JWT_EXPIRE_HOURS", "24")),
        db_backend=os.getenv("DB_BACKEND", "auto").lower(),
        sqlite_path=os.getenv("SQLITE_PATH", "datos/bonoloto.db"),
        db_user=os.getenv("ORACLE_USER") or os.getenv("DB_USER", ""),
        db_password=os.getenv("ORACLE_PASSWORD") or os.getenv("DB_PASSWORD", ""),
        db_dsn=os.getenv("ORACLE_DSN") or os.getenv("DB_DSN", ""),
        db_wallet_location=os.getenv("ORACLE_WALLET_LOCATION", ""),
        db_wallet_password=os.getenv("ORACLE_WALLET_PASSWORD", ""),
        db_pool_min=int(os.getenv("DB_POOL_MIN", "2")),
        db_pool_max=int(os.getenv("DB_POOL_MAX", "10")),
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        max_trabajos_memoria=int(os.getenv("MAX_TRABAJOS_MEMORIA", "50")),
        timeout_calculo_segundos=int(os.getenv("TIMEOUT_CALCULO_SEGUNDOS", "3600")),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )


# Instancia global. Importable como `from app.config import settings`.
# Construida lazy en el primer acceso para evitar side effects al import.
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Devuelve la configuración (singleton)."""
    global _settings
    if _settings is None:
        _settings = cargar_settings()
    return _settings
