# Review keuangan, 6 Oktober 2026

Ivan meminta keuangan dibuat lebih profesional dan tetap mudah digunakan.
Perubahan ini memperbaiki laporan dan pencatatan existing, serta memasok fakta
keuangan terbaru ke chat umum. Pencatatan pengeluaran lewat chat dan pengingat
terjadwal belum diimplementasikan; formulir Keuangan dan Nota belanja tetap
menjadi jalur penyimpanan.

## Perilaku

- Pembayaran awal nota mengikuti tanggal penerimaan; cicilan mengikuti tanggal
  event pembayaran. Event lama yang berisi nominal permintaan berlebih dibaca
  dari selisih `paid_after`, sehingga hanya uang yang benar-benar dicatat masuk
  perhitungan. Event baru menyimpan nominal aktual dan `paid_before`.
- Nota tanpa riwayat lengkap diberi status perkiraan. Akun asal pembayaran nota
  belum disimpan pada model purchasing, sehingga laporan tidak menganggapnya
  berasal dari laci kas. Pembayaran nota tidak menggandakan Expense terkait.
- HPP keuangan memakai snapshot Decimal yang sama dengan protokol HPP native.
  Resep dengan satuan tidak valid dikeluarkan seluruhnya dari HPP yang diketahui,
  termasuk ketika sebagian bahan valid. Harga beli lama tidak menutupi resep
  yang tidak lengkap. Coverage mengikuti jumlah barang terjual.
- Laba tampil sebagai perkiraan berdasarkan HPP terkini dan biaya tercatat.
  Harga modal historis belum dibekukan, dan total POS masih mencakup pajak serta
  biaya layanan. Arus kas ditampilkan sebagai perubahan, bukan saldo bank/laci.
- Utang supplier dan nominal lewat jatuh tempo adalah posisi saat ini,
  termasuk ketika pengguna membuka laporan bulan lain. Label menegaskan ini.
- Pengeluaran mempertahankan dua desimal, tanggal WIB, dan timestamp lama jika
  tanggal tidak berubah. Validasi mencakup metode, kategori, nominal, waktu,
  supplier dan akun dari tenant yang benar. Akun historis yang tidak berubah
  tetap dipertahankan. Catatan nonkas dari stok tidak diedit melalui form biaya.
- Simpan baru memakai UUID permintaan dan fingerprint pada audit existing,
  dilindungi advisory lock transaksi. Replay identik mengembalikan catatan yang
  sama; payload atau pengguna berbeda mendapat 409. Form mempertahankan payload
  ketika hasil write tidak pasti dan memeriksa UUID yang sama pada retry.
- Edit memakai row lock dan row_version. Salin template bulanan memakai lock
  tenant/bulan dan dedup dalam satu batch. UI meminta pemeriksaan bahwa biaya
  sudah dibayar sebelum menyalin. Template bukan reminder atau pembayaran otomatis.
- Server Actions mengembalikan error sebagai data agar Next production tidak
  menyamarkan pesannya. Gagal membaca tidak menampilkan laba nol atau daftar
  biaya kosong. Perubahan outlet/periode memakai pengaman respons terlambat.
- CSV menyertakan basis laporan, periode, kelengkapan, ringkasan, arus kas,
  dan biaya. Formula dari teks pengguna diberi escape, nominal tetap numerik.
- Chat umum membaca fakta keuangan baru tanpa cache ringkasan harian, sesuai
  tenant/outlet. Konteks memuat batas periode, perkiraan, arus kas versus saldo,
  dan larangan mengaku menyimpan atau membayar. Gagal membaca tidak boleh diganti
  angka cache. Tidak menguji atau memanggil provider LLM dengan data merchant.

## Validasi

