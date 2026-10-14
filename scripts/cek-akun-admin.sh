#!/usr/bin/env bash
# Baca saja: siapa admin platform Selaris (SUPERADMIN_PHONES) + akun pemilik.
# Tidak menampilkan password/PIN/hash. Tidak mengubah apa pun.
set -euo pipefail

echo "== Nomor di SUPERADMIN_PHONES (container backend) =="
PHONES=$(sudo docker exec kasira-backend-1 printenv SUPERADMIN_PHONES || true)
echo "${PHONES:-(kosong)}"
echo

LIST=$(echo "$PHONES" | tr ',' '\n' | sed 's/[^0-9]//g' | grep -v '^$' | sed "s/.*/'&'/" | paste -sd, -)
[ -z "$LIST" ] && LIST="''"

sudo docker exec -i kasira-db-1 psql -U kasira -d kasira_db -P pager=off <<SQL
\echo '== Akun yang nomornya admin platform / is_superuser / Google muhivan =='
select u.full_name, u.phone, u.login_username, u.google_email,
       u.is_superuser, u.is_active, t.name as toko, r.name as jabatan,
       u.password_hash is not null as ada_password,
       u.google_uid is not null as bisa_google,
       u.created_at::date as dibuat
from users u
join tenants t on t.id = u.tenant_id
left join roles r on r.id = u.role_id
where u.deleted_at is null
  and (u.phone in ($LIST) or u.is_superuser or u.google_email ilike 'muhivan%')
order by u.created_at;
SQL
