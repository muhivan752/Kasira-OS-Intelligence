# Alur HPP web, 4 Oktober 2026

Ivan kesulitan mengisi HPP di web dashboard. Alur sebelumnya menuntut berpindah
dari Bahan Baku ke edit produk, tab Resep, lalu Pengaturan. Harga pembelian,
takaran resep dan stok fisik kurang dibedakan. Preview lama juga menjumlah bahan
opsional dan memakai quantity mentah tanpa aturan satuan backend.

Design Read sebelum edit: satu produk dan satu porsi menjadi dasar form. Harga
pembelian bahan diterangkan sebagai dasar biaya, sedangkan stok fisik mempunyai
tindakan terpisah. Total menjadi fokus setelah bahan diisi. Source Sans 3,
warm neutral, charcoal dan coral Sefrekuensi dipertahankan. ENERGY 2 / RHYTHM 2 /
MOTION 1; antislop during adalah pilihan sesi pengguna. Panel resep mengikuti
panjang isi, ringkasan terpisah di desktop, baris input dua kolom di tablet dan
susunan satu kolom di HP. Tidak ada animasi atau ilustrasi dekoratif baru.

## Perubahan

- Halaman `/dashboard/hpp`, nav Atur HPP dan pintu masuk dari Menu, Bahan Baku,
  Pengaturan serta Laporan HPP. Tautan `?product=...` membuka produk langsung.
- Pilih bahan existing atau buat bahan di tempat dengan harga dan jumlah
  pembelian nyata. Nama preset di Bahan Baku tidak lagi mengisi perkiraan harga
  atau jumlah pembelian sebagai data yang siap disimpan.
- Setiap baris menjelaskan harga pembelian dan takaran untuk satu porsi.
  Gram/ml lebih mudah diisi; quantity yang disimpan memakai base_unit bahan,
  tanpa mengubah base_unit ingredient existing. Konversi tidak mengubah stok fisik.
- Preview mengikuti HPP server, melewati bahan opsional, dan menjelaskan bahwa
  biaya operasional belum masuk. Sesudah simpan total server ditampilkan dan harga
  bahan dimuat ulang. Jika refresh gagal, simpan tetap dinyatakan sukses dengan
  petunjuk memuat ulang rincian.
- Resep lama dengan satuan berbeda perlu konfirmasi. Flag optional dan catatan
  resep/bahan dipertahankan. Edit harga menjaga row_version dan tidak mengubah
  satuan stok. Harga bahan berlaku pada semua resep yang menggunakannya.
- Error API menjadi hasil Server Action yang aman dibaca dalam production:
  validasi ditampilkan, error 500 tidak dibocorkan, draft tetap bisa dicoba lagi.
  Peralihan produk menanyakan apakah perubahan yang belum disimpan dibuang.
- Menyimpan resep tidak mengaktifkan mode stok. Petunjuk Settings diperbaiki
  agar bahan/resep disiapkan sebelum peralihan. Backend tetap memvalidasi tier,
  resep dan persyaratan mode. Restok bahan adalah tindakan terpisah.
- Pesan stok awal pada form Bahan Baku tidak lagi mengaku sukses bila restok gagal.

## Verifikasi

- Production Docker build Next.js serta TypeScript tanpa error. Warning lama
  Sentry/OpenTelemetry dan Browserslist tetap non-blocking.
- `tests/hpp-units.cjs`: konversi dua arah kg/gram dan liter/ml, alias satuan,
  quantity tidak valid, cross-family mismatch dan preview legacy dibandingkan
  langsung dengan helper Python backend, bukan kalkulator fixture.
- `tests/hpp-browser.cjs`: API fixture terisolasi, bahan existing/baru, harga
  kosong, duplikasi, paginasi bahan melewati 100 item, harga 409, validasi 400/422,
  error 500 aman, retry, 401, simpan/buka ulang, optional, catatan, konfirmasi
  satuan lama, quantity canonical, total server, gagal refresh setelah simpan,
  guard draft, produk berikutnya, editor Menu, entry links dan gate Pro.
