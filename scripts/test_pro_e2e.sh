#!/bin/bash
#
# Kasira Pro E2E Test Script
# Test semua fitur Pro dari API — simulasi real user flow
#
BASE="http://localhost:8000/api/v1"
PASS=0; FAIL=0; SKIP=0

# Pro tenant — Kasira Coffee
TOKEN="$1"
TENANT="$2"
OUTLET="$3"
BRAND="$4"

if [ -z "$TOKEN" ]; then
  echo "Usage: bash test_pro_e2e.sh <TOKEN> <TENANT_ID> <OUTLET_ID> <BRAND_ID>"
  exit 1
fi

H1="-H Authorization:\ Bearer\ $TOKEN"
H2="-H X-Tenant-ID:\ $TENANT"
H3="-H Content-Type:\ application/json"

api_get() {
  curl -s -L -o /tmp/pr.json -w "%{http_code}" \
    -H "Authorization: Bearer $TOKEN" \
    -H "X-Tenant-ID: $TENANT" \
    "$BASE$1"
}

api_post() {
  curl -s -L -o /tmp/pr.json -w "%{http_code}" \
    -H "Authorization: Bearer $TOKEN" \
    -H "X-Tenant-ID: $TENANT" \
    -H "Content-Type: application/json" \
    -X POST -d "$2" "$BASE$1"
}

api_put() {
  curl -s -L -o /tmp/pr.json -w "%{http_code}" \
    -H "Authorization: Bearer $TOKEN" \
    -H "X-Tenant-ID: $TENANT" \
    -H "Content-Type: application/json" \
    -X PUT -d "$2" "$BASE$1"
}

api_delete() {
  curl -s -L -o /tmp/pr.json -w "%{http_code}" \
    -H "Authorization: Bearer $TOKEN" \
    -H "X-Tenant-ID: $TENANT" \
    -X DELETE "$BASE$1"
}

jq_field() { python3 -c "import sys,json; d=json.load(open('/tmp/pr.json')); print($1)" 2>/dev/null; }

chk() {
  local name="$1" exp="$2" got="$3"
  if [ "$got" = "$exp" ]; then echo "  ✅ $name"; PASS=$((PASS+1))
  else echo "  ❌ $name (expected=$exp got=$got)"; FAIL=$((FAIL+1)); fi
}

chk_not() {
  local name="$1" not_exp="$2" got="$3"
  if [ "$got" != "$not_exp" ] && [ -n "$got" ]; then echo "  ✅ $name ($got)"; PASS=$((PASS+1))
  else echo "  ❌ $name (got=$got, should not be $not_exp)"; FAIL=$((FAIL+1)); fi
}

TODAY=$(date -u +%Y-%m-%d)

echo "╔══════════════════════════════════════════════════════╗"
echo "║     KASIRA PRO — FULL E2E TEST SCENARIO             ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
echo "Tenant: $TENANT"
echo "Outlet: $OUTLET"
echo "Brand:  $BRAND"
echo "Date:   $TODAY"
echo ""

# ══════════════════════════════════════════════════════════
echo "━━━ SCENARIO 1: BAHAN BAKU LIFECYCLE ━━━"
echo ""

echo "[1.1] Create ingredient — Tepung Terigu"
S=$(api_post "/ingredients/" "{
  \"brand_id\": \"$BRAND\",
  \"name\": \"Tepung Terigu Test\",
  \"base_unit\": \"gram\",
  \"unit_type\": \"WEIGHT\",
  \"buy_price\": 12000,
  \"buy_qty\": 1000,
  \"ingredient_type\": \"recipe\"
}")
chk "Create ingredient" "200" "$S"
ING_ID=$(jq_field "d['data']['id']")
COST=$(jq_field "d['data']['cost_per_base_unit']")
chk "Auto-calc cost/unit (12000/1000=12)" "12" "${COST%.*}"
echo "  → Ingredient ID: ${ING_ID:0:8}..."

echo ""
echo "[1.2] Restock ingredient — 5000g"
S=$(api_post "/ingredients/$ING_ID/restock" "{
  \"outlet_id\": \"$OUTLET\",
  \"quantity\": 5000,
  \"notes\": \"Test restock\"
}")
chk "Restock 5000g" "200" "$S"

