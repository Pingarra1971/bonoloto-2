# 📱 GUÍA FÁCIL — Montar Bonoloto 2.0 desde tu PC Windows

Esta guía está pensada para alguien que **nunca ha programado**. Cada paso es
pequeño y se explica qué haces y por qué. No tengas prisa. Si algo no sale,
haz una captura de pantalla y pregunta antes de seguir.

---

## 🗺️ Primero, entiende el mapa (2 minutos de lectura)

El proyecto tiene **dos partes** que trabajan juntas:

1. **La APP** → es la "ventana" que instalas en tu móvil Android. Te muestra
   la información y te deja configurar cosas. Pero ella sola no calcula nada.

2. **El SERVIDOR** → es el "cerebro" que hace todos los cálculos. No está en
   tu móvil ni en tu PC: vive en internet (en un sitio llamado Oracle Cloud).

La app del móvil se conecta al servidor por internet, le pide los cálculos, y
te muestra el resultado. **Necesitas las dos partes** para que funcione.

Vamos a montarlo en este orden (de lo más fácil a lo más difícil):

- **PARTE 1**: crear la app en tu PC → la instalas en el móvil.
- **PARTE 2**: montar el servidor en internet.
- **PARTE 3**: conectar la app con el servidor.

Empezamos por la PARTE 1, que es la más fácil y te dará una primera victoria.

---
---

# 🟢 PARTE 1 — Crear la app (en tu PC Windows)

Para convertir el proyecto en una app de Android necesitas dos programas
gratuitos: **Flutter** y **Android Studio**. Se instalan una sola vez.
Esta parte es lenta y aburrida (descargas grandes), pero solo se hace una vez.

---

## PASO 1 — Instalar Flutter

**¿Qué es Flutter?** Es la herramienta que transforma el proyecto en una app
de móvil. Sin ella, el proyecto es solo un montón de archivos.

**1.0.** (Requisito previo) Flutter necesita un programa llamado **Git**. Si no
lo tienes, instálalo primero: entra en `https://git-scm.com/download/win`,
descarga el instalador y ejecútalo pulsando "Next" en todo (acepta lo que
viene por defecto). Si no sabes si lo tienes, instálalo igual: no estorba.

**1.1.** Abre tu navegador y entra en esta dirección:

```
https://docs.flutter.dev/install
```

**1.2.** Elige la opción de instalar el **SDK de Flutter** (instalación
manual). La página directa es: `https://docs.flutter.dev/install/manual`
Selecciona **Windows** como sistema y descarga el SDK. Es un archivo `.zip`
grande (alrededor de 1 GB), así que tardará un poco en bajar. Déjalo
descargar entero.

**1.3.** Cuando termine, ve a tu carpeta de **Descargas** y busca el archivo
(se llamará algo como `flutter_windows_3.44.x-stable.zip`; el número exacto
da igual, cualquier versión 3.x sirve).

**1.4.** Ahora vamos a crear una carpeta donde vivirá Flutter. Abre el
**Explorador de archivos** (la carpeta amarilla de la barra de tareas) y:
   - Ve a `Este equipo` → `Disco local (C:)`.
   - Haz clic derecho en una zona vacía → **Nuevo** → **Carpeta**.
   - Llámala `src` (en minúsculas, sin espacios).
   - Ahora tienes la carpeta `C:\src`.

> ⚠️ **Importante**: NO pongas Flutter en "Archivos de programa" ni en el
> Escritorio. Tiene que ser `C:\src` para evitar problemas.

**1.5.** Vuelve a Descargas, haz **clic derecho** en el `.zip` de Flutter →
**"Extraer todo..."**. Cuando te pregunte dónde, escribe o navega a `C:\src`
y extrae. Tardará un par de minutos. Al acabar tendrás `C:\src\flutter`.

---

## PASO 2 — Decirle a Windows dónde está Flutter (el "PATH")

**¿Por qué?** Windows necesita saber dónde encontrar Flutter cuando lo
llamemos. Esto se hace añadiéndolo a una lista del sistema llamada "PATH".
Es el paso donde más gente se atasca, así que ve despacio.

**2.1.** Pulsa la tecla **Windows** (la del logo) y, sin abrir nada más,
escribe directamente:

```
variables de entorno
```

**2.2.** Te aparecerá una opción que dice **"Editar las variables de entorno
del sistema"**. Haz clic en ella.

**2.3.** Se abre una ventana pequeña. Abajo a la derecha hay un botón que
dice **"Variables de entorno..."**. Haz clic.

**2.4.** Se abre otra ventana dividida en dos mitades. Mira la mitad de
**ABAJO** ("Variables del sistema"). Busca en la lista una fila llamada
**"Path"** (puede que tengas que bajar un poco). Haz **clic encima de "Path"**
para seleccionarla y luego en el botón **"Editar..."**.

**2.5.** Se abre una ventana con una lista de rutas. Haz clic en **"Nuevo"**
(arriba a la derecha). Se crea una línea vacía. Escribe ahí exactamente:

```
C:\src\flutter\bin
```

**2.6.** Pulsa **"Aceptar"** en esa ventana. Y **"Aceptar"** otra vez. Y
**"Aceptar"** en la última. Tres veces aceptar para cerrar todo.

> 💡 Si te equivocas, no pasa nada: puedes volver a entrar y editarlo. Lo
> único importante es que la línea `C:\src\flutter\bin` quede en la lista.

---

## PASO 3 — Instalar Android Studio

**¿Qué es?** Es un programa de Google que Flutter necesita para crear apps de
Android. Aunque no lo vamos a usar directamente, tiene que estar instalado.

**3.1.** Entra en:

```
https://developer.android.com/studio
```

**3.2.** Pulsa el botón grande de descarga, acepta las condiciones, y baja el
instalador.

**3.3.** Ejecuta el instalador y ve pulsando **"Next"** (Siguiente) aceptando
todo lo que viene por defecto. No cambies nada.

**3.4.** Cuando termine de instalarse, **ábrelo una vez**. La primera vez
hará un asistente de configuración ("Setup Wizard"): pulsa Next aceptando todo
y deja que **descargue los componentes** que pida (esto tarda y baja varios
GB). Cuando llegue a la pantalla principal, ya puedes **cerrarlo**.

---

## PASO 4 — Comprobar que todo está bien

**¿Por qué?** Antes de seguir, vamos a verificar que Flutter y Android están
bien instalados. Flutter tiene un "médico" que lo revisa solo.

**4.1.** Pulsa **Windows + R** (las dos teclas a la vez). Se abre una ventanita.
Escribe `cmd` y pulsa Enter. Se abre una **ventana negra** (es la "consola";
no te asustes, solo vamos a escribir una orden).

**4.2.** Escribe esto exactamente y pulsa Enter:

```
flutter doctor
```

**4.3.** Pensará un momento y te mostrará una lista con marcas. Lo que quieres
ver es una marca verde **[√]** en **"Flutter"** y en **"Android toolchain"**.

**4.4.** Si en "Android toolchain" te dice algo de **licencias** sin aceptar,
escribe esto y pulsa Enter:

```
flutter doctor --android-licenses
```

   Te irá preguntando cosas; responde escribiendo `y` y Enter cada vez, hasta
   que termine.

> ⚠️ Si `flutter doctor` dice **"'flutter' no se reconoce como un comando"**,
> significa que el PASO 2 (el PATH) no quedó bien. Vuelve a hacerlo con calma,
> cierra la ventana negra, ábrela de nuevo y prueba otra vez.
>
> 📸 **Si te atascas aquí, hazme una captura de lo que muestra `flutter doctor`
> y te digo exactamente qué falta.**

---

## PASO 5 — Crear la app (¡el script lo hace casi todo!)

