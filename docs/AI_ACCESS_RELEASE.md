# Deployment tahap 3 AI dan minimum password

6 Oktober 2026. Ivan melanjutkan tahap 3 dengan “gas”, lalu meminta minimum username/password lebih pendek. Otorisasi deploy/rilis sebelumnya tetap berlaku. Backend/web **live**, schema **115**, APK POS/Dapur **1.6.34+201**, update opsional. Minimum username **3**, password baru **8** di API/web/native; login akun lama tetap menerima password existing. Review [AI_ACCESS_REVIEW.md](AI_ACCESS_REVIEW.md), Delivery Gate [AI_ACCESS_GATE.md](AI_ACCESS_GATE.md).

## Source dan pemasangan

- Runtime backend/frontend dari `4f30484ff7b92d55369300283c2f3ed87370774c`; metadata CI `07d8fdf3d4ee2466dc5150c97b9c6bdea9812d0f` diambil fast-forward sebelum build frontend terakhir. SHA remote main diverifikasi.
- Backup privat `/tmp/selaris-ai-access-release-backup`: DB custom tervalidasi `pg_restore --list`, seluruh 310 Python source/hotfix baseline dan hashes, metadata image/version serta APK lama.
- Preflight seluruh source live cocok backup; sembilan source existing diganti dan dua baru dipasang lewat `docker cp` ke backend existing. Migrasi115 menambah `hpp_setup_sessions.access_version`. Tidak ada HPP pending aktif sebelum migrasi/restart. Seluruh312 hash source live cocok expected, termasuk301 source lain yang dipertahankan.
- Backend image tetap `sha256:160766c62c58c2be22ea7893461d77951b46d70289904fd1e4920ad9ac5fd31a`; tidak recreate image lama. DB/Redis tidak direstart.
- Frontend final `sha256:742368c98bb327cf842dcd84e8521337e75e28b9da0d08803a09d5a93d7b66e2`, build metadata1.6.34. Delapan belas source frontend/version cocok hash dengan source reviewed. Image diuji di localhost dengan fixture sintetis lalu dipasang memakai frontend-only `compose up -d --no-deps`; mount APK tetap.
- Empat service healthy; health backend database/background healthy. QA tidak mengubah akun, password, profil, transaksi atau stok merchant.

## APK

