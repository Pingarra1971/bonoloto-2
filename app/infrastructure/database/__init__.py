"""
Paquete de base de datos. Expone `BaseDatos` eligiendo el backend según
la configuración:

  - DB_BACKEND=sqlite  → base de datos de archivo (sqlite3, sin configurar)
  - DB_BACKEND=oracle  → Oracle Autonomous Database
  - DB_BACKEND=auto    → Oracle si hay credenciales Oracle; si no, sqlite

El resto del código hace `from app.infrastructure.database import BaseDatos`
y no necesita saber qué backend hay debajo: la interfaz es idéntica.
"""

import logging

logger = logging.getLogger(__name__)


def _elegir_base_datos():
    from app.config import get_settings
    cfg = get_settings()
    backend = (getattr(cfg, "db_backend", "auto") or "auto").lower()

    if backend == "oracle":
        from .oracle import BaseDatos
        logger.info("Backend de BD: Oracle (forzado por DB_BACKEND=oracle)")
        return BaseDatos
    if backend == "sqlite":
        from .sqlite import BaseDatos
        logger.info("Backend de BD: SQLite (archivo local)")
        return BaseDatos

    # auto: Oracle solo si hay credenciales; si no, SQLite (archivo).
    if cfg.db_configurada:
        from .oracle import BaseDatos
        logger.info("Backend de BD: Oracle (credenciales detectadas)")
        return BaseDatos
    from .sqlite import BaseDatos
    logger.info("Backend de BD: SQLite (sin credenciales Oracle)")
    return BaseDatos


BaseDatos = _elegir_base_datos()

__all__ = ["BaseDatos"]
