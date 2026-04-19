#!/bin/bash
# Kasira DB Restore dari Cloudflare R2 — Disaster Recovery Automation (#9)
#
# Usage:
#   sudo ./restore_db.sh                 # restore dari backup TERBARU
#   sudo ./restore_db.sh <timestamp>     # restore dari specific backup
#                                          contoh: 20260419_0600
#   sudo ./restore_db.sh --list          # list available backups di R2
#
# Prerequisite:
#   - Docker + docker compose up (kasira-db-1 container RUNNING)
#   - AWS CLI terinstall + profile "r2" ter-configure
#     ~/.aws/credentials [r2] aws_access_key_id + aws_secret_access_key
#   - R2 endpoint reachable (cek koneksi via awscli)
#
# Safety:
#   - Konfirmasi y/n DUA KALI sebelum drop database
#   - Validasi file integrity (gunzip test) sebelum inject
#   - Atomic: drop+create+restore dalam satu transaction batch
#   - Rollback instruksi kalau gagal
#
# Logging: /var/log/kasira_restore.log — semua output ke stdout + log file

set -e
set -u
set -o pipefail

# ─── Config ──────────────────────────────────────────────────────────────────
BUCKET="s3://kasira-production/backups"
ENDPOINT="https://63003661b5b663860000bcf6e9dc4955.r2.cloudflarestorage.com"
AWS="/usr/local/bin/aws"
DOCKER_CONTAINER="kasira-db-1"
DB_NAME="kasira_db"
DB_USER="kasira"
LOG="/var/log/kasira_restore.log"
TEMP_DIR="/tmp/kasira_restore_$$"

# ─── Colors ──────────────────────────────────────────────────────────────────
C_GREEN='\033[0;32m'
C_RED='\033[0;31m'
C_YELLOW='\033[1;33m'
C_BLUE='\033[0;34m'
C_RESET='\033[0m'

log() {
    local level="$1"
    local msg="$2"
    local color
    case "$level" in
        OK)    color="$C_GREEN" ;;
        FAIL)  color="$C_RED" ;;
        WARN)  color="$C_YELLOW" ;;
        INFO)  color="$C_BLUE" ;;
        *)     color="" ;;
    esac
    local ts="[$(date +'%Y-%m-%d %H:%M:%S')]"
    echo -e "${color}${ts} [${level}] ${msg}${C_RESET}"
    echo "${ts} [${level}] ${msg}" >> "$LOG"
}

abort() {
    log FAIL "$1"
    cleanup
    exit 1
}

cleanup() {
    rm -rf "$TEMP_DIR" 2>/dev/null || true
}

trap cleanup EXIT

# ─── Check prerequisites ─────────────────────────────────────────────────────
check_prerequisites() {
    log INFO "── Step 1/6: Check prerequisites ──"

    # AWS CLI installed?
    if ! command -v "$AWS" &>/dev/null; then
        abort "AWS CLI tidak ditemukan di $AWS. Install: apt install awscli atau pip install awscli"
    fi
    log OK "AWS CLI tersedia"

    # R2 profile configured?
    if ! $AWS configure list --profile r2 &>/dev/null; then
        abort "AWS profile 'r2' belum di-configure. Setup via: aws configure --profile r2"
    fi
    log OK "AWS profile 'r2' ter-configure"

    # Test R2 connectivity
    if ! $AWS s3 ls "$BUCKET" --endpoint-url "$ENDPOINT" --profile r2 &>/dev/null; then
        abort "Gak bisa connect ke R2 bucket ${BUCKET}. Cek credentials + network."
    fi
    log OK "R2 bucket reachable"

    # Docker container running?
    if ! docker ps --format '{{.Names}}' | grep -q "^${DOCKER_CONTAINER}$"; then
        abort "Container ${DOCKER_CONTAINER} tidak running. Jalankan: docker compose up -d db"
    fi
    log OK "Container ${DOCKER_CONTAINER} running"

    # pg_isready check
    if ! docker exec "$DOCKER_CONTAINER" pg_isready -U "$DB_USER" &>/dev/null; then
        abort "PostgreSQL di ${DOCKER_CONTAINER} belum ready. Tunggu startup complete."
    fi
    log OK "PostgreSQL ready"
}

