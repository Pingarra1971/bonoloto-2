# Manual completo de puesta en marcha — Bonoloto 2.0

Este manual tiene **dos partes**:

- **PARTE A** — Para ti (el dueño del proyecto). Explica en lenguaje normal
  qué es esto, qué hace falta, qué cuesta y qué decisiones tienes que tomar.
- **PARTE B** — Para la persona técnica que lo instale. Pasos detallados.

Léete la Parte A entera. La Parte B pásala a quien monte el sistema.

---
---

# PARTE A — Para el dueño del proyecto (lenguaje normal)

## Lo primero, con honestidad

Esta aplicación está bien construida y funciona. Pero **necesita una persona
con conocimientos de programación para ponerla en marcha.** No es como bajar
una app del móvil: hay que alquilar un servidor, instalar una base de datos y
compilar la aplicación con herramientas de desarrollo. Esto no se puede hacer
con conocimientos cero, por bueno que sea este manual. Es como tener los
planos de una casa: necesitas un constructor para levantarla.

**Lo que de verdad necesitas conseguir primero: una persona técnica**
(un programador, freelance, o un conocido que sepa). Con este proyecto y la
Parte B de este manual, sabrá exactamente qué hacer.

## Qué es esta app y qué hace (y qué NO hace)

Es una app que genera combinaciones de Bonoloto usando muchos algoritmos
estadísticos, con un panel que te muestra honestamente la realidad de la
lotería.

**Lo que NO hace, y es importante que lo tengas claro:** no aumenta tus
probabilidades de acertar. Ninguna app puede. Cada combinación —la que dé la
app o la que pongas tú— tiene la misma probabilidad: 1 entre 13.983.816.

**Lo que SÍ hace de forma honesta:**
- Genera combinaciones con criterios estadísticos.
- Te garantiza, si juegas varios boletos con su sistema de cobertura, cómo se
  reparten los aciertos *si los hay*.
- Si llegaras a ganar, te ayuda a cobrar algo más eligiendo combinaciones que
  poca gente juega (menos gente con quien repartir).
- Te muestra la verdad matemática: cuánto se gasta de media, cuánto se
  recupera, etc.

## Qué cosas hay que contratar (y cuánto cuesta, aproximado)

| Qué | Para qué | Coste aproximado |
|---|---|---|
| **Servidor Oracle Cloud** | Donde "vive" el cerebro de la app | Hay capa gratuita ("Always Free"); si no, desde ~unos pocos €/mes |
| **Base de datos Oracle** | Guardar sorteos y resultados | Incluida en Oracle Cloud (capa gratuita disponible) |
| **Cuenta de desarrollador móvil** | Solo si quieres publicar la app en tiendas | Google Play: 25€ una vez. Apple: 99€/año |
| **API de resultados de lotería** | Que la app se entere de los sorteos | Variable; ver más abajo |
| **Persona técnica** | Montarlo todo | Lo que acuerdes con quien lo haga |

Para uso personal (solo tu móvil, sin publicar en tiendas), te puedes ahorrar
las cuentas de desarrollador: la app se puede instalar directamente.

## Servicios externos que hay que conectar

La app usa dos servicios de fuera. Tu persona técnica los configurará, pero
para que sepas qué son:

1. **API de resultados de Bonoloto** — para que la app sepa qué números
   salieron en cada sorteo. Usa **loteriasapi.com** (verificada y activa).
   Hay que **registrarse en https://loteriasapi.com para obtener una clave**
   (API key) gratuita o de pago según su plan. Sin esto, la app funciona
   igual, pero tendrías que meter los resultados de cada sorteo a mano.

2. **Telegram (opcional)** — si quieres que la app te mande las combinaciones
   por Telegram. Requiere crear un "bot" gratis. Es opcional; la app funciona
   sin esto.

## Tu decisión más importante

Antes de gastar nada, decide esto con la cabeza fría: **¿cuánto estás
dispuesto a invertir (en montar esto y en apostar) sabiendo que la app no
mejora tus probabilidades de ganar?**

