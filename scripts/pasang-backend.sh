#!/usr/bin/env bash
# Pasang file backend ke container produksi, pola SELARIS (docker cp ke
# container existing, JANGAN recreate image). Restart = alembic upgrade head.
#
#   bash scripts/pasang-backend.sh <commit-dasar> <file> [file...]
#
# <commit-dasar>: commit SEBELUM perubahan. File live harus sama dengan versi
# di commit itu (atau belum ada, untuk file baru); kalau beda berarti ada
# hotfix di container yang belum tercatat, dan skrip berhenti.
set -euo pipefail
cd /var/www/kasira
[ $# -ge 2 ] || { echo "Pakai: bash scripts/pasang-backend.sh <commit-dasar> <file>..."; exit 1; }
BASE=$1; shift
D() { sudo -n docker "$@"; }
B=/tmp/selaris-backend-backup-$(date +%Y%m%d-%H%M%S)

[ "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)" ] || { echo "❌ HEAD belum sama dengan origin/main (push dulu)"; exit 1; }
for f in "$@"; do
  case $f in backend/*) ;; *) echo "❌ $f bukan file backend"; exit 1;; esac
  [ -f "$f" ] || { echo "❌ $f tidak ada di repo"; exit 1; }
  if D exec kasira-backend-1 test -e /app/$f; then
    git cat-file -e "$BASE:$f" 2>/dev/null || { echo "❌ $f ada di container tapi tidak di $BASE"; exit 1; }
    [ "$(D exec kasira-backend-1 sha256sum /app/$f | cut -d' ' -f1)" = "$(git show $BASE:$f | sha256sum | cut -d' ' -f1)" ] \
      || { echo "❌ $f di container beda dari $BASE (ada hotfix?), berhenti"; exit 1; }
  fi
done
n=$(D exec kasira-db-1 psql -U kasira kasira_db -Atc "select count(*) from hpp_setup_sessions where pending_request is not null and pending_until > now()")
[ "$n" = 0 ] || { echo "❌ ada $n HPP pending, coba lagi sebentar"; exit 1; }

mkdir -p $B
for f in "$@"; do
  if D exec kasira-backend-1 test -e /app/$f; then mkdir -p $B/$(dirname $f); D cp kasira-backend-1:/app/$f $B/$f; else echo "$f" >> $B/FILE-BARU.txt; fi
done
echo "cadangan: $B"
for f in "$@"; do D cp $f kasira-backend-1:/app/$f; done
for f in "$@"; do
  [ "$(D exec kasira-backend-1 sha256sum /app/$f | cut -d' ' -f1)" = "$(sha256sum $f | cut -d' ' -f1)" ] || { echo "❌ hash $f"; exit 1; }
done
D restart kasira-backend-1 >/dev/null
for i in $(seq 1 60); do
  [ "$(D inspect kasira-backend-1 --format '{{.State.Health.Status}}')" = healthy ] && break; sleep 3
done
[ "$(D inspect kasira-backend-1 --format '{{.State.Health.Status}}')" = healthy ] \
  || { echo "❌ backend tidak healthy. Rollback: salin balik isi $B, hapus file di FILE-BARU.txt, restart"; exit 1; }
echo "migrasi: $(D exec kasira-db-1 psql -U kasira kasira_db -Atc 'select version_num from alembic_version')"
echo "✅ terpasang $# file. Rollback: $B"