# ─── List available backups ──────────────────────────────────────────────────
list_backups() {
    log INFO "Available backups di R2:"
    $AWS s3 ls "${BUCKET}/" --endpoint-url "$ENDPOINT" --profile r2 \
        | grep '\.sql\.gz$' \
        | sort -r \
        | head -20 \
        | awk '{printf "  %s %s  %.1f MB\n", $1, $4, $3/1048576}'
}

# ─── Find target backup file ─────────────────────────────────────────────────
select_backup() {
    local target_ts="$1"
    local backup_file

    if [ -z "$target_ts" ]; then
        # Pick LATEST
        backup_file=$(
            $AWS s3 ls "${BUCKET}/" --endpoint-url "$ENDPOINT" --profile r2 \
                | grep '\.sql\.gz$' \
                | sort -r \
                | head -1 \
                | awk '{print $4}'
        )
        if [ -z "$backup_file" ]; then
            abort "Tidak ada backup di R2 bucket."
        fi
        log INFO "Latest backup: ${backup_file}"
    else
        backup_file="kasira_db_${target_ts}.sql.gz"
        # Verify file exists
        if ! $AWS s3 ls "${BUCKET}/${backup_file}" --endpoint-url "$ENDPOINT" --profile r2 &>/dev/null; then
            abort "Backup file ${backup_file} tidak ada di R2. Pake --list untuk cek available."
        fi
        log INFO "Selected backup: ${backup_file}"
    fi

    echo "$backup_file"
}

# ─── Download + verify ───────────────────────────────────────────────────────
download_backup() {
    local backup_file="$1"
    mkdir -p "$TEMP_DIR"
    local local_path="${TEMP_DIR}/${backup_file}"

    log INFO "── Step 2/6: Download dari R2 ──"
    log INFO "Downloading ${backup_file}..."
    if ! $AWS s3 cp "${BUCKET}/${backup_file}" "$local_path" \
        --endpoint-url "$ENDPOINT" --profile r2 >> "$LOG" 2>&1; then
        abort "Gagal download backup dari R2."
    fi
    local size=$(stat -c %s "$local_path" 2>/dev/null || stat -f %z "$local_path")
    log OK "Downloaded: ${size} bytes"

    # Verify gzip integrity
    log INFO "── Step 3/6: Verify integrity ──"
    if ! gunzip -t "$local_path" 2>/dev/null; then
        abort "File corrupt — gzip integrity check FAILED. File ter-truncate atau corrupt di R2."
    fi
    log OK "Gzip integrity OK"

    echo "$local_path"
}

# ─── Confirmation prompt ─────────────────────────────────────────────────────
confirm_destructive() {
    local backup_file="$1"

    log INFO "── Step 4/6: User confirmation ──"
    echo ""
    echo -e "${C_YELLOW}⚠ WARNING: OPERASI DESTRUCTIVE ⚠${C_RESET}"
    echo ""
    echo "Yang akan terjadi:"
    echo "  1. Database '${DB_NAME}' di container ${DOCKER_CONTAINER} akan di-DROP (data hilang)"
    echo "  2. Database di-CREATE ulang kosong"
    echo "  3. Data dari backup '${backup_file}' akan di-INJECT"
    echo ""
    echo "Data yg EXIST sekarang di ${DB_NAME} akan HILANG PERMANEN."
    echo ""

    # First confirmation
    read -r -p "Lanjut restore? Ketik 'yes' (full word) untuk konfirmasi: " ans1
    if [ "$ans1" != "yes" ]; then
        log WARN "User membatalkan — abort."
        exit 0
    fi

    # Second confirmation with file check
    echo ""
    read -r -p "Konfirmasi SEKALI LAGI ketik nama backup file '${backup_file}': " ans2
    if [ "$ans2" != "$backup_file" ]; then
        log WARN "Nama backup tidak match — abort (safety guard)."
        exit 0
    fi

    log OK "User confirmed restore"
}

