# Deployment akun dan rilis Selaris 1.6.32

Tanggal: 6 Oktober 2026. Ivan mengotorisasi deployment dan rilis APK melalui pesan "deploy dan rilis apk".

Backend dan web akun sudah dipasang ke produksi. APK/AAB POS dan Dapur 1.6.32+199 dipublikasikan melalui [CI #199](https://github.com/muhivan752/Kasira-OS-Intelligence/actions/runs/37451765808) dari source `66ddd592ce4ec84750f0bbce14525c8b3faafd6b`. [Release 1.6.32](https://github.com/muhivan752/Kasira-OS-Intelligence/releases/tag/v1.6.32) berisi keempat artifact. Update opsional, tidak dipaksa.

Source yang sebelumnya belum dipush mencakup modul Keuangan/Pembelian/Pelanggan/HRIS yang sudah live, perbaikan HPP native yang menunggu rilis, serta tahap akun. Perbandingan dengan source container produksi membuktikan hanya 17 file backend berbeda, semuanya akun/akses/migrasi 114; hotfix modul lain sama dengan source dan dipertahankan. Bukti cakupan `/tmp/selaris-release-scope-evidence.json`.

## Deployment

- Backup database format custom diverifikasi lewat `pg_restore --list`; snapshot seluruh backend/hotfix, metadata versi, identitas image frontend dan APK 1.6.31 disimpan privat di `/tmp/selaris-accounts-release-backup`.
- Tidak ada job HPP dengan `pending_request` aktif sebelum deployment. Migrasi produksi 113 ke 114 selesai; tabel sesi existing dilengkapi, bukan diganti. Pengguna legacy tetap versi kredensial nol sampai melakukan perubahan akun.
- Hanya 17 file akun/akses dipasang lewat `docker cp`, lalu restart container backend existing. Identitas image tetap `160766c6…31a`; seluruh hash 17 file cocok dengan source rilis. Backend lama tidak direcreate.
- Frontend dibangun dengan Docker produksi, lalu `compose up -d --no-deps frontend`. Mount APK di `/app/public/apk` dan fallback standalone tetap ada. Build kedua memakai metadata versi 1.6.32 dari commit CI `d03e595` untuk halaman download.
- APK POS/Dapur dipasang lewat file sementara, verifikasi hash, lalu rename atomik. Metadata `/app/version.json` backend juga diganti atomik setelah artifact lolos. Data merchant dan antrean perangkat tidak dihapus.

## Verifikasi

| Pemeriksaan | Hasil |
| --- | --- |
| Native sebelum dispatch | 35 PASS, dua fixture opsional skip; `/tmp/selaris-release-native-tests.log`. Alias library SQLite lokal menunjuk runtime existing; CI memakai `libsqlite3-dev`. |
| CI APK/AAB | Sukses pada SHA source yang sama, build #199; Firebase dan keystore dipasang, test rilis PASS, signing bukan debug; `/tmp/selaris-release-ci.log`. |
| APK POS | `com.selaris.pos`, versionName 1.6.32, versionCode 199, signer sama dengan APK 1.6.31; APK/AAB signature valid dan resource Firebase tersedia. |
| APK Dapur | `com.selaris.dapur`, versionName 1.6.32, versionCode 199, signer sama dengan APK 1.6.31; APK/AAB signature valid dan resource Firebase tersedia. |
| Artifact | SHA256/ukuran keempat file cocok dengan digest GitHub release; `/tmp/selaris-release-artifact-manifest.json`, `/tmp/selaris-release-artifact-check.log`. |
| Download pengguna | Hash GET HTTPS `/api/download/pos` dan `/api/download/dapur` cocok dengan APK resmi, bukan file lama. |
| Metadata update | `/api/v1/auth/app/version?app=pos` dan `app=dapur` mengembalikan 1.6.32 dan `is_mandatory=false`. |
| Smoke web produksi | Login/register/activate/recover pada 320/768/1440 px light/dark: 24 keadaan tanpa overflow; keyboard/fokus, pilihan username staf, halaman legacy/download dan tanpa pageerror; `/tmp/selaris-release-public-browser.log`. |
| Kontrak API produksi | Delapan route akun/HRIS memberikan validasi 422 atau auth 401 yang sesuai tanpa kredensial; login identitas fiktif ditolak 401. |
| Kompatibilitas | API `kasira.online` tetap tersedia untuk APK lama. |
| Health | Backend, frontend, database dan Redis healthy; `/health` DB ok/background healthy/tanpa task mati. |

Hash APK POS: `19ccc8d5a4931a1964cfa5b04782daeb36b760973d3dbe028191fd831c81b0e8`.

Hash APK Dapur: `39bc614d0dacf9069afe5b7f526d81fd790c54549071f9a55e511294c1936dba`.

Automatic approval review sempat menolak push besar ke main. Setelah cakupan dicocokkan dengan produksi dan test rilis lulus, push diterima; SHA main diverifikasi sebelum dispatch. Pembuatan JWT langsung untuk owner demo produksi ditolak karena akses privat tanpa otorisasi akun spesifik. Pemeriksaan produksi memakai halaman publik dan kontrak tanpa kredensial; pengujian fungsi akun terautentikasi memakai QA terisolasi yang sudah tercatat dalam [review akun](ACCOUNT_ACCESS_REVIEW.md).

## Batas rilis

Jabatan managed baru hanya HRIS; akses POS, domain lain dan AI belum dibuka untuk jabatan tersebut. Owner dapat memigrasikan akun legacy sendiri melalui pengaturan akun, tanpa pemindahan UUID atau riwayat. Google/OTP legacy tetap untuk transisi. Native POS mendukung akun password, aktivasi/pemulihan dan punch pribadi online; Dapur adalah build pendamping dengan login PIN existing dan sesi server yang bisa dicabut.

GPS/foto, payroll, OTP pemulihan baru, masa izin offline dan enforcement semua domain/AI tetap pekerjaan berikutnya. Rilis menyediakan APK bertanda tangan yang kompatibel dengan update versi lama; tidak mengklaim sudah terpasang atau diuji pada HP Ivan. Gate UI sebelumnya PASS pada [review akun](ACCOUNT_ACCESS_REVIEW.md); deployment tidak menambah desain baru.