Ya tienes las herramientas. Ahora el proyecto.

**5.1.** Busca el archivo `bonoloto_2_completo.zip` que te di. Haz **clic
derecho** → **"Extraer todo..."** → extráelo en tu **Escritorio**. Tendrás una
carpeta llamada `bonoloto_2`.

**5.2.** Entra en `bonoloto_2` → entra en la carpeta `install`.

**5.3.** Busca el archivo **`compilar_app.bat`** y haz **doble clic** sobre él.

**5.4.** Se abre una ventana que te irá explicando lo que hace. Ve leyendo y
pulsando una tecla cuando te lo pida. La primera vez **tarda 10-20 minutos**
(está descargando cosas y construyendo la app). Es normal que parezca parado;
ten paciencia.

**5.5.** Cuando termine bien, te dirá que ha dejado el archivo **`bonoloto_2.apk`**
en tu **Escritorio**. ¡Esa es tu app! 🎉

> 📸 **Si el script da un error** (texto en rojo o que dice [ERROR]), hazme una
> captura de la ventana entera y te digo qué pasó. Lo más común es que falte
> algo del Paso 1 o 2.

---

## PASO 6 — Instalar la app en tu móvil Android

**6.1.** Pasa el archivo `bonoloto_2.apk` del PC a tu móvil. La forma más
fácil: súbelo a tu **Google Drive** desde el PC, y ábrelo desde el Drive en el
móvil. (También vale por cable USB, o enviártelo por correo.)

**6.2.** En el móvil, **toca el archivo** `bonoloto_2.apk` para abrirlo.

**6.3.** Android te dirá que no puede instalar apps de "origen desconocido"
(es una protección normal). Te ofrecerá un botón de **Ajustes**: tócalo y
**activa el permiso** para instalar desde tu explorador o navegador.

**6.4.** Vuelve atrás y pulsa **Instalar**. En unos segundos tendrás la app
instalada. 🎉

> La app ya está en tu móvil, pero **todavía no calculará nada**: le falta el
> servidor (PARTE 2). Si la abres ahora, verás la interfaz pero sin datos.

---

✅ **¡Has terminado la PARTE 1!** Tienes la app hecha e instalada. Esto era lo
más alcanzable. Tómate un respiro antes de la PARTE 2, que es la del servidor.

---
---

# 🟠 PARTE 2 — Montar el servidor (en internet)

> ⚠️ **Aviso honesto**: esta es la parte difícil de verdad. Son muchos clics en
> la web de Oracle, y es trabajo técnico. Es totalmente normal atascarse aquí.
> Ve MUY despacio y mándame capturas en cuanto algo no cuadre. No avances a
> ciegas: mejor preguntar diez veces que romper algo.

## PASO 7 — Crear una cuenta en Oracle Cloud

**¿Qué es Oracle Cloud?** Es una empresa que te "alquila" un ordenador en
internet (el servidor) y una base de datos. Tienen una capa **gratuita**
("Always Free") que nos sirve.

**7.1.** Entra en: `https://www.oracle.com/cloud/free/`

**7.2.** Pulsa **"Start for free"** y rellena el registro. Te pedirá correo,
datos personales y una **tarjeta** (para verificar que eres una persona; con
la capa gratuita no te cobran si usas los recursos gratis). Esto **tienes que
hacerlo tú**: ningún programa puede meter tus datos por ti.

> 📸 La web de registro de Oracle cambia a menudo y a veces pone pegas según el
> país. Si te bloqueas en el registro, mándame captura y vemos.

## PASO 8 — Crear el servidor y la base de datos

Una vez dentro de tu cuenta de Oracle, hay que crear dos cosas: el servidor
(una "máquina virtual") y la base de datos. Como el panel de Oracle es
complejo y cambia, **aquí es donde más te voy a guiar con tus capturas.**