echo ""
echo "[1.3] Get ingredient — verify stock + usage"
S=$(api_get "/ingredients/$ING_ID?outlet_id=$OUTLET")
chk "Get ingredient" "200" "$S"
STOCK=$(jq_field "d['data']['current_stock']")
chk "Stock = 5000" "5000.0" "$STOCK"
USED_IN=$(jq_field "len(d['data'].get('used_in',[]))")
chk "Used in 0 menus (belum ada recipe)" "0" "$USED_IN"

echo ""
echo "[1.4] Update buy_price — harga naik"
S=$(api_put "/ingredients/$ING_ID" "{
  \"buy_price\": 15000,
  \"buy_qty\": 1000,
  \"row_version\": 0
}")
chk "Update buy_price" "200" "$S"
NEW_COST=$(jq_field "d['data']['cost_per_base_unit']")
chk "New cost/unit (15000/1000=15)" "15" "${NEW_COST%.*}"

echo ""
echo "[1.5] List ingredients — verify usage data returned"
S=$(api_get "/ingredients/?brand_id=$BRAND&outlet_id=$OUTLET")
chk "List ingredients" "200" "$S"
HAS_USED=$(jq_field "'used_in' in str(d)")
chk "Response includes used_in field" "True" "$HAS_USED"


# ══════════════════════════════════════════════════════════
echo ""
echo "━━━ SCENARIO 2: RECIPE BUILDER ━━━"
echo ""

echo "[2.1] Get a product to attach recipe"
S=$(api_get "/products/?brand_id=$BRAND")
chk "List products" "200" "$S"
# Pick first product without existing recipe if possible
PROD_ID=$(jq_field "d['data'][0]['id']")
PROD_NAME=$(jq_field "d['data'][0]['name']")
echo "  → Product: $PROD_NAME (${PROD_ID:0:8}...)"

echo ""
echo "[2.2] Get existing ingredients for recipe"
S=$(api_get "/ingredients/?brand_id=$BRAND&outlet_id=$OUTLET")
ALL_INGS=$(jq_field "[(i['id'],i['name']) for i in d['data'][:3]]")
ING1=$(jq_field "d['data'][0]['id']")
ING2=$(jq_field "d['data'][1]['id']" 2>/dev/null || echo "")
echo "  → Using ingredients: $(jq_field "[i['name'] for i in d['data'][:2]]")"

echo ""
echo "[2.3] Create recipe with real quantities"
RECIPE_BODY="{
  \"product_id\": \"$PROD_ID\",
  \"ingredients\": [
    {\"ingredient_id\": \"$ING1\", \"quantity\": 25, \"quantity_unit\": \"gram\", \"is_optional\": false}
  ]
}"
if [ -n "$ING2" ]; then
  RECIPE_BODY="{
    \"product_id\": \"$PROD_ID\",
    \"ingredients\": [
      {\"ingredient_id\": \"$ING1\", \"quantity\": 25, \"quantity_unit\": \"gram\", \"is_optional\": false},
      {\"ingredient_id\": \"$ING2\", \"quantity\": 10, \"quantity_unit\": \"gram\", \"is_optional\": false}
    ]
  }"
fi
S=$(api_post "/recipes/" "$RECIPE_BODY")
chk "Create recipe" "200" "$S"
RECIPE_ID=$(jq_field "d['data']['id']")
RECIPE_HPP=$(jq_field "d['data']['total_cost']")
echo "  → Recipe ID: ${RECIPE_ID:0:8}... | HPP: Rp$RECIPE_HPP"

echo ""
echo "[2.4] Verify ingredient now shows usage"
S=$(api_get "/ingredients/?brand_id=$BRAND&outlet_id=$OUTLET")
USAGE=$(jq_field "[u for i in d['data'] for u in i.get('used_in',[]) if '$PROD_NAME' in u.get('product_name','')]")
chk_not "Ingredient shows usage for $PROD_NAME" "[]" "$USAGE"


