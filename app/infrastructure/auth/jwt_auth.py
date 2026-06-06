"""
Autenticación JWT.

Extraído del main.py legacy. La función `verificar_token` se convierte en
dependency injectable de FastAPI. La generación de tokens vive aquí también
para que sea testeable sin levantar la API.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

import jwt as pyjwt
from fastapi import HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Depends

from app.config import get_settings

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=True)


def generar_token(
    payload: Optional[dict] = None,
    horas_validez: Optional[int] = None,
) -> str:
    """
    Genera un JWT firmado con el secreto del entorno.

    Args:
        payload: campos adicionales a incluir (sub, scope, etc.)
        horas_validez: override del default de settings

    Returns:
        Token JWT codificado como string.
    """
    settings = get_settings()
    horas = horas_validez if horas_validez is not None else settings.jwt_expire_hours

    ahora = datetime.now(timezone.utc)
    claims = {
        "iat": ahora,
        "exp": ahora + timedelta(hours=horas),
    }
    if payload:
        claims.update(payload)

    return pyjwt.encode(claims, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def verificar_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """
    Dependency de FastAPI: verifica el JWT del header Authorization.

    Lanza HTTPException 401 si el token es inválido o ha expirado.
    Devuelve el payload decodificado en caso correcto, lo que permite
    a los endpoints leer claims (p.ej. el `sub`).
    """
    settings = get_settings()
    token = credentials.credentials
    try:
        payload = pyjwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        return payload
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except pyjwt.InvalidTokenError as e:
        logger.warning("Intento de acceso con token inválido: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )
