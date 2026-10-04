# SESSION — 2026-10-04

Baca `CLAUDE.md` → `MEMORY.md` → handoff ini sebelum melanjutkan. Bagian Oktober
di atas adalah acuan sesi terakhir; catatan dan NEXT ACTION April di bawah
merupakan arsip, bukan pekerjaan yang sedang aktif.

## HANDOFF TERAKHIR — estimasi langsung melengkapi HPP, live 4 Oktober 2026

- Ivan meminta estimasi tetapi masih bingung. Baca read-only sesi terbaru:
  permintaan estimasi dalam chat tidak mengubah mode Manual, model bilang siap
  padahal harga baru kosong dan minyak estimasi ml tidak cocok bahan toko kg.
  Source **a36c9ca** sudah live; tidak menjalankan/mutasi sesi asli otomatis.
- Web baru default Estimasi. Server conversation_mode mengenali permintaan
  langsung; session.mode efektif berubah, turn.mode tetap mode payload asli
  supaya duplicate-ID check dan retry dari request awal konsisten. Manual tetap
  memblokir tebakan dan negasi estimasi dihormati. Bukan classifier LLM.
- Estimasi langsung susun bahan/takaran/porsi/harga/jumlah beli dari nama menu.
  Takaran perkiraan mengikuti keluarga satuan bahan toko, bukan konversi massa-
  volume. Angka/kutipan nyata, bahan yang dihapus dan cost toko dipertahankan.
- generate melakukan prepare, lalu satu completion feedback jika estimate masih
  incomplete. Maksimal dua provider call total dengan schema repair, output
  8192/16384 unchanged. Usage input/output akumulatif. Backend re-read harga tetap.
  reply_for_preview dipanggil lagi worker: incomplete tidak mengaku siap dan
  pembahasan angka uang dari model diganti ajakan Lihat resep. Tidak math di LLM.
- Lengkapi estimasi di kartu incomplete mengirim pesan bantuan mode estimate;
  disabled pending/busy/unsent. Guard URL idle+href berubah, typed correction
  retry, human approval dan atomic transaction dipertahankan. Old replies unchanged.
- Build/TypeScript final image
  `sha256:cd6bd24f7fdf016663fd97de6e17aa42808a2a4ad9880e05865ef676f4dc1017`,
  live frontend Created2026-10-04T17:19:10Z; image sama QA. Backend dua file
  `services/hpp_setup_service.py` dan `api/routes/hpp_setup.py` docker cp/restart
  existing setelah active_hpp_jobs=0. Backup `/tmp/selaris-hpp-estimate-backup`.
  Jangan recreate backend. Migration112/APK1.6.31+198 unchanged, layanan healthy.
- QA: math18/500 oracle dan fake provider completion/usage/financial reply guard;
  PG RLS non-superuser/schema-only, explicit estimate/raw replay/manual rejection,
  longchat/concurrent/atomic rollback/POS/cancel/storefront/HTTP202 worker PASS.
  Browser chat lima lebar dua tema/AA44/200%/short/keyboard/retry/409/500 dan
  assistance incomplete320 dua tema PASS. Tidak mengubah CSS global task ini.
- Provider nyata empat fixture lama PASS; fixture sintetis replay harga kosong,
  oil kg-versus-ml estimates, reuse cost, human correction dan single-menu ready
  PASS. Auto-review menolak replay original conversation+shop context ke provider,
  tidak dieksekusi; alternatif tanpa DB/merchant payload selesai. Jangan mencoba
  replay data merchant tanpa authorization untuk ekspor tersebut.
- Review/gate `docs/HPP_CONVERSATION_REVIEW.md`; test provider sintetis tersimpan
  `tests/hpp-estimate-provider.py`, modul QA dipasang ke /tmp sesuai header loader.
  Log `/tmp/selaris-hpp-estimate-*`. Smoke HTTPS actual baca saja, tidak message/
  approve/write harga/resep/stok/mode/pesanan toko.
- Smoke HTTPS awal segera sesudah deploy sekali lagi mencatat React418 pada
  chat. Diagnostic ulang enam kombinasi ukuran/tema + history/form/entry PASS
  tanpa error; cache dokumen CF DYNAMIC. Penyebab belum teridentifikasi, jangan
  mengklaim hydration sudah diperbaiki. Source chat baru/fill ditest fixture
  seluruhnya tanpa pageerror. Bila berulang di penggunaan nyata, simpan fase
  document/theme/history/form-return untuk melokalisasi, bukan menonaktifkan guard.
- Pembandingan origin memakai image final dan API production read-only juga
  enam kombinasi tema/ukuran + navigasi PASS tanpa pageerror. Semua preview,
  DB/Redis/network QA task ini dan modul /tmp di container aktif dibersihkan.

## ARSIP — revisi chat biasa, live 4 Oktober 2026

- Permintaan Ivan: percakapan jangan textbook, seperti chat biasa. Source
  **cdcc2ec** live, satu kolom dengan user bubble kanan, asisten kiri dan composer
  di bawah. Riwayat via dialog tombol; kartu HPP kecil, Lihat resep membuka review
  dan approval. Tidak mengembalikan dropdown/permanent side preview lama.
- Textarea auto-grow 56–160px; Enter kirim, Shift+Enter newline, IME guard.
  Boleh mengetik koreksi saat pending; kirim disabled. Retry lama tidak menghapus
  koreksi baru. Preview/error/unsent/pending dan replacement confirmation tetap
  mengunci approval. Dialog native Tab/Shift+Tab/Escape/focus return teruji.
- Prompt aku/kamu, singkat, satu pertanyaan, tanpa daftar langkah, istilah form
  berulang atau HPP hasil model. Gunakan nama menu dari cerita, tidak meminta
  istilah nama produk formal. Balasan historis tidak diubah. Tidak ada streaming
  token; async POST202/poll GET seperti sebelumnya.
- Backend hanya SYSTEM prompt di hpp_setup_service.py. Rumus/worker/schema/API/
  RLS/stock tidak diubah. Migration112, APK1.6.31+198 tetap. Docker cp satu file
  + restart existing setelah active_hpp_jobs=0; jangan recreate backend.
  Backup `/tmp/selaris-hpp-modern-backup`. Frontend compose up --no-deps.
- Image tested/aktif
  `sha256:42f83214fedffb4ca5451374022b47ac36922131903c23e22ce7da050aa4f4de`,
  frontend Created2026-10-04T16:44:12Z, kedua mount APK tetap. Keempat layanan
  running/healthy setelah deploy.
- QA build/TypeScript, chat browser five widths/two themes AA/44px/200%/short
  viewport/keyboard/dialog, long50k input, sources/precision/resume/history,
  approval/replacement/unsent/409/500/pending GET/retry-preserves-correction PASS.
  Screenshot setelah transisi sidebar settle; sebelumnya foto sempat menangkap
  sidebar di tengah transisi, bukan menu benar-benar terbuka. Source UI unchanged
  setelah build final; perubahan test menunggu transform selesai.
- Math15/500 oracle/protocol PASS; configured provider manual batch1500,
  pack2x10→2000, per-kg75k→1500 dan labeled estimates PASS. Dua turn nyata:
  tanya pelengkap nasi ayam penyet, tawarkan Estimasi saat bingung, Manual tetap
  incomplete tanpa data nyata. Awal provider sempat meminta nama Nasi ulang;
  prompt pengenalan nama diperjelas lalu uji ulang lolos.
- Regresi form HPP, Bahan Baku, auth dan stock/storefront PASS. Runner storefront
  memakai CHROMIUM_PATH (bukan CHROMIUM_EXECUTABLE); salah env awal meninggalkan
  fixture8185, hanya proses tes tersebut dihentikan lalu rerun benar PASS.
- HTTPS actual: endpoint200, single-column/manual/estimate, riwayat/refresh/form
  navigation, entry HPP dan Bahan Baku, 320/768/1440 kedua tema PASS. Tidak write
  setup/bahan/resep/harga/stok/mode/pesanan merchant. First smoke mencatat sekali
  React418 hydration tanpa lokasi; rerun diagnostic menangkap URL+stack jika error
  tetapi semua alur selesai bersih. Penyebab tidak teridentifikasi, tidak mengubah
  source secara spekulatif. Bila berulang, telusuri HTML/chunks/theme di navigasi
  aktual sebelum mengaitkan ke chat. Semua fixture browser bersih tanpa pageerror.
- Review/gate `docs/HPP_CONVERSATION_REVIEW.md`, log/screens `/tmp/selaris-hpp-modern-*`.
  Simpan guard URL idle + href berbeda; jangan no-op replaceState atau update di
  tengah create→send. Catatan backend implementation awal di bawah masih berlaku.

## ARSIP — setup HPP percakapan awal, 4 Oktober 2026

- Ivan mengizinkan implementasi langsung dan mewajibkan rumus backend; source
  `a94dd85` + fix `360b049` dipush main dan dipasang. Web Atur HPP → Atur lewat percakapan,
  `/dashboard/hpp/chat`; entry juga dari Bahan Baku. Manual/Estimasi sama-sama
  chat, sumber dan kutipan per field, koreksi serta review/approve revisi terakhir.
  Form manual tetap. Jangan kembali ke status "masih diskusi" di arsip bawah.
