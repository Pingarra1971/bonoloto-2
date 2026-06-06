# Sesión 2 — Task Queue + Persistencia + SSE

## Objetivo

Convertir el cálculo "fire-and-forget en RAM que muere con el proceso" en una **task queue persistente** con **streaming en tiempo real**.

## Cambios

### 1. Repo de trabajos abstraído (Protocol + 2 implementaciones)

**Antes:** clase única `TrabajosRepo` in-memory con dict global. Si el proceso reinicia, todos los trabajos en curso desaparecen sin rastro.

**Ahora:** 
- `RepoTrabajos` (Protocol async): contrato común.
- `TrabajosRepoMemoria`: in-memory con cap FIFO. Fallback en dev sin BD.
- `TrabajosRepoOracle`: write-through cache contra tabla `calculos` en Oracle ATP. Cada cambio se persiste; lecturas pegan a cache primero.

La factory `get_trabajos_repo()` elige automáticamente según haya BD o no. **El resto del código no se entera.**

```python
# Idéntico en ambos casos:
repo = await get_trabajos_repo()
trabajo = await repo.obtener(trabajo_id)
trabajo.estado = "completado"
await repo.guardar(trabajo)
```

### 2. WorkerPool async

**Antes:** `BackgroundTasks` de FastAPI. Cada petición lanza una tarea en el mismo proceso. Sin throttling, sin cola, sin límite. 10 peticiones simultáneas = 10 cálculos compitiendo por la CPU.

**Ahora:** patrón productor-consumidor con `asyncio.Queue`.

- N workers (default 2) consumen jobs en paralelo controlado.
- Cola con `max_pendientes` (default = `MAX_TRABAJOS_MEMORIA`).
- Si la cola se satura: HTTP 503 al cliente. **Backpressure**.
- Cierre limpio en lifespan: envía centinelas, espera con timeout, cancela si no responden.

**Por qué NO Dramatiq+Redis aún:**
Dramatiq sumaría una dependencia de infraestructura (Redis) que para uso personal con 1-2 cálculos simultáneos no aporta. La interfaz `WorkerPool.enqueue(JobCalculo)` ya está abstraída — si en el futuro escalas, sustituir esta clase es local. Hoy ganamos lo mismo (cola, throttling, persistencia) sin sumar piezas.

### 3. Server-Sent Events

**Antes:** polling cada 3s del frontend → un GET cada 3s × N usuarios × hasta 50 min/cálculo = ~1000 requests por sesión. Cada uno toca el repo.

**Ahora:** `GET /api/calculo/stream/{id}` devuelve un `text/event-stream`. El cliente abre **una conexión** y recibe eventos progresivos.

- Lectura del estado cada 1s (más rápido que polling de 3s).
- Solo emite si hay cambio respecto al payload anterior (dedup por hash).
- Ping keepalive cada 15s (proxies pueden cortar a 30-60s).
- Auto-cierre en `completado` o `error`.
- Timeout duro a 1h para limpiar conexiones zombi.

**Endpoint legacy `/progreso/{id}` mantenido** por compatibilidad con el frontend Flutter actual; Sesión 3 lo migrará a SSE.

### 4. Recuperación tras reinicio

**Antes:** reinicio del backend = trabajos en curso desaparecen silenciosamente. El frontend hace polling de un trabajo que ya no existe → 404 confuso.

**Ahora:** en el lifespan startup, `WorkerPool.iniciar()` llama a `repo.rehidratar_huerfanos()`. Para Oracle:

```sql
UPDATE calculos SET estado = 'error',
  error = 'Proceso reiniciado durante cálculo'
WHERE estado IN ('iniciando', 'encolado', 'calculando');
```

El frontend recibe un estado `error` claro. El usuario reintenta. Sin trabajos zombi.

### 5. Persistencia con throttling

**Antes:** N/A (no había persistencia).

**Ahora:** el callback del pipeline persiste cada delta significativo:
- Cambio de iteración
- ≥1% de progreso desde la última persistencia
- Cambio en `estado_algoritmos`

Pero con throttle hard: **mínimo 2s entre `UPDATE`s**. Esto evita saturar la BD con UPDATEs durante los primeros segundos del pipeline donde el progreso oscila rápido.

Resultado: un cálculo de 30 minutos genera ~50-100 UPDATEs a la BD, no miles. Carga manejable incluso con tier Always Free.

### 6. Bug latente #126 corregido

`BaseDatos` legacy usaba `oracledb.create_pool` (sync) dentro de async, con `with self._pool.acquire()` (sync). Cada query bloqueaba el event loop, serializando todas las peticiones HTTP bajo carga. **Solo se manifestaba con >1 cálculo concurrente**, por eso no se detectó.

`app/infrastructure/database/oracle.py` ahora usa `create_pool_async` y `async with` en todos los métodos. Los nuevos métodos para `calculos` también son async-native.

## Métricas de la sesión

- **6 archivos nuevos** (`worker_pool.py`, `trabajos_repo_oracle.py`, `test_worker_pool.py`, `test_worker_pool_e2e.py`, `run_tests.py`, este doc)
- **4 archivos modificados** (`trabajos_repo.py`, `oracle.py`, `servicio_calculo.py`, `calculo.py`, `main.py`, `admin.py`)
- **+1000 líneas** netas (worker pool + repo oracle + 7 nuevos métodos en BaseDatos + tests + docs)
- **37 tests pasando** (sesión 1: 23, sesión 2: 14 nuevos)

## Cómo probarlo

Sin BD (modo degradado, in-memory):
```bash
cd bonoloto_2
unset JWT_SECRET  # se generará efímero
uvicorn app.main:app --reload
# Lanzar un cálculo
curl -X POST http://localhost:8000/api/calculo/iniciar \
  -H "Authorization: Bearer <jwt>" \
  -H "Content-Type: application/json" \
  -d '{"cantidad": 3, "presupuesto_eur": 10, "bote_acumulado_eur": 600000}'
# Streaming SSE
curl -N http://localhost:8000/api/calculo/stream/<trabajo_id> \
  -H "Authorization: Bearer <jwt>"
```

Con Oracle ATP (modo persistente):
```bash
export ORACLE_USER=admin
export ORACLE_PASSWORD=...
export ORACLE_DSN=bonolotodb_high
export ORACLE_WALLET_LOCATION=/opt/wallet
uvicorn app.main:app
# Reiniciar el proceso a mitad de cálculo → al volver, el trabajo
# aparece marcado 'error' con mensaje 'Proceso reiniciado durante cálculo'.
```

## Próxima sesión

**Sesión 3 — Frontend Flutter modernizado.** Migración de Provider a Riverpod (elimina la clase entera de bugs como #115 setState-tras-await), `freezed` para modelos inmutables, `dio` con interceptors, y consumo SSE en lugar de polling.
