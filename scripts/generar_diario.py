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
# Y los módulos nuevos que viven en esta misma carpeta (scripts/).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.pipeline.pipeline_v4 import PipelineV4  # noqa: E402
from app.domain.apuesta_multiple import calcular_apuestas_multiples  # noqa: E402
import sistema_garantizado  # noqa: E402  (Fase A: sistema con garantía)

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
HISTORIAL_ACIERTOS = os.path.join(RAIZ, "data", "historial_aciertos.json")


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


def _guardar_historico_limpio(sorteos: dict):
    """Escribe el histórico fusionado y validado a disco, en formato
    'AAAA-MM-DD,n1,...,n6,complementario', ordenado de antiguo a reciente.
    Es la copia AUTORIZADA del repo: se auto-repara cada día (sin duplicados,
    sin filas inválidas) y sobrevive aunque la fuente externa caiga."""
    try:
        os.makedirs(os.path.dirname(CACHE_CSV), exist_ok=True)
        with open(CACHE_CSV, "w", encoding="utf-8") as f:
            for fecha in sorted(sorteos):
                s = sorteos[fecha]
                nums = ",".join(str(n) for n in s["numeros"])
                comp = s.get("complementario", 0) or 0
                f.write(f"{fecha},{nums},{comp}\n")
        return True
    except Exception as e:  # noqa: BLE001
        print(f"  Aviso: no se pudo guardar el histórico limpio: {e}")
        return False


def descargar_historico():
    """Histórico de Bonoloto, AUTO-REPARABLE.

    El plan gratuito de la API NO permite descargar histórico, así que el
    histórico se obtiene de un CSV público y se mantiene al día con
    /results/bonoloto/latest. Para no perder nunca datos, esta versión FUSIONA
    tres fuentes (sin duplicar y validando todo):
      1) el histórico limpio ya guardado en el repo (base autorizada),
      2) el CSV público recién descargado,
      3) el último sorteo oficial de la API.
    Luego reescribe el histórico limpio en disco (auto-reparado).
    """
    sorteos = {}

    # 1) Base: histórico limpio ya guardado en el repo (nunca perdemos datos).
    if os.path.exists(CACHE_CSV):
        try:
            with open(CACHE_CSV, "r", encoding="utf-8") as f:
                base = _parsear_csv_historico(f.read())
            sorteos.update(base)
            print(f"  Histórico guardado (base): {len(base)} sorteos.")
        except Exception as e:  # noqa: BLE001
            print(f"  Aviso: no se pudo leer el histórico guardado: {e}")

    # 2) Fusionar el CSV público recién descargado.
    texto = _descargar_csv()
    if texto:
        nuevos = _parsear_csv_historico(texto)
        if nuevos:
            antes = len(sorteos)
            sorteos.update(nuevos)  # fusiona por fecha (sin duplicar)
            print(f"  CSV público: {len(nuevos)} sorteos "
                  f"(+{len(sorteos) - antes} nuevos).")
        else:
            muestra = texto[:300].replace("\n", " | ")
            print("  ── El CSV no encajó. Primeros 300 caracteres ──")
            print("  " + muestra)

    # 3) Fusionar el último sorteo oficial de la API.
    ultimo = _obtener_ultimo()
    if ultimo and ultimo.get("fecha"):
        if ultimo["fecha"] not in sorteos:
            print(f"  + Último sorteo añadido: {ultimo['fecha']} "
                  f"{ultimo['numeros']}")
        sorteos[ultimo["fecha"]] = ultimo

    # 4) Auto-reparar: reescribir el histórico limpio (sin duplicados ni
    #    filas inválidas, ya garantizado por el parser y el merge por fecha).
    if sorteos:
        _guardar_historico_limpio(sorteos)

    lista = sorted(sorteos.values(), key=lambda s: s["fecha"], reverse=True)
    print(f"  Total sorteos válidos (auto-reparado): {len(lista)}.")
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


def _evaluacion_anterior(ruta, ultimo_sorteo):
    """Lee el archivo del día anterior y, si su predicción era PARA el sorteo
    que acaba de celebrarse, calcula cuántos números acertó cada combinación.

    Devuelve un dict 'evaluacion' o None si no hay nada que comparar (por
    ejemplo, la primera vez o si no coinciden las fechas)."""
    if not ultimo_sorteo:
        return None
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            previo = json.load(f)
    except (FileNotFoundError, ValueError):
        return None
    prev_fecha = previo.get("fecha_sorteo")
    prev_combos = previo.get("combinaciones") or []
    fecha_resultado = ultimo_sorteo.get("fecha")
    # Solo comparamos si la predicción anterior era justo para este sorteo.
    if not prev_fecha or not prev_combos or prev_fecha != fecha_resultado:
        return None
    ganadores = set(ultimo_sorteo.get("numeros") or [])
    predicciones = []
    mejor = 0
    for c in prev_combos:
        nums = c.get("numeros") if isinstance(c, dict) else None
        if not nums:
            continue
        aciertos = len(set(nums) & ganadores)
        if aciertos > mejor:
            mejor = aciertos
        predicciones.append({"numeros": list(nums), "aciertos": aciertos})
    if not predicciones:
        return None
    return {
        "fecha_sorteo": prev_fecha,
        "numeros_ganadores": list(ultimo_sorteo.get("numeros") or []),
        "complementario": ultimo_sorteo.get("complementario"),
        "reintegro": ultimo_sorteo.get("reintegro"),
        "predicciones": predicciones,
        "mejor_aciertos": mejor,
    }


