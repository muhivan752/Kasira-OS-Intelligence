# Test Plan: Dine-In Tab System

## Prasyarat
- Backend deployed (docker cp + restart) dengan migration 077 applied
- Frontend rebuilt
- APK terbaru dari GitHub Actions
- Outlet Pro tier (subscription_tier = 'pro')
- Outlet Starter tier (untuk isolation test)
- Minimal 3 meja aktif di outlet Pro
- Shift terbuka untuk kasir

---

## FASE 1: Backend API Verification

### 1.1 Migration 077
```bash
# Di dalam container backend
alembic upgrade head
# Verify: SELECT column_name FROM information_schema.columns WHERE table_name='payments' AND column_name='tab_id';
```
- [ ] Migration 077 apply sukses
- [ ] Kolom `payments.tab_id` ada, nullable, UUID type
- [ ] Index `ix_payments_tab_id` ada

### 1.2 Tab CRUD Endpoints (Pro Only)
```
POST /tabs/           → buka tab baru (outlet_id, table_id, guest_count)
GET  /tabs/?outlet_id=X  → list tabs
GET  /tabs/{tab_id}   → detail + splits
```
- [ ] Buka tab → status 'open', tab_number generated (TAB-YYYYMMDD-NNN)
- [ ] Buka tab tanpa shift → 400 "Buka shift dulu"
- [ ] List tabs → filter by status, by table_id
- [ ] Detail tab → include table_name, splits, order_ids

### 1.3 Tab Actions
```
POST /tabs/{id}/move-table     → pindah meja
POST /tabs/{id}/merge          → gabung tab
POST /tabs/{id}/request-bill   → minta bill
POST /tabs/{id}/cancel         → batalkan tab
```
- [ ] Move table: meja lama jadi 'available', meja baru jadi 'occupied'
- [ ] Move table ke meja yang sudah ada tab → 400 error
- [ ] Merge tab: source cancelled, orders pindah ke target, totals recalculated
- [ ] Merge tab yang sudah ada pembayaran → 400 error
- [ ] Request bill: status berubah ke 'asking_bill'
- [ ] Cancel: orders unlinked (tab_id = null), meja released

### 1.4 Tab by Table
```
GET /tabs/by-table/{table_id}  → open tab for table
```
- [ ] Meja dengan open tab → return tab data
- [ ] Meja tanpa open tab → return null (data: null)

### 1.5 Tier Isolation
- [ ] Semua /tabs/ endpoint → Starter tenant → 403 "Fitur ini hanya tersedia untuk paket Pro"
- [ ] Pro tenant → 200 OK

---

## FASE 2: Payment Flow Verification

### 2.1 Tab Pay-Full
```
POST /tabs/{id}/pay-full  → {payment_method: 'cash', amount_paid: X, row_version: Y}
```
- [ ] Payment created dengan `tab_id` populated
- [ ] Payment amount = tab total_amount
- [ ] Semua orders status → 'completed'
- [ ] Tab status → 'paid'
- [ ] Meja status → 'available' (kalau gak ada order lain)
- [ ] Event 'tab.paid' appended ke event store

### 2.2 Tab Split + Pay
```
POST /tabs/{id}/split/equal → {num_people: 3, row_version: Y}
POST /tabs/{id}/splits/{split_id}/pay → {payment_method: 'cash', amount_paid: X, row_version: Z}
```
- [ ] Split equal → 3 splits created, tab status 'splitting'
- [ ] Bayar split 1 → split status 'paid', tab paid_amount naik
- [ ] Bayar split 2 → same
- [ ] Bayar split 3 (terakhir) → tab status 'paid', semua orders 'completed'
- [ ] Setiap payment punya `tab_id`

### 2.3 Cancel Order in Tab
```
PUT /orders/{id}/status → {status: 'cancelled', row_version: Y}
```
- [ ] Cancel 1 order dari tab 3 orders → tab total turun
- [ ] Stock di-restore (simple mode: stock_qty naik, recipe mode: ingredient stock naik)
- [ ] Tab masih open, remaining orders masih ada

### 2.4 Zero Double Payment
- [ ] Tab pay-full 1x → cek payments table → hanya 1 payment untuk tab ini
- [ ] Order di tab → cek payments table → TIDAK ada payment terpisah untuk order individual

---

## FASE 3: Flutter POS Dine-In (Pro)

### 3.1 Flow: Kirim ke Dapur
1. Buka shift
2. Pilih produk (min 2 item)
3. Pilih 'Dine In'
4. Pilih meja
5. Tekan "KIRIM KE DAPUR" (tombol hijau)

