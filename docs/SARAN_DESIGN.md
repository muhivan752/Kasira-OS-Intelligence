# Mesin Saran Selaris (rancangan, 9 Oktober 2026)

Arah dari Ivan: AI Selaris adalah fitur utama yang dijual, dan harus PROAKTIF.
Selaris menyodorkan saran yang siap dijalankan; pemilik memilih Terapkan, Ubah,
atau Abaikan. Mockup yang sudah disetujui alurnya:
https://claude.ai/artifact/32Gghjbq9E37UoBaBJXR32 (HP, tablet per peran, DM Sefrekuensi).

## Tiga jawaban arsitek

1. **Rumahnya di mana?** Satu modul `backend/services/suggestions/` dan satu tabel
   `suggestions`. Saran harga bahan yang SUDAH ADA (`tasks/kg_price_event_loop.py`,
   kirim WA lewat Fonnte) dilebur ke sini, bukan berjalan di sebelahnya.
2. **Siapa yang memutuskan?** Detektor (kode murni) memutuskan KAPAN ada saran dan
   SEMUA angkanya. Model AI hanya dipakai di dua tempat: mengusulkan takaran resep
   (berlabel perkiraan) dan memahami kalimat pemilik di percakapan Ubah. Eksekusi
   aksi lewat service yang sudah ada, dengan izin yang sama dengan tombol manualnya.
3. **Kalau salah, ketahuan dari mana?** Setiap saran menyimpan keputusan pemilik
   (diterapkan, diubah lalu diterapkan, diabaikan + alasan, dibatalkan). Rasio per
   jenis saran terbaca di superadmin; jenis yang selalu diabaikan dimatikan. Ada
   saklar global per jenis untuk mematikan detektor yang bermasalah tanpa deploy.

## Data

Tabel baru `suggestions` (migrasi 117). Tabel baru, bukan numpang `notifications`:
notifikasi itu kabar satu arah, saran punya siklus hidup (keputusan, batal, kedaluwarsa).

| Kolom | Isi |
|---|---|
| tenant_id, outlet_id | pemilik baris; ikut terhapus otomatis oleh hapus akun (punya tenant_id) |
| kind | `stock_low`, `ingredient_price_up`, `thin_margin`, `recipe_missing` |
| subject_type, subject_id | bahan atau produk yang dibicarakan |
| dedup_key | kind + subject; satu saran terbuka per subjek |
| facts (jsonb) | angka yang DIHITUNG detektor dan ditampilkan apa adanya |
| proposal (jsonb) | aksi + parameter, misal `{action: update_price, product_id, new_price}` |
| impact_rp, urgent | untuk urutan: mendesak dulu, lalu dampak rupiah per bulan |
| data_hash | sidik data sumber; saran yang diabaikan muncul lagi hanya kalau ini berubah |
| visibility | `hpp` (berisi modal/harga beli) atau `stock` (peringatan stok tanpa harga) |
| status | `open`, `applied`, `skipped`, `undone`, `expired`, `superseded` |
| decided_by, decided_at, skip_reason, edited (bool) | jejak keputusan |
| undo (jsonb) | nilai sebelum diterapkan, untuk Batalkan |
| expires_at | saran stok basi dalam hitungan hari, saran harga dalam 2 minggu |

Index unik PARSIAL `(tenant_id, outlet_id, dedup_key) WHERE status = 'open'`.
Upsert WAJIB membawa predikat yang sama (CLAUDE.md, jebakan SQL ON CONFLICT parsial).

Pengaturan per tenant (kolom JSON di tabel yang sama dengan pengaturan outlet atau
tabel kecil `assistant_settings`): saluran (`app` atau `sefrekuensi`, satu saja),
jenis saran yang aktif, jam ringkasan (bawaan 07.00 waktu outlet).

## Detektor (kode murni, tanpa AI)

Jalan setiap pagi per outlet sebelum jam ringkasan, plus dipicu kejadian
(pembelian diterima, nota dicatat). Kunci Redis + SKIP LOCKED karena uvicorn 2 worker.

- **stock_low**: pemakaian rata-rata 7 hari dari `stock_events` (consume) untuk
  mode resep, dari `order_items` untuk mode biasa. Saran kalau sisa hari ≤ waktu
  kirim pemasok + 2 hari (waktu kirim bawaan 1 hari). Usulan: draf pembelian untuk
  7 hari ke pemasok dan harga terakhir (`supplier_price_history` / item pembelian).
  Mendesak.
