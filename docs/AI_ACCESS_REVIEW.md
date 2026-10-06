# Tahap 3 akses AI dan password akun

6 Oktober 2026. Ivan melanjutkan tahap 3 dengan “gas”, lalu meminta minimum username/password lebih pendek. Pilihan password belum dijawab; setelah memberi kesempatan menjawab, implementasi memakai minimum 8 karakter, username tetap 3. Login akun lama tetap menerima password existing. Registrasi, claim, aktivasi, recovery dan ganti password memakai minimum baru di API/web/native.

Managed AI memakai grant `ai.chat` tersendiri. Hak tersebut tidak memberikan data modul lain. Tier Pro aktif tetap diperlukan untuk chat dan HPP. Owner/legacy mempertahankan fitur existing; akun managed tidak dimigrasikan otomatis.

| Jalur | Pemeriksaan managed |
| --- | --- |
| Chat umum | `ai.chat`, outlet aktif dalam akun; hanya konteks dengan grant data terkait |
| Insight beranda | `ai.chat` + `sales.view`; cache akun/outlet/versi izin |
| Riwayat chat umum | tenant, user, outlet, access_version dan conversation UUID; TTL 30 menit; tidak membaca key lama per tenant |
| Cache konteks managed | tenant, user, outlet, access_version dan hash pertanyaan; TTL 60 detik; tidak membaca cache owner per outlet |
| HPP list/get | `ai.chat`, `hpp.view`, `supplier.price.view`, pemilik percakapan, outlet dan versi izin saat dibuat |
| HPP create/message | grant baca di atas + `hpp.manage`; hasil tetap draft |
| HPP approve | grant di atas + `hpp.approve`; revision/fingerprint/replay existing tetap berlaku |
| OCR scan | `ai.chat`, `purchasing.manage`, `supplier.price.view`, outlet eksplisit |
| OCR apply harga | `ai.chat`, `hpp.view`, `hpp.manage`, `hpp.approve`, `supplier.price.view`, outlet di body dan semua ingredient dalam brand outlet |
| Apply resep/menu massal lama | tetap tertutup managed; setup resep managed melalui draft/review/approve HPP |
| Restock dari chat | managed hanya diarahkan ke Operasional; chat tidak menulis stok |
| KG/embedding alternatif/admin | tetap tertutup managed; retrieval internal hanya produk brand outlet yang sudah diizinkan |

Katalog menu hanya masuk ke AI bila akun boleh membaca katalog POS/stok/HPP/pembelian. Harga beli produk membutuhkan `supplier.price.view`; HPP bahan membutuhkan `hpp.view`, dengan harga beli mentah disamarkan bila tidak memiliki grant harga. Stok bahan, penjualan lunas, nota dan fakta pelanggan memakai outlet yang sedang dipilih. Profil pelanggan bersama bisnis mengikuti kontrak CRM existing. Keuangan memakai DTO finance yang sudah menerapkan outlet/global/account scope tahap 2. Data rincian penjualan tidak membawa profil pelanggan tanpa hak CRM. AI tidak memakai metadata KG bebas untuk managed; retrieval produk tidak membuka tenant atau brand lain.

Jawaban dibuffer hingga izin dan sesi diperiksa lagi. Panggilan provider tidak menahan transaksi baca. Worker memeriksa akun/tenant/brand/outlet/grant/access_version, masa JWT dan sesi sid/cv sebelum provider dan sebelum menyimpan. Worker yang sudah antre ketika akses/sesi dicabut membersihkan pending tanpa menyimpan jawaban/draft. Pemeriksaan terakhir mutasi memegang row lock akun/jabatan/karyawan/outlet/brand/tenant/sesi sampai commit. Semua writes HPP, audit/event/result tetap satu transaksi.

Migrasi 115 menambahkan `hpp_setup_sessions.access_version` nullable. Riwayat lama tetap tersimpan untuk owner/legacy. Managed hanya dapat membuka percakapan yang dibuat dengan versi izin kini; perubahan izin meminta percakapan baru, sehingga jawaban lama tidak ikut konteks baru. Persetujuan tetap untuk percakapan milik akun sendiri, sesuai workflow existing.

Web managed memiliki halaman AI sederhana dengan pilihan outlet, pertanyaan, jawaban, percakapan baru dan link draft HPP sesuai grant. Pilihan outlet HPP dikirim melalui tautan dan server actions. Perubahan access_version me-remount isi halaman sehingga percakapan lama tidak menetap setelah refresh izin. Review HPP tanpa approve menampilkan status draft tanpa tombol simpan. OCR mengisi draft nota yang harus diperiksa pengguna.

Design Read: arah Selaris existing, warm neutral/charcoal/coral, Source Sans 3 dan panel/kontrol HPP. ENERGY 1 / RHYTHM 1 / MOTION 1. Percakapan dan outlet menjadi fokus; coral hanya untuk kirim, teks status menjelaskan data/draft. Tidak menambah aset visual atau dekorasi baru.

QA backend: 10 kelompok HTTP/JWT/forced-RLS/provider palsu PASS, termasuk query pgvector nyata untuk RAG dan revoke selama OCR; 64 unit backend, 63 PASS dan 1 optional skip; regresi tahap 2 dan HPP existing PASS, termasuk percakapan panjang, atomisitas/replay dan real HTTP 202 sebelum provider selesai. Form akun native 4 tests PASS. TypeScript PASS. Browser image produksi final PASS; Delivery Gate [AI_ACCESS_GATE.md](AI_ACCESS_GATE.md), deployment [AI_ACCESS_RELEASE.md](AI_ACCESS_RELEASE.md). Tidak ada panggilan provider berbayar atau mutasi merchant untuk QA. GPS/foto absensi/offline tetap tahap berikutnya; native managed AI tetap mengikuti pembatasan navigasi APK existing.
