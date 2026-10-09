#!/usr/bin/env bash
# Rilis 9 Okt 2026: Selaris AI ubah harga jual lewat kartu Simpan (pemilik saja).
#
#   bash scripts/rilis-ai-harga-jual.sh
set -euo pipefail
cd /var/www/kasira
BASE=671a6fe
FILES="backend/services/ai_service.py backend/services/selaris_agent.py backend/services/selaris_bahan.py"
WEB="components/dashboard/bahan-cards.tsx"

if [ -n "$(git status --porcelain -- $FILES $WEB scripts/rilis-ai-harga-jual.sh)" ]; then
  git add $FILES $WEB scripts/rilis-ai-harga-jual.sh
  git commit -q -F - <<'MSG'
feat(selaris-ai): alat ubah_harga_jual dengan kartu yang bisa diedit

- Model menyalin harga akhir, naik/turun rupiah, atau naik/turun persen;
  new_sell_price menghitung (persen dibulatkan ke Rp500), modal resep dan
  harga varian dihitung kode (recipe_modal satu fungsi, variant_price).
- Kartu menandai harga di bawah modal dan lonjakan >3x; angka bisa diubah
  sebelum Simpan. Simpan = PUT /products/{id} dengan row_version.
- Hanya pemilik: PUT /products belum terdaftar untuk jabatan managed.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01BgwEYPmazt9ENyxRjVq5vH
MSG
  echo "✅ commit $(git rev-parse --short HEAD)"
fi
git push -q origin main && echo "✅ push main"

bash scripts/pasang-backend.sh $BASE $FILES
for i in $(seq 1 30); do
  sudo -n docker exec kasira-backend-1 python -c "from backend.services import selaris_bahan, ai_service" >/dev/null 2>&1 && break
  sleep 2
done
sudo -n docker exec kasira-backend-1 python -c "
from backend.services import selaris_bahan as s
from decimal import Decimal
assert s.new_sell_price(Decimal(18000), {'naik_persen': 7})[0] == 19500
print('✅ backend memuat alat harga jual')" || { echo "❌ backend gagal memuat alat. Frontend TIDAK dipasang."; exit 1; }

sudo -n docker tag kasira-frontend:latest selaris-frontend-before-harga-jual:20261009 2>/dev/null || true
sudo -n docker compose build frontend
sudo -n docker compose up -d --no-deps frontend
echo "✅ frontend terpasang. Rollback web: docker tag selaris-frontend-before-harga-jual:20261009 kasira-frontend:latest && docker compose up -d --no-deps frontend"
