#!/usr/bin/env bash
# ============================================================================
# E2E smoke test — STOK (Finding 1 server-authoritative + Finding 3 idempotency
# + recipe mode deduct/restore). Dua mode: simple (products.stock_qty) & recipe
# (porsi dari ingredient).
#
# Usage: bash scripts/test_stock_e2e.sh [SIMPLE_PHONE] [RECIPE_PHONE]
#   default SIMPLE = 6289999990003 (_loadtest_tenant, Pro simple)
#   default RECIPE = 6282380068100 (kopi sadis, Pro recipe)
# Butuh container kasira-backend-1 + kasira-redis-1 jalan.
# ============================================================================
set -uo pipefail
SIMPLE_PHONE="${1:-6289999990003}"
RECIPE_PHONE="${2:-6282380068100}"
BASE="http://localhost:8000/api/v1"
PASS=0; FAIL=0; SKIP=0
TOKEN=""; TENANT=""; OUTLET=""; BRAND=""

say()  { printf '\n\033[1m▸ %s\033[0m\n' "$*"; }
ok()   { printf '  \033[32m✓ PASS\033[0m %s\n' "$*"; PASS=$((PASS+1)); }
bad()  { printf '  \033[31m✗ FAIL\033[0m %s\n' "$*"; FAIL=$((FAIL+1)); }
skip() { printf '  \033[33m∼ SKIP\033[0m %s\n' "$*"; SKIP=$((SKIP+1)); }
chk()  { if [ "$2" = "$3" ]; then ok "$1 (=$3)"; else bad "$1 (harap $2, dapat $3)"; fi; }
chklt(){ if [ "$2" -lt "$3" ]; then ok "$1 ($2 < $3)"; else bad "$1 (harap $2 < $3)"; fi; }
field(){ python3 -c "import sys,json;d=json.load(sys.stdin);print($1)" 2>/dev/null; }
api()  { local m=$1 p=$2 d=${3:-}; curl -s -X "$m" "$BASE$p" -H "Authorization: Bearer $TOKEN" -H "X-Tenant-ID: $TENANT" -H "Content-Type: application/json" ${d:+-d "$d"}; }

# ── login(phone): set TOKEN/TENANT/OUTLET; return 1 kalau gagal ─────────────
# Token via OTP-inject; tenant/outlet dari DB langsung (reliable semua tenant).
login() {
  local phone=$1
  sudo docker exec kasira-redis-1 redis-cli SET "otp:$phone" "123456" EX 3600 >/dev/null
  TOKEN=$(sudo docker exec kasira-backend-1 python -c "import httpx;r=httpx.post('http://localhost:8000/api/v1/auth/otp/verify',json={'phone':'$phone','otp':'123456'},timeout=10);print(r.json().get('data',{}).get('access_token',''))" 2>/dev/null)
  [ -z "$TOKEN" ] && return 1
  local row; row=$(sudo docker exec kasira-db-1 psql -U kasira -d kasira_db -t -A -F'|' -c \
    "SELECT u.tenant_id, o.id, o.brand_id FROM users u JOIN outlets o ON o.tenant_id=u.tenant_id AND o.deleted_at IS NULL WHERE u.phone='$phone' AND u.deleted_at IS NULL ORDER BY o.created_at LIMIT 1;" 2>/dev/null)
  TENANT=$(echo "$row" | cut -d'|' -f1 | tr -d ' ')
  OUTLET=$(echo "$row" | cut -d'|' -f2 | tr -d ' ')
  BRAND=$(echo "$row" | cut -d'|' -f3 | tr -d ' ')
  [ -n "$TENANT" ] && [ -n "$OUTLET" ]
}

