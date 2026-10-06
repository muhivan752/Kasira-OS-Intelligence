# Izin Keuangan, Pembelian, CRM dan HPP

6 Oktober 2026. Ivan meminta “gas tahap 2” setelah tahap POS/stok/sync live. Scope ini membuka empat domain untuk managed staff melalui web. Semua handler AI, chat HPP, OCR dan API alternatif yang belum mendukung managed masih ditolak server. Native POS/Dapur tetap 1.6.33+200; tidak ada perubahan APK pada tahap ini.

Registry `business_access.py` mencocokkan 31 callable endpoint dan HTTP method. `deps.get_current_user` memuat izin dan cakupan terbaru sebelum handler berjalan. Outlet aktif, brand aktif, tenant, parent resep/produk, resource dan ID path/query/body diperiksa; dua nilai query yang bertentangan juga ditolak. Owner aktual dan legacy mempertahankan alur existing. Role lama tidak dimigrasikan otomatis. Tidak ada migrasi database baru; schema tetap 114.

| Izin | Perilaku |
| --- | --- |
| `finance.view` | Laporan dan pengeluaran outlet yang diizinkan, termasuk ringkasan HPP/laba dan utang. Tidak mengizinkan perubahan atau rincian resep. |
| `finance.manage` | Catat/ubah/hapus pengeluaran, salin pengeluaran bulanan dan kelola akun kas. Pengeluaran tanpa outlet serta perubahan akun kas bersama membutuhkan cakupan seluruh bisnis. |
| `purchasing.view` | Nota dan profil supplier. Agregat supplier dibatasi outlet yang diizinkan, termasuk saat outlet tidak disebutkan. |
| `purchasing.manage` | Supplier, pencatatan nota dan pembayaran. Nota/pembayaran juga membutuhkan `supplier.price.view`; penerimaan stok membutuhkan `stock.receive`. Produk baru tetap ditambahkan pemilik. Bahan baru membutuhkan `hpp.manage` dan `hpp.approve`. |
| `supplier.price.view` | Harga pembelian dan nominal nota. Tanpa izin ini nominal, foto nota, catatan bebas dan riwayat pembayaran disamarkan. Biaya sebelum/sesudah juga membutuhkan `hpp.view`. |
| `customers.view` | Profil dan catatan bersama bisnis; statistik, pencarian/sort/segmen, riwayat dan produk favorit memakai transaksi dari outlet yang diizinkan. |
| `customers.manage` | Tambah/ubah profil dan catatan bersama bisnis. Tidak otomatis memberi ekspor. |
| `customers.export` | Tombol CSV meminta ulang data dengan `export=true`; server memeriksa izin ekspor dan cakupan data. Data yang memang boleh dibaca tetap dapat disalin pengguna. |
| `hpp.view` | Resep/HPP katalog bersama brand dalam cakupan outlet. Harga pembelian mentah memerlukan izin harga terpisah. |
| `hpp.manage` dan `hpp.approve` | Endpoint manual yang langsung menyimpan bahan/resep membutuhkan keduanya. Editor web juga membutuhkan `supplier.price.view` karena mengedit harga bahan. Draft AI dan persetujuan chat termasuk tahap berikutnya. |

Owner dapat memilih cakupan outlet tertentu atau **seluruh bisnis**, termasuk outlet aktif baru. Daftar outlet kosong tidak sah untuk cakupan outlet; cakupan seluruh bisnis tidak memakai daftar outlet/brand terpisah. Jabatan tenant dapat dipasang ke akun karyawan. Role brand dari kontrak fondasi tetap dikenali server, tetapi editor baru hanya menawarkan outlet/tenant.

Keuangan outlet tidak memasukkan pengeluaran global, termasuk pada tren dan salinan bulanan. Akun kas shared boleh dipilih saat mencatat pembayaran, tetapi saldo awal shared disamarkan pada cakupan outlet; akun milik outlet lain disaring. Membaca laporan managed tidak membuat akun kas baru. Shared profil supplier/pelanggan dan katalog brand merupakan batas data yang ditampilkan pada editor izin.

Web mengikuti izin lihat/tindakan, memilih outlet HPP dari cookie hanya jika masih diizinkan dan memeriksa manifest baru saat pindah halaman/foreground. Hasil manifest lama tidak menimpa hasil request yang lebih baru. Manifest rusak tidak boleh dianggap owner. Server tetap memeriksa tiap request, termasuk request dengan JWT yang sudah ada setelah izin dicabut. Pending UUID dan key workspace existing dipertahankan; algoritme stok, unit resep dan HPP tidak diubah.

## QA

PostgreSQL schema-only terpisah, data sintetis dua tenant dan beberapa outlet/brand, FORCE RLS dengan app NOSUPERUSER/NOBYPASSRLS. Jaringan internal tanpa port publik dan tanpa provider keys. Browser memakai fixture localhost, bukan data merchant.

- Backend: 64 test, 63 PASS dan satu fixture opsional skip; `/tmp/selaris-business-unit-final.log`.
- HTTP/JWT: tujuh kelompok PASS, termasuk domain independen, sibling outlet satu brand, ID/query/nested parent palsu, redaction, UUID replay stok/pembayaran/profil, tenant role assignment/replay, malformed JSON, pencabutan pada JWT aktif, brand nonaktif, owner/legacy dan forced RLS; `/tmp/selaris-business-qa-http-final.log`, `tests/business-access-isolated.py`.
- Regresi finance/purchasing/customer/accounts PostgreSQL PASS; matematika HPP 21 dan katalog 5 test PASS. Adapter hanya mengganti guard/kredensial sintetis agar suite lama memakai database QA yang sama. `/tmp/selaris-business-legacy-regressions.log`.
- Browser Keuangan/Pembelian/CRM/HPP pada image produksi PASS: lima lebar, dua tema, teks 200%, AA kontras, kontrol 44px, keyboard/fokus/Escape, error/loading/empty, retry dengan UUID yang sama, unit lama dan entry links. `/tmp/selaris-business-production-{finance,purchasing,customers,hpp}.log`.
- Browser managed pada image produksi PASS: izin baca empat modul, nominal tersamar, pilihan outlet cookie HPP, ekspor terpisah, chat diblokir dan foreground revoke. `/tmp/selaris-business-production-business-access.log`.
- Build produksi pertama PASS; kandidat final menambah validasi struktur manifest. Hasil kandidat final dan deployment dicatat pada dokumen release setelah diperiksa.

Tidak ada write merchant, perubahan antrean native atau klaim pengujian perangkat fisik. Granularisasi seluruh AI/context/cache/history/RAG/worker/write adalah tahap berikutnya. Lease offline/GPS/foto/OTP/radius/retensi tetap keputusan tersendiri.
