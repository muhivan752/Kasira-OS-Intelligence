# Review redesign Selaris × Sefrekuensi

Direction: onboarding merchant memakai identitas visual Sefrekuensi yang ada di server, dengan logo Selaris. ENERGY 2 / RHYTHM 2 / MOTION 1. Warm white `#F7F5F2`, coral `#E5A08C`, charcoal `#121212`, Plus Jakarta Sans; Space Mono hanya untuk kode. Rujukan utama: Sefrekuensi `DESIGN.md` September 2026 dan theme native terkini.

Scope: web login, daftar, onboarding, tema shell dashboard, serta onboarding/login dan token POS Flutter. Google tersedia setelah konfigurasi Firebase; database usaha tetap di Selaris.

## Evidence

- Web production build berhasil; TypeScript lolos. Image memakai `npm ci` dari lockfile.
- Backend: 8 unit tests memeriksa tanda tangan/claim token, provider, expiry, proof nomor, replay dan rate limit; tes integrasi Postgres membuktikan tautan akun lama dan pendaftaran baru tanpa toko ganda.
- Migrasi 111 lolos upgrade, downgrade ke 110, lalu upgrade ulang di salinan schema Postgres. Constraint unik juga menolak duplikasi identitas langsung di database.
- Flutter: 8 widget tests; welcome 320/768 px, semua state login di 320 px, ready dan formulir Google dengan teks 160%. APK kasir release berhasil dikompilasi. Analyzer tidak menemukan error; empat warning lama berada di modul Dapur/orders/products.
- Browser fixture memakai server actions asli dan Chromium. Tidak mengirim OTP ke nomor pengguna. Alur validasi nomor, Sef tidak ditemukan, fallback WA, OTP salah/benar, pilihan usaha, PIN tidak cocok, referral, produk gagal/retry, skip/back, theme, menu mobile dan tautan publik sudah diklik.
- Popup Google sungguhan dan pengiriman OTP ke akun pengguna menunggu konfigurasi konsol dan pengujian pemilik. Tombol Google yang belum dikonfigurasi tampil nonaktif dengan penjelasan.

## Delivery gate

