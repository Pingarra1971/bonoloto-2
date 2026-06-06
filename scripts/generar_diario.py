#!/usr/bin/env python3
"""
TAREA DIARIA (GitHub Actions) — Bonoloto 2.0
============================================

Una vez al día, después del sorteo:
  1. Descarga el histórico de Bonoloto de loteriasapi.com (con la API key,
     que llega como secreto de GitHub: LOTERIAS_API_KEY).
  2. Ejecuta el motor de IA con los datos al día.
  3. Escribe las combinaciones del día (y las apuestas múltiples) en
     docs/combinaciones.json, que la app descargará.

No usa base de datos: pasa el histórico directamente al pipeline.
"""
import os
import sys
import json
import time
import asyncio
from datetime import datetime, timezone, timedelta

import httpx

# Permite importar el paquete app/ desde la raíz del repositorio.
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from app.services.pipeline.pipeline_v4 import PipelineV4  # noqa: E402
from app.domain.apuesta_multiple import calcular_apuestas_multiples  # noqa: E402

API_URL = "https://api.loteriasapi.com/api/v1"
API_KEY = os.getenv("LOTERIAS_API_KEY", "").strip()
CANTIDAD = int(os.getenv("CANTIDAD_COMBINACIONES", "5"))
LIMITE_HISTORICO = int(os.getenv("LIMITE_HISTORICO", "3000"))
SALIDA = os.getenv("SALIDA_JSON", os.path.join(RAIZ, "docs", "combinaciones.json"))


def _mapear_sorteo(item: dict):
    """Convierte un sorteo de la API al formato que espera el pipeline."""
    if not isinstance(item, dict):
        return None
    rd = item.get("resultData") if isinstance(item.get("resultData"), dict) else {}
    numeros = (item.get("combination") or item.get("numeros")
               or item.get("combinacion") or rd.get("combination") or [])
    try:
        numeros = [int(n) for n in numeros]
    except (ValueError, TypeError):
        return None
    if len(numeros) != 6:
        return None
    return {
        "fecha": str(item.get("drawDate") or item.get("fecha") or ""),
        "numeros": numeros,
        "complementario": int(item.get("complementario",
                                       rd.get("complementario", 0)) or 0),
        "reintegro": int(item.get("reintegro", rd.get("reintegro", 0)) or 0),
        "bote": int(item.get("jackpot", item.get("bote", 0)) or 0),
    }


def descargar_historico():
    """Descarga y normaliza el histórico de sorteos desde loteriasapi.com."""
    if not API_KEY:
        raise SystemExit(
            "ERROR: falta LOTERIAS_API_KEY. Configúralo como secreto en "
            "GitHub (Settings -> Secrets and variables -> Actions)."
        )
    headers = {"X-API-Key": API_KEY, "Content-Type": "application/json"}
    url = f"{API_URL}/results/bonoloto/history?limit={LIMITE_HISTORICO}"

    # Reintentos: la API puede fallar puntualmente (red, 5xx, etc.).
    cuerpo = None
    ultimo_error = None
    for intento in range(1, 4):
        try:
            with httpx.Client(timeout=60) as client:
                resp = client.get(url, headers=headers)
                resp.raise_for_status()
                cuerpo = resp.json()
            break
        except Exception as e:  # noqa: BLE001
            ultimo_error = e
            print(f"  Intento {intento}/3 fallido: {e}")
            if intento < 3:
                time.sleep(5)
    if cuerpo is None:
        raise SystemExit(
            f"ERROR: no se pudo descargar el histórico tras 3 intentos: {ultimo_error}"
        )

    datos = cuerpo.get("data", cuerpo) if isinstance(cuerpo, dict) else cuerpo
    if isinstance(datos, dict):
        datos = (datos.get("results") or datos.get("items")
                 or datos.get("draws") or [datos])

    sorteos = []
    for item in datos or []:
        s = _mapear_sorteo(item)
        if s:
            sorteos.append(s)

    # Más reciente primero (igual que la base de datos del servidor).
    sorteos.sort(key=lambda s: s["fecha"], reverse=True)
    return sorteos


def proxima_fecha_sorteo():
    """Fecha del próximo sorteo. La Bonoloto se juega TODOS los días a las
    21:30 (hora España). Aproximamos la hora peninsular con UTC+1."""
    ahora = datetime.now(timezone.utc) + timedelta(hours=1)
    corte = ahora.replace(hour=21, minute=30, second=0, microsecond=0)
    f = ahora + timedelta(days=1) if ahora > corte else ahora
    return f.strftime("%Y-%m-%d")


def _a_nativo(obj):
    """Convierte tipos de numpy (y estructuras anidadas) a tipos nativos de
    Python, para que el JSON salga con números de verdad y no texto.

    El motor usa numpy, así que confianzas/scores pueden ser np.float64 y los
    números np.int64. Sin esto, json los rompería o los guardaría como string.
    """
    try:
        import numpy as np
    except ImportError:
        np = None
    if np is not None:
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.bool_):
            return bool(obj)
        if isinstance(obj, np.ndarray):
            return [_a_nativo(x) for x in obj.tolist()]
    if isinstance(obj, dict):
        return {(_a_nativo(k) if not isinstance(k, str) else k): _a_nativo(v)
                for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_a_nativo(x) for x in obj]
    return obj


async def main():
    print("→ Descargando histórico de Bonoloto...")
    sorteos = descargar_historico()
    print(f"  {len(sorteos)} sorteos cargados.")
    if len(sorteos) < 50:
        raise SystemExit(
            "ERROR: histórico insuficiente (<50 sorteos). Revisa la API key "
            "o la respuesta de la API."
        )

    historico = [s["numeros"] for s in sorteos]
    print(f"→ Ejecutando el motor de IA (cantidad={CANTIDAD})...")
    pipeline = PipelineV4(historico=historico, sorteos_completos=sorteos)
    resultado = await pipeline.ejecutar(CANTIDAD)

    apuestas_multiples = {}
    try:
        apuestas_multiples = calcular_apuestas_multiples(
            getattr(resultado, "scores_finales", {}) or {}
        )
    except Exception as e:  # noqa: BLE001
        print(f"  Aviso: no se pudieron calcular apuestas múltiples: {e}")

    salida = {
        "generado": datetime.now(timezone.utc).isoformat(),
        "fecha_sorteo": proxima_fecha_sorteo(),
        "total_historico": len(sorteos),
        "ultimo_sorteo": sorteos[0] if sorteos else None,
        "combinaciones": resultado.combinaciones,
        "apuestas_multiples": apuestas_multiples,
        "mejoras_activas": list(getattr(resultado, "mejoras_activas", []) or []),
    }

    os.makedirs(os.path.dirname(SALIDA), exist_ok=True)
    salida = _a_nativo(salida)  # numpy -> tipos nativos (JSON con números reales)
    with open(SALIDA, "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, indent=2, default=str)
    print(f"✓ Escrito {SALIDA} con {len(resultado.combinaciones)} "
          f"combinaciones para el sorteo del {salida['fecha_sorteo']}.")


if __name__ == "__main__":
    asyncio.run(main())
