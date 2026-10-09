#!/usr/bin/env bash
# Rilis 9 Okt 2026: masuk tanpa username toko + form karyawan 3 isian.
# Urutan penting: backend DULU (web baru memanggil /auth/password/login tanpa
# shop_username; backend lama menolaknya), baru frontend.
#
#   bash scripts/rilis-masuk-mudah.sh
set -euo pipefail
cd /var/www/kasira
BASE=c596555
FILES="backend/api/routes/accounts.py backend/schemas/account.py backend/services/accounts.py backend/services/staff_accounts.py"
WEB="app/actions/accounts.ts app/dashboard/hris/access/page.tsx app/dashboard/hris/hris.css app/dashboard/hris/page.tsx app/login/password/page.tsx components/auth/auth-flow.tsx lib/hris.ts"
APP="kasir_app/lib/features/auth/presentation/pages/login_page.dart"

if ! git diff --quiet -- $FILES $WEB $APP; then
  git add $FILES $WEB $APP scripts/rilis-masuk-mudah.sh
  git commit -q -F - <<'EOF'
feat(akun): masuk tanpa username toko, form karyawan 3 isian, kode aktivasi diganti password baru

- POST /auth/password/login: shop_username opsional. Tanpa itu server mencari
  akun karyawan (nomor HP/username) di semua toko, atau pemilik lewat username
  tokonya; cocok di >1 toko -> choose_shop + daftar toko (sesudah password
  cocok), klien kirim ulang dengan tenant_id. Jalur lama APK tetap.
- Akun karyawan tidak lagi butuh username toko pemilik.
- Web /login: Google, kode Sefrekuensi, dan nomor HP/username + password di
  satu layar; /login/password redirect ke /login.
- Tim: tambah karyawan = nama, nomor HP, tugas, password otomatis; sisanya di
  Detail lain. Tombol Buat password baru per karyawan. Pesan WA tanpa username
  toko. Bagian kode aktivasi di Jabatan dan izin dihapus.
- App: layar masuk yang sama + Pilih toko (ikut APK berikutnya).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01BgwEYPmazt9ENyxRjVq5vH
EOF
  echo "✅ commit $(git rev-parse --short HEAD)"
fi
git push -q origin main && echo "✅ push main"

bash scripts/pasang-backend.sh $BASE $FILES

echo "⏳ cek backend sehat…"
for i in $(seq 1 30); do
  sudo -n docker exec kasira-backend-1 python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=3)" 2>/dev/null && break
  sleep 2
done
code=$(sudo -n docker exec kasira-backend-1 python -c "
import json,urllib.request
r=urllib.request.Request('http://127.0.0.1:8000/api/v1/auth/password/login',data=json.dumps({'username':'tidakada-cek-rilis','password':'x'}).encode(),headers={'Content-Type':'application/json'})
try: urllib.request.urlopen(r,timeout=10); print(200)
except Exception as e: print(getattr(e,'code','ERR'))")
[ "$code" = 401 ] || { echo "❌ login tanpa username toko balas $code (harus 401). Frontend TIDAK dipasang."; exit 1; }
echo "✅ backend baru jalan (login tanpa username toko = 401 untuk akun tak dikenal)"

sudo -n docker tag kasira-frontend:latest selaris-frontend-before-masuk:20261009 2>/dev/null || true
sudo -n docker compose build frontend
sudo -n docker compose up -d --no-deps frontend
echo "✅ frontend terpasang. Rollback web: docker tag selaris-frontend-before-masuk:20261009 kasira-frontend:latest && docker compose up -d --no-deps frontend"