- Tes HPP memeriksa AA teks, kontrol 44 px, fokus dan Escape, 320/390/768/1024/1440
  px kedua tema, pembesaran teks 200%, serta field aktif pada viewport 320×420
  untuk simulasi ruang layar yang berkurang saat keyboard terbuka.
- Regresi `auth-browser.cjs`, `stock-storefront-browser.cjs` dan
  `web-refinement-browser.cjs` lolos pada image final. Mode tetap ketika API
  menolak; auth/onboarding/dashboard serta seluruh fase storefront tetap berjalan.
- Smoke baca data demo aktual: 13 produk pada 320/768/1440, terang/gelap, tanpa
  error halaman/overflow; form bahan baru kosong dan bisa dibatalkan; link
  Pengaturan ke HPP berjalan. Tidak menyimpan bahan/resep/stok/mode di toko aktual.
- Screenshot fixture dan data aktual diperiksa di `/tmp/selaris-hpp-*.png`.
  Log build/tes di `/tmp/selaris-hpp-*.log`. Screenshot fixture hanya bukti QA,
  tidak dijadikan data toko, foto produk atau konten pemasaran.
- Batas kontrol light/dark memenuhi 3:1; ring fokus light/dark memenuhi 3:1.
  Teks tombol utama memakai brand-on-fill terhadap brand-fill, memenuhi 4.5:1.
- Image final: `sha256:73c25119aa34589be27584400504aed915ffc071792bf35690108a016d3fa0f6`.
- Source `4f7934c` dipasang ke selaris.id; frontend aktif memakai image yang sama
  dengan preview final. Frontend/backend/Postgres/Redis healthy. Smoke HTTPS HPP
  13 produk × tiga lebar × dua tema dan storefront aktual menu/cart kedua tema
  pada 320 px lolos. Tidak menulis bahan/resep/stok/mode atau submit pesanan nyata.

## Delivery gate antislop

Gate berlaku untuk perubahan HPP dan pintu masuk yang disentuh. API writes diuji
di fixture terisolasi; produksi hanya dibaca. APK tetap 1.6.31+198.

