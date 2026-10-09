#!/usr/bin/env bash
# Rilis 9 Okt 2026: pemilik/pengelola bisa menghapus karyawan dari halaman Tim.
#
#   bash scripts/rilis-hapus-karyawan.sh
set -euo pipefail
cd /var/www/kasira
BASE=c89ab5c
FILES="backend/services/hris.py backend/api/routes/hris.py backend/schemas/hris.py backend/services/access.py"
WEB="app/dashboard/hris/page.tsx app/dashboard/hris/hris.css app/actions/hris.ts"

if [ -n "$(git status --porcelain -- $FILES $WEB scripts/rilis-hapus-karyawan.sh)" ]; then
  git add $FILES $WEB scripts/rilis-hapus-karyawan.sh
  git commit -q -F - <<'MSG'
feat(tim): pemilik bisa menghapus karyawan

- POST /hris/employees/{id}/remove (services/hris.remove_employee): akun login
  dikosongkan lewat account_deletion.anonymize_user (rumah yang sama dengan
  hapus akun sendiri), sesi dicabut; profil disembunyikan, HP dikosongkan,
  nama tetap supaya riwayat jadwal/absensi utuh. Ditolak kalau masih ada
  absensi belum pulang. Replay client_request_id + audit seperti HRIS lain.
- Terdaftar untuk jabatan managed; izin dan cakupan outlet lewat
  staff_accounts.target seperti ubah akun.
- Web: tombol Hapus per karyawan + dialog konfirmasi.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01BgwEYPmazt9ENyxRjVq5vH
MSG
  echo "✅ commit $(git rev-parse --short HEAD)"
fi
git push -q origin main && echo "✅ push main"

bash scripts/pasang-backend.sh $BASE $FILES
for i in $(seq 1 30); do
  sudo -n docker exec kasira-backend-1 python -c "from backend.services.hris import remove_employee" >/dev/null 2>&1 && break
  sleep 2
done
# Router API dipasang sebagai sub-aplikasi, jadi cek lewat HTTP: rute ada = 401 (perlu login), bukan 404.
code=$(sudo -n docker exec kasira-backend-1 python -c "
import urllib.request
r = urllib.request.Request('http://127.0.0.1:8000/api/v1/hris/employees/00000000-0000-0000-0000-000000000000/remove', data=b'{}', headers={'Content-Type': 'application/json'}, method='POST')
try: urllib.request.urlopen(r, timeout=10); print(200)
except Exception as e: print(getattr(e, 'code', 'ERR'))")
[ "$code" = 401 ] || { echo "❌ rute hapus balas $code (harus 401). Frontend TIDAK dipasang."; exit 1; }
echo "✅ backend punya rute hapus karyawan"

sudo -n docker tag kasira-frontend:latest selaris-frontend-before-hapus-karyawan:20261009 2>/dev/null || true
sudo -n docker compose build frontend
sudo -n docker compose up -d --no-deps frontend
echo "✅ frontend terpasang. Rollback web: docker tag selaris-frontend-before-hapus-karyawan:20261009 kasira-frontend:latest && docker compose up -d --no-deps frontend"
