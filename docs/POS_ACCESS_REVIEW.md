# Izin POS, stok dan sync

6 Oktober 2026. Ivan memilih langkah 1 setelah rilis akun 1.6.32: membedakan hak lihat/tindakan, membatasi outlet, dan menjaga antrean saat akses berubah. Backend/web live dan rilis resmi 1.6.33+200 terverifikasi; rincian di [deployment POS](POS_ACCESS_RELEASE.md).

Managed staff memakai izin canonical yang diperiksa ulang server pada setiap permintaan. Registry mencocokkan callable endpoint dan HTTP method; nama/path serupa tidak membuka handler baru. Scope outlet aktif, brand, tenant, parent pesanan/pembayaran/tab/shift dan tujuan perpindahan diperiksa sebelum mutation. ID path/query/body yang bertentangan ditolak; tambahan ID tidak boleh menyamarkan target atau parent. Owner aktual dan akun legacy mempertahankan alur existing. Role lama tidak diubah otomatis.

| Izin | Perilaku |
| --- | --- |
| `pos.sell` | Pesanan, pembayaran, meja/tab dan penanganan pesanan online di outlet yang diizinkan. |
| `pos.discount.override` | Perubahan harga katalog dan diskon agregat di atas 20%. Subtotal dihitung server. |
| `pos.refund` / `pos.refund.approve` | Pengajuan dipisah dari persetujuan/penolakan. Membatalkan pesanan/tab yang sudah dibayar membutuhkan persetujuan refund. |
| `pos.shift.manage` / `pos.cash.manage` | Buka/jeda/hitung sesi dipisah dari catatan kas masuk/keluar. Tanpa rincian penjualan, total laci, review, selisih dan pesan selisih disembunyikan. |
| `pos.kitchen` | Daftar operasional dan status dapur tanpa izin menerima pembayaran. |
| `sales.detail.view` | Riwayat seluruh kasir. Kasir tanpa grant ini membaca transaksi sendiri, termasuk pesanan online yang diterimanya, dan pekerjaan aktif bersama. |
| `stock.view` / `stock.receive` / `stock.adjust` | Hak membaca stok, menerima barang dan opname dipisah. Pengelolaan stock/HPP/menu lain tetap tertutup untuk managed. |
| `customers.lookup` | Pencarian transaksi minimum tiga karakter, maksimum lima nama/nomor tersamar. Tidak membuka profil lengkap, ekspor, catatan atau agregat CRM. Wildcard SQL diperlakukan literal. |

Harga modal/HPP, counter penjualan dan secret provider direduksi pada JSON response managed. Pembayaran staf harus menunjuk pesanan POS; invoice billing dan pembayaran di luar pesanan/tab ditolak, termasuk lewat refund/list/history; tagihan diperiksa terhadap sisa pesanan, bukan jumlah client. Replay kunci pembayaran tidak boleh menunjuk pesanan berbeda. Catatan kas membutuhkan jumlah positif dan keperluan.

Stok simple tetap canonical di Product, digunakan bersama outlet satu brand; memilih outlet tidak membuat stok simple terpisah. Resep tetap memakai OutletStock per outlet. Algoritme raw quantity resep, unit conversion HPP, PN counter, event, idempotence dan return stok saat cancel tetap existing. Teks web menjelaskan stok simple bersama.

## Web dan APK

Owner mengatur izin baru melalui editor jabatan HRIS. Web managed memiliki Operasional untuk kasir/stok: pilihan outlet, daftar stok, terima produk/bahan dan opname produk simple. Produk resep tidak diberi tombol restock/opname; yang diterima adalah bahan dengan satuan tercatat. Timeout/5xx menahan tindakan berikutnya sampai pembacaan stok baru berhasil, tanpa retry mutation otomatis.

APK managed memiliki workspace operasional sendiri. Kasir, riwayat, sesi kas, catatan kas, pengajuan/persetujuan refund dan papan dapur mengikuti grant. Keuangan/HPP/pengelolaan owner tidak dimount melalui IndexedStack legacy. Stok dikelola melalui tautan web. Login/PIN, foreground dan sync memuat manifest server; menu UI membantu penggunaan, otorisasi tetap server. Dapur pendamping masih login PIN existing; akun username staff menggunakan POS, termasuk papan dapur managed.

Kebijakan masa izin offline belum dipilih. Default konservatif yang diumumkan dalam sesi: managed baru hanya transaksi online dan sync pull-only. Push nonkosong ditolak sebelum idempotency claim/mutation dengan `OFFLINE_SYNC_REVIEW_REQUIRED`. Perangkat mempertahankan semua antrean lama dan pending retry key; pemilik menyelesaikannya memakai alur existing. Role legacy tetap dapat offline sesuai perilaku existing, sehingga pencabutan tidak dapat sampai seketika pada perangkat legacy yang offline.

