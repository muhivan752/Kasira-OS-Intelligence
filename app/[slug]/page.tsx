'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { getStorefront } from '@/app/actions/storefront';
import { useCart } from './CartContext';
import { ShoppingBag, MessageCircle, Store, Clock, MapPin, CheckCircle2, Plus, Minus, CalendarDays, Star, Crown, Flame, Sparkles } from 'lucide-react';
import { Logo } from '@/components/ui/logo';

export default function StorefrontPage() {
  const params = useParams();
  const slug = params.slug as string;
  const router = useRouter();
  const { items, addItem, updateQuantity, totalItems, totalPrice } = useCart();

  const [loading, setLoading] = useState(true);
  const [storeData, setStoreData] = useState<any>(null);
  const [selectedCategory, setSelectedCategory] = useState<string>('all');

  useEffect(() => {
    if (!slug) return;
    async function loadData() {
      const data = await getStorefront(slug);
      if (data) setStoreData(data);
      setLoading(false);
    }
    loadData();
  }, [slug]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="w-10 h-10 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-sm text-gray-500">Memuat menu...</p>
        </div>
      </div>
    );
  }

  if (!storeData) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center p-4 text-center bg-gray-50">
        <Store className="w-16 h-16 text-gray-300 mb-4" />
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Toko Tidak Ditemukan</h1>
        <p className="text-gray-500">Toko yang Anda cari mungkin sudah tutup atau link tidak valid.</p>
      </div>
    );
  }

  const { outlet, categories, products } = storeData;
  const isPro = ['pro', 'business', 'enterprise'].includes(outlet.tier || '');

  const formatCurrency = (amount: number) =>
    new Intl.NumberFormat('id-ID', { style: 'currency', currency: 'IDR', minimumFractionDigits: 0 }).format(amount || 0);

  const filteredProducts =
    selectedCategory === 'all'
      ? products
      : products.filter((p: any) => p.category_id === selectedCategory);

  const handleAddToCart = (product: any) => {
    if (product.stock <= 0) return;
    addItem({ id: product.id, name: product.name, price: product.price, quantity: 1, image_url: product.image_url });
  };

  const handleWhatsApp = () => {
    if (!outlet.phone) return;
    const phone = outlet.phone.startsWith('0') ? '62' + outlet.phone.slice(1) : outlet.phone;
    window.open(`https://wa.me/${phone}?text=Halo%20${outlet.name},%20saya%20ingin%20bertanya%20tentang%20menu%20Anda.`, '_blank');
  };

  // Pro: identify top 3 products by sold_total for "Populer" badge
  const topProductIds = new Set(
    [...products].sort((a: any, b: any) => (b.sold_total || 0) - (a.sold_total || 0)).slice(0, 3).map((p: any) => p.id)
  );

  if (isPro) return <ProStorefront />;
  return <StarterStorefront />;

  // ════════════════════════════════════════════════════════════
  // STARTER STOREFRONT — clean, functional, blue accent
  // ════════════════════════════════════════════════════════════
  function StarterStorefront() {
    return (
      <div className="min-h-screen bg-gray-50">
        {/* Hero */}
        <div className="relative h-44 md:h-64 bg-gray-200">
          {outlet.cover_image_url ? (
            <img src={outlet.cover_image_url} alt={outlet.name} className="w-full h-full object-cover" />
          ) : (
            <div className="w-full h-full bg-gradient-to-br from-blue-600 to-blue-800 flex items-center justify-center">
              <Store className="w-16 h-16 text-white/40" />
            </div>
          )}
          <div className="absolute inset-0 bg-gradient-to-t from-black/70 to-transparent" />
          <div className="absolute bottom-4 left-4 right-4 text-white">
            <div className="max-w-7xl mx-auto">
              <div className="flex items-start justify-between gap-4">
                <h1 className="text-2xl md:text-3xl font-bold">{outlet.name}</h1>
                <span className={`shrink-0 px-3 py-1 rounded-full text-xs font-bold ${outlet.is_open ? 'bg-green-500' : 'bg-red-500'}`}>
                  {outlet.is_open ? 'BUKA' : 'TUTUP'}
                </span>
              </div>
              <div className="flex flex-wrap gap-x-4 gap-y-1 mt-1.5 text-sm text-gray-200">
                {outlet.address && <span className="flex items-center gap-1.5"><MapPin className="w-3.5 h-3.5" />{outlet.address}</span>}
                {outlet.opening_hours && <span className="flex items-center gap-1.5"><Clock className="w-3.5 h-3.5" />{outlet.opening_hours}</span>}
              </div>
            </div>
          </div>
        </div>

        {/* Trust badge */}
        <div className="bg-blue-50 border-b border-blue-100">
          <div className="max-w-7xl mx-auto px-4 py-2.5 flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-blue-600 shrink-0" />
            <span className="text-sm font-medium text-blue-900">Terverifikasi Kasira · Zero Komisi</span>
            <div className="ml-auto flex items-center gap-3">
              <button onClick={handleWhatsApp} className="flex items-center gap-1.5 text-green-700 hover:text-green-800 text-sm font-medium">
                <MessageCircle className="w-4 h-4" /><span className="hidden sm:inline">WhatsApp</span>
              </button>
            </div>
          </div>
        </div>

        {/* Category filter */}
        <div className="sticky top-0 bg-white z-20 border-b border-gray-100 shadow-sm">
          <div className="max-w-7xl mx-auto px-4">
            <div className="flex overflow-x-auto hide-scrollbar py-3 gap-2">
              <button onClick={() => setSelectedCategory('all')}
                className={`px-4 py-1.5 rounded-full text-sm font-medium whitespace-nowrap transition-colors ${selectedCategory === 'all' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}>
                Semua
              </button>
              {categories.map((cat: any) => (
                <button key={cat.id} onClick={() => setSelectedCategory(cat.id)}
                  className={`px-4 py-1.5 rounded-full text-sm font-medium whitespace-nowrap transition-colors ${selectedCategory === cat.id ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}>
                  {cat.name}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Products */}
        <div className="max-w-7xl mx-auto px-4 py-6 pb-32 md:pb-12">
          <div className="md:grid md:grid-cols-3 md:gap-8 items-start">
            <div className="md:col-span-2">
              {filteredProducts.length === 0 ? (
                <div className="py-16 text-center text-gray-500 bg-white rounded-2xl">Tidak ada produk di kategori ini.</div>
              ) : (
                <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
                  {filteredProducts.map((product: any) => (
                    <div key={product.id} className="bg-white border border-gray-100 rounded-xl overflow-hidden shadow-sm flex flex-col">
                      <div className="aspect-square bg-gray-100 relative">
                        {product.image_url
                          ? <img src={product.image_url} alt={product.name} className="w-full h-full object-cover" />
                          : <div className="w-full h-full flex items-center justify-center text-gray-300"><Store className="w-8 h-8" /></div>}
                        {product.stock <= 0 && (
                          <div className="absolute inset-0 bg-white/70 flex items-center justify-center backdrop-blur-[2px]">
                            <span className="bg-red-600 text-white px-3 py-1 rounded-full text-sm font-bold">HABIS</span>
                          </div>
                        )}
                      </div>
                      <div className="p-3 flex-1 flex flex-col">
                        <h3 className="text-sm font-bold text-gray-900 line-clamp-2 mb-1">{product.name}</h3>
                        <div className="mt-auto pt-2 flex items-center justify-between">
                          <span className="text-sm font-bold text-blue-600">{formatCurrency(product.price)}</span>
                          <button onClick={() => handleAddToCart(product)} disabled={product.stock <= 0 || !outlet.is_open}
                            className="w-8 h-8 bg-blue-50 text-blue-600 rounded-full flex items-center justify-center hover:bg-blue-100 disabled:opacity-50 disabled:bg-gray-100 disabled:text-gray-400 transition-colors text-lg font-bold leading-none">
                            +
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
              <PoweredByFooter className="md:hidden" />
            </div>
            <DesktopCart />
          </div>
        </div>
        <MobileFloatingBar />
      </div>
    );
  }

  // ════════════════════════════════════════════════════════════
  // PRO STOREFRONT — premium, elevated, emerald/dark accents
  // ════════════════════════════════════════════════════════════
  function ProStorefront() {
    return (
      <div className="min-h-screen bg-stone-50">
        {/* Hero — taller, cinematic */}
        <div className="relative h-56 md:h-80 bg-gray-900">
          {outlet.cover_image_url ? (
            <img src={outlet.cover_image_url} alt={outlet.name} className="w-full h-full object-cover" />
          ) : (
            <div className="w-full h-full bg-gradient-to-br from-gray-900 via-emerald-950 to-gray-900 flex items-center justify-center">
              <div className="text-center">
                <div className="w-20 h-20 mx-auto bg-emerald-500/20 rounded-2xl flex items-center justify-center mb-3">
                  <Store className="w-10 h-10 text-emerald-400" />
                </div>
              </div>
            </div>
          )}
          <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/30 to-transparent" />
          <div className="absolute bottom-5 left-4 right-4 text-white">
            <div className="max-w-7xl mx-auto">
              <div className="flex items-center gap-2 mb-2">
                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                  <Crown className="w-3 h-3" /> PRO
                </span>
                <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold ${outlet.is_open ? 'bg-green-500/20 text-green-300 border border-green-500/30' : 'bg-red-500/20 text-red-300 border border-red-500/30'}`}>
                  {outlet.is_open ? 'BUKA' : 'TUTUP'}
                </span>
              </div>
              <h1 className="text-3xl md:text-5xl font-extrabold tracking-tight">{outlet.name}</h1>
              <div className="flex flex-wrap gap-x-4 gap-y-1 mt-2 text-sm text-gray-300">
                {outlet.address && <span className="flex items-center gap-1.5"><MapPin className="w-3.5 h-3.5 text-emerald-400" />{outlet.address}</span>}
                {outlet.opening_hours && <span className="flex items-center gap-1.5"><Clock className="w-3.5 h-3.5 text-emerald-400" />{outlet.opening_hours}</span>}
              </div>
            </div>
          </div>
        </div>

        {/* Trust badge — premium */}
        <div className="bg-gradient-to-r from-emerald-50 to-stone-50 border-b border-emerald-100">
          <div className="max-w-7xl mx-auto px-4 py-2.5 flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            <span className="text-sm font-medium text-emerald-900">Terverifikasi Kasira Pro · Zero Komisi</span>
            <div className="ml-auto flex items-center gap-3">
              {outlet.reservation_enabled && (
                <button onClick={() => router.push(`/${slug}/booking`)}
                  className="flex items-center gap-1.5 text-emerald-700 hover:text-emerald-800 text-sm font-medium transition-colors">
                  <CalendarDays className="w-4 h-4" /><span className="hidden sm:inline">Reservasi</span>
                </button>
              )}
              <button onClick={handleWhatsApp}
                className="flex items-center gap-1.5 text-green-700 hover:text-green-800 text-sm font-medium transition-colors">
                <MessageCircle className="w-4 h-4" /><span className="hidden sm:inline">WhatsApp</span>
              </button>
            </div>
          </div>
        </div>

        {/* Category filter — pill style with emerald accent */}
        <div className="sticky top-0 bg-white/80 backdrop-blur-lg z-20 border-b border-stone-200">
          <div className="max-w-7xl mx-auto px-4">
            <div className="flex overflow-x-auto hide-scrollbar py-3 gap-2">
              <button onClick={() => setSelectedCategory('all')}
                className={`px-4 py-1.5 rounded-full text-sm font-medium whitespace-nowrap transition-all ${selectedCategory === 'all' ? 'bg-gray-900 text-white shadow-md' : 'bg-stone-100 text-stone-600 hover:bg-stone-200'}`}>
                Semua Menu
              </button>
              {categories.map((cat: any) => (
                <button key={cat.id} onClick={() => setSelectedCategory(cat.id)}
                  className={`px-4 py-1.5 rounded-full text-sm font-medium whitespace-nowrap transition-all ${selectedCategory === cat.id ? 'bg-gray-900 text-white shadow-md' : 'bg-stone-100 text-stone-600 hover:bg-stone-200'}`}>
                  {cat.name}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Products — premium cards */}
        <div className="max-w-7xl mx-auto px-4 py-6 pb-32 md:pb-12">
          <div className="md:grid md:grid-cols-3 md:gap-8 items-start">
            <div className="md:col-span-2">
              {filteredProducts.length === 0 ? (
                <div className="py-16 text-center text-stone-500 bg-white rounded-2xl border border-stone-200">Tidak ada produk di kategori ini.</div>
              ) : (
                <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3 md:gap-4">
                  {filteredProducts.map((product: any) => (
                    <div key={product.id}
                      className="bg-white rounded-2xl overflow-hidden shadow-sm hover:shadow-md transition-all duration-200 flex flex-col border border-stone-100 group">
                      <div className="aspect-square bg-stone-100 relative overflow-hidden">
                        {product.image_url
                          ? <img src={product.image_url} alt={product.name} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" />
                          : <div className="w-full h-full flex items-center justify-center text-stone-300 bg-gradient-to-br from-stone-100 to-stone-200"><Store className="w-8 h-8" /></div>}
                        {/* Populer badge */}
                        {topProductIds.has(product.id) && product.sold_total > 0 && (
                          <div className="absolute top-2 left-2">
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-500 text-white shadow-sm">
                              <Flame className="w-3 h-3" /> Populer
                            </span>
                          </div>
                        )}
                        {product.stock <= 0 && (
                          <div className="absolute inset-0 bg-white/80 flex items-center justify-center backdrop-blur-sm">
                            <span className="bg-stone-800 text-white px-3 py-1 rounded-full text-sm font-bold">HABIS</span>
                          </div>
                        )}
                      </div>
                      <div className="p-3.5 flex-1 flex flex-col">
                        <h3 className="text-sm font-bold text-gray-900 line-clamp-2 mb-0.5">{product.name}</h3>
                        {product.description && <p className="text-[11px] text-stone-400 line-clamp-1 mb-1">{product.description}</p>}
                        <div className="mt-auto pt-2 flex items-center justify-between">
                          <span className="text-sm font-bold text-gray-900">{formatCurrency(product.price)}</span>
                          <button onClick={() => handleAddToCart(product)} disabled={product.stock <= 0 || !outlet.is_open}
                            className="w-8 h-8 bg-emerald-500 text-white rounded-full flex items-center justify-center hover:bg-emerald-600 disabled:opacity-40 disabled:bg-stone-200 disabled:text-stone-400 transition-all text-lg font-bold leading-none shadow-sm hover:shadow">
                            +
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
              <PoweredByFooter className="md:hidden" />
            </div>

            {/* Pro cart sidebar — dark theme */}
            <div className="hidden md:block sticky top-20">
              <div className="bg-gray-900 rounded-2xl overflow-hidden shadow-lg">
                <div className="px-5 py-4 border-b border-gray-800 flex items-center justify-between">
                  <h2 className="text-base font-bold text-white">Pesanan Anda</h2>
                  {totalItems > 0 && (
                    <span className="bg-emerald-500/20 text-emerald-400 text-xs font-bold px-2.5 py-1 rounded-full">
                      {totalItems} item
                    </span>
                  )}
                </div>
                {items.length === 0 ? (
                  <div className="px-5 py-10 text-center">
                    <ShoppingBag className="w-10 h-10 text-gray-700 mx-auto mb-3" />
                    <p className="text-sm text-gray-500">Belum ada pesanan</p>
                    <p className="text-xs text-gray-600 mt-1">Pilih menu untuk mulai memesan</p>
                  </div>
                ) : (
                  <>
                    <div className="px-5 py-3 space-y-3 max-h-72 overflow-y-auto">
                      {items.map((item) => (
                        <div key={item.id} className="flex items-center gap-3">
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-white truncate">{item.name}</p>
                            <p className="text-xs text-emerald-400 font-semibold">{formatCurrency(item.price)}</p>
                          </div>
                          <div className="flex items-center gap-1.5 shrink-0">
                            <button onClick={() => updateQuantity(item.id, item.quantity - 1)}
                              className="w-6 h-6 bg-gray-800 rounded-full flex items-center justify-center hover:bg-gray-700 transition-colors">
                              <Minus className="w-3 h-3 text-gray-400" />
                            </button>
                            <span className="text-sm font-bold w-5 text-center text-white">{item.quantity}</span>
                            <button onClick={() => updateQuantity(item.id, item.quantity + 1)}
                              className="w-6 h-6 bg-gray-800 rounded-full flex items-center justify-center hover:bg-gray-700 transition-colors">
                              <Plus className="w-3 h-3 text-gray-400" />
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                    <div className="px-5 py-4 border-t border-gray-800 space-y-3">
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-gray-400">Total</span>
                        <span className="text-lg font-bold text-white">{formatCurrency(totalPrice)}</span>
                      </div>
                      <button onClick={() => router.push(`/${slug}/cart`)} disabled={!outlet.is_open}
                        className="w-full py-3 bg-emerald-500 text-white font-bold rounded-xl hover:bg-emerald-600 disabled:opacity-50 transition-all flex items-center justify-center gap-2 shadow-lg shadow-emerald-500/20">
                        <ShoppingBag className="w-4 h-4" /> Lanjut Pesan
                      </button>
                    </div>
                  </>
                )}
              </div>

              <button onClick={handleWhatsApp}
                className="mt-3 w-full py-2.5 bg-gray-900 text-green-400 font-medium rounded-xl hover:bg-gray-800 transition-colors flex items-center justify-center gap-2 text-sm border border-gray-800">
                <MessageCircle className="w-4 h-4" /> Hubungi via WhatsApp
              </button>

              <PoweredByFooter className="" />
            </div>
          </div>
        </div>

        {/* Pro mobile floating bar — emerald accent */}
        <div className="md:hidden fixed bottom-6 left-0 right-0 px-4 pointer-events-none flex flex-col items-center z-50">
          <div className="w-full max-w-md mx-auto flex justify-between items-end pointer-events-auto">
            <div className="flex gap-2">
              {outlet.reservation_enabled && (
                <button onClick={() => router.push(`/${slug}/booking`)}
                  className="w-12 h-12 bg-gray-900 text-emerald-400 rounded-full shadow-lg flex items-center justify-center hover:bg-gray-800 transition-colors border border-gray-800">
                  <CalendarDays className="w-6 h-6" />
                </button>
              )}
              <button onClick={handleWhatsApp}
                className="w-12 h-12 bg-green-500 text-white rounded-full shadow-lg flex items-center justify-center hover:bg-green-600 transition-colors">
                <MessageCircle className="w-6 h-6" />
              </button>
            </div>
            {totalItems > 0 && (
              <button onClick={() => router.push(`/${slug}/cart`)}
                className="flex-1 ml-4 bg-emerald-500 text-white rounded-full shadow-lg shadow-emerald-500/30 p-1 flex items-center hover:bg-emerald-600 transition-all">
                <div className="w-10 h-10 bg-white/20 rounded-full flex items-center justify-center font-bold">{totalItems}</div>
                <div className="flex-1 px-3 text-left">
                  <p className="text-xs text-emerald-100">Total Pesanan</p>
                  <p className="text-sm font-bold">{formatCurrency(totalPrice)}</p>
                </div>
                <div className="pr-4"><ShoppingBag className="w-5 h-5" /></div>
              </button>
            )}
          </div>
        </div>
      </div>
    );
  }

  // ════════════════════════════════════════════════════════════
  // SHARED COMPONENTS
  // ════════════════════════════════════════════════════════════
  function DesktopCart() {
    return (
      <div className="hidden md:block sticky top-20">
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
          <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
            <h2 className="text-base font-bold text-gray-900">Pesanan Anda</h2>
            {totalItems > 0 && (
              <span className="bg-blue-100 text-blue-700 text-xs font-bold px-2.5 py-1 rounded-full">{totalItems} item</span>
            )}
          </div>
          {items.length === 0 ? (
            <div className="px-5 py-10 text-center">
              <ShoppingBag className="w-10 h-10 text-gray-300 mx-auto mb-3" />
              <p className="text-sm text-gray-500">Belum ada pesanan</p>
            </div>
          ) : (
            <>
              <div className="px-5 py-3 space-y-3 max-h-72 overflow-y-auto">
                {items.map((item) => (
                  <div key={item.id} className="flex items-center gap-3">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate">{item.name}</p>
                      <p className="text-xs text-blue-600 font-semibold">{formatCurrency(item.price)}</p>
                    </div>
                    <div className="flex items-center gap-1.5 shrink-0">
                      <button onClick={() => updateQuantity(item.id, item.quantity - 1)}
                        className="w-6 h-6 bg-gray-100 rounded-full flex items-center justify-center hover:bg-gray-200"><Minus className="w-3 h-3 text-gray-600" /></button>
                      <span className="text-sm font-bold w-5 text-center">{item.quantity}</span>
                      <button onClick={() => updateQuantity(item.id, item.quantity + 1)}
                        className="w-6 h-6 bg-gray-100 rounded-full flex items-center justify-center hover:bg-gray-200"><Plus className="w-3 h-3 text-gray-600" /></button>
                    </div>
                  </div>
                ))}
              </div>
              <div className="px-5 py-4 border-t border-gray-100 space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-500">Total</span>
                  <span className="text-lg font-bold text-gray-900">{formatCurrency(totalPrice)}</span>
                </div>
                <button onClick={() => router.push(`/${slug}/cart`)} disabled={!outlet.is_open}
                  className="w-full py-3 bg-blue-600 text-white font-bold rounded-xl hover:bg-blue-700 disabled:opacity-50 transition-colors flex items-center justify-center gap-2">
                  <ShoppingBag className="w-4 h-4" /> Lanjut Pesan
                </button>
              </div>
            </>
          )}
        </div>
        <button onClick={handleWhatsApp}
          className="mt-3 w-full py-2.5 bg-green-50 text-green-700 font-medium rounded-xl hover:bg-green-100 transition-colors flex items-center justify-center gap-2 text-sm border border-green-200">
          <MessageCircle className="w-4 h-4" /> Hubungi via WhatsApp
        </button>
        <PoweredByFooter className="" />
      </div>
    );
  }

  function MobileFloatingBar() {
    return (
      <div className="md:hidden fixed bottom-6 left-0 right-0 px-4 pointer-events-none flex flex-col items-center z-50">
        <div className="w-full max-w-md mx-auto flex justify-between items-end pointer-events-auto">
          <div className="flex gap-2">
            {outlet.reservation_enabled && (
              <button onClick={() => router.push(`/${slug}/booking`)}
                className="w-12 h-12 bg-blue-600 text-white rounded-full shadow-lg flex items-center justify-center hover:bg-blue-700 transition-colors">
                <CalendarDays className="w-6 h-6" />
              </button>
            )}
            <button onClick={handleWhatsApp}
              className="w-12 h-12 bg-green-500 text-white rounded-full shadow-lg flex items-center justify-center hover:bg-green-600 transition-colors">
              <MessageCircle className="w-6 h-6" />
            </button>
          </div>
          {totalItems > 0 && (
            <button onClick={() => router.push(`/${slug}/cart`)}
              className="flex-1 ml-4 bg-blue-600 text-white rounded-full shadow-lg p-1 flex items-center hover:bg-blue-700 transition-colors">
              <div className="w-10 h-10 bg-white/20 rounded-full flex items-center justify-center font-bold">{totalItems}</div>
              <div className="flex-1 px-3 text-left">
                <p className="text-xs text-blue-100">Total Pesanan</p>
                <p className="text-sm font-bold">{formatCurrency(totalPrice)}</p>
              </div>
              <div className="pr-4"><ShoppingBag className="w-5 h-5" /></div>
            </button>
          )}
        </div>
      </div>
    );
  }

  function PoweredByFooter({ className }: { className?: string }) {
    return (
      <div className={`mt-5 flex flex-col items-center gap-1 ${className}`}>
        <p className="text-xs text-gray-400">Powered by</p>
        <Logo size="xs" variant="light" />
        <p className="text-[10px] text-gray-400 mt-0.5">Zero Komisi</p>
      </div>
    );
  }
}
