# Delivery Gate form akun karyawan

Design Read: form operasional Selaris bagi pemilik dan pengelola toko, memakai
Source Sans3, warm neutral/charcoal/coral existing, ENERGY1/RHYTHM1/MOTION1.
Profil dan login disusun dalam satu form; Simpan menjadi tindakan utama.
Spacing memisahkan identitas, penempatan, login, dan masa kerja. Tidak ada aset
baru; password toggle memakai komponen existing. Bukti: production build image
ec2599c…0e09, enam hash runtime, tests/staff-accounts-browser.cjs dan
tests/accounts-browser.cjs. Seluruh mutasi browser menuju fixture localhost.

- R-02 PASS: copy baru diperiksa; tidak memakai em dash.
- R-03 PASS: form phone/username/profile pada320/375/768/1440, kedua tema dan200% tidak overflow; password field membungkus toggle bila ruang sempit.
- R-17 PASS: daftar/status memakai API; semua record QA bernama fixture, bukan angka pemasaran.
- R-18 PASS: tidak menambah testimonial.
- R-23 PASS: hanya membuat flow akun yang diminta; tidak membuat aset/identitas baru.
- R-24 PASS: link Akun saya menuju /dashboard/hris/access yang diuji dalam suite akun.
- R-25 PASS: scanner formula WCAG memeriksa teks form pada kedua tema; batas/fokus kontrol memakai token existing yang diuji suite akun.
- R-26 PASS: mode akun, identifier, role, reset password, toggle, Simpan, receipt retry dan link memiliki handler nyata; grant manager diklik dan terkirim.
- R-27 PASS: loading/error/retry, profil saja, toko tanpa username, manager tanpa grant dan pending saved/unknown diuji.
- R-28 PASS: tidak menambah FAQ.
- R-32 PASS: label input/select, toggle Space, focus outline, dialog trap/Escape dan target44px diuji.
- R-33 PASS: UI ditulis di source TSX/CSS melalui patch; fixture tidak memodifikasi produk.
- R-34 PASS: kedua tema diperiksa pada empat lebar serta auth/console akun.
- R-35 PASS: image produksi dijalankan dan seluruh kontrol baru diuji; HTTP/JWT/forced-RLS terpisah lulus.
- R-36 PASS: tidak menambah klaim sertifikasi/performa; batas QA dan perangkat fisik disebutkan.
- R-37 PASS: brand existing dan dials1/1/1 dipertahankan.
- R-38 PASS: nama dan data live berasal API; nomor/nama dari contoh user hanya dipakai pada fixture sintetis, tanpa write merchant.
- R-01 PASS: tidak menambah gradient/glow.
- R-04 PASS: tidak menambah ikon dekoratif; toggle menggunakan teks tindakan.
- R-06 PASS: font existing untuk membaca form, tanpa monospace heading.
- R-07 PASS: tidak menambah background grid/dot.
- R-08 PASS: tidak menambah panah dekoratif.
- R-09 PASS: tidak menambah badge pemasaran.
- R-10 PASS: tidak menambah glassmorphism.
- R-12 PASS: border pemisah memakai token existing, tanpa shadow baru.
- R-13 PASS: tidak menambah glow.
- R-14 PASS: field disusun menurut data/proses karyawan; tanpa kartu fitur seragam.
- R-19 PASS: disabled/status mengikuti request; tanpa animasi dekoratif.
- R-22 PASS: tidak menambah ilustrasi.
- Liveliness dials PASS: ENERGY1/RHYTHM1/MOTION1 dinyatakan dan mengikuti form existing.
- Liveliness consistency PASS: form tenang dan tindakan Simpan jelas, tanpa dekorasi baru.
- Liveliness focal point PASS: satu Simpan menangani profil dan akun.
- Liveliness whitespace PASS: separator/spacing membedakan profil, login, dan masa kerja.
- Liveliness accent PASS: coral hanya untuk tindakan utama; kontrol lain netral.
- Liveliness identity PASS: font, istilah karyawan/outlet/hak akses dan kontrol Selaris dipertahankan.
- Liveliness Design Read PASS: arah existing dicatat sebelum penyerahan.
- C-1 PASS: password wrap menjawab hasil uji320/200%; layout dan warna mengikuti brand existing.
- C-2 PASS: setiap kontrol baru mempunyai handler dan click-through.
- C-3 PASS: setiap bagian menjawab pembuatan profil/login, tidak memakai template marketing.
- C-4 PASS: tema/mobile/200%/keyboard, network uncertainty/reload dan restricted manager diuji.
- C-5 PASS: tidak membuat statistik, testimonial atau klaim fiktif.
- R-05 PASS: form operasional, tanpa hero/bento/pricing.
- R-11 PASS: radius input/panel/button existing dipertahankan.
- R-15 PASS: CTA menyebut Simpan, Periksa penyimpanan, Tampilkan/Sembunyikan.
- R-16 PASS: tidak menambah buzzword marketing.
- R-20 PASS: pola form Tim & absensi dan bahasa toko Selaris dipertahankan.
- R-21 PASS: tema terang/gelap existing tersedia dan diuji.
- R-29 PASS: palette existing tanpa warna inti baru.
- R-30 PASS: meneruskan interface Selaris, tanpa meniru produk lain.
- R-31 PASS: separator untuk login, spacing untuk kelompok field, coral untuk Simpan, wrap untuk password di layar sempit.

UI supplement PASS: typography/palette existing, tanpa aset/ikon dekoratif;
profil saja tetap tersedia dan label menjelaskan default absensi pribadi.

Human supplement PASS: kontras, label, focus/keyboard/Escape, target44px,
error/status dan teks200% diperiksa; password dimulai tertutup dan toggle
tidak mengirim form. Recovery setelah reload tidak memerlukan password
untuk receipt yang sudah tersimpan.

Layoutmobile supplement PASS: empat lebar/dua tema dan200% diuji; input dan
toggle password membungkus secara alami; dialog dapat digulir tanpa
overflow horizontal, tanpa hover-only control atau nav baru.