- AI tidak menghitung total: `hpp_math.py` + Decimal/helper `unit_utils.py`
  untuk harga per unit × pembelian, kemasan, satuan, batch/porsi dan HPP. Harga
  existing weighted cost dipakai; update nyata harus diminta/diapprove. Manual
  tidak menerima tebakan. Estimasi tetap flag resep/editor/laporan setelah approve.
- Migration **112** live: FORCE RLS session/turn, recipe.is_estimated dan cost
  Numeric(18,8). Quantity/quantity_unit resep canonical ingredient.base_unit.
  Purchasing bahan 8 desimal, produk 2. Stock paths raw existing unchanged.
- History/draft durable Postgres, input 100k karakter; output 8192/16384 schema
  repair, tanpa kuota harian ordinary chat. Model window boleh memangkas turn
  lama/katalog, cerita terbaru dan draft terakhir beserta angka/units/sumber/
  kutipan/catatan tetap utuh. Semua turn untuk validasi sumber tetap tersedia.
- POST messages 202 + own-session BackgroundTasks tenant scope, lepas transaksi
  saat model, polling GET 2,5 detik. Lease 8 menit/retry UUID sama, local draft
  text. Jangan update URL/history di tengah create→send Server Action; pernah
  membuat queue macet. URL hanya diperbarui jika href berubah; no-op replaceState
  sesudah refresh juga pernah menahan link ke form. Tes refresh→form→chat ditambah.
  Resize riwayat mengikuti pesan terakhir; textarea 10rem
  perlu selector sesudah rule merchant-shell yang menimpa min-height form.
- Approval revision/fingerprint/session+brand locks, dependency conflict 409
  memperbarui preview/revisi untuk review lagi. Repeat hasil sama; concurrent
  nama bahan reuse. Satu commit bahan/resep/hasil/KG/audit/event, rollback bila
  final flush gagal; tidak helper audit commit. Versi resep dari seluruh history.
- Tidak write stok fisik/OutletStock/restock/mode. Menu baru nonaktif; pengguna
  atur harga jual/aktifkan di Menu. Gas/gaji/sewa belum dialokasikan ke HPP bahan.
  Retrieval KG/pgvector scoped/savepoint dan cache brand outlet setelah approve.
  Flow legacy `/ai/chat` dan APK tidak diganti. Provider error internal disaring.
- QA final: math 15/500 oracle, actual PostgreSQL RLS + POS/order/cancel/storefront,
  durable 12 turn/50k cerita/correction/replay/repeat/concurrent/conflict/atomic
  rollback/provider fail/HTTP202+fresh worker; configured provider draft-only
  batch/per-unit-price/pack contents + labeled estimates. Chat browser, HPP manual,
  inventory, auth dan stock/storefront semua lolos image final. Browser AA/44px,
  lima lebar dua tema/keyboard/200%/viewport pendek/pending polling GET-only.
- Deployed image `sha256:5fcc63cc7be259229df771488cfc30c0bc19146df25ff0381bbd18bd91be8ffb`,
  container frontend Created 2026-10-04T16:05:31Z, sesuai image final QA.
  Backend docker cp file terarah, alembic112, restart existing; tidak recreate
  backend karena hotfix sebelumnya harus dipertahankan. Source backup sebelum
  deploy `/tmp/selaris-hpp-deploy-backup`. Frontend-only compose --no-deps;
  APK mounts/native1.6.31+198 unchanged. Empat layanan healthy.
- Smoke HTTPS actual: endpoint session list 200 dengan header tenant wajib;
  chat kosong/mode/refresh/form links serta entry HPP/Bahan Baku, 320/768/1440
  kedua tema, tinggi textarea/no overflow/page errors PASS. Form manual membaca
  13 produk × tiga lebar × dua tema; inventory form kosong/cancel dan storefront
  menu/cart kedua tema 320 px juga PASS. Tidak write setup/bahan/resep/stok/mode/
  pesanan merchant. Alert diperiksa scoped workspace; router live-region kosong
  bukan error aplikasi. Semua fixture/temp QA container dibersihkan setelah tes.
- Review/gate `docs/HPP_CHAT_REVIEW.md`, tests `hpp-{math,setup-isolated,provider-smoke,chat-browser}`.
  Evidence log/screenshot `/tmp/selaris-hpp-*`, bukan konten/data merchant.
  Progress ke Ivan tetap Indonesia; update Portugis yang keliru sudah dijelaskan.

## ARSIP — redesign, sync, Mode Stok dan storefront

### Diskusi berikutnya: setup HPP percakapan dengan approval manusia

- Setelah Bahan Baku live, Ivan ingin AI mengurus input/setup lewat chat sampai
  bahan/harga/takaran/resep siap. User hanya cerita, koreksi dan approve ringkasan;
  sebelum approve simpan sebagai draft, bukan menulis tabel operasional.
- Mode manual dan estimasi keduanya conversational. Jika user bingung takaran,
  AI menawarkan estimasi yang dapat diubah. Terima potong/batch/jumlah porsi,
  konversikan lewat helper. Field nyata dan estimasi bisa bercampur; sumber dan
  status estimasi tetap jelas. Stok fisik tidak ditebak dari ukuran kemasan.
- Arahan terakhir **jangan terlalu membatasi token di mode ini, cerita mereka
  bisa panjang**. Input/context/history perlu cukup ruang, output draft juga.
  Belum menentukan angka budget. Perlu percakapan/draft durable dan state angka,
  satuan, harga, asumsi serta koreksi yang tidak hilang ketika context diringkas.
- KG, pgvector dan event store memang ada. Setup existing di ai_service.py
  generate_recipe_proposal masih single-message max_tokens=1200 output + default
  harga/stock perkiraan; branch setup berhenti sebelum history/RAG normal chat.
  Chat history biasa Redis TTL30min/lima turn-pair. Apply-recipe existing memakai
  tombol Buat Resep; bukan workflow approval/draft durable yang baru diminta.
- Ini masih diskusi arah/requirements. Belum mengubah runtime, limit, backend,
  UI chat atau deployment. Checkpoint implementasi live tetap Bahan Baku di bawah.

### Update terbaru: Bahan Baku web, 4 Oktober 2026

- Ivan meminta Bahan Baku lebih user friendly. Source `6d91aac` sudah di main
  dan live. Antislop during sesi tetap, ENERGY 2 / RHYTHM 2 / MOTION 1; Source
  Sans 3 dan palet Sefrekuensi mengikuti Atur HPP.
- Route `/dashboard/bahan-baku` stock-first, search/filter dan counts aktual.
  Form Tambah bahan langsung kosong; input harga pembelian bukan stok. Save satu
  write, lalu Catat stok lewat modal terpisah. Restok = tambahan, dengan konversi
  dan projected stock. Ubah harga berlaku pada semua resep; pemakaian menampilkan
  produk/takaran. Bahan masih dipakai tidak bisa dihapus dari UI sampai dilepas.
- Bagian Biaya operasional terpisah: nama + estimasi harian, tanpa stok/pembelian.
  Belum dialokasikan ke modal bahan per porsi, jangan klaim sudah masuk HPP.
- Null stock bukan habis; cost desimal/server weighted cost bukan pembelian terakhir.
  Harga tetap row_version dan base_unit/unit_type existing; merge response tanpa
  stock/used_in harus menjaga nilai loaded. Unit baru kg/liter canonical gram/ml.
- Backend restock belum idempotent. Guard double-click dan uncertain 500/network
  wajib dipertahankan: reconcile dulu, tidak auto-replay write. Load transport
  error browser ditangkap, draft 400/422/409 dipertahankan. Dialog native punya
  manual Tab trap, Escape, dirty confirm dan focus return sesudah reconcile.
- Production build/TypeScript, backend unit oracle, inventory/HPP/auth/stock-
  storefront browser passed. Lima lebar dua tema AA/44px/placeholder, Tab/Shift+Tab,
  return focus, 200% text dan compressed viewport; API 400/422/409/500/401,
  browser network abort, pagination >100, simulated commit 500 tanpa stock ganda.
- Demo aktual 0 bahan; tidak diisi data palsu. Smoke HTTPS inventory tiga lebar
  dua tema dan HPP 13 produk × tiga lebar × dua tema serta storefront actual
  menu/cart 320 px dua tema passed. Tidak write bahan/resep/stok/mode/pesanan.
- Final/live image `sha256:c7b54e58aa043ab5633b1c6b7d183de764cdcc8e2a0f5f8b250b166c53daec9c`.
  Empat layanan healthy. Deploy frontend-only, APK 1.6.31+198/backend migration111
  unchanged. Review `docs/INGREDIENT_INVENTORY_REVIEW.md`; source tes baru
  `tests/ingredient-inventory-browser.cjs`; bukti `/tmp/selaris-inventory-*`.

### Update terbaru: alur HPP web, 4 Oktober 2026

- Ivan bingung mengisi HPP dan mengonfirmasi cakupan **web dashboard**. Source
  terbaru `4f7934c` sudah dipasang; code+tests dipush main. Image frontend final
  `sha256:73c25119aa34589be27584400504aed915ffc071792bf35690108a016d3fa0f6`.
