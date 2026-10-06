# KASIRA — Long-Term Memory
# Update ini setiap selesai satu task!

## TERKINI - POS/STOK/SYNC LIVE DAN APK 1.6.33+200 DIRILIS, 2026-10-06

- Ivan “oke lanjut ke 1”; deploy/rilis sebelumnya tetap otorisasi. Source e0947ba
  dipush dan SHA remote diverifikasi. CI #200/run37458813872 sukses; release
  v1.6.33 berisi signed POS/Dapur APK+AAB. Review docs/POS_ACCESS_REVIEW.md
  dan deployment docs/POS_ACCESS_RELEASE.md. Update opsional.
- Backend 21 file runtime dicopy/restart existing; hash baru sesuai source,
  288 source Python lain tetap hotfix baseline. Image backend 160766…31a
  tidak direcreate, migration114 tetap. Frontend-only compose --no-deps,
  image 3f2b849…33c3. Semua service/DB/background healthy.
- Backup privat /tmp/selaris-pos-access-release-backup: DB custom tervalidasi,
  seluruh source/hotfix, image/version/APK1.6.32. Tidak HPP pending saat restart.
  APK dan version.json diganti atomik setelah APK/AAB signature/package/
  build200/Firebase/hash/ukuran lolos; signer sama existing. Download HTTPS
  kedua app cocok hash/Content-Length; API dan label download 1.6.33.
- Managed registry callable+method dan scope parent/outlet/brand/tenant.
  Sell/refund/approve/discount/shift/cash/kitchen/history/stock/lookup terpisah;
  harga/tagihan canonical, biaya/counter/provider/blind drawer direduksi.
  ID path/query/body bertentangan dan parent payment palsu ditolak; invoice
  billing tidak terbuka lewat POS. SSE/FCM hanya event POS sesuai izin.
- Web Operasional: outlet, receive simple/bahan resep, count simple,
  uncertainty lock tanpa retry. Simple stock tetap bersama brand; resep per
  outlet. APK workspace managed kasir/riwayat/shift/kas/refund/dapur; stok web.
- Managed online-only/pull-only; cold manifest/foreground refresh. Cache
  ownership/cursor tenant/user/outlet/access-version memaksa full pull setelah
  switch/revoke/owner roundtrip; semua queue/dependency/retry key tetap dan
  same-ID pending tidak ditimpa. Legacy offline existing, offline lease belum
  dipilih. Dapur PIN existing. Tidak memigrasikan role lama otomatis.
- QA 62 unit +1 skip, lima kelompok HTTP PG/JWT/RLS/SSE/FCM, 45 native +2
  optional skip, sepuluh izin khusus; web image produksi tindakan stok empat
  lebar/tema/200%/kontras/keyboard PASS. Smoke publik 24 auth keadaan,
  download/legacy dan delapan protected route denied tanpa kredensial.
  Tidak write merchant/uji perangkat fisik. QA preview/container/network
  milik tugas dihentikan; artifact/log/backup tetap /tmp/selaris-pos-access*.
- Berikutnya tahap 2 Keuangan/Pembelian/CRM/HPP, lalu seluruh AI/cache/history/
  RAG/worker/write. GPS/foto/OTP/offline/radius/retensi keputusan tersendiri.

## SEBELUMNYA - AKUN LIVE DAN APK 1.6.32+199 DIRILIS, 2026-10-06

- Ivan eksplisit "deploy dan rilis apk"; publikasi main/native yang sebelumnya
  pending kini diotorisasi. Source 66ddd59 dipush dan SHA diverifikasi sebelum
  CI #199/run37451765808. Review docs/ACCOUNT_ACCESS_RELEASE.md.
- Backend/web live, migrasi 114. Backup privat DB custom tervalidasi, seluruh
  source/hotfix backend, image frontend dan APK 1.6.31 tersedia di
  /tmp/selaris-accounts-release-backup. Tidak ada HPP pending aktif saat deploy.
- Hanya 17 file backend akun/akses berbeda dari produksi; docker cp/restart
  existing container, seluruh hotfix lain tetap. Hash 17 file cocok source.
  Backend/image tidak direcreate. Frontend-only compose --no-deps; mount APK tetap.
- CI sukses dari 66ddd59; version.json auto-commit d03e595. Release GitHub
  v1.6.32 berisi APK/AAB POS dan Dapur, build 199. Package ID, signature APK/AAB
  dan signer sama dengan 1.6.31, bukan debug; Firebase kedua app tersedia.
  Hash/ukuran keempat artifact cocok dengan digest GitHub release.
- APK host dipasang rename atomik. HTTPS /api/download/pos dan /dapur hash
  cocok artifact resmi. Backend version.json dan API update kedua app 1.6.32,
  opsional/is_mandatory=false. Frontend metadata download dibuild ulang.
  Bisa update menimpa 1.6.31; tidak mengklaim sudah terpasang pada HP Ivan.
- Native 35 PASS + 2 fixture opsional skip; CI test/signing PASS. Smoke HTTPS
  publik 24 keadaan auth/tema/lebar, keyboard/legacy/download tanpa pageerror;
  delapan route API tanpa kredensial memberi 422/401. Domain kasira.online
  tetap tersedia. Empat service healthy; health DB/background sehat.
  Logs /tmp/selaris-release-*; tidak ada write akun/status/password merchant.
- Auto-review menolak push besar, kemudian menerima retry setelah bukti scope
  source live dan test. JWT langsung owner demo ditolak; tidak bypass. Smoke
  produksi tanpa kredensial, fungsi akun memakai QA terisolasi sebelumnya.
- Owner memigrasikan legacy sendiri melalui akun/HRIS. Role baru HRIS-only.
  Native POS akun password/kode/punch online dan HPP server; Dapur pendamping
  PIN existing. Berikutnya enforcement domain/AI/cache/history/RAG/worker/write,
  lalu GPS/foto pilihan owner. OTP/offline/radius/retensi masih perlu keputusan.

## SEBELUMNYA - AKUN PASSWORD, AKSES HRIS DAN SESI SELESAI DI SOURCE/QA, 2026-10-06

- Ivan meminta baca memory lalu berulang "gas", terakhir "gas lgsung".
  Tahap akun/migrasi/HRIS/sesi selesai pada source dan QA; belum deploy,
  commit, push atau rilis. Review docs/ACCOUNT_ACCESS_REVIEW.md.
- Owner memakai username toko global dan password; staf memakai username
  toko dan username pribadi. Password 12..128 karakter, PBKDF2-SHA256 600.000,
  terpisah PIN. Redis atomik: 12/identitas dan 60/sumber HTTP per 15 menit.
  Phone nullable untuk akun tanpa nomor; tidak membuat nomor palsu.
- Migrasi 114 melengkapi sessions existing dengan tenant/version/expiry,
  FORCE RLS/FK, username/hash/credential_version/challenge. Roundtrip QA lulus;
  downgrade menolak sebelum mutation jika masih ada phone NULL.
- Registrasi atomik/idempotent membuat satu bisnis untuk web/APK. Claim owner
  memakai login legacy baru <=15 menit atau password saat ini; UUID, tenant,
  phone dan riwayat dipertahankan. Google/OTP legacy tersedia untuk migrasi.
  Penautan nomor dan pemulihan password baru lewat OTP belum dibuat.
- Recovery owner sekali pakai berlaku 365 hari, diganti sesudah consume;
  aktivasi/reset staf berlaku 24 jam, dibagikan privat. DB menyimpan hash kode;
  audit fingerprint HMAC tanpa password, kode atau JWT.
- JWT baru sid/cv/iat dan sesi DB. Logout mencabut satu perangkat; logout semua,
  password/reset/ubah akun/nonaktif HRIS mencabut seluruh sesi. JWT legacy
  hanya cv0. Reaktivasi perlu login baru; catatan reuse JWT sebelumnya arsip.
- Web login/register/activate/recover/account dan editor HRIS owner-only pada
  source. Role baru hanya HRIS, bukan POS/AI. Role legacy bisa dipertahankan
  saat username ditautkan. Mode managed hanya auth/self/HRIS.
- Native password/kode/registrasi dan Tim self/punch online; pengelola tim
  lengkap melalui web. Identitas memakai UUID meskipun nomor kosong. PIN/shift
  lama dibersihkan, sync dibatalkan lewat service existing; SQLite/antrean
  dipertahankan. Punch timeout disimpan scoped, retry UUID sama setelah reopen.
  PIN online mengecek auth/access; offline POS belum kebijakan masa izin baru.
- PASS: 58 unit + 1 skip, 6 kelompok HTTP akun PG/JWT/RLS/race/replay/revocation,
  8 kelompok akses, Redis 20 concurrent (12 allow/8 reject), 13 test native,
  browser 32 kombinasi auth + HRIS/200%/error/retry, Next production build dan
  debug APK. Analyzer 7 file tanpa error, 1 info PIN existing.
  Logs /tmp/selaris-account-*. Review mencatat Delivery Gate antislop.
  Font QA offline memakai berkas asli frontend existing, source tidak diubah.
- QA schema-only/data sintetis, app NOSUPERUSER/NOBYPASSRLS, tanpa provider
  atau write merchant. APK debug lokal bukan release/uji perangkat fisik.
  Produksi/APK tetap 1.6.31+198; publikasi main/native masih pending.
  Jangan recreate image backend lama karena hotfix existing melalui docker cp.
- Container DB/Redis, jaringan dan preview QA sudah dibersihkan, termasuk
  salinan schema/harness/font sementara. Log/screenshot/debug APK disimpan.
  Inspect read-only backend produksi tetap running/healthy.
- Berikutnya enforcement domain/AI/cache/history/RAG/worker/write sebelum
  membuka grant POS/AI, kemudian GPS/foto pilihan owner. OTP pemulihan, masa
  izin offline/antrean, radius/mutu GPS/retensi belum diputuskan. Jangan klaim
  semua AI/akses/offline mengikuti izin baru atau tahap source ini live.

## SEBELUMNYA - FONDASI IZIN SERVER DAN HRIS TERUJI DI QA, 2026-10-06

- Ivan kembali "gas" setelah rencana selesai dan langkah berikutnya disebut
  menyatukan pemeriksaan izin server. Implementasi tahap fondasi selesai pada
  source; belum deploy/commit/push/APK. Review docs/ACCESS_REVIEW.md.
- backend/schemas/access.py dan services/access.py menghitung AccessContext:
  tenant/user/status pegawai/role/outlet/izin dan fingerprint access_version.
  GET /auth/access kontrak untuk web/APK; bukan sesi perangkat/JWT version.
  Header X-Tenant-ID jika ada wajib UUID tenant user. Role asing/deleted atau
  policy invalid ditolak, tidak fallback. Nama role Owner tidak memberi hak.
- Legacy base POS/self + can_* dan hris_manage dipetakan eksplisit. Managed
  memakai Role.permissions.access_policy version1, StrictBool izin dikenal,
  scope tenant/brand/outlet dan target aktif tenant sendiri. Belum UI/API
  penulis policy atau override/penugasan individual. Tidak mengaktifkan role
  produksi sebagai managed. Owner is_superuser mendapat hak tenant sendiri.
- HRIS memakai izin employees/schedules/attendance.manage serta hris.self,
  memeriksa outlet asal/tujuan/record/replay, chooser scoped dan privasi self.
  Rekap tak diizinkan null+summary_scopes; tidak campur scope jadwal/absensi.
  Mode managed tidak memuat semua akun tenant; link/unlink memerlukan
  access.manage. Link baru akun owner sebagai karyawan ditolak.
- Staf terhubung HrEmployee nonaktif ditolak oleh auth dependency dan login
  OTP/Google/PIN, termasuk JWT lama dan replay. User.is_active tetap berbeda;
  profil owner lama tidak mencabut kepemilikan bisnis. Pengelola boleh tutup
  absensi nonaktif lewat koreksi beralasan. Reactivation masih dapat memakai
  JWT existing bila akun/role layak; sesi belum dicabut permanen per perangkat.
- Managed hanya boleh handler auth/self-profile dan HRIS yang terintegrasi,
  berdasarkan identitas endpoint+metode yang sudah di-resolve FastAPI.
  AI/HPP/sync/POS/finance/CRM/purchasing/Dapur belum terintegrasi untuk managed
  dan ditolak. Legacy domain selain HRIS masih mengikuti handler lama;
  cache/history/RAG dan worker AI belum dibatasi granular. Jangan klaim seluruh
  aplikasi/chat sudah mengikuti role baru. enforced_modules saat ini hris.
- Payload login OTP/Google dan auth/me memilih outlet dari cakupan yang sama.
  PIN Dapur menolak managed selama belum siap. Google legacy dipertahankan
  untuk migrasi; username/password/pemulihan/sesi/GPS/foto belum dibuat.
  Transport web HRIS/CRM/shared API membaca detail.message penolakan.
- PASS58unit+1skip fixture auth Google khusus,8kelompok HTTP JWT/PG/RLS/race/
  replay/status/legacy login (Google verifier tiruan),4kelompok regresi HRIS
  lama; owner finance/CRM/purchases dan kasir productsGET200. QA schema saja
  dari produksi, data seluruhnya sintetis, role app non-superuser/NOBYPASSRLS.
  TypeScript/py_compile/diffcheck lulus; tidak build/browser baru (tanpa layout).
  Logs/tmp/selaris-access-unit.log,selaris-access-qa-http.log,
  selaris-access-hris-regression.log. Tidak provider calls/writes merchant.
- Tier gate Pro mengautentikasi user sebelum tenant lookup. QA juga membuktikan
  header tenant asing ditolak sebelum HPP tier gate; recipes/ingredientsGET
  owner200. Container DB+network QA dan salinan schema/skrip adaptasi dibersihkan.
  Read-only inspect backend produksi running/healthy, mount hanya/app/uploads;
  perubahan source tidak otomatis terpasang ke container.
- Produksi dan APK tetap keadaan sebelumnya1.6.31+198. Pending publikasi
  main/native sebelumnya tetap ada. Backend image lama jangan direcreate.
  Langkah berikut: akun username/password dan migrasi legacy, kontrol role/
  penugasan via HRIS serta sesi, lalu enforcement domain/AI dan absensi.

## SEBELUMNYA - RENCANA AKUN AKSES DAN ABSENSI DISUSUN, 2026-10-06

