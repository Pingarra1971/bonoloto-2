# Sesión 4 — Dashboard de Honestidad

## El compromiso cumplido

Esta sesión implementa el **dashboard de honestidad** que acordamos como condición del proyecto: una pantalla que muestra al usuario la verdad numérica de su relación con la Bonoloto, sin adornos.

## Matemática (verificada con 11 tests)

Todo el módulo `app/domain/honestidad_math.py` está blindado con tests que confirman:

| Constante / cálculo | Valor | Verificado |
|---|---|---|
| C(49,6) | 13.983.816 | ✅ |
| Σ P(k aciertos) | 1.0 | ✅ |
| P(6 aciertos) | 1/13.983.816 ≈ 7.15×10⁻⁸ | ✅ |
| Aciertos esperados/boleto al azar | 36/49 ≈ 0.7347 | ✅ |
| P(premio, ≥3) por boleto | ≈ 1.86% | ✅ |
| EV sin bote | **negativo** (~-59%) | ✅ |
| EV con bote 50M | favorable (teórico) | ✅ |

El EV negativo es el punto clave: **el test falla si alguien manipula los premios para hacer parecer que el sistema es rentable.** Si en el futuro alguien ajusta `TablaPremios` con valores irreales, el test `test_ev_sin_bote_es_negativo` lo detecta.

## KPIs del dashboard

### 1. Balance (P&L)
- Total apostado (suma de costes de todas las apuestas registradas)
- Total ganado (suma de premios de las apuestas evaluadas)
- Balance neto (verde si positivo, rojo si negativo)

### 2. Valor Esperado
- EV de una apuesta hoy (según el bote actual)
- Pérdida esperada acumulada (lo que la matemática predice que perderás)
- Tu resultado vs lo esperado (¿estás peor o mejor que la expectativa? — normalmente es ruido)

### 3. El sistema vs el azar (backtest honesto)
La parte más importante. Compara:
- Aciertos medios del **sistema** (de las predicciones que generó ANTES de cada sorteo)
- Aciertos esperados **al azar** (0.7347/boleto, constante teórica)
- Veredicto textual honesto que se adapta al tamaño de muestra:
  - <30 predicciones → "muestra pequeña, sin conclusiones"
  - diferencia <0.05 → "indistinguible del azar, como predice la matemática"
  - diferencia >0 → "podría ser ruido afortunado, con más datos tenderá a cero"

### 4. Coste de oportunidad
Lo apostado invertido en un índice (~7% anual MSCI World) cuánto valdría. Dato de contexto, no consejo financiero.

## Arquitectura

**Backend:**
```
app/domain/honestidad_math.py          matemática pura (11 tests)
app/services/honestidad/
  └── servicio_honestidad.py           registro + KPIs (4 tests)
app/api/routes/honestidad.py           5 endpoints
app/infrastructure/database/oracle.py  +tablas apuestas, predicciones
```

**Endpoints:**
- `POST /api/honestidad/apuesta` — registrar apuesta real
- `POST /api/honestidad/prediccion` — registrar predicción del sistema
- `POST /api/honestidad/evaluar-sorteo` — evaluar pendientes contra resultado
- `GET /api/honestidad/estadisticas` — snapshot de KPIs
- `GET /api/honestidad/ev` — EV educativo dado el bote

**Frontend:**
```
lib/models/honestidad.dart             4 modelos inmutables
lib/screens/honestidad_screen.dart     pantalla completa
lib/main.dart                          +tab "Rendimiento" (5 tabs ahora)
```

## Integración con el flujo de cálculo

El registro de predicciones para el backtest se conecta así (a completar en sesión 5):
1. El usuario genera combinaciones → el sistema las registra vía `/api/honestidad/prediccion`
2. Tras el sorteo, el watchdog (sesión 2) llama `/api/honestidad/evaluar-sorteo`
3. El dashboard muestra el backtest actualizado

**Nota:** el paso 1-2 automático se conectará en sesión 5/7. Por ahora los endpoints existen y funcionan manualmente.

## Modo incógnito

Respetado: si `config.modoIncognito` está activo, `registrarApuesta()` en el AppNotifier devuelve sin registrar nada. El usuario puede usar la app sin afectar su tracker.

## Recursos de juego responsable

El disclaimer al pie del dashboard incluye:
- Probabilidad real (1 entre 13.983.816)
- jugarbien.es y el teléfono de la FEJAR (900 200 225)

## Tests

52 tests totales (37 anteriores + 15 nuevos):
- 11 de matemática de honestidad
- 4 del servicio (registro, evaluación, P&L, backtest)

## Honestidad sobre lo no terminado

- **No probé los endpoints contra BD Oracle real.** Las tablas `apuestas` y `predicciones` y sus MERGE statements están escritos pero sin verificar contra una instancia real. Mismo riesgo que sesión 2: la sintaxis Oracle (MERGE, INTERVAL) puede tener algún detalle.
- **El RTP modelado (~41%) no es exactamente el oficial (~55%)** porque no modelo la categoría 5+C (5 aciertos + complementario) ni el detalle de reparto del fondo. Es una aproximación honesta y conservadora — si acaso, sobreestima la pérdida, que es el lado seguro para un dashboard de honestidad.
- **El frontend no está compilado** (sin Flutter SDK). Validación estructural solamente.

## Próxima sesión

**Sesión 5 — Bloque L reforzado.** La parte con valor matemático real:
- Anti-popularidad calibrada con datos de SELAE
- Sistemas reducidos con cobertura verificada por fuerza bruta
- Kelly fraccional
- Conexión del registro de predicciones al flujo de cálculo (para alimentar el backtest del dashboard automáticamente)
