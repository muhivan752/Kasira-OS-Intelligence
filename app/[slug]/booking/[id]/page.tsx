'use client';

import { useState, useEffect, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { getBookingStatus } from '@/app/actions/storefront';
import { ArrowLeft, CheckCircle2, Clock, XCircle, CalendarCheck, Users, MessageCircle, Phone } from 'lucide-react';

const STATUS_META: Record<string, { label: string; color: string; icon: React.ReactNode; description: string }> = {
  pending: {
    label: 'Menunggu Konfirmasi',
    color: 'text-yellow-600',
    icon: <Clock className="w-10 h-10 text-yellow-500" />,
    description: 'Booking Anda sudah diterima. Outlet akan segera mengkonfirmasi.',
  },
  confirmed: {
    label: 'Reservasi Dikonfirmasi!',
    color: 'text-green-600',
    icon: <CheckCircle2 className="w-10 h-10 text-green-500" />,
    description: 'Meja sudah disiapkan untuk Anda. Sampai jumpa!',
  },
  cancelled: {
    label: 'Reservasi Dibatalkan',
    color: 'text-red-600',
    icon: <XCircle className="w-10 h-10 text-red-500" />,
    description: 'Maaf, reservasi ini tidak dapat dipenuhi. Silakan hubungi outlet untuk info lebih lanjut.',
  },
  completed: {
    label: 'Reservasi Selesai',
    color: 'text-gray-600',
    icon: <CalendarCheck className="w-10 h-10 text-gray-400" />,
    description: 'Terima kasih sudah berkunjung!',
  },
};

export default function BookingStatusPage() {
  const params = useParams();
  const slug = params.slug as string;
  const bookingId = params.id as string;
  const router = useRouter();

  const [booking, setBooking] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  const fetchBooking = async () => {
    const data = await getBookingStatus(bookingId);
    if (data) {
      setBooking(data);
      // Stop polling when final status reached
      if (['confirmed', 'cancelled', 'completed'].includes(data.status)) {
        if (intervalRef.current) {
          clearInterval(intervalRef.current);
          intervalRef.current = null;
        }
      }
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchBooking();
    // Poll every 10 seconds
    intervalRef.current = setInterval(fetchBooking, 10_000);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [bookingId]);

  const formatDateTime = (isoStr: string) => {
    if (!isoStr) return '-';
    try {
      return new Intl.DateTimeFormat('id-ID', {
        weekday: 'long',
        day: 'numeric',
        month: 'long',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        timeZone: 'Asia/Jakarta',
      }).format(new Date(isoStr));
    } catch {
      return isoStr;
    }
  };

  const handleWhatsApp = () => {
    if (!booking?.outlet?.phone) return;
    const phone = booking.outlet.phone.startsWith('0')
      ? '62' + booking.outlet.phone.slice(1)
      : booking.outlet.phone;
    const msg = encodeURIComponent(
      `Halo ${booking.outlet.name}, saya ${booking.customer_name} ingin menanyakan reservasi saya (ID: ${bookingId.slice(0, 8).toUpperCase()}).`
    );
    window.open(`https://wa.me/${phone}?text=${msg}`, '_blank');
  };

  if (loading) {
    return (
      <div className="max-w-md mx-auto min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="w-10 h-10 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-sm text-gray-500">Memuat status booking...</p>
        </div>
      </div>
    );
  }

  if (!booking) {
    return (
      <div className="max-w-md mx-auto min-h-screen flex flex-col items-center justify-center p-6 text-center">
        <XCircle className="w-16 h-16 text-gray-300 mb-4" />
        <h2 className="text-xl font-bold text-gray-900 mb-2">Booking Tidak Ditemukan</h2>
        <p className="text-gray-500 mb-6">ID booking tidak valid atau sudah kedaluwarsa.</p>
        <button
          onClick={() => router.push(`/${slug}`)}
          className="bg-blue-600 text-white px-6 py-3 rounded-xl font-semibold"
        >
          Kembali ke Menu
        </button>
      </div>
    );
  }

  const meta = STATUS_META[booking.status] || STATUS_META['pending'];

  return (
    <div className="max-w-md mx-auto bg-white min-h-screen shadow-sm">
      {/* Header */}
      <div className="sticky top-0 bg-white z-10 border-b border-gray-100 px-4 py-4 flex items-center gap-3">
        <button onClick={() => router.push(`/${slug}`)} className="p-2 hover:bg-gray-100 rounded-full transition-colors">
          <ArrowLeft className="w-5 h-5 text-gray-700" />
        </button>
        <h1 className="text-lg font-bold text-gray-900">Status Reservasi</h1>
      </div>

      <div className="p-6">
        {/* Status card */}
        <div className="flex flex-col items-center text-center py-6">
          {meta.icon}
          <h2 className={`text-xl font-bold mt-3 ${meta.color}`}>{meta.label}</h2>
          <p className="text-sm text-gray-500 mt-1 max-w-xs">{meta.description}</p>
          {booking.status === 'pending' && (
            <div className="flex items-center gap-2 mt-3 text-xs text-gray-400">
              <div className="w-2 h-2 bg-yellow-400 rounded-full animate-pulse" />
              Halaman ini otomatis diperbarui
            </div>
          )}
        </div>

        {/* Booking details */}
        <div className="bg-gray-50 rounded-2xl p-4 space-y-3 mt-2">
          <DetailRow
            icon={<CalendarCheck className="w-4 h-4 text-blue-500" />}
            label="Waktu Reservasi"
            value={formatDateTime(booking.reservation_time)}
          />
          <DetailRow
            icon={<Users className="w-4 h-4 text-blue-500" />}
            label="Jumlah Tamu"
            value={`${booking.guest_count} orang`}
          />
          {booking.table_name && (
            <DetailRow
              icon={<span className="text-blue-500 text-xs font-bold">🪑</span>}
              label="Meja"
              value={booking.table_name}
            />
          )}
          {booking.notes && (
            <DetailRow
              icon={<span className="text-blue-500 text-xs">📝</span>}
              label="Catatan"
              value={booking.notes}
            />
          )}
          <div className="border-t border-gray-200 pt-3">
            <DetailRow
              icon={<span className="text-gray-400 text-xs">🔖</span>}
              label="ID Booking"
              value={bookingId.slice(0, 8).toUpperCase()}
            />
          </div>
        </div>

        {/* Guest info */}
        <div className="mt-4 bg-white border border-gray-200 rounded-2xl p-4 space-y-2">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Data Pemesan</p>
          <p className="text-sm font-semibold text-gray-900">{booking.customer_name}</p>
          {booking.customer_phone && (
            <p className="text-sm text-gray-600 flex items-center gap-1">
              <Phone className="w-3 h-3" /> {booking.customer_phone}
            </p>
          )}
        </div>

        {/* WA button */}
        {booking.outlet?.phone && (
          <button
            onClick={handleWhatsApp}
            className="w-full mt-5 flex items-center justify-center gap-2 bg-green-500 text-white rounded-xl py-3 font-semibold hover:bg-green-600 transition-colors"
          >
            <MessageCircle className="w-5 h-5" />
            Hubungi {booking.outlet.name || 'Outlet'}
          </button>
        )}

        {/* Back to menu */}
        <button
          onClick={() => router.push(`/${slug}`)}
          className="w-full mt-3 border border-gray-200 text-gray-700 rounded-xl py-3 font-semibold hover:bg-gray-50 transition-colors"
        >
          Kembali ke Menu
        </button>
      </div>
    </div>
  );
}

function DetailRow({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="flex items-start gap-3">
      <div className="mt-0.5">{icon}</div>
      <div className="flex-1 min-w-0">
        <p className="text-xs text-gray-400 font-medium">{label}</p>
        <p className="text-sm text-gray-900 font-semibold break-words">{value}</p>
      </div>
    </div>
  );
}
