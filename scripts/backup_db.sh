#!/bin/bash
# Kasira DB Backup — pg_dump dari Docker container
# Simpan 7 hari terakhir, hapus yang lebih lama

BACKUP_DIR="/var/backups/kasira"
CONTAINER="kasira-db-1"
DB_NAME="kasira_db"
DB_USER="kasira"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/kasira_$TIMESTAMP.sql.gz"
KEEP_DAYS=7
LOG_FILE="/var/log/kasira_backup.log"

mkdir -p "$BACKUP_DIR"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Memulai backup..." >> "$LOG_FILE"

docker exec "$CONTAINER" pg_dump -U "$DB_USER" "$DB_NAME" | gzip > "$BACKUP_FILE"

if [ $? -eq 0 ]; then
    SIZE=$(du -sh "$BACKUP_FILE" | cut -f1)
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Backup berhasil: $BACKUP_FILE ($SIZE)" >> "$LOG_FILE"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] BACKUP GAGAL!" >> "$LOG_FILE"
    exit 1
fi

# Hapus backup lebih dari KEEP_DAYS hari
find "$BACKUP_DIR" -name "kasira_*.sql.gz" -mtime +$KEEP_DAYS -delete
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Cleanup selesai. File tersisa:" >> "$LOG_FILE"
ls -lh "$BACKUP_DIR" >> "$LOG_FILE"
