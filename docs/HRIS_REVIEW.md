# HRIS tahap pertama

Ivan menyetujui pembangunan tahap awal dengan "gas", 6 Oktober 2026,
setelah pembahasan profil karyawan, penempatan outlet, jadwal, dan absensi.
Halaman web `/dashboard/hris` memakai nama **Tim & absensi** di navigasi.

## Perilaku

- Profil karyawan terpisah dari User/POS: kode KRY otomatis, nama, tugas,
  outlet penempatan, kontak opsional, tanggal mulai/selesai, status aktif,
  dan catatan pengelola. Profil dapat dibuat tanpa akun kasir. Menghubungkan
  satu akun ke dua profil ditolak. Profil tidak membuat akun POS atau
  mengubah izin login akun tersebut. Menonaktifkan profil menyimpan riwayat.
- Pemilik `User.is_superuser`, atau Role tenant dengan permission JSON
  `hris_manage: true`, boleh mengelola tim. Permission diperiksa sebelum
  replay permintaan. Akun lain hanya membaca profil/jadwal/kehadiran dirinya
  yang terhubung; kontak dan catatan profil pengelola tidak ditampilkan.
  Akun tanpa profil mendapat penjelasan untuk meminta bantuan pemilik.
- Satu jadwal dan satu catatan kehadiran per karyawan per tanggal kerja.
  Jadwal memakai waktu outlet, boleh melewati tengah malam, maksimal24jam.
  Jadwal yang bertabrakan ditolak, termasuk antar outlet dalam bisnis.
  Jadwal/tanggal/identitas catatan tidak dapat dipindah melalui edit;
  batalkan catatan keliru dengan alasan, lalu buat yang benar.
- Kehadiran: hadir, izin, sakit, cuti, libur. Hadir memerlukan jam masuk,
  jam pulang opsional, urutan waktu valid dan tidak di masa depan.
  Masuk lewat tengah malam dapat memakai tanggal mulai jadwal malam yang
  sesuai; aturan yang sama berlaku saat pengelola mengoreksi catatannya.
  Status lain tidak memakai jam masuk/pulang dan memerlukan alasan.
  Izin/cuti/libur yang telah dikonfirmasi boleh dicatat untuk tanggal depan.
  Hanya pengelola yang mencatat status tersebut pada tahap ini.
- Akun terhubung dapat mencatat masuk/pulang **di web ini** dengan waktu
  server. Masuk di outlet penempatan, atau outlet jadwal yang sedang
  berjalan. Jadwal malam mempertahankan tanggal kerja ketika masuk lewat
  tengah malam. Pulang menutup catatan terbuka yang sama, termasuk saat
  profil sudah dinonaktifkan. Tidak ada GPS, foto, atau klaim bukti lokasi.
- Pengelola mengoreksi waktu/status dengan alasan dan versi data terbaru.
  Pembatalan menyimpan audit dan soft delete. Jadwal dengan kehadiran belum
  dapat diedit/dibatalkan sebelum catatan kehadiran yang keliru ditangani.
  Akun/outlet penempatan tidak bisa diganti selama kehadiran masih terbuka.
- Durasi hanya untuk catatan yang sudah pulang, berupa menit tercatat;
  belum mengurangi istirahat atau menentukan lembur/gaji. Sumber awal
  manual versus akun karyawan ditampilkan; koreksi tersimpan di AuditLog.
- Daftar50 per halaman, nama/kode dicari secara literal, status aktif/nonaktif
  untuk daftar profil. Pilihan karyawan aktif berasal dari seluruh outlet
  tenant, dengan pencarian dan pagination50. Akun kasir aktif menjadi pilihan
  penghubung profil; penghubung akun tidak aktif yang sudah ada dapat dipertahankan.
- Ringkasan mengikuti outlet dan periode1..31hari: profil aktif yang ditempatkan
  di outlet saat ini; jumlah jadwal, kehadiran dan izin/cuti/libur dalam periode;
  catatan terbuka serta jadwal yang sudah mulai tanpa catatan. Filter daftar
  tidak mengubah ringkasan. Belum tercatat **tidak otomatis berarti bolos**.
  Semua tanggal kerja memakai zona Outlet.timezone, termasuk WIB/WITA/WIT.
