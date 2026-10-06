# Rencana akun akses karyawan dan absensi Selaris

Tanggal: 6 Oktober 2026. Status: fondasi izin dan tahap akun/sesi sudah diimplementasikan pada source dan QA; belum deploy/rilis.

Fondasi izin server/HRIS dan tahap username/password, migrasi legacy, pengaturan akun/jabatan HRIS, sesi perangkat serta native self/punch online sudah diimplementasikan pada source dan diuji di QA. Batasnya ada di [review fondasi akses](ACCESS_REVIEW.md) dan [review akun](ACCOUNT_ACCESS_REVIEW.md). Role baru hanya HRIS; domain lain/AI dan GPS/foto masih pekerjaan berikutnya. Rencana dan inventaris awal di bawah merekam kondisi sebelum implementasi; rincian yang belum diputuskan tetap usulan.

Owner memakai username toko dan password untuk akun bisnis yang sama di web dan APK. Karyawan memakai akun individual yang aksesnya diatur melalui HRIS. Server memeriksa izin yang sama untuk halaman aplikasi, API dan AI. Setelah fondasi ini selesai, absensi native memeriksa lokasi HP dengan foto yang kewajibannya ditentukan owner.

Urutan pengerjaan: fondasi akses server, akun dan migrasi pengguna lama, pengaturan akses melalui HRIS di web dan APK, pembatasan AI, lalu absensi lokasi. Payroll menyusul. Rencana disusun sesuai kesepakatan “plan dulu”; rincian usulan berikut bukan fitur yang sudah live atau izin publikasi APK. Tahap implementasi yang selesai dicatat dalam review masing-masing.

## Keputusan yang sudah disepakati

- Owner daftar memakai username toko dan password. Google tidak menjadi bagian dari rancangan login baru.
- OTP SeFrekuensi tetap tersedia sebagai pilihan. Fungsi rinci OTP belum diputuskan.
- Web dapat dipakai lebih dahulu. Ajakan download APK dapat dilewati dan tidak membuat bisnis kedua.
- Owner mengatur akun, jabatan, outlet dan izin karyawan melalui HRIS. AI mengikuti izin tersebut, dengan hak melihat dan mengubah data yang terpisah.
- Absensi native memeriksa lokasi HP. Owner menentukan apakah foto diperlukan.
- Akun pengguna lama perlu dimigrasikan tanpa memutus hubungan data dan transaksi.

Acuan keputusan: [MEMORY.md](../MEMORY.md) dan [SESSION.md](../SESSION.md), bagian kesepakatan 6 Oktober paling atas.

## Inventaris awal sebelum implementasi

| Bagian | Kondisi source sekarang | Perubahan yang diperlukan |
| --- | --- | --- |
| Identitas | `User` punya nomor HP wajib dan unik, PIN, satu tenant dan satu role; belum ada username atau password akun | Kredensial username dan password terpisah dari PIN; dukung akun tanpa nomor pemulihan |
| Jabatan | `Role` punya scope, JSON permissions dan sejumlah kolom izin khusus | Satu pemeriksa izin dengan pemetaan eksplisit dari izin lama |
| Profil pegawai | `HrEmployee` terpisah dari `User`, opsional terhubung satu akun dan memiliki satu outlet utama | Hubungkan status kerja dengan kelayakan akses akun; pisahkan penempatan utama dari daftar outlet yang boleh diakses |
| Outlet login | Beberapa jalur login dan `/auth/me` memilih outlet pertama bisnis | Pilih dari outlet yang benar-benar diizinkan untuk pengguna |
| Sesi | JWT saat ini membawa `sub` dan `exp`; logout backend memakai blacklist per user, logout web menghapus cookie | Sesi per perangkat dan pencabutan semua sesi untuk perubahan kredensial/status; tinjau tabel `sessions` yang sudah ada dari migrasi 006 |
| HRIS | `hris_manage` atau owner memberi akses pengelola; perubahan status profil tidak mengubah `User.is_active` | Pisahkan izin kelola pegawai, akun, jadwal dan absensi dengan batas outlet |
| AI | Chat memvalidasi tenant outlet, tetapi konteks umum di-cache per outlet; history memakai tenant dan ID percakapan | Filter konteks menurut pengguna, izin dan outlet; verifikasi kepemilikan percakapan |
| Tindakan AI | Jalur `RESTOCK` di chat umum dapat menjalankan penambahan stok langsung | Periksa izin tindakan dan minta konfirmasi draft sebelum melakukan perubahan |
| Lokasi absensi | Outlet sudah punya latitude, longitude dan timezone; absensi belum menyimpan bukti lokasi/foto | Kebijakan absensi tersendiri, bukti masuk/pulang dan pengajuan pengecualian |
| Native | Dependency `geolocator`, `image_picker` dan `permission_handler` sudah tersedia | Integrasi ke alur absensi, penanganan izin dan hasil pengiriman |

