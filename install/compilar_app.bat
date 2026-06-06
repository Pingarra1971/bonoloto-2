@echo off
:: ═══════════════════════════════════════════════════════════════════════
:: BONOLOTO 2.0 - COMPILADOR DE APP ANDROID (Windows 11)
:: ═══════════════════════════════════════════════════════════════════════
:: Genera el archivo .apk que se instala en un movil Android (10 o superior).
:: Doble clic sobre este archivo para ejecutarlo.
:: ═══════════════════════════════════════════════════════════════════════
setlocal enabledelayedexpansion
title Bonoloto 2.0 - Compilador de App Android
color 0B
cls
echo.
echo  ============================================================================
echo                 BONOLOTO 2.0 - COMPILADOR DE APP ANDROID
echo  ============================================================================
echo.
echo  Este script genera el archivo .apk para instalar en tu movil Android.
echo  La primera vez tarda 10-20 minutos.
echo.
echo  REQUISITO PREVIO (una sola vez): tener Flutter instalado.
echo  Si no lo tienes, este script te dira como hacerlo.
echo.
pause

:: ─── [1/5] Verificar Flutter ───
echo.
echo [1/5] Verificando Flutter...
where flutter >nul 2>&1
if errorlevel 1 (
    color 0E
    echo.
    echo  [FALTA FLUTTER] Hay que instalarlo una vez. Sigue estos pasos:
    echo.
    echo   1. Abre esta web:  https://docs.flutter.dev/install
    echo   2. Descarga el SDK de Flutter ^(un archivo .zip grande^).
    echo   3. Descomprimelo en  C:\src\flutter
    echo   4. Tambien instala Android Studio desde:
    echo        https://developer.android.com/studio
    echo      ^(necesario para compilar apps Android^)
    echo   5. Anade  C:\src\flutter\bin  al PATH de Windows:
    echo        - Tecla Windows, escribe "variables de entorno", Enter
    echo        - Boton "Variables de entorno"
    echo        - En "Path" -^> Editar -^> Nuevo -^> escribe  C:\src\flutter\bin
    echo        - Aceptar todo
    echo   6. CIERRA esta ventana y vuelve a ejecutar este script.
    echo.
    pause
    exit /b 1
)
echo [OK] Flutter esta instalado.

:: ─── [2/5] Localizar el proyecto ───
echo.
echo [2/5] Localizando el proyecto...
set "PROYECTO="
:: El .bat esta dentro de bonoloto_2\install, asi que el proyecto es la carpeta de arriba
set "PROYECTO=%~dp0.."
if not exist "%PROYECTO%\pubspec.yaml" (
    echo [ERROR] No encuentro pubspec.yaml. Asegurate de que este .bat
    echo         esta dentro de la carpeta  bonoloto_2\install
    pause
    exit /b 1
)
echo [OK] Proyecto encontrado.

:: ─── [3/5] Preparar dependencias ───
echo.
echo [3/5] Preparando el proyecto Android...
cd /d "%PROYECTO%"
:: Si falta la estructura Android de Gradle, Flutter la regenera.
:: (El proyecto trae el AndroidManifest pero no toda la estructura Gradle.)
if not exist "%PROYECTO%\android\app" (
    echo      Regenerando estructura Android ^(primera vez^)...
    call flutter create --platforms=android --org com.bonoloto --project-name bonoloto_2 .
)

:: ─── Forzar compileSdk 36 en TODOS los modulos (app + plugins) ───
:: Algunos plugins (connectivity_plus, etc.) requieren compilar contra
:: Android API 34 o superior. Un script aparte inyecta la configuracion
:: en el build.gradle(.kts) raiz. Detecta solo el formato (Kotlin o
:: Groovy) y es idempotente (no duplica si ya esta puesto).
echo      Ajustando compileSdk a 36 para compatibilidad con plugins...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0fijar_compilesdk.ps1" "%PROYECTO%\android"

echo      Descargando dependencias (flutter pub get)...
call flutter pub get
if errorlevel 1 (
    echo [ERROR] Fallo al descargar dependencias. Revisa tu conexion.
    pause
    exit /b 1
)
echo [OK] Dependencias listas.


:: ─── [4/5] Revisar errores antes de compilar ───
echo.
echo [4/5] Revisando el codigo (dart analyze)...
call dart analyze
echo.
echo  ^(Si arriba aparecen lineas que empiezan por "error", hay que
echo   corregirlas antes de compilar. Las "info" y "warning" no bloquean.^)
echo.
pause

:: ─── [5/5] Compilar el APK ───
echo.
echo [5/5] Compilando el APK para Android (esto tarda varios minutos)...
echo.
:: --release = version optimizada. Compatible con Android 10 (API 29) y superior.
call flutter build apk --release
if errorlevel 1 (
    echo.
    echo [ERROR] La compilacion fallo. Mira los mensajes de arriba.
    echo Lo mas comun: algun "error" de dart analyze sin corregir,
    echo o Android Studio / SDK sin instalar del todo.
    pause
    exit /b 1
)

:: ─── Copiar el APK a un sitio facil de encontrar ───
set "APK_ORIGEN=%PROYECTO%\build\app\outputs\flutter-apk\app-release.apk"
set "APK_DESTINO=%USERPROFILE%\Desktop\bonoloto_2.apk"
if exist "%APK_ORIGEN%" (
    copy /Y "%APK_ORIGEN%" "%APK_DESTINO%" >nul
    color 0A
    echo.
    echo  ============================================================================
    echo                          COMPILACION COMPLETADA
    echo  ============================================================================
    echo.
    echo  Tu app esta lista:  %APK_DESTINO%
    echo  ^(la he copiado a tu Escritorio como  bonoloto_2.apk^)
    echo.
    echo  COMO INSTALARLA EN TU MOVIL ANDROID 10:
    echo   1. Pasa el archivo bonoloto_2.apk a tu movil
    echo      ^(por cable USB, Bluetooth, o subiendolo a tu Drive/correo^).
    echo   2. En el movil, abre el archivo .apk.
    echo   3. Android pedira permiso para "instalar apps desconocidas":
    echo      acepta / activa el permiso para tu explorador de archivos.
    echo   4. Pulsa Instalar.
    echo.
    echo  IMPORTANTE: la app necesita el SERVIDOR funcionando para hacer algo.
    echo  Cuando abras la app, ve a Ajustes e introduce la URL de tu servidor.
    echo.
) else (
    echo [ERROR] No encuentro el APK generado. Revisa los mensajes de arriba.
)
pause
