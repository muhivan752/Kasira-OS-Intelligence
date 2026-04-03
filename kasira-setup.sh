#!/bin/bash
# ============================================================
#  kasira-setup.sh — One-command VPS setup untuk Kasira POS
#  Tested: Ubuntu 22.04 LTS
#
#  Cara pakai:
#    curl -fsSL https://raw.githubusercontent.com/muhivan752/Kasira-OS-Intelligence/main/kasira-setup.sh | bash
#  atau:
#    bash kasira-setup.sh
# ============================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

KASIRA_DIR="/var/www/kasira"
REPO_URL="https://github.com/muhivan752/Kasira-OS-Intelligence.git"

log()  { echo -e "${GREEN}[✓]${NC} $1"; }
info() { echo -e "${BLUE}[i]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
err()  { echo -e "${RED}[✗]${NC} $1"; exit 1; }

banner() {
  echo ""
  echo -e "${BOLD}${BLUE}╔══════════════════════════════════════════╗${NC}"
  echo -e "${BOLD}${BLUE}║        KASIRA POS — VPS Setup            ║${NC}"
  echo -e "${BOLD}${BLUE}║   Smart POS untuk Cafe Indonesia          ║${NC}"
  echo -e "${BOLD}${BLUE}╚══════════════════════════════════════════╝${NC}"
  echo ""
}

check_root() {
  if [ "$EUID" -ne 0 ]; then
    err "Jalankan sebagai root: sudo bash kasira-setup.sh"
  fi
}

get_server_ip() {
  SERVER_IP=$(curl -s ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')
  info "IP Server: ${BOLD}$SERVER_IP${NC}"
}

install_dependencies() {
  info "Mengupdate sistem dan menginstall dependensi..."
  apt-get update -qq
  apt-get install -y -qq \
    curl wget git unzip \
    ca-certificates gnupg \
    lsb-release apt-transport-https \
    ufw fail2ban \
    > /dev/null 2>&1
  log "Dependensi dasar terinstall"
}

install_docker() {
  if command -v docker &>/dev/null; then
    log "Docker sudah ada ($(docker --version | cut -d' ' -f3 | tr -d ','))"
    return
  fi

  info "Menginstall Docker..."
  curl -fsSL https://get.docker.com | sh > /dev/null 2>&1
  systemctl enable docker --quiet
  systemctl start docker

  # Install Docker Compose v2
  COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep '"tag_name"' | cut -d'"' -f4)
  curl -fsSL "https://github.com/docker/compose/releases/download/${COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" \
    -o /usr/local/bin/docker-compose > /dev/null 2>&1
  chmod +x /usr/local/bin/docker-compose
  log "Docker & Docker Compose terinstall"
}

setup_firewall() {
  info "Konfigurasi firewall UFW..."
  ufw --force reset > /dev/null 2>&1
  ufw default deny incoming > /dev/null 2>&1
  ufw default allow outgoing > /dev/null 2>&1
  ufw allow ssh > /dev/null 2>&1
  ufw allow 80/tcp > /dev/null 2>&1    # HTTP (Nginx)
  ufw allow 443/tcp > /dev/null 2>&1   # HTTPS
  ufw allow 8000/tcp > /dev/null 2>&1  # FastAPI (direct access dari app)
  ufw allow 3000/tcp > /dev/null 2>&1  # Next.js Dashboard
  ufw --force enable > /dev/null 2>&1
  log "Firewall aktif (port 22, 80, 443, 8000, 3000)"
}

clone_or_update_repo() {
  if [ -d "$KASIRA_DIR/.git" ]; then
    info "Repo sudah ada, pulling update..."
    cd "$KASIRA_DIR"
    git pull origin main 2>/dev/null || git pull origin claude/review-documentation-qqAkC 2>/dev/null || true
    log "Repo diupdate"
  else
    info "Cloning repo ke $KASIRA_DIR..."
    mkdir -p /var/www
    git clone "$REPO_URL" "$KASIRA_DIR" --depth=1 2>/dev/null || \
      git clone "$REPO_URL" "$KASIRA_DIR"
    log "Repo di-clone"
  fi
  cd "$KASIRA_DIR"
}

generate_secrets() {
  info "Membuat secret keys..."
  SECRET_KEY=$(openssl rand -hex 32)
  ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" 2>/dev/null || openssl rand -base64 32)
  DB_PASS=$(openssl rand -hex 16)
}

create_env_file() {
  if [ -f "$KASIRA_DIR/.env" ]; then
    warn ".env sudah ada. Skip (tidak ditimpa)."
    # Load existing values
    source "$KASIRA_DIR/.env" 2>/dev/null || true
    return
  fi

  info "Membuat file .env..."

  # Prompt untuk kredensial eksternal
  echo ""
  echo -e "${BOLD}Masukkan kredensial Fonnte (WA OTP):${NC}"
  read -rp "  FONNTE_TOKEN (bisa kosong dulu, isi nanti): " INPUT_FONNTE
  FONNTE_TOKEN=${INPUT_FONNTE:-""}

  echo ""
  echo -e "${BOLD}Masukkan kredensial Xendit (payment):${NC}"
  read -rp "  XENDIT_API_KEY (bisa kosong dulu): " INPUT_XENDIT_KEY
  read -rp "  XENDIT_WEBHOOK_TOKEN (bisa kosong dulu): " INPUT_XENDIT_WEBHOOK
  XENDIT_API_KEY=${INPUT_XENDIT_KEY:-""}
  XENDIT_WEBHOOK_TOKEN=${INPUT_XENDIT_WEBHOOK:-""}

  echo ""
  echo -e "${BOLD}Masukkan API Key Claude AI (untuk AI Chatbot Owner):${NC}"
  read -rp "  ANTHROPIC_API_KEY (bisa kosong dulu, isi nanti): " INPUT_ANTHROPIC
  ANTHROPIC_API_KEY=${INPUT_ANTHROPIC:-""}

  echo ""
  echo -e "${BOLD}Masukkan Sentry DSN (untuk error tracking — opsional):${NC}"
  echo -e "  Buat project di sentry.io → Settings → Client Keys → DSN"
  read -rp "  SENTRY_DSN (kosongkan jika belum punya): " INPUT_SENTRY
  SENTRY_DSN=${INPUT_SENTRY:-""}

  cat > "$KASIRA_DIR/.env" <<EOF
# ── Database ────────────────────────────────────────────
POSTGRES_SERVER=db
POSTGRES_USER=kasira
POSTGRES_PASSWORD=${DB_PASS}
POSTGRES_DB=kasira_db
POSTGRES_PORT=5432

# ── Redis ────────────────────────────────────────────────
REDIS_URL=redis://redis:6379/0

# ── Security ─────────────────────────────────────────────
SECRET_KEY=${SECRET_KEY}
ENCRYPTION_KEY=${ENCRYPTION_KEY}

# ── CORS ─────────────────────────────────────────────────
BACKEND_CORS_ORIGINS=["http://${SERVER_IP}:3000","http://localhost:3000","https://${SERVER_IP}"]

# ── Frontend ─────────────────────────────────────────────
NEXT_PUBLIC_API_URL=http://${SERVER_IP}:8000/api/v1

# ── WhatsApp OTP (Fonnte) ─────────────────────────────────
FONNTE_TOKEN=${FONNTE_TOKEN}

# ── Payment (Xendit) ─────────────────────────────────────
XENDIT_API_KEY=${XENDIT_API_KEY}
XENDIT_WEBHOOK_TOKEN=${XENDIT_WEBHOOK_TOKEN}
XENDIT_IS_PRODUCTION=False

# ── Claude AI ───────────────────────────────────────────
ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}

# Sentry Error Tracking
SENTRY_DSN=${SENTRY_DSN}
NEXT_PUBLIC_SENTRY_DSN=${SENTRY_DSN}

# ── App ──────────────────────────────────────────────────
ENVIRONMENT=production
EOF
  log ".env dibuat"
}

