# Setup HPP lewat percakapan, 4 Oktober 2026

Ivan meminta dua mode chat untuk mengurangi pekerjaan memasukkan bahan dan resep:
Manual menggunakan data nyata, Estimasi menawarkan usulan ketika pengguna belum
tahu. Pengguna dapat bercerita panjang, mengoreksi, lalu menyetujui revisi terakhir.
Rumus harus berada di backend; jawaban model tidak menjadi hasil perhitungan.

Design Read sebelum UI: Source Sans 3 dan palet warm neutral/charcoal/coral
Sefrekuensi dipertahankan. Percakapan dan angka HPP yang perlu diperiksa menjadi
fokus. ENERGY 2 / RHYTHM 2 / MOTION 1. Halaman mengikuti tugas menyiapkan satu
resep, dengan ringkasan di samping pada desktop dan sesudah percakapan di HP.
Antislop during mengikuti pilihan sesi pengguna.

## Perilaku dan batas perhitungan

- `/dashboard/hpp/chat`, melalui Atur HPP atau Bahan Baku. Form manual existing
  tetap tersedia. Pro, tenant, pemilik percakapan dan outlet diperiksa server.
- Model mengekstrak nama, satuan, harga beli, takaran, jumlah porsi, sumber dan
  kutipan cerita. Field total dari model diabaikan. Data tidak lengkap tetap
  berupa draft; mode Manual menghentikan approval angka tebakan.
- `hpp_math.py` memakai Decimal dan helper bersama `unit_utils.py`:
  total pembelian = harga per satuan beli × jumlah beli, jika harga per satuan;
  jumlah beli = konversi fisik atau jumlah kemasan × isi yang disebutkan;
  biaya satuan = total pembelian ÷ jumlah beli dalam base_unit;
  takaran per porsi = takaran batch ÷ jumlah porsi, untuk input batch;
  HPP = jumlah takaran per porsi × biaya satuan bahan wajib.
- Harga total pembelian maksimal dua desimal; biaya satuan disimpan delapan
  desimal HALF_UP. Kontribusi tidak dibulatkan per baris; total tampilan dua
  desimal HALF_UP. Quantity diselaraskan dengan representasi Float kolom resep
  sebelum preview dihitung agar preview dan pembacaan resep memakai nilai sama.
- Kg/gram dan liter/ml memakai konversi fisik existing. Potong/papan/dus/tray
  tidak diberi isi tetap. Isi kemasan atau ukuran yang belum diketahui ditanyakan
  atau berlabel Estimasi. Berat nasi matang tidak disamakan dengan beras mentah.
- Quantity dan quantity_unit yang disimpan selalu ingredient.base_unit. Enam
  jalur stok existing tetap menggunakan raw quantity yang konsisten. Setup tidak
  memanggil restock, membuat OutletStock, atau mengganti mode stok.
- Harga bahan existing menggunakan cost_per_base_unit server, termasuk biaya
  rata-rata pembelian. Perubahan harga harus diminta pengguna dan mempunyai
  sumber nyata; ringkasan memperlihatkan biaya sebelumnya dan menu terdampak.
- Kutipan sumber harus ada persis di pesan pengguna dan memuat angka inputnya.
  Sumber takaran existing diverifikasi terhadap resep aktif. Pemeriksaan ini
  tidak menjamin model memahami setiap kalimat; manusia tetap meninjau satuan,
  harga, takaran dan jumlah porsi. Estimasi tidak menjadi harga pasar terverifikasi.
- Setelah approve, flag estimasi tetap terlihat pada resep/editor/laporan HPP.
  Bahan baru dengan harga perkiraan tetap needs_review. Produk baru disimpan
  nonaktif, harga jual diatur melalui Menu sebelum diaktifkan. Bahan opsional dan
  catatan dipertahankan. Gas, gaji dan sewa belum dialokasikan ke HPP bahan.

## Percakapan, approval dan penyimpanan

- Migration 112 menambahkan dua tabel percakapan dengan FORCE RLS, status
  estimasi resep, serta presisi biaya bahan Numeric(18,8). Riwayat dan draft
  tersimpan di Postgres. Daftar menampilkan 100 percakapan terakhir per pemilik
  dan outlet; riwayat turn tidak memakai batas lima pasangan Redis.
- Input per pesan sampai 100.000 karakter, output 8.192 token dengan satu
  perbaikan schema sampai 16.384. Tidak memakai kuota harian chat biasa. Maksimal
  dua percakapan diproses bersamaan per pengguna untuk membatasi konkurensi.
- Semua riwayat tersimpan. Jika context terlalu besar, katalog dan turn lama
  dipadatkan; cerita terbaru serta draft terstruktur terakhir, termasuk angka,
  satuan, kutipan, sumber dan catatan, dipertahankan. Validasi sumber menggunakan
  seluruh pesan yang tersimpan. Model tidak selalu menerima seluruh riwayat lama.
