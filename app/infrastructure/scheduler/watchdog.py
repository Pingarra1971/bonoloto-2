"""
╔══════════════════════════════════════════════════════════════╗
║   BONOLOTO AI — WATCHDOG + SCHEDULER ORACLE CLOUD           ║
║   Anti-cuelgues + Reentrenamiento automático diario         ║
╚══════════════════════════════════════════════════════════════╝
"""

import asyncio
import logging
import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone

import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("/var/log/bonoloto_watchdog.log"),
    ],
)
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
# CONFIGURACIÓN
# ═══════════════════════════════════════════════════════════════
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
LOTERIAS_API_KEY = os.getenv("LOTERIAS_API_KEY", "")
LOTERIAS_API_URL = "https://api.loteriasapi.com/api/v1"
MAX_REINTENTOS = 5
INTERVALO_HEALTHCHECK = 60  # segundos
PROCESO_BACKEND = None


# ═══════════════════════════════════════════════════════════════
# WATCHDOG — MONITOREO Y REINICIO AUTOMÁTICO
# ═══════════════════════════════════════════════════════════════
async def verificar_salud_backend() -> bool:
    """Comprueba si el backend está respondiendo correctamente"""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{BACKEND_URL}/api/health")
            return resp.status_code == 200
    except Exception as e:
        logger.warning(f"Backend no responde: {e}")
        return False


def iniciar_backend():
    """[DEPRECADO en v7.0] El backend ahora lo gestiona systemd.
    Esta función se conserva por compatibilidad pero no debe usarse."""
    logger.warning("iniciar_backend() está deprecado en v7.0. "
                   "El backend debe gestionarse vía 'sudo systemctl start bonoloto-2'")
    return None


def reiniciar_backend():
    """Reinicia el backend vía systemctl (gestionado por systemd)."""
    logger.info("🔄 Solicitando reinicio del backend vía systemctl...")
    try:
        resultado = subprocess.run(
            ["sudo", "-n", "systemctl", "restart", "bonoloto-2"],
            capture_output=True, text=True, timeout=60
        )
        if resultado.returncode == 0:
            logger.info("✅ Backend reiniciado correctamente")
            return True
        else:
            logger.error(f"Error reiniciando backend: {resultado.stderr}")
            return False
    except subprocess.TimeoutExpired:
        logger.error("Timeout al reiniciar backend")
        return False
    except Exception as e:
        logger.error(f"Error reiniciando backend: {e}")
        return False


async def bucle_watchdog():
    """Bucle principal del watchdog — comprueba salud cada minuto.
    El proceso del backend lo gestiona systemd; aquí solo verificamos
    el endpoint /api/health y solicitamos reinicio si no responde."""
    reintentos_fallidos = 0

    while True:
        await asyncio.sleep(INTERVALO_HEALTHCHECK)

        saludable = await verificar_salud_backend()
        if not saludable:
            reintentos_fallidos += 1
            logger.warning(
                f"⚠️ Backend no saludable — intento {reintentos_fallidos}/{MAX_REINTENTOS}"
            )
            if reintentos_fallidos >= MAX_REINTENTOS:
                logger.error("❌ Máximo de reintentos alcanzado — solicitando reinicio...")
                if reiniciar_backend():
                    reintentos_fallidos = 0
                    await asyncio.sleep(30)   # esperar arranque
        else:
            if reintentos_fallidos > 0:
                logger.info("✅ Backend recuperado")
            reintentos_fallidos = 0