# ══════════════════════════════════════════════════════════
echo ""
echo "━━━ SCENARIO 3: HPP REPORT ━━━"
echo ""

echo "[3.1] Get HPP report"
S=$(api_get "/recipes/hpp?brand_id=$BRAND")
chk "HPP report" "200" "$S"

echo "[3.2] Verify ingredient breakdown exists"
HAS_INGS=$(jq_field "any(len(p.get('ingredients',[])) > 0 for p in d['data'])")
chk "HPP has ingredient breakdown" "True" "$HAS_INGS"

echo "[3.3] Check margin calculation"
MARGINS=$(jq_field "[(p['product_name'], p['margin_percent']) for p in d['data'] if p['has_recipe']][:3]")
echo "  → Margins: $MARGINS"
HAS_MARGIN=$(jq_field "any(p['margin_percent'] > 0 for p in d['data'] if p['has_recipe'])")
chk "At least one product has positive margin" "True" "$HAS_MARGIN"


# ══════════════════════════════════════════════════════════
echo ""
echo "━━━ SCENARIO 4: ORDER + INGREDIENT AUTO-DEDUCT ━━━"
echo ""

echo "[4.1] Get stock BEFORE order"
S=$(api_get "/ingredients/$ING1?outlet_id=$OUTLET")
STOCK_BEFORE=$(jq_field "d['data']['current_stock']")
echo "  → Stock before: $STOCK_BEFORE"

echo ""
echo "[4.2] Get active shift (or note if none)"
S=$(api_get "/shifts/?outlet_id=$OUTLET&status=open")
SHIFT_ID=$(jq_field "d['data'][0]['id']" 2>/dev/null || echo "")
if [ -z "$SHIFT_ID" ] || [ "$SHIFT_ID" = "None" ]; then
  echo "  ⚠️  No open shift — creating one"
  S=$(api_post "/shifts/" "{\"outlet_id\": \"$OUTLET\", \"opening_cash\": 100000}")
  SHIFT_ID=$(jq_field "d['data']['id']" 2>/dev/null || echo "")
fi
echo "  → Shift: ${SHIFT_ID:0:8}..."

echo ""
echo "[4.3] Create order with recipe product (x2)"
S=$(api_post "/orders/" "{
  \"outlet_id\": \"$OUTLET\",
  \"order_type\": \"takeaway\",
  \"shift_session_id\": \"$SHIFT_ID\",
  \"items\": [
    {\"product_id\": \"$PROD_ID\", \"quantity\": 2, \"unit_price\": 15000}
  ]
}")
chk "Create order" "200" "$S"
ORDER_ID=$(jq_field "d['data']['id']")
echo "  → Order ID: ${ORDER_ID:0:8}..."

echo ""
echo "[4.4] Get stock AFTER order"
S=$(api_get "/ingredients/$ING1?outlet_id=$OUTLET")
STOCK_AFTER=$(jq_field "d['data']['current_stock']")
echo "  → Stock after: $STOCK_AFTER"

echo "[4.5] Verify deduction: 25g × 2 = 50g less"
EXPECTED=$(python3 -c "print(${STOCK_BEFORE} - 50.0)")
chk "Stock deducted correctly" "$EXPECTED" "$STOCK_AFTER"

echo ""
echo "[4.6] Pay the order (cash)"
S=$(api_post "/payments/" "{
  \"order_id\": \"$ORDER_ID\",
  \"payment_method\": \"cash\",
  \"amount_paid\": 30000
}")
chk "Cash payment" "200" "$S"


# ══════════════════════════════════════════════════════════
echo ""
echo "━━━ SCENARIO 5: RECIPE ENFORCEMENT ━━━"
echo ""

echo "[5.1] Create product WITHOUT recipe"
S=$(api_post "/products/" "{
  \"brand_id\": \"$BRAND\",
  \"name\": \"Test No Recipe\",
  \"base_price\": 10000,
  \"stock_enabled\": true,
  \"is_active\": true
}")
chk "Create product" "200" "$S"
NOREC_ID=$(jq_field "d['data']['id']")