docker_up() {
  info "Membangun dan menjalankan container..."
  cd "$KASIRA_DIR"
  docker-compose pull --quiet 2>/dev/null || true
  docker-compose up -d --build 2>&1 | tail -5
  log "Container berjalan"
}

wait_for_backend() {
  info "Menunggu backend ready..."
  for i in $(seq 1 30); do
    if curl -sf http://localhost:8000/ > /dev/null 2>&1; then
      log "Backend ready"
      return
    fi
    sleep 3
    echo -n "."
  done
  echo ""
  warn "Backend belum respond setelah 90 detik. Cek: docker-compose logs backend"
}

run_migrations_and_seed() {
  info "Menjalankan migrasi database..."
  docker-compose exec -T backend alembic upgrade head 2>&1 | tail -3
  log "Migrasi selesai"

  info "Membuat akun admin..."
  docker-compose exec -T backend python -m backend.scripts.seed_admin 2>&1
}

setup_backup_cron() {
  info "Menyiapkan backup otomatis (pg_dump ke /var/backups/kasira)..."
  mkdir -p /var/backups/kasira

  # Load DB vars dari .env
  DB_USER=$(grep POSTGRES_USER "$KASIRA_DIR/.env" | cut -d= -f2)
  DB_NAME=$(grep POSTGRES_DB "$KASIRA_DIR/.env" | cut -d= -f2)
  DB_PASS_VAL=$(grep POSTGRES_PASSWORD "$KASIRA_DIR/.env" | cut -d= -f2)

  cat > /etc/cron.d/kasira-backup <<CRON
# Kasira DB Backup — tiap 6 jam (Rule #45)
0 */6 * * * root PGPASSWORD="${DB_PASS_VAL}" docker exec kasira-os-intelligence-db-1 pg_dump -U ${DB_USER} ${DB_NAME} | gzip > /var/backups/kasira/kasira_\$(date +\%Y\%m\%d_\%H\%M).sql.gz 2>&1
# Hapus backup lebih dari 7 hari
30 2 * * * root find /var/backups/kasira -name "*.sql.gz" -mtime +7 -delete
CRON

  chmod 644 /etc/cron.d/kasira-backup
  log "Backup cron aktif (tiap 6 jam)"
}

