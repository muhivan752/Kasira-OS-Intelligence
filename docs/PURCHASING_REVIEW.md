# Review Pembelian, 6 Oktober 2026

Ivan meminta Pembelian dirapikan sebelum memperluas konteks bisnis untuk AI.
Pekerjaan ini membenahi dashboard dan jalur nota yang sudah ada. Nota mencatat
barang yang sudah diterima, bukan pesanan pembelian formal atau draft stok.
Pembayaran utang menyimpan catatan pembayaran yang sudah dilakukan.

## Perilaku dan batas

- Outlet mengikuti pilihan sesi dan dapat diganti. Ringkasan penerimaan dan
  daftar nota memakai bulan WIB. Utang/overdue adalah posisi saat ini dari
  semua bulan; filter belum lunas tidak dibatasi bulan penerimaan.
- Pencarian nomor internal/nomor supplier/nama supplier dilakukan server,
  karakter `%`/`_` literal. Pagination menampilkan 50 nota dengan indikator
  halaman lanjutan; ringkasan bukan penjumlahan halaman yang terlihat saja.
- Error baca tampil eksplisit dengan retry, tidak menjadi nol atau daftar
  kosong. Respons lama tidak mengganti data outlet/periode terbaru.
- Nota dan cicilan memakai UUID, fingerprint pada after_state audit existing,
  serta advisory lock tenant/request. Replay identik mengembalikan nota yang
  sama. Permintaan berbeda mendapatkan 409. Expense/barang/event stok hanya
  tersimpan sekali. Pengujian race memakai HTTP dan PostgreSQL sebenarnya.
- Form mempertahankan payload saat respons tidak pasti; sessionStorage
  menyimpan permintaan nota/cicilan pada tab browser yang sama, termasuk saat
  dialog ditutup atau halaman dimuat ulang. Jika browser memblokir storage,
  retry tetap tersedia selama modal masih terbuka. Bukan dukungan offline.
- Penerimaan memanggil helper stok existing. Nomor nota diserialisasi dan
  memakai urutan maksimum, bukan jumlah baris. Target stok/harga dikunci dalam
  urutan tetap; harga setiap baris di-flush agar target berulang memakai harga
  terakhir dalam transaksi yang sama. Baris invalid membatalkan semua efek.
- Produk menghitung harga modal dari total aktual baris/pcs, termasuk total
  override dan konversi kemasan COUNT yang dikenal backend. Form produk
  menggunakan pcs. Jumlah bahan dikonversi dengan UNIT_ALIASES existing;
  harga modal bahan tetap delapan desimal. Quantity resep/deduct tidak diubah.
- Target harus berada di brand outlet dan tenant yang benar. Starter tetap
  mendukung produk/biaya dan menolak bahan. Estimasi overhead bukan stok bahan;
  biaya dicatat lewat baris Biaya. Supplier nonaktif tidak dipakai nota baru.
- Nota lama menampilkan efek harga modal dari event penerimaan existing.
  Beberapa baris target yang sama memiliki snapshot masing-masing. Riwayat
  cicilan memakai selisih paid_after/paid_before, bukan nominal permintaan
  lama yang mungkin berlebih; bagian tidak terbukti ditandai tidak lengkap.
- Supplier bersama di tingkat bisnis, tetapi angka belanja/utang ditampilkan
  khusus outlet terpilih. Edit memakai row lock/version dan nama duplikat
  ditolak. Nonaktif/hapus tidak menghapus nota dan utang historical.
- Foto mengisi draft dan tidak langsung menerima stok. Baris belum cocok
  harus ditentukan; baris tidak lengkap tidak dibuang diam-diam. Proxy baru
  `/api/upload/invoice` memakai lokasi Nginx upload existing, menghindari batas
  Server Actions 1 MB. Maksimal web 8 MB, JPG/PNG/WebP; supplier/brand berasal
  dari outlet yang dipilih. Pengujian foto memakai fixture sintetis 2 MB;
  tidak mengirim foto atau data merchant ke provider OCR/LLM.
- Cache AI dan storefront untuk outlet dalam brand diperbarui setelah commit
  penerimaan. Pekerjaan ini tidak membangun chat persisten/satu pusat AI baru.
