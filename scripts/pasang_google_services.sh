#!/usr/bin/env bash
# Perbarui secret GOOGLE_SERVICES_JSON di GitHub dari berkas lokal.
#
# Kapan dipakai: sesudah nambah/ubah app Android di Firebase Console. Sejak
# 11 Sep 2026 APK keluar dengan DUA applicationId (com.selaris.pos dan
# com.selaris.dapur), jadi google-services.json WAJIB memuat dua-duanya.
# Kalau kurang satu, workflow melewati Firebase dan APK keluar tanpa push
# (lihat langkah "Pasang google-services.json" di .github/workflows/build-apk.yml).
#
# Pakai: bash scripts/pasang_google_services.sh /path/google-services.json
set -euo pipefail
FILE="${1:?Pakai: $0 <google-services.json>}"
[ -f "$FILE" ] || { echo "Berkas nggak ketemu: $FILE"; exit 1; }

python3 - "$FILE" <<'PY'
import base64, json, subprocess, sys, urllib.request, urllib.error
from nacl import encoding, public

path = sys.argv[1]
d = json.load(open(path))
paket = [c['client_info']['android_client_info']['package_name'] for c in d['client']]
butuh = ["com.selaris.pos"]
kurang = [x for x in butuh if x not in paket]
print("project :", d['project_info']['project_id'])
print("paket   :", paket)
if kurang:
    print(f"\nBERHENTI: paket {kurang} belum ada di berkas ini.")
    print("Tambahkan app Android itu di Firebase Console dulu, unduh ulang berkasnya.")
    sys.exit(1)
if 'com.selaris.dapur' not in paket:
    print("CATATAN: com.selaris.dapur belum terdaftar. APK Dapur bakal dibangun")
    print("         tanpa notifikasi push. POS tetap dapat push.\n")
else:
    print("dua paket lengkap\n")

tok = open('/home/linuxuser/.git-credentials').read().split(':')[2].split('@')[0]
repo = "muhivan752/Kasira-OS-Intelligence"
api = f"https://api.github.com/repos/{repo}/actions/secrets"

def gh(url, method="GET", body=None):
    req = urllib.request.Request(url, method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": f"token {tok}", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read()
        return r.status, (json.loads(raw) if raw else {})

st, pk = gh(api + "/public-key")
box = public.SealedBox(public.PublicKey(pk["key"].encode(), encoding.Base64Encoder()))
isi = open(path, 'rb').read()
enc = base64.b64encode(box.encrypt(base64.b64encode(isi))).decode()
st, _ = gh(f"{api}/GOOGLE_SERVICES_JSON", "PUT", {"encrypted_value": enc, "key_id": pk["key_id"]})
print(f"secret GOOGLE_SERVICES_JSON diperbarui (HTTP {st})")
PY
