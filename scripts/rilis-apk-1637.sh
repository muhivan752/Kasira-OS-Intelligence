#!/usr/bin/env bash
# Rilis 9 Okt 2026: APK Selaris POS + Dapur 1.6.37, plus backend/web "kartu
# hanya untuk klien yang bisa menampilkannya".
#
#   bash scripts/rilis-apk-1637.sh
#
# Urutan: backend dulu (app kasir, termasuk APK lama, berhenti ditawari alat
# berkartu), lalu web (mengirim cards:true), lalu build APK di GitHub Actions
# (terbit di GitHub Releases + version.json, update tidak wajib).
set -euo pipefail
cd /var/www/kasira
BASE=b662df8
VERSION=1.6.37
FILES="backend/api/routes/ai.py backend/services/ai_service.py backend/services/selaris_agent.py"
WEB="app/dashboard/ai/page.tsx app/dashboard/ai/scoped-chat.tsx"
APP="kasir_app/lib/features/auth/presentation/pages/login_page.dart kasir_app/test/accounts_test.dart kasir_app/test/login_test.dart kasir_app/lib/features/ai/providers/ai_chat_provider.dart kasir_app/lib/features/ai/presentation/pages/ai_chat_page.dart kasir_app/lib/features/ai/presentation/widgets/ai_cards.dart kasir_app/test/ai_cards_test.dart .github/workflows/build-apk.yml"
NOTES="Karyawan masuk cukup dengan nomor HP atau username dan password, tanpa username toko. Tersedia hapus akun di menu Tim dan akun saya. Tab Laporan mengikuti izin jabatan dan mendukung outlet mode Resep. Selaris AI di aplikasi bisa menyusun resep, mengubah harga bahan, mencatat bahan masuk, dan mengubah harga jual, dengan konfirmasi Simpan."

if [ -n "$(git status --porcelain -- $FILES $WEB $APP scripts/rilis-apk-1637.sh)" ]; then
  git add $FILES $WEB $APP scripts/rilis-apk-1637.sh
  git commit -q -F - <<'MSG'
feat: app 1.6.37, kartu Simpan Selaris AI di app; alat berkartu Selaris AI hanya untuk klien yang bisa menampilkan kartu

- ChatRequest.cards: web mengirim true; app kasir (termasuk APK lama) tidak,
  jadi alat resep/harga bahan/stok/harga jual tidak ditawarkan di app dan AI
  mengarahkan ke Selaris AI di dashboard web (selaris_agent.NO_CARDS, setelah
  aturan gaya). Sebelumnya app menerima kartu yang tidak bisa ditampilkan.
- Chat app menampilkan kartu Simpan (resep, harga bahan, bahan masuk, harga
  jual) dan mengirim cards:true; Simpan memanggil endpoint yang sama dengan web
  dengan path persis (Dio tidak mengikuti 307 untuk POST/PUT). Parser SSE pakai
  LineSplitter (dulu event yang terbelah antar paket hilang). Tes ai_cards_test
  (8) masuk CI.
- Login app: baris pemisah boleh turun baris (meluber 277px di 320px/160%).
- Tes login/akun disesuaikan dengan layar masuk tanpa username toko.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01BgwEYPmazt9ENyxRjVq5vH
MSG
  echo "✅ commit $(git rev-parse --short HEAD)"
fi
git push -q origin main && echo "✅ push main"

# 1. Backend
bash scripts/pasang-backend.sh $BASE $FILES
for i in $(seq 1 30); do
  sudo -n docker exec kasira-backend-1 python -c "from backend.api.routes.ai import ChatRequest" >/dev/null 2>&1 && break
  sleep 2
done
sudo -n docker exec kasira-backend-1 python -c "
from backend.api.routes.ai import ChatRequest
from backend.services import selaris_agent
assert 'cards' in ChatRequest.model_fields and selaris_agent.NO_CARDS
print('✅ backend: alat berkartu hanya untuk web')" || { echo "❌ backend belum memuat perubahan. Web dan APK TIDAK diproses."; exit 1; }

# 2. Web
sudo -n docker tag kasira-frontend:latest selaris-frontend-before-apk1637:20261009 2>/dev/null || true
sudo -n docker compose build frontend
sudo -n docker compose up -d --no-deps frontend
echo "✅ web terpasang"

# 3. APK di GitHub Actions
gh workflow run build-apk.yml -f version=$VERSION -f is_mandatory=false -f release_notes="$NOTES"
sleep 8
gh run list --workflow=build-apk.yml --limit 1
echo "✅ build APK $VERSION dimulai di GitHub Actions (sekitar 15 s.d. 25 menit). Pantau: gh run watch"