def _referencia_azar(n_combos, trials=2000, seed=12345):
    """Monte Carlo: cuántos números acertaría DE MEDIA la mejor de n_combos
    combinaciones de 6, frente a un sorteo, por PURO AZAR. Es el listón honesto
    contra el que comparar lo que acierta la app."""
    import random as _r
    rng = _r.Random(seed)
    universo = list(range(1, 50))
    n = max(1, int(n_combos))
    total = 0
    for _ in range(trials):
        ganador = set(rng.sample(universo, 6))
        mejor = 0
        for _c in range(n):
            h = len(set(rng.sample(universo, 6)) & ganador)
            if h > mejor:
                mejor = h
        total += mejor
    return round(total / trials, 2)


def _actualizar_track_record(evaluacion):
    """Acumula el resultado de cada comparación (cuántos acertó la app cada
    sorteo) y devuelve un resumen honesto a lo largo del tiempo. A prueba de
    fallos: nunca rompe la generación diaria."""
    registros = []
    try:
        if os.path.exists(HISTORIAL_ACIERTOS):
            with open(HISTORIAL_ACIERTOS, "r", encoding="utf-8") as f:
                registros = (json.load(f) or {}).get("registros", [])
    except Exception:  # noqa: BLE001
        registros = []

    # Añadir el registro de hoy si hay una evaluación nueva.
    if evaluacion:
        aciertos = [p.get("aciertos", 0)
                    for p in (evaluacion.get("predicciones") or [])]
        if aciertos:
            reg = {
                "fecha": evaluacion.get("fecha_sorteo"),
                "mejor": int(max(aciertos)),
                "media": round(sum(aciertos) / len(aciertos), 2),
                "n": len(aciertos),
            }
            registros = [r for r in registros
                         if r.get("fecha") != reg["fecha"]]
            registros.append(reg)

    # Dedupe por fecha, ordenar y limitar a los últimos 180.
    porfecha = {r["fecha"]: r for r in registros if r.get("fecha")}
    registros = [porfecha[f] for f in sorted(porfecha)][-180:]

    # Guardar el acumulado (copia autorizada en el repo).
    try:
        os.makedirs(os.path.dirname(HISTORIAL_ACIERTOS), exist_ok=True)
        with open(HISTORIAL_ACIERTOS, "w", encoding="utf-8") as f:
            json.dump({"registros": registros}, f,
                      ensure_ascii=False, indent=2)
    except Exception as e:  # noqa: BLE001
        print(f"  Aviso: no se pudo guardar el historial de aciertos: {e}")

    if not registros:
        return None

    mejores = [r["mejor"] for r in registros]
    n_sorteos = len(registros)
    dist = {"0": 0, "1": 0, "2": 0, "3+": 0}
    for m in mejores:
        dist["3+" if m >= 3 else str(m)] += 1
    n_medio = max(1, round(sum(r.get("n", 1) for r in registros) / n_sorteos))

    return {
        "n_sorteos": n_sorteos,
        "media_mejor": round(sum(mejores) / n_sorteos, 2),
        "mejor_historico": max(mejores),
        "distribucion": dist,
        "referencia_azar": _referencia_azar(n_medio),
        "registros": [{"fecha": r["fecha"], "mejor": r["mejor"]}
                      for r in registros[-60:]],
    }