Cursor managed dipisah per tenant/user/outlet dan versi akses. Penanda pemilik cache juga memaksa purge/full pull saat akun staf yang sama kembali setelah sync pemilik. Perubahan versi membersihkan cache yang sudah synced, mempertahankan antrean dan parent yang diperlukan, lalu menarik data ulang. Backfill legacy ditandai ulang agar cache pemilik terisi penuh saat kembali login, tanpa memajukan watermark atau membuang retry key pemilik. Pull tidak menimpa ID pending atau parent antrean. Pergantian UUID/outlet/token/generation membatalkan hasil sync lama sebelum apply/checkpoint. Riwayat/menu managed tidak memakai fallback SQLite lama. JSON manifest rusak gagal tertutup. SSE mengecek ulang izin/sesi sebelum meneruskan event dan berhenti saat dicabut; FCM memeriksa ulang user/grant/outlet/order sebelum memilih token; SSE/FCM hanya meneruskan event POS yang didukung, bukan reservasi atau domain baru. Tidak mengklaim penautan setiap token FCM ke satu sid perangkat.

## Bukti QA

QA memakai schema-only dan data sintetis pada PostgreSQL terpisah dengan FORCE RLS, app NOSUPERUSER/NOBYPASSRLS, jaringan internal tanpa port publik. Provider pembayaran/WhatsApp/FCM nyata tidak dipanggil. Browser memakai fixture lokal; tidak write merchant.

| Pemeriksaan | Hasil |
| --- | --- |
| Backend unit | 63 test, 62 PASS dan satu fixture opsional skip; `/tmp/selaris-pos-access-unit-final.log`. Registry, strict grants, redaction dan regresi modul existing. |
| HTTP/JWT/PostgreSQL | Lima kelompok PASS: izin/scope/harga/subtotal/replay/stok; riwayat/payment tab/refund/kas/customer/dapur/push; sync semua tabel push ditolak dan pull dibatasi; SSE dicabut sebelum event; stok resep sale/cancel/receive, pencabutan dan legacy. `/tmp/selaris-pos-access-qa-final.log`, `tests/pos-access-isolated.py`. |
| Native penuh | 45 PASS, dua fixture diagnostik opsional skip; `/tmp/selaris-pos-access-native-full-final.log`. |
| Native khusus | Sepuluh PASS: cold manifest, queue/dependency/same-ID pull, revocation/account switch, 320px/160%, catatan kas, blok offline, dialog refund cancel/approve/reject dan tiga status dapur; `/tmp/selaris-pos-access-native-final.log`. |
| Analyzer | Enam file final tanpa issue; pemeriksaan 13 file sebelumnya hanya dua info withOpacity existing. `/tmp/selaris-pos-access-analyze-final.log`. |
| Web | TypeScript PASS dan Docker Next production build PASS; `/tmp/selaris-pos-access-tsc.log`, `/tmp/selaris-pos-access-web-build-final.log`. |
| Browser stok | 320/375/768/1440 light/dark, 200% teks, AA kontras, keyboard, outlet, terima/count, unit bahan, timeout lock tanpa retry, error/empty, revoke dan download PASS; `/tmp/selaris-pos-access-browser-final.log`, trace `/tmp/selaris-pos-access-browser-trace.zip`, screenshot `/tmp/selaris-pos-access-stock.png`. |
| Browser akun | Regresi auth/HRIS dan klik semua checkbox izin baru PASS; `/tmp/selaris-pos-access-accounts-browser.log`. |

QA pada image produksi juga PASS dengan fixture yang sama (`/tmp/selaris-pos-access-production-browser.log`), termasuk empat lebar/tema/200% dan seluruh tindakan. Locator alert QA dibatasi ke workspace agar tidak bentrok dengan route announcer bawaan Next produksi.

Preview memakai berkas font Selaris existing agar tidak bergantung pada DNS Google Fonts; source font tidak dipatch. Docker production build memakai konfigurasi produksi. Native memakai Plus Jakarta Sans dan tema operasional existing; web Source Sans 3. Belum pengujian perangkat fisik.

## Arah visual dan Delivery Gate antislop

Operasional untuk kasir/petugas stok mengikuti Selaris: warm neutral, charcoal, coral. ENERGY 1 / RHYTHM 1 / MOTION 1: heading tugas, daftar jumlah, lalu form tindakan aktif; spasi memisahkan pekerjaan. Coral menandai save/konfirmasi. Refresh/back/akun dan ikon receipt/store menyatakan fungsi, bukan dekorasi. Direction existing ditinjau saat penyempurnaan layar; tidak menciptakan brand/aset baru. Gate mencakup UI baru dan binding yang berubah; flow POS/shift existing dipertahankan dan API-nya diuji.

