#!/usr/bin/env bash
# Pengawas janitor → alert Telegram. Jalan lewat cron root tiap 15 menit,
# jadi hidup terus tanpa terminal siapa pun terbuka.
#
# Kenapa ada: 5 Sep 2026, sesudah semua janitor dikasih kunci satu-worker,
# `shift_cutoff` error tiap siklus (KeyError: 'failed') karena bentuk hasil
# jalur "dilewati kunci" beda dari jalur normal. Itu cuma ketahuan karena
# kebetulan ada yang membaca log. Janitor rusak itu SENYAP: uang COD nggak
# dicatat, stok nggak balik, invoice nggak terbit, dan nggak ada yang tahu
# sampai ada yang mengeluh berhari-hari kemudian.
#
# Cara kerja: baca log container backend sejak tick terakhir, cari baris ERROR
# dari logger `backend.tasks.*`, kirim ringkasannya. Throttle per jenis error
# (sidik jari = nama janitor + baris pertama pesan) supaya error yang berulang
# tiap siklus nggak jadi 96 pesan sehari.
#
# State: /var/run/kasira-janitor-watch.state  (sidik jari yang sudah dikabari)
set -uo pipefail

CONFIG_FILE="${CONFIG_FILE:-/etc/kasira/healthcheck.env}"
CONTAINER="${CONTAINER:-kasira-backend-1}"
WINDOW="${WINDOW:-16m}"            # sedikit lebih lebar dari interval cron (15m)
STATE_FILE="${STATE_FILE:-/var/run/kasira-janitor-watch.state}"
STATE_TTL_HOURS="${STATE_TTL_HOURS:-6}"   # kabari lagi kalau masih rusak sesudah 6 jam
TG_TIMEOUT="${TG_TIMEOUT:-8}"

[[ -f "$CONFIG_FILE" ]] && source "$CONFIG_FILE"
if [[ -z "${TG_BOT_TOKEN:-}" ]] || [[ -z "${TG_CHAT_ID:-}" ]]; then
  echo "$(date -Is) SKIP: TG_BOT_TOKEN/TG_CHAT_ID belum diisi di $CONFIG_FILE"
  exit 0
fi

kirim() {
  curl -sS --max-time "$TG_TIMEOUT" \
    -d "chat_id=${TG_CHAT_ID}" -d "disable_web_page_preview=true" \
    --data-urlencode "text=$1" \
    "https://api.telegram.org/bot${TG_BOT_TOKEN}/sendMessage" >/dev/null
}

LOG="$(docker logs --since "$WINDOW" "$CONTAINER" 2>&1 || true)"
if [[ -z "$LOG" ]]; then
  echo "$(date -Is) SKIP: log container kosong / container tidak jalan"
  exit 0
fi

# Baris ERROR dari janitor. Format log JSON: "logger": "backend.tasks.<nama>"
ERRORS="$(printf '%s\n' "$LOG" | grep -E '"level": "ERROR"' | grep -E '"logger": "backend\.(tasks|services\.platform_intelligence)' || true)"

touch "$STATE_FILE" 2>/dev/null || STATE_FILE=/tmp/kasira-janitor-watch.state
touch "$STATE_FILE"
NOW_EPOCH=$(date +%s)
TTL=$(( STATE_TTL_HOURS * 3600 ))

# Buang sidik jari yang sudah kedaluwarsa, supaya masalah yang masih ada
# dikabari lagi nanti (bukan diam selamanya).
TMP="$(mktemp)"
while IFS='|' read -r ts fp; do
  [[ -z "${ts:-}" ]] && continue
  if (( NOW_EPOCH - ts < TTL )); then echo "${ts}|${fp}" >> "$TMP"; fi
done < "$STATE_FILE"
mv "$TMP" "$STATE_FILE"

BARU=0
PESAN="🧹 Janitor bermasalah"
while IFS= read -r line; do
  [[ -z "$line" ]] && continue
  NAMA="$(printf '%s' "$line" | grep -oP '"logger": "backend\.tasks\.\K[^"]+' | head -1)"
  [[ -z "$NAMA" ]] && NAMA="$(printf '%s' "$line" | grep -oP '"logger": "\K[^"]+' | head -1)"
  PESAN_ERR="$(printf '%s' "$line" | grep -oP '"message": "\K[^"]{0,160}' | head -1)"
  FP="$(printf '%s|%s' "$NAMA" "$PESAN_ERR" | md5sum | cut -c1-16)"
  if grep -q "|${FP}\$" "$STATE_FILE"; then continue; fi
  echo "${NOW_EPOCH}|${FP}" >> "$STATE_FILE"
  BARU=$((BARU+1))
  PESAN="${PESAN}"$'\n\n'"• ${NAMA}"$'\n'"  ${PESAN_ERR}"
  [[ $BARU -ge 5 ]] && break
done <<< "$ERRORS"

if (( BARU > 0 )); then
  PESAN="${PESAN}"$'\n\n'"Cek: docker logs ${CONTAINER} --since 30m | grep ERROR"
  kirim "$PESAN"
  echo "$(date -Is) ALERT_SENT janitor_errors=${BARU}"
  exit 0
fi

DIULANG="$(printf '%s\n' "$ERRORS" | grep -c . || true)"
if (( DIULANG > 0 )); then
  echo "$(date -Is) OK ${DIULANG} baris error tapi semuanya sudah dikabari (throttle ${STATE_TTL_HOURS}h)"
else
  echo "$(date -Is) OK tidak ada error janitor dalam ${WINDOW}"
fi
