# ============================================================
#  fijar_compilesdk.ps1
#  Fuerza compileSdk 36 en TODOS los modulos de Android
#  (la app y todos los plugins: connectivity_plus, etc.)
#
#  Algunos plugins de Flutter se compilan contra android-33,
#  pero las librerias androidx modernas exigen compilar contra
#  la API 34 o superior. Este script anade un bloque al
#  build.gradle(.kts) raiz del proyecto que aplica compileSdk
#  36 a todos los subproyectos durante la compilacion.
#
#  Funciona con los DOS formatos de Flutter:
#    - build.gradle.kts  (Kotlin DSL, Flutter 3.29+)  <-- el tuyo
#    - build.gradle      (Groovy, formato antiguo)
#
#  IMPORTANTE: Flutter ya mete en ese archivo una linea
#  (evaluationDependsOn ":app") que evalua los modulos pronto.
#  Por eso el bloque comprueba si cada modulo YA esta evaluado
#  (state.executed) y solo se engancha a los que aun no lo estan.
#  Asi se evita el error "Cannot run afterEvaluate when the
#  project is already evaluated".
#
#  Es IDEMPOTENTE: si el bloque ya esta puesto, no lo duplica.
#  Lo llama automaticamente compilar_app.bat. No hay que
#  ejecutarlo a mano.
# ============================================================

param(
    [Parameter(Mandatory = $true)]
    [string]$RutaAndroid
)

$ErrorActionPreference = "Stop"

# Comprobar que la carpeta android existe
if (-not (Test-Path $RutaAndroid)) {
    Write-Host "      [AVISO] No se encontro la carpeta $RutaAndroid"
    Write-Host "              (se omite el ajuste de compileSdk)"
    exit 0
}

# Determinar que archivo de build RAIZ existe.
# Flutter moderno (3.29+) usa Kotlin DSL: build.gradle.kts
# Flutter antiguo usa Groovy: build.gradle
$rutaKts    = Join-Path $RutaAndroid "build.gradle.kts"
$rutaGroovy = Join-Path $RutaAndroid "build.gradle"

if (Test-Path $rutaKts) {
    $archivo  = $rutaKts
    $esKotlin = $true
}
elseif (Test-Path $rutaGroovy) {
    $archivo  = $rutaGroovy
    $esKotlin = $false
}
else {
    Write-Host "      [AVISO] No se encontro build.gradle ni build.gradle.kts"
    Write-Host "              en $RutaAndroid (se omite el ajuste)."
    exit 0
}

# Leer el contenido actual
$contenido = Get-Content -Path $archivo -Raw

# Si ya tiene el marcador, no hacer nada (idempotente)
if ($contenido -match "BONOLOTO_COMPILESDK") {
    Write-Host "      [OK] compileSdk 36 ya estaba configurado."
    exit 0
}

# Elegir el bloque segun el formato del archivo.
if ($esKotlin) {
    # --- Kotlin DSL (build.gradle.kts) ---
    # Se usa reflexion (javaClass.getMethod) para llamar a
    # compileSdkVersion(int) sin necesitar los tipos de AGP en el
    # classpath del build raiz, que en proyectos Flutter no estan.
    # El guard !state.executed evita el error de afterEvaluate.
    $bloque = @'

// ============================================================
// BONOLOTO_COMPILESDK
// Fuerza compileSdk 36 en todos los modulos (app + plugins).
// Necesario porque algunos plugins (connectivity_plus, etc.)
// se compilan contra android-33, pero las librerias androidx
// modernas exigen compilar contra la API 34 o superior.
// ============================================================
subprojects {
    if (!state.executed) {
        afterEvaluate {
            val extensionAndroid = extensions.findByName("android")
            if (extensionAndroid != null) {
                try {
                    val metodo = extensionAndroid.javaClass.getMethod(
                        "compileSdkVersion", Int::class.javaPrimitiveType
                    )
                    metodo.invoke(extensionAndroid, 36)
                } catch (e: Exception) {
                    // Este modulo no expone compileSdkVersion(int): se ignora.
                }
            }
        }
    }
}
'@
}
else {
    # --- Groovy (build.gradle) ---
    $bloque = @'

// ============================================================
// BONOLOTO_COMPILESDK
// Fuerza compileSdk 36 en todos los modulos (app + plugins).
// Necesario porque algunos plugins (connectivity_plus, etc.)
// se compilan contra android-33, pero las librerias androidx
// modernas exigen compilar contra la API 34 o superior.
// ============================================================
subprojects {
    if (!project.state.executed) {
        afterEvaluate { proyecto ->
            if (proyecto.hasProperty('android')) {
                proyecto.android {
                    compileSdkVersion 36
                }
            }
        }
    }
}
'@
}

# Anadir el bloque al final del archivo
Add-Content -Path $archivo -Value $bloque

$nombre = [System.IO.Path]::GetFileName($archivo)
Write-Host "      [OK] compileSdk 36 anadido en $nombre."
exit 0