- R-02 PASS: copy form baru berupa kalimat biasa, tanpa em dash.
- R-03 PASS: lima lebar, kedua tema, overflow dan target sentuh diperiksa browser.
- R-17 PASS: jumlah produk, harga dan biaya berasal dari API; tanpa angka pemasaran.
- R-18 PASS: tidak ada testimoni atau avatar pelanggan baru.
- R-23 PASS: nav HPP merupakan bagian alur yang diminta; identitas/aset existing dipertahankan.
- R-24 PASS: entry Menu/Bahan Baku/Settings/Laporan dan tautan editor menuju route yang diuji.
- R-25 PASS: teks baru AA pada kedua tema; control-border dan ring dihitung terhadap surface.
- R-26 PASS: tambah/hapus bahan, harga, takaran, optional, simpan, lanjut, cancel dan tautan bekerja.
- R-27 PASS: loading, tanpa produk/resep, gagal load/retry, gagal save/retry dan sesi habis diuji.
- R-28 PASS: tidak menambah FAQ generik; bantuan lokal menjelaskan purchase/takaran/stok.
- R-32 PASS: label input, fokus tampak, Escape cancel dan pemulihan fokus diuji; confirm draft native.
- R-33 PASS: seluruh perubahan source/CSS memakai apply_patch, bukan script pengganti source.
- R-34 PASS: HPP kedua tema diuji dan screenshot diperiksa; regresi theme persistence lolos.
- R-35 PASS: production build, unit/backend oracle, browser click-through dan smoke aktual lolos.
- R-36 PASS: tidak ada klaim security/performance baru; biaya operasional disebut belum termasuk.
- R-37 PASS: Design Read dan dials diumumkan sebelum edit berdasarkan feedback pengguna.
- R-38 PASS: tanpa harga, resep atau stok buatan dalam produk; preset tidak mengisi harga perkiraan.
- R-01 PASS: panel dan tombol datar; tidak menambah gradient atau glow.
- R-04 PASS: Calculator nav mengidentifikasi kalkulasi HPP; tidak ada ikon dekoratif baru.
- R-06 PASS: Source Sans 3 existing menjaga keterbacaan angka/form, tanpa monospace dekoratif.
- R-07 PASS: tanpa pola grid/dot latar.
- R-08 PASS: label tindakan tanpa panah dekoratif berulang.
- R-09 PASS: status resep berupa teks di pilihan produk, tanpa badge promosi.
- R-10 PASS: tidak menambah glassmorphism atau backdrop baru.
- R-12 PASS: panel HPP memakai border; tidak menambah shadow pada tiap elemen.
- R-13 PASS: tidak menambah glow.
- R-14 PASS: form mengikuti isi resep; ringkasan biaya mempunyai hierarki tersendiri.
- R-19 PASS: MOTION 1; hanya feedback kontrol/loading existing, tanpa animasi baru.
- R-22 PASS: tidak ada ilustrasi generik atau foto buatan.
- Dials PASS: ENERGY 2 / RHYTHM 2 / MOTION 1 dinyatakan dan diterapkan.
- Focal point PASS: pilihan produk, takaran satu porsi dan HPP menjadi urutan perhatian.
- Whitespace PASS: gap memisahkan tugas; panel kosong tidak ditarik mengikuti tinggi ringkasan.
- Accent PASS: coral untuk tindakan utama, warna semantik untuk pesan dengan teks.
- Identity PASS: warm neutral/charcoal Sefrekuensi dan tipografi web Selaris dipertahankan.
- Design Read PASS: alasan komposisi, warna, font dan alur tertulis sebelum implementasi.
- C-1 PASS: semua keputusan baru mempunyai alasan tugas pada Design Read.
- C-2 PASS: kontrol form dan tautan memakai handler/API/route nyata yang diuji.
- C-3 PASS: setiap section melayani pilihan produk, harga bahan, resep atau biaya.
- C-4 PASS: kedua tema, breakpoint, keyboard, draft, gagal save/load dan retry diuji.
- C-5 PASS: data toko dari API; fixture hanya QA terisolasi dan tidak dipasang sebagai data.
- R-05 PASS: komposisi form/ringkasan mengikuti input resep; bukan hero/bento atau tiga kartu langkah.
- R-11 PASS: radius kontrol 12 px, panel 20 px; tanpa capsule untuk semua komponen.
- R-15 PASS: CTA menyebut tindakan: simpan resep/HPP, buat bahan, ubah harga, atur produk lain.
- R-16 PASS: bahasa merchant biasa tanpa buzzword pemasaran.
- R-20 PASS: pembelian bahan, takaran, resep, stok dan mode HPP spesifik tugas pemilik Selaris.
- R-21 PASS: terang tetap default, gelap tersedia dan mengikuti pilihan pengguna.
- R-29 PASS: palet existing warm neutral/coral/charcoal, status memakai token semantik.
- R-30 PASS: arah mengikuti Sefrekuensi yang diminta, tanpa meniru layout SaaS lain.
- R-31 PASS: font untuk angka/form, border untuk kontrol, gap untuk urutan dan panel untuk ringkasan.
- Human contrast PASS: browser menghitung teks AA; batas kontrol dan ring memenuhi 3:1.
- Human keyboard PASS: label/fokus/Escape, form cancel dan langkah berikutnya diuji.
- Human states PASS: status dan kegagalan berupa teks, dengan isian tetap tersedia.
- Human resize PASS: teks 200% dan fokus field pada compressed viewport diuji tanpa clipping.
- Mobile reflow PASS: satu kolom HP, input/cost dua kolom tablet, ringkasan samping desktop.
- Mobile scale PASS: panel padding 16 px di HP, 24 px mulai 640 px; kontrol tetap 44 px.
- Mobile overflow PASS: document tidak overflow pada lima lebar; field/label mengikuti lebar tersedia.
- Mobile touch PASS: ukuran kontrol minimal 44 px; tidak ada aksi baru yang bergantung hover.
- Mobile navigation PASS: shell/menu existing tetap lolos regresi Escape/fokus pada HP.
- Copy PASS: label konkret, pembelian/takaran/stok dibedakan, harga/cost tidak dipasarkan sebagai laba bersih.
