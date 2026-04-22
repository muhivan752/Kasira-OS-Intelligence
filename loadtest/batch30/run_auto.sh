#!/bin/bash
# Kasira Batch #30 Tahap 2 — AUTO-PILOT variant
# Dipake untuk `at` scheduler — TIDAK ada confirmation prompt.
# Include: JWT refresh (Redis OTP inject fallback) + run k6 + cleanup SQL otomatis.
#
# Run manual: bash /var/www/kasira/loadtest/batch30/run_auto.sh
# Run via at: echo "bash /var/www/kasira/loadtest/batch30/run_auto.sh" | at 18:55

set -o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd || echo "/var/www/kasira/loadtest/batch30")"
LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR"

TIMESTAMP=$(date +%Y%m%d-%H%M%S)
LOG_FILE="$LOG_DIR/auto-$TIMESTAMP.log"
SUMMARY_FILE="$LOG_DIR/summary-$TIMESTAMP.json"

exec > >(tee -a "$LOG_FILE") 2>&1

echo "══════════════════════════════════════════════════════════════════"
echo "🚀 KASIRA BATCH #30 TAHAP 2 — AUTO-PILOT LOAD HAMMER"
echo "══════════════════════════════════════════════════════════════════"
echo "Start:     $(date -u '+%Y-%m-%d %H:%M:%S UTC') / $(TZ=Asia/Jakarta date '+%H:%M WIB')"
echo "Log:       $LOG_FILE"
echo "Summary:   $SUMMARY_FILE"
echo ""

# Ensure PATH includes k6 + docker + standard
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$PATH"

# ── Step 1: Source config ───────────────────────────────────────────────
source "$SCRIPT_DIR/run_config.sh"
echo ""

# ── Step 2: JWT pre-flight — auto-refresh kalau expired ─────────────────
echo "🔍 Step 2: JWT pre-flight check"
HTTP_CODE=$(curl -sS -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant-ID: $TENANT_ID" \
  "$BASE_URL/auth/me" 2>/dev/null || echo "000")

if [ "$HTTP_CODE" != "200" ]; then
  echo "⚠️  JWT rejected (HTTP $HTTP_CODE). Refreshing via Redis OTP inject..."
  sudo docker exec kasira-redis-1 redis-cli SET "otp:6289999990001" "123456" EX 3600 >/dev/null
  NEW_TOKEN=$(sudo docker exec kasira-backend-1 python -c "
import httpx, sys
try:
    r = httpx.post('http://localhost:8000/api/v1/auth/otp/verify',
                   json={'phone':'6289999990001','otp':'123456'}, timeout=10)
    print(r.json()['data']['access_token'])
except Exception as e:
    print(f'ERR: {e}', file=sys.stderr); sys.exit(1)
" 2>&1)
  if [[ "$NEW_TOKEN" == ERR:* ]] || [ -z "$NEW_TOKEN" ]; then
    echo "❌ JWT refresh FAILED: $NEW_TOKEN"
    exit 2
  fi
  export TOKEN="$NEW_TOKEN"
  # Re-verify
  HTTP_CODE=$(curl -sS -o /dev/null -w "%{http_code}" \
    -H "Authorization: Bearer $TOKEN" \
    -H "X-Tenant-ID: $TENANT_ID" \
    "$BASE_URL/auth/me")
  if [ "$HTTP_CODE" != "200" ]; then
    echo "❌ JWT still invalid post-refresh (HTTP $HTTP_CODE). Abort."
    exit 2
  fi
  echo "✅ JWT refreshed OK"
else
  echo "✅ JWT valid (HTTP 200)"
fi

# ── Step 3: Backend health ──────────────────────────────────────────────
echo ""
echo "🔍 Step 3: Backend health check"
HEALTH=$(curl -sS http://localhost:8000/health 2>&1)
echo "   $HEALTH"
if ! echo "$HEALTH" | grep -q '"status": "ok"'; then
  echo "❌ Backend unhealthy. Abort."
  exit 3
fi
echo "✅ Backend OK"

# ── Step 4: Run k6 hammer ───────────────────────────────────────────────
echo ""
echo "🔥 Step 4: k6 load hammer — 12min ramp 10→25→50→100 VUs"
echo "─────────────────────────────────────────────────────────────────"

k6 run \
  --env TOKEN="$TOKEN" \
  --env PRODUCT_IDS="$PRODUCT_IDS" \
  --env TENANT_ID="$TENANT_ID" \
  --env OUTLET_ID="$OUTLET_ID" \
  --env BASE_URL="$BASE_URL" \
  --summary-export="$SUMMARY_FILE" \
  "$SCRIPT_DIR/k6_hammer.js"

K6_EXIT=$?
echo "─────────────────────────────────────────────────────────────────"
echo "k6 exit code: $K6_EXIT (0=all thresholds pass, 99=threshold fail)"
echo ""

# ── Step 5: Cleanup (run regardless k6 pass/fail) ───────────────────────
echo "🧹 Step 5: Cleanup — delete batch30-load-* orders + sync_idempotency + events"
echo "─────────────────────────────────────────────────────────────────"

CLEANUP_OUT=$(sudo docker exec -i kasira-db-1 psql -U kasira -d kasira_db < "$SCRIPT_DIR/cleanup.sql" 2>&1)
echo "$CLEANUP_OUT"
echo "─────────────────────────────────────────────────────────────────"

# ── Step 6: Post-test summary ───────────────────────────────────────────
echo ""
echo "📊 Step 6: Final summary"
echo ""
echo "End:       $(date -u '+%Y-%m-%d %H:%M:%S UTC') / $(TZ=Asia/Jakarta date '+%H:%M WIB')"
echo "k6 exit:   $K6_EXIT"

if [ -f "$SUMMARY_FILE" ]; then
  echo "Summary JSON exported: $SUMMARY_FILE"
  # Extract key metrics
  echo ""
  echo "Quick metrics (pakai jq untuk detail):"
  echo "   jq '.metrics.http_req_duration.values' $SUMMARY_FILE"
  echo "   jq '.metrics.http_req_failed.values' $SUMMARY_FILE"
  echo "   jq '.metrics.orders_created.values' $SUMMARY_FILE"
fi

echo ""
echo "Full log: $LOG_FILE"
echo "══════════════════════════════════════════════════════════════════"

exit $K6_EXIT
