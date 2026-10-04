# Bahan Baku web, 4 Oktober 2026

Ivan meminta halaman Bahan Baku lebih mudah dipakai setelah alur Atur HPP
dirapikan. Halaman lama mencampur stok, harga, biaya operasional dan status resep.
Tambah bahan dimulai dengan preset; harga satuan kecil dibulatkan menjadi nol dan
stok yang belum dicatat bisa disalahartikan sebagai stok habis.

Design Read sebelum edit: stok menjadi informasi utama, tindakan Tambah stok,
Ubah harga dan Lihat pemakaian dipisahkan. Biaya operasional mendapat bagian
sendiri. Source Sans 3 serta warm neutral, charcoal dan coral Sefrekuensi
dipertahankan. ENERGY 2 / RHYTHM 2 / MOTION 1; antislop during mengikuti pilihan
pengguna untuk sesi ini. Daftar tiga kolom desktop menjadi dua kolom informasi
di HP lebar dan satu kolom pada 320 px. Form mengikuti isi, tanpa ilustrasi atau
animasi dekoratif.

## Perilaku

- Tambah bahan langsung membuka form kosong: nama, total harga pembelian,
  jumlah dan satuan. Harga nol boleh diisi secara eksplisit; harga kosong,
  jumlah nol/negatif, angka tidak finite dan nama duplikat ditolak.
- Pembelian kg/liter untuk bahan baru disimpan dalam gram/ml. Edit bahan existing
  mempertahankan base_unit dan unit_type; input pembelian dikonversi ke satuan
  existing sebelum PUT. Harga membawa row_version untuk konflik perubahan.
- Simpan bahan hanya satu write. Stok dicatat melalui tindakan terpisah sesudah
  bahan dibuat. Restok menjelaskan jumlah **tambahan**, konversi dan stok sesudah
  penambahan, dengan catatan opsional. Klik berulang dikunci selama request.
- Nilai current_stock null/undefined disebut Belum dicatat, nol disebut Stok
  habis, dan stock <= min_stock disebut Stok menipis. Batas minimum existing
  dipertahankan. List memakai cost_per_base_unit server dengan desimal; harga
  pembelian terakhir ditampilkan terpisah karena biaya rata-rata server dapat
  berbeda. Preview perubahan harga menjelaskan biaya HPP setelah simpan.
- Response edit harga tidak membawa stok outlet atau pemakaian resep. UI menjaga
  nilai yang sudah dimuat agar edit harga tidak membuat stok tampak hilang.
- Pencarian dan filter memakai data aktual: stok rendah, belum dicatat, harga
  perlu diperiksa dan belum dipakai. Seluruh halaman API dimuat, bukan hanya 100
  bahan pertama. Angka jumlah bahan berasal dari hasil API.
- Pemakaian menampilkan produk dan takaran dari used_in. Penghapusan bahan yang
  masih dipakai dihentikan dengan petunjuk melepasnya di Atur HPP. Penghapusan
  bahan tidak terpakai memerlukan klik konfirmasi di dialog.
- Biaya operasional hanya mencatat nama dan estimasi harian; tanpa restok atau
  field pembelian. Copy menyatakan biaya ini belum termasuk HPP bahan per porsi.
- Loading, daftar kosong, pencarian kosong, gagal load/retry, sesi habis dan
  validasi save terlihat. Draft dipertahankan saat 400/422/409. Hasil 500/network
  yang tidak pasti meminta Periksa data terbaru, tanpa mengulang write otomatis.
  Menutup hasil tidak pasti juga memuat ulang sebelum form bisa dibuka lagi.
- Dialog native mengunci fokus, mendukung Escape, mengembalikan fokus dan
  menggulir pada viewport pendek. Draft yang berubah mendapat konfirmasi sebelum
  dibuang. Kontrol dinonaktifkan selama save, tanpa mengubah stok melalui harga.

Backend, perhitungan HPP/stock deduction, optimistic versions, audit/event CRDT,
tier Pro, aktivasi mode, APK dan data merchant tidak diubah oleh redesign ini.
Data uji browser hanya fixture terisolasi. Tidak membuat harga atau stok toko
agar halaman demo tampak terisi.

## Verifikasi

- Production Docker build Next.js dan TypeScript lolos. Warning existing Sentry,
  OpenTelemetry dan Browserslist tetap non-blocking.