Temuan ini berdasarkan source, bukan pemeriksaan produksi baru. Referensi: [model user](../backend/models/user.py), [model role](../backend/models/role.py), [model HRIS](../backend/models/hris.py), [auth](../backend/api/routes/auth.py), [pemeriksaan user](../backend/api/deps.py), [service HRIS](../backend/services/hris.py), [service AI](../backend/services/ai_service.py), [route AI](../backend/api/routes/ai.py), [auth web](../app/actions/auth.ts), [outlet](../backend/models/outlet.py), [migrasi sessions](../backend/migrations/versions/006_sessions.py) dan [dependency native](../kasir_app/pubspec.yaml).

## Usulan alur akun

### Owner baru

1. Isi username toko, password, nama owner dan identitas usaha. Username login dibedakan dari nama tampilan toko dan slug storefront. Perubahan nama toko tidak mengubah cara masuk.
2. Server memvalidasi username yang dinormalisasi dan membuat tenant, owner, brand serta outlet secara atomik. Pengulangan request yang sama mengembalikan bisnis yang sama.
3. Owner melengkapi pengaturan usaha dan langsung dapat memakai web.
4. Ajakan download APK dapat dilewati. Saat APK dibuka, username dan password yang sama membawa owner ke bisnis yang sudah dibuat.

Usulan teknis: username toko unik secara global dan tidak peka huruf besar/kecil; karakter dibatasi agar tidak ambigu. Password disimpan sebagai hash password tersendiri, tidak menggunakan `pin_hash`, tidak tercatat di log/audit, dan tidak dikirim ke AI. Verifikasi login harus memiliki pembatasan percobaan dan pesan kegagalan yang tidak membocorkan keberadaan akun. Kebijakan panjang/password dan algoritme hash ditetapkan saat implementasi setelah memeriksa library yang digunakan.

### Karyawan

Owner membuat atau menghubungkan profil HRIS, memberi username karyawan, jabatan, outlet yang diizinkan dan izin tambahan. Karyawan masuk dengan username toko, username pribadi dan password pribadi; pada perangkat yang sudah mengenal toko, username toko cukup dipilih dari konteks perangkat. Kredensial owner tidak dibagikan ke staf.

Akun baru menggunakan aktivasi sekali pakai yang kedaluwarsa untuk membuat password sendiri. Owner dapat mengulang aktivasi atau memulai reset, tetapi tidak melihat password lama. Profil pegawai tanpa akun tetap didukung. Jumlah profil HRIS dan batas akun kasir/POS tidak disamakan; perubahan harga/batas paket membutuhkan keputusan tersendiri.

PIN tetap berfungsi sebagai pembuka cepat pada perangkat dengan sesi individual yang sah. Jalur PIN server yang saat ini digunakan aplikasi Dapur perlu masuk pemeriksaan izin dan pencabutan sesi yang sama; jangan menjadikannya jalan untuk melewati akun nonaktif atau batas outlet.

### OTP SeFrekuensi

Usulan: OTP menjadi alternatif masuk dan pemulihan password bagi akun yang sudah menautkan serta memverifikasi nomor pribadi. OTP tidak wajib pada setiap login password. Pendaftaran tanpa penautan nomor tetap dapat memakai web dan APK, tetapi pemulihan mandiri lewat SeFrekuensi belum tersedia.

Kode login, penautan nomor dan pemulihan dibedakan berdasarkan tujuan, akun dan challenge. Kode kedaluwarsa, hanya dapat digunakan sekali, dibatasi percobaannya dan tidak mengalihkan kanal diam-diam. Mengetahui nomor saja tidak cukup untuk menautkan nomor atau mengambil alih akun. Untuk akun owner tanpa sarana pemulihan, siapkan kode pemulihan sekali pakai pada pengaturan awal; staf juga dapat meminta aktivasi ulang kepada owner. Mekanisme pemulihan akhir perlu disepakati sebelum pendaftaran password dirilis.

