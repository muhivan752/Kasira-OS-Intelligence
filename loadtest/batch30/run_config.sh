#!/bin/bash
# Kasira Batch #30 Tahap 2 — Runtime config
# Sourced sebelum `k6 run` — semua env var ready.
#
# Usage (02:00 WIB):
#   source loadtest/batch30/run_config.sh
#   k6 run loadtest/batch30/k6_hammer.js
#
# JWT refresh (expired 2026-04-27 13:57 UTC — regen kalau expired):
#   sudo docker exec kasira-redis-1 redis-cli SET "otp:6289999990001" "123456" EX 3600
#   TOKEN=$(sudo docker exec kasira-backend-1 python -c "import httpx; r=httpx.post('http://localhost:8000/api/v1/auth/otp/verify', json={'phone':'6289999990001','otp':'123456'}, timeout=10); print(r.json()['data']['access_token'])")
#   # Update TOKEN line di bawah.

export BASE_URL="http://localhost:8000/api/v1"
export TENANT_ID="426c79ee-f86d-4b5a-9cef-63bf24bbd677"
export OUTLET_ID="0465ade4-81d3-444b-bd4f-d5d0485263c4"

# JWT — _loadtest_tenant, user LoadTest Owner, exp 2026-04-27 13:57 UTC
export TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3Nzc1NTgyNzEsInN1YiI6ImJlY2M1ZGRjLWI0NjUtNGFmMi04NjUwLWJkOGY4MWI1ODE2ZSJ9.pa1n9hh0ZlYlyXxrRd0c_Xh8U80ClN7Ra-NP1ci9NlQ"

# 10 product IDs (stock_qty > 100k — plenty for 100 VU × 12min write load)
export PRODUCT_IDS="85dde621-011a-4b63-b4e5-e8ab4f11d9d8,ea17135c-2137-4a1c-be6e-8d27e6ee1fc8,0e1ac1b3-bc06-4992-839b-27cb4c4cee19,f69be056-d87c-4c23-ba88-0258d6d673d7,982a7101-4124-47b8-927a-f7c5d96420fb,0c7cc9c0-8bb1-42a1-9f73-c452c3055851,fa24e935-9d3d-4658-a88f-63c27653848f,e9a638a3-672b-4e86-8a1f-a5291e02c130,7d11470f-8425-4f95-9297-286f9226ad53,5caa1bf6-98be-41bf-a6b7-4f53302303bd"

echo "✅ Batch #30 run_config loaded"
echo "   BASE_URL: $BASE_URL"
echo "   TENANT:   $TENANT_ID"
echo "   OUTLET:   $OUTLET_ID"
echo "   PRODUCTS: $(echo "$PRODUCT_IDS" | tr ',' '\n' | wc -l) IDs"
echo "   TOKEN:    ${TOKEN:0:20}..."
echo ""
echo "Next: k6 run loadtest/batch30/k6_hammer.js"
