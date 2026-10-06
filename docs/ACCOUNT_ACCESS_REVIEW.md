# Akun username dan akses tim Selaris

Tanggal: 6 Oktober 2026. Dokumen ini merekam source dan QA tahap akun. Setelah Ivan meminta deployment/rilis, backend/web dan APK 1.6.32+199 dipublikasikan; [review deployment](ACCOUNT_ACCESS_RELEASE.md) menjadi acuan status produksi terbaru.

Owner dapat mendaftar dengan username toko dan password, memakai akun bisnis yang sama di web dan APK, serta memigrasikan akun lama tanpa mengganti UUID, nomor telepon, tenant atau hubungan transaksi. Owner mengatur jabatan HRIS, outlet dan akun individual karyawan. Perubahan password, aktivasi ulang, perubahan akun dan penonaktifan profil staf mencabut sesi terdahulu. Mengaktifkan profil kembali memerlukan login baru.

Tahap ini melanjutkan [fondasi akses server](ACCESS_REVIEW.md) dan [rencana akun dan absensi](ACCOUNT_ACCESS_ATTENDANCE_PLAN.md). Jabatan baru hanya mendukung izin HRIS. POS, sync, Keuangan, Pembelian, CRM, AI/HPP dan Dapur tetap ditolak untuk mode managed sampai integrasi domain selesai. Akun legacy yang diberi username tanpa mengganti jabatan mempertahankan aturan akses legacy.

## Kontrak dan penyimpanan

| Jalur | Perilaku |
| --- | --- |
| `POST /auth/password/register` | Owner, tenant, brand, outlet dan kategori awal dibuat dalam satu transaksi; UUID request dan fingerprint mencegah bisnis ganda saat retry/race. |
| `POST /auth/password/login` | Username toko global dan username akun dalam tenant; owner memakai `owner`. Pesan gagal generik, pembatasan Redis atomik per identitas dan sumber permintaan. |
| `POST /auth/password/claim` | Owner dengan login legacy baru, atau password saat ini jika sudah ditetapkan; mempertahankan identitas lama dan mengakhiri sesi terdahulu. Username yang sudah ditetapkan tidak diubah melalui jalur ini. |
| `POST /auth/password/challenge` | Aktivasi staf sekali pakai, berlaku 24 jam; pemulihan owner sekali pakai, berlaku 365 hari, diganti setelah dipakai. Retry identik hanya berhasil selama versi kredensial masih sesuai. |
| `GET /auth/account`, `GET /auth/sessions` | Identitas login dan daftar sesi sendiri; tidak memberikan hash, token atau sesi orang lain. |
| `DELETE /auth/logout` | Mencabut sesi perangkat saat ini. Token legacy tanpa identitas sesi dicabut secara individual melalui Redis. |
| `POST /auth/sessions/revoke-all` | Mencabut semua sesi pengguna, menaikkan versi kredensial dan mencatat audit atomik. |
| `GET /hris/access/setup` | Hanya owner aktual; akun, profil, jabatan dan outlet dalam tenant sendiri. Delegasi pengaturan akun belum dibuka. |
| `POST /hris/access/roles` | Jabatan dengan izin HRIS StrictBool dan outlet aktif milik tenant; UUID/version/audit, tanpa mengedit jabatan sistem/legacy. |
| `POST /hris/employees/{id}/account` | Buat atau tautkan username staf dengan pemeriksaan versi profil/akun, status, role dan outlet utama; akun owner dilindungi. |
| `POST /hris/employees/{id}/activation` | Owner membuat kode pribadi, menghapus password lama dan mencabut sesi staf; password dibuat sendiri oleh karyawan. |

Password baru memakai PBKDF2-SHA256 600.000 iterasi, panjang 12 sampai 128 karakter; PIN tetap hash terpisah. Server menyimpan hash kode challenge, bukan kode mentah. Audit menyimpan metadata hasil dan fingerprint HMAC, tidak menyimpan password, kode, JWT atau hash password. JWT login baru membawa `sid`, `cv` dan `iat`; server memeriksa hash token sesi, masa berlaku, tenant, status dan versi kredensial.

JWT legacy tanpa `sid` hanya diterima pada versi kredensial nol. Login OTP/Google dan PIN Dapur menghasilkan sesi baru melalui helper bersama; alur registrasi legacy tetap kompatibel. Google dan OTP tersedia melalui halaman masuk akun lama untuk migrasi, bukan pilihan utama pendaftaran baru. Penautan nomor terverifikasi dan pemulihan password baru melalui OTP belum dibuat.