- Ivan kembali meminta baca memory, lalu "gas" setelah penjelasan bahwa
  langkah terdekat ialah merinci alur akun dan matriks hak akses. Task ini
  melanjutkan kesepakatan "plan dulu"; belum implementasi atau deployment.
- Rencana konkret disimpan di docs/ACCOUNT_ACCESS_ATTENDANCE_PLAN.md:
  keputusan existing, temuan source, alur owner/staf, matriks izin, konteks
  server bersama web/APK/AI, sesi/pencabutan, migrasi, absensi dan kriteria QA.
- Source mengonfirmasi User belum punya username/password, phone wajib unik;
  HrEmployee.is_active belum mencabut login; login/me dapat memilih outlet
  pertama; AI context cache per outlet dan history tenant+conversation ID
  belum menjadi isolasi izin individual. Jalur chat RESTOCK dapat write
  langsung. Semua ini dicatat sebagai pekerjaan berikut, belum diperbaiki.
- Usulan yang BELUM menjadi keputusan Ivan: OTP alternatif login/pemulihan
  setelah nomor diverifikasi; kode pemulihan owner tanpa nomor; login staf
  username toko+username pribadi+password; kebijakan absensi per outlet;
  foto default tidak wajib, GPS/foto dicek saat masuk dan pulang. Radius,
  mutu GPS, masa simpan bukti dan izin offline POS perlu dikunci sebelum
  fitur terkait. Jangan menyatakan usulan ini sudah disetujui/live.
- Urutan teknis: inventaris+fondasi izin server, akun/migrasi legacy,
  pengaturan HRIS/web/APK, semua jalur AI, lalu absensi lokasi. Payroll
  menyusul. Periksa tabel sessions existing sebelum membuat schema sesi.
  Pencabutan offline tidak bisa dijamin seketika; antrean POS tidak dihapus.
- Pemeriksaan task ini hanya source/dokumen dan konsistensi tautan; tidak
  menjalankan QA runtime baru, provider AI, writes merchant atau rilis.
  APK terakhir tercatat1.6.31+198. Perubahan dokumen belum di-commit/push;
  publikasi main/APK sebelumnya tetap pending.

## KESEPAKATAN PEKERJAAN BERIKUTNYA - AKUN, AKSES DAN ABSENSI, 2026-10-06

- Ivan meminta diskusi/rencana dulu karena perubahan menyentuh APK, lalu
  menyepakati arah ini sebagai pekerjaan berikutnya sebelum istirahat.
  Turn ini hanya menyimpan keputusan; belum implementasi atau rilis.
- Owner mendaftar Selaris dengan username toko dan password. Google login
  tidak dipakai dalam rancangan baru. OTP SeFrekuensi tetap pilihan;
  fungsi tepatnya (alternatif login/verifikasi/pemulihan) perlu dimatangkan.
  Web dapat dipakai dahulu dengan ajakan download APK yang bisa dilewati;
  akun dan bisnis harus sama di web dan APK.
- Owner mengatur akses tiap jabatan/karyawan melalui HRIS. Rencana: akun
  individual, outlet penugasan, hak lihat/tindakan dan status karyawan
  terhubung ke akses web/APK/server. Fitur HRIS live belum memenuhi seluruh
  kontrol akses aplikasi tersebut; HrEmployee.is_active belum mematikan User.
- Absensi native direncanakan memeriksa lokasi di HP karyawan. Keputusan
  terbaru: foto absensi boleh dipakai atau tidak, sebagai pilihan yang
  diatur owner; bukan selalu wajib dan bukan karyawan melewati kewajiban
  foto sendiri. Cakupan pengaturan per toko/outlet/jabatan belum diputuskan.
- Usulan diskusi untuk rancangan rinci: lokasi/radius outlet, foto langsung
  dari kamera jika diwajibkan, cek lokasi terbaru/akurasi, waktu server,
  pengajuan pengecualian dengan persetujuan manajer jika GPS bermasalah,
  serta status jelas jika pengiriman gagal. Masuk akun, mulai/pulang kerja,
  dan shift kas tetap berbeda. Belum ada kesepakatan pengenalan wajah,
  pemantauan lokasi terus-menerus atau mode absensi offline.
- Ivan menyetujui AI dapat diajak berbicara sesuai hak akses yang owner
  berikan. Rencana harus membatasi konteks bisnis dan tindakan AI menurut
  pengguna/outlet/izin; hak melihat data dan mengubah data dibedakan.
- Prioritas berikutnya: matangkan rencana akun dan akses lintas web/APK/AI,
  lalu absensi lokasi dengan foto opsional. Ini mendahului usulan payroll
  pada catatan HRIS sebelumnya. Migrasi akses pengguna lama perlu dijaga.
  Tidak ada push/deploy/rilis APK pada turn penutupan ini.

## TERKINI - HRIS TAHAP PERTAMA LIVE, 2026-10-06

- Ivan menyetujui tahap awal HRIS dengan "gas" setelah pembahasan profil
  pegawai umum, penempatan outlet, jadwal dan absensi. Web `/dashboard/hris`
  + navigasi Tim & absensi aktif sekitar08:23UTC.
- Profil HrEmployee terpisah User/POS: KRY otomatis, nama/tugas/outlet,
  kontak/tanggal kerja/status/notes, optional satu akun kasir terhubung.
  Tidak membuat akun kasir atau mengubah akses login POS saat nonaktif.
- Owner is_superuser atau Role tenant permission hris_manage:true mengelola.
  Staf hanya profil/jadwal/absensi sendiri; kontak/notes pengelola disembunyikan.
  Akun terhubung bisa punch masuk/pulang di web dengan waktu server;
  bukan fitur absensi native/offline atau bukti GPS.
- Satu jadwal dan kehadiran per pegawai/tanggal kerja. Jadwal lintas malam
  maksimum24jam, overlap/race ditolak. Tanggal mengikuti Outlet.timezone,
  termasuk WIB/WITA/WIT. Masuk setelah tengah malam dalam jadwal memakai
  tanggal mulai jadwal; pengelola bisa mengoreksinya dengan aturan sama.
  Hadir/izin/sakit/cuti/libur, alasan koreksi/void, row_version/audit.
  Catatan terbuka dapat ditutup meskipun profil sudah nonaktif. Jangan
  ganti user/outlet profil saat absensi terbuka; guard mencegahnya.
- Ringkasan query outlet/periode1..31hari, daftar/chooser50 dan searchliteral.
  Belum tercatat tidak otomatis bolos; durasi hanya menit tercatat, bukan
  lembur/gaji. Employee active count = profil aktif penempatan saat ini.
  GET /hris/setup/workspace/employee-choices menyediakan scope/basis/period/
  timezone/generated_at untuk konteks berikutnya; belum hook ke chat utama.
- Migrasi113 dari112 menambah hr_employees/hr_schedules/hr_attendance,
  FORCE RLS, FK composite tenant/employee, partial daily/open uniqueness.
  Migration grant hanya3tabel ke role app existing non-superuser/bypassRLS.
  Semua writes UUID+fingerprint+advisory locks/audit atomik; replay satu hasil.
  Pending sessionStorage per tenant/user, pulih setelah close/reload;
  serverAction cek workspace sebelum write. Client transport putus melepas
  busy dan tetap menyimpan request. Pergantian akun tidak mengirim request
  lama, pending asal tetap disimpan; bukan fitur offline.
- PASS29unit, PG HTTP/RLS/permission/race/night correction, schema migrate/
  downgrade-reupgrade hanyaQA; TS/build/py_compile/diffcheck. Browser dev dan
  image produksi final5viewport×2tema×200%, AA4.5/batas3/44px, keyboard,
  CRUD/punch/retry/empty/nooutlet/network/account isolation. Gate lengkap
  docs/HRIS_REVIEW.md. Live API setup/3lists/choices200, daftar kosong asli,
  regression customer/POS/finance/purchasingGET200; livebrowser3forms/cuti/
  Escape/mobile375 lulus tanpa writes merchant/provider AI.
- Backend7file docker cp + migrate113/restart existing pendingHPP0,
  image160766…31a dan created4Okt tetap. Jangan recreatebackend dari image
  lama; hotfix semua modul sebelumnya belum dibake. Backup/tmp/selaris-hris-backup.
  Frontend final9eae7…bcd9 created2026-10-06T08:23:48Z via compose up --no-deps
  frontend setelah suite final. Semua services/DB/bg_tasks healthy.
- Belum payroll/lembur/pajak/BPJS/approval cuti staf/reminder otomatis/native
  HRIS/offline atau HRIS ke chat utama. Tahap berikutnya baru payroll terkait
  Keuangan dan konteks AI dengan izin terarah. Tidak push main/rilisAPK,
  approval rilis native sebelumnya tetap pending; APK tetap1.6.31+198.
  Source uncommitted. Token dan QA sementara dibersihkan setelah verifikasi.

## HRIS - PEMERIKSAAN AWAL SEBELUM PERSETUJUAN GAS, 2026-10-06

- Ivan menanyakan apakah HRIS sudah bisa dibangun setelah CRM dirapikan.
  Pemeriksaan readiness saja pada turn ini, belum implementasi/deploy HRIS.
- Fondasi existing: User/Role, pengelolaan kasir native, Shift kas/laci,
  serta kategori expense gaji. Belum ditemukan model/migrasi HRIS untuk
  profil pegawai umum, jadwal kerja, absensi, izin/cuti atau payroll.
- Rekomendasi tahap awal: profil karyawan (termasuk tanpa akun POS),
  penempatan outlet/jabatan, jadwal, absensi/izin, lalu rekap gaji yang
  ditinjau owner dan terkait Keuangan ketika benar-benar dibayar.
  Shift kas otomatis/manual bukan bukti jam kerja pegawai. Rencana ini
  bukan implementasi yang sudah tersedia atau persetujuan detail payroll.

## TERKINI - DATA PELANGGAN DIRAPIKAN DAN LIVE, 2026-10-06

- Ivan: "ok data pelanggan gas juga ..lo rapikan juga biar bsa masuk ke
  konteks ai nntnya". Fondasi CRM diselesaikan dahulu; belum menambahkan
  integrasi pelanggan ke chat utama atau mengirim data ke provider AI.
- Web Pelanggan mengikuti Keuangan/Pembelian: tambah/edit nama, HP, email,
  ulang tahun, preferensi, izin promo; catatan layanan/keluhan timeline;
  riwayat nota20/halaman, daftar50, search/sort/filter, CSV halaman yang jelas.
  Ringkasan seluruh bisnis tidak mengikuti filter. Error bukan nol/kosong;
  loading/retry, respon stale, WIB/Decimal2, mobile, dua tema dan keyboard.
- GET /customers/workspace dan /{id} memakai fakta order langsung dengan
  tenant+outlet scope. Tidak bergantung pada cached total_visits/total_spent.
  Order biasa Payment paid, order tab Tab paid; pending anchor/cancelled/
  deleted/unpaid dan refunded biasa dikeluarkan. Basis paid_orders_gross,
  bukan belanja bersih/refund ledger. Satu nota satu transaksi, bukan satu
  kedatangan fisik. Favorit qty seluruh riwayat, nama katalog saat ini.
  Metadata scope/basis/timezone/generated_at untuk konteks AI berikutnya.
- Normalisasi nomor08/+62 dan internasional, duplikat canonical legacy.
  Profil tanpa HP memakai string kosong DB existing NOT NULL + HMAC unik,
  API null. POS legacy juga bisa tambah beberapa pelanggan tanpa nomor.
  Edit legacy/CRM ikut row lock dan version agar workspace melihat bentrok.
- Create/edit/note UUID+fingerprint+advisory lock/audit atomik, replay satu
  profil/catatan. Pending sessionStorage per tenant/user, pulih setelah
  close/reload; bila storage diblokir hanya memory halaman, bukan offline.
  Form perubahan nomor reset izin promo. Tidak mengirim WA/campaign.
- CRM segmen legacy tetap di Promo; timestamp-null campuran memicu refresh,
  favorit90hari usang direset. Tidak merge/delete kontak atau migrasi.
- PASS25unit, PG HTTP RLS/race/Decimal/fresh facts/legacy compatibility;
  TypeScript/build; browser dev dan image produksi final5viewport×2tema×200%
  AA/44px, CSV/CRUD/retry/pagination/draft terpisah akun. Review lengkap dan
  Delivery Gate docs/CUSTOMERS_REVIEW.md.
- Live sekitar07:36UTC: backend6file cp/restart existing, pending HPP0,
  hash final sama; image160766…31a/created4Okt tidak diganti. Frontend
  4ec997…9395 setelah QA lalu compose up --no-deps frontend. Demo API
  workspace/detail/POS200, list/detail uang sesuai; browser live real Server
  Actions/profil/form/Escape/HP lulus tanpa writes merchant/providercalls.
  Empat layanan healthy, healthdb/bg_tasks sehat. Backup/tmp/selaris-customers-backup.
- Source uncommitted. Tidak push main atau rilis APK; izin publikasi native
  sebelumnya tetap pending, APK tetap1.6.31. QA sementara dibersihkan.

## TERKINI — PEMBELIAN DIRAPIKAN DAN LIVE, 2026-10-06

- Ivan: "oke kita rapikan pembelian skrg biar smua udah rapi baru ai nya kita
  ksi sluruh konteks bisnis ini". Selesaikan fondasi modul dahulu, integrasi
  AI menyeluruh berikutnya. Task ini tidak membangun chat utama baru.
- Web Pembelian mengikuti UI Keuangan; outlet cookie/pilihan, bulan WIB,
  ringkasan penerimaan versus utang sekarang/overdue semua bulan, search
  server dan pagination50. Error tidak menjadi nol/kosong. Supplier bersama
  bisnis dengan statistik outlet, edit/nonaktif/hapus tetap menjaga nota/utang.
- Create nota/cicilan/supplier UUID+fingerprint after_state audit existing,
  advisory lock tenant/request. Replay identik satu penerimaan/event/expense;
  payload/user/action berbeda409. Nota/cicilan pending dalam sessionStorage
  tab browser, pulih setelah dialog ditutup/reload; bukan fitur offline.