- R-02 PASS: copy baru tidak memakai em dash.
- R-03 PASS: browser empat lebar/200% dan widget 320px/160% tanpa overflow; dropdown native isExpanded dan judul dialog pelanggan dapat membungkus.
- R-17 PASS: jumlah stok berasal dari API; tidak ada statistik pemasaran.
- R-18 PASS: tidak ada testimonial.
- R-23 PASS: memakai aset/theme existing; navigasi operasional mengikuti langkah 1 yang dipilih Ivan.
- R-24 PASS: tautan operasional/account/download ada; browser membuka operasional dan download.
- R-25 PASS: sampel teks/kontrol operasional dan editor izin lulus pemeriksaan AA light/dark; native memakai token tema existing.
- R-26 PASS: semua kontrol memiliki handler; klik terima/count/outlet/refresh dan kas/refund/dapur diuji, kontrak kasir/shift diuji HTTP.
- R-27 PASS: loading, empty, denied/revoked, network failure dan uncertain-write memiliki tampilan; QA menjalankan state tersebut.
- R-28 PASS: tidak menambah FAQ.
- R-32 PASS: kontrol standar berlabel, fokus input saat form dibuka, Tab/focus-visible dan Escape menu diperiksa browser.
- R-33 PASS: implementasi dalam source repository; font fixture hanya konfigurasi preview.
- R-34 PASS: tema web terang/gelap lulus seluruh lebar; native mempertahankan tema light existing.
- R-35 PASS: Docker build dan widget native dijalankan; interaksi browser tersimpan dalam trace, widget kas/refund/dapur klik handler nyata dan API operasional diuji PostgreSQL.
- R-36 PASS: tidak menambah klaim sertifikasi/kinerja; batas online/offline dan QA dinyatakan.
- R-37 PASS: direction Selaris dan dials tercatat pada penyempurnaan akhir, tidak memakai arah brand fiktif.
- R-38 PASS: data QA sintetis hanya fixture; product menampilkan API nyata.
- R-01 PASS: tidak menambah gradient/glow.
- R-04 PASS: refresh/store/receipt/back menunjukkan tindakan; memakai ikon operasional existing.
- R-06 PASS: font brand existing; tidak ada monospace heading baru.
- R-07 PASS: tidak menambah background grid/dot.
- R-08 PASS: tidak menambah panah dekoratif CTA.
- R-09 PASS: tidak menambah badge pemasaran.
- R-10 PASS: tidak menambah glassmorphism.
- R-12 PASS: panel memakai border existing, bukan shadow besar.
- R-13 PASS: tidak menambah glow.
- R-14 PASS: daftar barang dan form edit melayani dua pekerjaan nyata, bukan kartu fitur seragam.
- R-19 PASS: loading/disabled menyatakan status request; tidak menambah motion dekoratif.
- R-22 PASS: tidak menambah ilustrasi.
- Liveliness dials PASS: ENERGY 1 / RHYTHM 1 / MOTION 1 untuk operasional.
- Liveliness consistency PASS: daftar/form berurutan dengan interaksi tenang.
- Liveliness focal point PASS: heading pekerjaan dan satu save/konfirmasi aktif.
- Liveliness whitespace PASS: jarak memisahkan outlet, daftar dan form.
- Liveliness accent PASS: coral pada tindakan utama mengikuti tema.
- Liveliness identity PASS: warm neutral, font Selaris dan tombol operasional berulang.
- Liveliness Design Read PASS: arah existing dibaca sebelum penyempurnaan final layar dan dicatat di atas.
- C-1 PASS: warna/font/list/form/spasi melayani pembacaan stok dan pencatatan.
- C-2 PASS: handler nyata dan kontrak server tersedia, tidak ada placeholder action.
- C-3 PASS: setiap bagian melayani outlet, kasir, stok atau tindakan grant.
- C-4 PASS: browser mobile/tema/200%/keyboard dan widget 320px/160% lulus; batas perangkat fisik tercatat.
- C-5 PASS: tidak ada testimonial/statistik/klaim fiktif.
- R-05 PASS: layout tugas operasional, tanpa hero/bento/pricing.
- R-11 PASS: memakai radius panel/form/button existing.
- R-15 PASS: CTA Terima barang, Stok opname, Catat kas, Setujui dan Muat ulang menyebut tindakan.
- R-16 PASS: tidak menambah buzzword pemasaran.
- R-20 PASS: memakai identitas Selaris existing.
- R-21 PASS: tema web bisa dipilih, tidak memaksa dark.
- R-29 PASS: palet dan status existing; tidak menambah warna sistem baru.
- R-30 PASS: mengikuti repository Selaris, tidak menyalin produk lain.
- R-31 PASS: alasan layout/font/warna/spasi tertulis di bagian arah visual.

Berikutnya: enforcement Keuangan/Pembelian/CRM/HPP, lalu seluruh jalur AI termasuk konteks/cache/history/RAG/worker/write. Offline lease baru, OTP pemulihan, GPS/foto/radius/retensi tetap keputusan tersendiri. Jangan membuka grant modul lain hanya karena menu baru disembunyikan.