- Loading, error/retry, daftar kosong, dan belum ada outlet ditampilkan
  secara terpisah. Data lama tidak disajikan sebagai ringkasan baru saat gagal.
  InventoryDialog mendukung fokus, Escape dan keyboard. Form dibekukan saat
  penyimpanan belum pasti; permintaan sama dapat dilanjutkan setelah close/reload.

## Penyimpanan dan konteks

- Migrasi113 dari112 menambah `hr_employees`, `hr_schedules`, `hr_attendance`;
  seluruhnya FORCE RLS tenant, employee FK composite tenant/id, partial unique
  per hari dan satu kehadiran terbuka. Migration memberikan privilege hanya
  tiga tabel ini pada role aplikasi existing bila dikonfigurasi dan tersedia;
  role tersebut harus tidak superuser/bypassRLS. Tidak mengubah tabel POS,
  stock, Shift kas/laci, order, pelanggan, atau expense.
- Semua writes UUID wajib, fingerprint user/action/entity/payload, advisory
  lock tenant/request serta per karyawan. Hasil dan snapshot AuditLog dalam
  transaksi yang sama. Replay sama satu hasil; payload berbeda409. Edit dan
  void memakai row_version. Tidak memakai helper audit yang commit terpisah.
- Browser menyimpan permintaan pending dalam sessionStorage per hash tenant/user.
  Bila storage tidak tersedia, hanya bertahan di memory halaman. Server Action
  memeriksa identitas workspace authenticated sebelum write. Putus koneksi
  browser-ke-server juga melepas busy state tanpa membuang permintaan pending.
- `GET /hris/setup`, `/workspace`, `/employee-choices`, serta CRUD/void/punch
  memakai auth existing. Workspace menyediakan scope, basis
  `recorded_attendance_and_schedules`, periode, timezone, generated_at.
  Data faktual dapat dipakai integrasi AI berikutnya setelah aksesnya diatur.
  **Belum menambahkan payroll, perhitungan pajak/BPJS/lembur, approval cuti
  staf, reminder terjadwal, absensi native/offline, atau HRIS ke chat utama.**
  Catatan manusia tetap data, bukan instruksi untuk asisten.

## Desain

Design Read diumumkan sebelum edit dengan Anti Slop, dial ENERGY1/RHYTHM1/
MOTION1. Audiens pemilik, pengelola dan karyawan outlet. Mengikuti token/font
Selaris, Keuangan dan Pelanggan: CTA menyesuaikan pekerjaan aktif, tab dengan
status terpilih, ringkasan sebelum daftar, baris identitas karyawan dan waktu.
Whitespace memisahkan konteks outlet, angka, dan catatan; panel berfungsi
mengelompokkan data. Users existing dipakai di navigasi karena menunjuk tim.
Panah hanya menandai rentang mulai-selesai, bukan ornamen CTA. Tanpa aset
gambar baru, dekorasi, animasi, atau janji pemasaran AI.

## Verifikasi

- PASS29unit: validasi HRIS, jadwal malam/tanggal outlet, waktu hadir/status
  izin, koreksi masuk sesudah tengah malam dalam jadwalnya, dan regresi pelanggan/keuangan/pembelian/HPP. Log `/tmp/selaris-hris-unit.log`.
- PASS PostgreSQL nyata dan HTTP ASGI terisolasi, role aplikasi non-superuser,
  tenant sintetis. Create/replay concurrent, fingerprint conflict, akun unik,
  permission owner/role/self/privacy, cross-tenant outlet/user/employee denial,
  jadwal overlap/race, versi, punch malam/replay/durasi, inactive finish,
  manual izin/koreksi/void, tanggal depan, literal search/pagination/period,
  RLS SELECT dan INSERT rejection, composite employee FK, permission dicabut,
  audit dan akun kasir tetap. Log `/tmp/selaris-hris-isolated.log`.
- PASS migrasi112→113, downgrade/re-upgrade hanya QA, upgrade ulang head,
  serta runtime privileges yang diberikan migration tanpa grant manual.
  Log `/tmp/selaris-hris-migration-repeat-qa.log`.