- **ingredient_price_up**: harga beli naik ≥ 5% dari pembelian sebelumnya. Modal
  per produk sebelum dan sesudah dihitung dengan `cost_map_for_brand`. Usulan:
  harga jual yang mengembalikan margin lama, dibulatkan ke atas ke Rp 500.
  Dampak = selisih modal × penjualan 30 hari.
- **thin_margin**: margin < 20% dan terjual ≥ 10 dalam 30 hari. Usulan: harga untuk
  margin 30%, kenaikan maksimal 25% (lebih dari itu ditawarkan sebagai "cek resep").
  Dampak = tambahan untung × penjualan 30 hari, berlabel "jika penjualan tetap".
- **recipe_missing**: produk outlet mode resep yang terjual tapi resepnya tidak
  ada atau tidak lengkap. Urutan dari jumlah terjual. Usulan takaran dari model
  (lihat bawah); modal dan margin dihitung `hpp_math` dari harga bahan toko.

Maksimal 5 saran terbuka per outlet. Teks kartu dirakit kode dari `facts`
(template), jadi tidak ada angka yang ditulis model dan tidak ada biaya AI untuk
tiga dari empat jenis saran.

## Peran AI

| Tugas | Model | Batas |
|---|---|---|
| Takaran resep perkiraan | DeepSeek (teks) | Keluaran divalidasi skema `Draft` yang sudah ada di `hpp_setup_service`; setiap takaran berlabel `estimate` |
| Percakapan Ubah | DeepSeek dengan function calling | Alatnya hanya mengubah parameter usulan saran itu (takaran, harga, jumlah beli); kode menghitung ulang |
| Baca foto nota | OpenAI vision (model murah, sama dengan Sefrekuensi) | Hasilnya draf pembelian; harga baru memicu detektor harga |
| Cadangan | `llm_client` router | DeepSeek mati: pakai model OpenAI murah |

Kunci OpenAI disalin ke `.env` Selaris lewat skrip yang dijalankan Ivan
(pengaman Claude Code tidak mengizinkan Claude memindahkan kredensial).
`/privacy` wajib menambah OpenAI sebelum vision tayang.

## Terapkan dan Batalkan

Satu eksekutor per aksi, memanggil service yang sama dengan tombol manual:

| Aksi | Service | Izin |
|---|---|---|
| draf pembelian | purchasing (status `draft`, stok tidak berubah sampai diterima) | purchasing.manage |
| simpan resep | jalur simpan resep HPP yang sudah ada | hpp.manage |
| ubah harga jual | jalur update produk yang sama (cache storefront ikut dibersihkan) | pemilik / products |

Transisi status pakai kunci baris + `client_request_id` (idempoten, aman diketuk dua
kali). Batalkan hanya berjalan kalau nilai sekarang masih sama dengan yang diterapkan;
kalau sudah diubah orang sesudahnya, Selaris menolak dan menjelaskan.

## Siapa melihat apa

- `visibility = hpp`: pemilik dan jabatan ber-izin `hpp.view` (gerbang yang sama
  dengan tab Laporan, `business_access`).
- `stock_low` untuk jabatan ber-izin stok: tampil TANPA harga beli dan total
  (API membuang field harga, bukan disembunyikan di layar).
- Notifikasi hanya ke perangkat pemilik (`fcm.notify_outlet(device_types=("owner",))`),
  atau ke DM Sefrekuensi kalau saluran itu dipilih. Tidak pernah keduanya.

## API

- `GET /suggestions?outlet_id=` daftar terbuka + yang diputuskan 7 hari terakhir
- `POST /suggestions/{id}/apply` `{client_request_id, params?}`
- `POST /suggestions/{id}/skip` `{reason}`
- `POST /suggestions/{id}/undo`
- `POST /suggestions/{id}/chat` percakapan Ubah
- `GET/PUT /assistant/settings`

## Tahapan

1. **A, tanpa APK**: migrasi, empat detektor, eksekutor, API, kartu saran di
   Beranda dashboard web, metrik keputusan di superadmin. Uji di DB sintetis.
2. **B**: notifikasi pagi + mendesak ke HP pemilik, pengaturan saluran, percakapan Ubah.
3. **C**: vision nota OpenAI, kartu saran di app (masuk build APK yang sedang ditahan).
4. **D**: saluran DM Sefrekuensi (akun Selaris Assistant; Sefrekuensi hanya
   mengantar kalimat, data tetap di Selaris).

## Keputusan Ivan yang dibutuhkan

1. Notifikasi saran bawaan NYALA atau MATI? (aturan lama di Sefrekuensi:
   otomatisasi bawaan mati).
2. Paket mana dapat apa (usulan: semua paket dapat saran stok dan resep; Pro dapat
   harga, margin, percakapan Ubah, dan DM Sefrekuensi).
