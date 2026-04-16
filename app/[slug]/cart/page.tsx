'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useCart } from '../CartContext';
import { createStorefrontOrder, getStorefront, getTablesWithStatus, requestBillFromStorefront } from '@/app/actions/storefront';
import {
  ArrowLeft, Trash2, Plus, Minus, MapPin, Clock, CreditCard,
  Banknote, Loader2, ShoppingBag, Store, User, Phone, Utensils,
  Armchair, ChevronDown, Bell,
} from 'lucide-react';
import Link from 'next/link';

export default function CartPage() {
  const params = useParams();
  const slug = params.slug as string;
  const router = useRouter();
  const { items, updateQuantity, removeItem, clearCart, totalPrice, totalItems, tableId, tableName, setTable } = useCart();

  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [storeData, setStoreData] = useState<any>(null);
  const [tables, setTables] = useState<any[]>([]);
  const [isPro, setIsPro] = useState(false);

  const [orderType, setOrderType] = useState<'pickup' | 'delivery' | 'dine_in'>('pickup');
  const [customerName, setCustomerName] = useState('');
  const [customerPhone, setCustomerPhone] = useState('');
  const [deliveryAddress, setDeliveryAddress] = useState('');
  const [notes, setNotes] = useState('');
  const [pickupTime, setPickupTime] = useState('15');
  const [showTablePicker, setShowTablePicker] = useState(false);
  const [requestingBill, setRequestingBill] = useState(false);
  const [billRequested, setBillRequested] = useState(false);

  useEffect(() => {
    async function loadData() {
      const [data, tableData] = await Promise.all([
        getStorefront(slug),
        getTablesWithStatus(slug),
      ]);
      if (data) setStoreData(data);
      if (tableData) {
        setTables(tableData.tables || []);
        setIsPro(tableData.is_pro || false);
      }
      setLoading(false);
    }
    loadData();
  }, [slug]);

  // Auto-select dine_in when table param is present AND outlet is Pro
  useEffect(() => {
    if (tableId && isPro) setOrderType('dine_in');
  }, [tableId, isPro]);

  const formatCurrency = (amount: number) =>
    new Intl.NumberFormat('id-ID', { style: 'currency', currency: 'IDR' }).format(amount || 0);

  const isFormValid =
    customerName.trim() !== '' &&
    customerPhone.trim() !== '' &&
    (orderType !== 'delivery' || deliveryAddress.trim() !== '') &&
    (orderType !== 'dine_in' || tableId !== null);

  const handleCheckout = async (paymentMethod: 'cash' | 'qris') => {
    if (!isFormValid) {
      if (orderType === 'dine_in' && !tableId) {
        alert('Pilih meja terlebih dahulu');
      } else if (orderType === 'delivery' && !deliveryAddress) {
        alert('Alamat pengiriman wajib diisi untuk Delivery');
      } else {
        alert('Nama dan Nomor WA wajib diisi');
      }
      return;
    }
    setSubmitting(true);
    const payload = {
      order_type: orderType,
      customer_name: customerName,
      customer_phone: customerPhone,
      delivery_address: orderType === 'delivery' ? deliveryAddress : null,
      table_id: orderType === 'dine_in' ? tableId : null,
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

  const handleRequestBill = async () => {
    if (!tableId) return;
    setRequestingBill(true);
    const res = await requestBillFromStorefront(slug, tableId);
    setRequestingBill(false);
    if (res.success) {
      setBillRequested(true);
    } else {
      alert(res.message);
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
          href={`/${slug}${tableId ? `?table=${tableId}` : ''}`}
          className="px-6 py-3 bg-blue-600 text-white font-medium rounded-xl hover:bg-blue-700 transition-colors"
        >
          Lihat Menu
        </Link>
        {/* Minta Bill button for dine-in without items (Pro only) */}
        {tableId && isPro && (
          <button
            onClick={handleRequestBill}
            disabled={requestingBill || billRequested}
            className="mt-4 px-6 py-3 bg-amber-500 text-white font-medium rounded-xl hover:bg-amber-600 disabled:opacity-50 transition-colors flex items-center gap-2"
          >
            <Bell className="w-5 h-5" />
            {billRequested ? 'Bill Sudah Diminta' : requestingBill ? 'Meminta...' : 'Minta Bill'}
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white px-4 py-4 border-b border-gray-100 sticky top-0 z-10">
        <div className="max-w-5xl mx-auto flex items-center gap-4">
          <Link href={`/${slug}${tableId ? `?table=${tableId}` : ''}`} className="p-2 -ml-2 text-gray-500 hover:bg-gray-100 rounded-full transition-colors">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <h1 className="text-lg font-bold text-gray-900 flex-1">Keranjang Pesanan</h1>
          <span className="text-sm font-medium text-gray-500">{totalItems} item</span>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-6 pb-32 md:pb-8">
        <div className="md:grid md:grid-cols-5 md:gap-8 items-start">

          {/* Left: Form */}
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
              <div className={`grid ${tableId && isPro ? 'grid-cols-3' : 'grid-cols-2'} gap-3`}>
                {tableId && isPro && (
                  <button
                    onClick={() => setOrderType('dine_in')}
                    className={`flex flex-col items-center justify-center p-4 rounded-xl border-2 transition-colors ${
                      orderType === 'dine_in'
                        ? 'border-emerald-600 bg-emerald-50 text-emerald-700'
                        : 'border-gray-200 bg-white text-gray-500 hover:border-emerald-300'
                    }`}
                  >
                    <Utensils className="w-6 h-6 mb-2" />
                    <span className="text-sm font-bold">Dine In</span>
                    <span className="text-xs mt-0.5 opacity-75">Makan di tempat</span>
                  </button>
                )}
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
                  <span className="text-sm font-bold">Delivery</span>
                  <span className="text-xs mt-0.5 opacity-75">Kirim</span>
                </button>
              </div>

              {/* Dine-in: show selected table */}
              {orderType === 'dine_in' && (
                <div className="flex items-center gap-3 p-3 bg-emerald-50 border border-emerald-200 rounded-xl">
                  <Armchair className="w-5 h-5 text-emerald-600" />
                  <div className="flex-1">
                    <p className="text-sm font-bold text-emerald-800">{tableName || 'Meja'}</p>
                    <p className="text-xs text-emerald-600">Pesanan akan masuk ke tab meja ini</p>
                  </div>
                  {!tableId && tables.length > 0 && (
                    <button
                      onClick={() => setShowTablePicker(!showTablePicker)}
                      className="text-sm text-emerald-600 font-medium"
                    >
                      Pilih <ChevronDown className="w-4 h-4 inline" />
                    </button>
                  )}
                </div>
              )}

              {/* Table picker dropdown */}
              {orderType === 'dine_in' && showTablePicker && (
                <div className="grid grid-cols-3 gap-2 max-h-48 overflow-y-auto">
                  {tables.filter((t: any) => t.status === 'available' || t.status === 'occupied').map((t: any) => (
                    <button
                      key={t.id}
                      onClick={() => {
                        setTable(t.id, `Meja ${t.name}`);
                        setShowTablePicker(false);
                      }}
                      className={`p-3 rounded-lg border text-center text-sm transition-colors ${
                        tableId === t.id
                          ? 'border-emerald-500 bg-emerald-50 text-emerald-700 font-bold'
                          : t.status === 'available'
                            ? 'border-gray-200 hover:border-emerald-300 text-gray-700'
                            : 'border-orange-200 bg-orange-50 text-orange-700'
                      }`}
                    >
                      <Armchair className="w-4 h-4 mx-auto mb-1" />
                      Meja {t.name}
                      <span className="block text-xs opacity-75">{t.capacity} kursi</span>
                    </button>
                  ))}
                </div>
              )}

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

          {/* Right: Order summary (sticky on desktop) */}
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
              {orderType === 'dine_in' ? (
                <button
                  onClick={() => handleCheckout('cash')}
                  disabled={submitting || !isFormValid}
                  className="w-full flex items-center justify-center gap-2 py-3 px-4 bg-emerald-600 text-white rounded-xl hover:bg-emerald-700 disabled:opacity-50 transition-colors"
                >
                  {submitting ? (
                    <Loader2 className="w-5 h-5 animate-spin" />
                  ) : (
                    <>
                      <Utensils className="w-5 h-5" />
                      <span className="text-sm font-bold">Pesan ke Meja</span>
                    </>
                  )}
                </button>
              ) : (
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
              )}

              {/* Minta Bill button for dine-in */}
              {orderType === 'dine_in' && tableId && isPro && (
                <button
                  onClick={handleRequestBill}
                  disabled={requestingBill || billRequested}
                  className="w-full flex items-center justify-center gap-2 py-2.5 px-4 bg-amber-50 text-amber-700 border border-amber-200 rounded-xl hover:bg-amber-100 disabled:opacity-50 transition-colors"
                >
                  <Bell className="w-4 h-4" />
                  <span className="text-sm font-medium">
                    {billRequested ? 'Bill Sudah Diminta — Kasir Akan Menghampiri' : 'Minta Bill'}
                  </span>
                </button>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Mobile: fixed bottom payment */}
      <div className="md:hidden fixed bottom-0 left-0 right-0 bg-white border-t border-gray-100 p-4 z-20 shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.05)]">
        <div className="max-w-md mx-auto space-y-3">
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-500 font-medium">Total Pembayaran</span>
            <span className="text-xl font-bold text-gray-900">{formatCurrency(totalPrice)}</span>
          </div>
          {orderType === 'dine_in' ? (
            <div className="space-y-2">
              <button
                onClick={() => handleCheckout('cash')}
                disabled={submitting || !isFormValid}
                className="w-full flex items-center justify-center gap-2 py-3 px-4 bg-emerald-600 text-white rounded-xl hover:bg-emerald-700 disabled:opacity-50 transition-colors"
              >
                {submitting ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  <>
                    <Utensils className="w-5 h-5" />
                    <span className="text-sm font-bold">Pesan ke Meja</span>
                  </>
                )}
              </button>
              {tableId && (
                <button
                  onClick={handleRequestBill}
                  disabled={requestingBill || billRequested}
                  className="w-full flex items-center justify-center gap-2 py-2.5 px-4 bg-amber-50 text-amber-700 border border-amber-200 rounded-xl disabled:opacity-50 transition-colors"
                >
                  <Bell className="w-4 h-4" />
                  <span className="text-sm font-medium">
                    {billRequested ? 'Bill Diminta' : 'Minta Bill'}
                  </span>
                </button>
              )}
            </div>
          ) : (
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
          )}
        </div>
      </div>
    </div>
  );
}