- PASS browser development: create/edit/jadwal malam/absensi/koreksi/void,
  retry UUID setelah close/reload, self punch/restricted controls, empty/error,
  draft terpisah akun; lima viewport320/375/768/1024/1440 × dua tema,
  teks200% pada tiga form dan halaman, AA4.5, kontrol44px, keyboard/fokus/Escape.
  Log `/tmp/selaris-hris-browser-dev-final.log`; juga menguji batas kontrol3:1,
  workspace read failure, bisnis tanpa outlet, browser transport interruption,
  serta menolak write pending ketika akun berubah tanpa reload. Screenshot terang/gelap diperiksa.
- PASS TypeScript, py_compile runtime, `git diff --check`; seluruh kode
  authoritative di source, tanpa patch DOM/CSS runtime di produk.
- PASS live API demo setup/ketiga workspace/employee choices HTTP200 dan
  tiga tabel FORCE RLS. Daftar benar-benar kosong, tanpa data sintetis di toko.
  Existing pelanggan/POS customer/finance/purchasing GET tetap HTTP200.
  Log `/tmp/selaris-hris-live-api.log`.

## Delivery Gate

Semua hasil berikut merujuk source HRIS, suite browser development dan image
produksi final, unit/PG QA, serta pemeriksaan screenshot yang tercatat di atas.

Hard Gate:

- R-02 PASS: copy halaman/form HRIS tidak memakai em dash.
- R-03 PASS:320/375/768/1024/1440 dan teks200% tanpa overflow, kontrol44px.
- R-17 PASS: angka berasal dari query tabel HRIS; error tidak menghasilkan nol palsu.
- R-18 PASS: tidak ada testimonial atau avatar.
- R-23 PASS: modul dan tautan Tim & absensi mengikuti persetujuan HRIS Ivan; tanpa aset visual baru.
- R-24 PASS: HRIS route ada; Buka pengaturan menuju settings existing, diuji saat tanpa outlet.
- R-25 PASS: seluruh teks diuji4.5:1; batas input/select/textarea diuji3:1 pada dua tema.
- R-26 PASS: create/edit/jadwal/absensi/koreksi/void/punch/search/filter/pager/retry memakai aksi nyata dan diuji.
- R-27 PASS: loading, empty, setup/workspace error, retry, dan tanpa outlet diuji terpisah.
- R-28 PASS: tidak ada FAQ.
- R-32 PASS: Tab/ShiftTab, fokus terlihat, Escape dan pengembalian fokus diuji pada dialog native.
- R-33 PASS: page/CSS/actions merupakan source authoritative; tidak memakai patch DOM runtime.
- R-34 PASS: matrix tema terang/gelap menguji halaman, tiga form dan teks200%.
- R-35 PASS: Next standalone dibangun, suite click-through dijalankan pada image final;29unit dan PG QA lulus.
- R-36 PASS: tidak mengklaim payroll, GPS, sertifikasi keamanan, atau kehadiran dari jadwal kosong.
- R-37 PASS: Design Read dan dial1/1/1 diumumkan sebelum edit, arah visual mengikuti dashboard Selaris.
- R-38 PASS: fixture sintetis hanya di QA; toko demo menampilkan daftar kosong dari DB nyata.

Purpose Gate:

- R-01 PASS: tanpa gradient/glow tambahan; brand token mengidentifikasi tindakan utama.
- R-04 PASS: Users existing di navigasi berarti tim; tidak menambah ikon dekoratif.
- R-06 PASS: font existing Selaris dan hierarki heading/list, tanpa monospace besar/tracking label.
- R-07 PASS: tanpa pola latar.
- R-08 PASS: panah hanya menandai rentang waktu mulai-selesai, alasan tercatat di Desain.
- R-09 PASS: status karyawan memakai teks biasa, tanpa kapsul promosi.
- R-10 PASS: tanpa glassmorphism baru.
- R-12 PASS: panel menggunakan batas existing untuk kelompok data, tanpa bayangan menyeluruh.
- R-13 PASS: tanpa glow.
- R-14 PASS: panel ringkasan dan baris daftar berbeda karena isi dan pekerjaan, bukan kartu fitur seragam.
- R-19 PASS: tidak menambahkan animasi; sesuai MOTION1.
- R-22 PASS: tidak menambahkan ilustrasi.

