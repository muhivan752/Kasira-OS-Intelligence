'use client';

import { useState, useEffect, useMemo } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { getStorefront } from '@/app/actions/storefront';
import { useCart, cartLineId } from './CartContext';
import {
  rp, waNumber, waLink, loadLastOrder,
  StoreAvatar, StatusPill, Card, Stepper, Sheet, PoweredBy, EmptyState, Spinner, btnPrimary,
} from './_ui';
import { MessageCircle, MapPin, Clock, Search, CalendarDays, ShoppingBag, Utensils, ChevronRight, BadgeCheck, Timer, QrCode } from 'lucide-react';

/**
 * Halaman menu toko. Satu tata letak untuk semua tier: pelanggan nggak
 * peduli paket langganan toko, mereka peduli menunya jelas dan pesannya
 * cepat. Fitur Pro (reservasi, meja) cuma menambah tombol, bukan mengganti
 * tampilan.
 *
 * SEMUA hook di atas `return` awal (React #310, CLAUDE.md #31).
 */
export default function StorefrontPage() {
  const params = useParams();
  const slug = params.slug as string;
  const router = useRouter();
  const { items, addItem, updateQuantity, totalItems, totalPrice, tableId, tableName } = useCart();

  const [loading, setLoading] = useState(true);
  const [storeData, setStoreData] = useState<any>(null);
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [search, setSearch] = useState('');
  const [variantProduct, setVariantProduct] = useState<any>(null);
  const [lastOrder, setLastOrder] = useState<{ id: string; displayNumber: number } | null>(null);

  useEffect(() => {
    if (!slug) return;
    (async () => {
      const data = await getStorefront(slug);
      if (data) setStoreData(data);
      setLoading(false);
    })();
    setLastOrder(loadLastOrder(slug));
  }, [slug]);

  const products: any[] = storeData?.products ?? [];
  const categories: any[] = storeData?.categories ?? [];

  const grouped = useMemo(() => {
    const q = search.trim().toLowerCase();
    const visible = products.filter((p) =>
      (selectedCategory === 'all' || p.category_id === selectedCategory) &&
      (!q || p.name.toLowerCase().includes(q) || (p.description || '').toLowerCase().includes(q)),
    );
    if (selectedCategory !== 'all' || q) return [{ id: 'filtered', name: null, items: visible }];
    const byCat = new Map<string, any[]>();
    for (const p of visible) {
      const k = p.category_id || '_none';
      byCat.set(k, [...(byCat.get(k) || []), p]);
    }
    const out: { id: string; name: string | null; items: any[] }[] = [];
    for (const c of categories) if (byCat.has(c.id)) out.push({ id: c.id, name: c.name, items: byCat.get(c.id)! });
    if (byCat.has('_none')) out.push({ id: '_none', name: categories.length ? 'Lainnya' : null, items: byCat.get('_none')! });
    return out;
  }, [products, categories, selectedCategory, search]);

  if (loading) return <Spinner label="Memuat menu" />;
  if (!storeData) {
    return (
      <EmptyState
        title="Toko tidak ditemukan"
        body="Tautan yang Anda buka tidak valid atau toko sudah tidak aktif. Periksa kembali alamat yang Anda terima."
      />
    );
  }

  const { outlet } = storeData;
  const accepting: boolean = outlet.accepting_orders ?? (outlet.is_open && (outlet.online_orders_enabled ?? true));
  const confirmMinutes: number = outlet.auto_cancel_minutes ?? 10;
  const wa = waNumber(outlet.whatsapp);
  const cartHref = `/${slug}/cart${tableId ? `?table=${tableId}` : ''}`;

  const qtyOf = (product: any) => {
    if ((product.variants?.length ?? 0) > 0) {
      return items.filter((i) => i.productId === product.id).reduce((s, i) => s + i.quantity, 0);
    }
    return items.find((i) => i.id === cartLineId(product.id))?.quantity ?? 0;
  };

  const addLine = (product: any, variant: any | null) => {
    addItem({
      id: cartLineId(product.id, variant?.id),
      productId: product.id,
      variantId: variant?.id,
      variantName: variant?.name,
      name: variant ? `${product.name} (${variant.name})` : product.name,
      price: variant ? variant.price : product.price,
      quantity: 1,
      image_url: product.image_url,
    });
  };

  const handleAdd = (product: any) => {
    if (!accepting || !product.is_available) return;
    if ((product.variants?.length ?? 0) > 0) { setVariantProduct(product); return; }
    addLine(product, null);
  };

  const closedReason = !outlet.is_open
    ? `Toko sedang tutup. Menu tetap bisa dilihat${outlet.next_open ? `. ${outlet.next_open}` : ', pemesanan dibuka kembali pada jam operasional'}.`
    : !accepting
      ? 'Toko sedang tidak menerima pesanan online. Untuk memesan, hubungi toko lewat WhatsApp.'
      : null;

  return (
    <div className="pb-32 md:pb-12">
      {/* Bilah atas */}
      <header className="sticky top-0 z-30 bg-[color-mix(in_srgb,var(--bg-base)_88%,transparent)] backdrop-blur-md border-b border-[var(--border-subtle)]">
        <div className="max-w-6xl mx-auto px-4 h-14 flex items-center gap-3">
          <StoreAvatar name={outlet.name} size={32} />
          <p className="font-display font-extrabold text-[15px] text-[var(--text-strong)] truncate flex-1">{outlet.name}</p>
          {outlet.reservation_enabled && (
            <button onClick={() => router.push(`/${slug}/booking`)} className="hidden sm:inline-flex items-center gap-1.5 text-sm font-semibold text-[var(--text-strong)] px-3 py-1.5 rounded-full hover:bg-[var(--bg-subtle)]">
              <CalendarDays className="w-4 h-4" /> Reservasi
            </button>
          )}
          {wa && (
            <a href={waLink(wa, `Halo ${outlet.name}, saya ingin bertanya tentang menu.`)} target="_blank" rel="noreferrer"
              className="inline-flex items-center gap-1.5 text-sm font-semibold text-white bg-[#25D366] px-3 py-1.5 rounded-full hover:opacity-90">
              <MessageCircle className="w-4 h-4" /> <span className="hidden sm:inline">WhatsApp</span>
            </a>
          )}
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4">
        {/* Sampul + identitas */}
        <section className="mt-4">
          <div className="relative aspect-[16/7] sm:aspect-[16/5] rounded-[28px] overflow-hidden bg-[var(--surface-inverse)]">
            {outlet.cover_image_url ? (
              <img src={outlet.cover_image_url} alt={outlet.name} className="w-full h-full object-cover" />
            ) : (
              <div className="w-full h-full" style={{ background: 'var(--gradient-aurora)', opacity: 0.9 }} />
            )}
            <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-black/10 to-transparent" />
            <div className="absolute left-4 right-4 bottom-4 sm:left-6 sm:bottom-6 flex items-end gap-4">
              <StoreAvatar name={outlet.name} size={56} />
              <div className="min-w-0 text-white">
                <h1 className="font-display font-extrabold text-2xl sm:text-4xl tracking-tight leading-none truncate">{outlet.name}</h1>
                <div className="mt-2 flex flex-wrap items-center gap-2 text-xs sm:text-sm text-white/85">
                  {outlet.address && <span className="inline-flex items-center gap-1"><MapPin className="w-3.5 h-3.5" />{outlet.address}</span>}
                  {(outlet.hours_today || outlet.opening_hours) && <span className="inline-flex items-center gap-1"><Clock className="w-3.5 h-3.5" />{outlet.hours_today || outlet.opening_hours}</span>}
                </div>
              </div>
            </div>
          </div>

          <div className="mt-4 flex flex-wrap items-center gap-2">
            {outlet.is_open
              ? <StatusPill tone="open">{accepting ? 'Buka, menerima pesanan' : 'Buka'}</StatusPill>
              : <StatusPill tone="closed">Tutup</StatusPill>}
            <span className="inline-flex items-center gap-1.5 text-xs font-medium text-[var(--text-muted)] px-2.5 py-1 rounded-full bg-[var(--surface-card)] border border-[var(--border-subtle)]">
              <Timer className="w-3.5 h-3.5" /> Dikonfirmasi toko dalam {confirmMinutes} menit
            </span>
            <span className="inline-flex items-center gap-1.5 text-xs font-medium text-[var(--text-muted)] px-2.5 py-1 rounded-full bg-[var(--surface-card)] border border-[var(--border-subtle)]">
              <QrCode className="w-3.5 h-3.5" /> QRIS atau bayar di kasir
            </span>
            <span className="inline-flex items-center gap-1.5 text-xs font-medium text-[var(--text-muted)] px-2.5 py-1 rounded-full bg-[var(--surface-card)] border border-[var(--border-subtle)]">
              <BadgeCheck className="w-3.5 h-3.5" /> Harga sama dengan di toko
            </span>
          </div>

          {outlet.latitude != null && outlet.longitude != null && outlet.maps_enabled && (
            <a href={`https://www.google.com/maps/dir/?api=1&destination=${outlet.latitude},${outlet.longitude}`} target="_blank" rel="noreferrer"
              className="mt-4 flex items-center gap-3 rounded-2xl bg-[var(--surface-card)] border border-[var(--border-subtle)] p-2 pr-4 hover:bg-[var(--bg-subtle)]">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={`${(process.env.NEXT_PUBLIC_API_URL || '').replace(/\/$/, '')}/connect/geo/static?lat=${outlet.latitude}&lng=${outlet.longitude}&zoom=15&w=240&h=120`}
                alt="Lokasi toko" className="w-28 h-14 rounded-xl object-cover shrink-0" />
              <span className="min-w-0 flex-1 text-sm">
                <span className="block font-semibold text-[var(--text-strong)]">Petunjuk arah ke toko</span>
                <span className="block text-xs text-[var(--text-muted)] truncate">{outlet.address || 'Buka di Google Maps'}{outlet.delivery_radius_km ? ` · Antar sampai ${outlet.delivery_radius_km} km` : ''}</span>
              </span>
              <ChevronRight className="w-4 h-4 text-[var(--text-muted)] shrink-0" />
            </a>
          )}
          {closedReason && (
            <div className="mt-4 rounded-2xl bg-[color-mix(in_srgb,var(--warning)_14%,white)] text-[var(--text-strong)] px-4 py-3 text-sm">
              {closedReason}
            </div>
          )}
          {tableId && (
            <div className="mt-4 rounded-2xl bg-[var(--surface-inverse)] text-white px-4 py-3 text-sm flex items-center gap-3">
              <Utensils className="w-4 h-4 shrink-0" />
              <span><b>{tableName || 'Meja Anda'}</b>. Pesanan diantar ke meja dan dibayar di kasir.</span>
            </div>
          )}
          {lastOrder && (
            <Link href={`/${slug}/order/${lastOrder.id}`} className="mt-4 flex items-center justify-between rounded-2xl bg-[var(--surface-card)] border border-[var(--border-subtle)] px-4 py-3 text-sm hover:bg-[var(--bg-subtle)]">
              <span className="text-[var(--text-body)]">Pesanan terakhir Anda <b className="text-[var(--text-strong)]">#{lastOrder.displayNumber}</b></span>
              <span className="inline-flex items-center gap-1 font-semibold text-[var(--text-strong)]">Lihat status <ChevronRight className="w-4 h-4" /></span>
            </Link>
          )}
        </section>

        {/* Pencarian + kategori */}
        <div className="sticky top-14 z-20 -mx-4 px-4 py-3 bg-[color-mix(in_srgb,var(--bg-base)_92%,transparent)] backdrop-blur-md mt-6">
          <div className="flex gap-2 items-center">
            <label className="relative flex-1 max-w-xs">
              <Search className="w-4 h-4 text-[var(--text-muted)] absolute left-3.5 top-1/2 -translate-y-1/2" />
              <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Cari menu"
                className="w-full pl-10 pr-4 py-2.5 rounded-full bg-[var(--surface-card)] border border-[var(--border-subtle)] text-sm outline-none focus:border-[var(--focus-ring)]" />
            </label>
            <div className="flex overflow-x-auto hide-scrollbar gap-2 flex-1">
              {[{ id: 'all', name: 'Semua' }, ...categories].map((cat: any) => (
                <button key={cat.id} onClick={() => setSelectedCategory(cat.id)}
                  className={`px-4 py-2 rounded-full text-sm font-semibold whitespace-nowrap transition ${selectedCategory === cat.id ? 'bg-[var(--surface-inverse)] text-white' : 'bg-[var(--surface-card)] border border-[var(--border-subtle)] text-[var(--text-body)] hover:bg-[var(--bg-subtle)]'}`}>
                  {cat.name}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="md:grid md:grid-cols-[1fr_340px] md:gap-8 items-start">
          {/* Daftar menu */}
          <div className="space-y-8">
            {grouped.every((g) => g.items.length === 0) ? (
              <Card className="py-14 text-center text-[var(--text-muted)]">Tidak ada menu yang cocok.</Card>
            ) : grouped.map((group) => (
              <section key={group.id}>
                {group.name && <h2 className="font-display font-extrabold text-xl text-[var(--text-strong)] mb-3 tracking-tight">{group.name}</h2>}
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 sm:gap-4">
                  {group.items.map((product: any) => {
                    const qty = qtyOf(product);
                    const soldOut = !product.is_available;
                    const hasVariants = (product.variants?.length ?? 0) > 0;
                    return (
                      <article key={product.id} className={`group bg-[var(--surface-card)] border border-[var(--border-subtle)] rounded-[22px] overflow-hidden flex flex-col shadow-[var(--shadow-xs)] hover:shadow-[var(--shadow-md)] transition ${soldOut ? 'opacity-70' : ''}`}>
                        <div className="relative aspect-square bg-[var(--bg-subtle)] overflow-hidden">
                          {product.image_url
                            ? <img src={product.image_url} alt={product.name} loading="lazy" className="w-full h-full object-cover group-hover:scale-[1.03] transition duration-500" />
                            : <div className="w-full h-full flex items-center justify-center text-4xl font-display font-extrabold text-[var(--border-default)]">{product.name.charAt(0)}</div>}
                          {soldOut && (
                            <span className="absolute top-2 left-2 px-2.5 py-1 rounded-full bg-[var(--surface-inverse)] text-white text-[11px] font-bold">Habis</span>
                          )}
                          {hasVariants && !soldOut && (
                            <span className="absolute top-2 left-2 px-2.5 py-1 rounded-full bg-white/90 text-[var(--text-strong)] text-[11px] font-semibold">{product.variants.length} pilihan</span>
                          )}
                        </div>
                        <div className="p-3 sm:p-3.5 flex-1 flex flex-col">
                          <h3 className="text-[14px] font-bold text-[var(--text-strong)] leading-snug line-clamp-2">{product.name}</h3>
                          {product.description && <p className="text-xs text-[var(--text-muted)] line-clamp-2 mt-0.5">{product.description}</p>}
                          <div className="mt-auto pt-3 flex items-center justify-between gap-2">
                            <span className="text-[14px] font-extrabold text-[var(--text-strong)]">{hasVariants && 'dari '}{rp(product.price)}</span>
                            {qty > 0 && !hasVariants ? (
                              <Stepper qty={qty}
                                onDec={() => updateQuantity(cartLineId(product.id), qty - 1)}
                                onInc={() => updateQuantity(cartLineId(product.id), qty + 1)} />
                            ) : (
                              <button onClick={() => handleAdd(product)} disabled={soldOut || !accepting}
                                className="relative h-9 min-w-9 px-3 rounded-full bg-[var(--surface-inverse)] text-white text-sm font-semibold flex items-center justify-center hover:opacity-90 disabled:opacity-30 disabled:cursor-not-allowed">
                                {hasVariants ? 'Pilih' : '+'}
                                {qty > 0 && <span className="absolute -top-1.5 -right-1.5 w-5 h-5 rounded-full bg-[var(--brand-primary)] text-[10px] font-bold flex items-center justify-center">{qty}</span>}
                              </button>
                            )}
                          </div>
                        </div>
                      </article>
                    );
                  })}
                </div>
              </section>
            ))}
            <PoweredBy className="md:hidden" />
          </div>

          {/* Keranjang desktop */}
          <aside className="hidden md:block sticky top-32">
            <Card className="overflow-hidden">
              <div className="px-5 py-4 border-b border-[var(--border-subtle)] flex items-center justify-between">
                <h2 className="font-display font-extrabold text-[17px] text-[var(--text-strong)]">Pesanan Anda</h2>
                {totalItems > 0 && <span className="text-xs font-bold px-2.5 py-1 rounded-full bg-[var(--bg-subtle)] text-[var(--text-strong)]">{totalItems} item</span>}
              </div>
              {items.length === 0 ? (
                <div className="px-5 py-12 text-center">
                  <ShoppingBag className="w-9 h-9 text-[var(--border-default)] mx-auto mb-3" />
                  <p className="text-sm text-[var(--text-muted)]">Belum ada menu yang dipilih.</p>
                </div>
              ) : (
                <>
                  <ul className="px-5 py-3 space-y-3 max-h-80 overflow-y-auto">
                    {items.map((item) => (
                      <li key={item.id} className="flex items-center gap-3">
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-semibold text-[var(--text-strong)] truncate">{item.name}</p>
                          <p className="text-xs text-[var(--text-muted)]">{rp(item.price)}</p>
                        </div>
                        <Stepper qty={item.quantity} onDec={() => updateQuantity(item.id, item.quantity - 1)} onInc={() => updateQuantity(item.id, item.quantity + 1)} />
                      </li>
                    ))}
                  </ul>
                  <div className="px-5 py-4 border-t border-[var(--border-subtle)] space-y-3">
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-[var(--text-muted)]">Total</span>
                      <span className="text-lg font-extrabold text-[var(--text-strong)]">{rp(totalPrice)}</span>
                    </div>
                    <button onClick={() => router.push(cartHref)} disabled={!accepting} className={`${btnPrimary} w-full`}>
                      Lanjut ke pemesanan <ChevronRight className="w-4 h-4" />
                    </button>
                  </div>
                </>
              )}
            </Card>
            <PoweredBy />
          </aside>
        </div>
      </main>

      {/* Bilah keranjang mobile */}
      {totalItems > 0 && (
        <div className="md:hidden fixed bottom-4 left-4 right-4 z-40">
          <button onClick={() => router.push(cartHref)} disabled={!accepting}
            className="w-full rounded-full bg-[var(--surface-inverse)] text-white shadow-[var(--shadow-lg)] p-1.5 pl-2 flex items-center gap-3 disabled:opacity-60">
            <span className="w-10 h-10 rounded-full bg-white/15 flex items-center justify-center font-bold text-sm">{totalItems}</span>
            <span className="flex-1 text-left">
              <span className="block text-[11px] text-white/70 leading-none mb-0.5">Total pesanan</span>
              <span className="block text-[15px] font-extrabold leading-none">{rp(totalPrice)}</span>
            </span>
            <span className="pr-4 text-sm font-semibold inline-flex items-center gap-1">Lihat pesanan <ChevronRight className="w-4 h-4" /></span>
          </button>
        </div>
      )}

      {/* Pilih varian */}
      <Sheet open={!!variantProduct} onClose={() => setVariantProduct(null)} title={variantProduct?.name}>
        {variantProduct && (
          <>
            <p className="text-sm text-[var(--text-muted)] -mt-2 mb-4">Pilih salah satu.</p>
            <div className="space-y-2">
              {variantProduct.variants.map((v: any) => (
                <button key={v.id} onClick={() => { addLine(variantProduct, v); setVariantProduct(null); }}
                  className="w-full flex items-center justify-between gap-3 px-4 py-3.5 rounded-2xl border border-[var(--border-subtle)] hover:border-[var(--text-strong)] hover:bg-[var(--bg-subtle)] text-left transition">
                  <span className="font-semibold text-[var(--text-strong)]">{v.name}</span>
                  <span className="font-extrabold text-[var(--text-strong)]">{rp(v.price)}</span>
                </button>
              ))}
            </div>
          </>
        )}
      </Sheet>
    </div>
  );
}
