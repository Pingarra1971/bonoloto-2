"""Tests de la configuración."""

import os
import pytest


def _reset_settings_cache():
    """Limpia el singleton para que get_settings vuelva a leer env vars."""
    import app.config
    app.config._settings = None


@pytest.mark.unit
class TestSettings:
    def teardown_method(self):
        _reset_settings_cache()
        # Limpiar env vars de test
        for k in ["JWT_SECRET", "ORACLE_USER", "ORACLE_PASSWORD",
                  "ORACLE_DSN", "JWT_EXPIRE_HOURS"]:
            os.environ.pop(k, None)

    def test_jwt_secret_se_genera_si_no_existe(self, monkeypatch):
        monkeypatch.delenv("JWT_SECRET", raising=False)
        _reset_settings_cache()
        from app.config import cargar_settings
        s = cargar_settings()
        # Debe ser un string no vacío y razonablemente largo (aleatorio)
        assert len(s.jwt_secret) >= 32

    def test_jwt_secret_respeta_env(self, monkeypatch):
        monkeypatch.setenv("JWT_SECRET", "mi-secreto-de-test-12345")
        _reset_settings_cache()
        from app.config import cargar_settings
        s = cargar_settings()
        assert s.jwt_secret == "mi-secreto-de-test-12345"

    def test_db_configurada_property(self, monkeypatch):
        monkeypatch.setenv("ORACLE_USER", "admin")
        monkeypatch.setenv("ORACLE_PASSWORD", "secret")
        monkeypatch.setenv("ORACLE_DSN", "host:1521/srv")
        _reset_settings_cache()
        from app.config import cargar_settings
        s = cargar_settings()
        assert s.db_configurada is True

    def test_db_configurada_false_si_falta_algo(self, monkeypatch):
        monkeypatch.setenv("ORACLE_USER", "admin")
        # falta ORACLE_PASSWORD
        monkeypatch.delenv("ORACLE_PASSWORD", raising=False)
        monkeypatch.setenv("ORACLE_DSN", "host:1521/srv")
        _reset_settings_cache()
        from app.config import cargar_settings
        s = cargar_settings()
        assert s.db_configurada is False

    def test_singleton_get_settings(self):
        from app.config import get_settings
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2