- `tests/ingredient-inventory-browser.cjs`: 104 bahan awal dengan pagination,
  stok null/nol/positif, biaya desimal dan biaya rata-rata berbeda dari pembelian,
  search/filter/reset, pemakaian, guard delete, form kosong/duplikasi/validasi,
  create kg/gram dan liter/ml, harga nol eksplisit, stock write terpisah,
  projected stock, catatan, double click, edit base unit existing dan row_version,
  preserved stock/minimum/usage, 400/422 retry, 409 refresh, 500 setelah simulated
  commit tanpa duplicate, browser transport abort pada save/load dan retry,
  sesi 401, overhead create/edit/delete, empty dan Pro gate. Seluruh writes fixture.
- List, tambah bahan, harga, restok dan overhead diperiksa 320/390/768/1024/1440
  dalam kedua tema: teks/placeholder AA, kontrol 44 px, tanpa horizontal overflow.
  Tab berulang/Shift+Tab tetap di dialog, ring terlihat, Escape dan return focus
  lolos. Draft cancel/confirm, return focus sesudah reconcile, teks 200% dan
  focused field pada 320×420 diperiksa. Screenshot list/form/restock diperiksa.
- `tests/hpp-units.cjs` lolos dengan helper Python backend sebagai oracle untuk
  konversi dua arah, alias, invalid quantity dan cross-family rejection.
- Regresi `hpp-browser.cjs`, `auth-browser.cjs` dan
  `stock-storefront-browser.cjs` lolos pada image final: Menu recipe, entry links,
  canonical recipe quantities, login/onboarding/dashboard, theme persistence,
  guard stock mode serta fase storefront/cart/booking/COD.
- Smoke demo aktual preview: Bahan Baku pada 320/768/1440 kedua tema, tanpa alert,
  page error atau overflow. Form bahan dan biaya benar-benar kosong, cancel/Escape
  bekerja, link Atur HPP terbuka. Demo aktual 0 bahan; state terisi diuji pada
  fixture, tanpa menambahkan bahan agar demo terlihat terisi.
- Checker antislop-human: control-border terhadap surface 3.81:1 light dan
  4.34:1 dark; focus ring 6.37:1 dan 12.85:1; teks tombol utama 6.97:1 dan
  13.10:1. Teks browser diperiksa minimum 4.5:1, termasuk placeholder.
- Log dan screenshot QA `/tmp/selaris-inventory-*`; bukan aset/konten toko.
- Image final `sha256:c7b54e58aa043ab5633b1c6b7d183de764cdcc8e2a0f5f8b250b166c53daec9c`.
- Source `6d91aac` dipush main dan dipasang frontend-only ke selaris.id. Image
  aktif sama dengan image final yang diuji; frontend/backend/Postgres/Redis healthy.
- Smoke HTTPS inventory tiga lebar kedua tema, HPP aktual 13 produk × tiga lebar
  × dua tema dan storefront aktual menu/cart kedua tema 320 px lolos. Form kosong
  dan dapat dibatalkan, tanpa write bahan/resep/stok/mode atau submit pesanan.

## Delivery gate antislop

Gate untuk halaman Bahan Baku, form, dialog, actions dan CSS yang disentuh.

