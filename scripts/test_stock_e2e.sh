#!/usr/bin/env bash
# ============================================================================
# E2E smoke test — STOK (Finding 1 server-authoritative + Finding 3 idempotency)
# Verify: order create → deduct, cancel → restore, double-cancel → gak double,
#         restock → naik. Simple mode (products.stock_qty).
#
# Usage: bash scripts/test_stock_e2e.sh [PHONE]
#   default PHONE = 6289999990003 (_loadtest_tenant, Pro, simple mode)
# Butuh: container kasira-backend-1 + kasira-redis-1 jalan.
# ============================================================================
set -uo pipefail
PHONE="${1:-6289999990003}"
BASE="http://localhost:8000/api/v1"
PASS=0; FAIL=0

say()  { printf '\n\033[1m▸ %s\033[0m\n' "$*"; }
ok()   { printf '  \033[32m✓ PASS\033[0m %s\n' "$*"; PASS=$((PASS+1)); }
bad()  { printf '  \033[31m✗ FAIL\033[0m %s\n' "$*"; FAIL=$((FAIL+1)); }
chk()  { if [ "$2" = "$3" ]; then ok "$1 (=$3)"; else bad "$1 (harap $2, dapat $3)"; fi; }

# ── 1. Token via OTP inject ────────────────────────────────────────────────
say "Auth — inject OTP + verify (phone $PHONE)"
sudo docker exec kasira-redis-1 redis-cli SET "otp:$PHONE" "123456" EX 3600 >/dev/null
TOKEN=$(sudo docker exec kasira-backend-1 python -c "import httpx;r=httpx.post('http://localhost:8000/api/v1/auth/otp/verify',json={'phone':'$PHONE','otp':'123456'},timeout=10);print(r.json().get('data',{}).get('access_token',''))" 2>/dev/null)
if [ -z "$TOKEN" ]; then bad "gagal dapet token — stop"; exit 1; fi
ok "token didapat"

ME=$(curl -s "$BASE/auth/me" -H "Authorization: Bearer $TOKEN")
TENANT=$(echo "$ME" | python3 -c "import sys,json;d=json.load(sys.stdin).get('data',{});print(d.get('tenant_id') or d.get('tenant',{}).get('id',''))" 2>/dev/null)
OUTLET=$(echo "$ME" | python3 -c "import sys,json;d=json.load(sys.stdin).get('data',{});print(d.get('outlet_id') or (d.get('outlets',[{}])[0].get('id','') if d.get('outlets') else ''))" 2>/dev/null)
[ -z "$TENANT" ] && bad "tenant_id kosong dari /auth/me"

api() { local m=$1 p=$2 d=${3:-}; curl -s -X "$m" "$BASE$p" -H "Authorization: Bearer $TOKEN" -H "X-Tenant-ID: $TENANT" -H "Content-Type: application/json" ${d:+-d "$d"}; }
field() { python3 -c "import sys,json;d=json.load(sys.stdin);print($1)" 2>/dev/null; }

# fallback outlet dari daftar outlets
[ -z "$OUTLET" ] && OUTLET=$(api GET "/outlets/" | field "d['data'][0]['id']")
say "Konteks: tenant=${TENANT:0:8} outlet=${OUTLET:0:8}"

# ── 2. Pilih produk stock_enabled ──────────────────────────────────────────
say "Cari produk stock_enabled (simple mode)"
PRODUCTS=$(api GET "/products/?outlet_id=$OUTLET")
read -r PID PNAME PSTOCK < <(echo "$PRODUCTS" | python3 -c "
import sys,json
d=json.load(sys.stdin).get('data',[])
for p in d:
    if p.get('stock_enabled') and (p.get('stock') or 0) >= 5:
        print(p['id'], p.get('name','?').replace(' ','_'), int(p.get('stock',0))); break
" 2>/dev/null)
if [ -z "${PID:-}" ]; then bad "gak ada produk stock_enabled dgn stok>=5 — stop"; exit 1; fi
ok "produk: $PNAME (id ${PID:0:8}, stok $PSTOCK)"

getstock() { api GET "/products/?outlet_id=$OUTLET" | python3 -c "
import sys,json
for p in json.load(sys.stdin).get('data',[]):
    if p['id']=='$PID': print(int(p.get('stock',0))); break"; }

# ── 3. SCENARIO: order deduct (Finding 1 core) ─────────────────────────────
say "SCENARIO 1 — Order create → stok berkurang (server deduct)"
S0=$(getstock); echo "  stok awal: $S0"
QTY=2
ORDER=$(api POST "/orders/" "{\"outlet_id\":\"$OUTLET\",\"order_type\":\"takeaway\",\"subtotal\":20000,\"total_amount\":20000,\"tax_amount\":0,\"service_charge_amount\":0,\"discount_amount\":0,\"items\":[{\"product_id\":\"$PID\",\"quantity\":$QTY,\"unit_price\":10000,\"total_price\":20000,\"discount_amount\":0}]}")
OID=$(echo "$ORDER" | field "d['data']['id']")
OROW=$(echo "$ORDER" | field "d['data'].get('row_version',0)")
if [ -z "${OID:-}" ]; then bad "order gagal dibuat: $(echo "$ORDER" | head -c 200)"; else ok "order dibuat ${OID:0:8}"; fi
S1=$(getstock); echo "  stok setelah order: $S1"
chk "stok turun $QTY" "$((S0-QTY))" "$S1"

# ── 4. SCENARIO: cancel → restore ──────────────────────────────────────────
say "SCENARIO 2 — Cancel order → stok balik"
CANCEL=$(api PUT "/orders/$OID/status" "{\"status\":\"cancelled\",\"row_version\":$OROW}")
CSTAT=$(echo "$CANCEL" | field "d['data'].get('status','?')")
echo "  status: $CSTAT"
S2=$(getstock); echo "  stok setelah cancel: $S2"
chk "stok balik ke awal" "$S0" "$S2"

# ── 5. SCENARIO: double-cancel idempotency (Finding 3) ─────────────────────
say "SCENARIO 3 — Cancel LAGI → stok TIDAK double-restore (idempotency)"
api PUT "/orders/$OID/status" "{\"status\":\"cancelled\",\"row_version\":$OROW}" >/dev/null
api PUT "/orders/$OID/status" "{\"status\":\"cancelled\",\"row_version\":$((OROW+1))}" >/dev/null
S3=$(getstock); echo "  stok setelah cancel ke-2: $S3"
chk "stok tetap (gak inflate)" "$S0" "$S3"

# ── 6. SCENARIO: restock → naik (Finding 1 — perubahan server nongol) ──────
say "SCENARIO 4 — Restock produk → stok naik (server stock_qty authoritative)"
ADD=5
api POST "/products/$PID/restock" "{\"outlet_id\":\"$OUTLET\",\"quantity\":$ADD,\"notes\":\"e2e test\"}" >/dev/null
S4=$(getstock); echo "  stok setelah restock +$ADD: $S4"
chk "stok naik $ADD" "$((S0+ADD))" "$S4"
# balikin ke semula biar test idempotent
api POST "/products/$PID/adjust" "{\"outlet_id\":\"$OUTLET\",\"quantity\":$S0,\"notes\":\"e2e reset\"}" >/dev/null 2>&1 || true

# ── Ringkasan ──────────────────────────────────────────────────────────────
printf '\n\033[1m═══ HASIL: %d PASS, %d FAIL ═══\033[0m\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
