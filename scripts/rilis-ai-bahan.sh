#!/usr/bin/env bash
# Rilis 9 Okt 2026: Selaris AI ubah harga bahan + tambah stok lewat kartu Simpan.
# Backend dulu (alat baru), lalu frontend (kartu).
#
#   bash scripts/rilis-ai-bahan.sh
set -euo pipefail
cd /var/www/kasira
BASE=0087adb
FILES="backend/services/ai_service.py backend/services/selaris_agent.py backend/services/selaris_bahan.py"
WEB="components/dashboard/bahan-cards.tsx app/dashboard/ai/page.tsx app/dashboard/ai/scoped-chat.tsx"

if [ -n "$(git status --porcelain -- $FILES $WEB scripts/rilis-ai-bahan.sh)" ]; then
  git add $FILES $WEB scripts/rilis-ai-bahan.sh
  git commit -q -F - <<'MSG'
feat(selaris-ai): alat ubah_harga_bahan dan tambah_stok dengan kartu Simpan

- services/selaris_bahan.py: model hanya menyalin bahan/jumlah/satuan/rupiah;
  konversi satuan, stok sebelum/sesudah, rata-rata bergerak, dan dampak modal
  produk dihitung kode. Tidak menulis DB.
- Kartu web: Simpan memanggil PUT /ingredients/{id}, POST /purchases (dengan
  harga, client_request_id tetap per kartu), atau POST /ingredients/{id}/restock
  (tanpa harga). Izin dan audit tetap di endpoint modulnya.
- Alat ditawarkan sesuai izin endpoint tujuan; tanpa izin pembelian, harga
  diabaikan dan dicatat sebagai stok masuk saja.
- Jalur RESTOCK lama (tambah stok langsung tanpa konfirmasi) tidak dipakai
  selama DeepSeek aktif.

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
sudo -n docker exec kasira-backend-1 python -c "from backend.services import selaris_bahan, ai_service; print('✅ backend memuat alat bahan')" \
  || { echo "❌ backend gagal memuat alat. Frontend TIDAK dipasang."; exit 1; }

sudo -n docker tag kasira-frontend:latest selaris-frontend-before-ai-bahan:20261009 2>/dev/null || true
sudo -n docker compose build frontend
sudo -n docker compose up -d --no-deps frontend
echo "✅ frontend terpasang. Rollback web: docker tag selaris-frontend-before-ai-bahan:20261009 kasira-frontend:latest && docker compose up -d --no-deps frontend"