- PASS: 24 unittest, termasuk 11 keuangan dan 13 regresi HPP/sync.
- PASS: `tests/finance-isolated.py` pada PostgreSQL berstruktur existing tanpa
  data merchant, role non-superuser dan RLS. HTTP aktual membuktikan cicilan
  lintas bulan, nominal cicilan berlebih, beban nota tidak ganda,
  catatan nonkas tidak keluar kas, overdue, referensi lintas tenant ditolak,
  replay simultan hanya satu catatan, edit simultan 200/409, salin bulanan hanya
  sekali, dan konteks AI sesuai scope serta gagal secara eksplisit.
- PASS: `tests/finance-browser.cjs` memakai fixture sintetis. Outlet sesuai
  cookie, pindah bulan, desimal, tanggal WIB pada browser zona Amerika,
  timestamp edit tetap, retry write yang sama, CSV, konfirmasi biaya bulanan,
  penghapusan, error/read retry, serta empty state sudah diklik.
- PASS: browser halaman/dialog pada 320/375/768/1024/1440, terang/gelap,
  zoom teks 200%, tanpa overflow; seluruh teks terukur >=4.5:1 dan kontrol
  utama >=44px. Dialog memakai modal native, focus trap existing dan Escape.
- PASS: TypeScript `tsc --noEmit --incremental false` tanpa diagnostik.
- PASS: build image Next standalone produksi; suite browser yang sama juga
  dijalankan terhadap image produksi, bukan hanya dev server.
- PASS: live GET summary/expenses/accounts/categories toko demo HTTP200,
  scope outlet, freshness/WIB, identitas arus kas dan batas utang terverifikasi.
- PASS: browser live memakai Server Actions aktual dan laporan demo, modal
  buka/tutup tanpa menyimpan, layar HP tanpa overflow, tanpa pageerror.
- PASS: `git diff --check`.

Log lokal `/tmp/selaris-finance-{unit,integration,browser,tsc-final}.log`.
Screenshot fixture `/tmp/selaris-finance-{light,dark}.png` dan CSV sintetis
`/tmp/selaris-finance-export.csv`. Fixture tidak menggambarkan keuangan toko nyata.

## Alasan desain dan antislop

Design Read: halaman laporan operasional untuk pemilik toko; mengikuti warna
hangat dan aksen coral Selaris; ENERGY 1 / RHYTHM 1 / MOTION 1. Perhitungan
berurutan membuat angka dapat ditelusuri. Bagian kas dan utang bersebelahan di
desktop dan menumpuk di HP. Form singkat dengan penjelasan akun asal; dialog
native menjaga fokus. Tema, font, jarak dan warna memakai token existing;
ikon hanya untuk tindakan konkret. Teks dan hasil angka menjadi fokus utama.

Hard Gate:

- R-02 PASS: copy baru tanpa em dash dan memakai istilah pembayaran/biaya yang jelas.
- R-03 PASS: lima viewport dan 200% teks diuji tanpa overflow.
- R-17 PASS: semua contoh pengujian ditandai fixture; produk memakai data API.
- R-18 PASS: tidak ada testimonial.
- R-23 PASS: tidak membuat logo, avatar, aset atau struktur navigasi baru.
- R-24 PASS: link Menu/Nota/Pengaturan mengarah ke route existing.
- R-25 PASS: teks halaman dan dialog dihitung >=4.5:1 di kedua tema.
- R-26 PASS: pemilihan outlet/bulan, CRUD, salin biaya, CSV dan retry berjalan.
- R-27 PASS: loading, error eksplisit/retry dan empty state tersedia dan diuji.
- R-28 PASS: tidak menambahkan FAQ.
- R-32 PASS: kontrol native, label, focus ring, focus trap dan Escape tersedia.
- R-33 PASS: komponen dan CSS ditulis langsung pada source.
- R-34 PASS: tema terang/gelap memakai semantic tokens dan diuji.
- R-35 PASS: dashboard dijalankan dan kontrol diuji lewat Chromium.
- R-36 PASS: tidak menambahkan klaim security, akuntansi formal atau angka rekaan.
- R-37 PASS: arah profesional/user friendly memakai identitas dashboard existing.
- R-38 PASS: data screenshot sintetis hanya dalam pengujian, bukan data produk.

Purpose Gate:

