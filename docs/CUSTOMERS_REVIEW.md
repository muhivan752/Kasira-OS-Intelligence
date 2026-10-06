# Review Data Pelanggan

Permintaan Ivan, 6 Oktober 2026: rapikan data pelanggan agar dapat menjadi
konteks AI berikutnya. Halaman `/dashboard/pelanggan` kini mengikuti Keuangan
dan Pembelian. Fondasi data dibenahi; asisten lintas modul belum ditambahkan.

## Perilaku dan kontrak data

- Profil dapat dibuat dan diedit: nama, nomor HP, email, tanggal lahir,
  preferensi/catatan, dan persetujuan promo WhatsApp. Nama wajib; persetujuan
  memerlukan nomor. Mengganti nomor pada form menghapus pilihan persetujuan
  sehingga pengguna perlu mengonfirmasinya kembali. Menyimpan profil tidak
  mengirim pesan atau membuat campaign.
- Catatan layanan dan keluhan masuk timeline existing, terpisah dari catatan
  profil. Aktivitas izin promo juga tercatat. Timeline menampilkan maksimal
  100 aktivitas terakhir; riwayat nota 20 per halaman.
- Daftar 50 per halaman, pencarian server termasuk nomor lokal/internasional,
  sort stabil dengan UUID sebagai tie breaker, filter belanja berulang,
  absen 30 hari, belanja pertama 30 hari, belum belanja, dan izin promo.
  Ringkasan semua pelanggan tidak berubah mengikuti filter daftar.
- Gagal memuat menjadi error dengan retry. Tidak menampilkan nol atau daftar
  kosong palsu. Respons pencarian/detail yang sudah usang diabaikan. CSV
  secara eksplisit mengekspor halaman aktif, mempertahankan dua desimal,
  tanggal WIB, serta menetralkan formula dari nama/kontak/catatan.
- `GET /customers/workspace` dan `GET /customers/workspace/{id}` menghitung
  transaksi dari order saat dibaca, bukan dari penghitung Customer lama.
  Cakupan semua outlet milik tenant, termasuk riwayat outlet lama. Order
  dihapus/dibatalkan dikeluarkan. Order biasa memerlukan Payment paid;
  order tab memerlukan Tab paid, sehingga payment jangkar pada tab belum
  lunas tidak menggelembungkan belanja. Payment refunded biasa tidak lunas.
- Basis `paid_orders_gross`: nilai nota sesuai status lunas, sebelum
  pengurangan refund, bukan belanja bersih/arus kas/ledger refund. Tanggal
  riwayat adalah tanggal order. Satu nota dihitung satu transaksi, bukan
  jumlah kedatangan fisik. Favorit memakai kuantitas dari seluruh riwayat
  nota lunas, nama mengikuti katalog saat ini; varian riwayat memakai
  snapshot modifiers existing. Total/rata-rata berupa string Decimal2.
- Metadata `scope`, `basis`, `timezone`, `generated_at` dan profil/timeline
  menyediakan fakta terstruktur untuk integrasi AI berikutnya. Catatan staf
  harus diperlakukan sebagai data pelanggan dalam integrasi tersebut.
  Task ini tidak memberikan daftar kontak kepada provider AI dan tidak
  menghubungkan chat utama ke seluruh konteks pelanggan.
- Create/edit/note memakai UUID permintaan, fingerprint payload/user/action,
  advisory lock, serta hasil di AuditLog existing dalam transaksi yang sama.
  Replay sama mengembalikan hasil sama; UUID dengan isi berbeda409. Edit
  memakai row lock dan row_version; jalur edit profil legacy juga menaikkan
  versi dan mengunci baris. Tidak ada merge/hapus kontak otomatis.
- Permintaan dengan hasil tidak pasti dibekukan dan dapat dilanjutkan
  setelah dialog ditutup atau halaman direload melalui sessionStorage yang
  dipisahkan per tenant/pengguna. Jika storage diblokir, retry tersedia
  selama halaman masih terbuka. Ini bukan fitur offline.
- Nomor 08/+62 dinormalisasi, nomor internasional tetap didukung, duplikat dibandingkan juga terhadap format
  nomor legacy. Kontak tanpa nomor memakai phone string kosong karena skema
  existing NOT NULL, tetapi API menampilkan null dan HMAC identitas unik
  per kontak. Endpoint POS legacy juga bisa menambah beberapa kontak tanpa
  nomor. Tidak perlu migrasi atau mengubah relasi order pelanggan.