- Keuangan tetap menghitung pembayaran awal di tanggal penerimaan dan cicilan
  di tanggal event. Akun asal pembayaran nota belum disimpan. Koreksi/cancel
  nota yang sudah diterima, PO formal, return supplier, dan pembayaran bank
  otomatis belum ditambahkan; jangan mengklaim fungsi tersebut tersedia.

## Desain

Design Read disampaikan sebelum edit: mengikuti dashboard Selaris dan Keuangan,
neutral hangat + coral, font/token existing, ENERGY 1 / RHYTHM 1 / MOTION 1.
Total belanja dipisahkan dari utang current agar pengguna tidak menyamakan
penerimaan barang dengan pembayaran. Nota memakai baris lebar dengan nominal
di kanan; di HP nominal menumpuk di bawah. Form barang memakai label per
baris, total override dijelaskan, dan modal native menjaga fokus/Escape.
Style kontrol Keuangan dipakai bersama supaya UI tidak mempunyai sistem
warna/form kedua. Tidak membuat aset visual atau mengubah navigasi.

## Validasi

- PASS: 22 unittest validasi purchasing dan regresi finance/HPP snapshot.
- PASS: `tests/purchasing-isolated.py`, schema existing tanpa data merchant,
  role non-superuser/RLS, replay concurrent nota/cicilan, konflik edit,
  rollback baris invalid, referensi tenant/brand, kg/dus, precision delapan
  desimal, snapshot target berulang, penomoran concurrent, supplier/OCR scope,
  pencarian literal, utang/overdue dan finance bulan pembayaran yang cocok.
  Warning Redis pada QA terisolasi menunjukkan cache best-effort; assertion
  SQL/HTTP tetap lulus. Layanan produksi tidak dipakai untuk pengujian write.
- PASS: browser fixture outlet/periode/pencarian/pagination, decimal/WIB pada
  timezone Amerika, pemulihan nota dan cicilan dengan payload identik,
  supplier create/edit/nonaktif/hapus, kontrol barang baru dan foto sebagai
  draft. Error/read retry/empty state, Escape dan lima viewport dua tema
  dengan teks 200% sudah diuji; teks >=4.5:1, kontrol utama >=44px.
- PASS: TypeScript tanpa diagnostik dan `git diff --check`.
- PASS: build Next standalone produksi, suite Pembelian termasuk foto 2 MB
  dan suite regresi Keuangan pada image produksi final.
- PASS: demo live GET purchase summary/list/suppliers dan finance HTTP200;
  utang current/overdue identik. Bulan terpilih live kosong, jadi detail dan
  history menggunakan bukti SQL/HTTP serta browser sintetis, bukan klaim
  melihat riwayat pembayaran merchant di production.
- PASS: browser live memuat setup/barang, modal buka/Escape, supplier dan
  viewport HP tanpa overflow. Proxy foto lewat domain publik mengembalikan
  validasi HTTP400 sebelum provider dipanggil. Tidak ada test write merchant.

Log lokal `/tmp/selaris-purchasing-{unit,integration,browser,tsc}.log`;
screenshot fixture `/tmp/selaris-purchasing-{light,dark}.png`.

## Delivery gate antislop

Hard Gate:

- R-02 PASS: copy authored tanpa em dash; kata penerimaan/pembayaran konkret.
- R-03 PASS: halaman/form lima viewport dan 200% teks tanpa overflow.
- R-17 PASS: produk memakai API; semua data pengujian berlabel fixture.
- R-18 PASS: tidak ada testimonial.
- R-23 PASS: memakai token/komponen existing; tidak membuat aset/navigasi.
- R-24 PASS: link Keuangan/Pengaturan menuju route existing.
- R-25 PASS: teks terukur >=4.5:1 pada dua tema.
- R-26 PASS: kontrol nota, supplier, filter, search, pagination, retry dan foto berfungsi.
- R-27 PASS: loading, error/retry, dan empty state diuji.
- R-28 PASS: tidak menambah FAQ.
- R-32 PASS: label/focus ring, modal native, fokus dan Escape tersedia.
- R-33 PASS: source/CSS ditulis langsung.
- R-34 PASS: tema terang/gelap dan modal diuji.
- R-35 PASS: dashboard dijalankan dan alur diklik pada Chromium.
- R-36 PASS: tidak mengklaim transfer, PO formal atau akuntansi penuh.
- R-37 PASS: direction dari dashboard existing/user friendly dipakai sebelum edit.
- R-38 PASS: tidak menanam data screenshot sintetis pada produk.

