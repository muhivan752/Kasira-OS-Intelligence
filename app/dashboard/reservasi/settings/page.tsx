'use client';

import { useState, useEffect } from 'react';
import { getOutlets, getReservationSettings, updateReservationSettings } from '@/app/actions/api';
import { Loader2, ArrowLeft, Settings } from 'lucide-react';
import Link from 'next/link';

export default function ReservationSettingsPage() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [outletId, setOutletId] = useState('');

  const [form, setForm] = useState({
    is_enabled: true,
    slot_duration_minutes: 60,
    opening_hour: '08:00',
    closing_hour: '22:00',
    max_advance_days: 30,
    min_advance_hours: 2,
    max_reservations_per_slot: 5,
    auto_confirm: false,
    require_deposit: false,
    deposit_amount: 0,
    reminder_hours_before: 2,
  });

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    setLoading(true);
    try {
      const outlets = await getOutlets();
      if (outlets && outlets.length > 0) {
        const id = outlets[0].id;
        setOutletId(id);
        const settings = await getReservationSettings(id);
        if (settings) {
          setForm({
            is_enabled: settings.is_enabled ?? true,
            slot_duration_minutes: settings.slot_duration_minutes ?? 60,
            opening_hour: settings.opening_hour ?? '08:00',
            closing_hour: settings.closing_hour ?? '22:00',
            max_advance_days: settings.max_advance_days ?? 30,
            min_advance_hours: settings.min_advance_hours ?? 2,
            max_reservations_per_slot: settings.max_reservations_per_slot ?? 5,
            auto_confirm: settings.auto_confirm ?? false,
            require_deposit: settings.require_deposit ?? false,
            deposit_amount: settings.deposit_amount ?? 0,
            reminder_hours_before: settings.reminder_hours_before ?? 2,
          });
        }
      }
    } catch (error) {
      console.error('Failed to load settings', error);
    } finally {
      setLoading(false);
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    const res = await updateReservationSettings(outletId, form);
    if (res.success) {
      alert('Pengaturan reservasi berhasil disimpan');
    } else {
      alert(res.message || 'Gagal menyimpan pengaturan');
    }
    setSaving(false);
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('id-ID', { style: 'currency', currency: 'IDR' }).format(amount || 0);
  };

  if (loading) {
    return <div className="flex items-center justify-center h-64"><Loader2 className="w-6 h-6 animate-spin text-blue-500" /></div>;
  }

  return (
    <div className="space-y-6 max-w-2xl">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link href="/dashboard/reservasi" className="p-2 text-gray-500 hover:bg-gray-100 rounded-lg">
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Pengaturan Reservasi</h1>
          <p className="text-gray-500">Atur preferensi reservasi untuk outlet Anda.</p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Enable/Disable */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200 flex items-center gap-2">
            <Settings className="w-5 h-5 text-gray-500" />
            <h2 className="text-lg font-bold text-gray-900">Umum</h2>
          </div>
          <div className="p-6 space-y-5">
            {/* Toggle Reservasi */}
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-medium text-gray-900">Aktifkan Reservasi</h3>
                <p className="text-xs text-gray-500">Terima reservasi dari pelanggan melalui storefront.</p>
              </div>
              <button
                type="button"
                onClick={() => setForm({ ...form, is_enabled: !form.is_enabled })}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${form.is_enabled ? 'bg-blue-600' : 'bg-gray-200'}`}
              >
                <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${form.is_enabled ? 'translate-x-6' : 'translate-x-1'}`} />
              </button>
            </div>

            {/* Auto Confirm */}
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-medium text-gray-900">Auto-Konfirmasi</h3>
                <p className="text-xs text-gray-500">Otomatis konfirmasi reservasi tanpa perlu persetujuan manual.</p>
              </div>
              <button
                type="button"
                onClick={() => setForm({ ...form, auto_confirm: !form.auto_confirm })}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${form.auto_confirm ? 'bg-blue-600' : 'bg-gray-200'}`}
              >
                <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${form.auto_confirm ? 'translate-x-6' : 'translate-x-1'}`} />
              </button>
            </div>

            {/* Slot Duration */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Durasi Slot (menit)</label>
              <select
                value={form.slot_duration_minutes}
                onChange={e => setForm({ ...form, slot_duration_minutes: parseInt(e.target.value) })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-sm"
              >
                <option value={60}>60 menit</option>
                <option value={90}>90 menit</option>
                <option value={120}>120 menit</option>
                <option value={180}>180 menit</option>
              </select>
            </div>

            {/* Opening/Closing Hours */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Jam Buka</label>
                <input
                  type="time"
                  value={form.opening_hour}
                  onChange={e => setForm({ ...form, opening_hour: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-sm"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Jam Tutup</label>
                <input
                  type="time"
                  value={form.closing_hour}
                  onChange={e => setForm({ ...form, closing_hour: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-sm"
                />
              </div>
            </div>

            {/* Advance Booking */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Maks. Hari ke Depan</label>
                <input
                  type="number"
                  min={1}
                  value={form.max_advance_days}
                  onChange={e => setForm({ ...form, max_advance_days: parseInt(e.target.value) || 1 })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-sm"
                />
                <p className="text-xs text-gray-400 mt-1">Pelanggan bisa pesan maksimal berapa hari ke depan.</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Min. Jam Sebelumnya</label>
                <input
                  type="number"
                  min={0}
                  value={form.min_advance_hours}
                  onChange={e => setForm({ ...form, min_advance_hours: parseInt(e.target.value) || 0 })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-sm"
                />
                <p className="text-xs text-gray-400 mt-1">Minimal berapa jam sebelum waktu reservasi.</p>
              </div>
            </div>

            {/* Max per slot */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Maks. Reservasi per Slot</label>
              <input
                type="number"
                min={1}
                value={form.max_reservations_per_slot}
                onChange={e => setForm({ ...form, max_reservations_per_slot: parseInt(e.target.value) || 1 })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-sm"
              />
            </div>

            {/* Reminder */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Pengingat (jam sebelum)</label>
              <input
                type="number"
                min={0}
                value={form.reminder_hours_before}
                onChange={e => setForm({ ...form, reminder_hours_before: parseInt(e.target.value) || 0 })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-sm"
              />
              <p className="text-xs text-gray-400 mt-1">Kirim pengingat ke pelanggan berapa jam sebelum reservasi.</p>
            </div>
          </div>
        </div>

        {/* Deposit Settings */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-bold text-gray-900">Deposit</h2>
          </div>
          <div className="p-6 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-medium text-gray-900">Wajibkan Deposit</h3>
                <p className="text-xs text-gray-500">Pelanggan harus membayar deposit saat reservasi.</p>
              </div>
              <button
                type="button"
                onClick={() => setForm({ ...form, require_deposit: !form.require_deposit })}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${form.require_deposit ? 'bg-blue-600' : 'bg-gray-200'}`}
              >
                <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${form.require_deposit ? 'translate-x-6' : 'translate-x-1'}`} />
              </button>
            </div>

            {form.require_deposit && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Jumlah Deposit</label>
                <input
                  type="number"
                  min={0}
                  value={form.deposit_amount}
                  onChange={e => setForm({ ...form, deposit_amount: parseInt(e.target.value) || 0 })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                />
                {form.deposit_amount > 0 && (
                  <p className="text-xs text-gray-400 mt-1">{formatCurrency(form.deposit_amount)}</p>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Save button */}
        <div className="flex justify-end">
          <button
            type="submit"
            disabled={saving}
            className="flex items-center justify-center px-5 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {saving ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
            Simpan Pengaturan
          </button>
        </div>
      </form>
    </div>
  );
}
