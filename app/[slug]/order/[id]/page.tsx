'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { getStorefrontOrder, getStorefront } from '@/app/actions/storefront';
import { CheckCircle2, Clock, ChefHat, PackageCheck, MessageCircle, ArrowLeft, Loader2, MapPin } from 'lucide-react';
import Link from 'next/link';

export default function OrderStatusPage() {
  const params = useParams();
  const slug = params.slug as string;
  const orderId = params.id as string;
  const router = useRouter();
  
  const [loading, setLoading] = useState(true);
  const [order, setOrder] = useState<any>(null);
  const [storeData, setStoreData] = useState<any>(null);

  useEffect(() => {
    async function loadData() {
      const [orderData, store] = await Promise.all([
        getStorefrontOrder(orderId),
        getStorefront(slug)
      ]);
      
      if (orderData) setOrder(orderData);
      if (store) setStoreData(store);
      
      setLoading(false);
    }
    
    loadData();

    // Poll every 5 seconds
    const interval = setInterval(async () => {
      const data = await getStorefrontOrder(orderId);
      if (data) setOrder(data);
    }, 5000);

    return () => clearInterval(interval);
  }, [slug, orderId]);

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center">Loading...</div>;
  }

  if (!order) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center p-4 text-center">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Pesanan Tidak Ditemukan</h1>
        <p className="text-gray-500 mb-8">Pesanan yang Anda cari tidak ada atau link tidak valid.</p>
        <Link 
          href={`/${slug}`}
          className="px-6 py-3 bg-blue-600 text-white font-medium rounded-xl hover:bg-blue-700 transition-colors"
        >
          Kembali ke Menu
        </Link>
      </div>
    );
  }

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('id-ID', { style: 'currency', currency: 'IDR' }).format(amount || 0);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('id-ID', {
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const handleWhatsApp = () => {
    if (!storeData?.outlet?.phone) return;
    const phone = storeData.outlet.phone.startsWith('0') ? '62' + storeData.outlet.phone.slice(1) : storeData.outlet.phone;
    const text = `Halo ${storeData.outlet.name}, saya ingin bertanya tentang pesanan saya dengan nomor *${order.order_number}*.`;
    window.open(`https://wa.me/${phone}?text=${encodeURIComponent(text)}`, '_blank');
  };

  // Timeline logic
  const statuses = [
    { id: 'pending', label: 'Diterima', icon: Clock, desc: 'Menunggu konfirmasi' },
    { id: 'processing', label: 'Diproses', icon: ChefHat, desc: 'Sedang disiapkan' },
    { id: 'ready', label: 'Siap', icon: PackageCheck, desc: order.order_type === 'pickup' ? 'Siap diambil' : 'Siap dikirim' },
    { id: 'completed', label: 'Selesai', icon: CheckCircle2, desc: 'Pesanan selesai' }
  ];

  const getStatusIndex = (status: string) => {
    if (status === 'cancelled') return -1;
    return statuses.findIndex(s => s.id === status);
  };

  const currentIndex = getStatusIndex(order.status);

  return (
    <div className="max-w-md mx-auto bg-gray-50 min-h-screen pb-24">
      {/* Header */}
      <div className="bg-white px-4 py-4 border-b border-gray-100 flex items-center gap-4">
        <Link href={`/${slug}`} className="p-2 -ml-2 text-gray-500 hover:bg-gray-100 rounded-full transition-colors">
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <h1 className="text-lg font-bold text-gray-900 flex-1 text-center pr-8">Status Pesanan</h1>
      </div>

      {/* Order Info */}
      <div className="bg-white p-6 mb-2 flex flex-col items-center text-center">
        <p className="text-sm font-medium text-gray-500 mb-1">Nomor Pesanan</p>
        <h2 className="text-3xl font-black text-gray-900 tracking-tight mb-4">{order.order_number}</h2>
        
        {order.status === 'cancelled' ? (
          <div className="px-4 py-2 bg-red-100 text-red-800 rounded-full text-sm font-bold">
            Pesanan Dibatalkan
          </div>
        ) : (
          <div className="flex items-center gap-2 text-blue-600 bg-blue-50 px-4 py-2 rounded-full">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span className="text-sm font-bold">
              {statuses[currentIndex]?.label || 'Memproses...'}
            </span>
          </div>
        )}
      </div>

      {/* Timeline */}
      {order.status !== 'cancelled' && (
        <div className="bg-white p-6 mb-2">
          <h3 className="text-sm font-bold text-gray-900 mb-6">Lacak Pesanan</h3>
          <div className="relative">
            {/* Vertical Line */}
            <div className="absolute left-6 top-6 bottom-6 w-0.5 bg-gray-100" />
            
            <div className="space-y-8 relative">
              {statuses.map((step, index) => {
                const isCompleted = index <= currentIndex;
                const isCurrent = index === currentIndex;
                
                return (
                  <div key={step.id} className="flex gap-4 relative">
                    <div className={`w-12 h-12 rounded-full flex items-center justify-center shrink-0 z-10 transition-colors ${
                      isCompleted ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-400'
                    }`}>
                      <step.icon className="w-6 h-6" />
                    </div>
                    <div className="pt-2">
                      <h4 className={`text-base font-bold ${isCompleted ? 'text-gray-900' : 'text-gray-400'}`}>
                        {step.label}
                      </h4>
                      <p className={`text-sm ${isCompleted ? 'text-gray-600' : 'text-gray-400'}`}>
                        {step.desc}
                      </p>
                      {isCurrent && index === 1 && (
                        <p className="text-xs font-medium text-blue-600 mt-1">
                          Estimasi 10-15 menit
                        </p>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* Order Details */}
      <div className="bg-white p-6 mb-2 space-y-4">
        <h3 className="text-sm font-bold text-gray-900 border-b border-gray-100 pb-2">Detail Pesanan</h3>
        
        <div className="space-y-3">
          {order.items.map((item: any) => (
            <div key={item.id} className="flex justify-between text-sm">
              <div className="flex gap-2">
                <span className="font-medium text-gray-900">{item.quantity}x</span>
                <span className="text-gray-600">{item.product_name}</span>
              </div>
              <span className="font-medium text-gray-900">{formatCurrency(parseFloat(item.price) * item.quantity)}</span>
            </div>
          ))}
        </div>
        
        <div className="pt-4 border-t border-gray-100 space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-gray-500">Tipe Pesanan</span>
            <span className="font-medium text-gray-900 uppercase">{order.order_type}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-gray-500">Metode Pembayaran</span>
            <span className="font-medium text-gray-900 uppercase">{order.payment_method}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-gray-500">Waktu Pemesanan</span>
            <span className="font-medium text-gray-900">{formatDate(order.created_at)}</span>
          </div>
          
          {order.order_type === 'delivery' && order.delivery_address && (
            <div className="pt-2">
              <span className="text-gray-500 text-sm block mb-1">Alamat Pengiriman:</span>
              <div className="flex gap-2 text-sm text-gray-900 bg-gray-50 p-3 rounded-lg">
                <MapPin className="w-4 h-4 text-gray-400 shrink-0 mt-0.5" />
                <p>{order.delivery_address}</p>
              </div>
            </div>
          )}
        </div>
        
        <div className="pt-4 border-t border-gray-100 flex justify-between items-center">
          <span className="font-bold text-gray-900">Total</span>
          <span className="text-lg font-black text-blue-600">{formatCurrency(parseFloat(order.total_amount))}</span>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="fixed bottom-0 left-0 right-0 p-4 bg-white border-t border-gray-100 z-20 shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.05)]">
        <div className="max-w-md mx-auto">
          <button 
            onClick={handleWhatsApp}
            className="w-full flex items-center justify-center gap-2 px-6 py-3 bg-green-500 text-white font-bold rounded-xl hover:bg-green-600 transition-colors"
          >
            <MessageCircle className="w-5 h-5" />
            Hubungi Outlet via WA
          </button>
        </div>
      </div>
    </div>
  );
}