OTP tetap usulan fungsi, bukan keputusan baru Ivan. Login lama dipertahankan selama migrasi. Tombol Google baru dihapus setelah akun yang mengandalkannya sudah memiliki akses pengganti; hubungan identitas lama tidak dihapus saat transisi.

## Usulan matriks hak akses

Jabatan menjadi preset yang dapat owner sesuaikan. Tabel berikut adalah titik awal konfigurasi, bukan hak otomatis yang akan diberikan ke seluruh pengguna lama. “Outlet tugas” berarti daftar outlet yang owner berikan, termasuk penugasan sementara yang disahkan. Jabatan di profil pegawai adalah nama pekerjaan; ia tidak otomatis menjadi role aplikasi hanya karena teks namanya sama.

| Kemampuan | Owner | Manajer | Kasir | Staf stok | Karyawan umum |
| --- | --- | --- | --- | --- | --- |
| Outlet | Seluruh bisnis | Outlet tugas | Outlet tugas | Outlet tugas | Outlet tugas |
| Transaksi POS | Ya | Ya | Ya | Jika diberikan | Jika diberikan |
| Omzet dan laporan | Seluruh bisnis | Ringkasan outlet tugas | Transaksi sendiri sesuai kebutuhan POS | Jika diberikan | Jika diberikan |
| HPP dan harga supplier | Ya | Jika diberikan | Jika diberikan | Jika diberikan | Jika diberikan |
| Stok | Lihat dan kelola | Lihat; kelola jika diberikan | Lihat ketersediaan | Lihat dan terima barang jika diberikan | Jika diberikan |
| Keuangan dan pembayaran utang | Lihat dan catat | Jika diberikan | Jika diberikan | Jika diberikan | Jika diberikan |
| Profil pelanggan | Lihat dan kelola | Jika diberikan | Lookup yang diperlukan POS | Jika diberikan | Jika diberikan |
| Tim dan jadwal | Seluruh bisnis | Outlet tugas jika diberikan | Diri sendiri | Diri sendiri | Diri sendiri |
| Absensi | Kelola seluruh bisnis | Kelola outlet tugas jika diberikan | Masuk/pulang sendiri | Masuk/pulang sendiri | Masuk/pulang sendiri |
| Akun dan pemberian izin | Ya | Jika didelegasikan dengan batas | Tidak | Tidak | Tidak |
| Chat AI | Ya sesuai paket | Jika diaktifkan owner | Jika diaktifkan owner | Jika diaktifkan owner | Jika diaktifkan owner |

Refund, persetujuan refund, diskon khusus, persetujuan perubahan HPP dan melihat rincian omzet masing-masing tetap memiliki izin terpisah. Melihat ketersediaan produk tidak memberikan akses harga beli, margin atau harga supplier. Lookup pelanggan POS dibatasi pada kebutuhan transaksi dan tidak memberi akses ekspor kontak atau catatan keluhan pengelola.

### Pemeriksaan izin di server

Server membangun konteks akses berisi tenant, user, status akun/pegawai, role, izin efektif, outlet yang diizinkan dan versi akses. Semua endpoint memeriksa tindakan serta objek yang dituju. Cookie, header `X-Tenant-ID`, body outlet, dan pilihan di aplikasi hanya menjadi permintaan; semuanya harus cocok dengan konteks pengguna yang sudah diverifikasi.

Usulan katalog izin dipisahkan per tindakan: `pos.sell`, `pos.refund`, `pos.refund.approve`, `pos.discount.override`, `sales.view`, `sales.detail.view`, `hpp.view`, `hpp.manage`, `hpp.approve`, `stock.view`, `stock.receive`, `stock.adjust`, `purchasing.view`, `purchasing.manage`, `supplier.price.view`, `finance.view`, `finance.manage`, `customers.lookup`, `customers.view`, `customers.manage`, `customers.export`, `hris.self`, `hris.employees.manage`, `hris.schedules.manage`, `hris.attendance.manage`, `hris.exceptions.approve`, `access.manage` dan `ai.chat`.