- Segmen CRM legacy tetap tersedia melalui modul promo. Refresh mengenali
  satu timestamp segmen yang kosong di antara baris yang sudah dihitung;
  produk favorit usang dibersihkan ketika tidak ada item terbaru. Halaman
  pelanggan memakai kelompok berdasarkan fakta langsung, bukan badge RFM
  cached sebagai sumber ringkasan.

## Desain

Design Read diumumkan sebelum edit: dashboard pelanggan untuk operator dan
pemilik bisnis, mengikuti bahasa visual Selaris/Keuangan/Pembelian, dial
ENERGY1/RHYTHM1/MOTION1. Kontak dan profil menjadi fokus pekerjaan, Tambah
pelanggan satu tindakan utama coral. Ringkasan bisnis mendahului daftar;
baris dan whitespace memisahkan profil, nota, preferensi, dan catatan layanan.
Font/token existing menjaga kesatuan produk. Angka tabular memudahkan
perbandingan nilai. Tidak menambah aset, ikon dekoratif, atau navigasi baru.
InventoryDialog native menyediakan fokus, Escape, backdrop, dan focus trap.

## Verifikasi

- PASS: 25 unittest, termasuk validasi kontak/tanggal/nama dan Decimal,
  regresi Keuangan/Pembelian/HPP snapshot; log `/tmp/selaris-customers-unit.log`.
- PASS: `tests/customers-isolated.py` pada schema-only PostgreSQL terisolasi,
  dua tenant sintetis, akun aplikasi non-superuser/RLS. Concurrent create,
  edit/note replay, fingerprint conflict, versi profil, duplikat format
  nomor, beberapa kontak tanpa HP termasuk endpoint POS, tenant boundary,
  validasi input, fresh totals meski penghitung999, paid tab versus pending
  anchor/cancelled/unpaid/refunded, favorit seluruh riwayat, pagination,
  literal search, ringkasan terpisah filter, transaksi baru langsung tampil,
  timestamp segmen campuran, edit profil legacy dan favorit usang.
- PASS: browser development mengklik search/sort/filter/reset, pagination,
  CSV, create/edit/note, unknown-result retry setelah close/reload, riwayat,
  detail retry, persetujuan ulang saat mengganti nomor, error/empty/loading,
  draft terpisah akun, keyboard/focus/Escape. Lima viewport320/375/768/1024/
  1440, tema terang/gelap, teks200%, AA4.5 dan kontrol44px.
- PASS: TypeScript tanpa diagnostik, py_compile backend terpasang,
  `git diff --check`. Screenshot fixture terang/gelap diperiksa secara visual.
- PASS: live demo backend GET workspace/detail/POS HTTP200, kontrak scope/
  decimal, pencarian literal, dan ringkasan/detail konsisten. Tidak ada
  create/edit/note test pada database toko dan tidak memanggil provider.

- PASS: build Next standalone final dan suite browser pelanggan pada image
  produksi final4ec997…9395, termasuk recovery draft lintas reload dan
  pembatasan akun. Log `/tmp/selaris-customers-frontend-final-build.log` dan
  `/tmp/selaris-customers-browser-production.log`.

## Delivery Gate Anti Slop

Hard Gate:

- R-02 PASS: copy authored tanpa em dash, memakai nama/profil/nota/catatan konkret.
- R-03 PASS: lima viewport dan teks200% tanpa overflow pada halaman/form/profil.
- R-17 PASS: ringkasan memakai order DB; fixture hanya digunakan dalam pengujian.
- R-18 PASS: tidak menambahkan testimonial.
- R-23 PASS: token/font/komponen/navigasi existing; tanpa aset baru.
- R-24 PASS: tidak membuat link navigasi baru.
- R-25 PASS: browser mengukur teks>=4.5:1 pada kedua tema.
- R-26 PASS: search/filter/sort/pagination/CSV/profil/catatan/retry benar-benar diklik.
- R-27 PASS: loading, error dengan retry, dan empty state tersedia dan diuji.
- R-28 PASS: tidak menambahkan FAQ.
- R-32 PASS: label/focus ring/dialog native; Tab, Shift+Tab, Escape dan focus restore diuji.
- R-33 PASS: source dan CSS ditulis langsung.
- R-34 PASS: tema terang/gelap pada halaman, profil, dan form lulus browser.
- R-35 PASS: build standalone dan click-through image produksi final lulus.
- R-36 PASS: tidak mengklaim asisten lengkap, data transaksi anonim, atau net refund.
- R-37 PASS: arah mengikuti dashboard existing/user-friendly dan Design Read sebelum edit.
- R-38 PASS: tidak menanam data fixture ke database/aplikasi merchant.

