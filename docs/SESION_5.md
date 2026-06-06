# Sesión 5 — Bloque L reforzado

## Objetivo

Reforzar la parte del proyecto con valor matemático real: sistemas reducidos, anti-popularidad, Kelly, y conectar las predicciones al backtest de honestidad.

## 1. Sistemas reducidos verificados por fuerza bruta

**El hallazgo importante:** verifiqué exhaustivamente las 6 matrices de sistemas reducidos del Bloque L. Para cada sistema que afirma "garantiza G aciertos si aciertas K de tus N números", comprobé por fuerza bruta TODOS los C(N,K) subconjuntos posibles.

**Resultado: las 6 matrices son matemáticamente correctas.** Todas las garantías declaradas se cumplen, y varias son incluso conservadoras (garantizan más de lo que prometen):

| Sistema | Garantía declarada | Garantía real verificada |
|---|---|---|
| 7/3-4-5 | ≥3 si aciertan 4 | ≥4 (mejor que lo declarado) |
| 8/4 | ≥4 si aciertan 6 | ≥5 (mejor) |
| 9/4 | ≥4 si aciertan 6 | ≥5 (mejor) |
| 10/4 | ≥4 si aciertan 6 | ≥4 (exacto) |
| 12/3 | ≥3 si aciertan 5 | ≥3 (exacto) |
| 14/3 | ≥3 si aciertan 6 | ≥3 (exacto) |

Quien diseñó esas matrices hizo un buen trabajo. Esto ahora está **blindado con un test permanente** (`test_sistemas_reducidos.py`): si alguien edita una matriz y rompe la cobertura, el test salta.

## 2. Kelly fraccional (nuevo)

`app/domain/algorithms/kelly.py`. Honesto sobre lo que es:

- Con **EV negativo** (lo normal), la fracción de Kelly sale negativa (= no apuestes). El módulo lo confirma y, si el usuario va a jugar igual, recomienda una "fracción de entretenimiento" prudente (1% del bankroll por defecto), acotada por su límite mensual.
- Con **bote enorme** (EV+, raro), aplica Kelly fraccional (1/4 de Kelly) acotado a un máximo del 5%.
- La apuesta recomendada se redondea a múltiplos de 0.50€.

Verificado: bankroll 1000€ con bote 400k → Kelly teórico = -2.36 (no apostar), recomendación = 10€ (1%) con el mensaje honesto de que el EV es -58.8%.

Endpoint: `GET /api/bloque-l/kelly?bankroll_eur=X&bote_eur=Y&limite_mensual_eur=Z`

## 3. Anti-popularidad: honestidad sobre los datos

El comentario original decía "Datos basados en análisis de millones de boletos públicos" — **eso era falso**. SELAE no publica qué números juega la gente.

Lo corregí a una afirmación honesta: los patrones que detecta el scorer (cumpleaños ≤31, geometrías del boleto, secuencias, números "de la suerte") SÍ están bien documentados en la literatura sobre comportamiento de apostadores. Los conjuntos concretos de números "fuertes/débiles" son una **estimación heurística razonable, no una medición exacta**. El valor real está en evitar los PATRONES estructurales, donde el efecto es grande y establecido.

La lógica en sí es correcta y está testeada (secuencias y cumpleaños suben popularidad; números altos sin patrón la bajan).

## 4. Conexión predicción → backtest

Cuando el pipeline completa un cálculo, ahora registra automáticamente las combinaciones como predicciones en el servicio de honestidad (`_registrar_predicciones_honestidad`). Esto alimenta el backtest del dashboard: tras el sorteo, esas predicciones se evalúan y el dashboard muestra si el sistema acertó más que el azar.

El flujo completo queda:
1. Usuario genera combinaciones → se registran como predicciones (automático)
2. Tras el sorteo → `/api/honestidad/evaluar-sorteo` las evalúa
3. Dashboard muestra el backtest actualizado

El paso 2 automático (vía watchdog) se conectará en sesión 7.

## Tests

69 tests totales (52 + 17 nuevos):
- 6 de sistemas reducidos (incluyendo la verificación exhaustiva de garantías)
- 6 de Kelly
- 6 de anti-popularidad (en test_kelly_popularidad)

## Honestidad sobre lo no terminado

- **Anti-popularidad sigue siendo heurística.** Sin datos reales de SELAE, no puedo calibrarla con precisión. Lo que hay es lo mejor que se puede hacer con información pública, y ahora está documentado honestamente.
- **El registro automático predicción→backtest no está probado E2E** porque requiere el pipeline completo corriendo (8-50 min) contra BD real.
- **Kelly con bote enorme es conservador**: recomienda menos de lo que el Kelly puro permitiría. Para una herramienta de juego, errar por defecto es lo responsable.

## Próxima sesión

**Sesión 6 — Poda de algoritmos + framework de backtest serio.** Te presentaré la lista de los ~115 algoritmos con mi diagnóstico (conservar/fusionar/eliminar) para que decidas. Y construiré un framework de backtest que evalúe objetivamente el sistema sobre histórico real.