# ═══════════════════════════════════════════════════════════════
# SCHEDULER — ACTUALIZACIÓN TRAS CADA SORTEO
# ═══════════════════════════════════════════════════════════════
async def actualizar_datos_sorteo():
    """
    Se ejecuta automáticamente a las 21:45h (hora española) todos los días.
    Obtiene el último resultado de la API y ordena reentrenamiento.
    """
    logger.info("📡 Iniciando actualización de datos del sorteo...")

    headers = {
        "X-API-Key": LOTERIAS_API_KEY,
        "Content-Type": "application/json",
    }

    try:
        # 1. Obtener último resultado de loteriasapi.com (formato /api/v1)
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{LOTERIAS_API_URL}/results/bonoloto/latest",
                headers=headers,
            )

            if resp.status_code != 200:
                logger.error(f"Error obteniendo sorteo: {resp.status_code}")
                return

            cuerpo = resp.json()
            # La API envuelve el resultado en {"data": {...}}
            data = cuerpo.get("data", cuerpo) if isinstance(cuerpo, dict) else {}
            logger.info(f"✅ Sorteo obtenido: {data}")

            # 2. Generar JWT on-demand desde JWT_SECRET (evita token estático que expire)
            jwt_secret = os.getenv("JWT_SECRET", "")
            jwt_token = ""
            if jwt_secret:
                try:
                    import jwt as _jwt
                    from datetime import timedelta
                    now = datetime.now(timezone.utc)
                    jwt_token = _jwt.encode(
                        {"sub": "bonoloto-watchdog", "iat": now,
                         "exp": now + timedelta(hours=1)},  # válido 1 hora
                        jwt_secret, algorithm="HS256",
                    )
                except Exception as e:
                    logger.warning(f"No se pudo generar JWT: {e}")
                    jwt_token = os.getenv("JWT_TOKEN", "")
            else:
                jwt_token = os.getenv("JWT_TOKEN", "")
            auth_headers = {
                "Authorization": f"Bearer {jwt_token}",
                "Content-Type": "application/json",
            }

            # Campos del formato actual de la API (con compatibilidad antigua)
            result_data = data.get("resultData", {}) if isinstance(data.get("resultData"), dict) else {}
            sorteo_payload = {
                "fecha": data.get("drawDate", data.get("fecha", datetime.now(timezone.utc).isoformat())),
                "numeros": data.get("combination", data.get("numeros", data.get("combinacion", []))),
                "complementario": data.get("complementario", result_data.get("complementario", 0)),
                "reintegro": data.get("reintegro", result_data.get("reintegro", 0)),
                "bote": data.get("jackpot", data.get("bote", 0)),
            }

            # 2.5 Registrar el sorteo en la MEMORIA (idempotente) para que el
            # histórico crezca con cada sorteo. Esto alimenta a los algoritmos
            # con más base estadística en futuros cálculos.
            try:
                mem_resp = await client.post(
                    f"{BACKEND_URL}/api/memoria/sorteo",
                    headers=auth_headers,
                    json=sorteo_payload,
                )
                if mem_resp.status_code == 200:
                    logger.info("✅ Sorteo añadido a la memoria")
                else:
                    logger.warning(
                        "No se pudo añadir a memoria: %s", mem_resp.status_code
                    )
            except Exception as e:
                logger.warning("Error añadiendo a memoria: %s", e)

            reentrenar_resp = await client.post(
                f"{BACKEND_URL}/api/modelos/reentrenar",
                headers=auth_headers,
                json=sorteo_payload,
            )

            if reentrenar_resp.status_code == 200:
                logger.info("✅ Reentrenamiento iniciado correctamente")
            else:
                logger.error(f"Error iniciando reentrenamiento: {reentrenar_resp.status_code}")

    except Exception as e:
        logger.error(f"❌ Error en actualización de sorteo: {e}")


async def backup_base_datos():
    """Backup semanal automático de la base de datos Oracle"""
    logger.info("💾 Iniciando backup semanal de la base de datos...")
    try:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_dir = "/home/bonoloto/backups"
        backup_file = f"{backup_dir}/bonoloto_backup_{timestamp}.sql"
        os.makedirs(backup_dir, exist_ok=True)

        # Exportar datos críticos
        resultado = subprocess.run(
            ["expdp",
             f"userid={os.getenv('ORACLE_USER')}/{os.getenv('ORACLE_PASSWORD')}@{os.getenv('ORACLE_DSN')}",
             f"dumpfile=bonoloto_{timestamp}.dmp",
             "tables=SORTEOS,PREDICCIONES,MODELOS_RENDIMIENTO",
             "logfile=backup.log"],
            capture_output=True,
            text=True,
            timeout=300,
        )
        if resultado.returncode == 0:
            logger.info(f"✅ Backup completado: {backup_file}")
        else:
            logger.warning(f"Backup con advertencias: {resultado.stderr}")
    except Exception as e:
        logger.error(f"❌ Error en backup: {e}")


# ═══════════════════════════════════════════════════════════════
# PUNTO DE ENTRADA PRINCIPAL
# ═══════════════════════════════════════════════════════════════
async def main():
    logger.info("═" * 60)
    logger.info("  BONOLOTO AI — WATCHDOG + SCHEDULER INICIADO")
    logger.info("  Oracle Cloud ARM Ampere 24GB — Always Free")
    logger.info("═" * 60)
    logger.info("  El backend lo gestiona systemd (servicio bonoloto-2)")
    logger.info("  Este proceso solo monitoriza y programa tareas")
    logger.info("═" * 60)

    # Esperar a que el backend esté disponible
    logger.info("⏳ Esperando a que el backend esté disponible...")
    intentos_iniciales = 0
    while intentos_iniciales < 30:  # max 5 min
        if await verificar_salud_backend():
            logger.info("✅ Backend disponible")
            break
        await asyncio.sleep(10)
        intentos_iniciales += 1
    else:
        logger.warning("⚠ Backend no responde tras 5 min, continuando watchdog igualmente")

    # Configurar scheduler
    scheduler = AsyncIOScheduler(timezone="Europe/Madrid")

    # Actualización tras sorteo: todos los días a las 21:45h (hora española)
    # 15 minutos después del sorteo para asegurar que los datos están publicados
    scheduler.add_job(
        actualizar_datos_sorteo,
        CronTrigger(hour=21, minute=45, timezone="Europe/Madrid"),
        id="actualizar_sorteo",
        name="Actualización diaria tras sorteo Bonoloto",
        replace_existing=True,
    )

    # Backup semanal: domingos a las 03:00h
    scheduler.add_job(
        backup_base_datos,
        CronTrigger(day_of_week="sun", hour=3, minute=0, timezone="Europe/Madrid"),
        id="backup_semanal",
        name="Backup semanal base de datos",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("✅ Scheduler iniciado:")
    logger.info("   • Actualización sorteo: todos los días a las 21:45h (hora española)")
    logger.info("   • Backup semanal: domingos a las 03:00h")

    # Iniciar watchdog
    logger.info("✅ Watchdog activo — comprobando salud cada 60 segundos")
    await bucle_watchdog()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Watchdog detenido por el usuario")
