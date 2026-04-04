'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useCart } from '../CartContext';
import { createStorefrontOrder, getStorefront } from '@/app/actions/storefront';
import {
  ArrowLeft, Trash2, Plus, Minus, MapPin, Clock, CreditCard,
  Banknote, Loader2, ShoppingBag, Store, User, Phone,
} from 'lucide-react';
import Link from 'next/link';

export default function CartPage() {
  const params = useParams();
  const slug = params.slug as string;
  const router = useRouter();
  const { items, updateQuantity, removeItem, clearCart, totalPrice, totalItems } = useCart();

  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [storeData, setStoreData] = useState<any>(null);

  const [orderType, setOrderType] = useState<'pickup' | 'delivery'>('pickup');
  const [customerName, setCustomerName] = useState('');
  const [customerPhone, setCustomerPhone] = useState('');
  const [deliveryAddress, setDeliveryAddress] = useState('');
  const [notes, setNotes] = useState('');
  const [pickupTime, setPickupTime] = useState('15');

  useEffect(() => {
    async function loadData() {
      const data = await getStorefront(slug);
      if (data) setStoreData(data);
      setLoading(false);
    }
    loadData();
  }, [slug]);

  const formatCurrency = (amount: number) =>
    new Intl.NumberFormat('id-ID', { style: 'currency', currency: 'IDR' }).format(amount || 0);

  const isFormValid =
    customerName.trim() !== '' &&
    customerPhone.trim() !== '' &&
    (orderType !== 'delivery' || deliveryAddress.trim() !== '');

  const handleCheckout = async (paymentMethod: 'cash' | 'qris') => {
    if (!isFormValid) {
      alert(orderType === 'delivery' && !deliveryAddress ? 'Alamat pengiriman wajib diisi untuk Delivery' : 'Nama dan Nomor WA wajib diisi');
      return;
    }
    setSubmitting(true);
    const payload = {
      order_type: orderType,
      customer_name: customerName,
      customer_phone: customerPhone,
      delivery_address: orderType === 'delivery' ? deliveryAddress : null,
      notes: notes || null,
      items: items.map((item) => ({ product_id: item.id, qty: item.quantity, notes: '' })),
      payment_method: paymentMethod,
      idempotency_key: `${slug}-${customerPhone}-${Date.now()}`,
    };
    const res = await createStorefrontOrder(slug, payload);
    if (res.success) {
      clearCart();
      router.push(`/${slug}/order/${res.data.order_id}`);
    } else {
      alert(res.message);
      setSubmitting(false);
    }
  };

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center bg-gray-50">Loading...</div>;
  }

  if (items.length === 0) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center p-4 text-center bg-gray-50">
        <div className="w-20 h-20 bg-gray-100 rounded-full flex items-center justify-center mb-4">
          <ShoppingBag className="w-10 h-10 text-gray-400" />
        </div>
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Keranjang Kosong</h1>
        <p className="text-gray-500 mb-8">Anda belum menambahkan menu apapun.</p>
        <Link
          href={`/${slug}`}
          className="px-6 py-3 bg-blue-600 text-white font-medium rounded-xl hover:bg-blue-700 transition-colors"
        >
          Lihat Menu
        </Link>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white px-4 py-4 border-b border-gray-100 sticky top-0 z-10">
        <div className="max-w-5xl mx-auto flex items-center gap-4">
          <Link href={`/${slug}`} className="p-2 -ml-2 text-gray-500 hover:bg-gray-100 rounded-full transition-colors">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <h1 className="text-lg font-bold text-gray-900 flex-1">Keranjang Pesanan</h1>
          <span className="text-sm font-medium text-gray-500">{totalItems} item</span>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-6 pb-32 md:pb-8">
        <div className="md:grid md:grid-cols-5 md:gap-8 items-start">

          {/* ── Left: Form ── */}
          <div className="md:col-span-3 space-y-4">
            {/* Detail pemesan */}
            <div className="bg-white rounded-2xl p-5 space-y-4">
              <h2 className="text-base font-bold text-gray-900">Detail Pemesan</h2>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">
                  <User className="w-4 h-4 inline mr-1.5 text-gray-400" />
                  Nama Lengkap <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  placeholder="Masukkan nama Anda"
                  value={customerName}
                  onChange={(e) => setCustomerName(e.target.value)}
                  className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-sm"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">
                  <Phone className="w-4 h-4 inline mr-1.5 text-gray-400" />
                  Nomor WhatsApp <span className="text-red-500">*</span>
                </label>
                <input
                  type="tel"
                  required
                  placeholder="081234567890"
                  value={customerPhone}
                  onChange={(e) => setCustomerPhone(e.target.value.replace(/\D/g, ''))}
                  className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-sm"
                />
              </div>
            </div>

            {/* Tipe pesanan */}
            <div className="bg-white rounded-2xl p-5 space-y-4">
              <h2 className="text-base font-bold text-gray-900">Tipe Pesanan</h2>
              <div className="grid grid-cols-2 gap-3">
                <button
                  onClick={() => setOrderType('pickup')}
                  className={`flex flex-col items-center justify-center p-4 rounded-xl border-2 transition-colors ${
                    orderType === 'pickup'
                      ? 'border-blue-600 bg-blue-50 text-blue-700'
                      : 'border-gray-200 bg-white text-gray-500 hover:border-blue-300'
                  }`}
                >
                  <Store className="w-6 h-6 mb-2" />
                  <span className="text-sm font-bold">Ambil Sendiri</span>
                  <span className="text-xs mt-0.5 opacity-75">Pickup</span>
                </button>
                <button
                  onClick={() => setOrderType('delivery')}
                  className={`flex flex-col items-center justify-center p-4 rounded-xl border-2 transition-colors ${
                    orderType === 'delivery'
                      ? 'border-blue-600 bg-blue-50 text-blue-700'
                      : 'border-gray-200 bg-white text-gray-500 hover:border-blue-300'
                  }`}
                >
                  <MapPin className="w-6 h-6 mb-2" />
                  <span className="text-sm font-bold">Kirim ke Alamat</span>
                  <span className="text-xs mt-0.5 opacity-75">Delivery</span>
                </button>
              </div>

              {orderType === 'pickup' && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2 flex items-center gap-1.5">
                    <Clock className="w-4 h-4 text-gray-400" /> Estimasi Pengambilan
                  </label>
                  <div className="grid grid-cols-4 gap-2">
                    {['15', '30', '45', '60'].map((time) => (
                      <button
                        key={time}
                        onClick={() => setPickupTime(time)}
                        className={`py-2 rounded-lg text-sm font-medium transition-colors ${
                          pickupTime === time ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                        }`}
                      >
                        {time} mnt
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {orderType === 'delivery' && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">
                    Alamat Pengiriman <span className="text-red-500">*</span>
                  </label>
                  <textarea
                    required
                    rows={3}
                    placeholder="Masukkan alamat lengkap beserta patokan..."
                    value={deliveryAddress}
                    onChange={(e) => setDeliveryAddress(e.target.value)}
                    className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-sm resize-none"
                  />
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">Catatan Tambahan (Opsional)</label>
                <input
                  type="text"
                  placeholder="Contoh: Jangan pedas, tambah saus..."
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-sm"
                />
              </div>
            </div>
          </div>

          {/* ── Right: Order summary (sticky on desktop) ── */}
          <div className="md:col-span-2 md:sticky md:top-24 space-y-4 mt-4 md:mt-0">
            {/* Cart items */}
            <div className="bg-white rounded-2xl p-5">
              <h2 className="text-base font-bold text-gray-900 mb-4">Ringkasan Pesanan</h2>
              <div className="space-y-4 max-h-64 md:max-h-80 overflow-y-auto pr-1">
                {items.map((item) => (
                  <div key={item.id} className="flex gap-3">
                    <div className="w-14 h-14 bg-gray-100 rounded-lg overflow-hidden shrink-0">
                      {item.image_url ? (
                        <img src={item.image_url} alt={item.name} className="w-full h-full object-cover" />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center text-gray-400 font-bold text-lg">
                          {item.name.charAt(0)}
                        </div>
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="text-sm font-bold text-gray-900 line-clamp-2">{item.name}</h3>
                      <p className="text-sm font-medium text-blue-600">{formatCurrency(item.price)}</p>
                      <div className="flex items-center justify-between mt-1.5">
                        <button
                          onClick={() => removeItem(item.id)}
                          className="p-1 text-red-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                        <div className="flex items-center gap-2 bg-gray-100 rounded-full px-2 py-0.5">
                          <button
                            onClick={() => updateQuantity(item.id, item.quantity - 1)}
                            className="w-5 h-5 bg-white rounded-full flex items-center justify-center shadow-sm text-gray-600"
                          >
                            <Minus className="w-2.5 h-2.5" />
                          </button>
                          <span className="text-sm font-bold w-4 text-center">{item.quantity}</span>
                          <button
                            onClick={() => updateQuantity(item.id, item.quantity + 1)}
                            className="w-5 h-5 bg-white rounded-full flex items-center justify-center shadow-sm text-gray-600"
                          >
                            <Plus className="w-2.5 h-2.5" />
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
              <div className="mt-4 pt-4 border-t border-gray-100 flex justify-between items-center">
                <span className="text-gray-600 font-medium">Subtotal</span>
                <span className="text-xl font-bold text-gray-900">{formatCurrency(totalPrice)}</span>
              </div>
            </div>

            {/* Payment buttons - desktop */}
            <div className="hidden md:block bg-white rounded-2xl p-5 space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <button
                  onClick={() => handleCheckout('cash')}
                  disabled={submitting || !isFormValid}
                  className="flex flex-col items-center justify-center py-3 px-4 bg-gray-100 text-gray-800 rounded-xl hover:bg-gray-200 disabled:opacity-50 transition-colors"
                >
                  <Banknote className="w-5 h-5 mb-1" />
                  <span className="text-sm font-bold">Bayar di Tempat</span>
                </button>
                <button
                  onClick={() => handleCheckout('qris')}
                  disabled={submitting || !isFormValid}
                  className="flex flex-col items-center justify-center py-3 px-4 bg-blue-600 text-white rounded-xl hover:bg-blue-700 disabled:opacity-50 transition-colors"
                >
                  {submitting ? (
                    <Loader2 className="w-6 h-6 animate-spin" />
                  ) : (
                    <>
                      <CreditCard className="w-5 h-5 mb-1" />
                      <span className="text-sm font-bold">Bayar QRIS</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ── Mobile: fixed bottom payment ── */}
      <div className="md:hidden fixed bottom-0 left-0 right-0 bg-white border-t border-gray-100 p-4 z-20 shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.05)]">
        <div className="max-w-md mx-auto space-y-3">
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-500 font-medium">Total Pembayaran</span>
            <span className="text-xl font-bold text-gray-900">{formatCurrency(totalPrice)}</span>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <button
              onClick={() => handleCheckout('cash')}
              disabled={submitting || !isFormValid}
              className="flex flex-col items-center justify-center py-3 px-4 bg-gray-100 text-gray-800 rounded-xl hover:bg-gray-200 disabled:opacity-50 transition-colors"
            >
              <Banknote className="w-5 h-5 mb-1" />
              <span className="text-sm font-bold">Bayar di Tempat</span>
            </button>
            <button
              onClick={() => handleCheckout('qris')}
              disabled={submitting || !isFormValid}
              className="flex flex-col items-center justify-center py-3 px-4 bg-blue-600 text-white rounded-xl hover:bg-blue-700 disabled:opacity-50 transition-colors"
            >
              {submitting ? (
                <Loader2 className="w-6 h-6 animate-spin" />
              ) : (
                <>
                  <CreditCard className="w-5 h-5 mb-1" />
                  <span className="text-sm font-bold">Bayar via QRIS</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
