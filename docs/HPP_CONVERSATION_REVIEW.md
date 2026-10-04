# Percakapan HPP, revisi 4 Oktober 2026

Ivan meminta tampilan dan percakapan seperti chat biasa. Review ini menggantikan
komposisi UI awal di HPP_CHAT_REVIEW.md; rumus, penyimpanan dan kontrak API di
review tersebut tetap berlaku.

Design Read sebelum perubahan: satu kolom percakapan untuk pemilik usaha,
Source Sans 3 dan palet Sefrekuensi. ENERGY 2 / RHYTHM 2 / MOTION 1. Antislop
during mengikuti pilihan sesi pengguna.

## Revisi asisten bahan dan resep

Balasan pertanyaan sebelumnya selalu masuk pemeriksaan draft. Pertanyaan katalog
tanpa nama menu tertimpa "Mau bikin menu apa?", meskipun context toko sudah dikirim.

- Model membedakan jawaban/lookup dengan membuat atau mengoreksi resep. Lookup
  membaca katalog terbaru melalui backend: bahan, resep aktif, menu tanpa resep,
  takaran resep dan penggunaan bahan. Nama dan hitungan bukan dari reply model.
  Menu terdaftar dibedakan dari resep tersimpan; draft bukan resep operasional.
- Ringkasan jumlah tetap lengkap ketika input katalog dipadatkan. Hasil lookup
  membaca seluruh context tenant/brand, termasuk item di luar input model. HPP
  memakai Decimal dan helper biaya resep existing; optional, archived dan takaran
  nonpositif dikecualikan. Satuan invalid tidak dijadikan angka HPP tebakan.
- Pertanyaan menjaga draft, preview, revision, fingerprint dan mode sebelumnya.
  Mode sebelum pesan disimpan dalam turn.usage agar retry/worker tetap konsisten.
  Setelah approve composer tetap tersedia untuk bertanya. Mengubah resep yang
  telah disimpan diarahkan lewat Resep baru, dengan approval manusia tetap berlaku.
- Welcome menyebut cek bahan dan membuat resep. Arah visual tetap Source Sans 3,
  palet Sefrekuensi dan ENERGY 2 / RHYTHM 2 / MOTION 1; tanpa aset/CSS baru.
- Build/TypeScript PASS. Chat browser final PASS pada lima lebar dan kedua tema,
  AA/44px/fokus/200% serta pertanyaan setelah approve tanpa revision/total berubah.
  Math/protocol18/500 oracle PASS; katalog empat kasus PASS termasuk 700 item
  dipadatkan tanpa kehilangan hasil lookup atau mengubah draft.
- PG QA non-superuser RLS PASS: toko lain kosong tidak melihat bahan tenant pertama,
  pertanyaan di tengah draft/applied/replay, lanjut estimasi, repeat approval,
  rollback, POS/cancel/stok dan real HTTP202. Pertanyaan tidak menulis produk,
  bahan, resep, stok fisik atau event operasional.
- Provider nyata PASS pada enam pertanyaan katalog dan bantuan umum dengan fixture
  sintetis; empat regresi input HPP serta pelengkapan estimasi/koreksi juga PASS.
  Tidak membuka database atau mengekspor cerita/katalog merchant untuk QA provider.
- Image yang diuji: `sha256:7fa2f9a2d721a8230038fd894bda2bdc6105379ae1a9f554073b26e1d6da17fe`.
  Handoff/deployment aktual dicatat di MEMORY.md dan SESSION.md. Migration112/APK tetap.

## Revisi estimasi setelah tes pengguna

Percakapan terbaru menunjukkan pengguna meminta estimasi lewat pesan, tetapi
pilihan UI masih Manual. Model mengatakan resep siap meski pembelian bahan baru
kosong dan takaran minyak berbeda keluarga satuan dengan bahan toko.

