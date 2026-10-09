#!/usr/bin/env bash
# Rilis 9 Okt 2026: kunci Voyage khusus Selaris + pemutus 1 jam + /privacy.
#
#   bash scripts/rilis-voyage.sh
#
# Kunci diketik di terminal (tidak tampil, tidak masuk log/riwayat), dialirkan
# lewat stdin ke /app/secrets/voyage.key (600) di container yang ada, dan
# menggantikan VOYAGE_API_KEY lama di .env untuk recreate kelak.
set -euo pipefail
cd /var/www/kasira
BASE=4289444
FILES="backend/services/embedding_service.py"
WEB="app/privacy/page.tsx"

# Dua cara memberi kunci, keduanya tanpa menampilkan nilainya:
#   - terminal SSH biasa: diminta lewat isian tersembunyi;
#   - tanpa terminal (mis. awalan ! di Claude Code): dari ~/.selaris-voyage.key,
#     yang dihapus setelah terpasang.
KEYFILE="$HOME/.selaris-voyage.key"
if [ -t 0 ]; then
  read -rsp "Tempel kunci Voyage untuk Selaris lalu Enter: " KEY; echo
elif [ -s "$KEYFILE" ]; then
  KEY=$(cat "$KEYFILE")
else
  echo "❌ Jalankan dari terminal SSH, atau simpan kunci di $KEYFILE dulu."; exit 1
fi
KEY=$(printf '%s' "$KEY" | tr -d ' \r\n"'"'"'')
[ ${#KEY} -ge 20 ] || { echo "❌ Kunci terlalu pendek, batal."; exit 1; }

# 1. Uji kunci dulu, sebelum memasang apa pun.
code=$(printf '%s' "$KEY" | sudo -n docker exec -i kasira-backend-1 python -c '
import sys, httpx
key = sys.stdin.read().strip()
r = httpx.post("https://api.voyageai.com/v1/embeddings", timeout=30,
    headers={"Authorization": "Bearer " + key}, json={"model": "voyage-3-lite", "input": ["es kopi susu"], "input_type": "query"})
print(r.status_code, len(r.json()["data"][0]["embedding"]) if r.status_code == 200 else r.text[:120])')
case "$code" in 200\ 512) echo "✅ kunci diterima Voyage (vektor 512)";; *) echo "❌ Voyage menolak: $code"; unset KEY; exit 1;; esac

# 2. Commit + push kode.
if [ -n "$(git status --porcelain -- $FILES $WEB scripts/rilis-voyage.sh)" ]; then
  git add $FILES $WEB scripts/rilis-voyage.sh
  git commit -q -F - <<'MSG'
feat(voyage): kunci khusus Selaris dari berkas, pemutus 1 jam, /privacy menyebut Voyage

- embedding_service.voyage_key(): /app/secrets/voyage.key dulu, env cadangan
  (env container masih memuat kunci lama yang mati sejak 8 Okt).
- Pemutus: 401/403 = embedding dijeda 1 jam, jadi chat Selaris AI tidak lagi
  menunggu panggilan yang pasti gagal.
- /privacy: Voyage AI untuk data pencarian menu.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01BgwEYPmazt9ENyxRjVq5vH
MSG
  echo "✅ commit $(git rev-parse --short HEAD)"
fi
git push -q origin main && echo "✅ push main"

# 3. Kunci ke container + .env (nilai tidak pernah tampil).
printf '%s' "$KEY" | sudo -n docker exec -i kasira-backend-1 sh -c 'umask 077; mkdir -p /app/secrets; cat > /app/secrets/voyage.key'
tmp=$(mktemp); grep -v '^VOYAGE_API_KEY=' .env > "$tmp" || true
printf 'VOYAGE_API_KEY=%s\n' "$KEY" >> "$tmp"; cat "$tmp" > .env; rm -f "$tmp"
unset KEY; rm -f "$KEYFILE"
echo "✅ kunci terpasang (container + .env)"

# 4. Backend + uji lewat fungsi produksi.
bash scripts/pasang-backend.sh $BASE $FILES
for i in $(seq 1 30); do
  sudo -n docker exec kasira-backend-1 python -c "import backend.services.embedding_service" >/dev/null 2>&1 && break
  sleep 2
done
sudo -n docker exec kasira-backend-1 python -c "
import asyncio
from backend.services import embedding_service as e
assert e.is_available(), 'kunci tidak terbaca'
v = asyncio.run(e.embed_query('es kopi gula aren'))
assert len(v) == 512, len(v)
print('✅ Selaris memakai kunci baru (embed_query 512)')"

# 5. Halaman privasi.
sudo -n docker tag kasira-frontend:latest selaris-frontend-before-voyage:20261009 2>/dev/null || true
sudo -n docker compose build frontend
sudo -n docker compose up -d --no-deps frontend
echo "✅ selesai. Rollback web: docker tag selaris-frontend-before-voyage:20261009 kasira-frontend:latest && docker compose up -d --no-deps frontend"