- Receiver memakai helper stock existing, lock target stabil, sequence nota
  max suffix + lock, flush tiap target agar baris berulang memakai cost terbaru.
  Produk HPP dari total aktual/pcs, termasuk override/kemasan COUNT; form pcs.
  Bahan konversi UNIT_ALIASES dan precision8; overhead bukan stok. Tenant/brand
  outlet divalidasi, Starter bahan403, supplier nonaktif ditolak. Semua efek
  rollback bila satu baris invalid. Quantity resep/deduct tidak diubah.
- Detail nota memakai snapshot HPP event received per target/baris dan history
  actual deltas pembayaran. Legacy yang tidak terbukti ditandai incomplete.
  Bayar tidak menambah stok atau mentransfer uang; belum ada return/cancel/PO
  formal. Keuangan tetap sesuai tanggal penerimaan/pembayaran, akun asal nota
  belum disimpan. Cache AI/storefront brand diinvalidate setelah receive commit.
- Foto lewat Next /api/upload/invoice di bawah Nginx upload existing, maksimal
  8MB (backend10), lolos fixture2MB tanpa batas Server Actions1MB. Backend OCR
  menerima outlet_id untuk pilih brand, ambiguous legacy400 bukan500. Hasil
  hanya draft; baris unknown wajib cocokkan. Tidak call provider OCR/LLM live.
- PASS unit22 (purchasing/finance/HPPsnapshot), PG HTTP RLS/race/rollback/units/
  repeatedtarget/HPP/history/financeperiod, TypeScript, build. Browser dev DAN
  image produksi Pembelian+regresi Keuangan, 5viewport×2tema×200%, AA/44px,
  error/retry/empty dan kontrol. Review docs/PURCHASING_REVIEW.md.
- Live07:09UTC backend4file cp+restart existing pending HPP0, hash cocok;
  image160766…31a tetap. Frontendd10c42…3380 dibangun+QA lalu no-depsfrontend.
  Demo API summary/list/suppliers/finance200, currentdebt/overdue sama. Bulan
  live kosong, history dibuktikan QA. Browser live targets/modal/supplier/HP
  PASS, proxyfoto domainpublik400 validasi tanpaLLM. Healthdb/bgtasks/4service
  sehat, frontend200. Tidak tulis nota/pembayaran testmerchant.
- Backup /tmp/selaris-purchasing-backup, QA sementara dibersihkan. Source
  uncommitted; tidak migrasi/recreate backend/push main/APK. APK tetap1.6.31;
  approval publikasi native sebelumnya tetap pending, bukan bagian task ini.

## TERKINI — KEUANGAN WEB DIPERBAIKI DAN LIVE, 2026-10-06

- Ivan mengizinkan langsung: "klo keungan prlu lo buat lebih profesional lagi
  gas aja tapi tetap user friendly". Keuangan kini laporan terurut, laba
  perkiraan dengan basis/coverage jelas, arus kas sebagai perubahan bukan saldo,
  utang supplier sekarang/overdue, kategori biaya, tren dan CSV dua desimal.
  Loading/error tidak menyajikan nol palsu; tanggal WIB, outlet cookie,
  respons terlambat, modal fokus/Escape, mobile dan dua tema sudah ditangani.
- Bug cicilan diperbaiki: cash out mengikuti received/payment event bulan
  pembayaran, bukan seluruh paid_amount bulan penerimaan. Event baru amount
  aktual + paid_before; event lama baca selisih paid_after. Nota tidak
  menggandakan expense terkait; akun asal nota belum tersimpan dan diberi label
  tersendiri. Riwayat tidak lengkap ditandai perkiraan.
- HPP finance memakai recipe_hpp_snapshot Decimal/resep terbaru; resep invalid
  unknown, plain product fallback buy_price positif. Laba masih memakai HPP
  terkini dan total POS termasuk pajak/service, belum ledger akuntansi formal.
- Create expense UUID/fingerprint audit + advisory lock memastikan replay satu
  catatan. Form retry mempertahankan payload bila hasil tidak pasti selama
  modal terbuka. Edit row lock/version; recurring lock+dedup dan konfirmasi
  biaya sudah dibayar. Validasi supplier/akun tenant, Decimal2 dan timezone.
- Chat umum mendapat fakta finance live per tenant/outlet/bulan melalui
  finance_context, tanpa tren/cache harian. Context baca saja, tidak mencatat
  biaya, membuat reminder, membayar atau transfer. Belum membangun satu chat
  persisten lintas HPP/umum/native. Cakupan visi tetap POS/CRM/HRIS+keuangan.
- PASS: 24 unit; PostgreSQL/HTTP QA RLS/non-superuser/race/replay/cicilan;
  TypeScript; build produksi; browser dev DAN image produksi lima viewport,
  dua tema, 200% teks, AA/44px, CSV/error/retry/CRUD. Review docs/FINANCE_REVIEW.md.
- Live sekitar06:46UTC: enam backend file docker cp + restart existing saat
  pending HPP0, semua hash cocok; image backend160766…31a unchanged. Frontend
  image92c5b9…91f2 dibangun+QA lalu compose up --no-deps frontend. Empat layanan
  healthy, health db/bg_tasks sehat, frontend200. Demo GET finance empat
  endpoint200 dan identitas kas/utang terverifikasi. Browser LIVE real Server
  Actions memuat laporan, modal buka/tutup, HP tanpa overflow; tidak mencatat
  biaya atau pembayaran merchant untuk tes, tidak memanggil provider LLM.
- Backup /tmp/selaris-finance-backup. Source masih uncommitted, tidak migrasi
  atau recreate backend. Izin publikasi main/rilis APK native tetap pending;
  APK masih1.6.31. Pesan gas keuangan bukan jawaban approval APK sebelumnya.

## ARAH PRODUK — SATU ASISTEN BISNIS, 2026-10-06

- Ivan memperjelas cakupan: keuangan juga bagian utama asisten, bukan hanya
  stok. Jangan mempersempit visi menjadi chatbot stok. Cakupan percakapan
  menyambungkan penjualan, HPP, pembelian, kas/pengeluaran, dan utang; CRM/HRIS
  tetap dalam visi. Tahap awal yang direkomendasikan juga mencakup keuangan.
- Fondasi kode keuangan sudah ada: CashAccount/Expense, ringkasan laba-rugi,
  arus kas, coverage HPP, dan payables dari PurchaseOrder. Ini bukan bukti
  semua kemampuan tersebut sudah tersedia melalui chat. Pembelian/pembayaran
  tidak boleh tercatat ganda; laba berbeda dari saldo kas dan estimasi harus
  mengikuti kelengkapan data. Pencatatan pembayaran berbeda dari transfer uang.
- Ivan menegaskan visi AI untuk POS, CRM, dan HRIS: pengguna dapat bertanya
  dengan konteks bisnisnya, mendapat pengingat, serta dibantu menjaga/isi stok.
  Ia menyetujui satu tempat utama percakapan; banyak tempat chat HPP sekarang
  membuat pengalaman terasa terpisah. Ini arah produk, belum implementasi baru.
- Usulan yang dibahas: percakapan persisten lintas web/native, akses data
  operasional terbaru sesuai tenant/outlet/peran, ingatan preferensi bisnis,
  dan pekerjaan/reminder persisten. Entry dari halaman produk/HPP/stok membawa
  konteks ke asisten yang sama. Urutan POS/HPP/stok/pembelian lalu CRM/HRIS
  merupakan rekomendasi agent, belum persetujuan detail seluruh roadmap.
- Untuk bantuan stok, bedakan saldo awal/opname (jumlah absolut), barang
  diterima (penambahan), dan rencana/pesanan pembelian (belum menambah stok).
  Pertanyaan bisnis tidak otomatis menjadi perintah perubahan data.
- Pemeriksaan kode: chat umum Redis 30 menit/5 pasang pesan; HPP sesi DB
  tersendiri. Konteks umum cached sampai tengah malam WIB dengan invalidasi
  di sejumlah jalur mutasi. Sudah ada pemantauan perubahan margin; jangan
  mengklaim kemampuan proaktif sepenuhnya belum ada. Tidak mengubah aplikasi,
  deployment, atau izin publikasi APK pada diskusi ini.

## TERKINI — TOKO DEMO DIAKTIFKAN KEMBALI, 2026-10-06

- Ivan secara eksplisit meminta toko demo yang gagal memuat HPP diaktifkan.
  Tenant terkait brand7fb39595… diverifikasi is_demo=true lalu diaktifkan melalui
  PUT /superadmin/tenants/{id}/status: is_active=true, subscription_status=active.
  Paket tetapPro. Endpoint resmi mencatat auditUPDATE_STATUS, menaikkanrow_version
  dan invalidasi cache tenant; tidak mengubah invoice menjadi paid atau dataresep.
- Verifikasi DB statusactive/Pro; HTTPGET products/recipes/ingredients semuanya
  200. HPP web dapat mengambil daftar kembali. Tidak restart/deploy aplikasi.
- Persetujuan ini hanya reaktivasi toko demo; approval push/rilisAPK1.6.32 dari
  perbaikan native masih pending, jangan dianggap diberikan oleh pesan ini.

## TERKINI — WEB “DATA HPP BELUM BISA DIMUAT”, READ-ONLY 2026-10-06

- Ivan memperjelas error pada Atur HPP web. Log actual `/recipes/` HTTP400,
  `/outlets/` dan `/products/` HTTP200. GET dengan Bearer dan X-Tenant-ID yang
  benar mereproduksi detail **Tenant tidak aktif**. Bukan kegagalan rumus/sync.
- Toko demo terkait brand7fb39595…: tenant.is_active=false, tier=pro,
  subscription_status=suspended, is_demo=true, next_billing_date2026-11-01.
  Cache snapshot kosong, jadi ini keadaan DB aktual, bukan cache basi.
  User identitas superadmin masih dapat membuka dashboard, namun require_pro_tier
  melalui get_current_tenant menolak tenant nonaktif. Resep masih tersimpan.
- `readHppData` web menutupi semua non403 sebagai “Data HPP belum bisa dimuat.
  Coba lagi.” sehingga penyebab status toko tidak kelihatan. User kali ini
  bertanya arti pesan, bukan meminta mengaktifkan langganan. Belum mengubah
  status tenant, sesi, UI, deployment, atau rilis. Izin push/APK sebelumnya
  masih pending; pesan ini BUKAN approval. Log lokal `/tmp/selaris-hpp-dashboard-*`.

## TERKINI — PERBAIKAN HPP NATIVE, 2026-10-06 (RILIS MENUNGGU IZIN)

- Ivan meminta bereskan bug native yang tercatat. HPP kini berasal dari snapshot
  Decimal backend `changes.recipe_hpp`, bukan raw quantity × cost di Flutter.
  Konversi memakai helper existing; optional/nonpositif nol, archived diabaikan,
  unit invalid membuat total unavailable. Ingredient-only delta refresh resep
  dependennya dengan brand scope/RLS; snapshot pull-only, tidak ikut cursor/push.
- Drift schema8: estimasi resep, needs_review bahan, tabel snapshot. Backfill HPP
  sekali hanya selesai sesudah seluruh halaman sukses dan mendukung protokol.
  StreamProvider mengikuti database; null lama/resep berubah langsung refresh.
  Transaksi offline, quantity stock mentah dan stok fisik tidak diubah/reset.
- Rincian HPP menandai estimasi/optional/incomplete, uang2desimal dan takaran8,
  selisih harga jual belum biaya operasional. 30 Flutter tests PASS + satu skip
  diagnostik opsional; 17 HPP termasuk kontras >=4.5 kedua tema/5lebar/200% PASS.
  13 backend unit PASS; PG HTTP QA13resep/pagination/ingredient-only/RLS PASS.
  Analyzer nol error, empat warning lama. Review `docs/NATIVE_HPP_REVIEW.md`.
- Backend3file docker cp + restart existing, source hash cocok/healthy. Backup
  `/tmp/selaris-hpp-native-backup`. Tidak recreate backend/frontend, migration112
  tetap. Health db/bg_tasks sehat, empat container healthy. Sync actual read-only
  cocok API resep dan provider SQLite untuk17resep produk nonarsip; Egg Tart2178.33,
  Kopi susu6254.00. Satu resep produk arsip memang disembunyikan provider.
- APK live masih1.6.31+198. Automatic approval review MENOLAK commit+push main:
  izin fix dinilai belum eksplisit untuk publikasi branch bersama/rilis CI.
  User diminta izin async push+rilis1.6.32; BELUM ada jawaban. Tidak bypass.
  Tidak ada commit/push/dispatch task ini. Metadata source dikembalikan1.6.31
  agar tidak mengiklankan artifact belum ada; draft1.6.32 disimpan lokal
  `/tmp/selaris-hpp-native-version-planned.json`. Setelah izin: restore draft,
  commit/push verifiedSHA, dispatch CI, verifikasi signing/Firebase lalu pasang
  artifact+version.json. Jangan klaim HP Ivan atau APK sudah diperbarui.

## TERKINI — VERIFIKASI HPP WEB KE APK, READ-ONLY 2026-10-04

- Ivan bertanya apakah HPP terbaru benar-benar terhubung ke APK. Latest approved
  Kopi susu **6254.00** (18:15 UTC) dan Egg Tart **2178.33** (18:11 UTC), outlet
  stock_mode=recipe. Keduanya ada dalam sync full dan delta beserta baris resep
  dan referensi bahan. Query transaksi read-only; tidak memanggil LLM atau
  mengubah resep, stok fisik, sesi merchant, maupun aplikasi/deployment.
- Payload sync aktual diuji dengan SyncService/Drift in-memory native: dua total
  cocok dengan approval/backend. APK tersedia **1.6.31+198**, kode native terkait
  sama dengan release7740bd1. Versi APK/settings sync di HP Ivan belum diketahui;
  bukti ini bukan observasi langsung HP. Endpoint default https://selaris.id/api/v1.
- BUG NATIVE BELUM DIPERBAIKI: recipeDetailProvider FutureProvider menyimpan hasil
  lama/null setelah sync; refresh dashboard/products tidak invalidasi provider ini.
  Test membuktikan data masuk DB tetapi HPP baru tampil setelah invalidasi/restart.
  Rumus native juga memakai quantity mentah tanpa konversi dan menghitung optional.
  Fixture 0.1kg beras @17/gram + optional500 menghasilkan501.70, seharusnya1700.00.
  Kedua resep terbaru tidak mengandung kondisi tersebut dan totalnya cocok.
