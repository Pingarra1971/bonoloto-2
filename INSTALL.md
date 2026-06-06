# Instalación de Bonoloto AI v7.0 — Guía paso a paso

Esta guía cubre el despliegue completo del backend Python en una instancia
Oracle Cloud Always Free (ARM Ampere A1, 4 CPU, 24 GB RAM, Ubuntu 22.04).

## 1. Crear instancia Oracle Cloud Always Free

1. Entra en cloud.oracle.com y crea una cuenta gratuita.
2. Crea una nueva instancia VM:
   - Shape: **VM.Standard.A1.Flex** (ARM Ampere)
   - OCPUs: **4** | RAM: **24 GB** (todos los recursos gratuitos)
   - Imagen: **Canonical Ubuntu 22.04** (aarch64)
   - Red: VCN nueva con subred pública
3. Genera y guarda las claves SSH (`ssh-keygen -t ed25519`).
4. Conéctate por SSH: `ssh ubuntu@IP_PUBLICA`.

## 2. Abrir puertos en el firewall Oracle

Ve a Networking → Virtual Cloud Networks → Subred → Lista de seguridad y
añade reglas de ingreso TCP:

- 80 (HTTP)
- 443 (HTTPS)
- 22 (SSH, ya abierto)

En la instancia, abre el firewall local:

```bash
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
sudo netfilter-persistent save
```

## 3. Dependencias del sistema

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3.11 python3.11-venv python3-pip \
    nginx certbot python3-certbot-nginx \
    build-essential libssl-dev libffi-dev \
    libpq-dev unzip git curl
```

## 4. Crear usuario de servicio

```bash
sudo useradd -m -s /bin/bash bonoloto
sudo usermod -aG sudo bonoloto
sudo su - bonoloto
```

## 5. Descargar el código v7.0

```bash
cd /home/bonoloto
mkdir bonoloto_ai && cd bonoloto_ai
# Sube el ZIP por SCP desde tu máquina local:
#   scp bonoloto_ai_v7.zip ubuntu@IP:/home/bonoloto/bonoloto_ai/
unzip bonoloto_ai_v7.zip
cd bonoloto_ai_v7
```

## 6. Entorno virtual Python

```bash
cd /home/bonoloto/bonoloto_ai/bonoloto_ai_v7/backend
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

Esto tardará 5–10 minutos en ARM. Si alguna librería falla por compilación
(p.ej. `oracledb` o `statsmodels`), instala primero su dependencia binaria:

```bash
sudo apt install -y libaio1 cargo gfortran libopenblas-dev
pip install -r requirements.txt --no-cache-dir
```

## 7. Configurar Oracle Autonomous Database (Always Free)

1. En Oracle Cloud → Autonomous Database → Crear nueva (Free Tier).
2. Descarga el Wallet de conexión (ZIP).
3. Súbelo al servidor:
   ```bash
   scp wallet.zip ubuntu@IP:/home/bonoloto/bonoloto_ai/bonoloto_ai_v7/backend/
   ```
4. Descomprime en `/home/bonoloto/wallet/`:
   ```bash
   mkdir -p /home/bonoloto/wallet
   unzip wallet.zip -d /home/bonoloto/wallet/
   chmod 600 /home/bonoloto/wallet/*
   ```
5. Configura las variables de entorno en `/home/bonoloto/bonoloto_ai/bonoloto_ai_v7/backend/.env`:

```bash
cat > /home/bonoloto/bonoloto_ai/bonoloto_ai_v7/backend/.env << 'EOF'
ORACLE_USER=ADMIN
ORACLE_PASSWORD=TuPasswordAdmin
ORACLE_DSN=tu_db_high
ORACLE_WALLET_LOCATION=/home/bonoloto/wallet
JWT_SECRET=GENERA_UN_SECRETO_LARGO_AQUI_CON_OPENSSL
LOG_LEVEL=INFO
EOF
chmod 600 /home/bonoloto/bonoloto_ai/bonoloto_ai_v7/backend/.env
```

Genera el JWT_SECRET con `openssl rand -hex 32`.

