#!/bin/bash
# ============================================================
# Kasira POS — VPS Migration Script
# ============================================================
# Jalankan di VPS BARU setelah fresh Ubuntu 22.04/24.04
#
# Usage:
#   1. Di VPS LAMA: bash scripts/migrate-vps.sh backup
#   2. Transfer backup ke VPS baru
#   3. Di VPS BARU:  bash scripts/migrate-vps.sh setup
#   4. Di VPS BARU:  bash scripts/migrate-vps.sh restore
#   5. Update DNS A record ke IP baru
#   6. Di VPS BARU:  bash scripts/migrate-vps.sh ssl
# ============================================================

set -e

BACKUP_DIR="/tmp/kasira-migration"
DOMAIN="kasira.online"

case "${1:-help}" in

# ── STEP 1: Backup di VPS lama ──────────────────────────────
backup)
    echo "=== Backing up Kasira from current VPS ==="
    mkdir -p "$BACKUP_DIR"

    # 1. Database dump
    echo "[1/4] Dumping PostgreSQL..."
    docker compose -f /var/www/kasira/docker-compose.yml exec -T db \
        pg_dump -U kasira kasira_db > "$BACKUP_DIR/kasira_db.sql"
    echo "  DB dump: $(du -h $BACKUP_DIR/kasira_db.sql | cut -f1)"

    # 2. Uploads
    echo "[2/4] Copying uploads..."
    docker cp kasira-backend-1:/app/uploads "$BACKUP_DIR/uploads" 2>/dev/null || mkdir -p "$BACKUP_DIR/uploads"

    # 3. Env file
    echo "[3/4] Copying .env..."
    cp /var/www/kasira/.env "$BACKUP_DIR/dot-env"

    # 4. Nginx config
    echo "[4/4] Copying nginx config..."
    cp /etc/nginx/sites-available/kasira "$BACKUP_DIR/nginx-kasira"

    # Tarball
    echo "Creating tarball..."
    tar czf /tmp/kasira-migration.tar.gz -C /tmp kasira-migration
    echo ""
    echo "=== Backup complete: /tmp/kasira-migration.tar.gz ==="
    echo "Transfer ke VPS baru dengan:"
    echo "  scp /tmp/kasira-migration.tar.gz root@NEW_VPS_IP:/tmp/"
    ;;

# ── STEP 2: Setup VPS baru ──────────────────────────────────
setup)
    echo "=== Setting up fresh VPS for Kasira ==="

    # 1. System update
    echo "[1/6] Updating system..."
    apt update && apt upgrade -y

    # 2. Install Docker
    echo "[2/6] Installing Docker..."
    if ! command -v docker &>/dev/null; then
        curl -fsSL https://get.docker.com | sh
        systemctl enable docker
        systemctl start docker
    else
        echo "  Docker already installed"
    fi

    # 3. Install Nginx
    echo "[3/6] Installing Nginx..."
    apt install -y nginx

    # 4. Install Certbot
    echo "[4/6] Installing Certbot..."
    apt install -y certbot python3-certbot-nginx

    # 5. Clone repo
    echo "[5/6] Cloning Kasira repo..."
    if [ ! -d /var/www/kasira ]; then
        mkdir -p /var/www
        git clone https://github.com/muhivan752/Kasira-OS-Intelligence.git /var/www/kasira
    else
        echo "  Repo already exists"
    fi

    # 6. UFW
    echo "[6/6] Configuring firewall..."
    ufw allow 22/tcp
    ufw allow 80/tcp
    ufw allow 443/tcp
    ufw --force enable

    echo ""
    echo "=== Setup complete! Now run: bash scripts/migrate-vps.sh restore ==="
    ;;

