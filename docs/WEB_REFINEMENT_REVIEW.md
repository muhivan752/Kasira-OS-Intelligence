# Selaris web refinement, 4 Oktober 2026

Design Read sebelum implementasi: pemilik meminta web lebih rapi, profesional dan premium, dengan tipografi dan copy yang tidak terasa seperti template AI. Warna hangat/coral Sefrekuensi tetap menjadi acuan. Antislop `during` adalah pilihan pengguna untuk sesi ini. ENERGY 2 / RHYTHM 2 / MOTION 1.

Source Sans 3 dipakai untuk teks, angka, form dan navigasi: bentuk humanis dan proporsinya menjaga keterbacaan pada dashboard padat. Source Serif 4 pada judul publik/auth memberi karakter yang lebih tenang tanpa menebalkan semua judul. Space Mono hanya untuk kode OTP. Merchant heading tetap sans dengan bobot 600. Radius membedakan kontrol, panel, dan dialog; pemisah garis menggantikan kartu dekoratif.

Perubahan meliputi fondasi tipografi seluruh web, landing, auth/onboarding, dashboard utama dan shell merchant, storefront, download, navigasi/footer publik, halaman informasi dan chat bantuan. Alur usaha yang sudah ada memakai fondasi baru; bukan penggantian backend atau aplikasi Android. APK tetap 1.6.31+198. Google tetap menunggu konfigurasi pemilik, sesuai pesan nonaktif yang diuji.

Kalimat yang ditolak pengguna dihapus. Copy pembelian sekarang: **“Unggah nota, periksa hasilnya, lalu simpan pembelian.”** Contoh nota/angka pemasaran buatan, badge “paling lengkap”, bingkai browser palsu, janji backup dan klaim QRIS tanpa biaya dihapus dari landing. Harga mengikuti `backend/api/routes/billing.py`; FAQ membedakan komisi Selaris dari biaya penyedia pembayaran.

Audit kontras juga menemukan benturan Tailwind: `--color-base` menghasilkan aturan warna `.text-base` yang memakai warna latar, padahal nama kelas itu lazim dipakai untuk ukuran font. Token diganti menjadi `--color-canvas`; penggunaan ukuran `text-base` kembali mewarisi tinta yang tepat. Regresi halaman agen memeriksa pasangan ini dalam kedua tema.

Screenshot baru pada `public/app/web-*.png` diambil dari preview produksi memakai akun/toko demo existing, bukan mockup. Label data demo ditampilkan. Keranjang screenshot hanya disimpan di browser; tidak mengirim pesanan. Screenshot dashboard lama dan APK dengan palet lama tidak lagi ditampilkan pada landing.

## Bukti pemeriksaan

- Production Docker build Next.js dan TypeScript. Peringatan lama Sentry/OpenTelemetry dan usia data Browserslist tidak memblokir build.
- `tests/web-refinement-browser.cjs`: 320/390/768/1024/1440, kedua tema, overflow, seluruh pasangan teks HTML publik terhadap AA, font yang benar, aset benar-benar terunduh, target anchor, menu/Escape/fokus, FAQ Enter, download/register, tema tersimpan, chat gagal/retry melalui mock.
- `tests/auth-browser.cjs`: validasi nomor, Sef tidak ditemukan, fallback WA, OTP salah/benar, PIN, referral, onboarding gagal/retry/skip/back; tema dan menu. Tambahan: laporan dashboard gagal lalu retry, angka laporan/top product dari fixture API, grafik dan tabel tujuh hari.
- `tests/stock-storefront-browser.cjs`: stok 400/422/500/401, retry, pindah dua arah, mode tetap ketika ditolak; storefront terang/gelap 320/768/1440, jumlah produk/varian/Escape, keranjang/meja/fokus, tujuh status order, tiga status reservasi, booking dan COD/failure. Fixture tidak mengirim OTP/WA atau pesanan nyata.
- Pemeriksaan visual screenshot desktop/HP kedua tema, dashboard demo, menu dan keranjang. Preview membaca data demo existing untuk dashboard/pembelian/keuangan tanpa page error atau overflow.
- Smoke data aktual: 16 route dashboard/menu/toko/kasir/pelanggan/pembelian/keuangan/promo/laporan/bahan-baku/reservasi/AI/settings/onboarding/jelajah/storefront pada 320 dan 1440 px, kedua tema. Total 64 pembukaan route, HTTP 200, tema tersimpan dan tidak ada document overflow/page error. CTA demo membuka storefront sungguhan dan keranjang lokal tanpa submit order.
- Image final yang diuji: `sha256:f2d69d2af62a12014564b871e16fc0a21c33eaa05a70b53db98fadc26c6e7b28`.
- Deploy frontend selesai pada source `2ca827f`. Image container produksi cocok dengan image final; backend/frontend/Postgres/Redis healthy. Pemeriksaan HTTPS mengulang tes publik (termasuk direktori toko aktual), auth/dashboard/onboarding demo dan storefront/menu/keranjang kedua tema, seluruhnya lolos tanpa page error atau submit transaksi/pesan nyata.