## 8. Inicializar base de datos

```bash
source venv/bin/activate
python -c "
import asyncio
from main import BaseDatos
asyncio.run(BaseDatos.inicializar())
print('BD inicializada OK')
"
```

Si tienes histórico de Bonoloto en CSV, súbelo y cárgalo (script propio
según el formato del CSV).

## 9. Servicio systemd

Edita el archivo `bonoloto-ai.service` con las rutas correctas:

```bash
sudo cp /home/bonoloto/bonoloto_ai/bonoloto_ai_v7/backend/bonoloto-ai.service \
    /etc/systemd/system/
sudo nano /etc/systemd/system/bonoloto-ai.service
```

Asegúrate de que las rutas absolutas a `/home/bonoloto/...` son correctas.

```bash
sudo systemctl daemon-reload
sudo systemctl enable bonoloto-ai
sudo systemctl start bonoloto-ai
sudo systemctl status bonoloto-ai
```

## 10. Nginx + HTTPS

```bash
sudo cp /home/bonoloto/bonoloto_ai/bonoloto_ai_v7/backend/nginx.conf \
    /etc/nginx/sites-available/bonoloto-ai
sudo ln -s /etc/nginx/sites-available/bonoloto-ai /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
```

Si tienes dominio (recomendado), configura HTTPS con Let's Encrypt:

```bash
sudo certbot --nginx -d tu-dominio.com
```

## 11. Generar token JWT inicial

```bash
curl -X POST http://IP/api/auth/token?secret=TU_JWT_SECRET
```

Guarda el token devuelto para usar en la app Flutter.

## 12. Verificar todo funciona

```bash
# Health check
curl http://IP/api/health

# Lista de loterías
curl -H "Authorization: Bearer TU_TOKEN" \
     http://IP/api/bloque-l/loterias

# Lista de sistemas reducidos
curl -H "Authorization: Bearer TU_TOKEN" \
     http://IP/api/bloque-l/sistemas-reducidos

# Esperanza matemática con bote alto
curl -H "Authorization: Bearer TU_TOKEN" \
     "http://IP/api/bloque-l/roi?bote_eur=5000000"
```

## 13. Programar reentrenamiento automático

El sistema viene con `watchdog_scheduler.py` que reentrena tras cada sorteo
(lunes–domingo a las 21:45h España) y hace backup semanal (domingos 03:00h).

Verificar con:

```bash
sudo journalctl -u bonoloto-ai -f
```

## 14. Configurar la app Flutter

En el archivo `lib/services/api_service.dart` de la app Flutter:

```dart
const String API_BASE_URL = 'https://tu-dominio.com/api';
const String AUTH_TOKEN = 'token_jwt_generado_arriba';
```

Compila la app:

```bash
cd /ruta/al/proyecto/flutter
flutter pub get
flutter build apk --release  # Android
flutter build ios --release  # iOS (necesita macOS)
```

## Soluciones a problemas comunes

**Problema:** El servicio se queda sin memoria durante el cálculo (OOM).
**Solución:** Activa swap:

```bash
sudo fallocate -l 8G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

**Problema:** Cálculo tarda más de 30 min.
**Solución:** Es normal en la primera ejecución (caché frío). Las siguientes
ejecuciones tardarán 12–22 min de media gracias al caché de scores.

**Problema:** Error de conexión a la base Oracle.
**Solución:** Verifica que el wallet está descomprimido en
`/home/bonoloto/wallet/` y que `sqlnet.ora` referencia esa ruta. Edita el
archivo `sqlnet.ora` del wallet:

```
WALLET_LOCATION = (SOURCE = (METHOD = file) (METHOD_DATA = (DIRECTORY="/home/bonoloto/wallet")))
SSL_SERVER_DN_MATCH=yes
```

## Costes mensuales esperados

**0,00 €** si te mantienes dentro de los límites Always Free de Oracle Cloud:
- 4 OCPU ARM + 24 GB RAM (1 instancia A1.Flex)
- 200 GB de almacenamiento
- 10 TB transferencia mensual
- 20 GB Autonomous Database
