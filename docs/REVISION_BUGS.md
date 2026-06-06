# Revisión final de bugs — Sesión 7-8

Esta es la revisión exhaustiva que pediste al inicio del proyecto, ahora sobre el código refactorizado de Bonoloto 2.0.

## Metodología

Auditoría sistemática por categorías de anti-patrones:
1. Manejo de errores (except desnudos, swallowing)
2. Divisiones por cero sin guarda
3. Race conditions / acceso a estado compartido en async
4. Null-safety en Dart (.first/.last sin isEmpty)
5. setState tras await sin mounted (bug #115)
6. Validación de entrada en endpoints
7. Dialecto SQL Oracle
8. Memory leaks (StreamSubscription/Timer/Controller sin dispose)

## Bugs encontrados y corregidos

### #127 — Tipo incorrecto en parámetro de query Kelly
`app/api/routes/bloque_l.py`: `limite_mensual_eur: float = Query(default=None)`. El tipo declaraba `float` pero el default era `None`. En Pydantic v2 / FastAPI esto puede provocar error de validación al arrancar o al recibir la petición sin el parámetro. **Corregido** a `Optional[float]`.

### #128 — Sintaxis INTERVAL inválida en Oracle (habría petado en producción)
`app/infrastructure/database/oracle.py`: `calculos_purgar_antiguos` usaba:
```sql
AND completado < CURRENT_TIMESTAMP - INTERVAL :d DAY
```
**Oracle NO acepta bind variables en literales INTERVAL.** Esto habría lanzado ORA-00911 o similar en la primera ejecución de la purga. **Corregido** a:
```sql
AND completado < CURRENT_TIMESTAMP - NUMTODSINTERVAL(:d, 'DAY')
```
que sí admite bind variables. Es exactamente el tipo de bug de dialecto SQL que advertí en sesiones 2 y 4 que podría existir.

### #130 — MERGE borraba el resultado_json con NULL en cada update de progreso
`app/infrastructure/database/oracle.py`: `calculo_upsert`. Durante el cálculo, `guardar()` se llama repetidamente con `resultado_json=None` (updates de progreso). El MERGE hacía `resultado_json = :rj`, poniendo NULL cada vez. Si por el orden async un update de progreso se entrelazaba tras el de "completado", **borraba el resultado ya calculado**. **Corregido** con:
```sql
resultado_json = COALESCE(:rj, resultado_json)
```
Ahora el resultado solo se sobrescribe cuando llega un valor no-NULL; los updates de progreso lo preservan.

## Verificaciones que pasaron (no eran bugs)

### Divisiones por cero
Todas las divisiones revisadas tienen guarda:
- `backtest_framework.py:116` y `honestidad_math.py:218`: protegidas por `if n == 0: return` previo.
- `motor_ia.py:171`: usa `+ 1e-8` (epsilon) como guarda.
- Resto: tienen `if suma > 0`, `or 1`, etc.

### Null-safety Dart (.first/.last)
Los 4 accesos `.first` tienen guarda `isNotEmpty` o `isEmpty → return` previa:
- `secondary_screens.dart:135`: `if (sesion.combinaciones.isNotEmpty)` antes
- `dashboard_screen.dart:121`: `if (provider.historial.isNotEmpty)` antes
- `dashboard_screen.dart:464`: ternario `isNotEmpty ? .first : null`
- `estadisticas_screen.dart:454`: `if (top10.isEmpty) return` antes

### Bug #115 (setState tras await sin mounted)
**Cero ocurrencias.** La migración a Riverpod eliminó la clase entera; los pocos `setState` que quedan en `ConsumerState` tienen `if (!mounted) return` previo.

### Memory leaks
- `secondary_screens.dart`: 5 TextEditingController declarados, 5 disposed.
- `progreso_screen.dart`: AnimationController disposed.
- `app_notifier.dispose()`: cancela `_streamProgreso` y `_timerSorteo`.
- `sse_client`: cleanup completo en `onCancel`, error y done paths.

### Race conditions
Accesos a dict compartido en asyncio son atómicos (GIL, sin await intermedio). `TrabajosRepoOracle` usa locks por trabajo_id para operaciones compuestas.

### except swallowing
No hay `except:` desnudos. Los `except...pass` revisados son fallbacks legítimos (parseo de fecha defensivo, lectura de meminfo con default).

## Bugs históricos (sesiones anteriores) — estado

Todos los bugs #103-#126 de las sesiones anteriores siguen corregidos en el código. Verificado en sesión 1 que los fixes están presentes.

## Total de bugs del proyecto

| Rango | Sesión | Cantidad |
|---|---|---|
| #103-#126 | Revisiones previas (heredadas) | 24 |
| #127-#130 | Revisión final (sesión 7-8) | 4 |
| **Total** | | **28** |
