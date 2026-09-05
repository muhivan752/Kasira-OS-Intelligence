#!/usr/bin/env bash
# Pasang kunci Firebase (FCM) ke .env dari berkas service account.
#
# Pakai:  ./scripts/pasang_fcm.sh /path/ke/selaris-firebase-adminsdk.json
#
# Berkas itu diunduh dari Firebase Console:
#   Setelan proyek > Akun layanan > Buat kunci pribadi baru
#
# Kenapa perlu skrip: kunci privatnya multi-baris. Ditempel apa adanya ke
# .env, parsernya patah di baris kedua dan SEMUA env sesudahnya ikut hilang.
# Di sini newline-nya diubah jadi \n harfiah, yang dibalikin lagi sama
# `backend/services/fcm.py`.
set -euo pipefail

BERKAS="${1:-}"
ENVFILE="${2:-/var/www/kasira/.env}"

if [ -z "$BERKAS" ] || [ ! -f "$BERKAS" ]; then
  echo "Pakai: $0 <service-account.json> [path .env]" >&2
  exit 1
fi

BACA=$(python3 - "$BERKAS" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
for k in ("project_id", "client_email", "private_key"):
    if not d.get(k):
        sys.exit(f"Berkas ini bukan service account Firebase: '{k}' nggak ada")
print(d["project_id"])
print(d["client_email"])
print(d["private_key"].replace("\n", "\\n"))
PY
)
PROJECT=$(printf '%s\n' "$BACA" | sed -n 1p)
EMAIL=$(printf '%s\n' "$BACA" | sed -n 2p)
KEY=$(printf '%s\n' "$BACA" | sed -n 3p)

cp "$ENVFILE" "$ENVFILE.bak.$(date +%s)"
# Buang nilai lama (kalau ada), lalu tulis yang baru di akhir berkas.
sed -i '/^FCM_PROJECT_ID=/d; /^FCM_CLIENT_EMAIL=/d; /^FCM_PRIVATE_KEY=/d' "$ENVFILE"
{
  echo "FCM_PROJECT_ID=$PROJECT"
  echo "FCM_CLIENT_EMAIL=$EMAIL"
  echo "FCM_PRIVATE_KEY=$KEY"
} >> "$ENVFILE"

echo "Tersimpan di $ENVFILE"
echo "  project : $PROJECT"
echo "  akun    : $EMAIL"
echo "  kunci   : ${#KEY} karakter"
echo
echo 'Env baru butuh BUILD ULANG, `docker restart` nggak muat ulang env:'
echo "  sudo docker compose build backend && sudo docker compose up -d --no-deps backend"
echo "Sesudah itu container di-recreate, jadi berkas hasil \`docker cp\` hilang."
echo "Pasang ulang version.json dan berkas cp lain (gotcha #9)."
