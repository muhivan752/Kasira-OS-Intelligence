'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { getAvailableTables, createBooking } from '@/app/actions/storefront';
import { ArrowLeft, Calendar, Clock, Users, MessageCircle, ChevronDown } from 'lucide-react';

export default function BookingPage() {
  const params = useParams();
  const slug = params.slug as string;
  const router = useRouter();

  const [tables, setTables] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  // Form state
  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [date, setDate] = useState('');
  const [time, setTime] = useState('');
  const [guestCount, setGuestCount] = useState(2);
  const [tableId, setTableId] = useState('');
  const [notes, setNotes] = useState('');

  useEffect(() => {
    async function loadTables() {
      const data = await getAvailableTables(slug);
      setTables(data || []);
      setLoading(false);
    }
    loadTables();

    // Default date = tomorrow
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    setDate(tomorrow.toISOString().split('T')[0]);
    setTime('19:00');
  }, [slug]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!name.trim()) { setError('Nama wajib diisi'); return; }
    if (!phone.trim() || phone.length < 9) { setError('Nomor telepon tidak valid'); return; }
    if (!date || !time) { setError('Tanggal dan jam wajib diisi'); return; }

    // Build ISO datetime with WIB offset +07:00
    const reservationTime = `${date}T${time}:00+07:00`;

    setSubmitting(true);
    try {
      const result = await createBooking(slug, {
        customer_name: name.trim(),
        customer_phone: phone.trim(),
        reservation_time: reservationTime,
        guest_count: guestCount,
        table_id: tableId || undefined,
        notes: notes.trim() || undefined,
      });

      if (!result.success) {
        setError(result.message || 'Gagal membuat booking');
        return;
      }

      router.push(`/${slug}/booking/${result.data.booking_id}`);
    } catch {
      setError('Terjadi kesalahan, coba lagi');
    } finally {
      setSubmitting(false);
    }
  };

  // Min date = tomorrow
  const minDate = new Date();
  minDate.setDate(minDate.getDate() + 1);
  const minDateStr = minDate.toISOString().split('T')[0];

  // Filter tables by guest count
  const suitableTables = tables.filter((t) => t.capacity >= guestCount);

  return (
    <div className="max-w-md mx-auto bg-white min-h-screen shadow-sm">
      {/* Header */}
      <div className="sticky top-0 bg-white z-10 border-b border-gray-100 px-4 py-4 flex items-center gap-3">
        <button onClick={() => router.back()} className="p-2 hover:bg-gray-100 rounded-full transition-colors">
          <ArrowLeft className="w-5 h-5 text-gray-700" />
        </button>
        <h1 className="text-lg font-bold text-gray-900">Reservasi Meja</h1>
      </div>

      <form onSubmit={handleSubmit} className="p-4 space-y-5">
        {/* Info banner */}
        <div className="bg-blue-50 border border-blue-100 rounded-xl p-3 text-sm text-blue-800">
          Booking akan dikonfirmasi oleh outlet via WhatsApp. Tidak perlu bayar di muka.
        </div>

        {/* Name */}
        <div>
          <label className="block text-sm font-semibold text-gray-700 mb-1">Nama Lengkap <span className="text-red-500">*</span></label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Nama pemesan"
            className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            required
          />
        </div>

        {/* Phone */}
        <div>
          <label className="block text-sm font-semibold text-gray-700 mb-1">Nomor WhatsApp <span className="text-red-500">*</span></label>
          <input
            type="tel"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            placeholder="08xxx atau +628xxx"
            className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            required
          />
        </div>

        {/* Date + Time */}
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-1">
              <Calendar className="w-4 h-4 inline mr-1" />Tanggal <span className="text-red-500">*</span>
            </label>
            <input
              type="date"
              value={date}
              min={minDateStr}
              onChange={(e) => setDate(e.target.value)}
              className="w-full border border-gray-200 rounded-xl px-3 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-1">
              <Clock className="w-4 h-4 inline mr-1" />Jam <span className="text-red-500">*</span>
            </label>
            <input
              type="time"
              value={time}
              onChange={(e) => setTime(e.target.value)}
              className="w-full border border-gray-200 rounded-xl px-3 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>
        </div>

        {/* Guest Count */}
        <div>
          <label className="block text-sm font-semibold text-gray-700 mb-1">
            <Users className="w-4 h-4 inline mr-1" />Jumlah Tamu <span className="text-red-500">*</span>
          </label>
          <div className="flex items-center gap-4 border border-gray-200 rounded-xl px-4 py-3">
            <button
              type="button"
              onClick={() => setGuestCount((c) => Math.max(1, c - 1))}
              className="w-8 h-8 bg-gray-100 rounded-full flex items-center justify-center font-bold text-gray-700 hover:bg-gray-200 transition-colors"
            >
              −
            </button>
            <span className="flex-1 text-center text-base font-semibold">{guestCount} orang</span>
            <button
              type="button"
              onClick={() => setGuestCount((c) => c + 1)}
              className="w-8 h-8 bg-gray-100 rounded-full flex items-center justify-center font-bold text-gray-700 hover:bg-gray-200 transition-colors"
            >
              +
            </button>
          </div>
        </div>

        {/* Table selection */}
        {!loading && (
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-1">Pilih Meja (opsional)</label>
            {suitableTables.length === 0 ? (
              <div className="border border-gray-200 rounded-xl px-4 py-3 text-sm text-gray-500 bg-gray-50">
                Tidak ada meja tersedia untuk {guestCount} orang. Outlet akan mencarikan meja terbaik.
              </div>
            ) : (
              <div className="relative">
                <select
                  value={tableId}
                  onChange={(e) => setTableId(e.target.value)}
                  className="w-full appearance-none border border-gray-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white pr-10"
                >
                  <option value="">Biarkan outlet memilih</option>
                  {suitableTables.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.name} — kapasitas {t.capacity} orang
                    </option>
                  ))}
                </select>
                <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
              </div>
            )}
          </div>
        )}

        {/* Notes */}
        <div>
          <label className="block text-sm font-semibold text-gray-700 mb-1">Catatan (opsional)</label>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Contoh: ulang tahun, minta meja dekat jendela, alergi kacang..."
            rows={3}
            className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
          />
        </div>

        {/* Error */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {/* Submit */}
        <button
          type="submit"
          disabled={submitting}
          className="w-full bg-blue-600 text-white rounded-xl py-4 font-bold text-base hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {submitting ? 'Mengirim booking...' : 'Buat Reservasi'}
        </button>

        <p className="text-xs text-center text-gray-400 pb-4">
          Konfirmasi dikirim ke WhatsApp Anda setelah booking diterima outlet.
        </p>
      </form>
    </div>
  );
}