- [ ] Tombol "KIRIM KE DAPUR" muncul (bukan "BAYAR SEKARANG")
- [ ] Order created + linked ke tab
- [ ] Dialog sukses: "Pesanan Dikirim!" + tab number + "Lihat Tab" button
- [ ] Order status = 'preparing' (kitchen bisa lihat)
- [ ] Cart cleared, providers refreshed
- [ ] Meja status = 'occupied'

### 3.2 Tambah Pesanan ke Meja yang Sama
1. Setelah 3.1, pilih produk baru
2. Pilih 'Dine In', pilih meja YANG SAMA
3. Tekan "KIRIM KE DAPUR"

- [ ] Tab yang sama di-reuse (bukan buat tab baru)
- [ ] Tab total naik (include order baru)
- [ ] Order count di tab naik

### 3.3 Bayar via Tab Detail
1. Buka Tab / Bon list
2. Tap tab yang aktif
3. Pilih "Bayar Lunas" atau "Split Bill"

- [ ] Tab detail tampil: table name, orders, total, guest count
- [ ] Bayar Lunas → payment modal → cash/QRIS → tab closed
- [ ] Split Bill → pilih metode → bayar per split → tab closed when all paid

### 3.4 Pindah Meja
1. Di tab detail, tap "Pindah Meja"
2. Pilih meja tujuan

- [ ] Meja lama released (available)
- [ ] Meja baru occupied
- [ ] Tab table_id updated
- [ ] Snackbar "Pindah ke Meja X"

### 3.5 Gabung Meja
1. Buka 2 tab di 2 meja berbeda (masing-masing ada order)
2. Di tab A detail, tap "Gabung Meja"
3. Pilih tab B

- [ ] Tab B cancelled, orders pindah ke tab A
- [ ] Tab A total = gabungan kedua tab
- [ ] Tab A guest_count += tab B guest_count
- [ ] Meja B released

### 3.6 Offline Check
1. Matikan internet/WiFi
2. Pilih 'Dine In', pilih meja, tekan "KIRIM KE DAPUR"

- [ ] Error message: "Tab/Bon membutuhkan koneksi internet. Gunakan mode Takeaway untuk offline."
- [ ] Ganti ke 'Takeaway' → "BAYAR SEKARANG" → offline order berhasil

---

## FASE 4: Flutter POS Dine-In (Starter)

### 4.1 Starter = Flow Lama
1. Login sebagai kasir Starter tier
2. Pilih produk, pilih 'Dine In', pilih meja

- [ ] Tombol "BAYAR SEKARANG" (bukan "KIRIM KE DAPUR")
- [ ] Payment modal langsung muncul
- [ ] Order created + payment created in 1 flow
- [ ] TIDAK ada tab involvement

### 4.2 Tab Menu Tidak Muncul
- [ ] Tab / Bon page → redirect atau error "Fitur Pro"
- [ ] Sidebar: Tab/Bon link tidak ada atau locked

---

## FASE 5: Storefront Dine-In (QR Scan)

### 5.1 Pro Outlet — Customer Scan QR
URL: `https://kasira.online/{slug}?table={table_uuid}`

1. Buka URL di browser HP
2. Cek banner "Dine In — Pesanan akan dikirim ke meja Anda"
3. Pilih menu, tambah ke cart
4. Ke halaman checkout

- [ ] Banner hijau "Dine In" muncul di atas
- [ ] Checkout: 3 opsi (Dine In / Ambil Sendiri / Delivery)
- [ ] Dine In auto-selected
- [ ] Table info tampil (Meja X)
- [ ] Tombol "Pesan ke Meja" (bukan pilihan cash/QRIS)
- [ ] "Minta Bill" button muncul

### 5.2 Storefront Order → Tab Link
1. Isi nama + phone, tekan "Pesan ke Meja"
2. Cek backend

- [ ] Order created dengan table_id + order_type='dine_in'
- [ ] Order auto-linked ke open tab (kalau ada)
- [ ] TIDAK ada Payment created (payment.status = 'pending_tab')
- [ ] Order status = 'preparing'
- [ ] Response message: "Pesanan masuk ke tab meja"

### 5.3 Storefront Order TANPA Open Tab
1. Scan QR untuk meja yang belum ada tab
2. Order via storefront

- [ ] Order created dengan table_id, TANPA payment
- [ ] Order NOT linked to any tab (tab_id = null) — karena belum ada tab
- [ ] Kasir nanti buka tab → link order manual
- [ ] TIDAK ada double payment risk

### 5.4 Minta Bill dari Storefront
1. Setelah order, tap "Minta Bill"

- [ ] Tab status berubah ke 'asking_bill'
- [ ] Response: "Bill diminta — kasir akan segera menghampiri"
- [ ] Button disabled setelah diminta

