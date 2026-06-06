@echo off
:: ═══════════════════════════════════════════════════════════════════════
:: EMPEZAR.bat — Punto de entrada para Bonoloto 2.0 en Windows
:: Doble clic sobre este archivo para ver por donde empezar.
:: ═══════════════════════════════════════════════════════════════════════
title Bonoloto 2.0 - Por donde empezar
color 0B
cls
echo.
echo  ============================================================================
echo                          BONOLOTO 2.0 - INICIO
echo  ============================================================================
echo.
echo   Este proyecto tiene DOS partes:
echo.
echo     1. LA APP (en tu PC, luego al movil)  ^<-- empieza por aqui
echo     2. EL SERVIDOR (en internet, Oracle Cloud)
echo.
echo  ----------------------------------------------------------------------------
echo   ANTES DE COMPILAR LA APP necesitas instalar (una sola vez):
echo     - Flutter:        https://docs.flutter.dev/install
echo     - Android Studio: https://developer.android.com/studio
echo.
echo   Todo esto esta explicado PASO A PASO en el archivo:
echo.
echo        GUIA_WINDOWS_PASO_A_PASO.md
echo.
echo   Abrelo y sigue los pasos en orden. Te recomiendo leerlo antes de seguir.
echo  ----------------------------------------------------------------------------
echo.
echo   Cuando YA tengas Flutter y Android Studio instalados (Pasos 1-4 de la
echo   guia), para generar la app ejecuta:
echo.
echo        install\compilar_app.bat
echo.
echo  ============================================================================
echo.
set /p abrir="Quieres abrir la guia paso a paso ahora? (s/n) [s]: "
if /i "%abrir%"=="n" (
    echo.
    echo De acuerdo. Cuando quieras, abre GUIA_WINDOWS_PASO_A_PASO.md
    echo y sigue los pasos. Mucho animo.
    pause
    exit /b 0
)
:: Abrir la guia con el programa por defecto
start "" "%~dp0GUIA_WINDOWS_PASO_A_PASO.md"
echo.
echo Guia abierta. Sigue los pasos en orden, empezando por el Paso 1.
echo.
pause
