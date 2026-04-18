#!/bin/bash
# Kasira DB Backup → Cloudflare R2
# Runs via cron every 6 hours alongside local backup

set -e

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="/tmp/kasira_db_${TIMESTAMP}.sql.gz"
BUCKET="s3://kasira-production/backups"
ENDPOINT="https://63003661b5b663860000bcf6e9dc4955.r2.cloudflarestorage.com"
AWS="/usr/local/bin/aws"
export HOME="/root"
LOG="/var/log/kasira_backup_r2.log"

echo "[$(date)] Starting R2 backup..." >> "$LOG"

# 1. Dump DB
docker exec kasira-db-1 pg_dump -U kasira kasira_db | gzip > "$BACKUP_FILE"

# 2. Upload to R2
$AWS s3 cp "$BACKUP_FILE" "${BUCKET}/kasira_db_${TIMESTAMP}.sql.gz" \
    --endpoint-url "$ENDPOINT" \
    --profile r2 \
    >> "$LOG" 2>&1

# 3. Cleanup local temp
rm -f "$BACKUP_FILE"

# 4. Remove R2 backups older than 14 days
CUTOFF=$(date -d '14 days ago' +%Y%m%d)
$AWS s3 ls "${BUCKET}/" --endpoint-url "$ENDPOINT" --profile r2 2>/dev/null | while read -r line; do
    FILE=$(echo "$line" | awk '{print $4}')
    FILE_DATE=$(echo "$FILE" | grep -oP '\d{8}' | head -1)
    if [ -n "$FILE_DATE" ] && [ "$FILE_DATE" -lt "$CUTOFF" ] 2>/dev/null; then
        $AWS s3 rm "${BUCKET}/${FILE}" --endpoint-url "$ENDPOINT" --profile r2 >> "$LOG" 2>&1
        echo "[$(date)] Deleted old backup: $FILE" >> "$LOG"
    fi
done

echo "[$(date)] R2 backup done: kasira_db_${TIMESTAMP}.sql.gz" >> "$LOG"