- Buka `/dashboard/hpp` atau nav **Atur HPP**. Pilih produk, tambah/pilih bahan,
  harga + jumlah pembelian nyata, takaran satu porsi, review biaya, simpan resep,
  lalu pilih **Atur produk lain**. Pintu masuk tersedia dari Menu, Bahan Baku,
  Settings dan Laporan HPP. Tab Resep Menu memakai komponen yang sama.
- Harga pembelian bukan stok fisik. Recipe setup tidak restok dan tidak mengganti
  mode outlet. Setelah semua resep siap, pemilik mencatat stok nyata di Bahan Baku
  lalu beralih melalui Settings; backend guard tetap berlaku. Jangan mengarang
  data toko untuk melengkapi resep yang masih kurang.
- `lib/hpp.ts` mengikuti preview legacy backend `unit_utils.py`, sedangkan input
  baru disimpan dalam ingredient.base_unit. Stock deduct/display masih quantity
  mentah, maka quantity+unit harus canonical sebelum save. Resep lama berbeda unit
  perlu konfirmasi. Optional/catatan dipertahankan. Total server setelah save,
  refresh harga bahan, error aman/retry, guard draft dan row_version harga tersedia.
- UI menyatakan modal bahan belum termasuk biaya operasional. Preset bahan tidak
  mengisi harga/jumlah perkiraan. Bila restok awal gagal, pesan menyatakan bahan
  berhasil dibuat tetapi stok belum tersimpan, bukan mengaku stok sudah ada.
- Production build, TypeScript, unit oracle Python dan browser HPP lolos: lima
  lebar, kedua tema, AA/44 px/fokus/Escape, 200% teks, viewport pendek, optional,
  catatan, legacy review, harga 409, 400/422/500/401, retry, pagination dan entry.
  Regresi auth/onboarding, stok/storefront dan publik juga lolos. Smoke baca data
  demo aktual memeriksa 13 produk pada 320/768/1440 dalam kedua tema tanpa write.
  Laporan/gate `docs/HPP_FLOW_REVIEW.md`, log dan screenshot `/tmp/selaris-hpp-*`.
- Setelah deploy, smoke HTTPS HPP 13 produk × tiga lebar × dua tema dan menu/cart
  storefront aktual kedua tema 320 px lolos. Image frontend cocok dengan final;
  frontend/backend/Postgres/Redis healthy. Tidak ada write stok/resep/mode/pesanan.
- Backend tetap migration 111, APK POS/Dapur 1.6.31+198. Backlog HPP native masih
  memakai raw quantity dan menjumlah optional; jangan menyatakan sudah diperbaiki.
  Login Google masih menunggu empat konfigurasi Firebase pemilik.

### Update terbaru: revisi web premium, 4 Oktober 2026

- Source terbaru `2ca827f` pada main. Web sudah dipasang ke selaris.id memakai
  image `sha256:f2d69d2af62a12014564b871e16fc0a21c33eaa05a70b53db98fadc26c6e7b28`.
  Ini menggantikan snapshot frontend hotfix di bawah. Backend tetap migration 111.
- Arahan Ivan: web keseluruhan masih terlalu AI, khususnya tipografi dan copy
  nota. Revisi memakai antislop during dan dials ENERGY 2 / RHYTHM 2 / MOTION 1.
  Web kini Source Sans 3 + judul Source Serif 4; Space Mono hanya kode. Pilihan
  baru ini disengaja sesuai feedback terakhir, bukan kembali ke PJS web lama.
  Palet hangat/coral tetap mengikuti Sefrekuensi. Native tetap pada theme sendiri.
- Landing memakai screenshot web aktual toko demo existing (`public/app/web-*.png`).
  Nota dan angka pemasaran buatan serta screenshot palet lama dihapus dari
  tampilan landing. Copy nota: "Unggah nota, periksa hasilnya, lalu simpan pembelian."
  Header/menu/tema/footer/download seragam; auth/onboarding lebih tenang;
  dashboard pendapatan menjadi fokus; storefront HP berupa daftar dengan tombol
  44 px dan sheet Tab/Escape/fokus. Chat bantuan punya loading/error/retry.
- Kontras mengungkap benturan `--color-base` dengan kelas font `text-base`:
  kelas itu memberi warna latar pada teks. Token sekarang `--color-canvas`.
  Hindari nama alias warna yang sama dengan ukuran font Tailwind.
- Build produksi dan tiga browser regression lolos, termasuk laporan dashboard
  gagal/retry, data dan tabel harian. Preview data demo 16 route, 320/1440 px,
  light/dark (64 pembukaan route) HTTP 200, tanpa page error/overflow. Review dan
  full PASS gate di `docs/WEB_REFINEMENT_REVIEW.md`; screenshot/log tes di /tmp.
- Hanya frontend direcreate. Tidak membuat pesanan, mengirim OTP/WA, mengganti
  stok/resep atau memproses pembayaran. APK tetap POS/Dapur 1.6.31+198.
  Google masih belum aktif karena empat konfigurasi Firebase belum diisi.
  Langkah Google dan HPP serta temuan native di bawah tetap berlaku.
- Setelah deploy, tes publik lengkap lewat HTTPS, direktori data aktual,
  auth/dashboard/onboarding demo dan menu/cart dua tema lolos tanpa page error.
  Semua container healthy; image deployment sama dengan yang diuji.

### Snapshot pekerjaan sebelumnya

- Workspace `/var/www/kasira`, branch `main`, domain `https://selaris.id`.
  Kode terakhir dipush pada commit `20f79cc` (Mode Stok + storefront). Checkpoint
  memory sesudahnya hanya mengubah dokumentasi. Cek status Git sebelum edit.
- Ivan menyatakan semua toko demo dan mengizinkan perubahan/deploy langsung.
  Arah desain mengikuti source Sefrekuensi 2.0 di `/var/www/sefrekuensi` karena
  kedua produk direncanakan bergabung. Referensi warna/font ada di MEMORY.
  Penyatuan database kedua produk belum diimplementasikan.
- Login/register/onboarding web dan welcome/login POS sudah mengikuti palet
  Sefrekuensi. OTP Sefrekuensi terhubung. Google sudah ada di kode, tetapi belum
  aktif karena konfigurasi Firebase belum diisi; jangan menyatakan sudah live.
- Backend migration `111`; backend/frontend/Postgres/Redis healthy pada
  pemeriksaan setelah deploy 4 Oktober. Frontend produksi identik dengan image
  yang diuji: `sha256:29457819bac7594368c2cf368aabe1d9bc0e2e1ea57a94687b544555fbd9ba7a`.
  Ini snapshot terakhir; verifikasi keadaan aktual lagi pada pekerjaan berikut.
- APK/AAB POS dan Dapur terbaru `1.6.31+198`, CI run `37199747458`, source fix
  `7740bd1`. APK publik sudah dipasang dan signing Selaris + Firebase push
  diverifikasi. URL unduhan `/api/download/pos` dan `/api/download/dapur`.
  Update dari 1.6.30 langsung ditimpa tanpa uninstall atau reset data offline.

## PERBAIKAN YANG SUDAH SELESAI

1. CRDT sync: DP reservasi tanpa `order_id` menyebabkan TypeError pada cache
   PaymentLocal lalu rollback seluruh apply meski API HTTP 200. Backend pull
   mengecualikan DP standalone; Flutter juga mengabaikannya. DP tetap di server.
   Pagination client/server juga diperbaiki, termasuk watermark server setelah
   semua halaman berhasil dan backfill satu kali untuk instalasi lama.
2. Mode Stok web: error produksi digest `1800943633` berasal dari validasi
   "Belum punya resep: Egg Tart, Kopi susu" yang dilempar Server Action.
   `app/actions/api.ts:updateStockMode` sekarang mengembalikan success/error
   sebagai data. Settings menampilkan pesan + link persiapan, menjaga mode lama
   saat gagal, dan mengunci input selama menyimpan. Bahan Baku tersedia untuk
   Pro saat mode simple agar resep bisa disiapkan sebelum beralih.
3. Storefront dark: tombol/teks inverse memakai pasangan token, input fokus
   memakai surface-card, warna booking lama dijembatani dalam scope khusus,
   status order/reservasi/COD tidak lagi putih di atas putih. Baris harga dan
   kontrol jumlah membungkus agar tombol tidak terpotong pada layar 320 px.
   Hotfix ini hanya web; tidak memerlukan rilis APK baru.

## NEXT ACTION — mulai dari sini sesuai permintaan Ivan berikutnya

- Jika melanjutkan aktivasi mode HPP: Egg Tart dan Kopi susu perlu resep lengkap.
  Alur pemilik kini: Dashboard → Atur HPP → pilih produk → bahan/harga/takaran
  satu porsi → simpan → atur produk lain → stok fisik Bahan Baku → Pengaturan
  → beralih ke Resep & HPP. Validasi backend tetap berlaku. Belum ada
  perubahan otomatis pada mode outlet/resep; jangan mengarang resep atau stok.