Liveliness:

- PASS: ENERGY1/RHYTHM1/MOTION1 tertulis di Design Read.
- PASS: komposisi tenang sesuai dial, screenshot terang/gelap diperiksa.
- PASS: CTA Tambah karyawan/Atur jadwal/Catat kehadiran mengikuti bagian aktif.
- PASS: whitespace memisahkan cakupan outlet, ringkasan dan daftar.
- PASS: satu aksen brand dipakai untuk tindakan utama dan pilihan tab.
- PASS: pola kode KRY, outlet, tanggal kerja dan asal pencatatan menjadi motif kerja tim.
- PASS: Design Read disampaikan sebelum penulisan UI.

Craftsmanship dan Quality Locks:

- C-1 PASS: alasan brand, grouping, font, waktu dan icon dicatat pada bagian Desain.
- C-2 PASS: kontrol utama mempunyai handler/href dan lulus click-through produksi.
- C-3 PASS: section berisi profil, jadwal dan kehadiran yang dikelola, tanpa isi pemasaran.
- C-4 PASS: tema, viewport,200%, keyboard, errors, pending dan putus koneksi diuji.
- C-5 PASS: angka live dari DB, durasi disebut menit tercatat dan batas stage dinyatakan.
- R-05 PASS: komposisi mengikuti pekerjaan HRIS, tanpa template landing page.
- R-11 PASS: radius panel/form/control mengikuti finance.css dan InventoryDialog existing.
- R-15 PASS: CTA menyebut aksi kerja dan Periksa penyimpanan, bukan slogan generik.
- R-16 PASS: copy berisi bahasa profil/jadwal/kehadiran, tanpa jargon pemasaran AI.
- R-20 PASS: identitas Selaris dipertahankan melalui token, kode KRY dan pekerjaan outlet/kasir.
- R-21 PASS: dua tema mengikuti pilihan existing pengguna.
- R-29 PASS: warna neutral/brand/danger existing, tanpa palette baru.
- R-30 PASS: mengikuti aplikasi sendiri, tanpa meniru produk luar.
- R-31 PASS: keputusan visual utama memiliki alasan satu kalimat pada bagian Desain.

## Pemasangan

Backend dipasang melalui docker cp7file dan migrasi113, py_compile, serta
restart container existing ketika pending HPP0. Image backend160766…31a
dan created4Okt tetap; semua perbaikan modul sebelumnya dipertahankan.
Backup registration/model imports dan image frontend lama terdapat di
`/tmp/selaris-hris-backup`. Service HRIS awal juga dicadangkan sebelum koreksi
tanggal untuk masuk sesudah tengah malam. Jangan recreate backend dari
image lama karena hotfix runtime existing belum masuk image itu.

Image frontend final:
`sha256:9eae7c8d69961f3934791630e20cb71d60e782da510dba974893f45814f3bcd9`.
Suite produksi final lulus pada image tersebut, termasuk tambahan kondisi
tanpa outlet,3:1 batas kontrol, abort koneksi browser-ke-server dan penolakan
write saat akun berubah sambil mempertahankan pending request milik akun asal.
Uji tambahan chooser pada image yang sama mengklik search, halaman berikut/
sebelum, reset pilihan, empty/error/retry dan Escape tanpa writes; log
`/tmp/selaris-hris-choices-production.log`.
Log `/tmp/selaris-hris-browser-production-final.log` dan
`/tmp/selaris-hris-frontend-release-build.log`. Frontend dipasang hanya dengan
`compose up -d --no-deps frontend`.


Live6Oktober2026 sekitar08:23UTC, frontend created08:23:48Z. Browser demo
Server Actions nyata membuka ketiga daftar/form, employee choices kosong,
status cuti, Escape, dan mobile375 tanpa overflow/page errors. Seluruh smoke
live baca-saja; tidak submit data HRIS sintetis atau memanggil provider AI.
Log `/tmp/selaris-hris-live-browser.log`. Semua4layanan healthy dan health
DB/bg_tasks sehat. Hash7file runtime final sama source setelah koreksi malam.
QA containers/network/devserver dan token demo sementara dibersihkan.
Source belum commit; tidak pushmain atau merilis APK1.6.31+198.