[CI #201](https://github.com/muhivan752/Kasira-OS-Intelligence/actions/runs/37473100415) sukses dari `85abad53ef6648b5809ece5f2d2a4b0e26198b34`. Diff `kasir_app` dan workflow terhadap source07d8fdf kosong; commit berikutnya hanya memperbaiki web/backend dan metadata. Analyze dan enam critical native suites CI lulus. [Release v1.6.34](https://github.com/muhivan752/Kasira-OS-Intelligence/releases/tag/v1.6.34) berisi empat artifact:

| Artifact | Byte | SHA-256 |
| --- | ---: | --- |
| POS APK | 74405472 | `9b28d42e4641e3122320eb182e2b5c9b3e7a87b43254004711371bd4f4e65e45` |
| POS AAB | 70316914 | `dfc8da241573c23924d8c7f79a40556e9216f500b8617825c7421234afa5e4f6` |
| Dapur APK | 63148672 | `3e214088312608882edc55faf00d7e216e4d0be10109e39946fa1a25c80178b4` |
| Dapur AAB | 61008920 | `137494bd916ff8cc89ef046378ac106cf845d3e49a1dbdcf023f51ae35e7e32f` |

Package `com.selaris.pos`/`com.selaris.dapur`, versionName1.6.34/versionCode201, INTERNET dan Firebase resources valid. APK/AAB signatures diverifikasi; signer SHA256 `2f4902808f50548ba23c94c2db122d01e9054d2ed182181d1db5220a14ab248c` sama dengan APK existing dan bukan debug. Ukuran/digest empat artifact cocok GitHub. Host APK diganti rename atomik, backend version.json dipasang atomik, `is_mandatory=false`. Tidak mengklaim APK sudah dipasang di HP Ivan.

## Verifikasi

- Sepuluh kelompok isolated HTTP/JWT/PostgreSQL/FORCE RLS PASS: grants/IDs/tenant/outlet, permission-filtered facts, pgvector retrieval nyata, cache/history akun+versi, HPP draft/approve terpisah, fingerprint/replay/atomic write, worker revoke sebelum/sesudah provider, sid/cv revoke, OCR dan owner compatibility. Provider palsu; tanpa API berbayar.
- Backend64 tests:63 PASS, satu optional skip. Business tahap2 dan HPP regression PASS, termasuk long12-turn history, math/provenance, atomic rollback/concurrent approval/pending lease dan real HTTP202 sebelum provider selesai. Enam legacy suites finance/purchasing/customers/accounts/HPP math21/catalog5 PASS.
- Migration115 upgrade/downgrade/upgrade di synthetic DB PASS. TypeScript dan Docker production build final PASS. Empat native account tests PASS. Flutter analyze mencatat232 issue existing (0 error, empat warning); bukan klaim analyzer bersih.
- AI browser pada image final PASS: navigation, cookie outlet/link/action, SSE multi-turn, reset percakapan, draft-only review dan foreground revocation. HPP manual diuji ulang image final PASS. HPP chat penuh PASS pada build feature identik; tujuh browser regression suites pada build feature PASS dengan hash file terdampak yang sama. Mobile320/768/1024/1440, HPP lima lebar, light/dark, WCAG teks AA,44px,200%, keyboard/dialog/errors/pending/replay diuji.
- Smoke HTTPS publik24 keadaan login/register/activate/recover, keyboard/individual username/legacy/download tanpa pageerror. Form minimum3/8 cocok. API minimum3/8 dikonfirmasi dengan register body yang sengaja tidak lengkap, selalu422 dan tidak membuat akun;7 password/2 username ditolak validasi.
- Dua puluh tiga endpoint protected menolak tanpa kredensial dengan JSON API401, termasuk AI/HPP/OCR. Kedua unduhan APK HTTPS cocok SHA256, ukuran dan Content-Length. API versi POS/Dapur, label download dan domain legacy1.6.34. Empat service dan DB/background sehat.
- QA preview, tiga container synthetic backend/DB/Redis dan network tugas dihentikan. Tidak menghapus resource layanan lain. Belum uji perangkat fisik.

Bukti lokal `/tmp/selaris-ai-*`: `access-qa-final.log`, `backend-unit.log`, `business-hpp-regressions.log`, `legacy-regressions.log`, `migration-roundtrip.log`, `typescript-final.log`, `accounts-native.log`, `flutter-analyze.log`, `frontend-build-version.log`, `access-browser-version.log`, `hpp-chat-browser-final.log`, `hpp-browser-version.log`, `browser-regressions.log`, `frontend-manifest.json`, `backend-scope.json`, `live-backend-hashes.json`, `live-state.json`, `deploy-backend.log`, `deploy-frontend.log`, `ci-final.json`, `artifact-manifest.json`, `artifact-verification.log`, `install-artifacts.log`, `public-password-minimum.json`, `public-smoke.json`, `public-browser.log`, trace dan screenshot. Backup memakai prefix `/tmp/selaris-ai-access-release-backup`.

## Rollback dan batas

Rollback source backend: kembalikan sembilan existing file dari backup, hapus dua file baru sesuai scope manifest dan restart setelah memeriksa pending HPP. Column115 nullable boleh ditinggalkan untuk rollback source; jangan downgrade atau restore DB atas transaksi merchant berjalan tanpa rencana terpisah. Backend harus tetap membawa301 hotfix lainnya.

Snapshot image frontend tahap2 tidak tersedia: daemon melaporkan content digest lama hilang saat mencoba snapshot container. Rollback web memerlukan rebuild source `f137427` dengan version.json1.6.33 dari backup lalu frontend-only deploy. APK dan metadata lama tersedia di backup untuk rollback atomik bila diperlukan.

Native managed AI tetap mengikuti pembatasan navigasi existing. Web AI memerlukan Pro aktif dan izin akun; chat managed tidak menulis stok atau apply menu massal. GPS/foto absensi berikutnya, dengan offline/radius/retensi/OTP perlu keputusan sebelum implementasi.