- Chat web baru mulai di Estimasi. Manual tetap dapat dipilih. Permintaan
  langsung seperti "bantu estimasikan" mengubah mode efektif server; pertanyaan,
  kutipan dan penolakan diperiksa. Mode asli request tetap disimpan pada turn
  agar retry UUID dari request awal tidak berubah identitas.
- Estimasi mengisi bahan, takaran dan harga/jumlah pembelian dari nama menu,
  memakai satu porsi perkiraan bila pengguna belum menyebut jumlah. Data nyata,
  kutipan, bahan terlarang dan harga toko dipertahankan. Tidak membuat konversi
  massa-volume; takaran estimasi dapat diusulkan dalam satuan toko.
- Draft estimasi yang belum lengkap diperiksa backend dan mendapat satu upaya
  pelengkapan dengan daftar kesalahan aktual, memakai budget output kedua yang
  sudah tersedia. Pemanggilan model maksimal dua, termasuk schema repair;
  input/output usage kedua panggilan dijumlahkan.
- Balasan tidak mengatakan siap jika preview backend incomplete. Angka uang
  dan pembahasan hitungan finansial model pada reply diganti ajakan review;
  angka HPP berasal dari kartu backend. Lengkapi estimasi di draft incomplete
  memberi pesan bantuan satu klik; disabled saat pending/busy atau ada koreksi
  belum terkirim. Approval tetap tindakan terpisah.
- Build/TypeScript dan chat browser final lolos, termasuk bantuan pada HP kedua
  tema. Math/protocol18 kasus dan 500 oracle; Postgres QA RLS, permintaan estimasi
  dari Manual, replay asli, kembali Manual, atomic approval/rollback/POS/stok,
  serta real HTTP202 worker lolos. Provider empat kasus asli fixture dan replay
  sintetis harga kosong/minyak kg-kebutuhan ml/koreksi nyata/single-menu lolos.
  Tidak menjalankan ulang provider dengan percakapan merchant: auto-review menolak
  ekspor payload asli; alternatif memakai fixture tanpa akses DB.
- Image frontend final revisi estimasi:
  `sha256:cd6bd24f7fdf016663fd97de6e17aa42808a2a4ad9880e05865ef676f4dc1017`.
  Catatan deployment/latest source ada di MEMORY.md dan SESSION.md.
- Source `a36c9ca` terpasang, frontend Created2026-10-04T17:19:10Z; empat layanan
  healthy. Migration112 dan APK unchanged. Provider sintetis regresi tersimpan
  di `tests/hpp-estimate-provider.py` tanpa akses database/merchant payload.
- Smoke HTTPS actual tiga lebar kedua tema/default/riwayat/form/entry lolos pada
  diagnostic ulang tanpa write merchant. Smoke awal sempat React418 lagi;
  penyebab belum teridentifikasi dan tidak diklaim telah diperbaiki.

## Perubahan UI awal

- Pesan pengguna di kanan, jawaban asisten di kiri; composer di bawah dengan
  textarea yang tumbuh sampai 160 px. Enter mengirim, Shift+Enter membuat baris
  baru, komposisi IME tidak memicu pengiriman.
- Riwayat lewat tombol, bukan dropdown di atas form. HPP backend menjadi satu
  kartu ringkas di percakapan. Lihat resep membuka dialog dengan rincian bahan,
  sumber, biaya delapan desimal, formula serta persetujuan manusia.
- Dialog native menjaga fokus, Tab/Shift+Tab, Escape dan kembali ke pemicu.
  Isi dapat digulir pada HP dan layar pendek; tombol tutup tetap tersedia.
- Pengguna dapat mengetik koreksi saat jawaban diproses. Retry UUID yang sama
  mempertahankan koreksi berikutnya. Approval diblokir selama pesan belum dikirim,
  pending, data tidak lengkap, atau ada kegagalan yang perlu diperiksa lewat GET.
  Konfirmasi mengganti resep aktif tetap terpisah.
