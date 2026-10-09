#!/usr/bin/env bash
# Deploy fitur hapus akun (commit e71c330) + Laporan mode Resep ke backend + frontend produksi.
# Pola SELARIS: docker cp ke container backend existing (JANGAN recreate image),
# restart = alembic upgrade head (migrasi 116), frontend --no-deps.
#   bash scripts/deploy-hapus-akun-20261009.sh
set -euo pipefail
cd /var/www/kasira
B=/tmp/selaris-hapus-akun-backup-20261009
CHANGED="backend/api/api.py backend/main.py backend/models/tenant.py backend/services/access.py backend/api/routes/reports.py"
NEW="backend/api/routes/account_deletion.py backend/services/account_deletion.py backend/migrations/versions/116_account_deletion.py"
D() { sudo -n docker "$@"; }

[ "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)" ] || { echo "❌ HEAD belum sama dengan origin/main"; exit 1; }
echo "== preflight: file live harus sama dengan sebelum perubahan"
for f in $CHANGED; do
  [ "$(D exec kasira-backend-1 sha256sum /app/$f | cut -d' ' -f1)" = "$(git show e71c330~1:$f | sha256sum | cut -d' ' -f1)" ] \
    || { echo "❌ $f di container beda dari git (ada hotfix?), berhenti"; exit 1; }
done
n=$(D exec kasira-db-1 psql -U kasira kasira_db -Atc "select count(*) from hpp_setup_sessions where pending_request is not null and pending_until > now()")
[ "$n" = 0 ] || { echo "❌ ada $n HPP pending, coba lagi sebentar"; exit 1; }

echo "== backup file live ke $B"
mkdir -p $B
for f in $CHANGED; do mkdir -p $B/$(dirname $f); D cp kasira-backend-1:/app/$f $B/$f; done
D inspect kasira-backend-1 --format '{{.Image}}' > $B/image.txt
D tag kasira-frontend:latest selaris-frontend-before-hapus-akun:20261009

echo "== pasang backend"
for f in $CHANGED $NEW; do D cp $f kasira-backend-1:/app/$f; done
for f in $CHANGED $NEW; do
  [ "$(D exec kasira-backend-1 sha256sum /app/$f | cut -d' ' -f1)" = "$(sha256sum $f | cut -d' ' -f1)" ] || { echo "❌ hash $f"; exit 1; }
done
D restart kasira-backend-1 >/dev/null
for i in $(seq 1 60); do
  [ "$(D inspect kasira-backend-1 --format '{{.State.Health.Status}}')" = healthy ] && break; sleep 3
done
[ "$(D inspect kasira-backend-1 --format '{{.State.Health.Status}}')" = healthy ] || { echo "❌ backend tidak healthy. Rollback: copy $B lalu hapus 3 file baru, restart"; exit 1; }
echo "migrasi: $(D exec kasira-db-1 psql -U kasira kasira_db -Atc 'select version_num from alembic_version')"

echo "== build + pasang frontend"
D compose build frontend >/tmp/selaris-hapus-akun-frontend-build.log 2>&1 || { echo "❌ build frontend, lihat /tmp/selaris-hapus-akun-frontend-build.log"; exit 1; }
D compose up -d --no-deps frontend >/dev/null 2>&1
for i in $(seq 1 60); do
  [ "$(D inspect kasira-frontend-1 --format '{{.State.Health.Status}}')" = healthy ] && break; sleep 3
done
echo "frontend: $(D inspect kasira-frontend-1 --format '{{.State.Health.Status}}')"
D ps --format '{{.Names}} {{.Status}}' | grep kasira
echo "✅ selesai. Rollback backend: $B. Rollback frontend: selaris-frontend-before-hapus-akun:20261009"
