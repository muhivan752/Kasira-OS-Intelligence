'use client';

import { useState, useEffect } from 'react';
import {
  getOutlets,
  getReservations,
  getTables,
  createReservation,
  confirmReservation,
  seatReservation,
  completeReservation,
  cancelReservation,
  noShowReservation,
} from '@/app/actions/api';
import {
  Loader2,
  X,
  ChevronLeft,
  ChevronRight,
  Plus,
  Clock,
  Users,
  Phone,
  MessageSquare,
  CheckCircle2,
  XCircle,
  UserX,
  Armchair,
  CalendarCheck,
} from 'lucide-react';
import Link from 'next/link';

const STATUS_CONFIG: Record<string, { label: string; color: string; bg: string; border: string }> = {
  pending: { label: 'Menunggu', color: 'text-yellow-700', bg: 'bg-yellow-50', border: 'border-yellow-300' },
  confirmed: { label: 'Dikonfirmasi', color: 'text-green-700', bg: 'bg-green-50', border: 'border-green-300' },
  seated: { label: 'Duduk', color: 'text-blue-700', bg: 'bg-blue-50', border: 'border-blue-300' },
  completed: { label: 'Selesai', color: 'text-gray-700', bg: 'bg-gray-50', border: 'border-gray-300' },
  cancelled: { label: 'Dibatalkan', color: 'text-red-700', bg: 'bg-red-50', border: 'border-red-300' },
  no_show: { label: 'Tidak Hadir', color: 'text-orange-700', bg: 'bg-orange-50', border: 'border-orange-300' },
};

const STATUS_FILTERS = [
  { value: '', label: 'Semua' },
  { value: 'pending', label: 'Menunggu' },
  { value: 'confirmed', label: 'Dikonfirmasi' },
  { value: 'seated', label: 'Duduk' },
];

function formatDate(date: Date): string {
  return date.toISOString().split('T')[0];
}

