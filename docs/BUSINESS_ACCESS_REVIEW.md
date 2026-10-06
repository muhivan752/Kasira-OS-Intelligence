# Izin Keuangan, Pembelian, CRM dan HPP

Backend/web live; deployment [BUSINESS_ACCESS_RELEASE.md](BUSINESS_ACCESS_RELEASE.md).

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
- Browser Keuangan/Pembelian/CRM/HPP pada image produksi PASS: lima lebar, dua tema, teks 200%, AA kontras, kontrol 44px, keyboard/fokus/Escape, error/loading/empty, retry dengan UUID yang sama, unit lama dan entry links. `/tmp/selaris-business-final-{finance,purchasing,customers,hpp}.log`.
- Browser managed pada image produksi PASS: izin baca empat modul, nominal tersamar, pilihan outlet cookie HPP, ekspor terpisah, chat diblokir dan foreground revoke. `/tmp/selaris-business-final-business-access.log`.
- Browser akun/POS image final PASS; editor sebelas izin business dan tenant scope diuji. `/tmp/selaris-business-final-accounts.log`, `/tmp/selaris-business-final-pos-access.log`.
- TypeScript dan build produksi final PASS. Manifest rusak ditolak pada browser kandidat final; `/tmp/selaris-business-tsc-final.log`, `/tmp/selaris-business-frontend-build-final.log`, `/tmp/selaris-business-final-business-access.log`. Deployment dicatat pada dokumen release.

Tidak ada write merchant, perubahan antrean native atau klaim pengujian perangkat fisik. Granularisasi seluruh AI/context/cache/history/RAG/worker/write adalah tahap berikutnya. Lease offline/GPS/foto/OTP/radius/retensi tetap keputusan tersendiri.

## Arah visual dan Delivery Gate antislop

Perubahan mengikuti Selaris existing: warm neutral, charcoal, coral, Source Sans 3. ENERGY 1 / RHYTHM 1 / MOTION 1 telah diumumkan sebelum penyempurnaan web. Heading pekerjaan, pilihan outlet dan daftar/form melayani pengelolaan toko; coral menandai tindakan simpan. Gate ini mencakup binding yang berubah dan tampilan baca baru. Trace `/tmp/selaris-business-managed-trace.zip`, screenshot `/tmp/selaris-business-managed-hpp.png`, serta log browser di bagian QA adalah bukti interaksi.

- R-02 PASS: pemeriksaan copy baru di source tidak menemukan em dash.
- R-03 PASS: empat/lima lebar dan 200% teks diuji tanpa overflow, termasuk HPP read-only.
- R-17 PASS: angka berasal dari API; fixture QA berlabel sintetis, tidak menambah statistik pemasaran.
- R-18 PASS: tidak menambah testimonial.
- R-23 PASS: aset/brand existing; navigasi empat modul mengikuti tahap 2 yang diminta Ivan.
- R-24 PASS: route Keuangan/Pembelian/Pelanggan/HPP nyata dan dibuka browser; link HPP dari modul existing juga diuji.
- R-25 PASS: formula WCAG pada browser menghitung teks/kontrol di kedua tema; tampilan managed baru turut diperiksa.
- R-26 PASS: outlet, ekspor, supplier, profil/catatan, pengeluaran dan resep memiliki handler nyata; browser mengklik alur tersebut.
- R-27 PASS: suite menjalankan loading/error/retry/empty, timeout write dan pencabutan izin; nominal tidak diizinkan ditulis jelas.
- R-28 PASS: tidak menambah FAQ.
- R-32 PASS: kontrol berlabel; Tab, fokus, Escape dan fokus setelah dialog ditutup diuji suite affected.
- R-33 PASS: implementasi dalam source repository; fixture hanya menyediakan data dan memanggil app yang dibuild.
- R-34 PASS: tema terang/gelap diuji pada seluruh lebar affected, termasuk kartu HPP baca.
- R-35 PASS: Docker production build dijalankan; klik UI disimpan dalam trace dan API mutation diuji dengan JWT/PostgreSQL.
- R-36 PASS: tidak menambah klaim sertifikasi/kinerja; cakupan shared data dan batas QA dicatat.
- R-37 PASS: mengikuti arah Selaris dan dials yang diumumkan; tidak menciptakan arah brand baru.
- R-38 PASS: produk memakai data API; contoh hanya ada di fixture QA berlabel.
- R-01 PASS: tidak menambah gradient/glow.
- R-04 PASS: Wallet/ShoppingCart/Users/Calculator merujuk empat domain; ikon existing disertai label.
- R-06 PASS: typography brand existing, tanpa heading monospace baru.
- R-07 PASS: tidak menambah background grid/dot.
- R-08 PASS: tidak menambah panah dekoratif pada CTA.
- R-09 PASS: tidak menambah badge pemasaran.
- R-10 PASS: tidak menambah glassmorphism.
- R-12 PASS: panel baru memakai border/style HPP existing, tanpa shadow besar.
- R-13 PASS: tidak menambah glow.
- R-14 PASS: laporan/daftar/form/kartu resep mengikuti jenis pekerjaan, bukan kartu fitur seragam.
- R-19 PASS: state loading/disabled mengikuti request; tidak menambah animasi dekoratif.
- R-22 PASS: tidak menambah ilustrasi.
- Liveliness dials PASS: ENERGY 1 / RHYTHM 1 / MOTION 1 dinyatakan untuk pengelolaan toko.
- Liveliness consistency PASS: urutan heading/filter/data/form dan interaksi tenang terlihat pada screenshot/trace.
- Liveliness focal point PASS: heading domain dan angka laporan atau resep terpilih menjadi pusat tiap layar.
- Liveliness whitespace PASS: spacing existing memisahkan outlet, daftar dan form.
- Liveliness accent PASS: coral pada tindakan utama existing; akses baca tidak menawarkan save yang tidak diizinkan.
- Liveliness identity PASS: font, warm neutral dan kontrol Selaris berulang lintas modul.
- Liveliness Design Read PASS: arah existing dan dials diumumkan sebelum penyempurnaan layar.
- C-1 PASS: panel/filter/form mengikuti penggunaan toko dan style existing, bukan default baru.
- C-2 PASS: setiap binding baru memiliki action/endpoint nyata; checkbox/scope/CSV/outlet diuji.
- C-3 PASS: bagian baru menyatakan cakupan data atau tindakan yang diizinkan.
- C-4 PASS: mobile/tema/200%/keyboard dan error/revoke diuji; perangkat fisik belum diuji.
- C-5 PASS: tidak ada testimonial/statistik/klaim fiktif.
- R-05 PASS: layout pengelolaan toko existing, tanpa hero/bento/pricing.
- R-11 PASS: radius panel/form/button mengikuti CSS brand existing.
- R-15 PASS: CTA menyebut tindakan seperti Catat nota, Catat pengeluaran, Ekspor halaman CSV dan Simpan jabatan.
- R-16 PASS: tidak menambah buzzword pemasaran.
- R-20 PASS: identity Selaris dan bahasa pengelolaan toko dipertahankan.
- R-21 PASS: kedua tema tersedia dan diperiksa browser.
- R-29 PASS: palette existing warm neutral/charcoal/coral; tidak menambah palette lain.
- R-30 PASS: perubahan mengikuti UI Selaris existing, tanpa meniru produk lain.
- R-31 PASS: typography untuk baca laporan, spacing untuk cakupan/form, coral untuk simpan dan state baca untuk grant terbatas dijelaskan di atas.