Migrasi 114 melengkapi tabel `sessions` existing, menambah identitas username/password dan `account_challenges`, serta mengganti policy sesi lama dengan tenant langsung. Foreign key tenant/user dan FORCE RLS mencegah sesi/challenge tertaut ke tenant lain. `phone` nullable mendukung akun tanpa nomor. Downgrade menolak sebelum mengubah schema apabila masih ada akun tanpa nomor; pemulihan harus menggunakan nomor terverifikasi yang sebenarnya, bukan nomor buatan.

## Web dan native

Web memiliki login, registrasi, aktivasi, pemulihan, pengaturan akun/perangkat dan editor akun/jabatan HRIS. Cookie sesi httpOnly disimpan server; JWT tidak dikembalikan ke komponen client. Owner dapat memakai web dahulu dan melewati ajakan APK pada onboarding existing. Staf managed diarahkan ke HRIS dan tidak melihat navigasi domain yang belum didukung. Form menyediakan validasi, loading, error dan retry; logout gagal tetap mempertahankan sesi lokal dan menampilkan cara mencoba lagi.

APK source memakai login password yang sama, registrasi, aktivasi/pemulihan dan halaman tim untuk profil serta punch online sendiri. Pengelola memakai web untuk editor tim lengkap. Pergantian identitas memakai UUID user/tenant/mode, termasuk saat nomor kedua akun sama-sama kosong. PIN dan cache sesi lama dibersihkan, sync berjalan dibatalkan melalui service existing, sedangkan SQLite dan antrean transaksi dipertahankan. Permintaan punch yang belum pasti disimpan per tenant/user dan memakai UUID yang sama setelah halaman dibuka ulang.

PIN online memeriksa akses server sebelum masuk. Perangkat sepenuhnya offline tetap mengikuti perilaku POS existing; pencabutan server tidak dapat sampai seketika. Masa izin offline dan penanganan antrean setelah pencabutan belum ditetapkan. GPS/foto, payroll dan seluruh jalur AI belum ditambahkan dalam tahap ini.

## Validasi

Semua database QA memakai salinan schema saja dan data sintetis, role app PostgreSQL NOSUPERUSER/NOBYPASSRLS, jaringan Docker internal tanpa port publik. Fixture browser tidak memanggil OTP, Google atau provider AI. Tidak ada write merchant.

| Pemeriksaan | Hasil dan bukti |
| --- | --- |
| Backend unit | 59 test: 58 PASS, satu skip fixture Google DB khusus; `/tmp/selaris-account-unit-final.log`. |
| HTTP akun dengan DB/JWT asli | Enam kelompok PASS: registrasi race/replay, identitas lintas client, recovery/aktivasi sekali pakai, scope role, status HRIS, migrasi UUID, reauthentication, logout perangkat/semua, RLS dan audit; `/tmp/selaris-account-qa-http-final.log`. |
| Regresi akses | Delapan kelompok PASS pada source final, termasuk reaktivasi yang menolak JWT lama dan login Google fixture baru, izin/scope/replay dan domain legacy; `/tmp/selaris-account-access-regression-final.log`. |
| Redis asli | 20 percobaan serentak, 12 diterima dan delapan dibatasi, kedua TTL valid; `/tmp/selaris-account-rate-qa.log`. |
| Migrasi | Upgrade/downgrade/upgrade 114 PASS sebelum akun tanpa nomor dibuat; guard downgrade setelah akun tanpa nomor dibuat menolak dan mempertahankan schema; `/tmp/selaris-account-migration-roundtrip.log`, `/tmp/selaris-account-downgrade-guard.log`. |
| Browser hasil production build | Empat halaman auth pada 320/375/768/1440 px, light/dark: 32 pemeriksaan overflow/kontras, alur akun dan HRIS, pembesaran teks 200%, keyboard dan tanpa pageerror; `/tmp/selaris-account-browser-production.log`. |
| Native | 13 test akun/login/onboarding PASS; mencakup pergantian UUID dengan nomor kosong, form 320 px pada teks 160%, dan punch tidak pasti yang diulang sesudah membuka ulang; `/tmp/selaris-account-native-test-final.log`. |
| Analyzer native | Tujuh file diperiksa, tanpa error; satu info existing `withOpacity` pada PIN lama; `/tmp/selaris-account-native-analyze-final.log`. |
| Build | Next production build dan Flutter debug APK PASS; `/tmp/selaris-account-web-build-final.log`, `/tmp/selaris-account-debug-apk-final.log`. |