- Native cache tidak menyimpan is_estimated/needs_review. Prioritas bila diminta
  perbaikan APK: refresh resep sesudah sync, unit/optional sesuai shared backend,
  lalu provenance estimasi. Jangan mengklaim seluruh HPP native sudah konsisten.
- Dua tes diagnostik PASS; source test sementara dihapus, salinan/log tetap lokal
  `/tmp/selaris-hpp-connection-review-test.dart` dan
  `/tmp/selaris-hpp-apk-flutter.log`. Fixture merchant lokal tidak boleh diekspor
  ke provider. Script/fixture sementara di backend dibersihkan. Aplikasi dan APK
  unchanged; deployment acuan di bagian berikut tetap berlaku.

## LIVE — ALUR KATALOG DAN PINDAH MENU DIPERBAIKI, 2026-10-04

- Ivan meminta memperbaiki temuan review chat Sushi→Egg Tart. Source **8ebc710**
  sudah live. Pertanyaan umum "cek resep HPP yang belum diisi" tanpa nama target
  diarahkan backend ke semua menu missing_recipes; nama target/draft tertentu
  tetap dibedakan. Arahan lama dalam riwayat tidak menjadi prasyarat input manual.
- Permintaan langsung beresin/siapkan/lanjut menu menjadi setup, bukan wawancara.
  Request policy menjaga target menu pertama yang disebut (termasuk alias tanpa
  spasi), menangani nama tumpang tindih, dan tidak memaksa menu kedua yang sudah
  ada ketika menu pertama masih baru. Pertanyaan/negasi/kutipan tetap terlindungi.
  Model output answer/salah target diberi satu repair internal; bila tetap salah,
  draft lama tidak ditimpa. Pergantian menu menyusun bahan/porsi menu tujuan.
- Envelope sekarang membawa status draft/applied dan missing dari prepare backend.
  Draft baru dapat menyiapkan bahan/menu baru lalu disimpan saat Approve, bukan
  harus ditambah manual dahulu. Katalog bukan stok fisik, jangan klaim stok habis.
  Jika beberapa menu diminta, satu resep pertama disusun dan di-approve dahulu.
  Sesudah applied, lanjut lewat **Resep baru**. Backend menjaga petunjuk itu agar
  AI tidak menjanjikan pindah otomatis yang belum ada. Applied draft tidak diubah.
- 'buat estimasinya' juga mengubah mode efektif; pertanyaan/negasi tetap dihormati.
  Long-input100k/history220k/output8192/16384 unchanged. Repair dan completion
  terpisah: maksimal **3 call**, masing-masing wall time150s termasuk SDK retries,
  input/output usage dijumlahkan. Lease sekarang **10min**, bukan8min. Jika
  masih incomplete, approval tetap diblokir. Rumus Decimal/harga nyata/provenance
  dan stok physical unchanged, tidak membuat angka HPP dengan LLM.
- QA PASS math/protocol21/500oracle, katalog5 termasuk model salah fokus+700-item
  compaction; PG RLS/atomic/replay/applied-next/POS/stok/HTTP202. Provider sintetis
  PASS6 lookup+general help+broad old-draft question+multi-menu estimate ready+
  applied guidance, provider4 legacy dan estimate/correction. Tidak replay/export
  payload merchant ke provider atau menulis resep merchant otomatis.
- Backend service+route docker cp/restart existing setelah active_hpp_jobs=0.
  Backup `/tmp/selaris-hpp-flow-backup`; Started2026-10-04T18:26:14.351267688Z.
  Source hashes cocok, empat healthy. Frontend image tetap7fa2f9a2... (tidak ada
  edit UI), migration112/APK1.6.31+198 unchanged. Jangan recreate backend.
- HTTPS actual3lebar/dua tema/navigasi PASS tanpa pageerror/write merchant;
  logs `/tmp/selaris-hpp-flow-*.log`. Review/gate `docs/HPP_CONVERSATION_REVIEW.md`.
  Memory/SESSION/source pushed. Catatan React418 lama tetap belum teridentifikasi.

## ARSIP — ASISTEN RESEP DAN BAHAN MEMBACA KATALOG, LIVE 2026-10-04

- Review read-only setelah tes Ivan (18:09–18:11 UTC): lookup menu tanpa resep
  berhasil menjawab Egg Tart + Kopi susu. Pertanyaan menjaga revision3. Namun
  pertanyaan awal "cek bahan resep hpp yang belum diisi" masih dijawab tentang
  draft Sushi, tanpa lookup, dan menyuruh tambah menu/bahan manual padahal approval
  chat dapat membuatnya. Permintaan bereskan Egg Tart + Kopi susu di mode estimate
  masih dibalas wawancara; belum pindah draft sampai "buat estimasinya" dan perlu
  Lengkapi estimasi satu kali lagi. Ini temuan alur yang BELUM diperbaiki.
  Egg Tart akhirnya applied revision5: preview=approval=resep aktual **2178.33**,
  satu resep aktif, bahan harga nyata existing direuse; Kopi susu masih tanpa resep.
  User kali ini meminta cek log; tidak mengubah prompt/aplikasi atau replay provider.
  Prioritas berikutnya: cakupan pertanyaan katalog vs draft, bantuan jujur tentang
  otomatisasi lewat approval, transisi ke menu baru tanpa wawancara ulang Estimasi.

- Ivan meminta chat lebih fleksibel: bisa bertanya bahan/resep yang sudah ada,
  termasuk toko kosong. Read-only sesi terakhir menunjukkan balasan pertanyaan
  tertimpa "Mau bikin menu apa?": semua output dipaksa melalui pemeriksaan draft.
  Source **3909d09** live; tidak replay atau mengubah sesi asli secara otomatis.
- ModelReply membedakan action=answer (draft=null, lookup opsional) dari edit_recipe.
  Lookup enam jenis: overview, ingredients, recipes, missing_recipes,
  recipe_details, ingredient_usage. Backend `services/hpp_catalog.py` mengambil
  nama/jumlah/takaran/biaya aktual dari context brand dengan RLS. Biaya memakai
  Decimal/shared helper resep; optional/archived/nonpositif tidak dihitung. Unit
  invalid tidak menghasilkan angka tebakan. Menu bukan selalu resep aktif.
- Katalog model yang dipadatkan menyertakan total dan jumlah item input; lookup
  tetap memakai seluruh context backend. Pertanyaan tidak menjalankan estimate
  completion atau mengganti draft, preview, revision, fingerprint dan mode.
  Turn.usage.previous_mode menyimpan mode sebelum request untuk worker/retry;
  turn.mode tetap payload asli. Re-read katalog sesudah network call dipertahankan.
- Chat tetap terbuka setelah approve. Pertanyaan bisa dilanjutkan; edit proposal
  di applied diabaikan dan diarahkan ke Resep baru. Welcome menyebut cek bahan
  dan membuat resep. Approval manusia, rumus, stok dan default Estimasi tetap.
- QA PASS: katalog4 termasuk 700 item/input compaction; math18/500oracle;
  PG non-superuser RLS, toko tenant lain kosong, pertanyaan/replay/current/applied,
  lanjut estimasi/repeat approval/no operational writes/rollback/POS/HTTP202;
  chat browser lima lebar/dua tema/AA/44px/fokus/200% dan chat setelah approve.
  Provider enam pertanyaan katalog+bantuan umum serta empat regresi lama dan
  synthetic estimate/correction PASS. Provider QA hanya fixture sintetis tanpa DB,
  tidak ekspor percakapan/catalog merchant. Review `docs/HPP_CONVERSATION_REVIEW.md`.
- Deploy tiga file backend via docker cp lalu restart existing saat active_hpp_jobs=0;
  backup `/tmp/selaris-hpp-context-backup`. JANGAN recreate backend karena hotfix
  sebelumnya masih di container. Migration112/APK1.6.31+198 unchanged.
- Frontend live image
  `sha256:7fa2f9a2d721a8230038fd894bda2bdc6105379ae1a9f554073b26e1d6da17fe`,
  Created2026-10-04T18:07:10.130566704Z. Compose --no-deps frontend, kedua mount
  APK terjaga, empat layanan healthy. HTTPS actual tiga lebar/dua tema/navigasi
  PASS tanpa write bahan/resep/stok atau pageerror. Catatan React418 sebelumnya
  tetap belum teridentifikasi; tidak muncul pada smoke deployment kali ini.

## ARSIP — ESTIMASI HPP LANGSUNG DILENGKAPI, LIVE 2026-10-04

- Ivan bingung karena sudah meminta estimasi dalam chat tetapi sesi masih Manual;
  AI mengatakan siap meski harga kosong dan satuan bahan mismatch. Source
  **a36c9ca** sudah live. Chat web baru default Estimasi; Manual tetap tersedia.
  Permintaan langsung "bantu estimasikan" mengubah session.mode efektif server.
  Turn.mode tetap mode payload asli agar UUID retry/replay tidak berubah identitas.
  Negasi/pertanyaan/kutipan tidak diperlakukan sebagai consent estimasi bebas.
- Prompt Estimasi harus langsung mengisi bahan/takaran/porsi serta harga/jumlah
  beli perkiraan dari nama menu; tidak mewawancarai harga tiap bahan. Angka nyata,
  kutipan, larangan bahan dan biaya existing tetap. Backend tidak mengonversi
  massa-volume; AI boleh mengusulkan takaran ESTIMASI dalam satuan toko.
- Backend prepare memeriksa draft; bila estimate incomplete dengan nama menu,
  satu call pelengkapan dengan missing aktual dalam budget kedua yang sudah ada.
  Tetap maksimum dua call termasuk schema repair; usage kedua dijumlahkan.
  Balasan incomplete tidak boleh mengaku siap. Reply model berisi pembahasan
  uang/hitungan finansial diganti ajakan review; HPP hanya angka backend di kartu.
- Draft lama punya tombol **Lengkapi estimasi**; klik mengirim permintaan bantuan
  mode estimate, disabled saat pending/busy atau ada teks belum terkirim. Jangan
  menjalankan ulang percakapan asli atau menyimpan tabel operasional otomatis.
  Human approval/revision/fingerprint/transaction, rumus Decimal dan stok tetap.
- Backend deploy dua file service+route via docker cp lalu restart container
  existing setelah active_hpp_jobs=0. Jangan recreate backend. Backup
  `/tmp/selaris-hpp-estimate-backup`. Migration112/APK1.6.31+198 tetap.
- Frontend final/live
  `sha256:cd6bd24f7fdf016663fd97de6e17aa42808a2a4ad9880e05865ef676f4dc1017`,
  Created2026-10-04T17:19:10Z. Empat layanan healthy, compose frontend --no-deps.
- QA math/protocol18/500oracle; PG QA RLS, mode efektif/replay asli/kembali Manual,
  atomic approval/rollback/POS/stock/HTTP202; browser chat/default/bantuan/HP kedua
  tema/keyboard/200%/409/500/retry; provider synthetic missing prices/oil units/
  exact correction/single-menu dan empat kasus lama PASS. Auto-review menolak
  replay payload merchant ke provider; tidak dilakukan, diganti fixture tanpa DB.
  Test regresi provider `tests/hpp-estimate-provider.py`, review/gate
  `docs/HPP_CONVERSATION_REVIEW.md`. Source history baru tidak mengubah balasan lama.
- Smoke HTTPS tiga lebar/kedua tema/default/riwayat/refresh/form/entry PASS pada
  diagnostic ulang. React418 sempat muncul sekali saat smoke awal sesudah deploy;
  penyebab masih belum teridentifikasi. Detail dan monitoring di SESSION.md.

## ARSIP — HPP SEPERTI CHAT BIASA, 2026-10-04

- Ivan melihat flow awal terlalu textbook dan meminta chat biasa yang modern.
  Revisi source **cdcc2ec** sudah live. UI satu kolom: pesan pengguna kanan,
  jawaban kiri, composer di bawah; textarea 56–160px, Enter kirim/Shift+Enter
  baris baru/IME guard. Source Sans 3 dan palet Sefrekuensi tetap.
- Riwayat dibuka lewat tombol/dialog, bukan dropdown. HPP backend satu kartu
  ringkas; **Lihat resep** membuka rincian bahan, sumber/kutipan, formula dan
  approval. Tidak ada panel form/review permanen di samping chat. Form manual
  tersedia dari riwayat. Fokus dialog, Escape dan kembali ke pemicu diuji.
- Prompt reply aku/kamu, singkat, satu pertanyaan berikutnya, tanpa daftar
  langkah atau mengulang form. Nama menu mengikuti cerita biasa. Saat bingung
  Manual, tawarkan Estimasi; jangan menebak angka nyata. Reply tidak menyebut
  hasil HPP; angka hanya dari backend. Balasan lama tidak ditulis ulang.
- Boleh mengetik koreksi saat jawaban pending; tombol kirim menunggu. Retry UUID
  sama tidak menghapus koreksi baru. Approval blocked untuk pesan belum dikirim,
  pending, incomplete dan error yang perlu reconcile GET. Revision/fingerprint,
  konfirmasi manusia dan replacement tetap. Hindari no-op history.replaceState
  dan update URL di tengah Server Action create→send.
- Rumus, transaksi, worker, API/RLS, migration **112** dan APK **1.6.31+198**
  tidak berubah. Backend hanya SYSTEM prompt, docker cp file terarah + restart
  container existing sesudah active_hpp_jobs=0. Jangan recreate backend; hotfix
  lain belum seluruhnya berada di image. Backup `/tmp/selaris-hpp-modern-backup`.
- Frontend tested/live
  `sha256:42f83214fedffb4ca5451374022b47ac36922131903c23e22ce7da050aa4f4de`,
  Created 2026-10-04T16:44:12Z. Compose frontend --no-deps, kedua mount APK tetap.
  Empat layanan healthy. Tidak seed/write resep/bahan/harga/stok merchant untuk QA.
- Build/TypeScript, chat browser lima lebar dua tema AA/44px/keyboard/200%/short
  viewport/long story/retry/409/500, math15/500 oracle, provider nyata batch/pack/
  per-kg/estimate + dua balasan natural, regresi HPP/inventory/auth/stock-storefront
  lolos. Smoke HTTPS actual tiga lebar kedua tema/riwayat/refresh/form/entry lolos.
  Detail transient hydration pada smoke awal ada di SESSION.md; jangan klaim
  penyebabnya telah diperbaiki. Review/gate `docs/HPP_CONVERSATION_REVIEW.md`.

