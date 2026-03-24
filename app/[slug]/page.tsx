'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { getStorefront } from '@/app/actions/storefront';
import { useCart } from './CartContext';
import { ShoppingBag, MessageCircle, Store, Clock, MapPin, CheckCircle2 } from 'lucide-react';

export default function StorefrontPage() {
  const params = useParams();
  const slug = params.slug as string;
  const router = useRouter();
  const { items, addItem, totalItems, totalPrice } = useCart();
  
  const [loading, setLoading] = useState(true);
  const [storeData, setStoreData] = useState<any>(null);
  const [selectedCategory, setSelectedCategory] = useState<string>('all');

  useEffect(() => {
    async function loadData() {
      const data = await getStorefront(slug);
      if (data) {
        setStoreData(data);
      }
      setLoading(false);
    }
    loadData();
  }, [slug]);

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center">Loading...</div>;
  }

  if (!storeData) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center p-4 text-center">
        <Store className="w-16 h-16 text-gray-300 mb-4" />
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Toko Tidak Ditemukan</h1>
        <p className="text-gray-500">Toko yang Anda cari mungkin sudah tutup atau link tidak valid.</p>
      </div>
    );
  }

  const { outlet, categories, products } = storeData;

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('id-ID', { style: 'currency', currency: 'IDR' }).format(amount || 0);
  };

  const filteredProducts = selectedCategory === 'all' 
    ? products 
    : products.filter((p: any) => p.category_id === selectedCategory);

  const handleAddToCart = (product: any) => {
    if (product.stock <= 0) return;
    
    addItem({
      id: product.id,
      name: product.name,
      price: product.price,
      quantity: 1,
      image_url: product.image_url
    });
  };

  const handleWhatsApp = () => {
    if (!outlet.phone) return;
    const phone = outlet.phone.startsWith('0') ? '62' + outlet.phone.slice(1) : outlet.phone;
    window.open(`https://wa.me/${phone}?text=Halo%20${outlet.name},%20saya%20ingin%20bertanya%20tentang%20menu%20Anda.`, '_blank');
  };

  return (
    <div className="max-w-md mx-auto bg-white min-h-screen shadow-sm relative">
      {/* Hero Section */}
      <div className="relative h-48 bg-gray-200">
        {outlet.logo_url ? (
          <img src={outlet.logo_url} alt={outlet.name} className="w-full h-full object-cover" />
        ) : (
          <div className="w-full h-full bg-blue-600 flex items-center justify-center">
            <Store className="w-16 h-16 text-white/50" />
          </div>
        )}
        <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent" />
        
        <div className="absolute bottom-4 left-4 right-4 text-white">
          <div className="flex items-center justify-between mb-1">
            <h1 className="text-2xl font-bold">{outlet.name}</h1>
            <span className={`px-2 py-1 rounded text-xs font-bold ${outlet.is_open ? 'bg-green-500' : 'bg-red-500'}`}>
              {outlet.is_open ? 'BUKA' : 'TUTUP'}
            </span>
          </div>
          
          <div className="flex items-center gap-2 text-sm text-gray-200 mb-2">
            <MapPin className="w-4 h-4" />
            <span className="truncate">{outlet.address || 'Alamat belum diatur'}</span>
          </div>
          
          <div className="flex items-center gap-2 text-sm text-gray-200">
            <Clock className="w-4 h-4" />
            <span>{outlet.opening_hours || 'Jam operasional belum diatur'}</span>
          </div>
        </div>
      </div>

      {/* Trust Badge */}
      <div className="px-4 py-3 bg-blue-50 border-b border-blue-100 flex items-center gap-2">
        <CheckCircle2 className="w-5 h-5 text-blue-600" />
        <span className="text-sm font-medium text-blue-900">
          Terverifikasi Kasira {outlet.tier === 'premium' ? 'Premium' : 'Basic'}
        </span>
      </div>

      {/* Categories */}
      <div className="sticky top-0 bg-white z-10 border-b border-gray-100 shadow-sm">
        <div className="flex overflow-x-auto hide-scrollbar p-4 gap-2">
          <button
            onClick={() => setSelectedCategory('all')}
            className={`px-4 py-2 rounded-full text-sm font-medium whitespace-nowrap transition-colors ${
              selectedCategory === 'all' 
                ? 'bg-blue-600 text-white' 
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            Semua Menu
          </button>
          {categories.map((cat: any) => (
            <button
              key={cat.id}
              onClick={() => setSelectedCategory(cat.id)}
              className={`px-4 py-2 rounded-full text-sm font-medium whitespace-nowrap transition-colors ${
                selectedCategory === cat.id 
                  ? 'bg-blue-600 text-white' 
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {cat.name}
            </button>
          ))}
        </div>
      </div>

      {/* Product Grid */}
      <div className="p-4 grid grid-cols-2 gap-4">
        {filteredProducts.map((product: any) => (
          <div key={product.id} className="bg-white border border-gray-100 rounded-xl overflow-hidden shadow-sm flex flex-col">
            <div className="aspect-square bg-gray-100 relative">
              {product.image_url ? (
                <img src={product.image_url} alt={product.name} className="w-full h-full object-cover" />
              ) : (
                <div className="w-full h-full flex items-center justify-center text-gray-400">
                  <Store className="w-8 h-8" />
                </div>
              )}
              
              {product.stock <= 0 && (
                <div className="absolute inset-0 bg-white/70 flex items-center justify-center backdrop-blur-[2px]">
                  <span className="bg-red-600 text-white px-3 py-1 rounded-full text-sm font-bold shadow-sm">
                    HABIS
                  </span>
                </div>
              )}
            </div>
            
            <div className="p-3 flex-1 flex flex-col">
              <h3 className="text-sm font-bold text-gray-900 line-clamp-2 mb-1">{product.name}</h3>
              {product.description && (
                <p className="text-xs text-gray-500 line-clamp-1 mb-2">{product.description}</p>
              )}
              <div className="mt-auto pt-2 flex items-center justify-between">
                <span className="text-sm font-bold text-blue-600">
                  {formatCurrency(product.price)}
                </span>
                <button
                  onClick={() => handleAddToCart(product)}
                  disabled={product.stock <= 0 || !outlet.is_open}
                  className="w-8 h-8 bg-blue-50 text-blue-600 rounded-full flex items-center justify-center hover:bg-blue-100 disabled:opacity-50 disabled:bg-gray-100 disabled:text-gray-400 transition-colors"
                >
                  +
                </button>
              </div>
            </div>
          </div>
        ))}
        
        {filteredProducts.length === 0 && (
          <div className="col-span-2 py-12 text-center text-gray-500">
            Tidak ada produk di kategori ini.
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="py-8 text-center border-t border-gray-100 mt-4">
        <p className="text-xs text-gray-400 font-medium">
          Powered by <span className="font-bold text-gray-500">Kasira</span> — Zero Komisi
        </p>
      </div>

      {/* Floating Action Buttons */}
      <div className="fixed bottom-6 left-0 right-0 px-4 pointer-events-none flex flex-col items-center gap-3 z-50">
        <div className="w-full max-w-md mx-auto flex justify-between items-end pointer-events-auto">
          {/* WA Button */}
          <button 
            onClick={handleWhatsApp}
            className="w-12 h-12 bg-green-500 text-white rounded-full shadow-lg flex items-center justify-center hover:bg-green-600 transition-colors"
          >
            <MessageCircle className="w-6 h-6" />
          </button>

          {/* Cart Button */}
          {totalItems > 0 && (
            <button 
              onClick={() => router.push(`/${slug}/cart`)}
              className="flex-1 ml-4 bg-blue-600 text-white rounded-full shadow-lg p-1 flex items-center hover:bg-blue-700 transition-colors"
            >
              <div className="w-10 h-10 bg-white/20 rounded-full flex items-center justify-center font-bold">
                {totalItems}
              </div>
              <div className="flex-1 px-3 text-left">
                <p className="text-xs text-blue-100">Total Pesanan</p>
                <p className="text-sm font-bold">{formatCurrency(totalPrice)}</p>
              </div>
              <div className="pr-4">
                <ShoppingBag className="w-5 h-5" />
              </div>
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
