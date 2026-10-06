# Fondasi izin server Selaris

Tanggal: 6 Oktober 2026. Dokumen merekam implementasi fondasi source/QA. Fondasi ini kemudian dipasang bersama tahap akun dan APK 1.6.32+199; [review deployment](ACCOUNT_ACCESS_RELEASE.md).

Server sekarang menghitung akses dari identitas user, role, status pegawai dan outlet. HRIS memakai pemeriksaan yang sama untuk izin profil, jadwal, absensi dan akses diri sendiri. Akun staf dengan profil HRIS nonaktif ditolak pada permintaan berikutnya dan ketika mencoba login kembali. Kontrak `GET /api/v1/auth/access` tersedia untuk integrasi web dan APK berikutnya.

Tahap ini merekam fondasi server dari [rencana akun dan absensi](ACCOUNT_ACCESS_ATTENDANCE_PLAN.md). Tahap berikutnya sudah menambahkan username/password, migrasi legacy, editor akun/jabatan HRIS, sesi per perangkat dan native self/punch pada source/QA: [review akun](ACCOUNT_ACCESS_REVIEW.md). Penonaktifan HRIS kini mencabut sesi dan reaktivasi memerlukan login baru. Uraian fondasi di bawah adalah hasil tahap awal; GPS/foto, delegasi/override individual dan domain/AI lengkap tetap belum dibuat.

## Perilaku akses

| Mode | Sumber izin | Cakupan dan penerapan |
| --- | --- | --- |
| Owner | `User.is_superuser` | Hak bisnis pada tenant sendiri, tetap mengikuti pemeriksaan modul dan paket existing. Nama role Owner saja tidak memberikan hak baru. |
| Legacy | Hak dasar POS/self, flag `can_*`, `hris_manage` dan key izin canonical | HRIS memakai izin canonical. Endpoint bisnis lain tetap mengikuti handler lama; daftar izin dalam manifest bukan klaim bahwa semua endpoint legacy sudah dibatasi. |
| Managed | `Role.permissions.access_policy`, version 1 | Grants eksplisit dan scope role. Endpoint di luar auth/self-profile dan HRIS ditolak sebelum handler, sampai pemeriksaan domain lengkap tersedia. |

Policy managed menggantikan fallback legacy sepenuhnya. Policy kosong, format salah, versi tidak dikenal, string/angka sebagai boolean dan nama izin tidak dikenal ditolak. Role yang dihapus, tidak ditemukan atau berasal dari tenant lain tidak berubah menjadi akses kasir biasa. Header tenant, bila dikirim, wajib UUID tenant user yang sudah diautentikasi. Pemeriksaan paket Pro menjalankan autentikasi ini terlebih dahulu sebelum mengambil tenant untuk tier gate.

Contoh bentuk konfigurasi untuk role dengan `scope="outlet"`:

```json
{
  "access_policy": {
    "version": 1,
    "permissions": {
      "hris.self": true,
      "hris.schedules.manage": true
    },
    "outlet_ids": ["11111111-1111-4111-8111-111111111111"]
  }
}
```

UUID contoh harus diganti dengan outlet bisnis yang sebenarnya. Scope tenant tidak menerima daftar outlet/brand; scope brand memakai `brand_ids` dan hanya mencakup brand aktif dalam tenant; scope outlet memakai `outlet_ids`. Daftar kosong menghasilkan nol outlet. Target dari tenant lain tidak masuk hasil. Belum ada endpoint atau layar untuk mengubah konfigurasi ini; tidak ada role produksi yang diaktifkan sebagai managed pada task ini.

## Kontrak akses

`GET /auth/access` mengembalikan `user_id`, `tenant_id`, izin canonical, outlet yang diizinkan, `employee_id`, `enforcement_mode`, `enforced_modules`, `access_version` dan `generated_at` di dalam StandardResponse. Saat ini `enforced_modules=["hris"]`. Profil privat, raw policy, password, PIN dan token tidak menjadi bagian manifest.

`access_version` adalah fingerprint keadaan akses yang dihitung ulang dari user/role/pegawai/outlet. Client dapat memakainya untuk membedakan konteks dan membuang cache yang sudah tidak sesuai. Ia belum menjadi versi kredensial atau identitas sesi dalam JWT. Logout dan blacklist existing belum diubah menjadi sesi per perangkat.

Login OTP dan login Google existing memakai helper payload yang sama dan memilih outlet dari cakupan akses. `/auth/me` memakai pilihan yang sama. Login PIN Dapur memeriksa status pegawai dan menolak mode managed selama integrasi Dapur belum siap. Google tetap tersedia pada source legacy untuk migrasi; penghapusan alur Google baru mengikuti tahap akun yang direncanakan.

## HRIS

