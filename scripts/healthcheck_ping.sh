#!/usr/bin/env bash
# Kasira backend health monitor → Telegram alert.
# Run via cron tiap 2 menit. State-change throttle: alert sekali per transition
# (down → up → down), bukan spam tiap tick saat down sustained.
#
# Setup:
#   1. Buat Telegram bot via @BotFather (lihat README di chat session).
#      Dapat TG_BOT_TOKEN format "123456789:ABCdef..."
#   2. Kirim pesan apa aja ke bot via Telegram app.
#   3. Get TG_CHAT_ID via:
#        curl https://api.telegram.org/bot<TOKEN>/getUpdates
#      Cari "chat":{"id":<NUMBER>...} dalam response.
#   4. Tulis ke /etc/kasira/healthcheck.env:
#        TG_BOT_TOKEN=123456789:ABCdef...
#        TG_CHAT_ID=<NUMBER>
#   5. chmod 600 /etc/kasira/healthcheck.env (token = secret)
#   6. Add cron root:
#        */2 * * * * /var/www/kasira/scripts/healthcheck_ping.sh \
#          >> /var/log/kasira-healthcheck.log 2>&1
#
# Behavior:
#   - /health unreachable / status non-ok / db non-ok / bg_tasks non-healthy
#     → state=DOWN
#   - State berubah dari UP → DOWN: kirim alert "🚨 Backend DOWN: <reason>"
#   - State tetap DOWN: skip (cegah spam)
#   - State berubah dari DOWN → UP: kirim alert "✅ Backend recovered"
#   - State tetap UP: skip silent
#
# State file: /var/run/kasira-healthcheck.state (UP / DOWN / unset=unknown)

set -uo pipefail

CONFIG_FILE="${CONFIG_FILE:-/etc/kasira/healthcheck.env}"
HEALTH_URL="${HEALTH_URL:-http://localhost:8000/health}"
HEALTH_TIMEOUT="${HEALTH_TIMEOUT:-10}"
TG_TIMEOUT="${TG_TIMEOUT:-8}"
STATE_FILE="${STATE_FILE:-/var/run/kasira-healthcheck.state}"

# Load TG_BOT_TOKEN + TG_CHAT_ID dari config file
if [[ -f "$CONFIG_FILE" ]]; then
  # shellcheck disable=SC1090
  source "$CONFIG_FILE"
fi

if [[ -z "${TG_BOT_TOKEN:-}" ]] || [[ -z "${TG_CHAT_ID:-}" ]]; then
  echo "[$(date -Iseconds)] FATAL: TG_BOT_TOKEN / TG_CHAT_ID not set (check $CONFIG_FILE)" >&2
  exit 2
fi

case "$TG_BOT_TOKEN" in
  *PLACEHOLDER* | *YOUR_TOKEN* | *EDIT_INI*)
    echo "[$(date -Iseconds)] FATAL: TG_BOT_TOKEN masih placeholder — edit $CONFIG_FILE" >&2
    exit 2
    ;;
esac

send_telegram() {
  local msg="$1"
  curl -sf -m "$TG_TIMEOUT" \
    "https://api.telegram.org/bot${TG_BOT_TOKEN}/sendMessage" \
    --data-urlencode "chat_id=${TG_CHAT_ID}" \
    --data-urlencode "text=${msg}" \
    --data "parse_mode=HTML" \
    --data "disable_web_page_preview=true" \
    > /dev/null 2>&1
}

# Read previous state (default to UP — first run gak alert palsu)
PREV_STATE="UP"
if [[ -f "$STATE_FILE" ]]; then
  PREV_STATE=$(cat "$STATE_FILE" 2>/dev/null || echo "UP")
fi

# Step 1: Fetch /health
HTTP_RESP=$(curl -sf -m "$HEALTH_TIMEOUT" "$HEALTH_URL" 2>/dev/null)
CURL_EXIT=$?

if [[ $CURL_EXIT -ne 0 ]] || [[ -z "$HTTP_RESP" ]]; then
  REASON="Backend tidak bisa di-reach (curl exit $CURL_EXIT)"
  CURRENT_STATE="DOWN"
else
  # Step 2: Parse JSON
  PARSED=$(echo "$HTTP_RESP" | python3 -c '
import sys, json
try:
    d = json.load(sys.stdin)
    ok = (
        d.get("status") == "ok"
        and d.get("db") == "ok"
        and d.get("bg_tasks") == "healthy"
    )
    dead = d.get("bg_tasks_dead", []) or []
    print("OK" if ok else "FAIL")
    print("status=" + str(d.get("status")) + " db=" + str(d.get("db")) + " bg=" + str(d.get("bg_tasks")))
    print(",".join(str(x) for x in dead))
except Exception as e:
    print("PARSE_ERR")
    print(str(e))
    print("")
' 2>/dev/null)

  STATUS=$(echo "$PARSED" | sed -n '1p')
  DIAG=$(echo "$PARSED" | sed -n '2p')
  DEAD=$(echo "$PARSED" | sed -n '3p')

  if [[ "$STATUS" == "OK" ]]; then
    CURRENT_STATE="UP"
    REASON=""
  else
    CURRENT_STATE="DOWN"
    REASON="${STATUS} | ${DIAG}${DEAD:+ | dead_tasks=$DEAD}"
  fi
fi

# Step 3: State transition logic
HOST=$(hostname)
TS=$(date -Iseconds)

if [[ "$PREV_STATE" == "UP" && "$CURRENT_STATE" == "DOWN" ]]; then
  # UP → DOWN: kirim alert
  MSG="🚨 <b>Kasira Backend DOWN</b>%0A%0A<b>Host:</b> ${HOST}%0A<b>Time:</b> ${TS}%0A<b>Detail:</b> ${REASON}"
  if send_telegram "$MSG"; then
    echo "[${TS}] ALERT_SENT down: $REASON"
  else
    echo "[${TS}] WARN: down alert send failed (Telegram unreachable)" >&2
  fi
elif [[ "$PREV_STATE" == "DOWN" && "$CURRENT_STATE" == "UP" ]]; then
  # DOWN → UP: kirim recovery
  MSG="✅ <b>Kasira Backend recovered</b>%0A%0A<b>Host:</b> ${HOST}%0A<b>Time:</b> ${TS}%0AService back to healthy."
  if send_telegram "$MSG"; then
    echo "[${TS}] ALERT_SENT recovered"
  else
    echo "[${TS}] WARN: recovery alert send failed" >&2
  fi
elif [[ "$CURRENT_STATE" == "DOWN" ]]; then
  # Still DOWN — silent, log only every tick
  echo "[${TS}] STILL_DOWN: $REASON"
else
  # Still UP — silent, no log spam
  :
fi

# Step 4: Persist current state
echo -n "$CURRENT_STATE" > "$STATE_FILE" 2>/dev/null || \
  echo "[${TS}] WARN: gagal write state file $STATE_FILE" >&2

# Exit clean — cron continues regardless
exit 0