- POST pesan menyimpan turn/id permintaan dan membalas HTTP 202. Background task
  membuka sesi database sendiri dengan tenant context, melepas transaksi saat
  menunggu provider, lalu menyimpan draft. UI polling GET setiap 2,5 detik dan
  dapat dilanjutkan setelah reload. Teks belum terkirim disimpan lokal.
- Lease delapan menit memungkinkan retry jika worker berhenti. Retry memakai
  request UUID yang sama; UUID yang dipakai untuk isi lain ditolak. Error provider
  tidak meneruskan body internal. Draft sebelumnya tetap ada dan approval diblokir
  sampai pesan terakhir selesai.
- Approval memerlukan revisi, fingerprint, pemeriksaan manusia, dan konfirmasi
  tambahan jika mengganti resep aktif. Harga/versi/resep yang berubah menghasilkan
  preview baru dan 409, sehingga pengguna memeriksa ulang sebelum menyimpan.
- Lock sesi dan brand menserialisasi approval. Bahan baru dengan nama yang sama
  tidak digandakan oleh dua percakapan bersamaan. Klik persetujuan ulang mengembalikan
  hasil yang sudah tersimpan, bukan membuat resep atau event kedua.
- Bahan, resep, status approved, audit, event serta relasi KG contains/used_by
  disimpan dalam satu commit. Kegagalan flush membatalkan semuanya. Tidak memakai
  helper audit yang melakukan commit tersendiri. Resep lama dan barisnya soft delete;
  versi berikutnya mempertimbangkan seluruh riwayat resep produk.
- Context memakai data bahan/resep terbaru, KG scoped tenant dan pgvector scoped
  brand. Retrieval best effort dalam savepoint; kegagalan retrieval tidak merusak
  transaksi. Context cache outlet satu brand dibersihkan setelah approval.
- Flow chat umum `/ai/chat` dan APK tidak diubah. Setup web ini memakai endpoint
  tersendiri `/ai/hpp-setup`; perubahan ini tidak mengganti proposal legacy native.

## Verifikasi

- Production Next.js build dan TypeScript lolos. Warning Sentry/OpenTelemetry dan
  Browserslist existing tidak menghalangi build.
- `tests/hpp-math.py`: 15 kasus, termasuk 500 perbandingan Fraction/Decimal
  independen, presisi kecil, harga per kg, isi kemasan, batch, satuan existing,
  input invalid, total model diabaikan, verifikasi sumber dan weighted average.
  Protocol provider diperiksa untuk riwayat panjang, perbaikan schema, dan context
  lebih dari 400.000 karakter yang menjaga cerita terbaru/fakta draft.
- `tests/hpp-setup-isolated.py`: Postgres dengan role aplikasi non-superuser/RLS;
  cerita sekitar 50.000 karakter dan 12 turn, koreksi, replay, ID salah, Pro,
  owner/tenant/outlet, approval berulang/bersamaan, perubahan harga dan re-review,
  reuse nama bahan, serta kegagalan flush terakhir tanpa commit parsial. HPP resep
  tersimpan dibandingkan preview; jumlah row stok tidak berubah oleh setup.
- POS order/insufficient stock/cancel dan storefront diuji dengan resep canonical
  pada database QA. HTTP nyata Uvicorn membalas 202 sebelum fake model dilepas,
  worker dengan sesi baru menyimpan draft dan GET menampilkan hasilnya.
- Provider yang sudah dikonfigurasi diperiksa dalam proses tanpa membuka DB:
  batch beras menghasilkan HPP 1.500, estimasi ayam memiliki sumber perkiraan,
  2 papan × 10 potong dengan harga 40.000 menghasilkan 2.000 per potong, dan
  5 kg × 15.000/kg menghasilkan total beli 75.000 serta HPP 1.500 untuk 100 gram.
  Draft estimasi dapat masih memerlukan klarifikasi; tidak dipaksa ready.
- `tests/hpp-chat-browser.cjs`: manual/estimasi, cerita panjang, sumber/kutipan,
  biaya delapan desimal, resume, checkbox/revisi/koreksi belum terkirim, 409,
  500 setelah simulated commit tanpa replay, incomplete/pending/lease/retry dan
  polling otomatis GET tanpa memanggil model ulang. Seluruh write fixture lokal.
- Lima lebar 320/390/768/1024/1440 dan dua tema: AA, kontrol minimal 44 px,
  tanpa overflow. Keyboard/focus, textarea untuk cerita panjang, 200% teks dan
  viewport pendek diperiksa. Screenshot desktop terang dan HP gelap diperiksa.
- Regresi `hpp-units.cjs`, `hpp-browser.cjs`, `ingredient-inventory-browser.cjs`,
  `auth-browser.cjs` dan `stock-storefront-browser.cjs` memakai image final.
  Catatan deploy/image serta smoke HTTPS disimpan di SESSION.md.
- Log dan screenshot `/tmp/selaris-hpp-*` merupakan bukti QA, bukan konten toko.

## Delivery gate antislop

