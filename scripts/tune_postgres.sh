#!/bin/bash
# Postgres tuning untuk VPS 2C/3.8GB shared cloud.
# Target: boost POST /orders/ & GET /products/ 2-3x tanpa upgrade hardware.
#
# Usage:
#   sudo bash /var/www/kasira/scripts/tune_postgres.sh
#
# Rollback:
#   sudo bash /var/www/kasira/scripts/tune_postgres.sh --rollback

set -e

CONFIG_FILE="/var/lib/postgresql/data/postgresql.conf"
BACKUP_FILE="/var/lib/postgresql/data/postgresql.conf.backup-$(date +%Y%m%d-%H%M%S)"
MARKER_START="# === KASIRA TUNING START ==="
MARKER_END="# === KASIRA TUNING END ==="

if [[ "$1" == "--rollback" ]]; then
    echo "[rollback] Removing Kasira tuning block..."
    sudo docker exec kasira-db-1 sed -i "/$MARKER_START/,/$MARKER_END/d" "$CONFIG_FILE"
    echo "[rollback] Restarting postgres..."
    sudo docker restart kasira-db-1
    echo "[rollback] Done. Config back to default."
    exit 0
fi

echo "[1/5] Backup current postgresql.conf..."
sudo docker exec kasira-db-1 cp "$CONFIG_FILE" "$BACKUP_FILE"
echo "      Backup: $BACKUP_FILE"

echo "[2/5] Check if tuning already applied..."
if sudo docker exec kasira-db-1 grep -q "$MARKER_START" "$CONFIG_FILE"; then
    echo "      Already tuned. Removing old block first..."
    sudo docker exec kasira-db-1 sed -i "/$MARKER_START/,/$MARKER_END/d" "$CONFIG_FILE"
fi

echo "[3/5] Apply tuning..."
sudo docker exec kasira-db-1 bash -c "cat >> $CONFIG_FILE << 'EOF'

$MARKER_START
# Tuned for VPS 2C/3.8GB shared, postgres container 1GB limit.
# Applied: $(date -u +%Y-%m-%dT%H:%M:%SZ)
shared_buffers = 256MB
work_mem = 8MB
effective_cache_size = 2GB
maintenance_work_mem = 64MB
random_page_cost = 1.1
effective_io_concurrency = 200
$MARKER_END
EOF"

echo "[4/5] Restart postgres (10-30s downtime)..."
sudo docker restart kasira-db-1

echo "[5/5] Wait for postgres ready..."
for i in {1..30}; do
    if sudo docker exec kasira-db-1 pg_isready -U kasira -d kasira_db > /dev/null 2>&1; then
        echo "      Postgres ready after ${i}s"
        break
    fi
    sleep 1
done

echo ""
echo "=== Verification ==="
sudo docker exec kasira-db-1 psql -U kasira -d kasira_db -c "
SHOW shared_buffers;
SHOW work_mem;
SHOW effective_cache_size;
SHOW random_page_cost;
"

echo ""
echo "=== Cache warmup (pg_prewarm) ==="
sudo docker exec kasira-db-1 psql -U kasira -d kasira_db -c "
CREATE EXTENSION IF NOT EXISTS pg_prewarm;
SELECT pg_prewarm('products');
SELECT pg_prewarm('orders');
SELECT pg_prewarm('order_items');
SELECT pg_prewarm('categories');
SELECT pg_prewarm('payments');
" 2>&1 | tail -15

echo ""
echo "[DONE] Postgres tuned. Test via:"
echo "   curl -w '\\nTime: %{time_total}s\\n' http://localhost:8000/api/v1/health"
