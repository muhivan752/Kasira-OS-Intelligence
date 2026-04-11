'use client';

import { useState, useEffect, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { getStorefront, getReservationSlots, createReservationPublic } from '@/app/actions/storefront';
import {
  ArrowLeft, Calendar, Clock, Users, MapPin, Phone, User,
  ChevronLeft, ChevronRight, CheckCircle2, Loader2, Sparkles,
  MessageCircle, Star,
} from 'lucide-react';

type Slot = { time: string; available: boolean; remaining_capacity: number; tables_available: number };
type Step = 'date' | 'time' | 'info' | 'confirm' | 'success';

export default function BookingPage() {
  const params = useParams();
  const slug = params.slug as string;
  const router = useRouter();

  const [outlet, setOutlet] = useState<any>(null);
  const [step, setStep] = useState<Step>('date');
  const [loading, setLoading] = useState(true);
  const [slotsLoading, setSlotsLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [slotsError, setSlotsError] = useState('');

  // Form
  const [selectedDate, setSelectedDate] = useState('');
  const [guestCount, setGuestCount] = useState(2);
  const [slots, setSlots] = useState<Slot[]>([]);
  const [selectedTime, setSelectedTime] = useState('');
  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [notes, setNotes] = useState('');

  // Success data
  const [bookingResult, setBookingResult] = useState<any>(null);

  useEffect(() => {
    async function load() {
      const data = await getStorefront(slug);
      setOutlet(data);
      setLoading(false);
    }
    load();
    // Default date = tomorrow
    const tmr = new Date();
    tmr.setDate(tmr.getDate() + 1);
    setSelectedDate(tmr.toISOString().split('T')[0]);
  }, [slug]);

  const loadSlots = useCallback(async (date: string, guests: number) => {
    setSlotsLoading(true);
    setSlotsError('');
    setSlots([]);
    setSelectedTime('');
    const result = await getReservationSlots(slug, date, guests);
    if (result && 'error' in result) {
      setSlotsError(result.error as string);
    } else if (result && result.slots) {
      setSlots(result.slots);
    }
    setSlotsLoading(false);
  }, [slug]);

  // Load slots when date or guest count changes
  useEffect(() => {
    if (selectedDate && step === 'time') {
      loadSlots(selectedDate, guestCount);
    }
  }, [selectedDate, guestCount, step, loadSlots]);

  const handleSubmit = async () => {
    setError('');
    if (!name.trim()) { setError('Nama wajib diisi'); return; }
    if (!phone.trim() || phone.length < 10) { setError('Nomor WhatsApp tidak valid (min 10 digit)'); return; }

    setSubmitting(true);
    const result = await createReservationPublic(slug, {
      reservation_date: selectedDate,
      start_time: selectedTime,
      guest_count: guestCount,
      customer_name: name.trim(),
      customer_phone: phone.startsWith('0') ? '62' + phone.slice(1) : phone.trim(),
      notes: notes.trim() || undefined,
    });

    if (!result.success) {
      setError(result.message || 'Gagal membuat reservasi');
      setSubmitting(false);
      return;
    }

    setBookingResult(result.data);
    setStep('success');
    setSubmitting(false);
  };

  // Date helpers
  const generateDates = () => {
    const dates = [];
    const today = new Date();
    for (let i = 1; i <= 14; i++) {
      const d = new Date(today);
      d.setDate(today.getDate() + i);
      dates.push(d);
    }
    return dates;
  };

  const formatDateShort = (d: Date) => {
    const days = ['Min', 'Sen', 'Sel', 'Rab', 'Kam', 'Jum', 'Sab'];
    return { day: days[d.getDay()], date: d.getDate() };
  };

  const formatDateLong = (dateStr: string) => {
    const d = new Date(dateStr + 'T00:00:00');
    return d.toLocaleDateString('id-ID', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    );
  }

  if (!outlet) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="text-center">
          <p className="text-gray-500 text-lg">Outlet tidak ditemukan</p>
          <button onClick={() => router.back()} className="mt-4 text-blue-600 font-medium">Kembali</button>
        </div>
      </div>
    );
  }

  const availableSlots = slots.filter(s => s.available);
  const dates = generateDates();

  return (
    <div className="min-h-screen min-w-full bg-gradient-to-br from-blue-50 via-white to-purple-50">
      {/* Header */}
      <div className="sticky top-0 z-20 bg-white/80 backdrop-blur-xl border-b border-gray-100">
        <div className="max-w-2xl mx-auto px-4 py-3 flex items-center gap-3">
          <button
            onClick={() => {
              if (step === 'date') router.push(`/${slug}`);
              else if (step === 'time') setStep('date');
              else if (step === 'info') setStep('time');
              else if (step === 'confirm') setStep('info');
              else router.push(`/${slug}`);
            }}
            className="p-2 hover:bg-gray-100 rounded-full transition-colors"
          >
            <ArrowLeft className="w-5 h-5 text-gray-700" />
          </button>
          <div className="flex-1">
            <h1 className="text-base font-bold text-gray-900">{outlet.name}</h1>
            <p className="text-xs text-gray-500">Reservasi Meja</p>
          </div>
          <div className="flex items-center gap-1 bg-blue-50 text-blue-700 px-2 py-1 rounded-full text-xs font-semibold">
            <Sparkles className="w-3 h-3" />
            PRO
          </div>
        </div>
        {/* Progress */}
        {step !== 'success' && (
          <div className="max-w-2xl mx-auto px-4 pb-3">
            <div className="flex gap-1">
              {['date', 'time', 'info', 'confirm'].map((s, i) => (
                <div key={s} className={`h-1 flex-1 rounded-full transition-all duration-300 ${
                  i <= ['date', 'time', 'info', 'confirm'].indexOf(step)
                    ? 'bg-blue-600' : 'bg-gray-200'
                }`} />
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="max-w-2xl mx-auto px-4 py-6">

        {/* ── STEP 1: DATE & GUESTS ─────────────────────────── */}
        {step === 'date' && (
          <div className="space-y-6 animate-in fade-in">
            <div className="text-center mb-2">
              <h2 className="text-2xl font-bold text-gray-900">Pilih Tanggal</h2>
              <p className="text-gray-500 mt-1">Kapan Anda ingin berkunjung?</p>
            </div>

            {/* Guest count */}
            <div className="bg-white rounded-2xl p-5 border border-gray-100 shadow-sm">
              <label className="flex items-center gap-2 text-sm font-semibold text-gray-700 mb-3">
                <Users className="w-4 h-4 text-blue-600" />
                Jumlah Tamu
              </label>
              <div className="flex items-center justify-center gap-6">
                <button
                  type="button"
                  onClick={() => setGuestCount(c => Math.max(1, c - 1))}
                  className="w-12 h-12 bg-gray-100 hover:bg-gray-200 rounded-xl flex items-center justify-center text-xl font-bold text-gray-700 transition-colors"
                >
                  −
                </button>
                <div className="text-center min-w-[80px]">
                  <span className="text-4xl font-bold text-gray-900">{guestCount}</span>
                  <p className="text-xs text-gray-500 mt-1">orang</p>
                </div>
                <button
                  type="button"
                  onClick={() => setGuestCount(c => Math.min(20, c + 1))}
                  className="w-12 h-12 bg-gray-100 hover:bg-gray-200 rounded-xl flex items-center justify-center text-xl font-bold text-gray-700 transition-colors"
                >
                  +
                </button>
              </div>
            </div>

            {/* Date picker - horizontal scroll */}
            <div className="bg-white rounded-2xl p-5 border border-gray-100 shadow-sm">
              <label className="flex items-center gap-2 text-sm font-semibold text-gray-700 mb-3">
                <Calendar className="w-4 h-4 text-blue-600" />
                Tanggal Reservasi
              </label>
              <div className="overflow-x-auto -mx-2 px-2 pb-2">
                <div className="flex gap-2 min-w-max">
                  {dates.map((d) => {
                    const dateStr = d.toISOString().split('T')[0];
                    const { day, date } = formatDateShort(d);
                    const isSelected = dateStr === selectedDate;
                    const isWeekend = d.getDay() === 0 || d.getDay() === 6;
                    return (
                      <button
                        key={dateStr}
                        onClick={() => setSelectedDate(dateStr)}
                        className={`flex flex-col items-center min-w-[60px] py-3 px-3 rounded-xl transition-all duration-200 ${
                          isSelected
                            ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/30 scale-105'
                            : isWeekend
                              ? 'bg-orange-50 text-orange-700 hover:bg-orange-100'
                              : 'bg-gray-50 text-gray-700 hover:bg-gray-100'
                        }`}
                      >
                        <span className={`text-xs font-medium ${isSelected ? 'text-blue-100' : ''}`}>{day}</span>
                        <span className="text-lg font-bold mt-0.5">{date}</span>
                      </button>
                    );
                  })}
                </div>
              </div>
              {selectedDate && (
                <p className="text-center text-sm text-gray-600 mt-3 font-medium">
                  {formatDateLong(selectedDate)}
                </p>
              )}
            </div>

            <button
              onClick={() => setStep('time')}
              disabled={!selectedDate}
              className="w-full bg-blue-600 text-white rounded-xl py-4 font-bold text-base hover:bg-blue-700 transition-all disabled:opacity-40 shadow-lg shadow-blue-600/20"
            >
              Pilih Jam
              <ChevronRight className="w-5 h-5 inline ml-1" />
            </button>
          </div>
        )}

        {/* ── STEP 2: TIME SLOT ─────────────────────────────── */}
        {step === 'time' && (
          <div className="space-y-6 animate-in fade-in">
            <div className="text-center mb-2">
              <h2 className="text-2xl font-bold text-gray-900">Pilih Jam</h2>
              <p className="text-gray-500 mt-1">
                {formatDateLong(selectedDate)} &middot; {guestCount} orang
              </p>
            </div>

            {slotsLoading && (
              <div className="flex flex-col items-center justify-center py-16">
                <Loader2 className="w-8 h-8 animate-spin text-blue-600 mb-3" />
                <p className="text-gray-500 text-sm">Mengecek ketersediaan...</p>
              </div>
            )}

            {slotsError && (
              <div className="bg-red-50 border border-red-100 rounded-2xl p-5 text-center">
                <p className="text-red-700 font-medium">{slotsError}</p>
                <button onClick={() => loadSlots(selectedDate, guestCount)} className="mt-3 text-red-600 text-sm font-medium underline">
                  Coba lagi
                </button>
              </div>
            )}

            {!slotsLoading && !slotsError && slots.length > 0 && (
              <div className="bg-white rounded-2xl p-5 border border-gray-100 shadow-sm">
                {availableSlots.length === 0 ? (
                  <div className="text-center py-8">
                    <Clock className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                    <p className="text-gray-600 font-medium">Tidak ada slot tersedia</p>
                    <p className="text-gray-400 text-sm mt-1">Coba pilih tanggal lain</p>
                  </div>
                ) : (
                  <div className="grid grid-cols-3 md:grid-cols-4 gap-2">
                    {slots.map((slot) => {
                      const isSelected = selectedTime === slot.time;
                      return (
                        <button
                          key={slot.time}
                          disabled={!slot.available}
                          onClick={() => setSelectedTime(slot.time)}
                          className={`relative py-3 px-2 rounded-xl text-center transition-all duration-200 ${
                            !slot.available
                              ? 'bg-gray-50 text-gray-300 cursor-not-allowed line-through'
                              : isSelected
                                ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/30 scale-105'
                                : 'bg-gray-50 text-gray-700 hover:bg-blue-50 hover:text-blue-700'
                          }`}
                        >
                          <span className="text-sm font-bold">{slot.time}</span>
                          {slot.available && (
                            <p className={`text-[10px] mt-0.5 ${isSelected ? 'text-blue-200' : 'text-gray-400'}`}>
                              {slot.tables_available} meja
                            </p>
                          )}
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>
            )}

            <button
              onClick={() => setStep('info')}
              disabled={!selectedTime}
              className="w-full bg-blue-600 text-white rounded-xl py-4 font-bold text-base hover:bg-blue-700 transition-all disabled:opacity-40 shadow-lg shadow-blue-600/20"
            >
              Lanjut Isi Data
              <ChevronRight className="w-5 h-5 inline ml-1" />
            </button>
          </div>
        )}

        {/* ── STEP 3: CUSTOMER INFO ─────────────────────────── */}
        {step === 'info' && (
          <div className="space-y-6 animate-in fade-in">
            <div className="text-center mb-2">
              <h2 className="text-2xl font-bold text-gray-900">Data Pemesan</h2>
              <p className="text-gray-500 mt-1">Isi data untuk konfirmasi reservasi</p>
            </div>

            <div className="bg-white rounded-2xl p-5 border border-gray-100 shadow-sm space-y-4">
              <div>
                <label className="flex items-center gap-2 text-sm font-semibold text-gray-700 mb-2">
                  <User className="w-4 h-4 text-blue-600" />
                  Nama Lengkap
                </label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Masukkan nama Anda"
                  className="w-full border border-gray-200 rounded-xl px-4 py-3.5 text-sm bg-gray-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                />
              </div>

              <div>
                <label className="flex items-center gap-2 text-sm font-semibold text-gray-700 mb-2">
                  <Phone className="w-4 h-4 text-blue-600" />
                  Nomor WhatsApp
                </label>
                <input
                  type="tel"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  placeholder="0812xxxxxxxx"
                  className="w-full border border-gray-200 rounded-xl px-4 py-3.5 text-sm bg-gray-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                />
                <p className="text-xs text-gray-400 mt-1.5">Konfirmasi akan dikirim via WhatsApp</p>
              </div>

              <div>
                <label className="flex items-center gap-2 text-sm font-semibold text-gray-700 mb-2">
                  <MessageCircle className="w-4 h-4 text-blue-600" />
                  Catatan <span className="text-gray-400 font-normal">(opsional)</span>
                </label>
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Contoh: minta meja dekat jendela, acara ulang tahun, dsb."
                  rows={3}
                  className="w-full border border-gray-200 rounded-xl px-4 py-3.5 text-sm bg-gray-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all resize-none"
                />
              </div>
            </div>

            {error && (
              <div className="bg-red-50 border border-red-100 rounded-xl px-4 py-3 text-sm text-red-700 font-medium">
                {error}
              </div>
            )}

            <button
              onClick={() => { setError(''); setStep('confirm'); }}
              className="w-full bg-blue-600 text-white rounded-xl py-4 font-bold text-base hover:bg-blue-700 transition-all shadow-lg shadow-blue-600/20"
            >
              Lihat Ringkasan
              <ChevronRight className="w-5 h-5 inline ml-1" />
            </button>
          </div>
        )}

        {/* ── STEP 4: CONFIRM ───────────────────────────────── */}
        {step === 'confirm' && (
          <div className="space-y-6 animate-in fade-in">
            <div className="text-center mb-2">
              <h2 className="text-2xl font-bold text-gray-900">Konfirmasi Reservasi</h2>
              <p className="text-gray-500 mt-1">Pastikan semua data sudah benar</p>
            </div>

            <div className="bg-white rounded-2xl overflow-hidden border border-gray-100 shadow-sm">
              {/* Outlet info */}
              <div className="bg-gradient-to-r from-blue-600 to-blue-700 px-5 py-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-white/20 rounded-xl flex items-center justify-center">
                    <MapPin className="w-5 h-5 text-white" />
                  </div>
                  <div>
                    <p className="text-white font-bold">{outlet.name}</p>
                    <p className="text-blue-200 text-xs">{outlet.address || 'Alamat outlet'}</p>
                  </div>
                </div>
              </div>

              <div className="p-5 space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-blue-50 rounded-xl p-3 text-center">
                    <Calendar className="w-5 h-5 text-blue-600 mx-auto mb-1" />
                    <p className="text-xs text-blue-600 font-medium">Tanggal</p>
                    <p className="text-sm font-bold text-gray-900 mt-0.5">
                      {new Date(selectedDate + 'T00:00:00').toLocaleDateString('id-ID', { day: 'numeric', month: 'short', year: 'numeric' })}
                    </p>
                  </div>
                  <div className="bg-purple-50 rounded-xl p-3 text-center">
                    <Clock className="w-5 h-5 text-purple-600 mx-auto mb-1" />
                    <p className="text-xs text-purple-600 font-medium">Jam</p>
                    <p className="text-sm font-bold text-gray-900 mt-0.5">{selectedTime} WIB</p>
                  </div>
                </div>

                <div className="border-t border-gray-100 pt-4 space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-500">Nama</span>
                    <span className="text-sm font-semibold text-gray-900">{name}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-500">WhatsApp</span>
                    <span className="text-sm font-semibold text-gray-900">{phone}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-500">Jumlah Tamu</span>
                    <span className="text-sm font-semibold text-gray-900">{guestCount} orang</span>
                  </div>
                  {notes && (
                    <div className="flex justify-between items-start">
                      <span className="text-sm text-gray-500">Catatan</span>
                      <span className="text-sm text-gray-700 text-right max-w-[200px]">{notes}</span>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {error && (
              <div className="bg-red-50 border border-red-100 rounded-xl px-4 py-3 text-sm text-red-700 font-medium">
                {error}
              </div>
            )}

            <button
              onClick={handleSubmit}
              disabled={submitting}
              className="w-full bg-blue-600 text-white rounded-xl py-4 font-bold text-base hover:bg-blue-700 transition-all disabled:opacity-50 shadow-lg shadow-blue-600/20"
            >
              {submitting ? (
                <span className="flex items-center justify-center gap-2">
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Mengirim...
                </span>
              ) : (
                'Konfirmasi Reservasi'
              )}
            </button>

            <p className="text-xs text-center text-gray-400">
              Dengan melanjutkan, Anda menyetujui kebijakan reservasi outlet.
            </p>
          </div>
        )}

        {/* ── STEP 5: SUCCESS ───────────────────────────────── */}
        {step === 'success' && bookingResult && (
          <div className="space-y-6 animate-in fade-in">
            <div className="text-center py-6">
              <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <CheckCircle2 className="w-10 h-10 text-green-600" />
              </div>
              <h2 className="text-2xl font-bold text-gray-900">
                {bookingResult.status === 'confirmed' ? 'Reservasi Dikonfirmasi!' : 'Reservasi Diterima!'}
              </h2>
              <p className="text-gray-500 mt-2">
                {bookingResult.status === 'confirmed'
                  ? 'Kami tunggu kedatangan Anda.'
                  : 'Menunggu konfirmasi dari outlet. Anda akan dihubungi via WhatsApp.'}
              </p>
            </div>

            <div className="bg-white rounded-2xl p-5 border border-gray-100 shadow-sm space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-blue-50 rounded-xl p-3 text-center">
                  <Calendar className="w-5 h-5 text-blue-600 mx-auto mb-1" />
                  <p className="text-xs text-blue-600 font-medium">Tanggal</p>
                  <p className="text-sm font-bold text-gray-900 mt-0.5">
                    {new Date(bookingResult.reservation_date + 'T00:00:00').toLocaleDateString('id-ID', { day: 'numeric', month: 'short' })}
                  </p>
                </div>
                <div className="bg-purple-50 rounded-xl p-3 text-center">
                  <Clock className="w-5 h-5 text-purple-600 mx-auto mb-1" />
                  <p className="text-xs text-purple-600 font-medium">Jam</p>
                  <p className="text-sm font-bold text-gray-900 mt-0.5">{bookingResult.start_time} — {bookingResult.end_time}</p>
                </div>
              </div>

              <div className="border-t border-gray-100 pt-4 space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-500">Meja</span>
                  <span className="text-sm font-semibold text-gray-900">{bookingResult.table_name}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-500">Jumlah Tamu</span>
                  <span className="text-sm font-semibold text-gray-900">{bookingResult.guest_count} orang</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-500">Status</span>
                  <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold ${
                    bookingResult.status === 'confirmed'
                      ? 'bg-green-100 text-green-700'
                      : 'bg-yellow-100 text-yellow-700'
                  }`}>
                    {bookingResult.status === 'confirmed' ? '✓ Dikonfirmasi' : '⏳ Menunggu'}
                  </span>
                </div>
              </div>
            </div>

            <div className="flex flex-col gap-3">
              <button
                onClick={() => router.push(`/${slug}`)}
                className="w-full bg-blue-600 text-white rounded-xl py-4 font-bold text-base hover:bg-blue-700 transition-all shadow-lg shadow-blue-600/20"
              >
                Kembali ke Menu
              </button>
              <button
                onClick={() => {
                  setStep('date');
                  setSelectedDate('');
                  setSelectedTime('');
                  setName('');
                  setPhone('');
                  setNotes('');
                  setBookingResult(null);
                  const tmr = new Date();
                  tmr.setDate(tmr.getDate() + 1);
                  setSelectedDate(tmr.toISOString().split('T')[0]);
                }}
                className="w-full bg-gray-100 text-gray-700 rounded-xl py-4 font-bold text-base hover:bg-gray-200 transition-all"
              >
                Buat Reservasi Lain
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