Si la respuesta honesta es que esperas recuperar la inversión ganando a la
lotería, por favor relee la primera sección. La lotería devuelve de media
menos de la mitad de lo que se apuesta. Monta y juega esto solo si te lo
puedes permitir como entretenimiento, no como inversión.

---
---

# PARTE B — Para la persona técnica que instale el sistema

## Resumen de arquitectura

- **Backend**: Python 3.11 + FastAPI. Cola de trabajos asíncrona, SSE para
  progreso en vivo. Sirve una API REST.
- **Base de datos**: por defecto un archivo local **SQLite** (sin configuración
  ni wallet). 4 tablas que se crean solas al arrancar (`sorteos`, `calculos`,
  `apuestas`, `predicciones`). Opcionalmente puede usarse Oracle ATP.
- **Frontend**: Flutter (Dart ≥3.0). App móvil (Android/iOS). Estado con
  Riverpod, HTTP con dio, progreso con SSE.
- **Watchdog**: proceso aparte (systemd) que tras cada sorteo actualiza la
  memoria y reentrena.

## Requisitos previos

- Servidor Linux (probado para Oracle Cloud ARM aarch64, Ubuntu 24).
- Python 3.11+
- Flutter SDK 3.19+ (para compilar la app)
- Base de datos: **nada que instalar** — usa un archivo SQLite local por defecto.
  (Oracle ATP con wallet es opcional, solo si prefieres usarlo.)

## PASO 1 — Backend

```bash
# En el servidor
git clone <o copia el proyecto>
cd bonoloto_2
pip install -r requirements.txt
```

### Variables de entorno

Crea `/etc/bonoloto-2.env` con (las que de verdad usa el código):

```
# Seguridad — OBLIGATORIO. Sin esto, los tokens son efímeros.
JWT_SECRET=<una cadena larga y aleatoria, guárdala bien>

# Base de datos — por defecto un archivo local (sin configurar nada).
DB_BACKEND=sqlite
SQLITE_PATH=/home/bonoloto/bonoloto_2/datos/bonoloto.db

# (OPCIONAL) Oracle ATP — solo si pones DB_BACKEND=oracle:
# ORACLE_USER=<usuario>
# ORACLE_PASSWORD=<contraseña>
# ORACLE_DSN=<DSN del tnsnames, ej. bonoloto_high>
# ORACLE_WALLET_LOCATION=/ruta/al/wallet
# ORACLE_WALLET_PASSWORD=<password del wallet>

# API de resultados (clave de loteriasapi.com — registrarse en su web)
LOTERIAS_API_KEY=<tu clave, si la API la requiere>

# Opcionales (tienen defaults razonables)
PORT=8000
HOST=0.0.0.0
LOG_LEVEL=INFO
DB_POOL_MIN=2
DB_POOL_MAX=10
TIMEOUT_CALCULO_SEGUNDOS=3600
```

### Arrancar

```bash
set -a; source /etc/bonoloto-2.env; set +a
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Al arrancar, crea las 4 tablas automáticamente (ignora ORA-00955 si ya
existen). Verifica en el log que no hay otros errores ORA-.

Para producción, móntalo como servicio systemd (ver `install/` si existe, o
crea una unit estándar de uvicorn).

## PASO 2 — Verificación del backend

Sigue **`docs/VERIFICACION_DESPLIEGUE.md`** (incluido en el proyecto). Es una
guía con comandos curl que ejercitan cada operación SQL contra Oracle real.
Esto es importante: el SQL no se ha probado contra una instancia real, solo
escrito según la documentación de Oracle.

## PASO 3 — Cargar el histórico de sorteos (la "memoria")

La app tiene memoria de sorteos. Para sembrarla con el histórico completo:

```bash
# Obtén un token
TOKEN=$(curl -s -X POST localhost:8000/api/auth/token \
  -H "Content-Type: application/json" \
  -d "{\"secret\":\"$JWT_SECRET\"}" | jq -r .token)