## Delivery gate antislop

Status berikut berlaku untuk perubahan dan permukaan yang diperiksa pada revisi ini. Alur pembayaran/provider produksi yang membutuhkan konfigurasi pemilik tidak diaktifkan oleh tes.

- R-02 PASS: copy baru memakai kalimat biasa; tidak ada em dash pada teks UI yang ditulis ulang.
- R-03 PASS: browser memeriksa overflow publik pada lima lebar dan storefront pada tiga lebar; kontrol jumlah tetap di dalam produk.
- R-17 PASS: angka ringkasan berasal dari API; harga dari billing; screenshot berlabel toko demo; contoh nota buatan dihapus.
- R-18 PASS: tidak menampilkan testimoni, avatar pelanggan atau nama fiktif pemasaran.
- R-23 PASS: logo mempertahankan geometri resmi; foto produk milik toko demo existing; screenshot baru merupakan capture produk nyata dalam scope redesign yang diizinkan pengguna.
- R-24 PASS: setiap anchor navigasi diperiksa terhadap ID section; route publik/register/download sudah dibuka melalui browser.
- R-25 PASS: tes publik menghitung AA untuk teks HTML yang tampak dalam kedua tema; tes auth/storefront menghitung pasangan kontrol aktif termasuk input fokus/status. Form/pencarian memakai control-border; tombol jumlah minimal 44 px.
- R-26 PASS: CTA menuju register, demo, download, dashboard atau tautan bantuan existing; menu, FAQ dan chat benar-benar berfungsi; Google nonaktif disertai penjelasan.
- R-27 PASS: dashboard memiliki loading/empty/error/retry; chat loading/error/retry; regresi auth dan stok mencakup keadaan gagal.
- R-28 PASS: FAQ membahas setup usaha, trial, stok sederhana/HPP, QRIS dan kasir offline berdasarkan fungsi produk.
- R-32 PASS: outline fokus 3 px; menu publik Escape mengembalikan fokus; FAQ memakai details/summary; sheet memerangkap Tab, menutup lewat Escape dan memulihkan fokus; grafik memiliki tabel harian.
- R-33 PASS: perubahan source/CSS ditulis memakai apply_patch; script luar hanya browser fixture, screenshot atau pemeriksaan.
- R-34 PASS: kedua tema diuji; tema bertahan setelah reload; screenshot gambar merupakan capture produk, bukan surface form.
- R-35 PASS: production build dan click-through direkam oleh tiga tes browser; screenshot hasil diperiksa langsung.
- R-36 PASS: copy baru tidak menambah janji security/performance/customer; landing menghapus klaim backup dan biaya QRIS nol yang terlalu mutlak.
- R-37 PASS: Design Read dan dials diumumkan sebelum edit, berdasarkan arahan langsung pemilik.
- R-38 PASS: fitur mengacu source existing, harga billing, dan capture data demo; tidak membuat contoh stok/HPP/transaksi pemasaran.
- R-01 PASS: surface dan tombol datar; gradient kompatibilitas logo hanya memakai warna sama, tidak ada glow dekoratif.
- R-04 PASS: ikon baru menunjukkan menu/tutup, pilihan tema, buka FAQ, kirim pesan dan WhatsApp; robot/crown/star dekoratif pada shell dashboard dihapus.
- R-06 PASS: alasan Source Sans/Serif tertulis di Design Read; monospace terbatas kode; eyebrow bukan kapital dengan tracking lebar.
- R-07 PASS: tidak menambah grid/dot/pola latar.
- R-08 PASS: CTA baru berupa label tindakan tanpa panah dekoratif berulang.
- R-09 PASS: badge pemasaran dihapus; label Pro dan status toko menunjukkan keadaan produk nyata.
- R-10 PASS: header publik memakai latar solid; blur existing terbatas layer sticky storefront dan backdrop dialog.
- R-12 PASS: panel laporan/fitur mengandalkan garis; shadow baru hanya chat yang muncul di atas halaman, untuk membedakan layer.
- R-13 PASS: token glow tetap none; tidak ada glow baru.
- R-14 PASS: fitur berbentuk daftar; pendapatan menjadi fokus terpisah dari tiga angka operasional; pricing mempunyai dua paket nyata.
- R-19 PASS: gerak hanya feedback kontrol, disclosure dan loading; reduced-motion existing tetap berlaku.
- R-22 PASS: screenshot produk nyata menggantikan ilustrasi/mockup dekoratif.
- Liveliness PASS: ENERGY 2 / RHYTHM 2 / MOTION 1; warna tenang dengan perbedaan komposisi menurut isi.
- Focal point PASS: judul publik dan capture dashboard, langkah auth, pendapatan dashboard dan daftar produk storefront memandu tugas layar masing-masing.
- Whitespace PASS: gap memisahkan penjelasan/capture, daftar modul dan paket; HP memakai susunan sendiri dengan padding lebih kecil.
- Accent PASS: coral untuk aksi/tautan; status mempunyai warna semantik dan tema gelap memakai pasangan tinta terang.
- Identity PASS: tipografi serif judul, warm neutral, garis pemisah dan mark Selaris berulang secara konsisten.
- Design Read PASS: arah premium/formal merchant dengan warna Sefrekuensi dicatat sebelum implementasi.
- C-1 PASS: alasan font, warna, panel dan radius dijelaskan di awal dokumen.
- C-2 PASS: navigasi, bantuan, FAQ dan form diuji melalui handler/link sebenarnya; chat network dimock untuk tes.
- C-3 PASS: section memperlihatkan produk, pembelian, toko online, fungsi dan paket; tidak ada filler testimoni/angka perusahaan.
- C-4 PASS: theme/breakpoint, fokus, error/retry auth, laporan dan stok serta status transaksi tercakup tes browser.
- C-5 PASS: angka nyata atau data demo berlabel; tidak ada klaim/testimoni baru yang direkayasa.
- R-05 PASS: komposisi mengikuti kebutuhan pemilik: preview produk, pembelian, menu pelanggan, daftar fungsi, paket dan FAQ; tidak memakai tiga kartu langkah atau bento palsu.
- R-11 PASS: kontrol 8–12 px, panel 16–20 px, dialog 28 px; capsule hanya untuk status kecil yang berfungsi.
- R-15 PASS: CTA menyebut aksi seperti Daftarkan usaha, Unduh APK POS dan Buka menu toko demo.
- R-16 PASS: copy baru menerangkan fungsi dengan bahasa biasa tanpa buzzword pemasaran AI.
- R-20 PASS: nota belanja, resep/HPP, supplier, OTP Sefrekuensi dan kasir/toko online adalah konteks spesifik Selaris.
- R-21 PASS: terang tetap default; tema gelap dipilih pengguna dan disimpan.
- R-29 PASS: warm neutral/coral/charcoal dengan status semantik; hijau WhatsApp mengidentifikasi kanal komunikasi.
- R-30 PASS: identitas mengikuti palet Sefrekuensi yang diminta dengan tipografi baru; bukan clone produk SaaS lain.
- R-31 PASS: font untuk keterbacaan/karakter, garis untuk data, spacing untuk urutan tugas, radius untuk layer dan ukuran kontrol untuk sentuh.
