#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════
# BONOLOTO 2.0 — INSTALADOR AUTOMÁTICO DE SERVIDOR
# ═══════════════════════════════════════════════════════════════════════
# Automatiza la instalación del backend en Ubuntu 24 (Oracle Cloud ARM).
# Reduce ~40 pasos manuales a uno.
#
# NO puede crear la cuenta Oracle ni descargar el wallet (eso se hace en la
# web de Oracle por una persona). Esos datos se piden durante la instalación.
#
# USO:  cd bonoloto_2/install && sudo bash install_servidor.sh
# ═══════════════════════════════════════════════════════════════════════
set -euo pipefail
ROJO='\033[0;31m'; VERDE='\033[0;32m'; AMARILLO='\033[1;33m'; AZUL='\033[0;34m'; NC='\033[0m'
ok()    { echo -e "${VERDE}✓${NC} $1"; }
info()  { echo -e "${AZUL}ℹ${NC} $1"; }
aviso() { echo -e "${AMARILLO}⚠${NC} $1"; }
error() { echo -e "${ROJO}✗ ERROR:${NC} $1"; exit 1; }

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║              BONOLOTO 2.0 — INSTALADOR                        ║"
echo "╚══════════════════════════════════════════════════════════════╝"

[ "$(id -u)" -eq 0 ] || error "Ejecuta con sudo: sudo bash install_servidor.sh"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROYECTO_ORIGEN="$(dirname "$SCRIPT_DIR")"
[ -f "$PROYECTO_ORIGEN/requirements.txt" ] && [ -d "$PROYECTO_ORIGEN/app" ] || error "Ejecuta desde bonoloto_2/install/"
ok "Proyecto localizado en: $PROYECTO_ORIGEN"
DESTINO="/home/bonoloto/bonoloto_2"

info "Instalando dependencias del sistema..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq python3.11 python3.11-venv python3.11-dev python3-pip nginx build-essential libssl-dev libffi-dev git curl unzip jq >/dev/null 2>&1 || apt-get install -y python3 python3-venv python3-dev python3-pip nginx build-essential curl unzip jq
ok "Dependencias del sistema instaladas"
if command -v python3.11 >/dev/null 2>&1; then PY=python3.11; else PY=python3; fi
info "Usando $PY ($($PY --version))"

if ! id bonoloto >/dev/null 2>&1; then useradd -m -s /bin/bash bonoloto; ok "Usuario 'bonoloto' creado"; else info "Usuario 'bonoloto' ya existe"; fi

info "Copiando proyecto a $DESTINO..."
mkdir -p "$DESTINO"
[ -d "$DESTINO/venv" ] && mv "$DESTINO/venv" /tmp/bonoloto_venv_backup || true
cp -r "$PROYECTO_ORIGEN"/. "$DESTINO"/
[ -d /tmp/bonoloto_venv_backup ] && { rm -rf "$DESTINO/venv"; mv /tmp/bonoloto_venv_backup "$DESTINO/venv"; } || true
chown -R bonoloto:bonoloto "$DESTINO"
ok "Proyecto copiado"

info "Creando entorno virtual e instalando dependencias Python (puede tardar)..."
sudo -u bonoloto bash -c "cd $DESTINO && $PY -m venv venv && venv/bin/pip install --upgrade pip setuptools wheel --quiet && venv/bin/pip install -r requirements.txt --quiet"
ok "Dependencias Python instaladas"

ENV_FILE="/etc/bonoloto-2.env"

# Carpeta para la base de datos de archivo (SQLite), propiedad de bonoloto.
DATOS_DIR="$DESTINO/datos"
mkdir -p "$DATOS_DIR"
chown -R bonoloto:bonoloto "$DATOS_DIR"

if [ -f "$ENV_FILE" ]; then
    aviso "$ENV_FILE ya existe. No lo sobrescribo."
else
    info "Base de datos: se usará un archivo local (SQLite). No necesitas Oracle."
    info "Lo único que necesito es tu clave de la API de resultados (loteriasapi.com)."
    read -p "  LOTERIAS_API_KEY [puedes dejarlo vacío y ponerlo luego]: " L_KEY
    JWT_SECRET=$(openssl rand -hex 32)
    cat > "$ENV_FILE" <<EOF
JWT_SECRET=$JWT_SECRET

# ── Base de datos ──
# Por defecto: archivo local SQLite (sin configuración, sin wallet).
DB_BACKEND=sqlite
SQLITE_PATH=$DATOS_DIR/bonoloto.db

# ── Clave de la API de resultados (loteriasapi.com) ──
LOTERIAS_API_KEY=$L_KEY

# ── Servidor ──
PORT=8000
HOST=0.0.0.0
LOG_LEVEL=INFO
BACKEND_URL=http://localhost:8000

# ── (OPCIONAL) Oracle Autonomous Database ──
# Si algún día prefieres usar Oracle en vez del archivo local, pon
# DB_BACKEND=oracle y rellena estas líneas (y descarga el wallet):
# ORACLE_USER=
# ORACLE_PASSWORD=
# ORACLE_DSN=
# ORACLE_WALLET_LOCATION=
# ORACLE_WALLET_PASSWORD=
EOF
    chmod 600 "$ENV_FILE"; chown root:bonoloto "$ENV_FILE"
    ok "Configuración creada en $ENV_FILE (base de datos de archivo, lista para usar)"
    aviso "JWT_SECRET generado automáticamente: $JWT_SECRET"
fi

info "Instalando servicio systemd..."
cp "$DESTINO/install/bonoloto-2.service" /etc/systemd/system/bonoloto-2.service
systemctl daemon-reload
systemctl enable bonoloto-2 >/dev/null 2>&1
ok "Servicio instalado y habilitado"

info "Ejecutando tests de verificación..."
if sudo -u bonoloto bash -c "cd $DESTINO && venv/bin/python run_tests.py" 2>&1 | grep -q "0 fail"; then
    ok "Tests pasan correctamente"
else
    aviso "Algunos tests fallaron. La instalación continúa; revisa la salida."
fi

info "Arrancando el servicio..."
systemctl restart bonoloto-2
sleep 3
if systemctl is-active --quiet bonoloto-2; then ok "Servicio bonoloto-2 ARRANCADO"; else aviso "No arrancó. Revisa: sudo journalctl -u bonoloto-2 -n 50"; fi

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                    INSTALACIÓN COMPLETADA                     ║"
echo "╚══════════════════════════════════════════════════════════════╝"
ok "Backend en: $DESTINO  |  Config en: $ENV_FILE"
info "Comandos: sudo systemctl status bonoloto-2 | sudo journalctl -u bonoloto-2 -f"
info "Probar:   curl http://localhost:8000/api/health"
aviso "Si dejaste vacíos los datos Oracle, edítalos en $ENV_FILE y reinicia."
aviso "Para la APP MÓVIL usa: install/compilar_app.sh (necesita Flutter)."