Purpose Gate:

- R-01 PASS: tanpa gradient dekoratif; warna mengikuti token existing.
- R-04 PASS: tidak menambah ikon generik; kontrol memakai teks pekerjaan.
- R-06 PASS: font existing untuk konsistensi; tabular numerals untuk membandingkan uang.
- R-07 PASS: tanpa grid/pola latar dekoratif.
- R-08 PASS: tanpa panah dekoratif.
- R-09 PASS: persetujuan promo berupa status teks dari profil, bukan badge pemasaran.
- R-10 PASS: tanpa glassmorphism.
- R-12 PASS: batas panel memisahkan data, tanpa shadow dekoratif baru.
- R-13 PASS: tanpa glow.
- R-14 PASS: ringkasan dan baris mengikuti data CRM, bukan feature cards seragam.
- R-19 PASS: tidak menambah animasi dekoratif.
- R-22 PASS: tidak membuat ilustrasi.

Liveliness:

- PASS: dial ENERGY1/RHYTHM1/MOTION1 dinyatakan untuk pekerjaan operasional.
- PASS: tampilan tenang mengikuti dial dan halaman Keuangan/Pembelian.
- PASS: Tambah pelanggan sebagai fokus tindakan; profil sebagai fokus data.
- PASS: whitespace memisahkan kontak, transaksi, dan catatan layanan.
- PASS: coral pada tindakan utama mengikuti brand existing.
- PASS: bahasa nota lunas/izin promo/preferensi pelanggan menjadi motif pekerjaan.
- PASS: Design Read diberikan sebelum edit dan alasan tercatat pada bagian Desain.

Craftsmanship dan Quality Locks:

- C-1 PASS: pilihan visual punya alasan brand, data, dan pekerjaan yang tertulis.
- C-2 PASS: setiap kontrol memiliki aksi aktual dan lulus click-through.
- C-3 PASS: section hanya memuat ringkasan, daftar, profil, riwayat dan catatan.
- C-4 PASS: tema, viewport, teks200%, error/retry, keyboard dan pending storage diuji.
- C-5 PASS: angka produk dari DB; batas gross/refund/scope dinyatakan.
- R-05 PASS: komposisi mengikuti pekerjaan CRM, tanpa section pemasaran.
- R-11 PASS: radius panel/control/form mengikuti komponen existing.
- R-15 PASS: CTA menyebut Tambah pelanggan, Simpan profil dan Periksa penyimpanan.
- R-16 PASS: copy tanpa jargon promosi AI.
- R-20 PASS: visual Selaris dan alur POS/nota/catatan khusus bisnis dipertahankan.
- R-21 PASS: kedua tema mengikuti pilihan pengguna.
- R-29 PASS: palette memakai neutral/brand/danger existing.
- R-30 PASS: tidak meniru produk luar.
- R-31 PASS: keputusan utama visual tertulis pada bagian Desain.

## Deployment

Live 6 Oktober 2026 sekitar07:36 UTC. Enam file backend dipasang dengan
docker cp, py_compile, dan restart container existing saat pekerjaan HPP
aktif nol. Hash final seluruh file sama dengan source. Container backend
created4Okt dan image160766…31a tetap. Backup tiga file existing dan image
frontend sebelumnya di `/tmp/selaris-customers-backup`; tiga file backend
lain merupakan modul baru, tidak mengubah skema DB.

Frontend dibangun dan diuji pada image final
`sha256:4ec9977035ba02f7601767288790a1511e9eaa578899dd40cd03fc051fe09395`,
lalu `compose up -d --no-deps frontend`. Container created07:36:44UTC.
Demo live API workspace/detail/POS HTTP200, list/detail total dan transaksi
sesuai; search literal tidak memengaruhi ringkasan. Browser live real Server
Actions membuka profil, riwayat/catatan, edit dan tambah form, Escape, serta
mobile375 tanpa overflow/page errors. Semua verifikasi merchant read-only.
Keempat layanan healthy; `/health` DB dan background tasks sehat. Token demo
sementara, dev server, container/database dan network QA telah dibersihkan.
Tidak recreate backend, migrasi, push main atau rilis APK. APK tetap1.6.31.