- `hris.employees.manage`, `hris.schedules.manage` dan `hris.attendance.manage` dipisahkan. `hris_manage:true` lama memetakan ketiganya; key canonical false mencabut hak tersebut. `hris.self` mengatur akses profil/jadwal/absensi sendiri dan punch.
- Outlet pilihan, outlet profil asal saat dipindah, outlet pegawai target jadwal/absensi, catatan yang dikoreksi/void dan hasil replay diperiksa. Chooser karyawan hanya memberikan nama/kode dalam cakupan outlet pengelola.
- Rekap setiap domain mengikuti izin domainnya sendiri. Rekap yang tidak boleh dilihat bernilai null dan memiliki `summary_scopes=no_access`. Jumlah belum tercatat tidak dihitung dengan mencampur cakupan jadwal tim dan absensi diri sendiri.
- Mode managed tidak mendapat daftar akun seluruh tenant dari setup HRIS. Mengubah atau melepas hubungan akun membutuhkan `access.manage` selain izin profil. Penautan baru akun owner sebagai akun karyawan ditolak.
- Pegawai nonaktif yang bukan owner tidak dapat menggunakan JWT lama atau mendapatkan token lewat OTP, Google maupun PIN. `User.is_active` tidak diubah oleh status pegawai. Owner bisnis tidak kehilangan kepemilikan karena profil kerja yang pernah ditautkan dinonaktifkan.
- Pengelola absensi tetap dapat menutup/mengoreksi catatan pegawai nonaktif dengan alasan. Staf tersebut tidak diberi akses khusus untuk punch pulang. Mengaktifkan pegawai kembali membuka akses hanya jika akun/role masih layak; sesi lama belum dicabut permanen lewat tabel sesi.
- Izin diperiksa sebelum replay idempotensi. Perubahan izin atau pencabutan outlet tidak dapat disiasati dengan mengirim ID request lama.

HRIS legacy masih mendapat pilihan akun kasir seluruh tenant sesuai perilaku tahap sebelumnya. Pembatasan delegasi akun lengkap dan penugasan individual akan ditambahkan bersama layar pengaturan akses.

## Batas tahap pertama

Mode managed belum mendukung POS, sync, Keuangan, Pembelian, CRM, AI/HPP atau Dapur. Permintaan authenticated menuju handler yang belum didukung ditolak menggunakan identitas callable endpoint yang telah dipilih FastAPI dan metode HTTP, bukan pencocokan awalan URL yang dikirim client. Pemberian `ai.chat` atau `pos.sell` dalam policy belum membuka endpoint tersebut.

Mode legacy mempertahankan perilaku handler domain selain HRIS; cache/history/RAG AI dan pending worker lama belum dimigrasikan ke pemeriksaan granular. Jangan menyatakan chat legacy sudah mengikuti izin HRIS. Endpoint publik storefront dan webhook tetap memakai aturan existing. Pencabutan perangkat offline, kebijakan antrean transaksi, sesi per perangkat, aktivasi/reset password dan kontrol role di UI merupakan pekerjaan berikutnya.

## Validasi

| Pemeriksaan | Hasil |
| --- | --- |
| Unit backend | 59 test dijalankan, 58 lulus dan 1 Google identity DB test dilewati karena memerlukan fixture auth khusus. Termasuk 15 unit baru untuk policy/izin/header/endpoint/manifest. |
| HTTP dengan JWT sebenarnya | Delapan kelompok lulus: kontrak, batas tenant/outlet, role asing, privasi self, izin granular, replay/race, status pegawai, perubahan role dan batas endpoint yang belum siap. |
| Login | OTP, Google existing dengan verifier tiruan dan PIN diuji untuk scope/status; `_login_payload` juga menolak staf nonaktif. Tidak ada panggilan Google, SeFrekuensi, WA atau provider AI. |
| PostgreSQL | Schema produksi saja disalin ke DB QA kosong; seluruh records sintetis. Role app NOSUPERUSER/NOBYPASSRLS, FORCE RLS HRIS dan isolasi tenant user/role/outlet dibuktikan. |
| Regresi HRIS | Empat kelompok suite existing lulus: CRUD/role/privacy, jadwal malam/punch, koreksi/void/pagination, forced RLS/audit. Ekspektasi staf nonaktif diperbarui menjadi penutupan oleh pengelola. |
| Regresi domain | Owner finance summary, customers workspace, purchases, recipes, ingredients dan kasir legacy products GET lulus. Header tenant asing ditolak sebelum tier gate HPP. Tidak melakukan write merchant. |
| Client web | TypeScript `tsc --noEmit --incremental false` lulus. Transport HRIS/CRM/shared API membaca `detail.message` agar alasan penolakan akses dapat ditampilkan. |
| Source | Python compile dan `git diff --check` lulus. Tidak ada perubahan layout, build frontend/APK atau QA browser baru. |

Log QA: `/tmp/selaris-access-unit.log`, `/tmp/selaris-access-qa-http.log`, `/tmp/selaris-access-hris-regression.log`. Suite source: [unit akses](../backend/tests/test_access.py), [HTTP akses](../tests/access-isolated.py) dan [regresi HRIS](../tests/hris-isolated.py).

## Kelanjutan implementasi

Gunakan [schema policy](../backend/schemas/access.py), [service akses](../backend/services/access.py), [dependency auth](../backend/api/deps.py) dan [service HRIS](../backend/services/hris.py) sebagai fondasi berikutnya. Tahap akun menambahkan username/password, pemulihan yang disepakati, migrasi user lama, pengaturan role/penugasan individual dan versi/sesi kredensial. Lalu tambahkan enforcement domain per endpoint, filter field dan konteks AI sebelum role managed dipakai untuk POS atau chat.

Task ini belum deploy, commit, push atau rilis APK. Produksi dan APK tetap pada keadaan sebelumnya. Pemeriksaan read-only mengonfirmasi backend produksi running/healthy dan mount hanya `/app/uploads`; source backend tidak di-bind ke container produksi. Database dan jaringan QA sementara sudah dihapus, salinan schema dan skrip adaptasi QA sementara dibersihkan, log hasil uji tetap disimpan. Backend produksi tetap memiliki hotfix yang belum seluruhnya dibake ke image; jangan recreate image lama saat pemasangan berikutnya.
