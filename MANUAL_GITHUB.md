# Puesta en marcha con GitHub — Bonoloto 2.0

Guía rápida (sin saber programar). Para la versión ilustrada, mira el PDF
**Bonoloto_2_Puesta_en_marcha_GitHub.pdf**.

## Cómo funciona
- **GitHub** = el "cerebro": cada noche ejecuta el motor y publica las combinaciones del día.
- **La app** = la "ventana": descarga ese archivo y te lo muestra.
- Esto **NO** aumenta la probabilidad de acertar. Es para observar. Juego responsable: 900 200 225.

## Pasos
1. **Cuenta de GitHub** — ya creada (Pingarra1971). ✓
2. **Repositorio** `bonoloto-2` — ya creado y público. ✓
3. **Subir el proyecto** (desde el PC, con GitHub Desktop):
   - Descomprime el ZIP del proyecto.
   - Instala GitHub Desktop (github.com/apps/desktop) e inicia sesión.
   - File → Clone repository → `bonoloto-2` → Clone.
   - Copia TODO el contenido del proyecto dentro de la carpeta clonada
     (deben verse `app`, `scripts`, `.github`, `requirements.txt`…).
   - Commit to principal → Push origin.
4. **API key como secreto**:
   - Settings → Secrets and variables → Actions → New repository secret.
   - Name: `LOTERIAS_API_KEY` (exacto). Secret: tu clave de loteriasapi.com. → Add secret.
   - La API key NUNCA va dentro de un archivo del repositorio.
5. **Probar la tarea**:
   - Pestaña Actions → "Combinaciones diarias Bonoloto" → Run workflow.
   - Al terminar en verde, aparece `docs/combinaciones.json`.

## Día a día
- Cada noche a las 23:00 (hora de España) GitHub genera automáticamente las
  combinaciones (y apuestas múltiples) del sorteo siguiente. Listas la noche anterior.
- La app las descarga al instante; tú eliges cuántas jugar / qué tamaño de apuesta múltiple.

## Si algo falla
- Actions → entra en la ejecución en rojo → el registro muestra el error → mándame captura.
- Si ves la tarea "ci" en rojo, ignórala (son pruebas internas).
- La primera ejecución suele necesitar uno o dos ajustes. Esos cambios se hacen en
  GitHub y NO obligan a recompilar la app.