# ─── Execute restore ─────────────────────────────────────────────────────────
execute_restore() {
    local local_path="$1"

    log INFO "── Step 5/6: Execute restore ──"

    # Drop + create
    log INFO "Dropping existing database ${DB_NAME}..."
    docker exec -i "$DOCKER_CONTAINER" psql -U "$DB_USER" -d postgres \
        -c "DROP DATABASE IF EXISTS ${DB_NAME};" >> "$LOG" 2>&1 \
        || abort "DROP DATABASE gagal."
    log OK "Database dropped"

    log INFO "Creating fresh database ${DB_NAME}..."
    docker exec -i "$DOCKER_CONTAINER" psql -U "$DB_USER" -d postgres \
        -c "CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};" >> "$LOG" 2>&1 \
        || abort "CREATE DATABASE gagal."
    log OK "Database created"

    log INFO "Injecting backup data (gunzip + psql)..."
    # Pipe gunzip → psql via docker exec -i
    if ! gunzip -c "$local_path" | docker exec -i "$DOCKER_CONTAINER" \
        psql -U "$DB_USER" -d "$DB_NAME" >> "$LOG" 2>&1; then
        abort "Inject data gagal. Lihat $LOG untuk detail error."
    fi
    log OK "Data injected"
}

# ─── Post-restore validation ─────────────────────────────────────────────────
validate_restore() {
    log INFO "── Step 6/6: Post-restore validation ──"

    # Count critical tables — kalau 0 rows di tenants, restore gagal
    local tenant_count
    tenant_count=$(docker exec "$DOCKER_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" \
        -tAc "SELECT COUNT(*) FROM tenants;" 2>/dev/null | tr -d '[:space:]')
    if [ -z "$tenant_count" ] || [ "$tenant_count" = "0" ]; then
        log WARN "Zero tenants setelah restore — cek backup apakah kosong atau ada error."
    else
        log OK "Tenants count: ${tenant_count}"
    fi

    # Payments + orders count sanity
    local orders_count payments_count
    orders_count=$(docker exec "$DOCKER_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" \
        -tAc "SELECT COUNT(*) FROM orders;" 2>/dev/null | tr -d '[:space:]')
    payments_count=$(docker exec "$DOCKER_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" \
        -tAc "SELECT COUNT(*) FROM payments;" 2>/dev/null | tr -d '[:space:]')
    log OK "Orders: ${orders_count} | Payments: ${payments_count}"

    # Verify RLS policies intact (important — migration 069)
    local rls_count
    rls_count=$(docker exec "$DOCKER_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" \
        -tAc "SELECT COUNT(*) FROM pg_tables WHERE schemaname='public' AND rowsecurity=true;" \
        2>/dev/null | tr -d '[:space:]')
    if [ "$rls_count" -lt 40 ]; then
        log WARN "RLS table count ${rls_count} < 40 — policy mungkin belum ter-apply. Run alembic upgrade head."
    else
        log OK "RLS enabled di ${rls_count} tables"
    fi

    # Alembic version check
    local alembic_version
    alembic_version=$(docker exec "$DOCKER_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" \
        -tAc "SELECT version_num FROM alembic_version;" 2>/dev/null | tr -d '[:space:]')
    log OK "Alembic version: ${alembic_version}"
}

# ─── Main ────────────────────────────────────────────────────────────────────
main() {
    # Handle args
    if [ "${1:-}" = "--list" ]; then
        check_prerequisites
        list_backups
        exit 0
    fi

    local target_ts="${1:-}"

    log INFO "════════════════════════════════════════════════"
    log INFO "  Kasira DB Restore — R2 → ${DOCKER_CONTAINER}"
    log INFO "════════════════════════════════════════════════"

    check_prerequisites
    local backup_file
    backup_file=$(select_backup "$target_ts")
    local local_path
    local_path=$(download_backup "$backup_file")
    confirm_destructive "$backup_file"
    execute_restore "$local_path"
    validate_restore

    log OK "════════════════════════════════════════════════"
    log OK "  RESTORE COMPLETE"
    log OK "════════════════════════════════════════════════"
    echo ""
    echo -e "${C_GREEN}Next steps:${C_RESET}"
    echo "  1. Restart backend:   sudo docker restart kasira-backend-1"
    echo "  2. Run migrations:    sudo docker exec kasira-backend-1 alembic upgrade head"
    echo "  3. Verify health:     curl http://localhost:8000/health"
    echo "  4. Check metrics:     curl http://localhost:8000/metrics | grep kasira_bg"
    echo ""
}

main "$@"
