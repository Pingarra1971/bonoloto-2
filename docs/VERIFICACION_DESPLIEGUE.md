# Guía de verificación en despliegue — Bonoloto 2.0

Esta guía cubre los **dos puntos ciegos** que no se pueden verificar sin
desplegar: el **compilador de Flutter** y la **base de datos Oracle real**.
Todo lo demás (backend Python, 96 tests, matemática, algoritmos) ya está
verificado en desarrollo.

Sigue los pasos en orden. Cada uno dice qué comando correr, qué esperar, y
qué hacer si falla. Tiempo estimado total: 30-45 min.

---

## PARTE 1 — Frontend Flutter (el punto más frágil)

El código Dart no se ha podido compilar en desarrollo (no había SDK de
Flutter). Aquí es donde es más probable que aparezca algo, sobre todo
residuos de la migración Provider→Riverpod.

### Paso 1.1 — Análisis estático

```bash
cd <raíz del proyecto>
flutter pub get
dart analyze
```

**Qué esperar:** una lista de `info`, `warning` y puede que algún `error`.

**Qué hacer:**
- **`error`** → hay que corregirlo sí o sí (impide compilar). Los más
  probables, por la migración a Riverpod:
  - "Too many positional arguments" / "named parameter expected" → una
    llamada usa argumento posicional donde la firma pide nombrado (o al
    revés). Se corrige poniendo `nombre: valor`.
  - "The method 'X' isn't defined for the type 'AppNotifier'" → falta un
    método o está mal escrito el nombre.
  - "The getter 'X' isn't defined" → un campo de modelo renombrado.
- **`warning`** → conviene revisarlos, rara vez bloquean.
- **`info`** (la mayoría serán imports sin usar) → cosméticos, opcional.
  Sé que hay ~45 imports sin usar; `dart fix --apply` los limpia solo.

> Si `dart analyze` sale limpio de errores, el 90% del riesgo del frontend
> desaparece.

### Paso 1.2 — Limpieza automática opcional

```bash
dart fix --apply
```

Elimina imports sin usar y aplica correcciones seguras automáticas.
Vuelve a correr `dart analyze` después.

### Paso 1.3 — Compilación real

```bash
# Para probar que compila de verdad (elige tu plataforma):
flutter build apk --debug        # Android
# o
flutter build ios --debug --no-codesign   # iOS
# o
flutter run                      # en un dispositivo/emulador conectado
```

**Qué esperar:** que termine sin errores y genere el binario.

**Qué hacer si falla:** el mensaje de error apunta al archivo y línea
exactos. Los errores de compilación que `dart analyze` no detectó suelen ser
de tipos genéricos o de inicialización tardía.

### Paso 1.4 — Prueba funcional mínima (humo)

Con la app corriendo (`flutter run`):
1. **Arranque**: debe mostrar el splash "BONOLOTO 2.0" y luego la pantalla
   principal (no quedarse en blanco). Verifica el `_ArranqueGate`.
2. **Tabs**: pulsa las 5 pestañas (Inicio, Estadísticas, Honestidad,
   Historial, Ajustes). Ninguna debe crashear.
3. **Generar**: pulsa generar, elige cantidad (1-20), confirma. Debe ir a la
   pantalla de progreso. Si el backend está conectado, debe completar y
   mostrar combinaciones + la cobertura garantizada.
4. **Tema**: prueba el botón de cambiar tema (claro/oscuro) — verifica que
   `toggleTema` funciona.
5. **Ajustes**: cambia el toggle de notificaciones y el de Telegram —
   verifica que no crashean (usan `copyWith` sobre config inmutable).

---

## PARTE 2 — Base de datos Oracle (Autonomous DB / ATP)

El SQL se escribió siguiendo la documentación de Oracle, pero no se ejecutó
contra una instancia real. Ya apareció un caso en desarrollo donde la teoría
y Oracle no coincidían (el `INTERVAL` con bind variable), así que conviene
verificar el resto.

### Paso 2.1 — Arranque y creación de tablas

Configura las credenciales (`/etc/bonoloto-2.env` con `JWT_SECRET` y datos
de Oracle) y arranca el backend:

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**Qué esperar:** en el log, la creación de las 4 tablas (`sorteos`,
`calculos`, `apuestas`, `predicciones`) sin errores ORA-.

**Qué vigilar:** errores `ORA-00955` (objeto ya existe) están **controlados**
en el DDL (se ignoran). Cualquier **otro** ORA- al arrancar hay que mirarlo.

### Paso 2.2 — Probar cada operación SQL con datos reales

Estos son los métodos que conviene ejercitar, porque usan SQL específico de
Oracle que no se ha probado en vivo. Llama a los endpoints en este orden:

