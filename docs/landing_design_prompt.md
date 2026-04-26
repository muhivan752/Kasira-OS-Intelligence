# Claude Design Prompt — Kasira Landing Page Revamp

**Created**: 2026-04-26
**For use at**: https://claude.ai/design
**Purpose**: Revamp `app/page.tsx` Next.js landing untuk pre-pilot launch yang "menjual maksimal" tapi tetap honest (no overselling feature yang belum ada).

---

## Cara pakai

1. Buka https://claude.ai/design (login Pro/Max account)
2. Pilih template **"Landing Page"** atau **"Web Design"**
3. Copy-paste FULL prompt di section bawah ke kolom prompt
4. Upload reference (optional):
   - Screenshot https://kasira.online (current landing)
   - Logo Kasira
5. Iterate: setelah draft pertama, refine via chat ("ganti hero copy jadi X", "tambah testimonial slot Y")
6. Export as HTML
7. Send HTML balik ke Claude Code (saya) untuk integrate ke Next.js component

---

## PROMPT (copy semua di bawah ini)

```
═══════════════════════════════════════════════════════════════════
PROJECT BRIEF: KASIRA LANDING PAGE REVAMP
═══════════════════════════════════════════════════════════════════

## What is Kasira

Kasira = Smart POS (Point of Sale) untuk cafe & UMKM Indonesia.
Built by solo dev (Ivan) yang ngerasa POS existing (Moka, Pawoon, 
Olsera) terlalu "barat" + over-priced + missing pattern khas warkop 
Indonesia.

Stack: FastAPI backend + PostgreSQL + Flutter Android app + 
Next.js 14 dashboard + Xendit QRIS.

Production: https://kasira.online (live)
Repo current landing: app/page.tsx (Next.js + Tailwind, 647 lines)

## Target Audience (3 personas, match 3 tier pricing)

### Persona A: Warung & Kantin (Starter — Rp 99rb/bulan)
- Owner: 1 orang, biasanya juga jadi kasir
- Outlet: 1, 30-50 menu
- Transaksi: 30-100/hari
- Pain: itung manual cash di akhir shift sering selisih, gak tau menu 
  paling laku, pelanggan repeat sering nanya "ada menu apa?"
- Tech savvy: low-medium
- Budget concern: TINGGI — mereka bandingin per Rp

### Persona B: Coffee Shop & Cafe Specialty (Pro — Rp 299rb/bulan)
- Owner: founder + 2-5 staff
- Outlet: 1-2, menu 50-150 (sering update musiman)
- Transaksi: 100-300/hari
- Pain: kasir lupa input order, customer split bill ribet, gak tau 
  margin per produk, perlu reservasi meja, dapur kacau pas peak hour
- Tech savvy: medium-high
- Budget concern: MEDIUM — mereka mau bayar kalau ROI jelas

### Persona C: Chain F&B & Multi-Outlet (Business — Rp 499rb/bulan)
- Owner: brand manager / GM
- Outlet: 3-10+
- Transaksi: 500+/hari per outlet
- Pain: butuh konsolidasi laporan HQ, transfer stok antar outlet, 
  custom domain storefront per brand
- Tech savvy: high
- Budget concern: LOW — mereka biasa bayar enterprise tool

## ⚠️ HARD REQUIREMENTS (Honesty / Anti-Misleading)

### 1. Pricing Tier yang Akurat
Per memory `project_starter_pilot_readiness.md` 2026-04-26:
- **Starter**: ✅ READY production. Tier ini fokus utama pilot launch.
- **Pro**: ⚠️ feature live SEMUA tapi masih validation phase. Self-service 
  trial OK tapi kasih disclaimer "early access".
- **Business**: ❌ Multi-outlet, HQ dashboard, transfer stok antar 
  outlet, custom domain storefront — SEMUA BELUM ADA. Defer Q3 2026.
  
**Wajib di Business tier**: badge "Coming Q3 2026 — Reserve list 
sekarang dapat diskon 50% Founder Pricing". TIDAK BOLEH jualan seakan-
akan udah live (legal/trust risk).

### 2. Payment Gateway Messaging
- **JANGAN** mention "Midtrans" (deprecated, udah migrate ke Xendit)
- **YANG BENAR**: "Daftar Xendit sendiri (BYOK = Bring Your Own Key), 
  paste API key di Settings → Pengaturan Pembayaran. Uang langsung 
  masuk ke rekening lo, Kasira ZERO komisi selamanya."
- Jelasin dgn 1 paragraf di FAQ: "Kenapa BYOK? Karena: (a) lo settle 
  langsung tanpa lewat Kasira, (b) Kasira gak perlu KYC platform = 
  pricing bisa lebih murah, (c) lo punya kontrol penuh"

### 3. Demo Storefront Disclosure
- Demo storefront link saat ini ke `kasira.online/kasira-coffee`
- Itu DEMO Ivan, bukan real merchant external
- Tetap include sebagai demo, TAPI tambah label kecil: 
  "Demo Storefront (sample data)"

### 4. Testimonial Strategy
- Belum ada cafe pilot beneran (per memory: 6 outlet di DB, 0 real 
  external merchant aktif)
- JANGAN bikin testimonial palsu / generic ("Cafe Joe — Sangat 
  membantu!")
- Solusi: section "Founder Story" — quote dari Ivan tentang kenapa 
  bikin Kasira (POS existing terlalu barat untuk warkop Indonesia)
- Reserve testimonial slot tapi kasih placeholder "Tunggu testimonial 
  cafe pilot pertama — slot reservasi terbuka"

## ✨ DIFFERENTIATOR — Highlight 4 Unique Selling Point

Kompetitor (Moka, Pawoon, Olsera, IsiPOS) gak punya ini — INI YANG 
HARUS DI-ANGKAT:

### 1. Warkop Pay-Items Pattern (UNIQUE INDONESIA — gak ada di kompetitor)
- Real warkop scenario: 3-5 orang nongkrong di meja sama, masing-
  masing bayar item dia sendiri. Ada yang dateng menyusul. Ada yang 
  pulang duluan bayar punya dia.
- Kasira: kasir tinggal centang item yang customer mau bayar → bayar 
  cash/QRIS. Sisa item nempel di tab. Orang berikutnya nyusul tinggal 
  ulangin.
- Kompetitor: split bill cuma "bagi rata" (Western style) — gak 
  humanity Indonesia
- Visual: animasi/screenshot kasir centang menu satu per satu

### 2. BYOK QRIS (Settle Langsung ke Rekening, Zero Komisi)
- Daftar Xendit sendiri (KYC merchant), paste API key di Kasira
- Setiap transaksi QRIS: uang langsung masuk rekening merchant, BYPASS 
  Kasira
- Kasira ZERO komisi selamanya (bukan "free trial 6 bulan, lalu 0.7%")
- Compare dengan kompetitor: Moka 0.7%, Pawoon 0.5% per QRIS

### 3. Margin Tracking Real-Time (Untung-Rugi per Produk)
- Input HPP (harga modal) per produk saat restock
- Dashboard auto-calculate: revenue per produk, HPP, margin %, profit
- Alert: "Kopi Susu margin turun dari 60% ke 45% bulan ini" 
- AI insight (Pro): "Naikin harga Kopi Susu Rp 2k atau ganti supplier 
  susu — saving Rp 12k/hari"
- Kompetitor: kasih revenue tapi gak cost tracking native

### 4. AI Kopi Asisten (Pro tier)
- Owner buka WhatsApp pagi → AI kirim: "Kemarin revenue Rp 2.4jt 
  (-12% vs minggu lalu). Kopi Susu turun 30%. Cek apakah supplier 
  baru jelek? Stock pisang goreng habis 14:30 — order lagi atau 
  remove dari menu?"
- Powered by Claude Sonnet 4.5 (PRICING_COACH intent) + Haiku 4.5 
  (general)
- Bukan generic chatbot — context-aware ke transaksi merchant

## 📦 FEATURES PER TIER (Akurat — sesuai code yang udah live)

### Starter (Rp 99rb/bulan) — READY production
- 1 kasir + 1 outlet
- Max 500 produk (cukup untuk warung/kantin)
- Cash + QRIS via BYOK Xendit
- Storefront online gratis (kasira.online/nama-cafe)
- Offline mode (transaksi saat WiFi mati, auto-sync online)
- Manajemen stok + alert stok rendah
- Margin tracking (HPP per produk, Untung-Rugi report) 
- Shift (buka/tutup kasir + ringkasan cash/QRIS otomatis)
- Laporan harian (revenue, best seller, cash flow)
- Customer database
- Refund flow
- Email support

### Pro (Rp 299rb/bulan) — Live, early access
- Semua Starter +
- Max 5 kasir
- Unlimited produk
- **Tab / Bon dengan Warkop Pay-Items Pattern** ⭐
- **AI Kopi Asisten** via WhatsApp ⭐
- Kitchen Display (Dapur App separate APK)
- Loyalty Points (1 poin/Rp10.000 earn, 1 poin = Rp100 redeem)
- Reservasi Meja (publik via storefront + dashboard kasir)
- Recipe + HPP tracking (resep mode untuk recipe-based menu)
- Knowledge Graph (AI insight basis data graph)
- Priority WhatsApp support
- Pre-launch validation phase: kasih disclaimer halus "Pro features 
  in active development — feedback welcome"

### Business (Rp 499rb/bulan) — COMING Q3 2026
- Semua Pro +
- Multi-outlet management ⏳
- HQ Dashboard konsolidasi ⏳
- Transfer stok antar outlet ⏳
- Custom domain storefront (yourdomain.com instead of kasira.online/x) ⏳
- Prediksi stok & revenue (ML-based forecasting) ⏳
- Dedicated account manager
- **CTA**: "Reserve di Waitlist — Founder Pricing 50% diskon untuk 
  10 cafe pertama yang reserve sekarang"
- Form input nama + WhatsApp + jumlah outlet → Ivan follow-up manual

## 🎨 VISUAL DIRECTION

### Color Palette (keep existing brand)
- Primary: emerald-500/600 (#10b981, #059669) — green Indonesia warm
- Secondary: gray-900 (#111827) — high-contrast text/CTA
- Accent: amber-400 (#fbbf24) — "Pro" badge, populer/featured items
- Pro tier badge: gradient amber-orange (luxurious feel)
- Business tier badge: gradient purple-pink (enterprise feel)
- Background: white + gray-50 alternating sections, bg-gray-950 
  untuk dark sections (pain points, final CTA)

### Typography
- Headline: extrabold (font-black for hero), tight letter-spacing
- Body: regular weight, gray-500/600 untuk secondary text
- Indonesian-friendly font (Inter atau Plus Jakarta Sans — both 
  support Indonesian glyphs cleanly)

### Imagery
- Mockup screenshot Kasira POS (existing di landing — keep + improve)
- Mockup dashboard owner (revenue + best seller chart)
- Mockup storefront mobile view (browser chrome)
- Photo cafe Indonesia (warung kopi vibes, BUKAN stock photo Western 
  Starbucks)
- Icons: Lucide (existing dependency, gak perlu add new dep)

## 🗣️ TONE OF VOICE

### DO ✅
- Bahasa Indonesia casual ("lo", "gak", "bro" sparingly)
- Straight-to-point — Indonesian millennial founder vibe
- Pakai pertanyaan retorik untuk hook ("Capek itung manual?")
- Konkret dengan angka ("setup 5 menit", "save 2 jam/hari")
- Honest tradeoff acknowledged ("Pro masih early access, feedback 
  welcome")

### DON'T ❌
- Corpo-speak ("synergistic", "leverage", "innovative solution")
- Generic claims ("the best POS for cafes")
- Fake urgency ("HARI INI SAJA 50% OFF!!!")
- Aspirasional language untuk feature yang belum ada (NO 
  "Multi-outlet management LIVE NOW" untuk Business)
- Translate dari English literally ("Hubungi kami untuk demo")

## 📐 PAGE STRUCTURE (sections, ordered)

1. **Navbar** sticky transparent → solid on scroll. Items: Fitur, 
   Harga, Demo, Download, Login + CTA "Daftar Gratis"

2. **Hero** — full viewport
   - Badge: "Dibuat khusus untuk F&B Indonesia 🇮🇩"
   - H1: "Buka kasir, bukan spreadsheet" (existing tagline, keep)
   - Subhead: "POS digital + storefront online + AI asisten — semua 
     dalam 1 app. Setup 5 menit, langsung jalan. Untuk warung, cafe, 
     sampai chain F&B."
   - 2 CTA: primary "Coba Gratis 30 Hari" → /register, secondary 
     "Lihat Demo" → /kasira-coffee
   - Trust line: "Tanpa kartu kredit. Cancel kapan saja. 
     Server di Indonesia 🇮🇩"
   - Hero visual: animated mockup (POS phone + dashboard desktop side 
     by side) atau live dashboard preview existing

3. **Pain Point Strip** (dark bg, 4 columns)
   - "Tutup shift selisih cash terus" → "Auto rekap cash + QRIS"
   - "Customer nanya menu, kirim foto satu-satu" → "Storefront online"
   - "Gak tau menu mana untung mana rugi" → "Margin tracking 
     real-time"  
   - "Bayar tip kompetitor 0.7% per QRIS" → "Zero komisi BYOK Xendit"

4. **Differentiator Section** (4 unique selling point dari section 
   "DIFFERENTIATOR" di atas — tiap satu dapet card besar dengan 
   visual + 1 kalimat hook + bullet 3 fact)

5. **3 Feature Deep-Dive** (existing — keep, refine):
   - POS (Smartphone icon, blue)
   - Storefront (Globe icon, violet)
   - Dashboard (BarChart icon, amber)

6. **Feature Grid 8-12 cards** dengan PRO badge (existing, expand 
   include new feature: Margin Tracking, Warkop Pay-Items, BYOK 
   QRIS, AI Kopi Asisten)

7. **How It Works** 3-step (existing — keep)

8. **Pricing Section** — 3 tier:
   - Starter: "Paling Populer" badge + "Mulai Gratis 30 Hari" CTA → 
     /register (self-service)
   - Pro: "Early Access" badge (orange) + "Mulai Pro 30 Hari" CTA → 
     /register?tier=pro (self-service)
   - Business: "Coming Q3 2026" badge (purple) + "Reserve Founder 
     Pricing" CTA → form atau WhatsApp dengan disclaimer "Diskon 
     50% untuk 10 cafe pertama yang reserve"

9. **Founder Story** (instead of fake testimonial)
   - Photo Ivan + quote: "Gue bikin Kasira karena POS existing 
     terlalu 'barat' untuk warkop Indonesia. Split bill bagi rata? 
     Real cafe Indo gak gitu. Customer nanya 'tadi gue makan apa?', 
     kasir checklist, bayar. Itu yang Kasira solve."
   - Subtle: "Pilot launch Q2 2026. Lo bisa jadi cafe pertama yang 
     bantu shape product."

10. **Testimonial Reserve Slot** (2 placeholder cards)
    - "Reserve testimonial slot — bantu kami launch dengan kasih 
      feedback honest. Slot 1, 2, 3 dari 10 cafe pertama yang ikutan 
      pilot dapet 2 bulan gratis Pro."

11. **FAQ** (existing — keep tapi UPDATE Midtrans → Xendit + tambah 
    section BYOK explanation)

12. **Final CTA** (dark bg, existing pattern — keep)
    - Tagline: "Cafe lo layak punya sistem yang proper"
    - 2 CTA: primary "Daftar Gratis Sekarang" + secondary "Tanya via 
      WhatsApp"

13. **Footer** (existing — keep + tambah link ke "Status Page" 
    https://kasira.online/api/health untuk transparency)

## 🛠️ TECHNICAL CONSTRAINTS

- Output: HTML + inline Tailwind classes (compatible Next.js 14 
  + Tailwind 3.x)
- File akan di-replace `/var/www/kasira/app/page.tsx` (React Server 
  Component default) — JANGAN pakai 'use client' kecuali necessary
- Existing components yang harus tetap di-import (jangan inline 
  ulang): `Navbar` from `@/components/landing/Navbar`, `FAQ` from 
  `@/components/landing/FAQ`
- JSON-LD structured data yang udah ada (schema.org SoftwareApplication, 
  Organization, FAQPage) WAJIB tetap include — penting untuk SEO
- Lucide icons sudah di pubspec, pakai itu (jangan tambah icon library 
  baru)
- Mobile-first responsive: test breakpoint sm (640px), md (768px), 
  lg (1024px)

## 🔍 SEO REQUIREMENTS

- Title: "Kasira — Smart POS & Storefront Online untuk Cafe Indonesia"
- Description: 150-160 chars, include "POS", "storefront online", 
  "QRIS", "cafe Indonesia", "AI insight"
- OG image: existing `/opengraph-image.tsx` route (jangan break)
- Robots: allow `/`, block `/dashboard/*` `/api/*` (existing 
  `robots.ts`)
- Structured data: keep 3 JSON-LD blocks (Software, Org, FAQ)

## 📋 OUTPUT EXPECTATION

1. **HTML** clean, semantic, accessible (proper aria-labels, alt 
   text, keyboard nav)
2. **Tailwind classes** — gak pakai @apply atau custom CSS
3. **Inline structure** sesuai page section di atas (13 section 
   ordered)
4. **No external dep** baru (Lucide + existing yang udah ada cukup)
5. **Mobile-first** — test responsive setiap breakpoint
6. **Performance**: lazy-load images, no layout shift, inline critical 
   CSS via Tailwind

## ⚠️ FINAL REMINDER (Honesty Check)

Sebelum output final, audit:
- [ ] Business tier semua features punya badge "Coming Q3 2026" 
  atau di-position sebagai "Reserve Founder Pricing"
- [ ] Pro tier disclaim "Early access" untuk transparency
- [ ] FAQ ganti Midtrans → Xendit + tambah BYOK explanation paragraph
- [ ] Demo storefront kasira-coffee dapat label "Sample data"  
- [ ] Testimonial section adalah placeholder reserve slot, bukan 
  fake quote
- [ ] Founder story honest tentang status pre-pilot
- [ ] CTA per tier match self-service capability:
  * Starter → /register direct
  * Pro → /register?tier=pro direct
  * Business → form reserve, BUKAN /register

Itu prioritas utama. Visual polish & copy refinement boleh creative 
freedom, tapi 7 honesty check di atas non-negotiable.
═══════════════════════════════════════════════════════════════════
```

---

## Setelah dapet output dari Claude Design

1. **Save sebagai HTML file** lokal (e.g., `landing_v2.html`)
2. **Send balik ke gue** (Claude Code) — gue convert ke Next.js 
   component (`app/page.tsx`)
3. **Verify** semua honesty check sebelum deploy:
   - Cek tier Business punya badge "Coming Q3"
   - Cek FAQ udah Xendit (bukan Midtrans)
   - Cek Pro CTA self-service
4. **Deploy**: `docker compose build frontend && docker compose up -d --no-deps frontend`
5. **Smoke test** di browser: hero load, CTA click ke /register, FAQ accordion expand, mobile responsive

## Kalau Claude Design hallucinate / output gak sesuai

- Tunjukin specific section yang miss → "Section pricing Business 
  belum kasih badge Coming Q3, fix"
- Atau export bagian yang OK + iterate yang belum
- Atau pakai output sebagai inspiration → gue manual implement based 
  on design intent