Build web QA memakai respons font offline yang menunjuk berkas font asli dari frontend existing karena DNS Google Fonts tidak tersedia. Source font tidak diubah. Saat tahap QA ini, APK hanya artifact debug lokal dan produksi masih 1.6.31+198. Deployment berikutnya memakai Docker production build dan CI signed APK/AAB 1.6.32+199; rincian ada pada review deployment. Pengujian perangkat fisik belum dilakukan. Jangan recreate image backend lama karena hotfix existing dipasang melalui `docker cp`.

Preview, database/Redis dan jaringan QA sudah dihentikan/dihapus. Salinan schema, harness adaptasi, mock dan salinan font sementara dibersihkan; log/screenshot dan APK debug lokal disimpan. Inspect read-only backend produksi tetap `running healthy`.

## Arah visual dan alasan

Arah mengikuti source Selaris existing: warm neutral, charcoal dan coral, Source Sans 3 untuk form, Source Serif 4 pada shell auth, serta monospace hanya untuk kode yang harus disalin. Form satu kolom mengurutkan identitas, kredensial dan satu tindakan utama; panel HRIS dipisah menurut akun owner, jabatan dan akun karyawan. Spasi mengelompokkan pekerjaan, bukan mengisi halaman. Coral menandai tindakan utama; error memakai token danger. Border/radius mengikuti komponen existing dan tidak menambah dekorasi, ilustrasi atau aset.

ENERGY 2 / RHYTHM 2 / MOTION 1 mengikuti arah Selaris yang dipakai pada awal pekerjaan: fokus utama jelas, kelompok form berbeda dan interaksi tenang. Heading serif pada auth serta tombol coral menjadi motif yang berulang; editor operasional tetap memakai heading sans existing. Ikon kembali/logout/menu/theme mengacu pada tindakan sebenarnya, bukan klaim fitur baru. Tidak ada animasi dekoratif.

## Delivery Gate antislop

Gate ini berlaku pada UI akun yang ditambahkan dan perubahan navigasi/sesi terkait. Bukti fungsional adalah browser hasil build, widget native dan pemeriksaan handler; pengujian perangkat fisik tidak diklaim.