# stok/porsi produk PID di outlet aktif
getstock() { api GET "/products/?outlet_id=$OUTLET" | python3 -c "
import sys,json
for p in json.load(sys.stdin).get('data',[]):
    if p['id']=='$1': print(int(p.get('stock',0)));break"; }

# ════════════════════════════ SIMPLE MODE ════════════════════════════
say "═══ SIMPLE MODE (phone $SIMPLE_PHONE) ═══"
if ! login "$SIMPLE_PHONE"; then bad "login simple gagal — skip"; else
  ok "login ok (tenant ${TENANT:0:8} outlet ${OUTLET:0:8})"
  read -r PID PNAME < <(api GET "/products/?outlet_id=$OUTLET" | python3 -c "
import sys,json
for p in json.load(sys.stdin).get('data',[]):
    if p.get('stock_enabled') and (p.get('stock') or 0)>=5: print(p['id'],p.get('name','?').replace(' ','_'));break")
  if [ -z "${PID:-}" ]; then bad "gak ada produk stock_enabled stok>=5"; else
    ok "produk: $PNAME (${PID:0:8})"
    S0=$(getstock "$PID"); QTY=2
    O=$(api POST "/orders/" "{\"outlet_id\":\"$OUTLET\",\"order_type\":\"takeaway\",\"subtotal\":20000,\"total_amount\":20000,\"tax_amount\":0,\"service_charge_amount\":0,\"discount_amount\":0,\"items\":[{\"product_id\":\"$PID\",\"quantity\":$QTY,\"unit_price\":10000,\"total_price\":20000,\"discount_amount\":0}]}")
    OID=$(echo "$O" | field "d['data']['id']"); ORV=$(echo "$O" | field "d['data'].get('row_version',0)")
    [ -z "${OID:-}" ] && bad "order gagal: $(echo "$O"|head -c150)" || ok "order ${OID:0:8}"
    say "S1 Order → deduct";        chk "stok turun $QTY" "$((S0-QTY))" "$(getstock "$PID")"
    api PUT "/orders/$OID/status" "{\"status\":\"cancelled\",\"row_version\":$ORV}" >/dev/null
    say "S2 Cancel → restore";      chk "stok balik" "$S0" "$(getstock "$PID")"
    api PUT "/orders/$OID/status" "{\"status\":\"cancelled\",\"row_version\":$((ORV+1))}" >/dev/null
    say "S3 Cancel 2× → idempotent";chk "gak inflate" "$S0" "$(getstock "$PID")"
    api POST "/products/$PID/restock" "{\"outlet_id\":\"$OUTLET\",\"quantity\":5,\"notes\":\"e2e\"}" >/dev/null
    say "S4 Restock → naik";        chk "stok +5" "$((S0+5))" "$(getstock "$PID")"
  fi
fi

# ════════════════════════════ RECIPE MODE ════════════════════════════
say "═══ RECIPE MODE (phone $RECIPE_PHONE) ═══"
if ! login "$RECIPE_PHONE"; then skip "login recipe gagal"; else
  ok "login ok (tenant ${TENANT:0:8} outlet ${OUTLET:0:8})"
  # Self-provision: restock semua bahan biar produk recipe punya porsi
  ING_IDS=$(api GET "/ingredients/?brand_id=$BRAND&outlet_id=$OUTLET" | field "' '.join(i['id'] for i in d.get('data',[]))")
  if [ -z "$ING_IDS" ]; then skip "recipe: gak ada ingredient (belum diset) — recipe deduct dicover test_pro_e2e.sh"; else
    for iid in $ING_IDS; do api POST "/ingredients/$iid/restock" "{\"outlet_id\":\"$OUTLET\",\"quantity\":100000,\"notes\":\"e2e provision\"}" >/dev/null; done
    ok "restock $(echo $ING_IDS | wc -w) bahan (100rb tiap)"
  fi
  read -r RPID RPNAME < <(api GET "/products/?outlet_id=$OUTLET" | python3 -c "
import sys,json
for p in json.load(sys.stdin).get('data',[]):
    if p.get('stock_enabled') and (p.get('stock') or 0)>=3: print(p['id'],p.get('name','?').replace(' ','_'));break")
  if [ -z "${RPID:-}" ]; then skip "recipe: produk masih porsi<3 (resep belum lengkap / unit mismatch)"; else
    ok "produk recipe: $RPNAME (${RPID:0:8})"
    P0=$(getstock "$RPID"); echo "  porsi awal: $P0"
    O=$(api POST "/orders/" "{\"outlet_id\":\"$OUTLET\",\"order_type\":\"takeaway\",\"subtotal\":10000,\"total_amount\":10000,\"tax_amount\":0,\"service_charge_amount\":0,\"discount_amount\":0,\"items\":[{\"product_id\":\"$RPID\",\"quantity\":1,\"unit_price\":10000,\"total_price\":10000,\"discount_amount\":0}]}")
    ROID=$(echo "$O" | field "d['data']['id']"); RRV=$(echo "$O" | field "d['data'].get('row_version',0)")
    [ -z "${ROID:-}" ] && bad "order recipe gagal: $(echo "$O"|head -c150)" || ok "order ${ROID:0:8}"
    P1=$(getstock "$RPID"); echo "  porsi setelah order: $P1"
    say "R1 Order recipe → bahan kepotong (porsi turun)"; chklt "porsi turun" "$P1" "$P0"
    api PUT "/orders/$ROID/status" "{\"status\":\"cancelled\",\"row_version\":$RRV}" >/dev/null
    P2=$(getstock "$RPID"); echo "  porsi setelah cancel: $P2"
    say "R2 Cancel → bahan balik";        chk "porsi balik" "$P0" "$P2"
    api PUT "/orders/$ROID/status" "{\"status\":\"cancelled\",\"row_version\":$((RRV+1))}" >/dev/null
    P3=$(getstock "$RPID"); echo "  porsi setelah cancel 2×: $P3"
    say "R3 Cancel 2× → idempotent (Finding 3 recipe)"; chk "gak inflate" "$P0" "$P3"
  fi
fi

printf '\n\033[1m═══ HASIL: %d PASS, %d FAIL, %d SKIP ═══\033[0m\n' "$PASS" "$FAIL" "$SKIP"
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
