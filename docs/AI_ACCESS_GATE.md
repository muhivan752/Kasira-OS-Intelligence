# Delivery Gate tahap 3

Design Read: Selaris existing, Source Sans 3, warm neutral/charcoal/coral, ENERGY 1 / RHYTHM 1 / MOTION 1. Percakapan, pilihan outlet dan review resep memandu keputusan pengguna. Aset existing; tidak membuat ilustrasi atau identitas baru.

Bukti: `tests/ai-access-browser.cjs` mengklik workspace managed, SSE, outlet/conversation reset, draft-only review, foreground revoke, empat lebar 320/768/1024/1440, kedua tema, formula WCAG teks, target 44px dan teks 200%. `tests/hpp-chat-browser.cjs` memeriksa lima lebar, seluruh aksi owner, Enter/Shift+Enter, sumber/precision, retry/replay, pending/poll, dialog focus/Escape, 200% dan viewport pendek. Tujuh suite regression browser memeriksa akun/POS/finance/purchasing/CRM/HPP/business. Hanya fixture lokal yang menerima mutasi. Trace `/tmp/selaris-ai-access-browser-trace.zip`; log `/tmp/selaris-ai-*-browser.log`. Image final dan smoke publik dicatat dalam release record.

- R-02 PASS: copy baru tidak menggunakan em dash.
- R-03 PASS: workspace managed reflow pada empat lebar; HPP pada lima lebar dan viewport pendek; tidak ada overflow.
- R-17 PASS: angka/hasil berasal API; contoh hanya fixture yang diberi nama fixture/synthetic.
- R-18 PASS: tidak menambah testimonial.
- R-23 PASS: semua fitur sesuai tahap 3/password yang diminta; tidak membuat aset baru.
- R-24 PASS: AI/HPP/backend routes nyata; tautan tindakan lanjutan mengikuti grant dan outlet.
- R-25 PASS: scanner WCAG menghitung kontras teks/kontrol di tema terang/gelap; gaya kontrol berasal komponen HPP existing.
- R-26 PASS: pilih outlet, kirim, percakapan baru, draft/review/approve/retry/history dan reset akses memiliki handler nyata.
- R-27 PASS: empty/loading/error/retry/pending/revoke diuji; draft tanpa grant approve dijelaskan tanpa tombol simpan.
- R-28 PASS: tidak menambah FAQ.
- R-32 PASS: label textarea/select/buttons, Enter/Shift+Enter, fokus kembali, dialog focus trap/Escape diuji.
- R-33 PASS: UI ditulis dalam source app; fixture hanya melayani data dan memanggil UI.
- R-34 PASS: light/dark tersedia dan dicek pada seluruh lebar affected.
- R-35 PASS: production Docker build dan browser click-through dijalankan; backend HTTP/JWT/pgvector/forced-RLS diuji terpisah.
- R-36 PASS: tidak menambah klaim sertifikasi/performa; batas provider palsu dan perangkat fisik dicatat.
- R-37 PASS: mengikuti arah brand existing dan dials yang dinyatakan.
- R-38 PASS: data produk berasal API; fixture tidak disimpan menjadi konten pemasaran atau merchant.
- R-01 PASS: tidak menambah gradient/glow.
- R-04 PASS: workspace managed tidak menambah ikon dekoratif; ikon pesan/navigation existing menjelaskan tujuan.
- R-06 PASS: font brand existing untuk membaca pertanyaan/hasil; tanpa monospace heading.
- R-07 PASS: tidak menambah grid/dot background.
- R-08 PASS: tidak menambah panah dekoratif CTA.
- R-09 PASS: tidak menambah badge pemasaran.
- R-10 PASS: tidak menambah glassmorphism.
- R-12 PASS: panel/border existing, tanpa shadow besar.
- R-13 PASS: tidak menambah glow atau status dekoratif.
- R-14 PASS: percakapan dan review memakai susunan sesuai tugas, bukan kartu fitur seragam.
- R-19 PASS: disabled/status mengikuti request; tidak menambah loop animasi.
- R-22 PASS: tidak menambah ilustrasi.
- Liveliness dials PASS: ENERGY 1 / RHYTHM 1 / MOTION 1 dinyatakan.
- Liveliness consistency PASS: komposisi tenang dan tindakan jelas mengikuti dials.
- Liveliness focal point PASS: pertanyaan/jawaban dan total resep menjadi fokus.
- Liveliness whitespace PASS: spacing memisahkan outlet, history, status dan composer.
- Liveliness accent PASS: coral hanya pada tindakan kirim/approve yang tersedia.
- Liveliness identity PASS: kontrol, font dan bahasa Selaris konsisten lintas HPP/AI/akun.
- Liveliness Design Read PASS: arah existing dicatat sebelum delivery.
- C-1 PASS: keputusan visual mengikuti penggunaan toko dan komponen Selaris.
- C-2 PASS: setiap kontrol mempunyai tindakan nyata; tidak menawarkan approve yang dilarang.
- C-3 PASS: setiap bagian membantu memilih outlet, bertanya atau memeriksa draft.
- C-4 PASS: tema/mobile/200%/keyboard/error/revoke diuji; tidak mengklaim uji perangkat fisik.
- C-5 PASS: tidak ada angka/klaim/testimonial fiktif.
- R-05 PASS: workspace percakapan/review mengikuti kebutuhan, tanpa hero/bento/pricing.
- R-11 PASS: radius panel/kontrol/button mengikuti CSS Selaris existing.
- R-15 PASS: CTA menyatakan tindakan: Kirim pertanyaan, Percakapan baru, Susun draft HPP, Approve dan simpan resep.
- R-16 PASS: tidak menambah buzzword pemasaran.
- R-20 PASS: identity dan istilah pengelolaan toko Selaris dipertahankan.
- R-21 PASS: kedua tema tersedia dan diuji.
- R-29 PASS: palette existing; tidak menambah warna inti.
- R-30 PASS: memakai Selaris existing, tanpa meniru produk lain.
- R-31 PASS: font untuk membaca, panel untuk history, spacing untuk outlet/composer, coral untuk tindakan utama.

UI supplement PASS: palette/accent/type dari brand; tanpa emoji/pill/grid/glass/dekorasi; setiap angka nyata atau fixture berlabel; tidak membuat fake metrics; empty/loading/error menyebut sebab dan tindakan; semua navigasi sesuai kemampuan akun.

Human supplement PASS: kontras dan label/fokus/keyboard/dialog diperiksa; status menggunakan teks; 200%/viewport pendek dan textarea yang dapat digulir diuji.

Layoutmobile supplement PASS: layar menyusun kontrol menjadi baris terpisah di mobile; tablet/laptop/desktop diperiksa; grid tidak bertabrakan; target 44px; tanpa hover-only action atau fixed nav yang menutup composer.