Role memberikan hak dasar; penyesuaian individual owner dapat memberi atau mencabut hak yang tercatat. Pencabutan eksplisit menang atas pemberian hak. Seluruh hak tetap dibatasi status, tenant, outlet, ketentuan paket dan kebijakan modul. Izin `ai.chat` tidak menambah izin data atau tindakan lain. Delegasi pengelolaan akun tidak boleh memberikan hak melebihi batas delegasi, mengangkat platform admin, atau mengubah owner terakhir.

Kolom `can_*` dan JSON izin lama dipetakan melalui satu adapter kompatibilitas. Endpoint lama, ekspor, upload, websocket, sync, AI dan pekerjaan latar belakang masuk inventaris agar izin tidak hanya diterapkan pada navigasi baru. RLS tenant tetap dipakai bersama pemeriksaan outlet dan izin tindakan. Owner bisnis dibedakan dari platform admin; `is_superuser` existing tidak boleh menjadi jalan untuk mengakses tenant lain.

### Status pegawai dan sesi

Setelah migrasi akses diaktifkan, pegawai terhubung yang dinonaktifkan tidak dapat login atau mengirim tindakan baru. Status kerja dan `User.is_active` tetap dua data berbeda: mengaktifkan pegawai kembali tidak otomatis membuka akun yang diblokir karena alasan lain. Effective access memerlukan keduanya layak. Perubahan status, password, role dan penugasan outlet menaikkan versi akses; pencabutan akun/password membatalkan sesi yang relevan.

Logout satu perangkat mencabut sesi perangkat itu. Perintah keluar semua perangkat dan reset password mencabut seluruh sesi pengguna. Implementasi meninjau serta melengkapi tabel `sessions` existing, menambahkan identitas sesi ke token dan memeriksa status/version server. Web memakai cookie httpOnly dan native memakai penyimpanan kredensial aman.

Saat pegawai dinonaktifkan dengan absensi masih terbuka, pengelola yang berwenang dapat menutup atau mengoreksi absensinya dengan alasan. Jangan membuka kembali akses seluruh aplikasi hanya untuk tombol pulang. Riwayat pegawai, transaksi dan audit tetap mengacu ke UUID user/pegawai lama.

Pencabutan server berlaku pada permintaan berikutnya; perangkat yang benar-benar offline tidak bisa menerima perubahan saat itu juga. Native perlu masa berlaku izin offline, penutupan tampilan sensitif saat izin kedaluwarsa, dan pemeriksaan ulang saat tersambung. POS offline existing harus dinilai terpisah: transaksi yang sudah terjadi tetap disimpan dan antrian yang ditolak karena pencabutan masuk penanganan owner, tidak dihapus atau diakui sebagai sukses. Durasi serta aturan penerimaan antrian lama belum ditetapkan pada rencana ini.

## AI mengikuti hak pengguna

Sebelum mengambil konteks, server memeriksa `ai.chat`, paket dan outlet. Setiap sumber data memeriksa izin domainnya sendiri. Kasir tanpa `finance.view` dapat menanyakan stok yang boleh dilihat, tetapi pertanyaan laba/utang tidak mengambil data finance atau mengirimnya ke provider. Penolakan tidak memuat angka rahasia. Data GPS, foto pegawai, password, PIN, token dan kontak yang tidak diperlukan tidak menjadi konteks AI umum.

Cache konteks dan history diikat ke tenant, pemilik percakapan, outlet serta versi/izin akses. Ketika izin berubah, history/ringkasan lama yang memuat informasi di luar izin baru tidak dikirim kembali ke model atau ditampilkan ke pengguna. Semua jalur HPP, RAG, pricing, insight, finance dan HRIS memakai pemeriksaan yang sama. Teks prompt dan ingatan percakapan tidak dapat memberikan izin.

Tindakan AI menggunakan draft yang menjelaskan perubahan, target outlet dan dampaknya. Server memeriksa izin saat draft dibuat dan saat user mengonfirmasi versi yang tepat. Request memiliki idempotency key, fingerprint, row version dan audit. Pertanyaan stok tidak otomatis menambah stok; barang diterima, opname dan rencana pembelian dibedakan. Tidak ada klaim transfer uang ketika hanya mencatat pembayaran.