- Prompt meminta balasan biasa memakai aku/kamu, satu pertanyaan berikutnya,
  tanpa daftar langkah atau penjelasan form berulang. Nama menu mengikuti cerita,
  tanpa mengharuskan pengguna menyebut istilah nama produk. Model tidak menulis
  hasil HPP dalam reply; UI mengambil angka backend.
- Riwayat balasan lama tetap tersimpan. Tidak ada simulasi streaming token.
  Worker, polling, batas cerita panjang, rumus Decimal, RLS dan transaksi
  approval tidak berubah. Migration tetap 112, APK tetap 1.6.31+198.

## Bukti verifikasi

- Build produksi/TypeScript lolos. Image final yang diuji:
  `sha256:42f83214fedffb4ca5451374022b47ac36922131903c23e22ce7da050aa4f4de`.
- `tests/hpp-chat-browser.cjs` lolos: cerita 50k karakter, Enter/Shift+Enter,
  manual/estimasi, resume/riwayat/navigasi form, kutipan dan biaya presisi,
  approval/koreksi/replacement, 409 re-review, 500 setelah simulated commit tanpa
  replay, polling GET dan retry yang menjaga koreksi baru. Semua write fixture.
- Lima lebar 320/390/768/1024/1440 dan kedua tema, teks AA, target 44 px,
  tanpa overflow, fokus dialog, Escape, 200% teks dan viewport 320×420.
  Screenshot diambil setelah transisi sidebar selesai; desktop terang, HP gelap
  dan dialog HP diperiksa secara visual.
- `tests/hpp-math.py`: 15 kasus termasuk 500 oracle independen dan protokol
  cerita panjang/schema repair. Provider nyata draft-only: batch, kemasan,
  harga per kg dan sumber estimasi lolos. Pemeriksaan dua turn percakapan
  menawarkan estimasi saat bingung tanpa membuat tebakan Manual siap approve.
- Regresi form HPP, Bahan Baku, auth dan mode stok/storefront memakai image final.
  Bukti deployment dan smoke HTTPS aktual dicatat di SESSION.md. Log/screenshot
  `/tmp/selaris-hpp-modern-*` tidak berisi perubahan harga/stok merchant.
- Source `cdcc2ec` live; empat layanan healthy dan mount APK tetap. HTTPS actual
  320/768/1440 kedua tema, riwayat/refresh/form/entry lolos tanpa write merchant.
  Smoke pertama pernah mencatat React418; diagnostic ulang selesai tanpa error,
  penyebab belum teridentifikasi dan tidak diklaim telah diperbaiki.

## Delivery gate antislop