- R-02 PASS: copy UI baru tidak memakai em dash.
- R-03 PASS: 32 kombinasi halaman/ukuran/tema tanpa overflow; editor 320 px dan teks 200%, widget native 320 px dengan teks 160% lulus.
- R-17 PASS: tidak menambah statistik pemasaran; data tim dan sesi datang dari server.
- R-18 PASS: tidak ada testimonial.
- R-23 PASS: menggunakan logo/font/aset Selaris existing; navigasi akun dan staf mengikuti pekerjaan akses yang diotorisasi.
- R-24 PASS: tautan login/register/activate/recover/legacy/account/HRIS memiliki halaman nyata dan dibuka dalam QA.
- R-25 PASS: sampel teks/kontrol pada seluruh auth light/dark dan panel akun HRIS memenuhi AA 4.5:1 normal atau 3:1 besar dalam browser.
- R-26 PASS: submit, checkbox, select, theme, retry, kode dan logout mempunyai handler; jalur server diuji dengan UUID/version yang nyata.
- R-27 PASS: akun belum ditetapkan, belum ada sesi/profil, loading, validasi, kegagalan permintaan dan retry mempunyai tampilan.
- R-28 PASS: tidak menambahkan FAQ.
- R-32 PASS: form native/web memakai label dan kontrol standar; Tab memindahkan fokus, source focus-visible existing dipertahankan, menu memakai Escape.
- R-33 PASS: fitur ditulis dalam source; mock font hanya konfigurasi build QA sementara.
- R-34 PASS: toggle mengubah tema dan 32 pemeriksaan auth serta editor light/dark lulus.
- R-35 PASS: build web/APK dijalankan; rekaman interaksi tercatat di bawah dan log QA.
- R-36 PASS: tidak menambahkan klaim keamanan/kinerja/sertifikasi; hash, rate limit dan pencabutan didukung uji server.
- R-37 PASS: arah mengikuti Selaris existing dan Design Read sebelum UI; dial 2/2/1 dinyatakan.
- R-38 PASS: tidak ada fitur/statistik/tim fiktif dalam product; fixture hanya data QA lokal.
- R-01 PASS: tidak menambah gradient atau glow.
- R-04 PASS: ikon existing logout/menu/theme dan panah kembali native menyatakan tindakan langsung.
- R-06 PASS: font mengikuti brand; monospace kode membantu penyalinan, bukan heading dekoratif.
- R-07 PASS: tidak menambah grid/dot background.
- R-08 PASS: tidak menambah panah dekoratif pada CTA.
- R-09 PASS: tidak menambah capsule badge pemasaran.
- R-10 PASS: tidak menambah glassmorphism.
- R-12 PASS: tidak menambah shadow besar; panel mengikuti border existing.
- R-13 PASS: tidak menambah glow.
- R-14 PASS: panel terpisah karena tugas akun/jabatan/karyawan, bukan feature cards seragam.
- R-19 PASS: loading dan disabled membantu status permintaan; tidak menambah animasi template.
- R-22 PASS: tidak menambah ilustrasi.
- Liveliness dials PASS: ENERGY 2 / RHYTHM 2 / MOTION 1 tercatat dan diterapkan melalui satu CTA, grouping form dan interaksi tenang.
- Liveliness consistency PASS: halaman auth satu langkah dominan; editor memisahkan tiga pekerjaan, tanpa motion dekoratif.
- Liveliness focal point PASS: heading dan submit tindakan aktif; kode recovery mengganti form setelah berhasil.
- Liveliness whitespace PASS: jarak antarfield dan panel memisahkan identitas, kredensial dan penugasan.
- Liveliness accent PASS: coral pada tindakan utama; warna status hanya untuk hasil/error.
- Liveliness identity PASS: shell auth serif, form sans dan CTA coral mengulang motif Selaris.
- Liveliness Design Read PASS: arah sumber dan dial diumumkan sebelum penulisan UI.
- C-1 PASS: warna, font, form, spacing dan panel mempunyai alasan pekerjaan di bagian arah visual.
- C-2 PASS: kontrol baru memiliki tindakan dan kontrak server; tidak ada tombol placeholder.
- C-3 PASS: tiap panel melayani kredensial, sesi, jabatan atau akun staf; tanpa section pemasaran.
- C-4 PASS: browser light/dark/mobile/200%, error/retry dan widget native diperiksa; batas uji fisik tercatat.
- C-5 PASS: tidak menambah testimonial, statistik atau klaim tanpa bukti.
- R-05 PASS: komposisi mengikuti urutan pekerjaan akun, tanpa template hero/bento/pricing.
- R-11 PASS: field, panel dan tombol memakai radius existing; tidak semua elemen berbentuk pill.
- R-15 PASS: CTA menyebut Masuk ke usaha, Simpan jabatan, Buat akun karyawan atau Simpan password.
- R-16 PASS: tidak menambah buzzword pemasaran.
- R-20 PASS: identitas visual mengikuti shell dan komponen Selaris, bukan template brand asing.
- R-21 PASS: light dan dark tersedia melalui toggle existing, tidak memaksa dark.
- R-29 PASS: warm neutral/charcoal/coral dan warna status existing.
- R-30 PASS: tidak meniru layout produk lain.
- R-31 PASS: alasan setiap keputusan besar tertulis pada bagian arah visual.

Rekaman interaksi: registrasi menolak konfirmasi berbeda dan menampilkan kode; checkbox menyimpan kode membuka onboarding; login salah menampilkan error; pilihan karyawan membuka username pribadi dan menuju HRIS; URL domain terlarang menampilkan penolakan. Owner menetapkan username/password tanpa bisnis baru, menyimpan kode, mengganti password, membuat dan mengedit jabatan, memilih outlet/izin, membuat dan menyimpan akun staf, serta membuat/menutup kode aktivasi. Aktivasi salah ditolak dan kode benar menuju HRIS. Pemulihan mengganti password dan menampilkan kode pengganti. Muat ulang setup/akun berhasil setelah fixture gagal; logout gagal mempertahankan cookie dan retry berhasil; login legacy OTP menuju dashboard; keluar semua perangkat kembali ke login. Theme mengubah tampilan, pembesaran teks tidak overflow dan Tab memindahkan fokus. Widget native memvalidasi form, mempertahankan antrean saat UUID berubah dan mengulangi punch dengan UUID yang sama sesudah timeout/buka ulang.

## Berikutnya

Integrasikan izin domain dan seluruh jalur AI, termasuk konteks/cache/history/RAG/worker dan tindakan write, sebelum membuka hak POS/AI pada jabatan baru. Setelah itu lanjut kebijakan absensi GPS/foto native sesuai pengaturan owner. Keputusan OTP pemulihan, masa izin offline, radius/mutu GPS dan retensi bukti masih mengikuti rencana; jangan menganggap rincian tersebut sudah diputuskan atau live.
