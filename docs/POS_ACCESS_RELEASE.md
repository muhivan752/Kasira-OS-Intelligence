# Deployment POS/stok/sync dan rilis Selaris 1.6.33

6 Oktober 2026. Ivan memilih langkah 1 melalui “oke lanjut ke 1”; instruksi sebelumnya “deploy dan rilis apk” mengotorisasi deployment dan publikasi.

Backend dan web POS/stok/sync sudah live. APK/AAB POS dan Dapur **1.6.33+200** tersedia pada [release resmi](https://github.com/muhivan752/Kasira-OS-Intelligence/releases/tag/v1.6.33), dibangun dari source `e0947bafcf160405f05fa975cdce86ec53a20f36` melalui [CI #200](https://github.com/muhivan752/Kasira-OS-Intelligence/actions/runs/37458813872). Update opsional, `is_mandatory=false`. Kontrak, batas dan Delivery Gate UI ada di [review POS](POS_ACCESS_REVIEW.md).

## Deployment

- Backup privat `/tmp/selaris-pos-access-release-backup` memuat database custom yang diverifikasi melalui pg_restore, seluruh source/hotfix backend, image frontend dan APK/metadata 1.6.32. SHA256 dump `7a06e12c827776fd5c26b038ff8187db0be626547b694821272b17d39f5cdbae`.
- Preflight membuktikan seluruh Python live cocok dengan backup; tidak ada HPP pending aktif saat restart. Hanya 21 file runtime baru/berubah dicopy ke container backend existing dan direstart. Hash 21 file cocok source; 288 source Python lainnya tetap sama. Backend image `sha256:160766c62c58c2be22ea7893461d77951b46d70289904fd1e4920ad9ac5fd31a` tidak direcreate; migrasi tetap 114.
- Frontend Docker production build dan QA interaksi pada image final PASS. Deployment hanya `compose up -d --no-deps frontend`; image `sha256:3f2b849cf8cbbec550327d358e144686c509f8d50d8d0cf7806e84cfbae433c3`. Dua bind mount APK read-only tetap tersedia. Font fixture dev tidak masuk source/build produksi.
- Keempat artifact diverifikasi sebelum pemasangan: package `com.selaris.pos`/`com.selaris.dapur`, versionName 1.6.33, versionCode 200, APK/AAB signature valid, signer sama dengan rilis existing dan bukan debug. Resource Firebase kedua APK tersedia.
- Ukuran/hash keempat artifact cocok digest resmi GitHub. APK host diganti memakai file sementara, hash check dan rename atomik; metadata backend juga diganti atomik. GET HTTPS `/api/download/pos` dan `/api/download/dapur` cocok ukuran, Content-Length dan hash APK resmi.
- API update POS/Dapur serta label halaman download menunjukkan 1.6.33. Domain API kasira.online tetap tersedia. Backend/frontend/database/Redis healthy; database dan background tasks sehat.

## Verifikasi

| Pemeriksaan | Hasil |
| --- | --- |
| Backend unit | 62 PASS + satu fixture opsional skip. |
| HTTP/JWT/PostgreSQL | Lima kelompok PASS pada schema-only/data sintetis FORCE RLS; izin, scope, harga/tagihan, riwayat, refund, kas, dapur, customer lookup, sync, SSE/FCM dan invarians resep. |
| Native | 45 PASS + dua fixture diagnostik opsional skip; termasuk sepuluh test khusus izin/queue/cache/revocation/refund/dapur/kas. Enam file final analyzer tanpa issue. |
| Web produksi dengan fixture | Tindakan stok, uncertainty lock tanpa retry, empat lebar 320..1440, light/dark, 200% teks, AA contrast, keyboard/error/empty/revoked PASS. |
| CI resmi | Test release, build empat artifact dan signing PASS dari SHA source yang sama. |
| Web publik produksi | 24 keadaan auth/lebar/tema plus fokus/keyboard/username staf/legacy/download; tanpa overflow/pageerror. |
| API publik produksi | Delapan route protected tanpa kredensial ditolak; kode aktual: 401, 401, 401, 401, 401, 401, 401, 401. Tidak write merchant atau memakai JWT owner sintetis. |

| Artifact | Bytes | SHA256 |
| --- | --- | --- |
| `selaris-pos-v1.6.33.apk` | 74405472 | `5785ac7fc0c1d33612e46b6e0c38609ec02c8c5810e4f96cd34a9e7c8ff476d6` |
| `selaris-pos-v1.6.33.aab` | 70316924 | `2f953c2b24f1b5ab9ef807a30630516afee2474bf2d274ee35118b847d7ae8de` |
| `selaris-dapur-v1.6.33.apk` | 63148676 | `31e2245f53fcdace20e1f18a87cfe157cc396ffc5b6e456b4c0768b026dabf2c` |
| `selaris-dapur-v1.6.33.aab` | 61008911 | `a883f4444a0db5cba03f121bfbc7a1d89911568504ea03b032117246c1e7cf3b` |

Bukti lokal: `/tmp/selaris-pos-access-deploy-backend.log`, `*-live-backend-hashes.json`, `*-artifact-manifest.json`, `*-artifact-check.log`, `*-public-smoke.json`, `*-public-browser.log`, `*-production-browser.log`, `*-ci-watch.log` dan `*-release-status.json`, dengan prefix `/tmp/selaris-pos-access`.

## Batas dan kelanjutan

Managed staff memakai POS/stok/sync sesuai grant dan outlet, transaksi online dan sync pull-only. Queue lama, dependency dan retry key dipertahankan; pemilik menyelesaikan antrean lewat alur existing. Legacy offline tetap existing. Simple stock tetap bersama brand, resep per outlet. Dapur pendamping masih login PIN existing; akun username staff memakai workspace POS.

Keuangan/Pembelian/CRM/HPP managed dan seluruh akses AI/cache/history/RAG/worker belum dibuka. Masa izin offline, GPS/foto/radius/retensi perlu keputusan tersendiri. Rilis APK kompatibel dengan signer existing; belum klaim install/uji pada perangkat fisik Ivan. Selanjutnya tahap 2: izin Keuangan/Pembelian/CRM/HPP.