```bash
# Token (usa tu JWT_SECRET). El endpoint devuelve el campo "token".
TOKEN=$(curl -s -X POST localhost:8000/api/auth/token \
  -H "Content-Type: application/json" \
  -d '{"secret":"<tu JWT_SECRET>"}' | jq -r .token)

# 1. Health (no toca BD crítica)
curl localhost:8000/api/health

# 2. Memoria: backfill de unos sorteos (prueba MERGE + executemany)
curl -X POST localhost:8000/api/memoria/backfill \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '[{"fecha":"2024-01-01","numeros":[3,11,19,27,35,43],"complementario":7,"reintegro":2,"bote":0}]'

# 3. Memoria: estado (prueba COUNT y MAX)
curl localhost:8000/api/memoria/estado -H "Authorization: Bearer $TOKEN"

# 4. Memoria: sorteo nuevo (prueba MERGE idempotente)
curl -X POST localhost:8000/api/memoria/sorteo \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"fecha":"2024-01-03","numeros":[1,2,3,4,5,6],"complementario":7,"reintegro":0,"bote":100000}'

# 5. Estadísticas de números (prueba lectura masiva)
curl localhost:8000/api/estadisticas/numeros -H "Authorization: Bearer $TOKEN"

# 6. Cálculo completo (prueba calculo_upsert con MERGE + COALESCE)
curl -X POST localhost:8000/api/calculo/iniciar \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"cantidad":3,"presupuesto_eur":5.0}'
```

**Qué vigilar especialmente** (lo que de verdad no se ha probado en vivo):
- El **MERGE** de `insertar_sorteo` y `insertar_sorteos_lote` (idempotencia).
- El **`executemany` con MERGE** del backfill (deduplicado intra-lote).
- El **`COALESCE(:rj, resultado_json)`** del `calculo_upsert` (que el
  progreso no borre el resultado).
- El **`NUMTODSINTERVAL`** de la purga de cálculos antiguos (corre por
  scheduler; puedes forzarlo o esperar al ciclo).
- Que las **fechas** se guarden y lean bien (el helper `_parse_fecha_iso`
  acepta ISO con y sin 'Z').

**Si algo falla con ORA-:** el número de error dice qué pasa. Los típicos:
- `ORA-00904` (columna inválida) → nombre de columna mal escrito.
- `ORA-01843`/`ORA-01861` (fecha) → formato de fecha; revisa `_parse_fecha_iso`.
- `ORA-00001` (unique violated) → no debería pasar con MERGE; si pasa, el
  ON del MERGE no está casando la clave.

### Paso 2.3 — Verificar el watchdog (actualización automática)

El watchdog corre como servicio aparte y llama a estos endpoints tras cada
sorteo (21:45h hora española):
- `/api/health`
- `/api/memoria/sorteo`  (añade el sorteo a la memoria)
- `/api/modelos/reentrenar`

**Qué hacer:** revisa que el nombre del servicio systemd coincide. El
watchdog usa `bonoloto-ai` por defecto:

```bash
grep -n "bonoloto-ai" app/infrastructure/scheduler/watchdog.py
```

Si despliegas el servicio con otro nombre (ej. `bonoloto-2`), cámbialo ahí, o
crea el servicio systemd con el nombre `bonoloto-ai`. Si no, el reinicio
automático no funcionará (pero el resto sí).

---

## PARTE 3 — Backtest sobre histórico real

Una vez la memoria tenga sorteos reales cargados (backfill del histórico de
Bonoloto), el backtest del dashboard de honestidad mostrará lo que de verdad
habría pasado jugando el sistema.

**Qué esperar:** el backtest confirmará que la tasa de aciertos del sistema
**no supera** la del azar (≈0.73 aciertos por boleto de media). Esto no es un
fallo — es la confirmación honesta de que ningún algoritmo vence a un sorteo
aleatorio. Si el backtest mostrara lo contrario, sería un bug (estaría
midiendo mal), no un éxito.

---

## Resumen de prioridades

| Prioridad | Qué | Tiempo | Por qué |
|---|---|---|---|
| 🔴 Alta | `dart analyze` | 2 min | Detecta errores de compilación del frontend |
| 🔴 Alta | Arranque backend + creación tablas | 5 min | Confirma que Oracle acepta el DDL |
| 🟠 Media | Probar los 6 endpoints SQL | 15 min | Verifica el SQL no probado en vivo |
| 🟠 Media | `flutter run` + prueba de humo | 10 min | Confirma que la app funciona de verdad |
| 🟢 Baja | `dart fix --apply` (limpieza) | 2 min | Cosmético (imports sin usar) |
| 🟢 Baja | Nombre del servicio systemd | 1 min | Solo afecta reinicio automático |

Si la Parte 1 (`dart analyze` limpio) y la Parte 2.1-2.2 (Oracle acepta el
SQL) pasan, el sistema está verificado de punta a punta.