# Carga masiva (array de sorteos). Idempotente: se puede repetir sin duplicar.
curl -X POST localhost:8000/api/memoria/backfill \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '[{"fecha":"2024-01-01","numeros":[3,11,19,27,35,43],"complementario":7,"reintegro":2,"bote":0}, ...]'
```

El histórico de Bonoloto es público (desde 1988). Habrá que conseguirlo de
una fuente (la API, o un CSV histórico) y formatearlo como el array de arriba.

## PASO 4 — Frontend Flutter

```bash
cd <raíz del proyecto>
flutter pub get
dart analyze        # IMPORTANTE: corregir cualquier 'error' antes de seguir
dart fix --apply    # limpia imports sin usar (cosmético)
```

> **Nota honesta**: el frontend no se ha podido compilar en desarrollo (sin
> SDK). `dart analyze` es muy probable que muestre algún error residual de la
> migración a Riverpod (típicamente llamadas con argumento posicional vs
> nombrado). Son rápidos de corregir; el mensaje indica archivo y línea.

Configura la URL del backend en el cliente (busca dónde se define la base
URL en `lib/services/api_client.dart`) apuntando a tu servidor.

Compilar:

```bash
flutter build apk --release      # Android
flutter build ios --release      # iOS (requiere Mac + Xcode)
```

Para uso personal, instala el APK directamente en tu móvil (activando
"orígenes desconocidos"). Para tiendas, necesitas las cuentas de desarrollador.

## PASO 5 — Watchdog (actualización automática)

Proceso aparte que corre a las 21:45h (hora española) tras cada sorteo:
obtiene el resultado, lo añade a la memoria y reentrena.

- Revisa el nombre del servicio systemd que espera: por defecto `bonoloto-ai`.
  ```bash
  grep -n "bonoloto-ai" app/infrastructure/scheduler/watchdog.py
  ```
  Si despliegas el servicio con otro nombre, ajústalo ahí.
- Necesita las mismas variables de entorno (sobre todo `JWT_SECRET` y
  `BACKEND_URL`).

## Servicios externos — enlaces

- **Oracle Cloud (servidor + base de datos)**: https://www.oracle.com/cloud/
  (busca "Always Free" para la capa gratuita).
- **API de resultados**: `https://api.loteriasapi.com/api/v1` (verificada).
  Formato: cabecera `X-API-Key`, endpoint `/results/bonoloto/latest`,
  respuesta con campos `combination` y `drawDate`. **Regístrate en
  https://loteriasapi.com para obtener tu API key** y ponla en
  `LOTERIAS_API_KEY`. Alternativa sin API: cargar resultados a mano vía el
  endpoint `/api/memoria/sorteo`.
- **Telegram (opcional)**: crea un bot con @BotFather en Telegram, obtén el
  token, y configúralo en los ajustes de la app. API: `https://api.telegram.org`.
- **Flutter SDK**: https://docs.flutter.dev/install

## Estado del código (para que el técnico sepa qué se ha verificado)

- ✅ Backend: 96 tests automáticos pasan. Todos los módulos importan y
  compilan. Algoritmos verificados (no producen valores inválidos).
- ✅ Matemática de honestidad verificada (probabilidades exactas).
- ⚠️ SQL Oracle: escrito según documentación, **no probado contra instancia
  real**. Seguir `docs/VERIFICACION_DESPLIEGUE.md`.
- ⚠️ Frontend Flutter: **no compilado en desarrollo**. Correr `dart analyze`
  y corregir errores antes de compilar.
- ⚠️ API de loterías: verificar disponibilidad actual.

## Documentación incluida en el proyecto

- `docs/ARQUITECTURA.md` — diseño técnico.
- `docs/VERIFICACION_DESPLIEGUE.md` — verificación paso a paso en despliegue.
- `docs/REVISION_BUGS.md` — historial de revisiones.
- `docs/SESION_*.md` — notas de cada fase de desarrollo.
