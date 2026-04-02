# SESSION — 2026-04-02
# Claude update file ini otomatis tiap task selesai

## FOKUS SESI INI
- [x] Feature D: Loyalty Points — backend + Flutter (selesai)
- [x] Feature A: Flutter Dapur App — 8 layar kitchen display (selesai)
- [ ] Feature B: Kasira Connect Storefront — **NEXT**

## MODUL AKTIF
Modul: Flutter Dapur App (Feature A) — selesai
Next: Kasira Connect Storefront (Feature B)

## PROGRESS SESI INI

### ✅ Feature D: Loyalty Points
- Migration 059: `customer_points` + `point_transactions`
  - UNIQUE(order_id, type) → idempotent earn/redeem (Golden Rule #35)
  - row_version pada customer_points (Golden Rule #29–30)
- `backend/api/routes/loyalty.py`
  - `GET /loyalty/{customer_id}/balance` → saldo + redeemValueRp
  - `POST /loyalty/earn` → idempoten via ON CONFLICT DO NOTHING
  - `POST /loyalty/redeem` → optimistic lock, deduct balance
  - `GET /loyalty/{customer_id}/history` → 20 transaksi terakhir
- `backend/api/api.py` → include loyalty router
- Flutter `features/loyalty/`:
  - `loyalty_provider.dart` (FutureProvider.family balance + history)
  - `loyalty_redeem_widget.dart` (switch + slider di CartPanel)
  - `loyalty_history_page.dart` (gradient balance card + txn list)
  - `cart_panel.dart` refactor → ConsumerStatefulWidget, integrasikan redeem widget
  - `main.dart` → tambah route `/loyalty/:customerId`

### ✅ Feature A: Flutter Dapur App
Commit: `1b9d67e` di branch `claude/review-documentation-qqAkC`

**File baru:**
```
kasir_app/lib/main_dapur.dart              ← entry point terpisah
kasir_app/lib/features/dapur/
  providers/dapur_provider.dart            ← polling + optimistic update
  presentation/pages/
    dapur_splash_page.dart                 ← dark splash, cek config
    dapur_login_page.dart                  ← numpad PIN 6 digit
    dapur_dashboard_page.dart              ← grid 3 tab + badge pesanan baru
    dapur_completed_page.dart              ← list selesai hari ini
    dapur_statistik_page.dart              ← stat cards + bar + urgent alert
    dapur_settings_page.dart               ← suara, interval, logout
  presentation/widgets/
    order_queue_card.dart                  ← card + 1-tap status update
```

**File diubah:**
```
backend/api/routes/auth.py                 ← tambah POST /auth/pin/verify
kasir_app/lib/features/auth/.../login_page.dart ← simpan 'phone' ke storage
.github/workflows/build-apk.yml           ← build 2 APK (pos + dapur)
```

**Detail teknikal dapur_provider.dart:**
- `startPolling(intervalSeconds: 8)` → Timer.periodic
- `fetchOrders()` → 2 request paralel: active orders + completed today
- `updateStatus()` → PUT /orders/{id}/status dengan row_version
  → 409 conflict → auto fetchOrders(silent: true)
- `dapurStatsProvider` → computed dari DapurState (Provider<DapurStats>)
- `DapurOrder.isUrgent` → elapsedMinutes >= 15 (card border merah)
- `DapurOrder.isWarning` → elapsedMinutes >= 10 (timer kuning)

**Detail teknikal POST /auth/pin/verify:**
- Input: `{phone, pin}` — tidak perlu JWT
- Verifikasi: `security.verify_pin(pin, user.pin_hash)`
- Return: JWT + tenant_id + outlet_id (sama dengan OTP verify)
- Audit log wajib (Golden Rule #2)

**Cara build Dapur APK:**
```bash
flutter build apk --release --target lib/main_dapur.dart
```

## KEPUTUSAN BARU SESI INI
1. **Dapur App = entry point terpisah** (bukan route dari main app).
   Alasan: tim dapur tidak butuh akses POS, UI berbeda (dark theme).
2. **PIN login tanpa OTP untuk dapur** via `POST /auth/pin/verify`.
   Alasan: dapur staff tidak selalu punya HP, login harus cepat di device shared.
3. **Phone disimpan ke FlutterSecureStorage** saat OTP verify di login_page.dart.
   Dibutuhkan dapur login untuk memanggil `/auth/pin/verify`.
4. **Auto-polling 8 detik** (bukan WebSocket).
   Alasan: cukup untuk kitchen display, tidak perlu infra WebSocket dulu.
5. **GitHub Actions build 2 APK** sekaligus (pos + dapur) dari 1 workflow trigger.

## CHECKPOINT TERAKHIR
Terakhir di: Feature A (Dapur App) selesai, pushed ke `claude/review-documentation-qqAkC`.
Lanjut dari: **Feature B — Kasira Connect Storefront**.

## CONTEXT UNTUK LANJUT FEATURE B
Backend Connect API sudah ada di `backend/api/routes/connect.py`:
- `GET /connect/{slug}` → info outlet + menu publik
- `POST /connect/{slug}/order` → buat order dari storefront + generate QRIS Xendit
- `GET /connect/orders/{order_id}` → cek status order

Yang belum ada / perlu diperbaiki:
- Next.js UI `app/[slug]/` — halaman menu publik yang bagus
- Cart state di storefront (local state, tanpa login)
- Order tracking page setelah bayar
- Xendit QRIS sudah di backend, pastikan storefront polling status tiap 3 detik
- Connect storefront slug sudah otomatis saat outlet register (Golden Rule #21)

File yang perlu dibaca saat lanjut:
- `backend/api/routes/connect.py` (API yang sudah ada)
- `app/[slug]/` (cek apakah sudah ada atau perlu dibuat dari nol)
- `backend/services/xendit.py` (untuk memahami QRIS flow)

## FILE YANG DIUBAH SESI INI
### Feature D (Loyalty):
- `backend/api/routes/loyalty.py` (baru)
- `backend/api/api.py`
- `kasir_app/lib/features/loyalty/providers/loyalty_provider.dart` (baru)
- `kasir_app/lib/features/loyalty/presentation/widgets/loyalty_redeem_widget.dart` (baru)
- `kasir_app/lib/features/loyalty/presentation/pages/loyalty_history_page.dart` (baru)
- `kasir_app/lib/features/pos/presentation/widgets/cart_panel.dart`
- `kasir_app/lib/main.dart`

### Feature A (Dapur):
- `kasir_app/lib/main_dapur.dart` (baru)
- `kasir_app/lib/features/dapur/providers/dapur_provider.dart` (baru)
- `kasir_app/lib/features/dapur/presentation/pages/dapur_splash_page.dart` (baru)
- `kasir_app/lib/features/dapur/presentation/pages/dapur_login_page.dart` (baru)
- `kasir_app/lib/features/dapur/presentation/pages/dapur_dashboard_page.dart` (baru)
- `kasir_app/lib/features/dapur/presentation/pages/dapur_completed_page.dart` (baru)
- `kasir_app/lib/features/dapur/presentation/pages/dapur_statistik_page.dart` (baru)
- `kasir_app/lib/features/dapur/presentation/pages/dapur_settings_page.dart` (baru)
- `kasir_app/lib/features/dapur/presentation/widgets/order_queue_card.dart` (baru)
- `backend/api/routes/auth.py` (tambah POST /auth/pin/verify)
- `kasir_app/lib/features/auth/presentation/pages/login_page.dart` (simpan phone)
- `.github/workflows/build-apk.yml` (build 2 APK)
- `MEMORY.md` (update progress)
- `SESSION.md` (file ini)

## BLOCKER
- Tidak ada.