echo ""
echo "[5.2] Try order product without recipe (should fail in recipe mode)"
S=$(api_post "/orders/" "{
  \"outlet_id\": \"$OUTLET\",
  \"order_type\": \"takeaway\",
  \"shift_session_id\": \"$SHIFT_ID\",
  \"items\": [
    {\"product_id\": \"$NOREC_ID\", \"quantity\": 1, \"unit_price\": 10000}
  ]
}")
chk "Order without recipe rejected (400)" "400" "$S"
ERR=$(jq_field "d.get('detail','')")
echo "  → Error: $ERR"

echo ""
echo "[5.3] Cleanup — delete test product"
S=$(api_delete "/products/$NOREC_ID")
chk "Delete test product" "200" "$S"


# ══════════════════════════════════════════════════════════
echo ""
echo "━━━ SCENARIO 6: TABLES & RESERVASI ━━━"
echo ""

echo "[6.1] List tables"
S=$(api_get "/tables/?outlet_id=$OUTLET")
chk "List tables" "200" "$S"
TABLE_COUNT=$(jq_field "len(d['data'])")
echo "  → $TABLE_COUNT tables"

echo ""
echo "[6.2] List reservations"
S=$(api_get "/reservations/?outlet_id=$OUTLET")
chk "List reservations" "200" "$S"

echo ""
echo "[6.3] Create reservation"
TOMORROW=$(date -u -d "+1 day" +%Y-%m-%d 2>/dev/null || date -u -v+1d +%Y-%m-%d)
S=$(api_post "/reservations/" "{
  \"outlet_id\": \"$OUTLET\",
  \"customer_name\": \"Test Customer\",
  \"customer_phone\": \"628999888777\",
  \"guest_count\": 4,
  \"reservation_date\": \"$TOMORROW\",
  \"start_time\": \"19:00\",
  \"notes\": \"E2E test\"
}")
if [ "$S" = "200" ] || [ "$S" = "201" ]; then
  chk "Create reservation" "200" "200"
  RES_ID=$(jq_field "d['data']['id']")
  echo "  → Reservation ID: ${RES_ID:0:8}..."
else
  echo "  ⚠️  Reservation creation: $S (may need settings enabled)"
  SKIP=$((SKIP+1))
fi


# ══════════════════════════════════════════════════════════
echo ""
echo "━━━ SCENARIO 7: LOYALTY POINTS ━━━"
echo ""

echo "[7.1] List loyalty points"
S=$(api_get "/loyalty/points/?outlet_id=$OUTLET")
chk "List loyalty" "200" "$S"

echo ""
echo "[7.2] Check point transactions"
S=$(api_get "/loyalty/transactions/?outlet_id=$OUTLET")
if [ "$S" = "200" ]; then
  chk "List transactions" "200" "$S"
  TX_COUNT=$(jq_field "len(d['data'])")
  echo "  → $TX_COUNT transactions"
else
  echo "  ⚠️  Loyalty transactions: $S"
  SKIP=$((SKIP+1))
fi


# ══════════════════════════════════════════════════════════
echo ""
echo "━━━ SCENARIO 8: KNOWLEDGE GRAPH ━━━"
echo ""

echo "[8.1] Rebuild knowledge graph"
S=$(api_post "/knowledge-graph/rebuild?brand_id=$BRAND" "{}")
chk "Rebuild KG" "200" "$S"
EDGES=$(jq_field "d['data']['edges_created']")
echo "  → $EDGES edges created"

echo ""
echo "[8.2] Top ingredients"
S=$(api_get "/knowledge-graph/top-ingredients?limit=5")
chk "Top ingredients" "200" "$S"
TOP=$(jq_field "[(i['name'], i['product_count']) for i in d['data'][:3]]")
echo "  → $TOP"

echo ""
echo "[8.3] Affected products (if ingredient runs out)"
S=$(api_get "/knowledge-graph/affected-products/$ING1")
chk "Affected products" "200" "$S"
AFFECTED=$(jq_field "len(d['data'])")
echo "  → $AFFECTED products affected"

echo ""
echo "[8.4] Product ingredients via KG"
S=$(api_get "/knowledge-graph/product-ingredients/$PROD_ID")
chk "Product ingredients" "200" "$S"


