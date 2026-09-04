'use client';

import { useState, useEffect, useMemo, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { useCart } from '../CartContext';
import { createStorefrontOrder, getStorefront, getTablesWithStatus, requestBillFromStorefront, geoAutocomplete, geoPlace } from '@/app/actions/storefront';
import {
  rp, loadCustomer, saveCustomer, saveLastOrder,
  Card, SectionTitle, Stepper, TopBar, EmptyState, Spinner, btnPrimary, btnSecondary, inputCls,
} from '../_ui';
import { Trash2, Store, Bike, Utensils, QrCode, Banknote, Loader2, Bell, ShieldCheck, ChevronRight, MapPin, LocateFixed, X } from 'lucide-react';

type OrderType = 'pickup' | 'delivery' | 'dine_in';
type PayMethod = 'qris' | 'cash';

/**
 * Halaman pemesanan (checkout). Urutan yang dibaca pelanggan:
 * pesanan, cara menerima, data pemesan, pembayaran, lalu satu tombol kirim.
 *
 * Yang dijanjikan di halaman ini (dikonfirmasi toko dalam N menit, kalau
 * tidak dibatalkan dan QRIS dikembalikan) ditepati backend lewat janitor
 * tasks/online_order_timeout.py. Jangan ubah kalimatnya tanpa ubah janitornya.
 */
export default function CheckoutPage() {
  const params = useParams();
  const slug = params.slug as string;
  const router = useRouter();
  const { items, updateQuantity, removeItem, clearCart, totalPrice, totalItems, tableId, tableName, setTable } = useCart();

  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [storeData, setStoreData] = useState<any>(null);
  const [tables, setTables] = useState<any[]>([]);
  const [isPro, setIsPro] = useState(false);

  const [orderType, setOrderType] = useState<OrderType>('pickup');
  const [payMethod, setPayMethod] = useState<PayMethod>('qris');
  const [customerName, setCustomerName] = useState('');
  const [customerPhone, setCustomerPhone] = useState('');
  const [deliveryAddress, setDeliveryAddress] = useState('');
  // Peta (Google lewat proxy backend). Aktif kalau toko punya kunci Maps.
  // Alur: ketik alamat -> saran -> pilih -> titik + jarak ke toko. Atau
  // "pakai lokasi saya". Tanpa peta, textarea biasa seperti dulu.
  const [addrQuery, setAddrQuery] = useState('');
  const [addrSuggestions, setAddrSuggestions] = useState<{ place_id: string; main: string; secondary: string; description: string }[]>([]);
  const [geoPoint, setGeoPoint] = useState<{ lat: number; lng: number; address: string; distance_km: number | null; within_radius: boolean | null; radius_km: number | null } | null>(null);
  const [geoBusy, setGeoBusy] = useState(false);
  const [geoErr, setGeoErr] = useState<string | null>(null);
  const [addrDetail, setAddrDetail] = useState('');
  const geoSession = useRef(`${Date.now().toString(36)}${Math.random().toString(36).slice(2, 10)}`);
  const [notes, setNotes] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [requestingBill, setRequestingBill] = useState(false);
  const [billRequested, setBillRequested] = useState(false);

  useEffect(() => {
    (async () => {
      const [data, tableData] = await Promise.all([getStorefront(slug), getTablesWithStatus(slug)]);
      if (data) setStoreData(data);
      if (tableData) { setTables(tableData.tables || []); setIsPro(!!tableData.is_pro); }
      setLoading(false);
    })();
    const saved = loadCustomer();
    if (saved) { setCustomerName(saved.name || ''); setCustomerPhone(saved.phone || ''); }
  }, [slug]);

  useEffect(() => { if (tableId && isPro) setOrderType('dine_in'); }, [tableId, isPro]);

  const dineInTab = orderType === 'dine_in' && isPro && !!tableId;
  const mapsEnabled: boolean = !!storeData?.outlet?.maps_enabled;
  const apiBase = (process.env.NEXT_PUBLIC_API_URL || '').replace(/\/$/, '');

  useEffect(() => {
    if (!mapsEnabled || orderType !== 'delivery' || geoPoint || addrQuery.trim().length < 3) { setAddrSuggestions([]); return; }
    const t = setTimeout(async () => {
      const list = await geoAutocomplete(slug, addrQuery, geoSession.current);
      setAddrSuggestions(list);
    }, 350);
    return () => clearTimeout(t);
  }, [addrQuery, mapsEnabled, orderType, geoPoint, slug]);

  const pickPlace = async (opts: { place_id?: string; lat?: number; lng?: number }) => {
    setGeoBusy(true);
    setGeoErr(null);
    const res = await geoPlace(slug, { ...opts, session: geoSession.current });
    setGeoBusy(false);
    if (!res.success || !res.data) { setGeoErr(res.message || 'Alamat tidak ditemukan'); return; }
    setGeoPoint(res.data);
    setAddrSuggestions([]);
    setAddrQuery(res.data.address);
    setDeliveryAddress(res.data.address);
    geoSession.current = `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 10)}`;
  };

  const useMyLocation = () => {
    if (!navigator.geolocation) { setGeoErr('Perangkat tidak mendukung lokasi.'); return; }
    setGeoBusy(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => pickPlace({ lat: pos.coords.latitude, lng: pos.coords.longitude }),
      () => { setGeoBusy(false); setGeoErr('Izin lokasi ditolak. Ketik alamat saja.'); },
      { enableHighAccuracy: true, timeout: 10000 },
    );
  };

  const clearGeo = () => { setGeoPoint(null); setAddrQuery(''); setDeliveryAddress(''); setGeoErr(null); };
  const confirmMinutes: number = storeData?.outlet?.auto_cancel_minutes ?? 10;
  const accepting: boolean = storeData?.outlet?.accepting_orders ?? true;
  // Ongkir (delivery gelombang 1). Tarif dari payload toko; kalau titik alamat
  // sudah dipilih, angka dari server (geo/place) yang dipakai. Server tetap
  // menghitung ulang saat order, ini cuma buat pelanggan lihat sebelum kirim.
  const deliveryCfg = storeData?.outlet?.delivery ?? { enabled: true, fee_base: 0, fee_per_km: 0, free_km: 0, min_order: 0, radius_km: null };
  const deliveryFee: number = orderType === 'delivery'
    ? (geoPoint && typeof (geoPoint as any).delivery_fee === 'number' ? (geoPoint as any).delivery_fee : (deliveryCfg.fee_base || 0))
    : 0;
  const minOrderShort: number = orderType === 'delivery' && deliveryCfg.min_order > 0 && totalPrice < deliveryCfg.min_order
    ? deliveryCfg.min_order - totalPrice : 0;
  const grandTotal = totalPrice + deliveryFee;
  // Metode yang toko aktifkan (mig 103). Storefront cuma nawarin QRIS dan
  // bayar di kasir; transfer dan kartu urusan kasir. QRIS 'manual' = toko
  // pakai QRIS statis miliknya, pelanggan kirim bukti lewat WhatsApp.
  const storeMethods: string[] = storeData?.outlet?.payment_methods ?? ['cash', 'qris'];
  const qrisOffered = storeMethods.includes('qris');
  const qrisManual = (storeData?.outlet?.qris_channel ?? 'manual') === 'manual';
  useEffect(() => { if (storeData && !qrisOffered) setPayMethod('cash'); }, [storeData, qrisOffered]);

  const phoneOk = /^0?8\d{8,12}$/.test(customerPhone) || /^628\d{8,12}$/.test(customerPhone);
  const validation = useMemo(() => {
    if (customerName.trim().length < 2) return 'Isi nama pemesan.';
    if (!phoneOk) return 'Isi nomor WhatsApp yang aktif, contoh 0812xxxxxxx.';
    if (orderType === 'delivery' && deliveryAddress.trim().length < 8) return 'Isi alamat pengantaran beserta patokan.';
    if (orderType === 'delivery' && geoPoint && geoPoint.within_radius === false) return `Alamat ${geoPoint.distance_km} km dari toko, di luar jangkauan antar (${geoPoint.radius_km} km).`;
    if (orderType === 'delivery' && deliveryCfg.enabled === false) return 'Toko sedang tidak melayani antar. Pilih ambil sendiri.';
    if (minOrderShort > 0) return `Minimal pesanan untuk antar ${rp(deliveryCfg.min_order)}. Kurang ${rp(minOrderShort)}.`;
    if (orderType === 'dine_in' && !tableId) return 'Pilih meja Anda.';
    return null;
  }, [customerName, phoneOk, orderType, deliveryAddress, tableId, minOrderShort, deliveryCfg.enabled]);

  if (loading) return <Spinner label="Menyiapkan pemesanan" />;

  if (items.length === 0) {
    return (
      <>
        <TopBar back={`/${slug}${tableId ? `?table=${tableId}` : ''}`} title={<span className="font-display font-extrabold text-[15px] text-[var(--text-strong)]">Pemesanan</span>} />
        <EmptyState
          title="Belum ada menu dipilih"
          body="Pilih menu dari halaman toko, lalu kembali ke sini untuk menyelesaikan pemesanan."
          action={
            <div className="flex flex-col items-center gap-3">
              <Link href={`/${slug}${tableId ? `?table=${tableId}` : ''}`} className={btnPrimary}>Lihat menu</Link>
              {tableId && isPro && (
                <button onClick={handleRequestBill} disabled={requestingBill || billRequested} className={btnSecondary}>
                  <Bell className="w-4 h-4" /> {billRequested ? 'Kasir sedang menuju meja Anda' : 'Minta tagihan meja'}
                </button>
              )}
            </div>
          }
        />
      </>
    );
  }

  async function handleRequestBill() {
    if (!tableId) return;
    setRequestingBill(true);
    const res = await requestBillFromStorefront(slug, tableId);
    setRequestingBill(false);
    if (res.success) setBillRequested(true); else setError(res.message);
  }

  const submit = async () => {
    if (validation) { setError(validation); return; }
    setError(null);
    setSubmitting(true);
    const phone = customerPhone.startsWith('0') ? '62' + customerPhone.slice(1) : customerPhone;
    const payload = {
      order_type: orderType,
      customer_name: customerName.trim(),
      customer_phone: phone,
      delivery_address: orderType === 'delivery' ? `${deliveryAddress.trim()}${addrDetail.trim() ? ` (${addrDetail.trim()})` : ''}` : null,
      ...(orderType === 'delivery' && geoPoint ? { delivery_lat: geoPoint.lat, delivery_lng: geoPoint.lng } : {}),
      table_id: orderType === 'dine_in' ? tableId : null,
      notes: notes.trim() || null,
      items: items.map((item) => ({
        product_id: item.productId,
        ...(item.variantId ? { product_variant_id: item.variantId } : {}),
        qty: item.quantity,
        notes: '',
      })),
      payment_method: dineInTab ? 'cash' : payMethod,
      idempotency_key: `${slug}-${phone}-${Date.now()}`,
    };
    const res = await createStorefrontOrder(slug, payload);
    if (res.success) {
      saveCustomer({ name: customerName.trim(), phone: customerPhone });
      saveLastOrder(slug, res.data.order_id, res.data.display_number);
      clearCart();
      router.push(`/${slug}/order/${res.data.order_id}`);
    } else {
      setError(res.message || 'Pesanan belum terkirim. Coba lagi.');
      setSubmitting(false);
    }
  };

  const typeOptions: { id: OrderType; label: string; hint: string; icon: any; show: boolean }[] = [
    { id: 'dine_in', label: 'Makan di tempat', hint: tableName || 'Pilih meja', icon: Utensils, show: isPro && tables.length > 0 },
    { id: 'pickup', label: 'Ambil sendiri', hint: 'Ambil di toko', icon: Store, show: true },
    { id: 'delivery', label: 'Antar', hint: deliveryCfg.fee_base > 0 ? `Ongkir mulai ${rp(deliveryCfg.fee_base)}` : 'Ke alamat Anda', icon: Bike, show: deliveryCfg.enabled !== false },
  ];
  const cashLabel = orderType === 'delivery' ? 'Bayar saat pesanan diterima' : 'Bayar di kasir';
  const submitLabel = dineInTab ? 'Kirim pesanan ke meja' : payMethod === 'qris' && !qrisManual ? 'Lanjut bayar QRIS' : 'Kirim pesanan';

  return (
    <div className="pb-36 md:pb-12">
      <TopBar
        back={`/${slug}${tableId ? `?table=${tableId}` : ''}`}
        title={<span className="font-display font-extrabold text-[15px] text-[var(--text-strong)]">Pemesanan</span>}
        right={<span className="text-sm text-[var(--text-muted)]">{totalItems} item</span>}
      />

      <main className="max-w-5xl mx-auto px-4 pt-5 md:grid md:grid-cols-[1fr_380px] md:gap-8 items-start">
        <div className="space-y-4">
          {/* 1. Pesanan */}
          <Card className="p-5">
            <SectionTitle step={1} title="Pesanan Anda" />
            <ul className="divide-y divide-[var(--border-subtle)]">
              {items.map((item) => (
                <li key={item.id} className="py-3 flex items-center gap-3">
                  <div className="w-14 h-14 rounded-2xl bg-[var(--bg-subtle)] overflow-hidden shrink-0">
                    {item.image_url
                      ? <img src={item.image_url} alt={item.name} className="w-full h-full object-cover" />
                      : <div className="w-full h-full flex items-center justify-center font-display font-extrabold text-[var(--border-default)] text-xl">{item.name.charAt(0)}</div>}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-bold text-[var(--text-strong)] leading-snug">{item.name}</p>
                    <p className="text-sm text-[var(--text-muted)]">{rp(item.price)}</p>
                  </div>
                  <div className="flex flex-col items-end gap-1.5">
                    <Stepper qty={item.quantity} onDec={() => updateQuantity(item.id, item.quantity - 1)} onInc={() => updateQuantity(item.id, item.quantity + 1)} />
                    <button onClick={() => removeItem(item.id)} className="text-xs text-[var(--text-muted)] hover:text-[var(--danger)] inline-flex items-center gap-1"><Trash2 className="w-3 h-3" /> Hapus</button>
                  </div>
                </li>
              ))}
            </ul>
            <Link href={`/${slug}${tableId ? `?table=${tableId}` : ''}`} className="mt-2 inline-flex items-center gap-1 text-sm font-semibold text-[var(--text-strong)]">
              Tambah menu lain <ChevronRight className="w-4 h-4" />
            </Link>
          </Card>

          {/* 2. Cara menerima */}
          <Card className="p-5">
            <SectionTitle step={2} title="Cara menerima pesanan" />
            <div className={`grid gap-2 ${typeOptions.filter(t => t.show).length === 3 ? 'grid-cols-3' : 'grid-cols-2'}`}>
              {typeOptions.filter((t) => t.show).map((t) => {
                const active = orderType === t.id;
                return (
                  <button key={t.id} type="button" onClick={() => setOrderType(t.id)}
                    className={`flex flex-col items-start gap-2 p-3.5 rounded-2xl border-2 text-left transition ${active ? 'border-[var(--text-strong)] bg-[var(--surface-card)]' : 'border-[var(--border-subtle)] hover:border-[var(--border-default)]'}`}>
                    <t.icon className={`w-5 h-5 ${active ? 'text-[var(--text-strong)]' : 'text-[var(--text-muted)]'}`} />
                    <span>
                      <span className="block text-sm font-bold text-[var(--text-strong)]">{t.label}</span>
                      <span className="block text-xs text-[var(--text-muted)]">{t.hint}</span>
                    </span>
                  </button>
                );
              })}
            </div>

            {orderType === 'dine_in' && (
              <div className="mt-4">
                <p className="text-sm font-semibold text-[var(--text-strong)] mb-2">Meja</p>
                <div className="grid grid-cols-3 sm:grid-cols-4 gap-2 max-h-48 overflow-y-auto pr-1">
                  {tables.filter((t: any) => t.status === 'available' || t.status === 'occupied').map((t: any) => (
                    <button key={t.id} type="button" onClick={() => setTable(t.id, `Meja ${t.name}`)}
                      className={`p-3 rounded-xl border text-center text-sm transition ${tableId === t.id ? 'border-[var(--text-strong)] bg-[var(--surface-inverse)] text-white font-bold' : 'border-[var(--border-subtle)] text-[var(--text-body)] hover:border-[var(--border-default)]'}`}>
                      Meja {t.name}
                      <span className={`block text-[11px] ${tableId === t.id ? 'text-white/70' : 'text-[var(--text-muted)]'}`}>{t.capacity} kursi</span>
                    </button>
                  ))}
                </div>
                {dineInTab && <p className="mt-3 text-xs text-[var(--text-muted)]">Pesanan masuk ke tagihan meja dan dibayar di kasir saat selesai.</p>}
              </div>
            )}

            {orderType === 'delivery' && !mapsEnabled && (
              <div className="mt-4">
                <label className="block text-sm font-semibold text-[var(--text-strong)] mb-1.5">Alamat pengantaran</label>
                <textarea rows={3} value={deliveryAddress} onChange={(e) => setDeliveryAddress(e.target.value)}
                  placeholder="Nama jalan, nomor rumah, dan patokan terdekat" className={`${inputCls} resize-none`} />
                <p className="mt-1.5 text-xs text-[var(--text-muted)]">Ongkos kirim, bila ada, disepakati langsung dengan toko lewat WhatsApp.</p>
              </div>
            )}
            {orderType === 'delivery' && mapsEnabled && (
              <div className="mt-4">
                <label className="block text-sm font-semibold text-[var(--text-strong)] mb-1.5">Alamat pengantaran</label>
                {!geoPoint ? (
                  <div className="relative">
                    <div className="flex gap-2">
                      <div className="relative flex-1">
                        <MapPin className="w-4 h-4 text-[var(--text-muted)] absolute left-3.5 top-1/2 -translate-y-1/2" />
                        <input value={addrQuery} onChange={(e) => setAddrQuery(e.target.value)} placeholder="Ketik nama jalan atau tempat"
                          className={`${inputCls} pl-10`} autoComplete="off" />
                      </div>
                      <button type="button" onClick={useMyLocation} disabled={geoBusy}
                        className="shrink-0 inline-flex items-center gap-1.5 px-3 rounded-xl border border-[var(--border-subtle)] text-sm font-semibold text-[var(--text-strong)] hover:bg-[var(--bg-subtle)] disabled:opacity-50">
                        {geoBusy ? <Loader2 className="w-4 h-4 animate-spin" /> : <LocateFixed className="w-4 h-4" />}
                        <span className="hidden sm:inline">Lokasi saya</span>
                      </button>
                    </div>
                    {addrSuggestions.length > 0 && (
                      <ul className="absolute z-20 left-0 right-0 mt-1 rounded-2xl bg-[var(--surface-card)] border border-[var(--border-subtle)] shadow-lg overflow-hidden">
                        {addrSuggestions.map((sg) => (
                          <li key={sg.place_id}>
                            <button type="button" onClick={() => pickPlace({ place_id: sg.place_id })}
                              className="w-full text-left px-4 py-2.5 hover:bg-[var(--bg-subtle)] flex gap-2.5">
                              <MapPin className="w-4 h-4 mt-0.5 shrink-0 text-[var(--text-muted)]" />
                              <span className="min-w-0">
                                <span className="block text-sm font-semibold text-[var(--text-strong)] truncate">{sg.main}</span>
                                <span className="block text-xs text-[var(--text-muted)] truncate">{sg.secondary}</span>
                              </span>
                            </button>
                          </li>
                        ))}
                      </ul>
                    )}
                    {geoErr && <p className="mt-1.5 text-xs text-[var(--danger)]">{geoErr}</p>}
                    <p className="mt-1.5 text-xs text-[var(--text-muted)]">Pilih dari saran supaya kurir dapat titik yang tepat, atau tekan Lokasi saya.</p>
                  </div>
                ) : (
                  <div className="rounded-2xl border border-[var(--border-subtle)] overflow-hidden">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img src={`${apiBase}/connect/geo/static?lat=${geoPoint.lat}&lng=${geoPoint.lng}&zoom=16&w=640&h=260`} alt="Peta alamat" className="w-full h-36 object-cover" />
                    <div className="p-3 flex items-start gap-2">
                      <MapPin className="w-4 h-4 mt-0.5 shrink-0 text-[var(--text-muted)]" />
                      <div className="min-w-0 flex-1 text-sm">
                        <p className="font-semibold text-[var(--text-strong)]">{geoPoint.address || 'Titik terpilih'}</p>
                        {geoPoint.distance_km != null && (
                          <p className={`text-xs mt-0.5 ${geoPoint.within_radius === false ? 'text-[var(--danger)] font-semibold' : 'text-[var(--text-muted)]'}`}>
                            {geoPoint.distance_km} km dari toko{geoPoint.within_radius === false ? `, di luar jangkauan antar (${geoPoint.radius_km} km)` : ''}
                          </p>
                        )}
                      </div>
                      <button type="button" onClick={clearGeo} className="p-1 rounded-full hover:bg-[var(--bg-subtle)]" aria-label="Ganti alamat"><X className="w-4 h-4 text-[var(--text-muted)]" /></button>
                    </div>
                  </div>
                )}
                <input value={addrDetail} onChange={(e) => setAddrDetail(e.target.value)} placeholder="Nomor rumah, blok, patokan, warna pagar" className={`${inputCls} mt-2`} />
                <p className="mt-1.5 text-xs text-[var(--text-muted)]">Ongkos kirim, bila ada, disepakati langsung dengan toko lewat WhatsApp.</p>
              </div>
            )}
            {orderType === 'pickup' && (
              <p className="mt-4 text-sm text-[var(--text-muted)]">Toko memberi perkiraan waktu siap saat mengonfirmasi pesanan. Anda akan menerima kabar lewat WhatsApp.</p>
            )}
          </Card>

          {/* 3. Data pemesan */}
          <Card className="p-5">
            <SectionTitle step={3} title="Data pemesan" hint="Nomor WhatsApp dipakai untuk kabar status pesanan, bukan untuk promosi." />
            <div className="grid sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-semibold text-[var(--text-strong)] mb-1.5">Nama</label>
                <input type="text" value={customerName} onChange={(e) => setCustomerName(e.target.value)} placeholder="Nama Anda" className={inputCls} autoComplete="name" />
              </div>
              <div>
                <label className="block text-sm font-semibold text-[var(--text-strong)] mb-1.5">Nomor WhatsApp</label>
                <input type="tel" inputMode="numeric" value={customerPhone} onChange={(e) => setCustomerPhone(e.target.value.replace(/\D/g, ''))} placeholder="0812xxxxxxxx" className={inputCls} autoComplete="tel" />
              </div>
            </div>
            <div className="mt-3">
              <label className="block text-sm font-semibold text-[var(--text-strong)] mb-1.5">Catatan untuk toko <span className="font-normal text-[var(--text-muted)]">(opsional)</span></label>
              <input type="text" value={notes} onChange={(e) => setNotes(e.target.value)} maxLength={300} placeholder="Contoh: gula sedikit, tanpa es, titip di satpam" className={inputCls} />
            </div>
          </Card>

          {/* 4. Pembayaran */}
          {!dineInTab && (
            <Card className="p-5">
              <SectionTitle step={4} title="Pembayaran" />
              <div className="grid grid-cols-2 gap-2">
                {([
                  { id: 'qris', label: 'QRIS', hint: qrisManual ? 'Pindai QRIS toko, kirim bukti bayar' : 'Semua e-wallet dan m-banking', icon: QrCode },
                  { id: 'cash', label: cashLabel, hint: 'Tunai atau sesuai kesepakatan', icon: Banknote },
                ] as const).filter((m) => m.id !== 'qris' || qrisOffered).map((m) => {
                  const active = payMethod === m.id;
                  return (
                    <button key={m.id} type="button" onClick={() => setPayMethod(m.id)}
                      className={`flex flex-col items-start gap-2 p-3.5 rounded-2xl border-2 text-left transition ${active ? 'border-[var(--text-strong)]' : 'border-[var(--border-subtle)] hover:border-[var(--border-default)]'}`}>
                      <m.icon className={`w-5 h-5 ${active ? 'text-[var(--text-strong)]' : 'text-[var(--text-muted)]'}`} />
                      <span>
                        <span className="block text-sm font-bold text-[var(--text-strong)]">{m.label}</span>
                        <span className="block text-xs text-[var(--text-muted)]">{m.hint}</span>
                      </span>
                    </button>
                  );
                })}
              </div>
              {payMethod === 'qris' && qrisOffered && (
                <p className="mt-3 text-xs text-[var(--text-muted)]">
                  {qrisManual
                    ? 'QRIS toko tampil di halaman berikutnya. Setelah membayar, kirim bukti ke WhatsApp toko lewat tombol yang tersedia.'
                    : 'Kode QR muncul di halaman berikutnya dan berlaku 15 menit.'}
                </p>
              )}
            </Card>
          )}
        </div>

        {/* Ringkasan */}
        <aside className="hidden md:block sticky top-20">
          <Summary />
        </aside>
      </main>

      {/* Mobile: total + kirim */}
      <div className="md:hidden fixed bottom-0 left-0 right-0 z-40 bg-[var(--surface-card)] border-t border-[var(--border-subtle)] px-4 pt-3 pb-5 shadow-[var(--shadow-lg)]">
        {error && <p className="text-sm text-[var(--danger)] mb-2">{error}</p>}
        <div className="flex items-center justify-between mb-3">
          <span className="text-sm text-[var(--text-muted)]">Total{deliveryFee > 0 ? ` termasuk ongkir ${rp(deliveryFee)}` : ''}</span>
          <span className="text-xl font-extrabold text-[var(--text-strong)]">{rp(grandTotal)}</span>
        </div>
        <button onClick={submit} disabled={submitting || !accepting} className={`${btnPrimary} w-full`}>
          {submitting ? <Loader2 className="w-5 h-5 animate-spin" /> : submitLabel}
        </button>
        <p className="mt-2.5 text-[11px] text-[var(--text-muted)] text-center leading-snug">
          Toko mengonfirmasi dalam {confirmMinutes} menit. Bila tidak, pesanan dibatalkan otomatis dan pembayaran QRIS dikembalikan.
        </p>
      </div>
    </div>
  );

  function Summary() {
    return (
      <Card className="p-5 space-y-4">
        <h2 className="font-display font-extrabold text-[17px] text-[var(--text-strong)]">Ringkasan</h2>
        <ul className="space-y-1.5 text-sm">
          {items.map((i) => (
            <li key={i.id} className="flex justify-between gap-3">
              <span className="text-[var(--text-body)] truncate">{i.quantity}x {i.name}</span>
              <span className="text-[var(--text-strong)] font-semibold shrink-0">{rp(i.price * i.quantity)}</span>
            </li>
          ))}
        </ul>
        {orderType === 'delivery' && (
          <div className="pt-3 border-t border-[var(--border-subtle)] space-y-1 text-sm">
            <div className="flex justify-between"><span className="text-[var(--text-muted)]">Pesanan</span><span className="text-[var(--text-strong)] font-semibold">{rp(totalPrice)}</span></div>
            <div className="flex justify-between">
              <span className="text-[var(--text-muted)]">Ongkir{geoPoint?.distance_km != null ? ` (${geoPoint.distance_km} km)` : ''}</span>
              <span className="text-[var(--text-strong)] font-semibold">{deliveryFee > 0 ? rp(deliveryFee) : 'Gratis'}</span>
            </div>
            {!geoPoint && deliveryCfg.fee_per_km > 0 && <p className="text-[11px] text-[var(--text-muted)]">Ongkir pasti dihitung setelah alamat dipilih.</p>}
          </div>
        )}
        <div className="pt-3 border-t border-[var(--border-subtle)] flex justify-between items-center">
          <span className="text-sm text-[var(--text-muted)]">Total</span>
          <span className="text-xl font-extrabold text-[var(--text-strong)]">{rp(grandTotal)}</span>
        </div>
        {error && <p className="text-sm text-[var(--danger)]">{error}</p>}
        <button onClick={submit} disabled={submitting || !accepting} className={`${btnPrimary} w-full`}>
          {submitting ? <Loader2 className="w-5 h-5 animate-spin" /> : submitLabel}
        </button>
        {dineInTab && tableId && (
          <button onClick={handleRequestBill} disabled={requestingBill || billRequested} className={`${btnSecondary} w-full`}>
            <Bell className="w-4 h-4" /> {billRequested ? 'Kasir sedang menuju meja Anda' : 'Minta tagihan meja'}
          </button>
        )}
        <p className="text-xs text-[var(--text-muted)] leading-relaxed flex gap-2">
          <ShieldCheck className="w-4 h-4 shrink-0 text-[var(--success)]" />
          <span>Toko mengonfirmasi dalam {confirmMinutes} menit. Bila tidak, pesanan dibatalkan otomatis dan pembayaran QRIS dikembalikan.</span>
        </p>
      </Card>
    );
  }
}
