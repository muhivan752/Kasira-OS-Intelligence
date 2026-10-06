# Akun karyawan dari Tim & absensi

Form karyawan kini dapat menyimpan profil dan akun login bersama. Pemilik atau
manager yang diberi izin memilih nomor HP atau username, hak akses, dan password
awal. Pilihan profil saja serta pemakaian akun lama tetap tersedia. Irfan yang
sudah mempunyai akun dapat memakai akun tersebut tanpa mengganti UUID atau
memecah riwayat.

Nomor HP login disimpan sebagai login_username milik bisnis, dengan normalisasi
08/62/+62. User.phone yang digunakan OTP/Google tetap memakai identitas existing;
nomor ketikan tidak mengklaim identitas tersebut. Alias username yang sama
ditolak saat pembuatan/pengubahan akun; dua alias legacy yang sudah ambigu
ditolak saat login. Username angka lama yang tidak merupakan nomor valid tetap
bisa dipakai. Minimum username3 dan password8 tetap; password tidak dipangkas.

Pemilik memberi `hris.accounts.manage` bersama `hris.employees.manage` pada
jabatan manager melalui Atur akun dan akses tim. Console jabatan, kode aktivasi,
dan pengaturan owner tetap owner-only. Manager hanya dapat memilih managed role
dengan izin yang merupakan subset haknya dan outlet di dalam cakupannya.
Manager tidak dapat mengubah owner, akun sendiri, atau akun legacy dengan akses
yang belum dibatasi. Jabatan seluruh bisnis memerlukan cakupan manager seluruh
bisnis. Default akun baru hanya `hris.self` pada outlet penempatan. Role bawaan
yang telah diperluas tidak otomatis diberikan melalui pilihan default.

Pembuatan/pengubahan profil, User, role default, credential, pencabutan sesi,
dan audit berada pada satu transaksi. Advisory lock tenant memakai urutan yang
sama dengan console akun; actor/role/profil/sesi/outlet/brand dikunci dan sesi
diperiksa kembali setelah hash password. ID permintaan tetap saat retry; audit
request berpassword memakai HMAC, tanpa plaintext password. Row version profil
dan akun mencegah perubahan dari form lama. Login lama dan challenge tetap ada.

Password hanya berada pada form/memori permintaan aktif. SessionStorage hanya
menyimpan payload tanpa password dan penanda apakah password perlu dimasukkan
lagi. `GET /hris/requests/{client_request_id}` hanya memberi receipt milik actor
yang sama dengan scope outlet/izin saat ini. Setelah reload, receipt saved
menyelesaikan pending tanpa kirim ulang password. Receipt unknown meminta
password lagi lalu melanjutkan UUID yang sama. Pergantian identitas menghapus
password retry dari memori form.

Web login karyawan menyebut username atau nomor HP. APK1.6.34+201 yang sudah
dirilis dapat memakai nomor pada kolom Username akun; fitur baru form pengelola
berada di web. Tidak ada perubahan native atau versi APK pada tugas ini.

Validasi source final:

- `tests/staff-accounts-isolated.py`: delapan kelompok HTTP/JWT/PostgreSQL
  sintetis PASS, termasuk replay bersamaan, password whitespace, rollback,
  scope manager, reuse Irfan, revoke saat hash, default grant, ambiguitas nomor
  legacy dan FORCE RLS. Tidak ada mutasi data merchant atau provider berbayar.
- Regresi `tests/hris-isolated.py` dan `tests/accounts-isolated.py` PASS pada
  schema-only QA. Unit backend64:63 PASS dan1 fixture opsional dilewati.
- TypeScript dan production Docker build PASS. Image frontend yang diuji
  `sha256:ec2599c890b85e8f206478fa3373623c79f3acf18c3fd68fbcbf63fb82cb0e09`;
  enam hash runtime frontend cocok dengan source.
- `tests/staff-accounts-browser.cjs` PASS: lima kelompok interaksi, empat lebar
  320/375/768/1440, dua tema, teks200%, kontras AA/target44px, keyboard/Escape,
  password toggle/confirmation, saved/unknown receipt setelah reload, storage
  tanpa secret, profil saja, prerequisite toko dan pengelola tanpa izin.
- `tests/accounts-browser.cjs` PASS: login/daftar/migrasi/aktivasi/pemulihan,
  console role/account, grant akun manager baru, error/retry, logout dan tema.
- Gate lengkap: [STAFF_ACCOUNT_GATE.md](STAFF_ACCOUNT_GATE.md).

Bukti privat `/tmp/selaris-staff-{http.log,legacy.log,unit.log,typescript.log,
build.log,browser.log,accounts-browser.log,frontend-manifest.json,mobile.png,
browser-trace.zip}`. Uji autentikasi memakai data sintetis; belum memakai
perangkat fisik atau mengubah akun/password Irfan di toko live.