**8.1.** Cuando estés dentro del panel de Oracle, hazme una **captura de la
pantalla principal** y te voy diciendo dónde hacer clic para:
   - Crear la máquina virtual (servidor) — elige una "Always Free", con Ubuntu.
   - Crear la base de datos (Autonomous Database) — también "Always Free".
   - Descargar el "wallet" (un archivo de seguridad de la base de datos).

No intento ponerlo todo aquí porque el panel cambia y te liaría más que
ayudarte. **Lo haremos juntos paso a paso con tus capturas.**

## PASO 9 — Instalar el cerebro en el servidor (script automático)

Cuando el servidor esté creado, te conectarás a él y ejecutarás **un solo
comando** que lo instala todo. Te guiaré para:
   - Conectarte al servidor desde Windows.
   - Subir el proyecto.
   - Ejecutar: `sudo bash install_servidor.sh`

Este script hace todo el trabajo pesado solo. Pero llegar hasta él (los pasos
8) es lo complicado, y lo haremos con calma.

Durante la instalación, el script te pedirá una **API key de loterías**. Para
tenerla lista, mira el PASO siguiente.

## PASO 9-bis — Conseguir la clave de resultados (API key)

**¿Qué es?** Para que la app se entere automáticamente de qué números salen en
cada sorteo, usa un servicio llamado **loteriasapi.com**. Necesita una clave
personal (como una contraseña) que identifica tus peticiones.

**9b.1.** Entra en: `https://loteriasapi.com`

**9b.2.** Regístrate (te pedirá un correo). Según su plan, la clave puede ser
gratuita o de pago; elige lo que te encaje.

**9b.3.** En tu zona de usuario, busca tu **API key** (una cadena larga de
letras y números). Cópiala y guárdala.

**9b.4.** Cuando el instalador del servidor (Paso 9) te pregunte por
`LOTERIAS_API_KEY`, **pega esa clave**. Ya está conectada.

> 💡 La clave va SOLO en el servidor, nunca en la app del móvil. La app le
> pide los datos al servidor, y el servidor es quien habla con loteriasapi.com.
>
> 💡 ¿No quieres usar la API? Puedes saltártela: la app funcionará igual, pero
> tendrás que meter tú los resultados de cada sorteo a mano. Para empezar,
> puedes dejar la clave vacía y añadirla más adelante.

---
---

# 🔵 PARTE 3 — Conectar la app con el servidor

Cuando el servidor funcione, tendrá una **dirección** (una IP, algo como
`http://123.45.67.89:8000`).

**PASO 10.1.** Abre la app **Bonoloto 2.0** en tu móvil.

**10.2.** Ve a la pestaña de **Ajustes**.

**10.3.** Busca el campo de la **dirección del servidor** y escribe ahí la IP
de tu servidor.

**10.4.** Guarda, vuelve a Inicio, y prueba a generar combinaciones. Si todo
está bien, la app se conecta al servidor y empieza a funcionar. ✅

---

# 🆘 Cómo pedirme ayuda cuando te atasques

1. Haz una **captura de pantalla** de lo que ves (el error, la web, la consola).
   - En Windows: tecla **Impr Pant** o **Windows + Mayús + S** para recortar.
   - En el móvil: los botones de bajar volumen + encendido a la vez.
2. Dime **en qué PASO de esta guía estás** (ej. "estoy en el Paso 4").
3. Mándame la captura y lo que esperabas que pasara.

Con eso te oriento exactamente. No te frustres si algo falla: es parte normal
del proceso, sobre todo en la PARTE 2.

---

# 💬 Recordatorio honesto

Vas a usar esta app para **observar**: ver qué combinaciones genera y
compararlas con los sorteos reales. Eso está muy bien como herramienta de
observación. Pero recuerda lo que verás con el tiempo: los aciertos rondarán
lo que da el puro azar. La app no predice ni mejora tus probabilidades —
ningún sistema puede. Disfrútala como lo que es: una herramienta para mirar y
aprender, no para ganar.