Penggabungan percakapan persisten web/APK menjadi tahap lanjutan setelah pembatasan ini siap. Kuota/paket AI existing tetap berlaku selain izin owner.

## Usulan absensi lokasi dan foto

### Kebijakan per outlet

Usulan tahap pertama memakai pengaturan per outlet dengan nilai awal yang dapat disalin dari bisnis. Owner menentukan titik absensi, radius dalam meter, batas umur/akurasi lokasi dan kewajiban foto. Foto default tidak wajib; jika diwajibkan, karyawan tidak dapat mematikannya sendiri. Override per jabatan ditunda agar kebijakan awal mudah dipahami.

Titik outlet existing dapat dipakai setelah owner memeriksa lokasinya. Radius delivery tidak digunakan sebagai radius absensi. Owner mengaktifkan kebijakan GPS setelah konfigurasi valid dan APK yang mendukungnya tersedia. Angka radius, batas akurasi serta umur sampel dipilih dalam pilot; rencana ini tidak menetapkan ukuran yang berlaku untuk semua jenis toko.

Usulan pengecekan berlaku saat masuk dan pulang. Bukti masuk dan pulang disimpan terpisah; pengaturan dan versi kebijakan yang berlaku disimpan bersama bukti agar perubahan radius tidak mengubah penilaian absensi lama.

### Alur karyawan

1. Karyawan memilih outlet penugasan yang diizinkan dan tindakan masuk/pulang. Login akun dan shift kas tetap aktivitas terpisah dari absensi.
2. APK meminta lokasi terbaru beserta akurasi saat tombol absensi digunakan. Jika foto wajib, APK membuka kamera langsung dan tidak menerima pilihan galeri pada alur normal.
3. Server memeriksa pengguna, pegawai, penugasan, jadwal, lokasi, kebijakan dan bukti. Jam absensi resmi memakai waktu server; tanggal kerja mengikuti timezone outlet dan aturan jadwal lintas malam existing.
4. Respons sukses membawa ID catatan. Saat koneksi terputus, aplikasi menampilkan hasil belum pasti dan mengecek status request yang sama sebelum mengulang; belum ada tanda hadir sampai server mengonfirmasi.

Lokasi yang kurang akurat atau berada di batas radius meminta pengambilan ulang, bukan otomatis diluluskan. Waktu pengambilan dari HP tetap input yang tidak dipercaya sepenuhnya; challenge server dan batas waktu pengiriman mengurangi penggunaan ulang bukti. GPS dan foto kamera tidak menjadi jaminan identitas atau bukti yang mustahil dipalsukan. Tidak ada pengenalan wajah atau pemantauan lokasi terus-menerus.

Ketika kebijakan GPS aktif, endpoint punch web/APK lama harus memerlukan bukti yang sama atau menolak dengan pesan memakai APK yang mendukungnya. Koreksi manual pengelola tetap tersedia dengan alasan dan audit; web lama tidak boleh menjadi jalan melewati kebijakan. Aktivasi per outlet mencegah pengguna lama kehilangan kemampuan absensi sebelum akses pengganti siap.

### Pengecualian dan penyimpanan bukti

Jika lokasi ditolak, izin HP tidak tersedia atau GPS bermasalah, karyawan dapat mengirim pengajuan pengecualian dengan alasan. Pengajuan berstatus menunggu dan tidak dihitung sebagai hadir. Pengelola dengan izin approval pada outlet tersebut dapat menyetujui atau menolak; pemohon tidak menyetujui pengajuannya sendiri. Approval membuat/memperbarui satu catatan dengan waktu yang disahkan, versi, alasan dan audit, serta mencegah bentrok dengan punch normal yang sudah berhasil.

Foto disimpan privat. Upload diikat ke user, tenant, request absensi dan bukti yang hanya dapat dikonsumsi sekali. Client tidak bebas mengirim URL foto arbitrary. Pembacaan bukti memerlukan otorisasi sebelum URL sementara diterbitkan. Titik lokasi/foto hanya tersedia kepada pemilik bukti dan pengelola absensi yang berwenang; chat AI umum tidak membacanya. Tetapkan masa simpan bukti sebelum mengaktifkan fitur, pisahkan penghapusan bukti dari penyimpanan riwayat jam kerja dan audit, serta bersihkan upload yang tidak terpakai.