- R-02 PASS: teks layar yang diubah memakai kalimat biasa tanpa em dash.
- R-03 PASS: browser 320/375/768/1440 px tanpa overflow; Flutter 320/768 dengan teks 160% lolos.
- R-17 PASS: tidak menambahkan statistik pemasaran; ringkasan dashboard memakai API yang sudah ada.
- R-18 PASS: tidak menambahkan testimoni atau identitas pelanggan.
- R-23 PASS: geometri logo dan foto onboarding memakai aset existing; font dari referensi Sefrekuensi disertai lisensi OFL.
- R-24 PASS: login/register/home/terms/privacy/dashboard/payment/download menuju route existing; link Play memakai package Sefrekuensi existing.
- R-25 PASS: tes browser mengukur teks aktif terhadap WCAG AA; heading 13.71:1 terang dan 16.33:1 gelap. Error light memakai `#B63530`; border kontrol memakai `#8B8178`.
- R-26 PASS: setiap kontrol memiliki handler/link; Google nonaktif saat konfigurasi kosong dengan label yang terlihat.
- R-27 PASS: pilihan login memuat status; form menampilkan error/retry; Google batal, nomor invalid, OTP invalid, PIN mismatch dan produk gagal ditangani.
- R-28 PASS: tidak menambahkan FAQ.
- R-32 PASS: focus browser 3 px; field memakai label, OTP autofill; menu mobile mendukung Escape dan mengembalikan fokus. Sidebar tertutup memakai inert.
- R-33 PASS: perubahan antarmuka ditulis lewat source patches; fixture eksternal hanya untuk pengujian.
- R-34 PASS: tema terang/gelap diuji lewat toggle, reload dan dashboard; pilihan tema disimpan.
- R-35 PASS: production web dan APK dibangun; click-through aktif direkam pada `tests/auth-browser.cjs`, `kasir_app/test/onboarding_test.dart`, dan `kasir_app/test/login_test.dart`. Konfigurasi Google kosong ditangani sebagai keadaan produk, bukan tombol palsu.
- R-36 PASS: klaim pembacaan otomatis kode WA yang tidak didukung dihapus; tidak menambahkan janji security/compliance/performance.
- R-37 PASS: direction berasal dari permintaan Ivan dan source Sefrekuensi; dials dipakai pada iterasi final.
- R-38 PASS: copy menyebut fitur existing; data fixture hanya dipakai pada lingkungan tes.
- R-01 PASS: glow dihapus; alias gradient lama dibuat datar untuk kompatibilitas logo/komponen.
- R-04 PASS: panah kembali, tema, akun, printer dan status merepresentasikan aksi nyata; ikon Google mengidentifikasi provider.
- R-06 PASS: Plus Jakarta Sans mengikuti brand referensi; monospace dipakai untuk OTP; label biasa tanpa tracking lebar.
- R-07 PASS: tidak menambahkan grid/dot/pola latar.
- R-08 PASS: aksi baru memakai kata kerja; panah hanya sebagai tombol kembali/navigasi.
- R-09 PASS: tidak menambahkan badge pemasaran; PRO existing menunjukkan paket usaha.
- R-10 PASS: tidak menambahkan glassmorphism.
- R-12 PASS: form onboarding flat; dashboard mempertahankan border/elevation kecil pada panel data.
- R-13 PASS: glow brand/pink/violet menjadi none di web dan daftar shadow Flutter kosong.
- R-14 PASS: konten autentikasi berupa satu alur; daftar pengaturan berisi aksi merchant yang berbeda.
- R-19 PASS: gerak terbatas ke feedback interaksi/loading; reduced-motion tersedia pada web.
- R-22 PASS: tidak menambahkan ilustrasi generik; welcome memakai foto meja existing.
- Liveliness PASS: ENERGY 2 / RHYTHM 2 / MOTION 1 tercatat pada direction dan diterapkan.
- Focal point PASS: judul langkah dan aksi utama memandu login, verifikasi, usaha, dan produk pertama.
- Whitespace PASS: spacing memisahkan heading, form, alternatif login dan footer; form maksimal 480 px.
- Accent PASS: coral pada aksi utama, tinta coral untuk label/action terang; dark memakai ink putih sesuai referensi.
- Identity PASS: palet Sefrekuensi dan Plus Jakarta Sans berulang; mark Selaris tetap dikenali.
- Design read PASS: merchant account setup dan POS, mengikuti arah Sefrekuensi yang diberikan pemilik.
- C-1 PASS: warna/font/radius mengikuti token referensi; layout mengikuti tugas merchant.
- C-2 PASS: handler/link dan state nonaktif diperiksa melalui click-through.
- C-3 PASS: hanya account, verifikasi nomor, usaha, menu dan persiapan kasir; tidak ada bagian pemasaran tambahan.
- C-4 PASS: breakpoint, theme, focus, error, retry dan teks besar diuji.
- C-5 PASS: tidak menambah testimoni, statistik atau klaim fiktif.
- R-05 PASS: urutan layar mengikuti langkah akun/usaha; dashboard mengikuti kebutuhan laporan existing.
- R-11 PASS: input/button 14 px, card 20 px, sheet 28 px; tidak semuanya pill.
- R-15 PASS: CTA menyebut aksi, misalnya Kirim kode, Verifikasi, Buat usaha, Simpan dan lanjut.
- R-16 PASS: copy tidak menambahkan buzzword pemasaran.
- R-20 PASS: pilihan Sefrekuensi, pesan Yasmin, PIN kasir, kategori usaha dan setup menu adalah konteks Selaris.
- R-21 PASS: terang default; gelap dipilih dan disimpan oleh pengguna.
- R-29 PASS: core palette warm neutral/coral/charcoal; warna status existing tetap punya fungsi.
- R-30 PASS: identitas berasal dari Sefrekuensi sesuai permintaan, bukan salinan produk SaaS lain.
- R-31 PASS: palet untuk penyatuan identitas, font untuk konsistensi, form sempit untuk fokus, ukuran kontrol untuk touch, tema untuk pilihan pengguna.
