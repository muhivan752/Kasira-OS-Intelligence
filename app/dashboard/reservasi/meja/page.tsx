'use client';

import { useState, useEffect } from 'react';
import { getOutlets, getTables, createTable, updateTable, deleteTable } from '@/app/actions/api';
import { Loader2, Plus, X, Edit2, Trash2, ArrowLeft } from 'lucide-react';
import Link from 'next/link';
import { useProGuard } from '@/app/hooks/use-pro-guard';

export default function MejaPage() {
  const allowed = useProGuard();
  const [loading, setLoading] = useState(true);
  const [tables, setTables] = useState<any[]>([]);
  const [outletId, setOutletId] = useState('');

  // Modal state
  const [modalOpen, setModalOpen] = useState(false);
  const [editingTable, setEditingTable] = useState<any>(null);
  const [saving, setSaving] = useState(false);

  const [form, setForm] = useState({
    name: '',
    capacity: 4,
    floor_section: '',
    is_active: true,
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
        const data = await getTables(id);
        setTables(data || []);
      }
    } catch (error) {
      console.error('Failed to load tables', error);
    } finally {
      setLoading(false);
    }
  }

  // Group tables by floor_section
  const grouped = tables.reduce((acc: Record<string, any[]>, table) => {
    const section = table.floor_section || 'Umum';
    if (!acc[section]) acc[section] = [];
    acc[section].push(table);
    return acc;
  }, {});

  const openCreateModal = () => {
    setEditingTable(null);
    setForm({ name: '', capacity: 4, floor_section: '', is_active: true });
    setModalOpen(true);
  };

  const openEditModal = (table: any) => {
    setEditingTable(table);
    setForm({
      name: table.name || '',
      capacity: table.capacity || 4,
      floor_section: table.floor_section || '',
      is_active: table.is_active !== false,
    });
    setModalOpen(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);

    const payload: any = {
      name: form.name,
      capacity: form.capacity,
      is_active: form.is_active,
    };
    if (form.floor_section) payload.floor_section = form.floor_section;

    let res;
    if (editingTable) {
      res = await updateTable(editingTable.id, payload);
    } else {
      res = await createTable(outletId, payload);
    }

    if (res.success) {
      setModalOpen(false);
      loadData();
    } else {
      alert(res.message);
    }
    setSaving(false);
  };

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`Hapus meja "${name}"? Tindakan ini tidak bisa dibatalkan.`)) return;
    const success = await deleteTable(id);
    if (success) {
      loadData();
    } else {
      alert('Gagal menghapus meja');
    }
  };

  const handleToggleActive = async (table: any) => {
    const newStatus = !table.is_active;
    // Optimistic update
    setTables(tables.map(t => t.id === table.id ? { ...t, is_active: newStatus } : t));
    const res = await updateTable(table.id, { is_active: newStatus });
    if (!res.success) {
      setTables(tables.map(t => t.id === table.id ? { ...t, is_active: table.is_active } : t));
      alert('Gagal mengubah status meja');
    }
  };

  if (!allowed || loading) {
    return <div className="flex items-center justify-center h-64"><Loader2 className="w-6 h-6 animate-spin text-blue-500" /></div>;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <Link href="/dashboard/reservasi" className="p-2 text-gray-500 hover:bg-gray-100 rounded-lg">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Kelola Meja</h1>
            <p className="text-gray-500">Tambah dan atur meja untuk reservasi.</p>
          </div>
        </div>
        <button
          onClick={openCreateModal}
          className="flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
        >
          <Plus className="w-4 h-4" />
          Tambah Meja
        </button>
      </div>

      {/* Tables grouped by section */}
      {Object.keys(grouped).length > 0 ? (
        Object.entries(grouped).map(([section, sectionTables]) => (
          <div key={section}>
            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-3">{section}</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {sectionTables.map((table: any) => (
                <div
                  key={table.id}
                  className={`bg-white rounded-xl border shadow-sm p-4 flex items-center justify-between ${table.is_active !== false ? 'border-gray-200' : 'border-gray-200 opacity-60'}`}
                >
                  <div className="flex items-center gap-3">
                    <div className={`w-10 h-10 rounded-lg flex items-center justify-center text-sm font-bold ${table.is_active !== false ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-400'}`}>
                      {table.name?.charAt(0) || '?'}
                    </div>
                    <div>
                      <p className="text-sm font-medium text-gray-900">{table.name}</p>
                      <p className="text-xs text-gray-500">Kapasitas: {table.capacity} orang</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-1">
                    {/* Toggle active */}
                    <button
                      onClick={() => handleToggleActive(table)}
                      className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors focus:outline-none ${table.is_active !== false ? 'bg-blue-600' : 'bg-gray-200'}`}
                    >
                      <span className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform ${table.is_active !== false ? 'translate-x-4.5' : 'translate-x-0.5'}`} />
                    </button>
                    <button
                      onClick={() => openEditModal(table)}
                      className="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                    >
                      <Edit2 className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => handleDelete(table.id, table.name)}
                      className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-8 text-center">
          <p className="text-gray-500">Belum ada meja. Klik &quot;Tambah Meja&quot; untuk mulai.</p>
        </div>
      )}

      {/* Create/Edit Modal */}
      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-gray-900/50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md overflow-hidden">
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
              <h3 className="text-lg font-bold text-gray-900">{editingTable ? 'Edit Meja' : 'Tambah Meja Baru'}</h3>
              <button onClick={() => setModalOpen(false)} className="text-gray-400 hover:text-gray-500">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Nama Meja</label>
                <input
                  type="text"
                  required
                  placeholder="Contoh: Meja 1, VIP-A"
                  value={form.name}
                  onChange={e => setForm({ ...form, name: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Kapasitas (orang)</label>
                <input
                  type="number"
                  min={1}
                  required
                  value={form.capacity}
                  onChange={e => setForm({ ...form, capacity: parseInt(e.target.value) || 1 })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Bagian / Lantai (opsional)</label>
                <input
                  type="text"
                  placeholder="Contoh: Lantai 1, Outdoor, VIP"
                  value={form.floor_section}
                  onChange={e => setForm({ ...form, floor_section: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                />
              </div>

              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-medium text-gray-900">Aktif</h3>
                  <p className="text-xs text-gray-500">Meja bisa dipilih untuk reservasi.</p>
                </div>
                <button
                  type="button"
                  onClick={() => setForm({ ...form, is_active: !form.is_active })}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${form.is_active ? 'bg-blue-600' : 'bg-gray-200'}`}
                >
                  <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${form.is_active ? 'translate-x-6' : 'translate-x-1'}`} />
                </button>
              </div>

              <div className="pt-4 flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setModalOpen(false)}
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
                  {editingTable ? 'Simpan' : 'Tambah'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
