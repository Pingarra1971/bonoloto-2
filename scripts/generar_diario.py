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
LIMITE_HISTORICO = int(os.getenv("LIMITE_HISTORICO", "500"))
ANIOS_HISTORICO = int(os.getenv("ANIOS_HISTORICO", "3"))
SALIDA = os.getenv("SALIDA_JSON", os.path.join(RAIZ, "docs", "combinaciones.json"))

# Histórico público de Bonoloto (CSV de Google Sheets, lotoideas.com).
# El plan gratuito de la API no permite descargar histórico, así que el
# histórico se toma de aquí y se mantiene al día con /results/bonoloto/latest.
HISTORICO_CSV_URL = os.getenv(
    "HISTORICO_CSV_URL",
    "https://docs.google.com/spreadsheets/d/e/"
    "2PACX-1vQALTRaLDFfhXOAQmeONPqmFKm9yOiQ4W97rhWgR41BZ7czFsjK5YktD6fnETKHGB9YUnyQ4XBSbhZx"
    "/pub?gid=0&single=true&output=csv",
)
CACHE_CSV = os.path.join(RAIZ, "data", "bonoloto_historico.csv")


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


def _fecha_iso(texto):
    """Convierte 'DD/MM/AAAA' (o DD/MM/AA) a 'AAAA-MM-DD'. None si no es fecha."""
    texto = (texto or "").strip()
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d"):
        try:
            return datetime.strptime(texto, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def _parsear_csv_historico(texto):
    """Convierte el CSV (fecha, 6 números, complementario) en sorteos.

    Formato de cada fila: DD/MM/AAAA,n1,n2,n3,n4,n5,n6,complementario
    (sin reintegro; no es relevante para el análisis). Las filas que no
    encajen — cabeceras, líneas vacías, datos corruptos — se descartan.
    """
    import csv as _csv
    import io as _io
    texto = (texto or "").lstrip("\ufeff")  # quita BOM si lo hubiera
    sorteos = {}
    for fila in _csv.reader(_io.StringIO(texto)):
        if len(fila) < 7:
            continue
        fecha = _fecha_iso(fila[0])
        if not fecha:
            continue  # cabecera o fila no válida
        try:
            numeros = [int(str(x).strip()) for x in fila[1:7]]
        except (ValueError, TypeError):
            continue
        if len(numeros) != 6 or not all(1 <= n <= 49 for n in numeros):
            continue
        comp = 0
        if len(fila) >= 8:
            try:
                comp = int(str(fila[7]).strip())
            except (ValueError, TypeError):
                comp = 0
        sorteos[fecha] = {
            "fecha": fecha,
            "numeros": numeros,
            "complementario": comp,
            "reintegro": 0,
            "bote": 0,
        }
    return sorteos


def _descargar_csv():
    """Descarga el CSV del histórico (con reintentos). Devuelve el texto o None."""
    ultimo_error = None
    for intento in range(1, 4):
        try:
            with httpx.Client(timeout=60, follow_redirects=True) as client:
                resp = client.get(HISTORICO_CSV_URL)
                resp.raise_for_status()
                return resp.text
        except Exception as e:  # noqa: BLE001
            ultimo_error = e
            print(f"  Descarga CSV intento {intento}/3 fallida: {e}")
            if intento < 3:
                time.sleep(5)
    print(f"  No se pudo descargar el CSV del histórico: {ultimo_error}")
    return None


def _obtener_ultimo():
    """Pide el último sorteo a la API (gratis). Devuelve un sorteo o None."""
    if not API_KEY:
        return None
    headers = {"X-API-Key": API_KEY, "Content-Type": "application/json"}
    url = f"{API_URL}/results/bonoloto/latest"
    try:
        with httpx.Client(timeout=30) as client:
            resp = client.get(url, headers=headers)
            resp.raise_for_status()
            cuerpo = resp.json()
    except Exception as e:  # noqa: BLE001
        print(f"  Aviso: no se pudo obtener el último sorteo: {e}")
        return None
    dato = cuerpo.get("data") if isinstance(cuerpo, dict) else cuerpo
    if isinstance(dato, list):
        dato = dato[0] if dato else None
    return _mapear_sorteo(dato) if dato else None


def descargar_historico():
    """Histórico de Bonoloto.

    El plan gratuito de la API NO permite descargar histórico (años pasados y
    rangos de fechas devuelven 403 Forbidden). Por eso el histórico se obtiene
    de un CSV público y abierto, y se mantiene al día con /results/bonoloto/latest
    (que sí funciona en el plan gratuito).
    """
    sorteos = {}

    # 1) Histórico desde el CSV público.
    texto = _descargar_csv()
    if texto:
        sorteos = _parsear_csv_historico(texto)
        print(f"  CSV histórico: {len(sorteos)} sorteos.")
        if not sorteos:
            muestra = texto[:300].replace("\n", " | ")
            print("  ── El CSV no encajó. Primeros 300 caracteres ──")
            print("  " + muestra)
            print("  ───────────────────────────────────────────────")
        # Copia local de respaldo (best-effort).
        try:
            os.makedirs(os.path.dirname(CACHE_CSV), exist_ok=True)
            with open(CACHE_CSV, "w", encoding="utf-8") as f:
                f.write(texto)
        except Exception:  # noqa: BLE001
            pass

    # 2) Si el CSV falló, usar la copia local de respaldo si existe.
    if not sorteos and os.path.exists(CACHE_CSV):
        try:
            with open(CACHE_CSV, "r", encoding="utf-8") as f:
                sorteos = _parsear_csv_historico(f.read())
            print(f"  Respaldo local: {len(sorteos)} sorteos.")
        except Exception as e:  # noqa: BLE001
            print(f"  No se pudo leer el respaldo local: {e}")

    # 3) Añadir el último sorteo oficial (mantiene el histórico al día).
    ultimo = _obtener_ultimo()
    if ultimo and ultimo.get("fecha"):
        if ultimo["fecha"] not in sorteos:
            print(f"  + Último sorteo añadido: {ultimo['fecha']} "
                  f"{ultimo['numeros']}")
        sorteos[ultimo["fecha"]] = ultimo

    lista = sorted(sorteos.values(), key=lambda s: s["fecha"], reverse=True)
    print(f"  Total sorteos válidos: {len(lista)}.")
    return lista


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


def calcular_estadisticas(sorteos):
    """Frecuencias por número (1-49) y clasificación caliente/frío/neutro.

    `sorteos` viene ordenado de más reciente (índice 0) a más antiguo, así que
    'ultima_aparicion_hace' = índice de la primera aparición. Mismas reglas que
    la pantalla de estadísticas de la app (umbral ±15% sobre lo esperado).
    """
    total = len(sorteos)
    if total == 0:
        return []
    apariciones = {n: [] for n in range(1, 50)}
    for i, s in enumerate(sorteos):
        for n in s.get("numeros", []):
            if 1 <= n <= 49:
                apariciones[n].append(i)
    esperada = 6 / 49
    stats = []
    for n in range(1, 50):
        idxs = apariciones[n]
        freq_total = len(idxs)
        rel = freq_total / total
        if rel > esperada * 1.15:
            clasif = "caliente"
        elif rel < esperada * 0.85:
            clasif = "frio"
        else:
            clasif = "neutro"
        stats.append({
            "numero": n,
            "frecuencia_total": freq_total,
            "frecuencia_ultimos_50": sum(1 for i in idxs if i < 50),
            "frecuencia_ultimos_100": sum(1 for i in idxs if i < 100),
            "frecuencia_ultimos_500": sum(1 for i in idxs if i < 500),
            "ultima_aparicion_hace": idxs[0] if idxs else None,
            "clasificacion": clasif,
        })
    return stats


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
        "estadisticas": calcular_estadisticas(sorteos),
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