- R-01 PASS: permukaan solid dan token coral existing, tanpa gradient/glow baru.
- R-02 PASS: copy chat memakai kalimat biasa, tanpa em dash.
- R-03 PASS: lima lebar/dua tema, input panjang dan kutipan membungkus tanpa overflow.
- R-04 PASS: History/Plus/X/ArrowUp masing-masing membuka riwayat, resep baru, tutup dan kirim.
- R-05 PASS: satu percakapan dan kartu HPP aktual, tanpa hero/bento.
- R-06 PASS: Source Sans 3 untuk chat/angka, tanpa monospace dekoratif.
- R-07 PASS: tidak menambah latar grid/dot/blueprint.
- R-08 PASS: panah hanya kontrol kirim dengan label aksesibel, tanpa panah dekoratif.
- R-09 PASS: status estimasi/tersimpan menyatakan kondisi resep aktual.
- R-10 PASS: composer/dialog solid, tanpa glassmorphism.
- R-11 PASS: sudut bubble, composer dan dialog mengikuti fungsi berbeda, bukan semua capsule.
- R-12 PASS: border memisahkan kontrol; tanpa shadow di setiap pesan.
- R-13 PASS: tanpa efek glow baru.
- R-14 PASS: bubble pengguna, jawaban plain dan ringkasan angka punya hierarki berbeda.
- R-15 PASS: Tulis pesan, Lihat resep dan persetujuan menyebut tindakan yang dilakukan.
- R-16 PASS: prompt dan copy memakai bahasa dapur biasa, tanpa buzzword pemasaran.
- R-17 PASS: harga/HPP/jumlah porsi/status berasal dari preview atau lookup backend.
- R-18 PASS: tanpa testimoni atau avatar pelanggan buatan.
- R-19 PASS: hanya scroll terbaru saat pengguna dekat akhir, tanpa animasi dekoratif.
- R-20 PASS: rincian pembelian, takaran/porsi, biaya toko dan sumber spesifik tugas HPP.
- R-21 PASS: mengikuti tema dashboard; terang/gelap diuji.
- R-22 PASS: tidak membuat ilustrasi/foto generik.
- R-23 PASS: identitas existing dipertahankan; tidak membuat aset baru.
- R-24 PASS: riwayat, form, resep tersimpan, Menu dan Bahan Baku menuju fungsi nyata.
- R-25 PASS: teks AA kedua tema diperiksa browser pada chat dan dialog.
- R-26 PASS: mode/kirim/riwayat/rincian/sumber/rumus/approve/retry/recovery, Lengkapi estimasi dan tanya katalog setelah approve diuji.
- R-27 PASS: kosong/loading/pending/incomplete/error/applied tersedia dengan recovery.
- R-28 PASS: bantuan lokal muncul di sumber dan approval, tanpa FAQ generik.
- R-29 PASS: warm neutral/charcoal/coral sesuai token Sefrekuensi.
- R-30 PASS: mengikuti permintaan chat biasa dan identitas pengguna yang sudah dipilih.
- R-31 PASS: font untuk cerita, ruang untuk giliran chat, border untuk kontrol dan angka.
- R-32 PASS: label, radio, checkbox, details/dialog native serta fokus keyboard diuji.
- R-33 PASS: source dan CSS diedit dengan apply_patch.
- R-34 PASS: kedua tema dan regresi dashboard theme persistence lolos.
- R-35 PASS: build, browser fixture, provider nyata, math dan smoke deployment diverifikasi.
- R-36 PASS: estimasi tetap berlabel, biaya operasional belum termasuk; incomplete tidak mengaku siap, katalog kosong tidak membuat bahan/resep fiktif.
- R-37 PASS: Design Read dan ENERGY 2 / RHYTHM 2 / MOTION 1 dinyatakan sebelum edit.
- R-38 PASS: tidak mengisi harga/resep/stok merchant untuk QA; semua usulan berlabel sumber.
- Liveliness dials PASS: ENERGY 2 / RHYTHM 2 / MOTION 1 diterapkan.
- Liveliness consistency PASS: percakapan tenang dengan feedback proses dan kartu aktual.
- Liveliness focal point PASS: cerita menjadi fokus; angka/review dapat dibuka saat diperlukan.
- Liveliness whitespace PASS: giliran pesan dan composer terpisah, tanpa panel form permanen.
- Liveliness accent PASS: coral pada tindakan dan mode terpilih sesuai tema existing.
- Liveliness identity PASS: Source Sans 3, permukaan hangat dan detail resep Selaris dipertahankan.
- Liveliness Design Read PASS: arah dinyatakan sebelum perubahan UI.
- C-1 PASS: font/palet berasal dari identitas; komposisi mengikuti permintaan chat biasa.
- C-2 PASS: seluruh kontrol punya fungsi nyata dan uji recovery.
- C-3 PASS: bagian untuk cerita atau pemeriksaan resep, tanpa template landing page.
- C-4 PASS: tema/viewport/keyboard/teks panjang dan pending/error diuji.
- C-5 PASS: angka dari backend; data QA hanya fixture dan tidak diklaim sebagai data toko.