- R-01 PASS: tidak menambah gradient/glow.
- R-04 PASS: ikon tambah, edit, hapus, refresh, unduh mengidentifikasi aksi.
- R-06 PASS: font dashboard existing; angka memakai tabular numerals untuk membandingkan.
- R-07 PASS: tidak menambah pola latar.
- R-08 PASS: tidak menambah panah dekoratif.
- R-09 PASS: status Perkiraan menjelaskan basis angka.
- R-10 PASS: tidak menambah glassmorphism.
- R-12 PASS: panel memakai batas untuk kelompok laporan, tanpa shadow baru.
- R-13 PASS: tidak menambah glow.
- R-14 PASS: ukuran panel mengikuti perhitungan, arus kas dan utang, bukan kartu fitur seragam.
- R-19 PASS: tidak menambah animasi dekoratif.
- R-22 PASS: tidak menambah ilustrasi.

Liveliness:

- PASS: dials 1/1/1 sesuai halaman laporan yang tenang.
- PASS: angka laba setelah biaya tercatat menjadi fokus layar.
- PASS: jarak memisahkan ringkasan, kas, biaya dan tren.
- PASS: aksen coral pada tindakan catat dan penanda bagian laporan.
- PASS: token Selaris dan istilah pembayaran konsisten.
- PASS: Design Read ditetapkan sebelum edit UI.

Craftsmanship:

- C-1 PASS: alasan warna, font, perhitungan berurutan dan layout tercatat di atas.
- C-2 PASS: semua kontrol terkait API, navigasi existing atau unduh lokal.
- C-3 PASS: tiap bagian menjawab laba, kas, utang, biaya atau perbandingan bulan.
- C-4 PASS: state/tema/viewport diuji; dialog keyboard memakai komponen existing.
- C-5 PASS: tanpa klaim atau data bisnis rekaan.
- R-05 PASS: urutan mengikuti laporan keuangan, tanpa section pemasaran.
- R-11 PASS: panel, form dan kontrol memakai radius berbeda sesuai fungsi.
- R-15 PASS: label tindakan konkret: Catat pengeluaran, Unduh CSV, Periksa nota.
- R-16 PASS: copy tanpa istilah pemasaran AI.
- R-20 PASS: tema existing dan perilaku nota/HPP khusus aplikasi dipertahankan.
- R-21 PASS: terang dan gelap tersedia, tidak memaksa tema baru.
- R-29 PASS: neutral/brand dan danger mengikuti palet existing.
- R-30 PASS: tidak meniru produk luar.
- R-31 PASS: keputusan utama punya alasan yang tertulis.

## Deployment

Sudah dipasang 6 Oktober 2026 sekitar 06:46 UTC. Lima file backend lama
dicadangkan di `/tmp/selaris-finance-backup`; enam file runtime, termasuk
finance_context baru, disalin ke container existing lalu restart saat pending
HPP nol. Semua hash source dan runtime cocok. Image backend tetap
`160766c62c58c2be22ea7893461d77951b46d70289904fd1e4920ad9ac5fd31a`.

Frontend standalone dibangun dan diuji di container QA sebelum hanya frontend
dibuat ulang dengan image
`92c5b913ad32cdc7e6c5605c580ba0a8316abe102b5cf4ca5e7f2d339db691f2`.
Backend/frontend/db/redis healthy; health db dan background tasks sehat,
frontend HTTP200. Tidak recreate backend, tidak migrasi database, tidak
mencatat biaya atau pembayaran merchant untuk pengujian, tidak push main
atau merilis APK. Source masih uncommitted bersama pekerjaan native sebelumnya.

Log produksi `/tmp/selaris-finance-frontend-build.log`,
`/tmp/selaris-finance-browser-production.log` dan
`/tmp/selaris-finance-live-check.log`, serta browser live
`/tmp/selaris-finance-live-browser.log`. Form Keuangan tetap jalur pencatatan;
chat mendapat konteks baca terbaru, bukan kemampuan menyimpan atau reminder baru.