- Jika melanjutkan Google: gunakan `docs/GOOGLE_LOGIN.md`. Empat nilai
  `GOOGLE_FIREBASE_PROJECT_ID`, `GOOGLE_FIREBASE_WEB_API_KEY`,
  `GOOGLE_FIREBASE_AUTH_DOMAIN`, `GOOGLE_FIREBASE_WEB_APP_ID` belum diisi pemilik.
  Daftarkan `com.selaris.pos` dan `com.selaris.dapur` beserta fingerprint yang
  tercatat di dokumen, perbarui google-services.json/secret CI, lalu build APK
  baru. Pertahankan project/kredensial FCM yang cocok untuk notifikasi.
- Temuan terpisah, belum diperbaiki: HPP native di
  `kasir_app/lib/features/products/providers/recipe_provider.dart` masih
  memakai quantity mentah × costPerBaseUnit dan menghitung bahan optional.
  Backend memakai `backend/services/unit_utils.py`, mengecualikan kontribusi
  optional/satuan tidak cocok. Periksa dan samakan kontrak bila pekerjaan
  berikutnya menyentuh HPP native. Ini terpisah dari error perpindahan mode.
- Redesign tahap berikutnya mengikuti arah Sefrekuensi dan scope baru dari Ivan;
  integrasi Google sungguhan/penyatuan database belum diuji atau selesai.

## BUKTI DAN CATATAN OPERASIONAL

- `tests/stock-storefront-browser.cjs`: lolos terhadap image production dengan
  API fixture, validasi 400/422, 500 aman, sesi 401, retry/pindah dua arah;
  light/dark 320/768/1440, varian/Escape, meja, input fokus, tujuh fase order,
  tiga fase reservasi, booking dan COD kurir. Tidak mengirim transaksi/WA nyata.
- Smoke HTTPS toko aktual `kasira-coffee` light/dark 320 px lolos: menu/cart,
  persistensi tema, kategori terpilih dan input fokus; tanpa page error.
  Log sesi: `/tmp/selaris-stock-storefront-test-final.log` dan
  `/tmp/selaris-storefront-live-check.log`. Container fixture sudah dibersihkan.
- Sync: 14 unit backend dan 14 tes Flutter lolos; fixture aktual 68 halaman
  mencakup seluruh ID full pull, termasuk 522 order_items. Detail ada di MEMORY
  dan ARCHITECTURE. Fixture `/tmp/selaris-sync-pages.json` bersifat sementara.
- Laporan desain: `docs/REDESIGN_REVIEW.md`. Pilihan antislop sesi ini `during`;
  ini catatan pilihan sesi, bukan preferensi global.
- Baca ARCHITECTURE penuh sebelum mengubah stock/recipe/sync. Konversi satuan
  HPP tidak boleh langsung diterapkan ke pengurangan/display stok raw quantity.
  Query audit standalone perlu `SET LOCAL app.current_tenant_id = ''` untuk RLS.
- Deploy layanan sendiri dengan build image lalu `compose up -d --no-deps`.
  Backend source tidak bind-mounted. VPS dibagi dengan Sefrekuensi; jangan
  restart daemon Docker atau layanan produk lain untuk deploy Selaris.
- Update APK membaca version.json dari Git main: jangan mengumumkan versi baru
  sebelum artifact signed tersedia. Cocokkan source CI, signing/package/FCM,
  lalu pasang APK publik dan metadata produksi. Backup APK 1.6.30 ada di
  `/tmp/selaris-apk-before-1.6.31`; backup DB sebelum redesign ada di
  `/tmp/selaris-before-redesign-20261004.dump`. Jangan tulis token/PIN ke memory.

## ARSIP APRIL 2026

Catatan berikut dipertahankan sebagai riwayat. Versi aplikasi, alamat, status
deploy, akun contoh dan NEXT ACTION lama di bawah tidak menjadi acuan terkini.

## ✅ SELESAI SESI INI (update terakhir)
- [x] Fix upload gambar: pipe raw body (jangan parse FormData), gunakan BACKEND_INTERNAL_URL=http://backend:8000
- [x] Fix ProductResponse: tambah computed_field price=base_price dan stock=stock_qty untuk Flutter & storefront
- [x] Fix read_products: brand_id sekarang Optional — infer dari tenant user saat Flutter tidak kirim brand_id
- [x] Fix fetchWithAuth: auto trailing-slash normalization (hindari 307 yang drop Authorization header)
- [x] **Fix 500 error products.py** — tambah `from datetime import datetime, timezone` (dipakai di update_product), hapus `from datetime import` duplikat di delete_product
- [x] **Fix audit log tidak tersimpan** — tambah `await db.commit()` setelah setiap `log_audit()` di products.py + categories.py
- [x] **Rebuild backend container** — container lama masih run kode dengan `request_id` di `log_audit()` yang menyebabkan TypeError → 500

## ✅ SELESAI SESI INI
- [x] VPS live: semua container running (backend 8000, frontend 3000, db, redis)
- [x] Feature F: FASE 5 Pre-Pilot (Sentry, R2 APK upload, env.example, kasira-setup.sh)
- [x] Tier Gating, CRDT Stock, Event-Sourced Stock, Offline-First PNCounter (sesi sebelumnya)
- [x] **Owner Dashboard — Kategori CRUD** (tab Kategori di menu/page.tsx)
  - Tambah/edit/hapus kategori, toggle aktif/non-aktif
  - Fix getCategories: outlet_id → brand_id
  - Fix categories.py: hapus `request_id` dari log_audit()
- [x] **Owner Dashboard — Produk CRUD Lengkap**
  - Tambah tombol hapus produk (soft delete)
  - Fix field names: price→base_price, stock→stock_qty, outlet_id→brand_id
  - Fix getProducts: pakai brand_id, trailing slash
  - Fix toggleProductActive: kirim row_version
  - Fix updateProduct: kirim row_version
- [x] **Fix 307 Redirect Bug** — `fetchWithAuth` sekarang normalize trailing slash otomatis
  - Semua GET yang kena redirect (outlets, categories, products) sekarang langsung benar
- [x] **Upload Foto Produk dari Device**
  - Backend: `backend/api/routes/media.py` — POST /media/upload (auth required, max 5MB)
  - Backend: `main.py` — mount StaticFiles /uploads/ → /app/uploads/
  - Backend: `api.py` — include media router
  - `docker-compose.yml` — tambah volume uploads_data:/app/uploads
  - Next.js: `app/api/upload/route.ts` — proxy upload (baca httpOnly cookie server-side)
  - UI: file picker + preview + ganti/hapus foto
- [x] **Fix event.py SQLAlchemy error** — kolom `metadata` reserved, rename ke `event_metadata`

---

## STATUS VPS

| Service | Status | Port |
|---------|--------|------|
| Backend (FastAPI) | ✅ Running | 8000 |
| Frontend (Next.js) | ✅ Running | 3000 |
| PostgreSQL | ✅ Running | 5432 |
| Redis | ✅ Running | 6379 |

**Admin**: phone `6285270782220`, OTP dev `123456`, PIN `111222`
**Outlet slug**: `kasira-coffee`
**Dashboard**: http://103.189.235.164:3000/dashboard/menu

---

## ✅ SELESAI SESI INI (dashboard + storefront sync fix)
- [x] **Fix storefront tampil mock data** — `storefront.ts` pakai `BACKEND_INTERNAL_URL` (bukan `NEXT_PUBLIC_API_URL`), hapus semua mock fallback, tambah null guard untuk slug
- [x] **Fix slug undefined** — tambah `if (!slug) return` di useEffect `[slug]/page.tsx`
- [x] Rebuild frontend container — hapus cached bundle lama
- [x] **Fix dashboard storefront link = "undefined"** — tambah `slug`, `is_open`, `opening_hours` ke `OutletInDBBase` schema (belum ada sebelumnya)
- [x] **Fix settings outlet tidak bisa save** — tambah endpoint `PUT /outlets/{id}` (belum ada), fix `OutletUpdate` schema
- [x] **Fix log_audit request_id kwarg di outlets.py** → sama seperti products.py sebelumnya
- [x] **Fix teks "QRIS Midtrans" → "QRIS Xendit"** di settings/page.tsx
- [x] **Fix connect endpoint** — tambah `slug` ke outlet response, flush Redis cache
- [x] **Cover image storefront** — migration 060 `cover_image_url` di outlets, upload dari settings, tampil di storefront hero
- [x] **Fix settings save error** — settings page di-rewrite: form sekarang kirim `cover_image_url`, `opening_hours` handle string JSONB, error message lebih jelas
- [x] **Hapus tombol Reservasi dari storefront** — fitur Pro, tidak boleh ada di Starter tier

---

## ✅ SELESAI SESI INI (pro teaser + kasir bug fix)
- [x] **Fix Kelola Kasir — semua endpoint backend dibuat**
  - `GET /users/` — list kasir (non-superuser) per tenant
  - `POST /users/cashier` — tambah kasir baru (owner only, validasi phone 628, PIN 6 digit)
  - `PUT /users/{id}/status` — toggle aktif/nonaktif
  - `PUT /users/{id}/pin` — reset PIN kasir
  - Semua endpoint: audit log + tenant isolation
- [x] **Pro Features Teaser**
  - `app/dashboard/pro/page.tsx` — 6 feature cards (Reservasi, AI Chatbot, Loyalty, Tab/Bon, Multi-Outlet, Laporan Lanjutan), card grayscale+overlay, badge PRO kuning, tombol CTA ke WA
  - `app/dashboard/layout.tsx` — nav item "Fitur Pro" dengan Lock icon + PRO badge di sidebar