Absensi offline belum menjadi cakupan. Retry request online dengan hasil belum pasti perlu batas waktu: jika belum pernah diterima server dan bukti sudah terlalu lama, minta bukti baru atau pengajuan pengecualian. Jika sudah diterima, pengulangan mengembalikan hasil asal tanpa memerlukan foto/lokasi kedua.

## Model data dan kontrak yang diusulkan

| Data atau kontrak | Tujuan |
| --- | --- |
| Username toko pada tenant atau tabel login bisnis | Identitas login unik, terpisah dari slug publik; hubungan owner tetap ke UUID user existing |
| Kredensial user | Username pribadi unik per tenant, hash password, status aktivasi, versi kredensial; nomor pribadi opsional untuk akun baru |
| Penugasan outlet dan penyesuaian izin | Hubungan tenant/user/outlet, status aktif serta rentang penugasan; tetap terpisah dari outlet utama HRIS |
| Sesi existing yang dilengkapi | Sesi perangkat, token hash, versi, masa berlaku dan pencabutan |
| Kebijakan absensi | Outlet, titik/radius, mutu lokasi, aturan foto, version, pengubah dan waktu berlaku |
| Bukti absensi | Bukti per masuk/pulang, sumber, titik/akurasi, waktu server dan versi kebijakan; foto privat jika diperlukan |
| Pengajuan pengecualian | Pemohon, tindakan, outlet, alasan, status, pengambil keputusan dan hubungan absensi |
| `/auth/me` atau kontrak akses baru | Identitas, outlet yang diizinkan, izin efektif dan versi akses yang sama untuk web/native |
| API HRIS akun dan role | Aktivasi, reset, role, penugasan dan perubahan status dengan pemeriksaan delegasi |
| Kontrak punch dan status request | ID request, tindakan, outlet, bukti, hasil/pending dan pemulihan setelah putus koneksi |

Nama tabel/endpoint final dan nomor migrasi ditetapkan setelah memeriksa head schema saat implementasi. Semua tabel tenant kritikal menggunakan UUID, row version, RLS, foreign key tenant yang sesuai, indeks unik dan audit. Writes terkait dibuat atomik dan dapat diulang tanpa efek ganda. Nomor HP user baru tanpa kontak pemulihan harus dapat kosong melalui perubahan schema yang benar, bukan nomor palsu; pertahankan keunikan dan identitas nomor legacy yang nyata.

## Migrasi pengguna lama dan urutan implementasi

1. Inventaris akun owner/kasir/Dapur, role NULL, hubungan HRIS, outlet, nomor, jalur auth dan schema sesi. Tentukan owner yang benar bila satu tenant memiliki lebih dari satu akun istimewa. Simpan pemetaan akses lama serta rencana rollback.
2. Tambahkan schema secara additive dan bangun pemeriksa izin server. Pemetaan legacy harus eksplisit, tidak mengisi semua izin menjadi true. Pertahankan UUID tenant/user/pegawai dan seluruh data merchant. Uji enforcement pada endpoint lama sebelum pengguna baru diarahkan ke sana.
3. Owner yang sudah login memilih username toko dan membuat password dengan verifikasi sesi yang sesuai. Akun lama tidak diberi password default atau dibuatkan tenant kedua. Sediakan pemulihan yang disepakati sebelum menutup pintu masuk lama.
4. Tambahkan pengaturan akun, role, outlet dan izin HRIS. Hubungkan akun kasir existing ke profil yang benar; jabatan HRIS tanpa akun tetap berjalan. Tampilkan pratinjau perubahan hak agar owner memahami dampaknya.
5. Web dan APK memakai kontrak akses yang sama. Saat akses ditolak atau dicabut, aplikasi memberi alasan dan tindakan yang sesuai serta membersihkan konteks akun lama. Pisahkan draft/antrian per tenant/user; jangan mengirim ulang draft akun sebelumnya.
6. Batasi semua konteks/tindakan AI, history dan cache. Uji dengan provider tiruan dan data QA sebelum mengaktifkan chat staf. Chat persisten menyusul.
7. Tambahkan kebijakan, bukti dan pengecualian absensi, kemudian uji native lokasi/foto. Aktifkan GPS per outlet setelah client siap. Payroll tetap tahap terpisah.