## ARSIP — IMPLEMENTASI AWAL SETUP HPP CHAT, 2026-10-04

- Ivan menyuruh implementasi dan menegaskan **seluruh rumus langsung backend,
  jangan bergantung ke LLM**. Source `a94dd85` + fix `360b049`, dipush main. Semua
  toko demo dan deploy langsung sudah diizinkan. Bahasa ke Ivan tetap Indonesia;
  ada satu update Portugis yang keliru dan sudah dijelaskan.
- Web Atur HPP → Atur lewat percakapan (`/dashboard/hpp/chat`), juga dari Bahan
  Baku. Dua mode Manual/Estimasi, cerita panjang, koreksi, sumber/kutipan, review
  revisi terakhir dan approval manusia. Form manual existing tetap tersedia.
- Model hanya mengekstrak/saran input. `hpp_math.py` + helper Decimal bersama
  `unit_utils.py` menghitung harga per kg × jumlah beli, isi kemasan, konversi,
  biaya satuan, takaran batch ÷ porsi dan jumlah HPP. Total model diabaikan.
  Quantity disimpan base_unit agar konsisten dengan stock paths raw existing.
- Harga bahan existing memakai weighted cost server kecuali perubahan nyata
  diminta/diapprove. Tebakan tidak boleh mengubah harga bahan toko. Manual
  memblokir angka perkiraan dan sumber yang tidak cocok; Estimasi tetap berlabel
  di resep/editor/laporan setelah approve. Harga bahan baru estimated needs_review.
  Kutipan/numerik diverifikasi, tetapi semantik input tetap perlu review manusia.
- Harga pembelian maksimal 2 desimal; unit cost Numeric(18,8), total tampilan
  HALF_UP 2 desimal. Purchasing bahan mempertahankan 8 desimal; produk tetap 2.
  Papan/dus/tray tidak punya isi tetap; kemasan harus punya ukuran eksplisit atau
  estimasi berlabel. Beras mentah tidak disamakan dengan berat nasi matang.
- Migration **112** menambah session/turn durable dengan FORCE RLS serta
  recipe.is_estimated. Semua history tersimpan; input 100k karakter/pesan,
  output 8192/16384 untuk repair schema, tanpa kuota harian chat biasa. Context
  besar memangkas katalog/turn lama sambil menjaga cerita terbaru serta draft
  terakhir lengkap angka/satuan/sumber/kutipan/catatan. Tidak klaim semua turn
  lama selalu masuk context model. Maksimal dua proses bersamaan per pengguna.
- POST pesan 202 setelah user turn tersimpan, BackgroundTasks punya AsyncSession
  sendiri + tenant scope dan lepas transaksi sebelum provider; UI polling GET
  2,5 detik. Lease 8 menit, retry request UUID sama; draft sebelumnya aman.
  Teks belum terkirim disimpan lokal. Jangan memakai history.replaceState di
  tengah rangkaian Server Actions create→send; update URL sesudah busy selesai
  dan hanya jika href berubah. No-op replaceState setelah refresh pernah membuat
  navigasi balik ke form macet. Regression refresh→form→chat ditambahkan.
- Approval lock session/brand, revision+fingerprint dan re-read dependencies.
  Perubahan harga/resep menimbulkan 409 + preview/revisi baru untuk review ulang.
  Repeat/concurrent approve idempotent, nama bahan existing dipakai ulang.
  Bahan/resep/hasil/audit/event/KG disimpan SATU commit, rollback lengkap saat
  gagal; jangan pakai audit helper yang commit sendiri. Resep lama soft delete.
- Setup tidak membuat OutletStock/restock/mengubah mode stok. Produk baru
  nonaktif dan harga jual diatur lewat Menu. Stok dicatat terpisah Bahan Baku.
  Gas/gaji/sewa belum masuk HPP bahan. KG + pgvector scoped jadi referensi,
  retrieval savepoint best effort, context cache seluruh outlet satu brand cleared.
- Endpoint `/ai/hpp-setup` Pro + tenant/user/outlet. Chat umum `/ai/chat` dan
  APK/native legacy **unchanged**, jangan menyebut seluruh chat lama sudah diganti.
- QA math 15 kasus/500 oracle, Postgres RLS non-superuser long chat/replay/repeat/
  concurrent approval/atomic rollback/actual POS+cancel/storefront/HTTP202 worker,
  provider nyata draft-only, browser chat + HPP/inventory/auth/stock-storefront
  lolos. Lima lebar kedua tema AA/44px/keyboard/200%/short viewport, textarea
  panjang dan source evidence. Tidak seed harga/resep/stok merchant untuk QA.
- Frontend aktif/tested `sha256:5fcc63cc7be259229df771488cfc30c0bc19146df25ff0381bbd18bd91be8ffb`;
  backend deploy docker cp terarah + alembic112 + restart existing container.
  **Jangan recreate backend**, hotfix lain masih melalui docker cp. Frontend
  `up -d --no-deps frontend`, APK mount tetap, native 1.6.31+198 unchanged.
  Empat layanan healthy. Review `docs/HPP_CHAT_REVIEW.md`, detail smoke SESSION.md.

## STATUS SEBELUM SETUP CHAT — ARSIP 2026-10-04

- **Bahan Baku web** dibuat lebih mudah dipakai dan sudah live, source `6d91aac`.
  `/dashboard/bahan-baku`: Tambah bahan langsung form kosong nama/harga/jumlah/
  satuan pembelian. Simpan bahan tidak restok; setelah save ada Catat stok.
  Tambah stok menyebut jumlah tambahan dan stok setelah simpan. Ubah harga dan
  Lihat pemakaian terpisah. Biaya operasional punya bagian/form estimasi harian
  sendiri, belum termasuk HPP bahan per porsi. Bahan yang masih dipakai di resep
  diarahkan melepas resep sebelum delete. Filter/search dari data aktual.
- Inventory null stock = belum dicatat, 0 = habis. Cost desimal dan
  cost_per_base_unit server ditampilkan terpisah dari pembelian terakhir (weighted
  average bisa berbeda). Kg/liter baru canonical gram/ml; edit existing tidak
  mengubah base_unit/unit_type, tetap row_version. Response price yang tanpa stock
  join harus mempertahankan loaded stock/minimum/used_in. Backend unchanged.
- Stock write belum idempotent: klik save dikunci, 500/network ambigu wajib
  reconcile/muat ulang tanpa replay otomatis. Draft validasi 400/422/409 tetap ada.
  Browser-to-Server-Action load transport error ditangkap agar loading tidak macet.
  Dialog native ditambah manual Tab/Shift+Tab trap; Escape/dirty confirm dan focus
  return sesudah cancel/reconcile tersedia. Jangan menghapus guard ini.
- Build/TypeScript, unit oracle backend, inventory/HPP/auth/stock-storefront
  browser lolos. Inventory lima lebar kedua tema, AA/placeholder/44px, keyboard,
  teks 200%, viewport pendek, pagination >100, network abort, 500 setelah simulated
  commit tanpa duplikasi. Writes hanya fixture; demo aktual 0 bahan tidak di-seed.
  HTTPS inventory dan HPP (13 produk, tiga lebar, dua tema), storefront actual
  menu/cart 320 px kedua tema lolos tanpa write bahan/resep/stok/mode/pesanan.
- Image inventory final/live
  `sha256:c7b54e58aa043ab5633b1c6b7d183de764cdcc8e2a0f5f8b250b166c53daec9c`.
  Frontend/backend/Postgres/Redis healthy. Frontend-only deploy; backend migration
  111 dan APK 1.6.31+198 tetap. Review/gate `docs/INGREDIENT_INVENTORY_REVIEW.md`,
  tes `tests/ingredient-inventory-browser.cjs`, log/screenshots `/tmp/selaris-inventory-*`.

- Alur HPP **web dashboard** disederhanakan sesuai keluhan Ivan, source `4f7934c`.
  Dashboard punya **Atur HPP** (`/dashboard/hpp`): pilih produk, pilih/buat bahan di
  tempat, isi harga + jumlah pembelian, takaran **satu porsi**, lihat biaya, simpan,
  lalu **Atur produk lain**. Entry dari Menu, Bahan Baku, Settings dan Laporan HPP.
  Tab Resep Menu memakai editor yang sama. Harga bahan berlaku untuk semua resep
  yang memakai bahan itu; stok fisik dan aktivasi mode tetap langkah tersendiri.
- Preview web mengikuti HPP backend: optional dikecualikan, gram/ml dikonversi ke
  base_unit bahan sebelum menyimpan quantity + quantity_unit. **Jangan mengubah
  base_unit ingredient existing atau helper deduct stock** untuk mempermudah UI.
  Resep lama berbeda unit perlu konfirmasi; catatan dan flag optional dipertahankan.
  Setelah save pakai total server dan refresh harga. Input harga/jumlah nyata kosong,
  preset Bahan Baku tidak lagi mengisi perkiraan harga seolah data pembelian nyata.
  Error save menjadi hasil Server Action aman, draft/retry tersedia, harga pakai
  row_version. Pesan stok awal tidak mengaku berhasil bila restok gagal.
- HPP yang ditampilkan adalah **modal bahan per porsi**, belum gas/gaji/sewa/biaya
  operasional. Selisih harga jual bukan laba bersih. Simpan resep tidak mengganti
  mode dan tidak menambah stok. Backend tetap memvalidasi resep produk stock-enabled
  (termasuk produk nonaktif yang stock_enabled) saat peralihan. Jangan membuat
  resep/harga/stok otomatis untuk Egg Tart, Kopi susu atau produk lain.
- Build produksi, TypeScript, tes unit dengan oracle helper Python backend,
  `tests/hpp-browser.cjs`, regresi auth, stok/storefront dan publik lolos. HPP
  diperiksa lima lebar/dua tema, AA, 44 px, fokus/Escape, teks 200%, viewport pendek,
  legacy units, optional/notes, pagination >100, 400/422/409/500/401 dan retry.
  Smoke baca demo aktual 13 produk, tiga lebar/dua tema lolos tanpa write toko.
  Review/gate lengkap di `docs/HPP_FLOW_REVIEW.md`.
- Frontend HPP terpasang dengan image final yang diuji
  `sha256:73c25119aa34589be27584400504aed915ffc071792bf35690108a016d3fa0f6`.
  Backend tetap migration 111, native/APK tetap 1.6.31+198. Temuan HPP native
  raw quantity/optional di bawah masih backlog, belum diubah dalam pekerjaan web.
- Setelah deploy source `4f7934c`, HPP HTTPS aktual (13 produk × tiga lebar × dua
  tema), link Settings dan storefront menu/cart aktual kedua tema 320 px lolos.
  Tidak membuat pesanan atau menulis bahan/resep/stok/mode toko. Seluruh layanan
  healthy, image frontend aktif sama dengan image final yang diuji.

- Revisi web profesional/premium sudah live, source `2ca827f`. Arahan terbaru Ivan menggantikan pilihan tipografi web sebelumnya: **Source Sans 3** untuk UI/form/angka, **Source Serif 4** untuk judul publik/auth, bobot merchant 600. Palet hangat/coral Sefrekuensi tetap; native dan APK tidak diubah oleh revisi ini. Antislop `during` tetap pilihan sesi, bukan preferensi global.
- Kalimat "Anda hanya memfoto notanya. Empat baris di atas tidak ada yang diketik manual" dihapus. Copy sekarang "Unggah nota, periksa hasilnya, lalu simpan pembelian." Landing memakai capture web terbaru dari data toko demo berlabel, bukan nota/angka buatan. Modul berupa daftar, paket tanpa badge populer, header/footer/download konsisten, dashboard menonjolkan pendapatan dan angka operasional, storefront HP memakai daftar produk dan kontrol 44 px. Chat bantuan memiliki error/retry serta Escape/fokus.
- Bug token Tailwind ikut ditemukan dan diperbaiki: `--color-base` membuat `.text-base` mengubah tinta menjadi warna latar. Ganti menjadi `--color-canvas`; jangan memperkenalkan alias warna yang berbenturan dengan nama ukuran font. Form merchant dijembatani ke surface/ink/control-border tema; success dark lebih terang.
- Build produksi, tiga regresi browser (`web-refinement-browser`, `auth-browser`, `stock-storefront-browser`) dan smoke data demo 16 route × dua lebar × dua tema lolos. Laporan lengkap/gate antislop `docs/WEB_REFINEMENT_REVIEW.md`. Frontend yang dipasang identik dengan image yang diuji: `sha256:f2d69d2af62a12014564b871e16fc0a21c33eaa05a70b53db98fadc26c6e7b28`. Semua container healthy; hanya frontend yang direcreate.
- Verifikasi HTTPS setelah deploy juga lolos: seluruh tes publik dan direktori data toko aktual, auth/dashboard/onboarding demo, menu/cart storefront 320 px pada kedua tema. Tidak mengirim OTP/WA/chat nyata atau submit order/pembayaran.
- Checkpoint lanjutan kerja disimpan di bagian Oktober `SESSION.md`: acuan kode terbaru `2ca827f`, status produksi/APK, perbaikan yang selesai, langkah persiapan HPP dan aktivasi Google, temuan native yang belum ditangani, bukti tes dan aturan deploy. Baca handoff itu sebelum melanjutkan; NEXT ACTION April pada SESSION adalah arsip.
- Setelah deploy hotfix web, smoke HTTPS storefront aktual `kasira-coffee` terang/gelap 320 px lolos untuk menu/cart, pilihan tema, kategori terpilih dan input fokus, tanpa page error atau submit pesanan. Semua layanan healthy; image frontend sama persis dengan image production yang diuji. Source hotfix sudah dipush ke `main` pada `20f79cc`; container fixture dibersihkan.