# ── STEP 3: Restore data di VPS baru ────────────────────────
restore)
    echo "=== Restoring Kasira data ==="

    # Extract backup
    if [ -f /tmp/kasira-migration.tar.gz ]; then
        echo "[0/5] Extracting backup..."
        tar xzf /tmp/kasira-migration.tar.gz -C /tmp
    fi

    if [ ! -d "$BACKUP_DIR" ]; then
        echo "ERROR: $BACKUP_DIR not found. Transfer backup first!"
        exit 1
    fi

    # 1. Restore .env
    echo "[1/5] Restoring .env..."
    cp "$BACKUP_DIR/dot-env" /var/www/kasira/.env

    # 2. Build & start containers (DB first)
    echo "[2/5] Building & starting containers..."
    cd /var/www/kasira
    docker compose up -d db redis
    echo "  Waiting for DB to be ready..."
    sleep 10

    # 3. Restore database
    echo "[3/5] Restoring database..."
    docker compose exec -T db psql -U kasira kasira_db < "$BACKUP_DIR/kasira_db.sql"

    # 4. Start all services
    echo "[4/5] Starting all services..."
    docker compose up -d

    # 5. Restore uploads
    echo "[5/5] Restoring uploads..."
    if [ -d "$BACKUP_DIR/uploads" ]; then
        docker cp "$BACKUP_DIR/uploads/." kasira-backend-1:/app/uploads/
    fi

    # 6. Setup Nginx
    echo "[+] Setting up Nginx..."
    cp "$BACKUP_DIR/nginx-kasira" /etc/nginx/sites-available/kasira
    ln -sf /etc/nginx/sites-available/kasira /etc/nginx/sites-enabled/kasira
    rm -f /etc/nginx/sites-enabled/default

    # Add rate limiting to nginx.conf if not present
    if ! grep -q "auth_limit" /etc/nginx/nginx.conf; then
        sed -i '/include \/etc\/nginx\/sites-enabled/i\\t# Rate limiting (Kasira)\n\tlimit_req_zone $binary_remote_addr zone=auth_limit:10m rate=5r/m;\n\tlimit_req_zone $binary_remote_addr zone=api_limit:10m rate=30r/s;\n' /etc/nginx/nginx.conf
    fi

    # Temporarily remove SSL lines for initial test (certbot will add them)
    sed -i '/listen 443 ssl/d; /ssl_certificate/d; /ssl_dhparam/d; /include.*letsencrypt/d' /etc/nginx/sites-available/kasira
    # Add listen 80 to main server block
    sed -i '/server_name kasira.online/a\    listen 80;' /etc/nginx/sites-available/kasira

    nginx -t && systemctl reload nginx

    echo ""
    echo "=== Restore complete! ==="
    echo ""
    echo "Next steps:"
    echo "  1. Update DNS A record: $DOMAIN → $(curl -s ifconfig.me)"
    echo "  2. Wait for DNS propagation (5-30 min)"
    echo "  3. Run: bash scripts/migrate-vps.sh ssl"
    ;;

# ── STEP 4: Setup SSL ───────────────────────────────────────
ssl)
    echo "=== Setting up SSL with Let's Encrypt ==="
    certbot --nginx -d "$DOMAIN" -d "www.$DOMAIN" --non-interactive --agree-tos -m muhivan752@gmail.com
    systemctl reload nginx
    echo "=== SSL configured! https://$DOMAIN should work now ==="
    ;;

# ── Cron backup setup ───────────────────────────────────────
backup-cron)
    echo "=== Setting up automated backups ==="
    cat > /etc/cron.d/kasira-backup << 'CRON'
# Kasira DB backup every 6 hours
0 */6 * * * root docker compose -f /var/www/kasira/docker-compose.yml exec -T db pg_dump -U kasira kasira_db | gzip > /var/backups/kasira/kasira_db_$(date +\%Y\%m\%d_\%H\%M).sql.gz
# Cleanup backups older than 7 days
0 3 * * * root find /var/backups/kasira -name "*.sql.gz" -mtime +7 -delete
CRON
    mkdir -p /var/backups/kasira
    echo "Backup cron installed (every 6 hours)"
    ;;

*)
    echo "Kasira VPS Migration Tool"
    echo ""
    echo "Usage:"
    echo "  VPS LAMA:"
    echo "    bash scripts/migrate-vps.sh backup     # Step 1: Backup semua data"
    echo ""
    echo "  Transfer: scp /tmp/kasira-migration.tar.gz root@NEW_IP:/tmp/"
    echo ""
    echo "  VPS BARU:"
    echo "    bash scripts/migrate-vps.sh setup       # Step 2: Install Docker, Nginx, clone repo"
    echo "    bash scripts/migrate-vps.sh restore      # Step 3: Restore DB, uploads, config"
    echo "    bash scripts/migrate-vps.sh ssl          # Step 4: Setup SSL (after DNS updated)"
    echo "    bash scripts/migrate-vps.sh backup-cron  # Step 5: Setup automated backups"
    ;;
esac
