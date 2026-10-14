#!/usr/bin/env bash
# Rilis 14 Okt 2026: akun staf jualan offline 12 jam + layar kasir staf sama
# dengan pemilik + jabatan di app (9ec3441). APK POS 1.6.39.
#
#   bash scripts/rilis-staf-offline-1639.sh
#
# Urutan: backend dulu (server menerima kiriman jualan offline staf; APK lama
# staf tidak mengirim apa pun, jadi aman), lalu APK di GitHub Actions
# (GitHub Releases + version.json, update tidak wajib). Web tidak berubah.
set -euo pipefail
cd /var/www/kasira
BASE=617c4fe
VERSION=1.6.39
FILES="backend/services/access.py backend/services/pos_access.py"
NOTES="Akun karyawan bisa berjualan tanpa internet sampai 12 jam sejak terakhir online, transaksinya terkirim sendiri begitu tersambung. Layar karyawan memakai tampilan kasir yang sama dengan pemilik, termasuk di tablet, dan menampilkan jabatan. Kolom pencarian menu lebih rapi."

git fetch -q origin
[ "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)" ] || { echo "❌ HEAD belum sama dengan origin/main"; exit 1; }

# 1. Backend
bash scripts/pasang-backend.sh $BASE $FILES
for i in $(seq 1 30); do
  sudo -n docker exec kasira-backend-1 python -c "import backend.services.pos_access" >/dev/null 2>&1 && break
  sleep 2
done
sudo -n docker exec kasira-backend-1 python -c "
from backend.services.access import OFFLINE_GRACE_HOURS
from backend.services.pos_access import validate_staff_push, STAFF_PUSH_TABLES
assert OFFLINE_GRACE_HOURS == 12 and STAFF_PUSH_TABLES == {'orders', 'order_items', 'payments'}
print('✅ backend: staf boleh kirim jualan offline miliknya, batas 12 jam')" || { echo "❌ backend belum memuat perubahan. APK TIDAK dibangun."; exit 1; }
code=$(curl -s -o /dev/null -w '%{http_code}' -X POST https://selaris.id/api/v1/sync/ -H 'Content-Type: application/json' -d '{}')
[ "$code" = 401 ] || [ "$code" = 403 ] || { echo "❌ /sync/ menjawab $code (harusnya 401/403 tanpa login)"; exit 1; }
echo "✅ /sync/ hidup ($code tanpa login)"

# 2. APK di GitHub Actions
gh workflow run build-apk.yml -f version=$VERSION -f is_mandatory=false -f release_notes="$NOTES"
sleep 8
gh run list --workflow=build-apk.yml --limit 1
echo "✅ build APK $VERSION dimulai di GitHub Actions (sekitar 15 s.d. 25 menit). Pantau: gh run watch"