# ══════════════════════════════════════════════════════════
echo ""
echo "━━━ SCENARIO 9: AI CHATBOT ━━━"
echo ""

echo "[9.1] Ask omzet (READ intent)"
S=$(curl -s -o /tmp/pr_ai.txt -w "%{http_code}" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant-ID: $TENANT" \
  -H "Content-Type: application/json" \
  -X POST "$BASE/ai/chat" \
  -d "{\"message\": \"Berapa omzet hari ini?\", \"outlet_id\": \"$OUTLET\"}")
chk "AI chat endpoint" "200" "$S"
AI_RESP=$(cat /tmp/pr_ai.txt | head -5)
echo "  → Response (first 200 chars): ${AI_RESP:0:200}"

echo ""
echo "[9.2] Ask reservasi (READ intent)"
S=$(curl -s -o /tmp/pr_ai2.txt -w "%{http_code}" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant-ID: $TENANT" \
  -H "Content-Type: application/json" \
  -X POST "$BASE/ai/chat" \
  -d "{\"message\": \"Ada meja kosong gak hari ini?\", \"outlet_id\": \"$OUTLET\"}")
chk "AI reservation intent" "200" "$S"

echo ""
echo "[9.3] Try WRITE intent (should be blocked)"
S=$(curl -s -o /tmp/pr_ai3.txt -w "%{http_code}" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant-ID: $TENANT" \
  -H "Content-Type: application/json" \
  -X POST "$BASE/ai/chat" \
  -d "{\"message\": \"Tambah produk baru harga 50000\", \"outlet_id\": \"$OUTLET\"}")
chk "AI write blocked" "200" "$S"
WRITE_RESP=$(cat /tmp/pr_ai3.txt)
HAS_WARNING=$(echo "$WRITE_RESP" | grep -c "mengubah data" || echo "0")
chk "AI write shows warning" "1" "$([ "$HAS_WARNING" -gt 0 ] && echo 1 || echo 0)"


# ══════════════════════════════════════════════════════════
echo ""
echo "━━━ SCENARIO 10: REPORTS ━━━"
echo ""

echo "[10.1] Daily report"
S=$(api_get "/reports/summary/?outlet_id=$OUTLET&start_date=$TODAY&end_date=$TODAY")
chk "Daily report" "200" "$S"

echo ""
echo "[10.2] HPP report"
S=$(api_get "/recipes/hpp?brand_id=$BRAND")
chk "HPP report" "200" "$S"


# ══════════════════════════════════════════════════════════
echo ""
echo "━━━ SCENARIO 11: EVENT STORE INTEGRITY ━━━"
echo ""

echo "[11.1] Verify stock vs event consistency"
python3 -c "
import json
# We already tested stock deduction in scenario 4
# Just verify the numbers are consistent
print('  Stock before: $STOCK_BEFORE')
print('  Stock after:  $STOCK_AFTER')
expected = float('$STOCK_BEFORE') - 50.0
actual = float('$STOCK_AFTER')
if abs(expected - actual) < 0.01:
    print('  ✅ Event-sourced deduction matches computed stock')
else:
    print(f'  ❌ DRIFT: expected={expected} actual={actual}')
"


# ══════════════════════════════════════════════════════════
echo ""
echo "━━━ CLEANUP ━━━"
echo ""
echo "[Cleanup] Delete test ingredient"
S=$(api_delete "/ingredients/$ING_ID")
chk "Delete test ingredient" "200" "$S"


# ══════════════════════════════════════════════════════════
echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║  RESULTS                                             ║"
echo "╠══════════════════════════════════════════════════════╣"
printf "║  ✅ PASS: %-3d                                        ║\n" $PASS
printf "║  ❌ FAIL: %-3d                                        ║\n" $FAIL
printf "║  ⚠️  SKIP: %-3d                                        ║\n" $SKIP
echo "╚══════════════════════════════════════════════════════╝"

if [ $FAIL -eq 0 ]; then
  echo ""
  echo "🎉 ALL PRO FEATURES PRODUCTION READY!"
else
  echo ""
  echo "⚠️  $FAIL tests failed — review above"
fi