Pengembangan dan QA memakai lingkungan terisolasi. Catatan deployment saat ini tetap berlaku: backend produksi berisi hotfix yang belum seluruhnya dibake ke image; jangan recreate dari image lama. Rilis APK menggunakan CI dengan signing/config yang benar. Implementasi siap diuji tidak sama dengan publikasi main atau rilis; tidak ada publikasi/deployment sebagai bagian penyusunan rencana ini.

## Kriteria selesai implementasi

- Owner daftar di web lalu masuk APK dan mendapatkan UUID bisnis yang sama. Retry registrasi dan aktivasi tidak membuat akun/bisnis ganda.
- User lama dapat beralih ke username/password tanpa kehilangan data, jalur pemulihan atau hubungan HRIS/POS. Login Google lama baru ditutup setelah migrasi pengganti siap.
- Kasir ditolak ketika mencoba tenant/outlet lain, endpoint finance, ekspor kontak, data HPP atau tindakan yang tidak diberi izin, termasuk melalui header/body buatan, sync, upload dan AI.
- Pencabutan pegawai/akun dan reset password menolak sesi sesuai aturan; logout satu perangkat tidak mengunci perangkat lain. Mengaktifkan pegawai tidak membuka blokir akun lain secara tidak sengaja.
- Role legacy dan kolom izin lama memiliki pemetaan yang diuji. Platform admin, owner bisnis dan pengelola dengan delegasi tidak tertukar.
- Provider AI tiruan menerima hanya konteks yang diizinkan. Pergantian pengguna/outlet dan pencabutan izin tidak memakai history, cache, RAG atau draft yang lebih luas. Konfirmasi tindakan memeriksa ulang izin/version dan retry memberi satu efek.
- GPS di dalam/luar/batas radius, sampel lama, akurasi buruk, izin ditolak dan perubahan policy menghasilkan status yang benar. Foto wajib tidak dapat dilewati; mode tanpa foto tidak meminta upload.
- Dua punch bersamaan, pengajuan yang disetujui dua kali, approval bersamaan punch normal dan retry dengan koneksi terputus tetap menghasilkan satu catatan. Jadwal lintas malam dan WIB/WITA/WIT mengikuti tanggal kerja yang tepat.
- Bukti privat menolak pembacaan lintas akun/outlet. Pengajuan pending tidak dihitung hadir. Pengelola dapat menutup absensi pegawai yang aksesnya telah dicabut.
- POS/shift/riwayat pembayaran, HPP, stok, sync offline existing, Keuangan, Pembelian dan Pelanggan tetap lolos regresi yang relevan.
- Web/native diuji pada keadaan kosong/loading/error, pergantian akun, dua tema dan ukuran layar yang didukung. Validasi lokasi/foto membutuhkan uji perangkat Android nyata selain unit/backend/browser.

## Rincian yang perlu dikunci sebelum fitur terkait dibuat

| Rincian | Usulan awal | Dampak keputusan |
| --- | --- | --- |
| Fungsi OTP | Alternatif login dan pemulihan setelah nomor diverifikasi | Menentukan kontrak challenge dan onboarding nomor |
| Pemulihan owner tanpa nomor | Kode pemulihan sekali pakai | Menentukan cara mendapatkan akses kembali tanpa Google |
| Identitas login staf | Username toko + username karyawan + password pribadi | Mencegah akun owner dipakai bersama dan konflik nama antar toko |
| Tingkat pengaturan absensi | Per outlet, dengan foto default tidak wajib | Menentukan inheritance konfigurasi dan cakupan pilot |
| Waktu pemeriksaan lokasi/foto | Saat masuk dan pulang | Menentukan dua bukti dan aturan pengecualian |
| Radius dan mutu lokasi | Dikonfigurasi owner dan divalidasi lewat pilot | Menghindari aturan jarak tunggal untuk semua usaha |
| Izin offline POS | Batas masa berlaku izin dan penanganan antrean lama | Membatasi pencabutan sambil mempertahankan transaksi yang sudah terjadi |
| Masa simpan bukti | Tetapkan sebelum GPS/foto diaktifkan | Mengatur penyimpanan privat dan penghapusan bukti |

Keputusan yang belum dikunci tidak menghalangi inventaris akses, adapter izin dan pengujian fondasi server. Ia harus selesai sebelum alur yang bergantung padanya diimplementasikan atau dirilis.