- [x] Rebuild backend + frontend image dan container

## ✅ SELESAI SESI INI (bug fix kasir + laporan)
- [x] **Fix Kelola Kasir — cashier.name → cashier.full_name** (crash saat render list)
- [x] **Fix Kelola Kasir — error message** dari backend pakai `data.detail`, bukan `data.message` → sekarang `data.message || data.detail`
- [x] **Fix Laporan — orders date filter** — backend `GET /orders/` tambah `start_date` & `end_date` query params
- [x] **Fix Laporan — reports date param** — backend `GET /reports/daily` tambah `report_date` param (sebelumnya selalu return hari ini), frontend kirim `report_date` bukan `date`
- [x] Rebuild backend + frontend container

## ✅ SELESAI SESI INI (auth bug fixes - 2026-04-04)
- [x] **Fix Dashboard login tidak bisa masuk** — root cause: `fetchWithAuth` tambah trailing slash `/users/me/` → FastAPI 307 redirect → Node.js fetch drop Authorization header → 401 → redirect balik ke login
  - `app/actions/api.ts`: Ganti ke `BACKEND_INTERNAL_URL` (http://backend:8000) untuk server actions
  - `app/actions/api.ts`: Tambah `redirect: 'manual'` + manual follow 307/308 dengan headers preserved
  - `app/actions/api.ts`: Trailing slash normalization sekarang skip untuk endpoints resource (/me, /status, /pin, dll)
  - Rebuild & restart frontend container ✅
- [x] **Fix Flutter APK SharedPreferences URL lama** — jika user install APK baru tapi SharedPreferences masih simpan `http://` URL lama, sekarang diabaikan dan pakai `defaultBaseUrl` (https://kasira.online)
  - `kasir_app/lib/core/config/app_config.dart`: Hanya load saved URL jika startsWith('https://')

## ✅ SELESAI SESI INI (2026-04-09) — Realtime Sync + Order Bug Fix

### Bug Fix 1: Data penjualan tidak realtime sync ke dashboard/laporan
- [x] `cart_panel.dart`: tambah `ref.invalidate(dashboardProvider/ordersProvider/productsProvider)` setelah payment sukses
- [x] `pos_page.dart`: invalidate semua provider setelah offline→online sync selesai
- [x] `payment_success_page.dart`: convert ke `ConsumerStatefulWidget`, invalidate saat navigasi ke dashboard
- **Efek:** Dashboard stats, order list, stock produk langsung update tanpa manual refresh

### Bug Fix 2: Order >1 item crash 500 (CRITICAL)
- [x] `orders.py`: ganti `selectinload(Order.items).joinedload(OrderItem.product)` → `selectinload().selectinload()` — joinedload trigger lazy load di async context → MissingGreenlet error
- [x] `stock_service.py`: fix `metadata=` → `event_metadata=` (field name salah setelah rename, metadata stock event tidak tersimpan ke DB)
- [x] Backend di-restart via `docker cp` + `docker restart`
- [x] Tested: order 2 item + cash payment → sukses
- **Commits:** `3358b34` (realtime sync) + `adf20a9` (order fix) — pushed to `origin/main`

### Juga di commit ini (minor):
- [x] `page.tsx` landing page: hapus kata "pilot" dari CTA copy

---

## ✅ SELESAI SESI INI (2026-04-09) — Register Fix + AI Chatbot Pro

### Fix Register Flow
- [x] Backend `otp/send`: tambah `purpose` param — `register` skip cek user exists, tolak jika nomor sudah terdaftar
- [x] `backend/schemas/auth.py`: tambah `purpose: Optional[Literal["login","register"]]` di OTPSendRequest
- [x] `app/actions/auth.ts`: `sendOtp()` terima param `purpose`, pakai `BACKEND_INTERNAL_URL` (bukan NEXT_PUBLIC)
- [x] `app/register/page.tsx`: kirim `purpose: 'register'` saat sendOtp
- [x] Deploy backend (docker cp + restart) + rebuild frontend

### AI Chatbot Owner (Pro Feature)
- [x] **Chat UI**: `app/dashboard/ai/page.tsx` — full chat interface, suggestion buttons, SSE streaming, model+token info
- [x] **SSE Proxy**: `app/api/ai/route.ts` — Next.js API route proxy ke backend (handle httpOnly cookie auth)
- [x] **Outlet Helper**: `app/api/ai/outlet/route.ts` — expose outlet_id dari httpOnly cookie ke client
- [x] **Sidebar Nav**: `app/dashboard/layout.tsx` — tambah "AI Asisten" dengan Bot icon + PRO badge (purple theme)
- [x] **Pro Tier Gate**: `backend/api/routes/ai.py` — query tenant.subscription_tier, 403 jika bukan Pro+
- [x] **Tenant Model Sync**: container tenant.py tidak punya subscription_tier — docker cp fix
- [x] **Tested**: Starter → 403 ditolak. Pro → stream OK (error karena ANTHROPIC_API_KEY placeholder)
- [x] Admin tenant di-upgrade ke `pro` di DB untuk testing
- **Backend AI service sudah ada sebelumnya**: `ai_service.py` (intent classifier, context builder, SSE stream, model selector)

### IdCloudHost Issue
- VPS semua service **online** (backend, frontend, db, redis, nginx, SSL valid)
- Tapi akses publik **timeout** — masalah di jaringan IdCloudHost, bukan server
- Backup lengkap dibuat: `/root/kasira-backup-20260409.tar.gz` (DB + uploads + .env)

---

## ✅ SELESAI SESI INI (2026-04-09) — Tab/Bon + Split Bill (Pro Feature)

### Backend
- [x] Migration 062: `tabs` + `tab_splits` tables + `orders.tab_id` FK
- [x] Models: `backend/models/tab.py` — Tab + TabSplit (row_version, relationships)
- [x] Schemas: `backend/schemas/tab.py` — full CRUD + split bill schemas
- [x] Routes: `backend/api/routes/tabs.py` — 10 endpoints (open, list, detail, add order, split equal/per-item/custom, pay full, pay split, cancel)
- [x] `backend/api/api.py` — include tabs router
- [x] `backend/models/order.py` — tambah tab_id FK + relationship
- [x] Pro tier gate via `require_pro_tier` dependency
- [x] Migration deployed + backend restarted in container

### Split Bill Options
1. **Bayar semua** — 1 orang bayar total (`/tabs/{id}/pay-full`)
2. **Split rata** — total ÷ jumlah orang (`/tabs/{id}/split/equal`)
3. **Split per item** — assign item ke orang, bayar masing-masing (`/tabs/{id}/split/per-item`)
4. **Split custom** — kasir input nominal per orang (`/tabs/{id}/split/custom`)
5. Setiap split bisa bayar dengan metode berbeda (cash/QRIS)

### Flutter Kasir UI
- [x] `features/tabs/providers/tab_provider.dart` — TabNotifier + TabModel + TabSplitModel (Riverpod)
- [x] `features/tabs/presentation/pages/tab_list_page.dart` — list tabs, filter aktif/selesai, buka tab baru
- [x] `features/tabs/presentation/pages/tab_detail_page.dart` — detail tab, list splits, bayar per split
- [x] `features/tabs/presentation/widgets/open_tab_modal.dart` — form buka tab (nama tamu, jumlah tamu)
- [x] `features/tabs/presentation/widgets/split_bill_modal.dart` — pilih metode (bagi rata/custom), input jumlah orang
- [x] `features/tabs/presentation/widgets/pay_split_modal.dart` — bayar per orang (cash/QRIS), hitung kembalian
- [x] `main.dart` — GoRouter /tabs + /tabs/:tabId
- [x] `dashboard_page.dart` — tombol "Tab / Bon" di header dashboard

### ANTHROPIC_API_KEY
- [x] Key di-set di `.env`, backend rebuilt

---

## ✅ SELESAI SESI INI (2026-04-10) — Deep Bug Fix Starter Production-Ready

### CRITICAL FIX 1: Dashboard Login Gagal
- [x] `config.py`: tambah `MASTER_OTP` setting (configurable, bukan hardcoded "123456")
- [x] `auth.py`: OTP verify + register → pakai `settings.MASTER_OTP`, decode bytes safety
- [x] `.env`: tambah `MASTER_OTP=123456` + `BACKEND_INTERNAL_URL=http://backend:8000`
- **Root cause**: ENVIRONMENT=production block hardcoded dev OTP "123456", BACKEND_INTERNAL_URL tidak di-set

### CRITICAL FIX 2: Riwayat Kas Tidak Sinkron
- [x] `schemas/shift.py`: tambah `CashPaymentSummary`, `ShiftWithActivitiesResponse` sekarang include `cash_payments`, `total_cash_sales`, `total_qris_sales`
- [x] `shifts.py`: `_enrich_shift_with_payments()` — query Payment linked ke shift, return display_number + net amount
- [x] `shifts.py`: GET `/shifts/{id}/activities` sekarang return `{activities, cash_payments}`
- [x] `shift_page.dart`: tampilkan Penjualan Cash, QRIS, Penerimaan Lainnya, Pengeluaran di tutup shift
- [x] `cash_drawer_history_page.dart`: merge CashActivity + Payment transactions, sorted by time
- **Root cause**: shift activities cuma CashActivity, payment transactions tidak termasuk

### CRITICAL FIX 3: Connect Order — Stock Event + Audit Log
- [x] `connect.py`: stok deduction sekarang via `deduct_stock()` service (event-sourced, Golden Rule #8)
- [x] `connect.py`: tambah `log_audit()` setelah order commit (Golden Rule #2)
- [x] `connect.py`: restructure flow — create order dulu, deduct stock dengan order_id

### HIGH FIX 4: Flutter Online Order Missing shift_session_id
- [x] `cart_provider.dart`: `_submitOnline()` sekarang baca `shift_session_id` dari SecureStorage, kirim ke backend

### HIGH FIX 5: Connect Bugs
- [x] `connect.py`: `Table.is_active == 'true'` → `True` (boolean)
- [x] `connect.py`: idempotency key scoped ke outlet (JOIN ConnectOutlet)
- [x] `connect.py`: `datetime.datetime.utcnow()` → `datetime.datetime.now(datetime.timezone.utc)`

### HIGH FIX 6: Double Commits
- [x] `categories.py`: 3 endpoint (create/update/delete) — hapus double commit, pakai flush+commit
- [x] `products.py`: 4 endpoint (create/update/delete/restock) — hapus double commit

### MEDIUM FIX 7: Reports
- [x] `reports.py`: tambah `end_of_day` boundary (sebelumnya cuma `>= start_of_day`, bisa bocor next day)
- [x] `reports.py`: tambah `Product.deleted_at.is_(None)` di top_products join
- [x] `reports.py`: tambah `Payment.deleted_at.is_(None)` di semua subquery

### OTHER
- [x] `payments.py`: `asyncio.create_task()` WA receipt wrapped in try/except (fire-and-forget safety)

---

## ✅ SELESAI SESI INI (2026-04-10) — Production Hardening + SEO

### Deploy & E2E Test
- [x] Semua fix deployed ke container (backend + frontend rebuilt)
- [x] **E2E Test 1 (API)**: 14/14 PASS — register, login, shift, order, payment, stock, audit
- [x] **E2E Test 2 (Dita Coffee real merchant)**: 20/25 PASS — 5 fail = test script bukan bug
- [x] MASTER_OTP dihapus dari .env — OTP hanya via WA Fonnte (production mode)
- [x] APK v1.1.0 built + published di GitHub Releases

### Production Hardening
- [x] **Payment reconciliation**: asyncio background task, auto-expire pending QRIS >10 min (Rule #38)
- [x] **OTP verify rate limit**: max 5 attempts/15min per phone (brute-force protection)
- [x] **APK version endpoint**: reads from version.json (auto-update via GitHub Actions, Rule #14)
- [x] **Tenant model ENUM**: subscription_tier/status pakai PostgreSQL ENUM (fix register crash)
- [x] **Audit log auto-commit**: log_audit() sekarang commit sendiri (fix missing audit entries)
- [x] **Product MissingGreenlet**: selectinload(category) on create/update/restock
- [x] **Storefront cache invalidation**: Redis cache di-invalidate saat stock berubah

### SEO Landing Page
- [x] Full metadata: OG, Twitter Card, canonical, keywords, robots directive
- [x] Dynamic OG image 1200x630 (logo + tagline + value props)
- [x] Dynamic favicon 32x32
- [x] robots.ts: allow /, block /dashboard/ /api/ /onboarding/
- [x] sitemap.xml: homepage, login, register
- [x] JSON-LD structured data (SoftwareApplication schema)

### Git Commits (10 total hari ini)
- `c89f01b` — 15 bug fixes (login, shift, connect, reports)
- `9883770` — auth.ts double path, config extra=ignore
- `951ed5f` — payment reconciliation + rate limit + APK version
- `7b834dd` — tenant ENUM + audit auto-commit
- `decd9c7` — product MissingGreenlet fix
- `e334ab9` — storefront cache invalidation
- `a9b6ba5` — complete SEO setup

---

## ✅ SELESAI SESI INI (2026-04-11) — Dashboard-Kasir Sync Fix

### Bug: Data penjualan kasir tidak muncul di dashboard owner
- [x] **Fix dashboard `page.tsx`** — field names salah: `total_revenue` → `revenue_today`, `total_orders` → `order_count`
- [x] **Fix `laporan/page.tsx`** — pakai `report.payment_breakdown` dari API (bukan hitung dari `o.payment_method` yang tidak ada di OrderResponse)
- [x] **Fix `getWeeklyRevenue`** — `json.data?.total_revenue` → `json.data?.revenue_today` (chart 7 hari selalu 0)
- [x] **Fix `reports.py`** — tambah `active_shifts` (count shift open) + `critical_stock_items` (stock ≤ threshold) di response
- [x] **Fix `orders.py` + `order.py` schema** — tambah `payment_method` + `payment_status` di OrderResponse (join Payment table), supaya tabel riwayat transaksi tampil metode pembayaran
- [x] Backend deployed (docker cp + restart), frontend rebuilt + recreated

---

## ✅ SELESAI SESI INI (2026-04-11) — Reservasi Pro Feature

### Backend
- [x] Migration 064: `reservation_settings` table, upgrade `reservations` (new columns), `tables.floor_section`
- [x] Models: `Reservation`, `ReservationSettings`, `Table` (updated)
- [x] Schemas: full CRUD + storefront schemas
- [x] Routes `reservations.py`: 10 endpoints (CRUD + confirm/seat/complete/cancel/no-show + settings)
- [x] Routes `tables.py`: CRUD meja (create/update/delete + floor section)
- [x] Routes `connect.py`: public storefront `GET /connect/{slug}/reservation/slots` + `POST /connect/{slug}/reservation`
- [x] Auto-assign table logic (smallest capacity that fits, no time conflict)
- [x] WA notification via Fonnte (konfirmasi + cancel)
- [x] Pro tier gate (`require_pro_tier`)

### Dashboard UI
- [x] `/dashboard/reservasi` — daily timeline, date nav, status filter, create modal, detail modal with actions
- [x] `/dashboard/reservasi/settings` — reservation settings form (enable, slot duration, hours, deposit, auto-confirm)
- [x] `/dashboard/reservasi/meja` — table management grouped by floor section
- [x] Sidebar: "Reservasi" nav with PRO badge
- [x] API functions: 13 new server actions in `api.ts`

### Also this session
- [x] Fix dashboard-kasir sync (field names mismatch)
- [x] Fix register: `is_superuser=true` for new merchant owners
- [x] Fix OTP rate limit (3→10), error handling Flutter
- [x] APK v1.2.0 built & published

---

## ✅ SELESAI SESI INI (2026-04-11) — WA Bot + Flutter Reservasi + Dashboard Fixes

### WhatsApp AI Bot
- [x] `POST /webhook/fonnte` + `/webhooks/fonnte` — dual route
- [x] `wa_bot.py` — 7 intents keyword-based (greeting, menu, reservasi, cek/cancel reservasi, general, order_status)
- [x] Multi-turn reservation flow via Redis (date→time→guests→name→confirm)
- [x] Flexible parsing: "besok", "7 malam", "15 April"
- [x] Auto-assign table, check slot availability
- [x] AI fallback Claude Haiku for ambiguous messages (150 token max)
- [x] Fonnte webhook URL set: `https://kasira.online/api/v1/webhooks/fonnte`

### Flutter APK v1.3.0
- [x] Tab "Reservasi" di bottom nav dashboard kasir
- [x] Reservation list page (grouped by status, date nav, detail+actions)
- [x] Table grid page (color-coded, floor sections)
- [x] Create reservation modal
- [x] Build success, published to GitHub Releases

### Dashboard Fixes
- [x] Tier-aware layout: 1 gradient PRO badge, flat nav for Pro, locked for Starter
- [x] `/users/me` return `subscription_tier`
- [x] `reports/daily` return `shift_status` (Flutter fix)
- [x] `get_current_tenant` match UUID (was matching schema_name only)
- [x] `require_pro_tier` use `.value` for enum comparison
- [x] Storefront tier badge dynamic (was hardcoded 'starter')
- [x] Reservation button conditional (only when enabled)
- [x] Auto-invalidate Redis cache on outlet/settings/tier change
- [x] Dashboard reservasi: auto-navigate to nearest upcoming + timezone fix
- [x] Table model: position_x/y Float fix
- [x] GitHub Actions workflow: reset to origin/main before version.json push

---

---

## ✅ SESI 2026-04-19 — Senior Audit + 17 CRITICAL FIXES
Role-swap ke auditor (`feedback_senior_audit_pattern.md`) → nemuin 17 CRITICAL bug yang gue miss sendiri. Semua fixed:
- **#2 + #8 HPP unification** — 4 raw-multiply sites pake helper `unit_utils.py` (pricing_coach, menu_engineering, knowledge_graph, ai_service)
- **#6 Sync idempotency dedup** di `/sync/` push (Migration 081)
- **#7 Sync cursor-based pagination** (Migration 082) — fix offline 3-hari load
- **#9 R2 restore automation** + disaster recovery runbook
- **#10 Observability**: Prometheus metrics + structured logging + health aggregate
- **#11 Async supervisor auto-restart** + health endpoint
- **#12 Xendit retry backoff** + webhook idempotency + fail-safe (Migration 083)
- **#13 Fonnte singleton** + retry + circuit breaker
- **#14 PRICING_COACH fail-closed** Sonnet→Haiku fallback (preserve quota)
- **#15 + #16 Subscription tier lifecycle** + cascade downgrade

---

## ✅ SESI 2026-04-20 — Flutter UX Hardening Batch #14-#18
APK v1.0.27 → v1.0.32. Close audit holes:
- **Batch #14**: Rule #50 outlet scope verification + tax config + UI polish
- **Batch #15**: Multi-outlet sync + phone normalize + modal protection
- **Batch #16**: Printer lock + sync resilience + async boundary (`unawaited()` pattern)
- **Batch #17**: Node ID isolation `sha256(device|user)` + orphan cleanup + hardened logout
- **Batch #18**: Atomic batch.update + Dio CancelToken + performLogout orphan cleanup
- **POS auto-print + WA customer save** di payment success path

---

## ✅ SESI 2026-04-21 — AI Multi-Turn + Adaptive Domain
APK v1.0.32 → v1.0.36:
- **Batch #19-#21**: UUID attr error fix + dine-in table release (Rule #50 follow-up) + stale order janitor + close ghost race janitor↔payment settle
- **Batch #22**: AI multi-turn chat via Redis-only session store
- **Batch #23**: Flutter wire multi-turn + HLC merge + persistent idempotency
- **Batch #24**: Backend hardening & hygiene
- **Batch #25**: AI chat UX polish v1.0.35
- **Batch #26**: Adaptive UI domain classify endpoint + Flutter infrastructure
- **Batch #27**: Strategic positioning — waitlist + AI guardrail + adaptive upgrade sheet + coming soon

---

## ✅ SESI 2026-04-22 — Inventory Powerhouse + KG Price Events
APK v1.0.36:
- **Batch #28**: POS stock visual guard (isAvailable + isOutOfStock gate)
- **Batch #29**: Inventory Powerhouse — tabbed Produk & Stok di Flutter
- **Backend Batch #28**: superadmin waitlist monitoring endpoint
- **Backend Batch #29**: KG Price Events (margin drift WA alert)
- Hotfix: missing `sync_provider.dart` import + Dart-side filter low-stock count
- Untrack `loadtest/` (contained JWT)

---

## ✅ SESI 2026-04-24 → 2026-04-25 — Starter Margin Tracking
Fitur **Untung-Rugi** untuk Starter tier:
- **Migration 084**: `products.buy_price`
- **Backend Fase 2**: `restock` accept `unit_buy_price` + `GET /reports/margin`
- **Flutter Fase 3**: Drift v5 + restock buy_price form + Untung-Rugi tab di laporan
- **Dashboard**: buy_price form di product create/edit + `/laporan/margin` page
- **UX clarity**: "modal" vs "stok" untuk merchant non-technical (`9538341`)
- APK v1.0.39 published

---

## ✅ SESI 2026-04-25 — Pre-Launch Hardening
Production hardening sebelum publish:
- **Remove MASTER_OTP bypass** — production OTP WA only (`cbb833a`)
- **Xendit reconciliation** hardening
- **FIX #2 security audit**: Flutter QRIS polling 30s timeout + retry dialog
- **FIX #3 follow-up**: RLS bypass added to `payment_reconciliation` background task — RLS gotcha (CLAUDE.md gotcha #16: background task tanpa `SET LOCAL app.current_tenant_id = ''` → silent broken)
- APK v1.0.40 published

---

## ✅ SESI 2026-04-25 — Split-Bill Humanity + Warkop Ad-Hoc
APK v1.0.40 → v1.0.45:
- **Split-bill data integrity** (`9762674`): table release guard untuk active tab — kitchen mark order ready/completed → table di-release prematurely → janitor heal back. Fix: query `Tab.status` + skip release kalau active. 2 code path: `orders.py:519-533` + `stale_order_cleanup.py:185-220`. Reference: gotcha #15.
- **v1.0.42**: split-bill UX gaps — table tap, info card, grid sub-badge
- **v1.0.43**: split-bill flow & dashboard navigation gaps
- **v1.0.44**: split-bill humanity — active list missing + per-split receipt
- **v1.0.45**: chore version bump
- **Migration 085**: warkop ad-hoc per-item payment (`order_items.paid_at`)
- **Phase A SHIPPED**: pay_items_modal + table_actions_sheet di Flutter
- **Source-of-truth split**: `tab.paid_amount` untuk split/full, `items.paid_at` untuk pay-items adhoc
- APK v1.0.46 build pending deploy (warkop pattern)

---

## ✅ SESI 2026-04-25 — Telegram Healthcheck Cron
- `/health` monitor → Telegram bot self-alert via cron (LIVE)
- Replace healthchecks.io plan, pivot karena signup difficulty + Fonnte self-send block (`project_fonnte_otp_gotcha.md`)
- State-change throttle (anti-spam)
- Script: `scripts/healthcheck_ping.sh` (untracked)

---

## ⏭️ NEXT ACTION (per 2026-04-26)

### PRIORITAS 1 — Build & Deploy APK v1.0.46
- Warkop ad-hoc Phase A udah merge ke main, build APK pending
- Cek gotcha #13: push commit terakhir dulu, verify `git log origin/main` match lokal, baru dispatch
- Verify `head_sha` di workflow run match latest push

### PRIORITAS 2 — Onboard Pilot Merchant
- 25 tenant cap aman publish (90% confidence per `project_publish_readiness.md`)
- 30 conservative cap
- Ops hardening 4-quick-wins sudah di list
- Pisah Fonnte device dari owner nomor (gotcha self-send block)

### PRIORITAS 3 — ~~Xendit Live Activation~~ → **BYOK Pivot DONE 2026-04-26**
- ~~Daftar Xendit sub-account untuk live merchant~~ — DROPPED, replaced by BYOK
- Merchant daftar Xendit sendiri lalu paste API key di Settings → Pengaturan Pembayaran
- See `project_byok_pivot.md` (auto-memory) for full detail

### PRIORITAS 4 — Multi-Outlet (Business Tier)
- Design + migration + tier gating
- Belum mulai, paling besar untuk monetisation Business tier

### PRIORITAS 5 — Vultr Credit Reminder
- $300 credit expire 2026-05-11
- Decision: hangus (per `project_vultr_credit.md`)
- Reminder 10 Mei cek dashboard

---

## ✅ SESI 2026-04-26 (FULL DAY) — Massive Sprint Pre-Pilot Launch

### Phase 1: Split-Bill Humanity Fix v1.0.46 → v1.0.47
**Issue**: User report "kemarin gw benerin bug split-bill humanity, tapi pas test masih model lama".
- **Backend hotfix `a95440f`**: `GET /tabs/` + `GET /tabs/by-table/` MissingGreenlet — `tab_response()` panggil `compute_paid_items_total()` iterate `o.items`, tapi 2 endpoint cuma `selectinload(Tab.orders)` tanpa chain `Order.items`. Fix: chain `.selectinload(Order.items)`.
- **Flutter v2 fix `62ef99b`**: split-bill default mode pivot → "Bayar Sebagian" (warkop pattern Indonesia) jadi chip pertama default. Mode lama (Bagi Rata/Per Tamu/Custom) tetap ada tapi bukan default. Plus mini popup "Berapa orang?" saat tap meja kosong (replace hardcoded `guest_count: 1`).
- APK v1.0.47 built + deployed ke kasira.online + bind-mount permanent (gotcha #9 mitigation).

### Phase 2: BYOK Xendit Pivot (commit `289508b`)
**Decision**: pivot dari sub-account model ke BYOK (Bring Your Own Key). Merchant daftar Xendit sendiri.
- 3 agent paralel audit (Plan + Explore + general-purpose) reveal: BYOK infra UDAH READY 90% (Migration 061 + EncryptedString TypeDecorator). Cuma butuh wire active code path.
- **Phase 1+1.5+2 SHIPPED** (~3 jam total bukan 1-2 hari):
  - `payments.py:234` POS BYOK-aware (mirror connect.py:528 pattern)
  - `payment_reconciliation.py:103` BYOK-aware (existing bug fix)
  - Migration 086: `outlets.xendit_callback_token` (EncryptedString)
  - Helper `_sanitize_xendit_response()` strip headers/auth (Risk Hunt #H1)
  - Dashboard Settings tab "Payment Gateway" extend dgn callback token field
- **Phase 3 DEFERRED** (per-merchant webhook verify) — sampai 1 BYOK merchant beneran onboard. Selama pilot pakai master callback token (acceptable per Risk Hunt #C1 mitigation).

### Phase 3: Starter Pilot Readiness Smoke (commit `7737917`)
**Issue**: User minta "spawn smoke tester scope Starter end-to-end".
- Fresh merchant register → setup data → order → margin → refund → connect → cleanup. 10 scenarios.
- **Initial verdict YELLOW** — 2 backend bug ditemukan:
  1. `POST /products/` silently drop `buy_price` (margin tracking baru ship 2026-04-25 broken di create flow). Fix: 1-line add field di `Product()` constructor.
  2. `GET /products/{id}` MissingGreenlet 500 (`validate_product_ownership` gak eager-load category). Fix: `selectinload(Product.category)` di shared helper (4 caller benefit).
- **Post-fix verdict GREEN** — 10/10 scenarios PASS, tier gating bulletproof 5/5 Pro endpoint return 403.
- Plus 3 doc gaps di CLAUDE.md API quirks (`/shifts/{id}/close` ending_cash, `/payments/` amount_due+amount_paid, `/connect/{slug}/order` order_type required).

### Phase 4: Pay-Items Tax/Service Fix (commit `383c7e2`) — APK v1.0.48
**Issue**: User report "split bill nominal kurang, terbayar 0, gak sinkron".
- **3 bug terhubung, akar sama**: `OrderItem.total_price` itu subtotal level (qty × unit_price). Tax + service charge simpan di Order level. Pay-items pattern lupa apply proportional share — beda dgn `split_per_item:335` yg udah benar.
  1. `tab_header.dart:49` display `tab.paidAmount` raw → "Dibayar Rp 0" stale (warkop pattern sengaja gak update field ini)
  2. `tabs.py:791 pay_items` hitung `total_due = sum(item.total_price)` subtotal only → kasir bayar kurang
  3. `tab_service.py:compute_paid_items_total` sum subtotal only → tab gak auto-close, tax/SC orphan stuck
- **Fix architecture**: helper baru `items_proportional_due(tab, items_subtotal) -> Decimal` di `tab_service.py`. Single source of truth untuk hitung "berapa total + tax + service per subset items". Dipakai 2 caller WAJIB konsisten (`compute_paid_items_total` + `pay_items` endpoint).
- Frontend `tab_header.dart` ganti display computed `tab.totalAmount - tab.remainingAmount`.
- Frontend `pay_items_modal.dart:_selectedTotal` mirror backend logic.
- **Verified math**: subtotal 20K → total_due 23K (10% tax + 5% service apply) ✅
- APK v1.0.48 built + deployed ke kasira.online.

### Phase 5: Flutter Performance Quick Wins (commit `efd82de`+`1f5b4d8`+`d959cac`+`3020c49`) — APK v1.0.50
**Issue**: User report "loading lambat" (vague tapi sense ada issue real, 3 minggu nambah feature tanpa profiling).
- **Audit 2 agent paralel** (Explore + general-purpose) konvergen pada CRITICAL findings:
  - Post-payment cascade invalidate (1-2s freeze per transaksi)
  - POS clock setState minute-ly (480x full tree rebuild per shift)
  - Dapur addPostFrameCallback in build (potensi infinite loop)
- **Plan agent design** 4-phase implementation dengan zero-break safety (rollback per phase, APK build 2x untuk catch issue early).
- **9 quick wins SHIPPED across 4 commits**:
  - **P1** Pure UI: splash 800ms delay removed, ListView.builder margin report, CachedNetworkImage product mgmt, force-update url_launcher fix
  - **P2** Widget extraction: POS clock isolated `_PosClock`, Dapur `ref.listen` migration
  - **P3** Behavior tweak: post-payment cascade defer microtask (helper baru `post_payment_refresh.dart`), POS search debounce 250ms
  - **P4** Async deferral: splash version check timeout 5s→2s
- APK v1.0.49 (P1+P2 internal validation) + v1.0.50 (full P1-P4 final ship) built + v1.0.50 deployed ke kasira.online.

### 🎯 Tier Status Update (per 2026-04-26)
| Tier | Status | Detail |
|---|---|---|
| **Starter** | ✅ READY pilot launch | Smoke 10/10 PASS, tier gating bulletproof, BYOK done. Sisa: Fonnte device + manual UX test |
| **Pro** | ⚠️ NOT READY pilot | 3 bug split-bill humanity baru fix, perlu APK v1.0.50 manual verify + 2-3 minggu internal validate |

### 🎯 NEXT ACTION (per 2026-04-26 EOD)
1. ⏳ **Ivan manual test APK v1.0.50** integration (12 skenario per plan checklist)
2. ⏳ **Fonnte device pisah** (1-2 hari kerja, beli SIM/device baru)
3. ⏳ **Onboard cafe pilot pertama Starter** (cash-only mode dulu, BYOK enable later)
4. ⏳ **Defer items dari quick wins**: singleton Dio, autoDispose mass migration, recipe stock cache, optimistic update payment

### Memory updated this session:
- ✅ `project_byok_pivot.md` (NEW) — full BYOK decision history + critical patterns
- ✅ `project_starter_pilot_readiness.md` (UPDATED) — explicit ISOLATION Starter vs Pro
- ✅ `project_warkop_pattern.md` (UPDATED) — Phase A post-ship bug fixes 2026-04-26
- ✅ `project_perf_quickwins_2026_04_26.md` (NEW) — 4-phase quick wins reference

### Commit list this session:
```
3020c49 perf(flutter): phase 4 quick win — splash version check timeout 5s→2s
d959cac perf(flutter): phase 3 quick wins — search debounce + post-payment cascade defer
1f5b4d8 perf(flutter): phase 2 quick wins — POS clock + Dapur listener isolation
efd82de perf(flutter): phase 1 quick wins — splash boot + image cache + url launcher
383c7e2 fix(tabs): pay-items tax+service charge konsistensi (3 bug terhubung)
289508b feat(payment): wire BYOK Xendit di POS + reconciliation + dashboard UI
7737917 fix(backend): Starter pilot blockers — buy_price drop + product detail 500
6f6f804 chore(deploy): bind-mount APK volume di frontend
62ef99b feat(flutter): split-bill humanity v2 — pay-items default + guest count input
a95440f fix(backend): MissingGreenlet di list_tabs + get_tab_by_table
```

### Cara reconnect:
> "baca CLAUDE.md, MEMORY.md, SESSION.md di /var/www/kasira/ lalu lanjut dari NEXT ACTION"

---

## ✅ SESI 2026-04-26 (EOD+1) — Split-Bill Float-vs-Decimal Hotfix → APK v1.0.51

### Bug Report
Ivan manual test APK v1.0.50 → split-bill cappucino bug "pembayaran kurang" walau nominal pas. Sengaja pivot dari pay_split modal ke "Bayar Sebagian" pay-items pattern (post v1.0.47 default).

### Root Cause
`pay_items_modal.dart:_selectedTotal` (line 57-69) pake Dart `double` multiply tanpa per-share quantize:
```dart
final shareTax = selectedSubtotal * taxRate;  // 27000 * 0.0909... = 2454.5454545454546
```

Backend `tab_service.py:items_proportional_due()` (line 51-76) quantize tiap share:
```python
share_tax = (items_subtotal * tax_rate).quantize(Decimal('0.01'))  // = 2454.55
```

Total drift Rp 0.0045 → frontend send `amount_paid = 32424.5454...`, backend hitung `total_due = 32424.55` → 32424.5454 < 32424.55 = TRUE → 400 "Nominal pembayaran kurang".

Reproduced di prod tab `6f78fc56-...`:
- subtotal 55K (tax-inclusive scheme), tax 5K, service 6050
- 3 item: Es Teh 10K (paid), Nasi Lele 18K (paid), Cappuccino 27K (unpaid)
- tax_rate = 5K/55K = 0.0909... non-integer ratio = trigger float drift

### Fix (commit `72f1fff`)
1 file changed di `pay_items_modal.dart`:
- Tambah `double _q2(double x) => (x * 100).roundToDouble() / 100;` helper
- Apply quantize di shareTax + shareService sebelum sum
- Frontend hasil now exact match backend (32424.55)

### Deploy
- Auto-bump CI commit `d1cf96c` (version.json → v1.0.51)
- APK build run `24954460994` headSha `72f1fff` ✅ success
- POS APK 67MB + Dapur APK 58MB di `/var/www/kasira/public/apk/` (bind-mount)
- Backend container `version.json` synced via `docker cp`
- Endpoint verified: `/api/download/{pos,dapur}` 200, `/api/v1/auth/app/version` returns 1.0.51

### Scheduled Follow-up
Routine `trig_01PsJEKFr2KEDJF5SBm8opu5` fires **Sun 2026-05-03T10:00:00Z (17:00 WIB)** — sweep audit precision mismatch di tab/payment endpoints, file GitHub issue kalau nemu sisa.
Manage: https://claude.ai/code/routines/trig_01PsJEKFr2KEDJF5SBm8opu5

### Commit list
```
d1cf96c chore: update version.json → v1.0.51 (CI auto)
72f1fff fix(flutter): pay-items quantize-per-share match backend Decimal
```

### NEXT ACTION (per 2026-04-26 EOD+1)
1. ⏳ Ivan re-test APK v1.0.51 — repro tab cappucino → bayar sebagian → harus sukses
2. ⏳ Tunggu sweep agent 2026-05-03 → review GitHub issue kalau ada findings
3. ⏳ Lanjut yg masih open (pre-existing): Fonnte device pisah, onboard cafe pilot pertama Starter, BYOK live merchant 1 onboard