- Hotfix web Mode Stok + storefront sudah dipasang: log frontend menunjukkan digest 1800943633 berasal dari HTTP 400 "Belum punya resep: Egg Tart, Kopi susu" yang dilempar Server Action. `updateStockMode` sekarang mengembalikan hasil success/error sebagai data, menampilkan validasi asli tanpa membocorkan error 500, serta pesan sesi habis/koneksi gagal. UI tidak mengubah pilihan saat ditolak, mencegah klik ganda selama menyimpan, dan memberikan tautan Bahan Baku + Menu/tab Resep. Bahan Baku tersedia untuk Pro sejak mode simple agar persiapan resep tidak buntu; tier backend dan validasi kelengkapan resep tetap berlaku. Tidak otomatis mengganti mode outlet atau mengarang resep.
- Storefront memakai pasangan `surface-inverse`/`text-inverse` untuk tombol, kategori, badge, keranjang, status pembayaran/reservasi dan COD. Fokus input memakai surface-card; booking lama dijembatani ke palet Sefrekuensi dengan scope khusus, status tidak mencampur warna dengan putih literal, success dark scoped lebih terang. Kartu produk membungkus baris harga/kontrol agar tombol tambah jumlah tidak terpotong di 320 px. Production Docker build dan browser `tests/stock-storefront-browser.cjs` lolos: validasi 400, 422, 500 aman, 401, retry dan pindah dua arah; light/dark 320/768/1440, varian/Escape, input fokus, meja, tujuh fase order, tiga fase reservasi, booking dan COD kurir. Perubahan hanya web; APK terbaru tetap 1.6.31+198.
- Temuan audit terpisah untuk pemeriksaan native berikutnya: `recipe_provider.dart` masih memakai quantity mentah × costPerBaseUnit serta menjumlah bahan optional, sementara backend HPP memakai `unit_utils` dan melewati optional/satuan tidak cocok. Ini bukan penyebab error perpindahan mode yang Ivan jelaskan, dan tidak diubah pada hotfix web ini.

- Hotfix sync: akar error dibuktikan pada respons outlet aktual fbc68df5…: payments.order_id NULL (DP reservasi) masuk ke PaymentLocal.orderId String non-null → TypeError, rollback seluruh apply walaupun HTTP 200. Backend sekarang hanya mengirim pembayaran berpesanan untuk cache Drift; Flutter juga mengabaikan DP standalone. DP tetap berada di DB dan alur reservasi server. Backend fix sudah live sehat; rilis v1.6.31+198 selesai sukses pada CI 37199747458 (source fix 7740bd1). APK POS/Dapur bertanda tangan Selaris dan Firebase push diverifikasi lalu dipasang atomik di public/apk. Endpoint versi dan image backend memakai 1.6.31. Update dari 1.6.30 langsung ditimpa, tanpa uninstall/data reset. Backup APK 1.6.30 di /tmp/selaris-apk-before-1.6.31.
- Bug pagination ikut diperbaiki: Flutter dulu mengabaikan has_more; cursor server memakai record paling baru lintas tabel dan bisa melewati sisa tabel yang capped. Cursor sekarang tail paling awal dari tabel yang masih punya halaman, urutan SQL sama dengan tuple HLC ms/version/id termasuk recipe dan varian. Client melanjutkan pull tanpa push ulang, menyimpan watermark server halaman pertama setelah semua halaman selesai, backfill sekali untuk APK lama. Tes actual 68 halaman (limit 10) mencakup seluruh ID dibanding full pull, 522 order_items; seluruh halaman sukses diaplikasikan ke SQLite lokal. 14 unit backend (sync + auth) lolos; 14 tes Flutter termasuk 6 sync dengan fixture aktual lolos, serta regression error/retry. HTTPS user-agent Dart lolos 2 halaman dengan 522 item; analyzer nol error dan empat warning lama. Tidak menghapus data merchant/offline.

- Redesign sudah live di selaris.id: login, daftar, onboarding dan theme dashboard mengikuti Sefrekuensi. Backend sehat pada migration 111; seluruh container healthy.
- Smoke test production memakai login demo yang sudah dikonfigurasi: dashboard autentikasi, tema terang/gelap, 320 px, menu/Escape dan onboarding toko existing lolos tanpa mengirim pesan OTP.
- Login Google sudah diimplementasikan pada web + POS Flutter, tetapi empat konfigurasi Firebase Google belum diisi pemilik. UI menyatakan belum tersedia; OTP Sefrekuensi aktif. Detail setup dan fingerprint di `docs/GOOGLE_LOGIN.md`.
- Source main sudah dipush: `cdf2c87` redesign, `420aea1` tes onboarding, dan `7740bd1` hotfix sync. Rilis terbaru v1.6.31+198 (APK + AAB POS/Dapur), menggantikan 1.6.30+197; signing Selaris dan Firebase push dipertahankan. Metadata memakai catatan rilis per aplikasi; backend dan public/apk disinkronkan sesudah artifact tersedia.
- Semua toko adalah demo menurut instruksi Ivan; angka flag `is_demo` pada audit awal bukan batas otorisasi terbaru. Audit dan arah awal di bawah adalah catatan sebelum implementasi, bukan status deployment terkini.

## ARAH REDESIGN SELARIS × SEFREKUENSI — 2026-10-04

- Permintaan Ivan: mulai dari onboarding, lalu UI/UX mengikuti theme, warna dan konsep desain Sefrekuensi di server; kedua produk direncanakan bergabung. Login mendatang memakai Google/Gmail dan OTP Sefrekuensi.
- Antislop dipilih **during untuk sesi ini** (jawaban pengguna "1"); bukan preferensi global yang disimpan.
- Referensi kode: `/var/www/sefrekuensi`, HEAD `fcd2dec` pada branch `bond-tingkat` ketika diperiksa. Baca `AGENTS.md`, `CLAUDE.md`, `DESIGN.md`, lalu source terbaru; dokumen/screenshot lama memuat arah yang sudah digantikan.
- Acuan visual terbaru adalah **Sefrekuensi 2.0**: `mobile/app/lib/native/theme.dart` dan `frontend/src/app/globals.css`. Terang: latar `#F7F5F2`, kartu putih, teks `#282725`, fill coral `#E5A08C`, tinta tombol `#30241F`, aksen teks coral tua `#914C38`. Gelap: latar `#121212`, kartu `#27282B`, teks/fill utama `#F2EFEA`, aksen coral. Font native Plus Jakarta Sans; Space Mono untuk kode fungsional. Native default terang, pilihan gelap/ikut sistem tersedia. Web memiliki scope tema tersendiri.
- Komponen: radius input/tombol 14, kartu 20, sheet 28; skala spasi 4/8/12/16/24/32. Tombol utama min-height 48, warna rata, tanpa glow; bergerak singkat sebagai respons interaksi. Tombol Google mempertahankan identitas provider.
- Kontras pasangan yang dihitung dari token source: tinta tombol/coral, coral tua/latar terang, teks sekunder/latar terang, teks utama/latar gelap, teks sekunder/kartu gelap dan tinta tombol/fill gelap semuanya >=4.5:1. Ini pemeriksaan token, bukan audit seluruh layar.
- Native login Sefrekuensi: `auth_screen.dart` sekarang Google sebagai pintu utama Android; Apple juga ada di iOS. Jalur nomor WA lama dibuka lewat tautan. Backend `handlers/firebase_auth.go` memverifikasi Firebase ID token dan memetakan `firebase_uid` ke akun. Akun lama dihubungkan dari sesi yang sudah login melalui alur `login-cepat`, bukan dicocokkan otomatis ke email ketikan.
- Onboarding Sefrekuensi terbaru: `onboard_pilih_screen.dart` (25 September), pilihan kota/minat/tujuan, progress, retry, dan pending flag untuk melanjutkan saat app dibuka lagi. Yang diadaptasi untuk Selaris adalah pola interaksi; isi merchant tetap setup usaha.
- Selaris masih memakai Aurora pink/violet di `app/globals.css` dan `kasir_app/lib/core/theme/kasira_ds.dart`. Login/daftar web dan Flutter serta onboarding web/WelcomePage/ReadyPage dibaca sebagai cakupan awal yang perlu diselaraskan.
- **Google login belum ditemukan di auth Selaris**: model `backend/models/user.py` masih berbasis nomor + tenant, tanpa provider UID; register mensyaratkan OTP nomor + nama usaha + owner + PIN. Perlu kontrak identitas dan tautan akun lama/toko yang sama sebelum mengaktifkan pintu Google.
- **OTP Sefrekuensi sudah terhubung dan dikonfigurasi di backend produksi Selaris** (`enabled()` true). Service `backend/services/sefrekuensi.py` memakai partner OTP API + DM Yasmin/push. Kode tetap dibuat/diverifikasi Selaris: ini pengiriman OTP, belum login akun bersama. Tidak mengirim OTP atau login pengguna dalam pemeriksaan.
- Usulan awal untuk desain berikutnya: Google sebagai pintu utama, OTP Sefrekuensi sebagai jalur alternatif; sesudah identitas dikenali, user lama kembali ke tokonya, user baru lanjut setup usaha. Hubungan alternatif vs verifikasi berurutan belum ditetapkan pengguna.
- Pada audit awal sebelum izin implementasi, hanya dilakukan pemeriksaan referensi/source/konfigurasi. Screenshot auth September yang diperiksa adalah fixture lama, bukan bukti layout login terbaru. Status implementasi kini ada di bagian STATUS TERKINI.

## STATUS AKTUAL TERVERIFIKASI — 2026-10-04

Bagian ini mengoreksi ringkasan April di bawah. Entri lama dipertahankan sebagai riwayat, bukan status saat ini.

- Brand sekarang **Selaris**, domain kanonik **https://selaris.id**. API lama `kasira.online/api/v1/auth/app/version` masih HTTP 200.
- Git lokal bersih di `main`; HEAD lokal dan remote `origin/main` sama: `4aabf547bb3b0513fa9c39e644c0f3a5a5b2a3d9` (2026-09-11).
- Rilis GitHub terbaru **v1.6.29**, published 2026-09-11, tersedia APK + AAB POS dan Dapur. `version.json` checkout juga 1.6.29.
- **Deployment APK tertinggal:** endpoint update produksi masih **1.6.28**. `/api/download/pos` dan `/api/download/dapur` HTTP 200, ukuran cocok dengan APK bind-mount `public/apk/` bertanggal 2026-09-06.
- Manifest kedua APK lokal: `versionName=1.6.28`, `versionCode=194`, package sama `com.kasira.kasira_kasir`. Workflow 1.6.29 memisahkan `com.selaris.pos` / `com.selaris.dapur`; release notes mewajibkan sinkron sebelum uninstall aplikasi lama karena perubahan package.
- Migration **kode dan DB produksi: 110**, bukan 086.
- Container backend, frontend, PostgreSQL, Redis semuanya healthy. `/health` HTTP 200: DB ok, background tasks healthy, tidak ada task dead. `/health/background` HTTP 200; frontend lokal dan homepage selaris.id HTTP 200.
- Sampel hash backend aktif cocok dengan checkout: `backend/main.py`, `backend/api/routes/outlets.py`, `backend/services/xendit.py`, `backend/services/fonnte.py`. Hash `version.json` berbeda. Ini pemeriksaan sampel, bukan bukti seluruh deployment identik.
- DB: **7 tenant aktif**, termasuk **4 demo**; tier aktif 4 Starter + 3 Pro. Tidak ada tenant Business/Enterprise aktif.
- Outlet aktif belum memiliki `xendit_business_id`, own `xendit_api_key`, atau `xendit_callback_token`. **QRIS otomatis belum terbukti siap live**; keberadaan toggle QRIS bukan bukti aktivasi gateway.
- Token Fonnte platform tersedia; 1 outlet aktif memiliki own Fonnte token. Pengiriman OTP dan pemisahan nomor sender/admin belum diuji dalam pemeriksaan ini.
- Multi-outlet sudah memiliki endpoint create + batas tier (Starter 1, Pro 5, Business 20, Enterprise unlimited). Tidak ditemukan tenant dengan beberapa outlet aktif; kesiapan UI dan alur lengkap belum diuji. Status lama "belum mulai" terlalu mutlak.
- Cron root: 1 healthcheck setiap 2 menit dan 1 entri backup ditemukan. Eksekusi terakhir, delivery Telegram, dan restore backup belum diuji.
- Fitur September tercatat di CLAUDE.md/kode: varian produk, purchasing, keuangan, CRM/promo WA, online order/delivery, push notification, rebrand, serta perubahan rilis Android. MEMORY/SESSION/ROADMAP April tidak merangkum perkembangan ini.
- Pemeriksaan ini hanya membaca layanan dan DB; tidak melakukan deploy, transaksi, pengiriman pesan, atau aktivasi gateway.

Prioritas temuan: selaraskan distribusi APK/endpoint versi dengan keputusan migrasi v1.6.29, lalu verifikasi integrasi Xendit live dan OTP sesuai kebutuhan merchant.

## 🗺️ ROADMAP PROGRESS (Menuju Tier Starter)
- ✅ **FASE 0: Fondasi** (Semua Migration, Docker, VPS, Backend Core)
- ✅ **FASE 1: Auth** (OTP WA, JWT, Device Binding, Role Check)
- ✅ **FASE 2: Core POS Starter** (Products, Orders, Payment QRIS **Xendit xenPlatform**, Stock Deduct)
- ✅ **FASE 3: Flutter Kasir App** (15 layar + Inventory Powerhouse, GoRouter, Sync Engine, Offline Mode)
- ✅ **FASE 4: Owner Dashboard Next.js** (Owner Login, Laporan, Menu, Margin Tracking)
- 🟡 **FASE 5: Pilot** (Pre-launch hardening DONE 2026-04-25, monitoring DONE, Xendit live pending)
- 🟡 **FASE 6: Pro Features** (AI Chatbot multi-turn, Tab/Bon split bill, Warkop ad-hoc, Reservasi, Loyalty, Recipe/HPP, Knowledge Graph DONE; Multi-outlet pending)