- R-01 PASS: panel datar dan border; tidak menambah gradient.
- R-02 PASS: copy baru berupa kalimat biasa tanpa em dash.
- R-03 PASS: lima lebar kedua tema, overflow dan target sentuh diuji.
- R-04 PASS: tidak menambah ikon dekoratif; navigasi existing dipertahankan.
- R-05 PASS: daftar stok dan form pembelian mengikuti pekerjaan merchant.
- R-06 PASS: Source Sans 3 existing untuk form dan angka; tanpa font monospace baru.
- R-07 PASS: tidak menambah pola latar grid/dot.
- R-08 PASS: tombol menyebut tindakan tanpa panah dekoratif.
- R-09 PASS: status stok/harga berupa teks; tanpa badge promosi baru.
- R-10 PASS: dialog memakai scrim untuk fokus tugas, tanpa glassmorphism/blur.
- R-11 PASS: radius kontrol 12 px dan list/dialog 16 px; tanpa capsule berulang.
- R-12 PASS: list memakai pembatas baris, tanpa shadow pada tiap bahan.
- R-13 PASS: tidak menambah glow.
- R-14 PASS: stok/biaya/pemakaian diatur menurut isi, tanpa bento dekoratif.
- R-15 PASS: CTA Tambah bahan, Tambah stok, Ubah harga, Lihat pemakaian dan Simpan.
- R-16 PASS: bahasa pengelolaan bahan, tanpa buzzword pemasaran.
- R-17 PASS: harga, stok dan counts dari API; tidak ada angka pencapaian buatan.
- R-18 PASS: tidak menambah avatar atau testimoni pelanggan.
- R-19 PASS: MOTION 1; tanpa animasi dekoratif baru.
- R-20 PASS: jumlah pembelian, stok tambahan, harga HPP dan pemakaian spesifik tugas.
- R-21 PASS: terang tetap default; gelap mengikuti pilihan pengguna.
- R-22 PASS: tidak menambah foto atau ilustrasi buatan.
- R-23 PASS: identitas Selaris/Sefrekuensi dipertahankan pada halaman yang diminta.
- R-24 PASS: entry Atur HPP dan form/usage links bekerja dalam browser.
- R-25 PASS: teks dan placeholder AA; border/focus di atas 3:1 pada kedua tema.
- R-26 PASS: search, filter, reset, create, price, restock, usage dan delete diuji.
- R-27 PASS: loading/empty/load error/retry, save validation/conflict/uncertain/session diuji.
- R-28 PASS: bantuan lokal pembelian/stok/biaya; tidak menambah FAQ generik.
- R-29 PASS: warm neutral/coral/charcoal existing; informasi status tidak bergantung warna.
- R-30 PASS: arah Sefrekuensi yang diminta; tidak meniru landing SaaS lain.
- R-31 PASS: font untuk angka/form, border untuk kontrol dan gap untuk tugas.
- R-32 PASS: label eksplisit, Tab/Shift+Tab/Escape, ring dan return focus diuji.
- R-33 PASS: source, CSS, tes dan dokumentasi diubah dengan apply_patch.
- R-34 PASS: kedua tema diuji; screenshot list/form/restock/aktual diperiksa.
- R-35 PASS: production build, unit oracle, click-through dan demo read smoke lolos.
- R-36 PASS: tidak mengklaim laba bersih atau alokasi otomatis biaya operasional.
- R-37 PASS: Design Read dan ENERGY 2 / RHYTHM 2 / MOTION 1 sebelum edit.
- R-38 PASS: harga/jumlah/stok baru tidak ditebak; input nyata kosong, fixture hanya QA.
- Dials PASS: ENERGY 2 / RHYTHM 2 / MOTION 1 diterapkan.
- Focal point PASS: stok tersedia menjadi angka utama; harga dan pembelian dibedakan.
- Whitespace PASS: pembatas memisahkan bahan, gap memisahkan tugas dan field.
- Accent PASS: coral untuk tindakan utama, selebihnya token existing.
- Identity PASS: palet Sefrekuensi dan Source Sans 3 existing dipertahankan.
- Design Read PASS: alasan alur/font/warna/komposisi diberikan sebelum implementasi.
- C-1 PASS: keputusan mengikuti kebingungan stok, harga dan HPP yang dilaporkan.
- C-2 PASS: setiap kontrol mempunyai handler/API/route nyata yang diuji.
- C-3 PASS: setiap bagian melayani bahan, stok, harga, pemakaian atau biaya harian.
- C-4 PASS: tema, viewport, keyboard, draft, load/save errors dan retry diuji.
- C-5 PASS: produksi hanya dibaca; fixture tidak dijadikan data toko.
- Human contrast PASS: teks/placeholder AA, kontrol/fokus 3:1, kedua tema.
- Human keyboard PASS: Tab berulang/Shift+Tab, Escape, draft guard dan return focus.
- Human states PASS: errors/status berbentuk teks; input dipertahankan pada failure.
- Human resize PASS: teks 200% dan viewport pendek tanpa clipping input fokus.
- Mobile reflow PASS: satu kolom 320 px, dua kolom metadata mulai 390, tiga desktop.
- Mobile scale PASS: padding 16 px HP/24 px desktop, kontrol minimum 44 px.
- Mobile overflow PASS: lima lebar list/form/restock/overhead tanpa overflow.
- Mobile touch PASS: semua tindakan minimal 44 px dan tidak bergantung hover.
- Mobile navigation PASS: regresi shell/menu, Escape dan focus return lolos.
- Copy PASS: harga pembelian, stok tambahan dan HPP per porsi dijelaskan terpisah.