### 5.5 Storefront Starter Outlet — No Dine-In
URL: `https://kasira.online/{starter-slug}?table={table_uuid}`

- [ ] TIDAK ada opsi "Dine In" di checkout (hanya Ambil Sendiri / Delivery)
- [ ] TIDAK ada "Minta Bill" button
- [ ] Order tetap bisa dibuat (pickup/delivery) dengan payment normal

### 5.6 Order Tambahan via QR (Customer pesen lagi)
1. Setelah 5.2, scan QR lagi (atau bookmark)
2. Pilih menu baru, checkout

- [ ] Order baru auto-linked ke tab yang sama
- [ ] Tab total naik
- [ ] Kasir lihat order baru di tab detail

---

## FASE 6: Event Store + AI Context

### 6.1 Tab Events
Setelah menjalankan test di atas, query event store:
```sql
SELECT event_type, event_data->>'tab_number', event_data->>'status'
FROM events
WHERE stream_id LIKE 'tab:%'
ORDER BY created_at DESC;
```

- [ ] Event 'tab.opened' ada
- [ ] Event 'tab.order_added' ada (per order)
- [ ] Event 'tab.asking_bill' ada (kalau di-test)
- [ ] Event 'tab.paid' atau 'tab.split_paid' ada
- [ ] Event 'tab.moved_table' ada (kalau di-test)
- [ ] Event 'tab.merged' ada (kalau di-test)
- [ ] Event 'tab.cancelled' ada (kalau di-test)

### 6.2 AI Context
```
POST /ai/chat → "berapa tab aktif sekarang?"
POST /ai/chat → "berapa order dine-in hari ini?"
POST /ai/chat → "meja mana yang occupied?"
```

- [ ] AI jawab jumlah tab aktif + status
- [ ] AI jawab dine-in vs takeaway breakdown
- [ ] AI tahu tab yang MINTA BILL (warning)
- [ ] AI tahu table occupancy

### 6.3 Payment.tab_id Populated
```sql
SELECT p.id, p.tab_id, p.order_id, p.amount_due, t.tab_number
FROM payments p
LEFT JOIN tabs t ON t.id = p.tab_id
WHERE p.tab_id IS NOT NULL;
```
- [ ] Tab payments punya tab_id
- [ ] Direct payments (non-tab) → tab_id = null

---

## FASE 7: CRDT + Sync Verification

### 7.1 Online → Sync → Verify
1. Buat dine-in order (Pro, online)
2. Trigger sync dari Flutter
3. Cek Drift DB

- [ ] Order muncul di Drift lokal dengan tab_id
- [ ] Product stock ter-update (CRDT merge)
- [ ] Tidak ada duplicate order

### 7.2 Offline Takeaway → Sync → Verify
1. Matikan internet
2. Buat takeaway order (offline via CRDT)
3. Nyalakan internet, trigger sync

- [ ] Order pushed ke server
- [ ] Stock deducted server-side (idempotent — skip kalau event sudah ada)
- [ ] Product CRDT counters merged (max per node)

### 7.3 Multi-Device Consistency
1. Device A buat dine-in order (online, Pro)
2. Device B sync → lihat order + updated stock

- [ ] Device B lihat order di list
- [ ] Device B lihat stock sudah berkurang
- [ ] Tidak ada ghost stock atau stale data

---

## FASE 8: Edge Cases

### 8.1 Tab di-cancel setelah ada payment partial
- [ ] Cancel ditolak: "Ada split yang sudah dibayar, tidak bisa cancel seluruh tab"

### 8.2 Bayar split lebih dari amount
- [ ] Cash: kembalian dihitung benar
- [ ] QRIS: exact amount required

### 8.3 Move table ke meja reserved
- [ ] Ditolak: "Meja X sedang reserved"

### 8.4 Gabung tab yang sudah ada split payment
- [ ] Ditolak: "Tab sumber sudah ada pembayaran"

### 8.5 Concurrent tab payment (2 kasir bayar tab yang sama)
- [ ] row_version conflict → 409 "Data berubah, refresh dulu"

### 8.6 Storefront order ke outlet yang tutup
- [ ] 400: "Maaf, outlet sedang tutup"

### 8.7 Cancel semua order di tab → tab total = 0
- [ ] Tab total = 0 setelah recalculate
- [ ] Bayar tab total 0 → ditolak "Tab kosong"

---

## Pass Criteria
- FASE 1-5: 100% pass (functional correctness)
- FASE 6: Event store complete, AI answers correct
- FASE 7: No data inconsistency, CRDT merge clean
- FASE 8: All edge cases handled gracefully (no 500, no data corruption)