def _numeros_favoritos(combinaciones) -> list:
    """Ordena los números por cuánto los 'recomienda' el motor de los 115
    algoritmos: frecuencia en las combinaciones del día, ponderada por el
    índice de confianza de cada una. Desempata por anti-popularidad (sesgo de
    cumpleaños: los números > 31 reparten con menos gente).

    Honesto: esto NO sube la probabilidad de que esos números salgan; solo
    decide qué números forman el grupo del sistema con garantía."""
    from collections import defaultdict
    peso = defaultdict(float)
    for c in combinaciones or []:
        nums = c.get("numeros") if isinstance(c, dict) else getattr(c, "numeros", [])
        conf = (c.get("indice_confianza") if isinstance(c, dict)
                else getattr(c, "indice_confianza", 50)) or 50
        for n in nums or []:
            peso[int(n)] += float(conf)

    def popularidad(n):  # menor = menos popular (mejor reparto)
        return 0 if n > 31 else (1 if n > 12 else 2)

    return sorted(peso.keys(), key=lambda n: (-peso[n], popularidad(n), n))


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

    # IMPORTANTE: leer la predicción del día anterior ANTES de sobrescribir el
    # archivo, para comparar esa predicción con el resultado que acaba de salir.
    evaluacion = _evaluacion_anterior(SALIDA, sorteos[0] if sorteos else None)

    # Track record honesto: acumula cuánto acierta la app sorteo a sorteo.
    track_record = _actualizar_track_record(evaluacion)
    if track_record:
        print(f"  Track record: {track_record['n_sorteos']} sorteos, "
              f"media mejor {track_record['media_mejor']} "
              f"(azar ~{track_record['referencia_azar']}).")

    fecha_sorteo = proxima_fecha_sorteo()

    # Fase A — Sistema de apuestas con garantía combinatoria verificada
    # (pool anti-popular + wheel). Determinista: misma fecha ⇒ mismo sistema.
    #
    # Política de errores (importante):
    #  - Si la garantía NO se verifica por fuerza bruta, generar_sistema_diario
    #    hace SystemExit y el workflow se pone en ROJO. Jamás publicamos un
    #    sistema sin garantía real. (No lo capturamos: debe propagarse.)
    #  - Si falla por cualquier OTRO motivo inesperado (un error puntual), lo
    #    registramos y seguimos publicando el JSON v1 de siempre, para no dejar
    #    a la app sin su actualización diaria.
    sistemas_v2 = None
    print("→ Construyendo sistemas con garantía (3 niveles: Económico / "
          "Equilibrado / Fuerte)...")
    try:
        favoritos = _numeros_favoritos(resultado.combinaciones)
        print(f"  Grupo base (motor de algoritmos): "
              f"{favoritos[:12]}")
        sistemas_v2 = sistema_garantizado.generar_sistemas_diarios(
            fecha_sorteo, pool_base=favoritos)
        for s in sistemas_v2["sistemas"]:
            print(f"  ✓ {s['nombre']}: {s['n_apuestas']} apuestas, "
                  f"{s['coste_eur']} EUR, garantía verificada.")
    except Exception as e:  # noqa: BLE001  (SystemExit NO es Exception: se propaga)
        print(f"  AVISO: no se pudieron generar los sistemas ({e}). "
              "Se publica el JSON v1 sin el bloque 'sistemas'.")

    salida = {
        "generado": datetime.now(timezone.utc).isoformat(),
        "fecha_sorteo": fecha_sorteo,
        "total_historico": len(sorteos),
        "estadisticas": calcular_estadisticas(sorteos),
        "ultimo_sorteo": sorteos[0] if sorteos else None,
        "evaluacion": evaluacion,
        "track_record": track_record,
        "combinaciones": resultado.combinaciones,
        "apuestas_multiples": apuestas_multiples,
        "mejoras_activas": list(getattr(resultado, "mejoras_activas", []) or []),
    }

    # ── Esquema v2 (retrocompatible): solo si los sistemas se generaron bien.
    # La app v1 ignora estas claves; la app v2 (Fase B) las aprovechará.
    if sistemas_v2 is not None:
        # Bloque legacy 'sistema'/'apuestas' = el nivel Equilibrado, para no
        # romper nada que ya lea esas claves.
        equil = next((s for s in sistemas_v2["sistemas"]
                      if s["nombre"] == "Equilibrado"),
                     sistemas_v2["sistemas"][0])
        salida["version_esquema"] = 2
        salida["fecha"] = fecha_sorteo  # alias del esquema v2
        salida["sistema"] = {
            "pool": equil["pool"],
            "garantia": equil["garantia"],
            "verificada_fuerza_bruta": equil["verificada_fuerza_bruta"],
            "n_apuestas": equil["n_apuestas"],
            "coste_eur": equil["coste_eur"],
        }
        salida["apuestas"] = equil["apuestas"]
        salida["honestidad"] = {
            "nota": sistema_garantizado.NOTA_HONESTIDAD,
            "backtest_ultima_fecha": None,
            "scorers_superan_azar": [],
        }
        # NUEVO (mejoras 1 y 2): los 3 niveles + tabla de probabilidades.
        salida["sistemas"] = sistemas_v2["sistemas"]
        salida["probabilidades_categoria"] = \
            sistemas_v2["probabilidades_categoria"]
    else:
        salida["version_esquema"] = 1

    os.makedirs(os.path.dirname(SALIDA), exist_ok=True)
    salida = _a_nativo(salida)  # numpy -> tipos nativos (JSON con números reales)
    with open(SALIDA, "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, indent=2, default=str)
    print(f"✓ Escrito {SALIDA} con {len(resultado.combinaciones)} "
          f"combinaciones para el sorteo del {salida['fecha_sorteo']}.")


if __name__ == "__main__":
    asyncio.run(main())