function formatDisplayDate(date: Date): string {
  return date.toLocaleDateString('id-ID', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
}

export default function ReservasiPage() {
  const [loading, setLoading] = useState(true);
  const [outletId, setOutletId] = useState('');
  const [reservations, setReservations] = useState<any[]>([]);
  const [tables, setTables] = useState<any[]>([]);
  const [selectedDate, setSelectedDate] = useState(new Date());
  const [statusFilter, setStatusFilter] = useState('');

  // Modals
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [detailModalOpen, setDetailModalOpen] = useState(false);
  const [selectedReservation, setSelectedReservation] = useState<any>(null);
  const [saving, setSaving] = useState(false);
  const [prefillTime, setPrefillTime] = useState('');

  // Create form
  const [form, setForm] = useState({
    reservation_date: '',
    start_time: '',
    guest_count: 2,
    customer_name: '',
    customer_phone: '',
    table_id: '',
    notes: '',
    source: 'walk_in',
  });

  useEffect(() => {
    loadInitial();
  }, []);

  useEffect(() => {
    if (outletId) loadReservations();
  }, [selectedDate, statusFilter, outletId]);

  async function loadInitial() {
    setLoading(true);
    try {
      const outlets = await getOutlets();
      if (outlets && outlets.length > 0) {
        const id = outlets[0].id;
        setOutletId(id);
        const [resvData, tableData] = await Promise.all([
          getReservations(id, formatDate(selectedDate), statusFilter || undefined),
          getTables(id),
        ]);
        setReservations(resvData || []);
        setTables(tableData || []);
      }
    } catch (error) {
      console.error('Failed to load data', error);
    } finally {
      setLoading(false);
    }
  }

  async function loadReservations() {
    try {
      const data = await getReservations(outletId, formatDate(selectedDate), statusFilter || undefined);
      setReservations(data || []);
    } catch { }
  }

  // Date navigation
  const goToDate = (offset: number) => {
    const d = new Date(selectedDate);
    d.setDate(d.getDate() + offset);
    setSelectedDate(d);
  };

  const goToToday = () => setSelectedDate(new Date());

  const isToday = formatDate(selectedDate) === formatDate(new Date());

  // Stats
  const stats = {
    total: reservations.length,
    pending: reservations.filter(r => r.status === 'pending').length,
    confirmed: reservations.filter(r => r.status === 'confirmed').length,
    seated: reservations.filter(r => r.status === 'seated').length,
  };

  // Timeline hours (8am-23pm)
  const timeSlots: string[] = [];
  for (let h = 8; h <= 23; h++) {
    timeSlots.push(`${h.toString().padStart(2, '0')}:00`);
  }

  // Open create modal
  const openCreateModal = (time?: string) => {
    setForm({
      reservation_date: formatDate(selectedDate),
      start_time: time || '12:00',
      guest_count: 2,
      customer_name: '',
      customer_phone: '',
      table_id: '',
      notes: '',
      source: 'walk_in',
    });
    setPrefillTime(time || '');
    setCreateModalOpen(true);
  };

  // Open detail modal
  const openDetail = (reservation: any) => {
    setSelectedReservation(reservation);
    setDetailModalOpen(true);
  };

  // Create reservation
  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    const payload: any = {
      reservation_date: form.reservation_date,
      start_time: form.start_time,
      guest_count: form.guest_count,
      customer_name: form.customer_name,
      customer_phone: form.customer_phone,
      source: form.source,
    };
    if (form.table_id) payload.table_id = form.table_id;
    if (form.notes) payload.notes = form.notes;

    const res = await createReservation(outletId, payload);
    if (res.success) {
      setCreateModalOpen(false);
      loadReservations();
    } else {
      alert(res.message);
    }
    setSaving(false);
  };

  // Status actions
  const handleAction = async (action: string) => {
    if (!selectedReservation) return;
    setSaving(true);
    let res;
    switch (action) {
      case 'confirm': res = await confirmReservation(selectedReservation.id); break;
      case 'seat': res = await seatReservation(selectedReservation.id); break;
      case 'complete': res = await completeReservation(selectedReservation.id); break;
      case 'cancel': res = await cancelReservation(selectedReservation.id); break;
      case 'no_show': res = await noShowReservation(selectedReservation.id); break;
      default: res = { success: false, message: 'Aksi tidak dikenal' };
    }
    if (res.success) {
      setDetailModalOpen(false);
      loadReservations();
    } else {
      alert(res.message);
    }
    setSaving(false);
  };

  // Get reservations at a specific hour
  const getReservationsAtHour = (hour: string) => {
    const h = parseInt(hour.split(':')[0]);
    return reservations.filter(r => {
      const rh = parseInt((r.start_time || '').split(':')[0]);
      return rh === h;
    });
  };

  // Find table name
  const getTableName = (tableId: string) => {
    const t = tables.find(t => t.id === tableId);
    return t ? t.name : '-';
  };

  if (loading) {
    return <div className="flex items-center justify-center h-64"><Loader2 className="w-6 h-6 animate-spin text-blue-500" /></div>;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Reservasi</h1>
          <p className="text-gray-500">Kelola reservasi pelanggan Anda.</p>
        </div>
        <div className="flex items-center gap-2">
          <Link
            href="/dashboard/reservasi/meja"
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
          >
            Kelola Meja
          </Link>
          <Link
            href="/dashboard/reservasi/settings"
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
          >
            Pengaturan
          </Link>
          <button
            onClick={() => openCreateModal()}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
          >
            <Plus className="w-4 h-4" />
            Tambah Reservasi
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {[
          { label: 'Total Hari Ini', value: stats.total, color: 'text-gray-900' },
          { label: 'Menunggu', value: stats.pending, color: 'text-yellow-600' },
          { label: 'Dikonfirmasi', value: stats.confirmed, color: 'text-green-600' },
          { label: 'Duduk', value: stats.seated, color: 'text-blue-600' },
        ].map(s => (
          <div key={s.label} className="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
            <p className="text-sm text-gray-500">{s.label}</p>
            <p className={`text-2xl font-bold ${s.color}`}>{s.value}</p>
          </div>
        ))}
      </div>

      {/* Date Navigation + Filter */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <button onClick={() => goToDate(-1)} className="p-2 text-gray-500 hover:bg-gray-100 rounded-lg">
            <ChevronLeft className="w-5 h-5" />
          </button>
          <button
            onClick={goToToday}
            className={`px-3 py-1.5 text-sm font-medium rounded-lg border transition-colors ${isToday ? 'bg-blue-50 text-blue-700 border-blue-200' : 'text-gray-700 border-gray-300 hover:bg-gray-50'}`}
          >
            Hari Ini
          </button>
          <button onClick={() => goToDate(1)} className="p-2 text-gray-500 hover:bg-gray-100 rounded-lg">
            <ChevronRight className="w-5 h-5" />
          </button>
          <span className="text-sm font-medium text-gray-700 ml-2">{formatDisplayDate(selectedDate)}</span>
        </div>
        <div className="flex items-center gap-2">
          {STATUS_FILTERS.map(f => (
            <button
              key={f.value}
              onClick={() => setStatusFilter(f.value)}
              className={`px-3 py-1.5 text-sm font-medium rounded-lg border transition-colors ${statusFilter === f.value ? 'bg-blue-50 text-blue-700 border-blue-200' : 'text-gray-600 border-gray-200 hover:bg-gray-50'}`}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {/* Timeline View */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <div className="divide-y divide-gray-100">
          {timeSlots.map(slot => {
            const slotReservations = getReservationsAtHour(slot);
            return (
              <div
                key={slot}
                className="flex min-h-[64px] hover:bg-gray-50/50 transition-colors cursor-pointer group"
                onClick={() => slotReservations.length === 0 && openCreateModal(slot)}
              >
                {/* Time label */}
                <div className="w-20 flex-shrink-0 flex items-start justify-end pr-4 pt-3">
                  <span className="text-sm font-medium text-gray-400">{slot}</span>
                </div>

                {/* Reservations in this slot */}
                <div className="flex-1 border-l border-gray-200 py-2 px-3">
                  {slotReservations.length > 0 ? (
                    <div className="flex flex-wrap gap-2">
                      {slotReservations.map(r => {
                        const cfg = STATUS_CONFIG[r.status] || STATUS_CONFIG.pending;
                        return (
                          <button
                            key={r.id}
                            onClick={(e) => { e.stopPropagation(); openDetail(r); }}
                            className={`flex items-center gap-2 px-3 py-2 rounded-lg border text-sm font-medium transition-shadow hover:shadow-md ${cfg.bg} ${cfg.border} ${cfg.color}`}
                          >
                            <span className="font-semibold">{r.customer_name}</span>
                            <span className="flex items-center gap-1 text-xs opacity-75">
                              <Users className="w-3 h-3" />{r.guest_count}
                            </span>
                            <span className="flex items-center gap-1 text-xs opacity-75">
                              <Clock className="w-3 h-3" />{(r.start_time || '').slice(0, 5)}
                            </span>
                            {r.table_id && (
                              <span className="text-xs opacity-75">
                                {getTableName(r.table_id)}
                              </span>
                            )}
                          </button>
                        );
                      })}
                    </div>
                  ) : (
                    <div className="flex items-center h-full min-h-[40px]">
                      <span className="text-xs text-gray-300 group-hover:text-gray-400 transition-colors">
                        + Klik untuk tambah reservasi
                      </span>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Create Reservation Modal */}
      {createModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-gray-900/50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md overflow-hidden">
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
              <h3 className="text-lg font-bold text-gray-900">Tambah Reservasi</h3>
              <button onClick={() => setCreateModalOpen(false)} className="text-gray-400 hover:text-gray-500">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreate} className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Tanggal</label>
                  <input
                    type="date"
                    required
                    value={form.reservation_date}
                    onChange={e => setForm({ ...form, reservation_date: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-sm"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Jam</label>
                  <input
                    type="time"
                    required
                    value={form.start_time}
                    onChange={e => setForm({ ...form, start_time: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-sm"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Nama Pelanggan</label>
                <input
                  type="text"
                  required
                  value={form.customer_name}
                  onChange={e => setForm({ ...form, customer_name: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Nomor Telepon</label>
                <input
                  type="tel"
                  required
                  placeholder="628..."
                  value={form.customer_phone}
                  onChange={e => setForm({ ...form, customer_phone: e.target.value.replace(/\D/g, '') })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Jumlah Tamu</label>
                  <input
                    type="number"
                    min={1}
                    required
                    value={form.guest_count}
                    onChange={e => setForm({ ...form, guest_count: parseInt(e.target.value) || 1 })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Meja (opsional)</label>
                  <select
                    value={form.table_id}
                    onChange={e => setForm({ ...form, table_id: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-sm"
                  >
                    <option value="">Belum dipilih</option>
                    {tables.filter(t => t.is_active !== false).map(t => (
                      <option key={t.id} value={t.id}>{t.name} (Kapasitas {t.capacity})</option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Catatan (opsional)</label>
                <textarea
                  rows={2}
                  value={form.notes}
                  onChange={e => setForm({ ...form, notes: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none resize-none text-sm"
                />
              </div>

              <div className="pt-4 flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setCreateModalOpen(false)}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
                >
                  Batal
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="flex items-center justify-center px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50"
                >
                  {saving ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
                  Simpan
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Reservation Detail Modal */}
      {detailModalOpen && selectedReservation && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-gray-900/50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md overflow-hidden">
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
              <h3 className="text-lg font-bold text-gray-900">Detail Reservasi</h3>
              <button onClick={() => setDetailModalOpen(false)} className="text-gray-400 hover:text-gray-500">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 space-y-4">
              {/* Status badge */}
              {(() => {
                const cfg = STATUS_CONFIG[selectedReservation.status] || STATUS_CONFIG.pending;
                return (
                  <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${cfg.bg} ${cfg.color} ${cfg.border} border`}>
                    {cfg.label}
                  </span>
                );
              })()}

              {/* Details */}
              <div className="space-y-3">
                <div className="flex items-center gap-3">
                  <Users className="w-4 h-4 text-gray-400" />
                  <div>
                    <p className="text-sm font-medium text-gray-900">{selectedReservation.customer_name}</p>
                    <p className="text-xs text-gray-500">{selectedReservation.guest_count} tamu</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <Phone className="w-4 h-4 text-gray-400" />
                  <p className="text-sm text-gray-700">{selectedReservation.customer_phone}</p>
                </div>
                <div className="flex items-center gap-3">
                  <Clock className="w-4 h-4 text-gray-400" />
                  <p className="text-sm text-gray-700">
                    {selectedReservation.reservation_date} &middot; {(selectedReservation.start_time || '').slice(0, 5)}
                  </p>
                </div>
                {selectedReservation.table_id && (
                  <div className="flex items-center gap-3">
                    <Armchair className="w-4 h-4 text-gray-400" />
                    <p className="text-sm text-gray-700">Meja: {getTableName(selectedReservation.table_id)}</p>
                  </div>
                )}
                {selectedReservation.notes && (
                  <div className="flex items-start gap-3">
                    <MessageSquare className="w-4 h-4 text-gray-400 mt-0.5" />
                    <p className="text-sm text-gray-700">{selectedReservation.notes}</p>
                  </div>
                )}
              </div>

              {/* Action buttons based on status */}
              <div className="pt-4 border-t border-gray-200 flex flex-wrap gap-2">
                {selectedReservation.status === 'pending' && (
                  <>
                    <button
                      onClick={() => handleAction('confirm')}
                      disabled={saving}
                      className="flex items-center gap-1.5 px-3 py-2 text-sm font-medium text-green-700 bg-green-50 border border-green-200 rounded-lg hover:bg-green-100 disabled:opacity-50"
                    >
                      {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
                      Konfirmasi
                    </button>
                    <button
                      onClick={() => handleAction('cancel')}
                      disabled={saving}
                      className="flex items-center gap-1.5 px-3 py-2 text-sm font-medium text-red-700 bg-red-50 border border-red-200 rounded-lg hover:bg-red-100 disabled:opacity-50"
                    >
                      {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <XCircle className="w-4 h-4" />}
                      Batalkan
                    </button>
                  </>
                )}
                {selectedReservation.status === 'confirmed' && (
                  <>
                    <button
                      onClick={() => handleAction('seat')}
                      disabled={saving}
                      className="flex items-center gap-1.5 px-3 py-2 text-sm font-medium text-blue-700 bg-blue-50 border border-blue-200 rounded-lg hover:bg-blue-100 disabled:opacity-50"
                    >
                      {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Armchair className="w-4 h-4" />}
                      Dudukkan
                    </button>
                    <button
                      onClick={() => handleAction('no_show')}
                      disabled={saving}
                      className="flex items-center gap-1.5 px-3 py-2 text-sm font-medium text-orange-700 bg-orange-50 border border-orange-200 rounded-lg hover:bg-orange-100 disabled:opacity-50"
                    >
                      {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <UserX className="w-4 h-4" />}
                      Tidak Hadir
                    </button>
                    <button
                      onClick={() => handleAction('cancel')}
                      disabled={saving}
                      className="flex items-center gap-1.5 px-3 py-2 text-sm font-medium text-red-700 bg-red-50 border border-red-200 rounded-lg hover:bg-red-100 disabled:opacity-50"
                    >
                      {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <XCircle className="w-4 h-4" />}
                      Batalkan
                    </button>
                  </>
                )}
                {selectedReservation.status === 'seated' && (
                  <button
                    onClick={() => handleAction('complete')}
                    disabled={saving}
                    className="flex items-center gap-1.5 px-3 py-2 text-sm font-medium text-gray-700 bg-gray-100 border border-gray-300 rounded-lg hover:bg-gray-200 disabled:opacity-50"
                  >
                    {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <CalendarCheck className="w-4 h-4" />}
                    Selesai
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