## ✅ SELESAI
- [x] Migration Batch 1–8 (semua tabel, row_version, Golden Rules compliant)
- [x] CRDT Bug Fixes (HLC.receive & PNCounter.get_value)
- [x] Flutter Login OTP Flow (4 states with Riverpod)
- [x] Flutter QRIS Screen (Payment Modal, QrImageView, Timer, Polling)
- [x] Flutter Offline Mode (Connectivity monitoring, UI banner, CachedNetworkImage)
- [x] Backend Reporting Endpoint (`GET /reports/daily`)
- [x] Setup Alembic (alembic.ini, env.py) - CRITICAL FIX
- [x] Create Customer model and update models/__init__.py - CRITICAL FIX
- [x] Fix auth router prefix in api.py
- [x] Fix order items cascade to delete-orphan
- [x] Verify missing row versions in migrations
- [x] Update config.py (remove Midtrans keys, make ENCRYPTION_KEY required)
- [x] Create Storefront Connect API (GET /connect/{slug}, POST /connect/{slug}/order, GET /connect/order/{order_id})
- [x] Create Next.js Owner Dashboard (login, dashboard, menu, kasir, laporan, settings, payment, onboarding)
- [x] Create Next.js Storefront Public (menu, cart, order status)
- [x] Docker + VPS Ready (Dockerfile, docker-compose.yml, .env.example)
- [x] Create backend/scripts/seed_demo.py (idempotent, timezone, sequence)
- [x] Fix Connect API bugs (product fields, order sequence, error messages)
- [x] Fix Dockerfile.next for Next.js frontend
- [x] Fix Next.js auth (save tenant_id & outlet_id to cookies, X-Tenant-ID header)
- [x] Fix backend auth response to include tenant_id & outlet_id
- [x] Fix Flutter app entry point (DashboardPage -> LoginPage)
- [x] Audit Alembic migrations – 100% Golden Rules compliance
- [x] Fix Midtrans webhook multi-tenant (custom_field2, dynamic search_path)
- [x] Pre-deployment checks (CORS, Dockerfile, env vars, docker-compose)
- [x] Flutter Sync Engine (Drift Database, HLC, Dio API Client, Riverpod Integration)
- [x] Fix Storefront Payment Edge Cases (CRDT stock, outlet validation, online order status)
- [x] **FASE 3: Flutter Kasir App — 15 Layar Lengkap**
  - SplashPage + version checker | LoginPage | TableGridPage | PosPage | PaymentModal
  - PaymentSuccessPage | ReceiptPreviewPage | OrderListPage + OrderDetailModal
  - ShiftOpenPage | ShiftPage | LowStockAlertPage | SettingsPage + PrinterSettings
  - GoRouter setup | package_info_plus | build-apk.yml → GitHub Releases
- [x] **Migrasi Payment Gateway: Midtrans → Xendit xenPlatform**
  - Migration 057–058 (drop midtrans_*, add xendit_business_id, rename xendit_raw)
  - backend/services/xendit.py (create_sub_account, create_qris_transaction, verify_webhook)
  - Update payments + outlets route: QRIS via Xendit, platform fee 0.2%
- [x] **AppConfig + Real API Integration**
  - `AppConfig` singleton (SharedPreferences, first-launch flow)
  - `ServerSetupPage` (input URL VPS + ping test)
  - `CartProvider` + `ProductsProvider` dengan real API call
  - Save `tenant_id`, `outlet_id`, `phone` ke FlutterSecureStorage saat login
- [x] **VPS Deployment**
  - `kasira-setup.sh` (one-command: Docker, UFW, clone repo, .env, pg_dump cron, systemd service)
  - `backend/scripts/seed_admin.py` (idempotent: Tenant + Brand + Outlet + User admin)
- [x] **Offline-First Pure CRDT Stock** — selesai 2026-04-03
  - `tables.dart`: Products tambah crdtPositive + crdtNegative (G-Counter JSON)
  - `app_database.dart`: schemaVersion 2, migration addColumn crdtPositive+crdtNegative
  - `pn_counter.dart`: PNCounter utility (increment, merge, getValue, fromJson, toJson)
  - `cart_provider.dart`: offline deduct = PNCounter.increment(crdtNegative, nodeId, qty) — bukan LWW
  - `sync_service.dart`: kirim + terima crdt_positive/crdt_negative saat sync
  - Backend sync: merge PNCounter via process_stock_sync (sudah ada di sync.py)
  - Merge rule: max per nodeId → commutative, associative, idempoten — tidak ada conflict
  - `cart_provider.dart`: submitOrder() cek koneksi → online=backend, offline=Drift SQLite
  - Offline: order+items disimpan lokal (isSynced:false), stockQty deduct di Drift sebagai guard anti-oversell
  - Backend sync: setelah order_items diproses, trigger deduct_stock (idempoten via stock.sale event check)
  - `stock_service.py`: _is_sale_already_recorded() — skip deduct jika stock.sale event sudah ada untuk order_id ini
  - Starter: offline jalan penuh, source of truth tetap events table saat sync ke server
  - `backend/models/event.py` — Event model (append-only, partitioned by outlet_id)
  - `backend/services/stock_service.py` — deduct_stock, restock_product, get_stock_history, recompute_stock_from_events
  - `orders.py` — stock deduct sekarang lewat stock_service (tulis stock.sale event dulu)
  - `products.py` restock — sekarang lewat stock_service (tulis stock.restock event dulu)
  - `schemas/stock.py` — tambah outlet_id di ProductRestock
  - Starter: events table = source of truth, products.stock_qty = cache
  - Pro (future): + outlet_stock CRDT untuk offline sync
- [x] **Tier Gating Pro Features** — selesai 2026-04-03
  - `deps.py`: `require_pro_tier` dependency, PRO_TIERS = {pro, business, enterprise}
  - `loyalty.py` + `reservations.py`: router-level gate, 403 untuk Starter
  - `auth.py /pin/verify`: cek tier tenant → 403 Starter (Dapur App = Pro only)
  - Starter: POS, Stock, Shift, Laporan, Connect | Pro+: Dapur, Loyalty, Reservasi, Partial Payment
- [x] **Feature D: Loyalty Points** — selesai 2026-04-02
  - Migration 059: `customer_points` + `point_transactions` (UNIQUE order_id+type, row_version)
  - `backend/api/routes/loyalty.py` — 4 endpoint: balance, earn (idempoten), redeem (optimistic lock), history
  - `backend/api/api.py` — include loyalty router
  - Flutter: `loyalty_provider.dart` (FutureProvider.family), `loyalty_redeem_widget.dart` (slider),
    `loyalty_history_page.dart` (gradient card), `cart_panel.dart` (integrated redeem + grand total)
  - `main.dart` — route `/loyalty/:customerId`
  - Aturan: 1 poin/Rp10.000, 1 poin=Rp100, min 10 poin untuk redeem
- [x] **Feature B: Kasira Connect Storefront** — selesai 2026-04-02
  - `connect.py`: ganti Midtrans → Xendit QRIS (reference_id = tenant_id::payment_id, platform_fee 0.2%)
  - `connect.py`: payment_method di ConnectOrderInput (cash/qris), cash → langsung paid+preparing
  - `connect.py`: POST response + GET /orders/{id} sekarang include full payment + items data
  - `payments.py` webhook: setelah order confirmed → update connect_orders.status = 'confirmed'
  - `app/actions/storefront.ts`: error handling real, mock data include payment object
  - `app/[slug]/order/[id]/page.tsx`: QRIS display + countdown MM:SS + auto-refresh saat expired
- [x] **Feature A: Flutter Dapur App (Kitchen Display)** — selesai 2026-04-02
  - Entry point terpisah: `kasir_app/lib/main_dapur.dart`
    → build dengan `flutter build apk --target lib/main_dapur.dart`
  - `features/dapur/providers/dapur_provider.dart`
    → DapurNotifier: auto-polling Timer setiap 8 detik (configurable)
    → fetchOrders: GET /orders/?status=pending,preparing,ready + GET /orders/?status=done&today=true
    → updateStatus: optimistic update + conflict detection row_version (409 → auto-refresh)
    → dapurStatsProvider: computed stats dari state
  - 6 halaman dapur:
    1. `dapur_splash_page.dart` — dark mode splash, cek AppConfig → /dapur/login atau /dapur/dashboard
    2. `dapur_login_page.dart` — numpad PIN 6 digit, tanpa OTP, panggil POST /auth/pin/verify
    3. `dapur_dashboard_page.dart` — grid 3 tab (Antrian/Dimasak/Siap Saji), badge "PESANAN BARU!" real-time,
       bottom sheet detail per order, auto-refresh indicator, PESANAN BARU flash indicator
    4. `dapur_completed_page.dart` — list pesanan selesai hari ini
    5. `dapur_statistik_page.dart` — stat cards + progress bar per status + alert urgent orders (>15 menit)
    6. `dapur_settings_page.dart` — toggle suara, interval refresh slider (5–30 detik), logout
  - `widgets/order_queue_card.dart` — card per order: timer merah >15 menit kuning >10 menit,
    status badge, 1-tap aksi (Mulai Masak → Siap Saji → Selesai)
  - Backend: `POST /auth/pin/verify` — standalone login phone+PIN (untuk dapur, tanpa OTP)
    → audit log setiap login, return JWT + tenant_id + outlet_id
  - `login_page.dart` — simpan `phone` ke FlutterSecureStorage saat OTP verify (dibutuhkan dapur)
  - `build-apk.yml` — build 2 APK: `kasira-pos-v*.apk` + `kasira-dapur-v*.apk`
  - GoRouter dapur: /dapur → /dapur/login → /dapur/dashboard → /dapur/completed,statistik,settings

