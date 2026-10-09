#!/usr/bin/env bash
# Rilis 9 Okt 2026: baca foto nota pakai OpenAI (kunci sama dengan Sefrekuensi).
#
#   bash scripts/rilis-nota-openai.sh
#
# Kunci TIDAK disalin lewat argumen atau log: dibaca dari /etc/sefrekuensi/openai.env,
# dialirkan lewat stdin ke berkas /app/secrets/openai.key (600) di container yang ada.
# Container tidak di-recreate (hotfix docker cp tetap); berkas di container bertahan
# saat restart. Kunci juga ditambahkan ke .env supaya ikut kalau suatu hari recreate.
set -euo pipefail
cd /var/www/kasira
BASE=4c0d80c
FILES="backend/core/config.py backend/services/llm_client.py backend/services/invoice_ocr_service.py"
WEB="app/privacy/page.tsx"

if [ -n "$(git status --porcelain -- $FILES $WEB scripts/rilis-nota-openai.sh)" ]; then
  git add $FILES $WEB scripts/rilis-nota-openai.sh
  git commit -q -F - <<'MSG'
feat(nota): baca foto nota pakai OpenAI vision, Anthropic jadi cadangan

- invoice_ocr_service: OpenAI Responses API (gpt-5.6-luna, json_object,
  store=false), pola sama dengan Sefrekuensi. Prompt dan parsing tetap.
- Kunci dari OPENAI_API_KEY atau /app/secrets/openai.key (container tidak
  di-recreate, jadi env baru tidak terbaca).
- /privacy: OpenAI untuk baca nota, DeepSeek juga saran harga, Anthropic
  cadangan.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01BgwEYPmazt9ENyxRjVq5vH
MSG
  echo "✅ commit $(git rev-parse --short HEAD)"
fi
git push -q origin main && echo "✅ push main"

# 1. Kunci ke container + .env (tanpa pernah tampil di layar)
KEY=$(sudo -n sed -n 's/^OPENAI_API_KEY=//p' /etc/sefrekuensi/openai.env | tr -d '"'"'"' \r')
[ -n "$KEY" ] || { echo "❌ OPENAI_API_KEY tidak ada di /etc/sefrekuensi/openai.env"; exit 1; }
printf '%s' "$KEY" | sudo -n docker exec -i kasira-backend-1 sh -c 'umask 077; mkdir -p /app/secrets; cat > /app/secrets/openai.key'
if ! grep -q '^OPENAI_API_KEY=' .env; then
  { printf '\nOPENAI_API_KEY=%s\n' "$KEY"; } >> .env
fi
unset KEY
echo "✅ kunci OpenAI terpasang (container + .env)"

# 2. Backend
bash scripts/pasang-backend.sh $BASE $FILES
for i in $(seq 1 30); do
  sudo -n docker exec kasira-backend-1 python -c "import backend.services.invoice_ocr_service" >/dev/null 2>&1 && break
  sleep 2
done

# 3. Uji nyata: satu gambar nota buatan (dibuat di host, PIL tidak ada di container)
#    dibaca OpenAI lewat fungsi produksi, tanpa menyimpan apa pun.
python3 - <<'PY' | sudo -n docker exec -i kasira-backend-1 python -c '
import asyncio, sys
from backend.services.llm_client import openai_key
from backend.services.invoice_ocr_service import extract_invoice_data
assert openai_key(), "kunci tidak terbaca"
data = asyncio.run(extract_invoice_data(sys.stdin.buffer.read(), "image/png"))
items = data.get("items") or []
print("hasil:", data.get("supplier_name"), [(x.get("name"), x.get("quantity"), x.get("unit"), x.get("total_price")) for x in items])
assert len(items) == 2 and "error" not in data, data
print("✅ OpenAI membaca nota uji")
'
import io, sys
from PIL import Image, ImageDraw, ImageFont
img = Image.new("RGB", (900, 420), "white"); d = ImageDraw.Draw(img)
try:
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 30)
except OSError:
    font = ImageFont.load_default()
for i, line in enumerate(["TOKO MAKMUR JAYA", "09/10/2026", "Gula aren 2 kg x 35.000 = 70.000",
                          "Susu UHT 5 liter x 18.000 = 90.000", "TOTAL 160.000"]):
    d.text((30, 30 + i * 70), line, fill="black", font=font)
buf = io.BytesIO(); img.save(buf, "PNG"); sys.stdout.buffer.write(buf.getvalue())
PY

# 4. Halaman privasi
sudo -n docker tag kasira-frontend:latest selaris-frontend-before-nota-openai:20261009 2>/dev/null || true
sudo -n docker compose build frontend
sudo -n docker compose up -d --no-deps frontend
echo "✅ selesai. Rollback web: docker tag selaris-frontend-before-nota-openai:20261009 kasira-frontend:latest && docker compose up -d --no-deps frontend"
