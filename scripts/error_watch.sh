#!/usr/bin/env bash
# Pengawas error → Telegram. Cron root tiap 15 menit, hidup tanpa terminal.
#
# Menggantikan janitor_watch.sh: sumbernya sama (log container), cuma
# cakupannya sekarang SEMUA error, bukan cuma janitor.
#
# Yang diawasi:
#   1. backend  — semua baris "level": "ERROR" (termasuk janitor backend.tasks.*
#                 dan 500 tak tertangani dari backend.main)
#   2. web      — error runtime Next.js di container frontend
#   3. nginx    — respons 5xx (yang benar-benar sampai ke pengunjung)
#
# Yang SENGAJA diabaikan (bising, bukan masalah):
#   - "Exception terminating connection" dari pool SQLAlchemy: muncul tiap
#     backend restart, koneksi lama diputus. Normal.
#   - "Failed to find Server Action" di Next: browser yang masih memegang
#     bundel versi lama sesudah deploy. Hilang sendiri begitu halaman dimuat
#     ulang. 74 kejadian sehari waktu diukur, semuanya tidak berbahaya.
#   - 502 pada /health saat restart: healthcheck_ping.sh yang mengurus itu,
#     dengan throttle transisi sendiri.
#
# Throttle: per sidik jari (sumber + pesan) selama STATE_TTL_HOURS. Masalah
# yang berulang tiap menit jadi satu pesan, tapi yang belum dibereskan
# ditagih lagi sesudah jendela itu lewat.
set -uo pipefail

CONFIG_FILE="${CONFIG_FILE:-/etc/kasira/healthcheck.env}"
BACKEND="${BACKEND:-kasira-backend-1}"
FRONTEND="${FRONTEND:-kasira-frontend-1}"
NGINX_LOG="${NGINX_LOG:-/var/log/nginx/access.log}"
WINDOW="${WINDOW:-16m}"
STATE_FILE="${STATE_FILE:-/var/run/kasira-error-watch.state}"
STATE_TTL_HOURS="${STATE_TTL_HOURS:-6}"
MAX_ITEMS="${MAX_ITEMS:-6}"
TG_TIMEOUT="${TG_TIMEOUT:-8}"

[[ -f "$CONFIG_FILE" ]] && source "$CONFIG_FILE"
if [[ -z "${TG_BOT_TOKEN:-}" ]] || [[ -z "${TG_CHAT_ID:-}" ]]; then
  echo "$(date -Is) SKIP: TG_BOT_TOKEN/TG_CHAT_ID belum diisi di $CONFIG_FILE"; exit 0
fi

ABAIKAN='Exception terminating connection|Failed to find Server Action|ExperimentalWarning|DeprecationWarning'

kirim() {
  curl -sS --max-time "$TG_TIMEOUT" \
    -d "chat_id=${TG_CHAT_ID}" -d "disable_web_page_preview=true" \
    --data-urlencode "text=$1" \
    "https://api.telegram.org/bot${TG_BOT_TOKEN}/sendMessage" >/dev/null
}

TMPI="$(mktemp)"   # daftar "sumber<TAB>pesan"

# 1. Backend: baris ERROR terstruktur
docker logs --since "$WINDOW" "$BACKEND" 2>&1 \
  | grep '"level": "ERROR"' \
  | grep -Ev "$ABAIKAN" \
  | python3 -c '
import sys, json
for ln in sys.stdin:
    try:
        d = json.loads(ln.strip())
    except Exception:
        print("backend\t" + ln.strip()[:150]); continue
    lg = d.get("logger", "?")
    src = "janitor" if lg.startswith("backend.tasks.") else "backend"
    nama = lg.replace("backend.tasks.", "").replace("backend.", "")
    print(f"{src}\t{nama}: " + str(d.get("message",""))[:170])
' >> "$TMPI" 2>/dev/null || true

# 2. Frontend Next.js
docker logs --since "$WINDOW" "$FRONTEND" 2>&1 \
  | grep -iE '(^| )(⨯|Error:|UnhandledPromiseRejection|TypeError)' \
  | grep -Ev "$ABAIKAN" \
  | sed 's/^[[:space:]]*//' | cut -c1-170 \
  | while IFS= read -r l; do printf 'web\t%s\n' "$l"; done >> "$TMPI" || true

# 3. nginx 5xx (kecuali /health, sudah diurus healthcheck_ping.sh)
if [[ -r "$NGINX_LOG" ]]; then
  SEJAK=$(date -d "-16 min" '+%d/%b/%Y:%H:%M' 2>/dev/null || echo "")
  awk -v sejak="$SEJAK" '$9 ~ /^(500|502|503|504)$/ && $7 !~ /^\/health/ {print $9, $7}' "$NGINX_LOG" 2>/dev/null \
    | sort | uniq -c | sort -rn | head -5 \
    | while read -r n kode jalur; do printf 'nginx\t%s x%s %s\n' "$kode" "$n" "$jalur"; done >> "$TMPI" || true
fi

touch "$STATE_FILE" 2>/dev/null || STATE_FILE=/tmp/kasira-error-watch.state
touch "$STATE_FILE"
NOW=$(date +%s); TTL=$(( STATE_TTL_HOURS * 3600 ))

# Buang sidik jari kedaluwarsa supaya masalah yang masih ada ditagih lagi
TMPS="$(mktemp)"
while IFS='|' read -r ts fp; do
  [[ -z "${ts:-}" ]] && continue
  (( NOW - ts < TTL )) && echo "${ts}|${fp}" >> "$TMPS"
done < "$STATE_FILE"
mv "$TMPS" "$STATE_FILE"

BARU=0; TOTAL=0; PESAN="⚠️ Error di Selaris"
while IFS=$'\t' read -r sumber pesan; do
  [[ -z "${pesan:-}" ]] && continue
  TOTAL=$((TOTAL+1))
  FP="$(printf '%s|%s' "$sumber" "$pesan" | md5sum | cut -c1-16)"
  grep -q "|${FP}\$" "$STATE_FILE" && continue
  echo "${NOW}|${FP}" >> "$STATE_FILE"
  BARU=$((BARU+1))
  PESAN="${PESAN}"$'\n\n'"[${sumber}] ${pesan}"
  (( BARU >= MAX_ITEMS )) && break
done < "$TMPI"
rm -f "$TMPI"

if (( BARU > 0 )); then
  PESAN="${PESAN}"$'\n\n'"docker logs ${BACKEND} --since 30m | grep ERROR"
  kirim "$PESAN"
  echo "$(date -Is) ALERT_SENT baru=${BARU} total_terlihat=${TOTAL}"
else
  echo "$(date -Is) OK terlihat=${TOTAL}, semua sudah dikabari (throttle ${STATE_TTL_HOURS}j)"
fi
