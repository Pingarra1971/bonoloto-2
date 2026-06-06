# Sesión 3 — Frontend Flutter modernizado

## Objetivo

Migrar el frontend de **Provider + http** a **Riverpod + dio + SSE**, sin perder funcionalidad y con cambios incrementales conservadores.

## Decisiones de diseño honestas

### 1. NO usar freezed

Inicialmente lo planifiqué. Al revisar el tamaño real de los modelos (295 líneas en total) y el coste de freezed (genera ~500 líneas por modelo, requiere `build_runner`, complica el dev loop), llegué a la conclusión de que **dataclasses Dart manuales bien escritas resuelven los mismos problemas** (inmutabilidad, parseo seguro, copyWith) en menos líneas y sin generación de código.

Resultado: 295 líneas → 7 archivos limpios, ~1100 líneas con docs y null-safety completos.

### 2. NO usar `package:provider` como adaptador

Empecé escribiendo un adaptador `AppProvider` (legacy API) sobre `AppNotifier` (Riverpod), pero el patrón es frágil porque `package:provider` y `flutter_riverpod` son sistemas independientes de propagación. Mejor reescribir los screens.

### 3. SÍ migrar screens automáticamente con un script

12 ocurrencias de `context.watch<AppProvider>()` en 4 archivos × patrones repetidos = mecanizable. Script `migrar_screens.py` aplicó:

- `StatelessWidget` → `ConsumerWidget` (y `build(...context, WidgetRef ref)`)
- `StatefulWidget` → `ConsumerStatefulWidget` + `ConsumerState`
- `context.watch<AppProvider>()` → `ref.watch(appProvider.notifier)` + `ref.watch(appProvider)`
- `context.read<AppProvider>()` → `ref.read(appProvider.notifier)`
- `withOpacity(x)` → `withValues(alpha: x)` (deprecación Flutter 3.27)
- `textScaleFactor` → `textScaler` (deprecación Flutter 3.16)

Total: **187 líneas modificadas automáticamente + 10 sustituciones de `withOpacity`**, 0 errores estructurales en validación.

### 4. Pasada correctiva post-script

El script automatizado introdujo dos clases de bugs sutiles:

**Bug A** — `Widget build(BuildContext context, WidgetRef ref)` añadido también a `ConsumerState` (donde el `ref` viene heredado, no por parámetro). Corregido con `fix_migration.py` que reconoce el patrón clase-por-clase.

**Bug B** — `ref.watch(appProvider.notifier)` no dispara rebuild (devuelve el notifier estable). Corregido sustituyendo por el patrón:
```dart
ref.watch(appProvider);    // dispara rebuild
final provider = ref.read(appProvider.notifier);   // usar para métodos
```

## Estructura nueva

```
lib/
├── main.dart                    [Riverpod ProviderScope]
├── models/
│   ├── json_helpers.dart        asDouble/asInt/asBool tolerantes
│   ├── credenciales.dart        inmutable + copyWith
│   ├── combinacion.dart         + esValida + estrategia + metricas
│   ├── sorteo.dart              ResultadoSorteo + EstadisticasNumero + RendimientoAlgoritmo
│   ├── estado.dart              EstadoCalculo (+encolado!) + EstadoAlgoritmo + ProgresoCalculo
│   ├── sesion.dart              SesionPrediccion + ConfiguracionApp (+modoIncognito)
│   └── models.dart              barrel
├── services/
│   ├── api_client.dart          [NUEVO] dio + interceptors
│   ├── sse_client.dart          [NUEVO] cliente SSE bare-metal
│   ├── backend_service.dart     [NUEVO] reemplaza oracle_service.dart
│   └── ...                      (legacy preservados)
├── state/                       [NUEVO directorio]
│   ├── app_state.dart           inmutable
│   └── app_notifier.dart        StateNotifier + getters de compat
├── providers/
│   └── app_provider.dart        [LEGACY: adaptador no usado, conservado por seguridad]
└── screens/
    ├── dashboard_screen.dart    migrado a ConsumerStatefulWidget
    ├── estadisticas_screen.dart migrado
    ├── progreso_screen.dart     migrado
    └── secondary_screens.dart   migrado
```

## Cambios destacables

### `ApiClient` (dio + interceptors)

Reemplaza al uso crudo de `package:http`. Incluye:

- **Timeouts conservadores**: 15s connect, 30s receive. Antes (v7) muchas llamadas no tenían timeout y podían colgarse indefinidamente (bugs #109, #110 sesión 1).
- **AuthInterceptor**: inyecta `Authorization: Bearer <token>` si está configurado.
- **RetryInterceptor**: reintenta 2 veces con backoff exponencial. Solo en GET (idempotente). POST `/api/calculo/iniciar` no se reintenta.
- **CancelToken**: dio nativo permite cancelar peticiones en curso sin gestionar flags manuales (lo que antes era el bug #109: `dispose()` no cancelaba polling).

### `SseClient` (Server-Sent Events)

Cliente bare-metal porque dio no soporta SSE streaming nativo. Parsea el protocolo manualmente:
- Eventos separados por línea en blanco
- Campos `event:` y `data:` reconocidos
- Ping `:keepalive` ignorado correctamente
- Cierre limpio al cancelar el stream del cliente

### `AppNotifier` (Riverpod StateNotifier)

Reemplaza el `AppProvider` (ChangeNotifier). Mejoras estructurales:

- **Estado inmutable** (`AppState` con `copyWith`). Imposible olvidarse de `notifyListeners()` porque no existe — `state = state.copyWith(...)` notifica automáticamente.
- **`if (!mounted)` ya no es necesario**: Riverpod gestiona el ciclo de vida del notifier automáticamente. **Bug #115 imposible por construcción.**
- **Timezone correcto** (`Europe/Madrid` con DST automático). Bug #111 (UTC+1 fijo) corregido en sesión 1; mantenido aquí.
- **Modo incógnito**: nuevo flag `config.modoIncognito` que omite persistir sesiones en el historial cuando está activo.
- **SSE integrado**: `iniciarCalculo()` se suscribe al stream SSE del backend; cuando el state cambia, la UI rebuilda automáticamente.

### Getters de compatibilidad en AppNotifier

Para no reescribir los screens entero, expongo `config`, `credenciales`, `historial`, etc. como getters delegados al state. Los screens hacen `ref.watch(appProvider)` para suscribirse y luego acceden a `provider.config` (donde `provider = ref.read(appProvider.notifier)`).

Esta es la forma menos invasiva de migrar sin reescribir cada `provider.xxx` → `state.xxx`.

## Métodos nuevos en AppNotifier

| Método | Estado |
|---|---|
| `inicializar()` | ✅ Migrado |
| `actualizarCredenciales()` | ✅ Migrado |
| `actualizarConfiguracion()` | ✅ Migrado |
| `activarModoIncognito(bool)` | ✅ Nuevo (sesión 3) |
| `iniciarCalculo()` | ✅ Migrado + SSE |
| `cancelarCalculo()` | ✅ Migrado |
| `cargarEstadisticas()` | ✅ Migrado (mínimo viable; ampliación sesión 4) |
| `eliminarSesion(id)` | ✅ Migrado |
| `obtenerUltimosSorteos()` | 🔶 Stub — API loterías necesita revisión sesión 4 |
| `exportarSesion()` | 🔶 Stub — ExportService legacy necesita refactor sesión 7 |
| `hacerBackup()` | 🔶 Stub — Google Drive integration sesión 7 |
| `restaurarBackup()` | 🔶 Stub — sesión 7 |

Los stubs **devuelven valores neutros** (null/false/[]) y los botones de la UI **no crashean**, solo no hacen nada visible. El usuario lo notará pero la app no se rompe.

## Lo que no compilaré en sesión 3 (honestidad)

No tengo el SDK de Flutter disponible para compilar el APK. **Las validaciones que hice son estructurales** (balance de llaves, imports correctos, consistencia ConsumerWidget/State). Pero podría haber **errores de tipos** que solo `dart analyze` detectaría.

Cuando lo compiles, los errores más probables son:
- **Tipos en mapas/listas**: `Map<String, dynamic>` vs `Map<dynamic, dynamic>` en algunos paths de parseo.
- **Const constructors**: si `const ConfiguracionApp()` se intenta usar donde se modifica.
- **Imports faltantes**: si algún `widget.dart` usaba `AppProvider` y no migré.

Tiempo estimado de corrección si aparecen: 30-60 minutos. Los errores serán claros y locales.

## Tests del frontend

No hay framework de tests funcional sin Flutter SDK. La validación se hace por:
1. Balance estructural de llaves/paréntesis/corchetes (24/26 archivos `(0,0,0)`).
2. Validador de consistencia ConsumerWidget/State (0 errores).
3. Verificación de imports (0 imports rotos).

## Próxima sesión

**Sesión 4 — Dashboard de honestidad.** Pestaña principal nueva con:
- P&L tracker (cuánto has apostado, cuánto has ganado, balance neto)
- EV teórico vs real
- Backtest del propio sistema (combinaciones registradas antes del sorteo, comparadas después)
- Coste de oportunidad

Esto requiere:
- Backend: nuevo endpoint `/api/honestidad/*` que registre apuestas/aciertos
- Frontend: pantalla nueva, modelo `RegistroApuesta`
- Persistencia: tabla `apuestas` en Oracle