setup_auto_restart() {
  info "Mengatur auto-restart on boot..."
  cat > /etc/systemd/system/kasira.service <<SERVICE
[Unit]
Description=Kasira POS Docker Compose
Requires=docker.service
After=docker.service network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=${KASIRA_DIR}
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
SERVICE

  systemctl daemon-reload
  systemctl enable kasira.service --quiet
  log "Auto-restart on boot aktif"
}

print_summary() {
  echo ""
  echo -e "${GREEN}${BOLD}╔══════════════════════════════════════════════════════╗${NC}"
  echo -e "${GREEN}${BOLD}║            ✅  KASIRA BERHASIL DIINSTALL!            ║${NC}"
  echo -e "${GREEN}${BOLD}╚══════════════════════════════════════════════════════╝${NC}"
  echo ""
  echo -e "  ${BOLD}URL Backend API :${NC} http://${SERVER_IP}:8000"
  echo -e "  ${BOLD}URL Dashboard   :${NC} http://${SERVER_IP}:3000"
  echo -e "  ${BOLD}API Docs        :${NC} http://${SERVER_IP}:8000/api/v1/openapi.json"
  echo ""
  echo -e "  ${BOLD}──── Akun Admin ────────────────────────────────────${NC}"
  echo -e "  ${BOLD}Phone           :${NC} 628111222333"
  echo -e "  ${BOLD}PIN             :${NC} 111222"
  echo -e "  ${BOLD}OTP dev         :${NC} 123456  (non-production)"
  echo ""
  echo -e "  ${BOLD}──── Setting URL di Flutter App ─────────────────────${NC}"
  echo -e "  Buka app → Server belum terkonfigurasi → masukkan:"
  echo -e "  ${YELLOW}http://${SERVER_IP}:8000${NC}"
  echo ""
  echo -e "  ${BOLD}──── Perintah berguna ───────────────────────────────${NC}"
  echo -e "  Lihat log   : ${YELLOW}docker-compose -f ${KASIRA_DIR}/docker-compose.yml logs -f${NC}"
  echo -e "  Restart     : ${YELLOW}docker-compose -f ${KASIRA_DIR}/docker-compose.yml restart${NC}"
  echo -e "  Update app  : ${YELLOW}cd ${KASIRA_DIR} && git pull && docker-compose up -d --build${NC}"
  echo ""
}

# ── Main ──────────────────────────────────────────────────────────────────────
banner
check_root
get_server_ip
install_dependencies
install_docker
setup_firewall
clone_or_update_repo
generate_secrets
create_env_file
docker_up
wait_for_backend
run_migrations_and_seed
setup_backup_cron
setup_auto_restart
print_summary
