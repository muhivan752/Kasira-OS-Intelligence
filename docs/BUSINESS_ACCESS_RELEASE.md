# Deployment tahap 2 akses bisnis

6 Oktober 2026. Ivan “gas tahap 2”, lalu “sorry kepencet lanjut lgi aja”. Otorisasi deploy/rilis sebelumnya tetap berlaku. Implementasi runtime dari source `4f1cd8ff8143d93f4caaa77612cb8699a1eecacc` dipush dan SHA remote diverifikasi sebelum deploy. Review dan Delivery Gate: [BUSINESS_ACCESS_REVIEW.md](BUSINESS_ACCESS_REVIEW.md).

Backend dan web **live**. Tahap ini tidak mengubah kode native atau menerbitkan APK baru; POS/Dapur tetap signed release **1.6.33+200**, update opsional. Tidak ada migrasi database baru; schema tetap **114**. Role lama tidak dimigrasikan otomatis.

## Backup dan pemasangan

- Backup privat `/tmp/selaris-business-access-release-backup`: custom DB dump tervalidasi `pg_restore --list`, seluruh 309 source Python/hotfix, hash baseline, version.json dan image ID sebelum perubahan.
- Preflight mencocokkan seluruh source live dengan backup dan 13 source baru dengan commit. Tidak ada permintaan HPP pending aktif saat restart. Dua belas source existing diganti dan satu modul baru ditambahkan melalui `docker cp` ke container backend existing; 297 source lainnya tetap cocok dengan baseline. Setelah restart seluruh 310 hash source cocok dengan expected.
- Backend image tetap `sha256:160766c62c58c2be22ea7893461d77951b46d70289904fd1e4920ad9ac5fd31a`; container tidak direcreate dari image lama.
- Frontend final dibuild dan diuji sebagai container localhost memakai fixture sintetis. Empat belas source frontend di image cocok byte/hash dengan source reviewed. Image live `sha256:c24faaad5c262ebf148e35052a23e831ffc4a6d0f3a053aa079df81fac079403` dipasang memakai frontend-only compose `up -d --no-deps`; mount APK tetap.
- Empat service healthy; DB/background backend healthy. DB dan Redis tidak direstart. Tidak ada write ke akun, password, profil, transaksi atau data merchant saat QA/smoke.

## Verifikasi

- 64 backend test: 63 PASS, satu fixture opsional skip. Tujuh kelompok HTTP/JWT/PG/FORCE RLS PASS. Regresi SQL finance/purchasing/CRM/accounts dan 21 matematika HPP + 5 katalog PASS; konversi unit web terhadap helper Python PASS.
- TypeScript dan Docker production build final PASS. Tujuh suite browser pada **image final** PASS: managed business, finance, purchasing, customers, HPP, accounts, POS. Termasuk grant baca/tindakan/ekspor terpisah, nominal tersamar, tenant scope editor/assignment, invalid manifest gagal tertutup, revoke, pending replay, lima lebar/dua tema/200% teks/kontras/keyboard.
- Smoke HTTPS publik: 24 keadaan halaman auth (empat route, tiga lebar, dua tema), keyboard, username individu, legacy login dan download tanpa pageerror. Tujuh belas protected endpoint menolak tanpa kredensial dengan JSON API 401, termasuk seluruh domain tahap 2.
- API versi POS/Dapur tetap 1.6.33 opsional. Kedua download HTTPS cocok hash/ukuran/Content-Length artifact signed release sebelumnya. Domain legacy dan health database/background tetap sehat.
- Preview dev dan empat container/network QA milik tugas dihentikan. Log, trace, screenshot dan backup tetap tersedia. Belum uji perangkat fisik; tidak ada perubahan antrean native.

Bukti lokal memakai prefix `/tmp/selaris-business`: `*-qa-http-final.log`, `*-unit-final.log`, `*-legacy-regressions.log`, `*-hpp-units.log`, `*-tsc-final.log`, `*-frontend-build-final.log`, `*-final-{business-access,finance,purchasing,customers,hpp,accounts,pos-access}.log`, `*-managed-trace.zip`, `*-frontend-manifest.json`, `*-backend-scope.json`, `*-live-backend-hashes.json`, `*-live-state.json`, `*-deploy-backend.log`, `*-deploy-frontend.log`, `*-public-smoke.json` dan `*-public-browser.log`.

## Rollback

Tidak ada schema change. Jika perlu rollback kode, copy ulang dua belas file existing dari backup, hapus hanya modul business_access baru, lalu restart backend setelah memeriksa HPP pending. Frontend sebelumnya `sha256:3f2b849cf8cbbec550327d358e144686c509f8d50d8d0cf7806e84cfbae433c3` tetap tersedia. Gunakan container frontend-only; jangan recreate backend dari image lama atau memulihkan DB atas transaksi merchant yang berjalan.

Berikutnya tahap 3 seluruh AI/context/cache/history/RAG/worker/write. Chat HPP dan OCR tetap tertutup untuk managed pada tahap 2. Lease offline/GPS/foto/OTP/radius/retensi tetap keputusan tersendiri.