Purpose Gate:

- R-01 PASS: warna status menandai utang; tanpa gradient dekoratif.
- R-04 PASS: plus untuk nota dan refresh untuk muat ulang, mengikuti kontrol Keuangan.
- R-06 PASS: font existing, angka tabular untuk membandingkan nominal.
- R-07 PASS: tanpa pola background.
- R-08 PASS: tanpa panah dekoratif.
- R-09 PASS: status lunas/utang/nonaktif menyatakan keadaan nyata.
- R-10 PASS: tanpa glassmorphism.
- R-12 PASS: batas memisahkan catatan, tanpa shadow baru.
- R-13 PASS: tanpa glow.
- R-14 PASS: layout berdasarkan penerimaan, utang, nota dan form, bukan feature cards.
- R-19 PASS: tidak menambah animasi dekoratif.
- R-22 PASS: tidak membuat ilustrasi.

Liveliness:

- PASS: dials 1/1/1 untuk laporan operasional.
- PASS: CTA Catat nota sebagai fokus tindakan, utang current sebagai fokus pemeriksaan.
- PASS: whitespace memisahkan scope/ringkasan/daftar dan baris form.
- PASS: coral hanya untuk tindakan utama dan active selection.
- PASS: bahasa stok/harga modal/nota spesifik pada alur aplikasi.
- PASS: Design Read sebelum edit dicatat dalam commentary dan alasan di atas.

Craftsmanship dan Quality Locks:

- C-1 PASS: alasan warna/layout/font/kontrol tercatat di bagian Desain.
- C-2 PASS: setiap kontrol punya aksi aktual, tanpa TODO palsu.
- C-3 PASS: section sesuai pekerjaan penerimaan/utang/supplier.
- C-4 PASS: viewport/theme/error/empty dan dialog keyboard diuji.
- C-5 PASS: angka produk dari backend dan batas fungsi dinyatakan.
- R-05 PASS: urutan mengikuti pekerjaan pembelian, tanpa section pemasaran.
- R-11 PASS: panel/form/control memakai radius sesuai fungsi existing.
- R-15 PASS: CTA menyebut simpan nota, catat pembayaran dan periksa penyimpanan.
- R-16 PASS: copy tanpa jargon promosi AI.
- R-20 PASS: visual dashboard existing dan alur nota/HPP khusus bisnis dipakai.
- R-21 PASS: kedua tema mengikuti pilihan pengguna.
- R-29 PASS: neutral/brand/danger mengikuti token existing.
- R-30 PASS: tidak meniru produk luar.
- R-31 PASS: keputusan visual utama dijelaskan di bagian Desain.

## Deployment

Terpasang 6 Oktober 2026 sekitar07:09 UTC. Empat file backend dicadangkan di
`/tmp/selaris-purchasing-backup`, lalu disalin dan restart existing ketika
pending HPP nol. Hash runtime/source cocok. Image/container backend tetap
`160766c62c58c2be22ea7893461d77951b46d70289904fd1e4920ad9ac5fd31a`.

Frontend standalone dibangun dan dua suite browser production lulus sebelum
`compose up -d --no-deps frontend`, image
`d10c428f7a476d7c8ea10d7a39ee682fd44bce6609566062e5e26c1228d43380`.
Frontend dibuat setelah mtime source final. Backend/frontend/db/redis sehat,
health db/bg_tasks sehat dan frontend HTTP200. Tidak recreate backend atau
migrasi database, tidak push main atau merilis APK; source masih uncommitted
bersama pekerjaan sebelumnya.

Log deployment/verifikasi: `/tmp/selaris-purchasing-frontend-build.log`,
`/tmp/selaris-purchasing-browser-production.log`,
`/tmp/selaris-purchasing-finance-regression.log`,
`/tmp/selaris-purchasing-live-{check,browser}.log`.