- R-01 PASS: permukaan datar dan coral untuk tindakan utama; tanpa gradient/glow baru.
- R-02 PASS: copy halaman berupa kalimat biasa, tanpa em dash.
- R-03 PASS: lima lebar dan dua tema tanpa overflow; angka/kutipan panjang membungkus.
- R-04 PASS: ikon navigasi Calculator existing relevan HPP; tanpa ikon magic/robot baru.
- R-05 PASS: percakapan dan draft mengikuti tugas resep, tanpa hero/bento/feature cards.
- R-06 PASS: Source Sans 3 untuk cerita/form/angka sesuai dashboard; tanpa monospace dekoratif.
- R-07 PASS: tanpa latar grid/dot/blueprint.
- R-08 PASS: tindakan memakai label teks, tanpa panah dekoratif berulang.
- R-09 PASS: status sumber/estimasi berupa teks bermakna, tanpa badge promosi.
- R-10 PASS: tanpa glassmorphism baru.
- R-11 PASS: panel 20 px dan kontrol 12 px mengikuti HPP existing; bukan semua capsule.
- R-12 PASS: panel dipisah border, tanpa shadow pada seluruh elemen.
- R-13 PASS: tanpa glow baru.
- R-14 PASS: hierarki cerita, ringkasan angka dan rincian bahan berbeda menurut fungsinya.
- R-15 PASS: Kirim cerita, Periksa percakapan, Approve dan simpan resep menyebut tindakan.
- R-16 PASS: bahasa kerja merchant, tanpa buzzword pemasaran.
- R-17 PASS: biaya/jumlah/sumber berasal dari draft server, tanpa angka pemasaran buatan.
- R-18 PASS: tanpa testimoni atau avatar pelanggan baru.
- R-19 PASS: MOTION 1, perubahan status/scroll terbaru untuk percakapan, tanpa animasi dekoratif.
- R-20 PASS: input batch, pembelian, harga toko dan stok terpisah spesifik tugas HPP Selaris.
- R-21 PASS: tema mengikuti preferensi dashboard; kedua tema diuji.
- R-22 PASS: tanpa ilustrasi generik atau foto buatan.
- R-23 PASS: entry dari HPP/Bahan Baku sesuai permintaan setup; identitas existing dipertahankan.
- R-24 PASS: link form HPP, resep tersimpan, Bahan Baku dan Menu menuju route existing.
- R-25 PASS: teks AA kedua tema diperiksa browser, memakai token kontras existing.
- R-26 PASS: pilihan mode/sesi, kirim, sumber/rumus, koreksi, retry, refresh dan approve bekerja.
- R-27 PASS: empty/loading/error/incomplete/pending/applied dan expired-session disediakan.
- R-28 PASS: bantuan lokal harga/takaran/approval, tanpa FAQ generik.
- R-29 PASS: warm neutral/charcoal/coral existing; status memakai teks dan token semantik.
- R-30 PASS: arah Sefrekuensi yang diminta; tanpa meniru layout SaaS lain.
- R-31 PASS: font untuk keterbacaan, ruang memisahkan cerita dari review, border untuk kontrol.
- R-32 PASS: label/radio/checkbox/details native, fokus terlihat dan keyboard diuji.
- R-33 PASS: source dan CSS diedit dengan apply_patch.
- R-34 PASS: kedua tema diuji; regresi theme persistence dashboard lolos.
- R-35 PASS: build, click-through fixture, backend QA dan provider nyata diperiksa sebelum deploy.
- R-36 PASS: tanpa klaim akurasi AI mutlak; batas HPP bahan dan sumber perkiraan terlihat.
- R-37 PASS: Design Read dan ENERGY 2 / RHYTHM 2 / MOTION 1 diumumkan sebelum UI.
- R-38 PASS: tidak mengisi stok/harga merchant dengan fixture; usulan AI berlabel estimasi.
- Liveliness dials PASS: ENERGY 2 / RHYTHM 2 / MOTION 1 dinyatakan dan diterapkan.
- Liveliness consistency PASS: hierarki input/review dengan feedback status sederhana.
- Liveliness focal point PASS: angka HPP dan rincian yang harus disetujui jelas.
- Liveliness whitespace PASS: gap dan divider memisahkan cerita, input, bahan dan approval.
- Liveliness accent PASS: coral pada tindakan utama dan kontrol terpilih.
- Liveliness identity PASS: Source Sans 3, permukaan hangat dan pembelian/takaran seperti HPP existing.
- Liveliness Design Read PASS: arah dinyatakan sebelum generasi UI.
- C-1 PASS: keputusan font/warna/komposisi mengikuti arah dan tugas pengguna.
- C-2 PASS: kontrol punya handler/endpoint nyata, diuji dengan recovery.
- C-3 PASS: setiap bagian untuk cerita, data sumber, hitungan atau approval.
- C-4 PASS: breakpoint/tema/keyboard/pending/error dan teks panjang diperiksa.
- C-5 PASS: tanpa klaim/testimoni buatan; contoh QA hanya fixture terisolasi.