- [x] **Feature E: Reservasi + Booking via Connect** — selesai 2026-04-03
  - `backend/models/reservation.py` — Table + Reservation models (row_version, ENUM)
  - `backend/api/routes/reservations.py` — owner CRUD: list/get/confirm/cancel/complete
    → confirm: set meja reserved (Golden Rule #24)
    → cancel/complete: release meja (Golden Rule #24)
    → log_audit setiap WRITE (Rule #2), optimistic lock row_version (Rule #33)
  - `backend/api/routes/connect.py` — tambah 3 endpoint:
    → GET /{slug}/tables → meja tersedia untuk booking form
    → POST /{slug}/booking → buat booking (tanpa login, WA confirmation)
    → GET /bookings/{id} → status polling
  - `backend/api/api.py` — include reservations + loyalty router
  - `app/actions/storefront.ts` — getAvailableTables, createBooking, getBookingStatus
  - `app/[slug]/booking/page.tsx` — form: nama, telepon, tanggal, jam, tamu, meja, catatan
  - `app/[slug]/booking/[id]/page.tsx` — status polling (pending/confirmed/cancelled)
  - `app/[slug]/page.tsx` — tombol "Reservasi Meja" saat cart kosong
- [x] **Feature D (Loyalty) — file yang hilang dibuat ulang** — 2026-04-03
  - `backend/migrations/versions/059_loyalty_points.py` — customer_points + point_transactions
  - `backend/models/loyalty.py` — CustomerPoints + PointTransaction models
  - `backend/api/routes/loyalty.py` — 4 endpoint: balance, earn (idempoten), redeem (optimistic lock), history

- [x] **Feature F: FASE 5 Pre-Pilot** — selesai 2026-04-03
  - Sentry Backend: `sentry-sdk[fastapi]>=2.0.0` di requirements.txt
    + init di `backend/main.py` (only if SENTRY_DSN set, traces_sample_rate=0.1, send_default_pii=False)
    + `SENTRY_DSN` di config.py + .env.example
  - Sentry Frontend: `@sentry/nextjs` di package.json
    + `sentry.client.config.ts` + `sentry.server.config.ts`
    + `instrumentation.ts` (Next.js 14+ native, no experimental flag)
    + `next.config.ts` wrapped dengan `withSentryConfig` (conditional on NEXT_PUBLIC_SENTRY_DSN)
  - APK ke R2: `build-apk.yml` tambah step upload ke Cloudflare R2 (S3-compatible API)
    + Upload kedua APK (pos + dapur) ke `s3://{R2_BUCKET}/apk/`
    + Generate + upload `version.json` ke R2 (Flutter baca ini saat startup — Golden Rule #14 + #15)
    + GitHub Secrets: R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET, R2_PUBLIC_URL
  - `.env.example` update: ANTHROPIC_API_KEY, SENTRY_DSN, NEXT_PUBLIC_SENTRY_DSN, R2 vars (commented)
  - `kasira-setup.sh` update: prompt ANTHROPIC_API_KEY + SENTRY_DSN saat setup VPS
  - pg_dump cron: sudah ada di kasira-setup.sh (tiap 6 jam ke /var/backups/kasira) — ✅ verified OK
  - UptimeRobot: manual setup di dashboard — monitor http://VPS_IP:8000/ dan http://VPS_IP:3000/

## ⏳ IN PROGRESS (per 2026-04-26)
- VPS sudah live: Ubuntu 22.04, semua container running (backend:8000, frontend:3000, db:5432, redis:6379)
- Admin: phone 6285270782220, outlet slug: kasira-coffee (MASTER_OTP sudah dihapus 2026-04-25 — production OTP WA only)
- APK terbaru: **v1.0.51** (POS + Dapur, fix split-bill float vs Decimal), download via GitHub Releases
- Migration terakhir: **086** (`outlets.xendit_callback_token` — BYOK Phase 2)
- Telegram healthcheck cron LIVE (state-change throttle, anti-spam)
- 25 tenant siap pilot (90% confidence cap, 30 conservative cap per `project_publish_readiness.md`)

## ✅ MAJOR MILESTONES 2026-04-12 → 2026-04-26

### Senior Audit + 17 CRITICAL Fixes (2026-04-19)
- 17/17 CRITICAL findings RESOLVED — sync idempotency dedup, HPP unification (4 raw-multiply sites), PRICING_COACH fail-closed Sonnet→Haiku fallback, Fonnte singleton + retry + circuit breaker, Xendit retry+webhook idempotency, async supervisor auto-restart, subscription tier lifecycle + cascade downgrade, sync cursor-based pagination
- Disaster Recovery: R2 restore automation + runbook (CRITICAL #9)
- Observability: Prometheus metrics + structured logging + health aggregate (#10)

### Flutter UX Hardening Batch #14-#18 (2026-04-20)
- Rule #50 outlet scope (anti cross-outlet leak)
- Multi-outlet sync + phone normalize + modal protection
- Printer lock + sync resilience + async boundary
- Node ID isolation `sha256(device|user)` + orphan cleanup + hardened logout
- v1.0.32 published

### Adaptive UI + AI Multi-Turn (2026-04-21)
- Batch #22-#23: AI multi-turn chat via Redis-only session store + Flutter wire + HLC merge + persistent idempotency
- Batch #24: backend hardening & hygiene
- Batch #25: AI chat UX polish v1.0.35
- Batch #26-#27: Adaptive domain classify endpoint + waitlist + AI guardrail + adaptive upgrade sheet + coming soon
- Migration 081 (`sync_idempotency`), 082 (`sync_pagination_indexes`), 083 (`xendit_reliability`)

### Inventory Powerhouse + KG Price Events (2026-04-22)
- Batch #28: POS stock visual guard (isAvailable + isOutOfStock gate)
- Batch #29: Inventory Powerhouse — tabbed Produk & Stok (Flutter v1.0.36)
- Backend: KG Price Events (margin drift WA alert)
- Backend: superadmin waitlist monitoring endpoint

### Starter Margin Tracking (2026-04-24 → 2026-04-25)
- Migration 084: `products.buy_price` untuk Starter margin tracking
- Backend Fase 2: restock unit_buy_price + `GET /reports/margin`
- Flutter Fase 3: Drift v5 + restock buy_price + Untung-Rugi tab
- Dashboard: buy_price form + `/laporan/margin` page (close margin tracking gap)
- UX: clarify "modal" vs "stok" untuk merchant non-technical
- v1.0.39 published

### Split-Bill Float-vs-Decimal Hotfix (2026-04-26 EOD)
- Bug: `pay_items_modal.dart:_selectedTotal` pake double float multiply tanpa quantize-per-share, sementara backend `tab_service.py:items_proportional_due()` quantize via `Decimal('0.01')`. Drift Rp 0.0045/share → backend reject "Nominal pembayaran kurang" walau display match.
- Reproduced: tab cappucino real merchant tax-inclusive ratio non-integer (5K/55K=0.0909..)
- Fix `72f1fff`: `_q2()` helper di Flutter mirror backend quantize. APK v1.0.51 built+deployed kasira.online.
- Sweep agent scheduled: `trig_01PsJEKFr2KEDJF5SBm8opu5` fires 2026-05-03 — audit other proportional compute sites.

### Pre-Launch Hardening (2026-04-25)
- Remove MASTER_OTP bypass (production OTP WA only)
- Xendit reconciliation hardening
- Flutter QRIS polling 30s timeout + retry dialog (FIX #2 security audit)
- RLS bypass added to payment_reconciliation (FIX #3 follow-up — RLS background task gotcha)
- v1.0.40 published

### Split-Bill Humanity + Warkop Ad-Hoc (2026-04-25)
- Split-bill data integrity — table release guard untuk active tab (commit `9762674`, gotcha #15)
- Flutter v1.0.42-v1.0.45: split-bill UX gaps — table tap, info card, grid sub-badge, flow & dashboard nav, active list missing, per-split receipt
- **Migration 085**: warkop ad-hoc per-item payment (`order_items.paid_at` + pay-items endpoint)
- Phase A SHIPPED: pay_items_modal + table_actions_sheet
- Source-of-truth split: `tab.paid_amount` (split/full) vs `items.paid_at` (pay-items adhoc)

### Telegram Healthcheck (2026-04-25)
- `/health` monitor → Telegram bot self-alert via cron (LIVE)
- Replace healthchecks.io plan, pivot karena signup difficulty + Fonnte self-send block
- State-change throttle (anti-spam)

## ✅ AI CHATBOT OWNER (2026-04-09) — Pro Feature
- [x] Chat UI: `app/dashboard/ai/page.tsx` (SSE streaming, suggestion buttons, purple theme)
- [x] SSE Proxy: `app/api/ai/route.ts` (Next.js proxy, httpOnly cookie auth)
- [x] Outlet helper: `app/api/ai/outlet/route.ts`
- [x] Sidebar nav: `app/dashboard/layout.tsx` — "AI Asisten" + PRO badge
- [x] Pro tier gate: `backend/api/routes/ai.py` — query tenant.subscription_tier, 403 Starter
- [x] Tenant model container sync (subscription_tier missing di container lama)
- [x] Admin tenant upgraded ke `pro` di DB
- **DONE**: ANTHROPIC_API_KEY sudah di-set dan backend rebuilt (2026-04-09)

## ✅ FIX REGISTER FLOW (2026-04-09)
- [x] `otp/send` sekarang terima `purpose: "register"` — skip cek user exists, tolak jika nomor sudah terdaftar
- [x] `auth.ts` pakai BACKEND_INTERNAL_URL + sendOtp() terima purpose param
- [x] `register/page.tsx` kirim purpose register

## ✅ BUG FIX 2026-04-09 — Realtime Sync + Order Multi-Item
- [x] Flutter: `ref.invalidate()` dashboardProvider/ordersProvider/productsProvider setelah payment sukses & sync
- [x] Backend: `selectinload().joinedload()` → `selectinload().selectinload()` di create_order (fix MissingGreenlet crash >1 item)
- [x] Backend: `metadata=` → `event_metadata=` di stock_service.py (field name salah)
- [x] `payment_success_page.dart` → ConsumerStatefulWidget (butuh ref untuk invalidate)
- Commits: `3358b34` + `adf20a9` pushed, backend di-restart via docker cp

## ✅ BUG FIX 2026-04-05 — Data Mock + Payment
- [x] `shift_open_page.dart`: ganti TODO mock → real `POST /shifts/open`, simpan shift_session_id ke FlutterSecureStorage
- [x] `payment_modal.dart`: cash tidak lagi silent fail — tampil error jika shift belum buka / payment gagal + kirim shift_session_id
- [x] `backend/api/routes/customers.py`: buat route GET /customers/ + POST /customers/
- [x] `backend/api/api.py`: include customers router
- [x] `customer_selection_modal.dart`: ganti 5 mock hardcoded → real API call + onSelected callback ke cartProvider
- [x] `add_customer_modal.dart`: ganti TODO → real POST /customers/
- [x] `cart_provider.dart`: tambah customerName di CartState, setCustomer() terima name
- [x] `cart_panel.dart`: tampilkan nama pelanggan yang dipilih, pass onSelected callback
- NOTE: File backend harus di-`docker cp` ke container karena tidak ada volume mount kode

## ✅ TAB/BON + SPLIT BILL (2026-04-09) — Pro Feature
- [x] Migration 062: `tabs` + `tab_splits` tables, `tab_id` FK di orders
- [x] Models: `Tab` + `TabSplit` (SQLAlchemy, relationships, row_version)
- [x] Schemas: `TabCreate`, `SplitEqualRequest`, `SplitPerItemRequest`, `SplitCustomRequest`, `PaySplitRequest`
- [x] API Routes: `backend/api/routes/tabs.py` — 10 endpoints:
  - `POST /tabs/` — buka tab (link ke meja)
  - `GET /tabs/` — list tabs per outlet
  - `GET /tabs/{id}` — detail tab + splits
  - `POST /tabs/{id}/orders` — tambah order ke tab
  - `POST /tabs/{id}/split/equal` — split rata (÷ jumlah orang)
  - `POST /tabs/{id}/split/per-item` — split per item (assign item ke orang)
  - `POST /tabs/{id}/split/custom` — split nominal bebas
  - `POST /tabs/{id}/pay-full` — 1 orang bayar semua
  - `POST /tabs/{id}/splits/{split_id}/pay` — bayar per orang (bisa beda metode: cash/QRIS)
  - `POST /tabs/{id}/cancel` — batalkan tab
- [x] Pro tier gate (require_pro_tier dependency)
- [x] Semua WRITE endpoint ada audit log
- [x] Optimistic locking (row_version) di semua update
- [x] Idempotency key di payment
- [x] Migration + container deployed, backend running
- [x] Flutter UI: tab_provider.dart, tab_list_page.dart, tab_detail_page.dart
- [x] Flutter widgets: open_tab_modal.dart, split_bill_modal.dart, pay_split_modal.dart
- [x] GoRouter: /tabs + /tabs/:tabId
- [x] Dashboard: tombol "Tab / Bon" di header

## ❌ BELUM MULAI / OPEN (per 2026-04-26)
1. ~~**ANTHROPIC_API_KEY**~~ — ✅ DONE 2026-04-09
2. ~~**UptimeRobot**~~ — REPLACED 2026-04-25 oleh Telegram healthcheck cron (signup HC.io susah, Fonnte self-send block)
3. **Xendit sub-account** — daftarkan outlet di Xendit untuk aktifkan QRIS production (outlets.xendit_business_id masih NULL untuk live merchant)
4. **Multi-outlet (Business tier)** — belum mulai, terakhir di FASE 6 belum disentuh
5. **APK v1.0.46 deploy** — warkop pattern Phase A udah merge ke main, build APK pending dispatch
6. **Vultr credit $300** — expire 2026-05-11 (`project_vultr_credit.md`), reminder 10 Mei cek dashboard
7. **Fonnte device pisah** — owner nomor = device = WA block self-send (`project_fonnte_otp_gotcha.md`), pisahin sender vs admin nomor sebelum publish

## Keputusan Teknikal (JANGAN DIUBAH TANPA ALASAN)
- ORM: SQLAlchemy async (bukan Tortoise)
- Migration: Alembic
- Validation: Pydantic v2
- Auth: PyJWT + bcrypt
- Background: Celery + Redis
- Flutter state: Riverpod
- Flutter offline: Drift
- HTTP Flutter: Dio + Retrofit
- Printer: bluetooth_print package
- Multi-tenant: schema-per-tenant di PostgreSQL
- AI streaming: SSE (bukan WebSocket) untuk chatbot
- Payment: **Xendit xenPlatform QRIS** + idempotency key (Master-Sub Account, platform fee 0.2%)
- Tax: PB1 10%, PPN 12%, service charge configurable
- Loyalty: 1 poin/Rp10.000 earn, 1 poin=Rp100 redeem, min 10 poin, UNIQUE(order_id,type)
- Dapur App: entry point terpisah main_dapur.dart, polling 8 detik, dark UI theme
- PIN Login: `/auth/pin/verify` untuk dapur (phone+PIN tanpa OTP)
- AI Model: Haiku default, Sonnet hanya Pro+/complex task — via get_model_for_tier()
- AI Context cache: Redis key ai:context:{outlet_id}, TTL sampai 00.00 WIB
- AI SSE format: {type: chunk/done/error, content, intent, tokens_used, model}

## Branch Git
- Branch aktif: `main`
- Semua commit langsung ke `main`, push ke `origin/main`

## Lanjut Berikutnya (per 2026-04-26)
Production-ready. Fokus pivot ke **acquisition + monetisation**:
1. **Build & deploy APK v1.0.46** — warkop ad-hoc pattern Phase A
2. **Onboard pilot merchant** — 25 tenant cap aman, 30 conservative
3. **Xendit live activation** — daftarkan sub-account untuk live QRIS (sandbox sudah test)
4. **Multi-outlet (Business tier)** — design + migration + tier gating
5. **Marketing landing page polish** — SEO sudah, tinggal copy + testimonial pilot

## Context Files Status
- context/database.md    → ⏳ In Progress
- context/auth.md        → ⏳ Belum dibuat
- context/orders.md      → ⏳ Belum dibuat
- context/inventory.md   → ⏳ Belum dibuat
- context/payment.md     → ⏳ Belum dibuat
- context/flutter-kasir.md → ⏳ Belum dibuat
- context/connect.md     → ⏳ Belum dibuat
- context/dapur.md       → ⏳ Belum dibuat

## IMPLEMENTASI REDESIGN DAN GOOGLE LOGIN — 2026-10-04

- Ivan menegaskan semua toko di server adalah demo dan mengizinkan perubahan langsung, sekaligus meminta panduan pendaftaran login Google.
- Web login/register/onboarding baru mengikuti token Sefrekuensi September 2026 (coral, warm white, charcoal, Plus Jakarta Sans). Theme toggle tersimpan, dashboard memakai palette yang sama. Onboarding usaha mengarah ke produk pertama; tidak membuat stok fiktif.
- Backend Google memakai verifikasi Firebase ID token RS256 (aud/iss/exp/iat/sub wajib, provider google.com, email terverifikasi). Google pertama kali + OTP nomor menghubungkan user/toko lama; nomor baru mendapat proof sekali pakai untuk register. Tautan tidak berdasarkan email ketikan. Schema 111 menambah project/uid/email nullable dengan unique/check constraint.
- Backend sudah direcreate dan sehat, database sudah revision 111. Source runtime lama dibandingkan seluruh file .py: perbedaan hanya perubahan task ini. Backup DB/source ada di /tmp/selaris-before-redesign-20261004.dump dan /tmp/selaris-backend-before-redesign.
- Google belum diaktifkan pada environment: empat GOOGLE_FIREBASE_* masih menunggu konfigurasi Firebase pemilik. Provider API mengembalikan google.enabled=false dan sefrekuensi=true; UI menjelaskan Google belum tersedia.
- Flutter POS: theme/font dibundel, welcome ringkas, OTP Sefrekuensi utama, Google login dan tautan nomor, business setup, PIN lokal, ready page scrollable. Register tidak lagi memakai PIN sementara tetap 000000; update PIN server harus berhasil sebelum lanjut.
- Panduan lengkap beserta fingerprint upload sertifikat publik: docs/GOOGLE_LOGIN.md. Gunakan project Firebase Sefrekuensi untuk UID yang sama; jika pindah project, samakan kredensial FCM backend.
- Validasi: 8 unit tests Google; integrasi Postgres toko lama/baru/replay; upgrade-downgrade-upgrade 111; 8 widget tests pada 320/768 px dan teks 160%; browser click-through dan WCAG AA pada 320/375/768/1440 dan kedua tema. Production web build dan APK release lokal lolos. Analyzer: nol error, empat warning lama. Delivery gate: docs/REDESIGN_REVIEW.md.
- APK lokal hanya validasi build (tanpa google-services.json). Distribusi harus memakai CI yang mempertahankan secret Firebase dan signing rilis. Rilis v1.6.30+197 dari CI sudah dipasang; jangan menyalin APK lokal tanpa Firebase ke public/apk sebagai pengganti rilis. Sertifikat APK CI cocok dengan fingerprint pada panduan. Resource default_web_client_id belum ada: setelah Google diaktifkan pada konsol, unduh JSON baru, perbarui secret lalu rebuild versi berikutnya.
