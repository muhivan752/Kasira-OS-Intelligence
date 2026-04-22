#!/bin/bash
# Kasira Batch #30 Tahap 2 — Load Hammer runner
# Usage: ./loadtest/batch30/run.sh
#
# JWT expires 2026-04-27 13:57 UTC. Refresh via:
#   sudo docker exec kasira-redis-1 redis-cli SET "otp:6289999990001" "123456" EX 3600
#   NEW_TOKEN=$(sudo docker exec kasira-backend-1 python -c "import httpx; r=httpx.post('http://localhost:8000/api/v1/auth/otp/verify', json={'phone':'6289999990001','otp':'123456'}, timeout=10); print(r.json()['data']['access_token'])")
#   # Update TOKEN line di run_config.sh

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/run_config.sh"

# Pre-flight: verify JWT still valid
echo "🔍 Pre-flight JWT check..."
HTTP_CODE=$(curl -sS -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $TOKEN" -H "X-Tenant-ID: $TENANT_ID" "$BASE_URL/auth/me")
if [ "$HTTP_CODE" != "200" ]; then
  echo "❌ JWT rejected (HTTP $HTTP_CODE). Refresh token via instructions di run_config.sh"
  exit 1
fi
echo "✅ JWT valid"

# Pre-flight: Grafana / monitoring reminder
echo ""
echo "⚠️  PRE-FLIGHT CHECKLIST:"
echo "   - Current WIB time: $(TZ=Asia/Jakarta date '+%Y-%m-%d %H:%M:%S')"
echo "   - Off-peak recommended: 02:00 - 06:00 WIB"
echo "   - Duration: ~12 menit (ramp 10→25→50→100 VUs)"
echo "   - Expected orders created: ~2000-5000 (batch30-load-*)"
echo ""
read -p "Lanjut? (y/N) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
  echo "Aborted."
  exit 0
fi

# Run
mkdir -p "$SCRIPT_DIR/logs"
LOG_FILE="$SCRIPT_DIR/logs/run-$(date +%Y%m%d-%H%M%S).log"
echo ""
echo "🚀 Launching k6 — log: $LOG_FILE"
echo ""

k6 run \
  --env TOKEN="$TOKEN" \
  --env PRODUCT_IDS="$PRODUCT_IDS" \
  --env TENANT_ID="$TENANT_ID" \
  --env OUTLET_ID="$OUTLET_ID" \
  --env BASE_URL="$BASE_URL" \
  --summary-export="$SCRIPT_DIR/logs/summary-$(date +%Y%m%d-%H%M%S).json" \
  "$SCRIPT_DIR/k6_hammer.js" 2>&1 | tee "$LOG_FILE"

echo ""
echo "✅ k6 selesai. Log: $LOG_FILE"
echo ""
echo "📋 Next step — CLEANUP:"
echo "   sudo docker exec -i kasira-db-1 psql -U kasira -d kasira_db < $SCRIPT_DIR/cleanup.sql"
