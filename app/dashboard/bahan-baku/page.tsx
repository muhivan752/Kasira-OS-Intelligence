'use client';

import { useEffect, useState } from 'react';
import { Package, Plus, RefreshCw, Pencil, Trash2, AlertTriangle } from 'lucide-react';
import { getIngredients, createIngredient, updateIngredient, deleteIngredient, restockIngredient, getOutlets, getCurrentUser } from '@/app/actions/api';
import { useProGuard } from '@/app/hooks/use-pro-guard';

interface UsedIn {
  product_name: string;
  qty_per_serving: number;
  unit: string;
}

interface Ingredient {
  id: string;
  brand_id: string;
  name: string;
  tracking_mode: string;
  base_unit: string;
  unit_type: string;
  buy_price: number;
  buy_qty: number;
  cost_per_base_unit: number;
  ingredient_type: string;
  overhead_cost_per_day?: number;
  row_version: number;
  current_stock?: number;
  min_stock?: number;
  used_in?: UsedIn[];
  created_at: string;
}

const UNIT_TYPES = [
  { value: 'WEIGHT', label: 'Berat (gram, kg)' },
  { value: 'VOLUME', label: 'Volume (ml, liter)' },
  { value: 'COUNT', label: 'Satuan (pcs, bungkus)' },
  { value: 'CUSTOM', label: 'Custom' },
];

export default function BahanBakuPage() {
  const allowed = useProGuard();
  const [ingredients, setIngredients] = useState<Ingredient[]>([]);
  const [loading, setLoading] = useState(true);
  const [brandId, setBrandId] = useState('');
  const [outletId, setOutletId] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [showRestockModal, setShowRestockModal] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [restockTarget, setRestockTarget] = useState<Ingredient | null>(null);
  const [error, setError] = useState('');
  const [form, setForm] = useState({
    name: '', base_unit: '', unit_type: 'WEIGHT', buy_price: '', buy_qty: '',
    ingredient_type: 'recipe', overhead_cost_per_day: '', row_version: 0,
  });
  const [restockForm, setRestockForm] = useState({ quantity: '', notes: '' });

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    setLoading(true);
    try {
      const outlets = await getOutlets();
      if (outlets?.length > 0) {
        setOutletId(outlets[0].id);
        setBrandId(outlets[0].brand_id);
        const data = await getIngredients(outlets[0].brand_id, outlets[0].id);
        setIngredients(data || []);
      }
    } catch { /* */ }
    setLoading(false);
  }

  async function handleSave() {
    setError('');
    try {
      if (editingId) {
        await updateIngredient(editingId, {
          name: form.name, base_unit: form.base_unit, unit_type: form.unit_type,
          buy_price: parseFloat(form.buy_price) || 0,
          buy_qty: parseFloat(form.buy_qty) || 1,
          ingredient_type: form.ingredient_type,
          overhead_cost_per_day: form.overhead_cost_per_day ? parseFloat(form.overhead_cost_per_day) : null,
          row_version: form.row_version,
        });
      } else {
        await createIngredient({
          brand_id: brandId, name: form.name, base_unit: form.base_unit,
          unit_type: form.unit_type, tracking_mode: 'simple',
          buy_price: parseFloat(form.buy_price) || 0,
          buy_qty: parseFloat(form.buy_qty) || 1,
          ingredient_type: form.ingredient_type,
          overhead_cost_per_day: form.overhead_cost_per_day ? parseFloat(form.overhead_cost_per_day) : null,
        });
      }
      setShowModal(false);
      resetForm();
      await loadData();
    } catch (e: any) {
      setError(e.message);
    }
  }

  async function handleDelete(id: string) {
    if (!confirm('Hapus bahan baku ini?')) return;
    await deleteIngredient(id);
    await loadData();
  }

  async function handleRestock() {
    if (!restockTarget) return;
    setError('');
    try {
      await restockIngredient(restockTarget.id, {
        outlet_id: outletId,
        quantity: parseFloat(restockForm.quantity),
        notes: restockForm.notes || undefined,
      });
      setShowRestockModal(false);
      setRestockForm({ quantity: '', notes: '' });
      await loadData();
    } catch (e: any) {
      setError(e.message);
    }
  }

  function openEdit(ing: Ingredient) {
    setEditingId(ing.id);
    setForm({
      name: ing.name, base_unit: ing.base_unit, unit_type: ing.unit_type,
      buy_price: String(ing.buy_price || 0),
      buy_qty: String(ing.buy_qty || 1),
      ingredient_type: ing.ingredient_type,
      overhead_cost_per_day: ing.overhead_cost_per_day ? String(ing.overhead_cost_per_day) : '',
      row_version: ing.row_version,
    });
    setShowModal(true);
  }

  function openRestock(ing: Ingredient) {
    setRestockTarget(ing);
    setRestockForm({ quantity: '', notes: '' });
    setShowRestockModal(true);
  }

  function resetForm() {
    setEditingId(null);
    setForm({ name: '', base_unit: '', unit_type: 'WEIGHT', buy_price: '', buy_qty: '', ingredient_type: 'recipe', overhead_cost_per_day: '', row_version: 0 });
    setError('');
  }

  const formatCurrency = (n: number) => new Intl.NumberFormat('id-ID', { style: 'currency', currency: 'IDR', maximumFractionDigits: 0 }).format(n);

  if (!allowed || loading) return <div className="flex items-center justify-center h-64">Memuat...</div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Bahan Baku</h1>
          <p className="text-gray-500">Kelola ingredient dan stok bahan baku outlet Anda</p>
        </div>
        <button
          onClick={() => { resetForm(); setShowModal(true); }}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
        >
          <Plus className="w-4 h-4" /> Tambah Bahan
        </button>
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="text-left px-4 sm:px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Nama</th>
              <th className="hidden sm:table-cell text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Unit</th>
              <th className="hidden lg:table-cell text-right px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Harga Beli</th>
              <th className="text-right px-4 sm:px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Cost/Unit</th>
              <th className="text-right px-4 sm:px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Stok</th>
              <th className="hidden md:table-cell text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Tipe</th>
              <th className="text-right px-4 sm:px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Aksi</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {ingredients.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-6 py-12 text-center text-gray-400">
                  <Package className="w-10 h-10 mx-auto mb-2 text-gray-300" />
                  Belum ada bahan baku. Klik "Tambah Bahan" untuk memulai.
                </td>
              </tr>
            ) : (
              ingredients.map((ing) => {
                const isLow = ing.current_stock !== undefined && ing.min_stock !== undefined && ing.current_stock <= ing.min_stock;
                return (
                  <tr key={ing.id} className="hover:bg-gray-50">
                    <td className="px-4 sm:px-6 py-4">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-gray-900">{ing.name}</span>
                        {isLow && <AlertTriangle className="w-4 h-4 text-amber-500" />}
                      </div>
                      <span className="sm:hidden text-xs text-gray-400">{ing.base_unit}</span>
                      {ing.used_in && ing.used_in.length > 0 ? (
                        <p className="text-xs text-gray-400 mt-0.5 truncate max-w-[250px]">
                          Dipakai: {ing.used_in.map(u => `${u.product_name} (${u.qty_per_serving}${u.unit})`).join(', ')}
                        </p>
                      ) : (
                        <p className="text-xs text-amber-500 mt-0.5">Belum dipakai di menu manapun</p>
                      )}
                    </td>
                    <td className="hidden sm:table-cell px-6 py-4 text-gray-600">{ing.base_unit}</td>
                    <td className="hidden lg:table-cell px-6 py-4 text-right text-gray-600">
                      {ing.buy_price ? (
                        <span>{formatCurrency(ing.buy_price)} / {ing.buy_qty} {ing.base_unit}</span>
                      ) : '-'}
                    </td>
                    <td className="px-4 sm:px-6 py-4 text-right text-gray-900 text-sm">{formatCurrency(ing.cost_per_base_unit)}/{ing.base_unit}</td>
                    <td className="px-4 sm:px-6 py-4 text-right">
                      <span className={`font-semibold text-sm ${isLow ? 'text-red-600' : 'text-gray-900'}`}>
                        {ing.current_stock !== undefined ? `${ing.current_stock}` : '-'}
                      </span>
                    </td>
                    <td className="hidden md:table-cell px-6 py-4">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                        ing.ingredient_type === 'recipe' ? 'bg-blue-50 text-blue-700' : 'bg-gray-100 text-gray-600'
                      }`}>
                        {ing.ingredient_type === 'recipe' ? 'Resep' : 'Overhead'}
                      </span>
                    </td>
                    <td className="px-4 sm:px-6 py-4">
                      <div className="flex items-center justify-end gap-1">
                        <button onClick={() => openRestock(ing)} className="p-2 text-green-600 hover:bg-green-50 rounded-lg" title="Restock">
                          <RefreshCw className="w-4 h-4" />
                        </button>
                        <button onClick={() => openEdit(ing)} className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg" title="Edit">
                          <Pencil className="w-4 h-4" />
                        </button>
                        <button onClick={() => handleDelete(ing.id)} className="p-2 text-red-600 hover:bg-red-50 rounded-lg" title="Hapus">
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Create/Edit Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="bg-white rounded-2xl w-full max-w-lg p-6 space-y-4 max-h-[90vh] overflow-y-auto">
            <h2 className="text-lg font-bold">{editingId ? 'Edit Bahan Baku' : 'Tambah Bahan Baku'}</h2>
            {error && <p className="text-red-600 text-sm">{error}</p>}
            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Nama *</label>
                <input value={form.name} onChange={e => setForm({ ...form, name: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg" placeholder="Kopi Arabica Bubuk" />
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Satuan *</label>
                  <input value={form.base_unit} onChange={e => setForm({ ...form, base_unit: e.target.value })}
                    className="w-full px-3 py-2 border rounded-lg" placeholder="gram" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Tipe Satuan</label>
                  <select value={form.unit_type} onChange={e => setForm({ ...form, unit_type: e.target.value })}
                    className="w-full px-3 py-2 border rounded-lg">
                    {UNIT_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
                  </select>
                </div>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Harga Beli (Rp) *</label>
                  <input type="number" value={form.buy_price} onChange={e => setForm({ ...form, buy_price: e.target.value })}
                    className="w-full px-3 py-2 border rounded-lg" placeholder="14000" />
                  <p className="text-xs text-gray-400 mt-1">Contoh: Rp14.000</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Isi per Beli ({form.base_unit || 'unit'}) *</label>
                  <input type="number" step="any" value={form.buy_qty} onChange={e => setForm({ ...form, buy_qty: e.target.value })}
                    className="w-full px-3 py-2 border rounded-lg" placeholder="1000" />
                  <p className="text-xs text-gray-400 mt-1">Contoh: 1000 {form.base_unit || 'gram'}</p>
                </div>
              </div>
              {(parseFloat(form.buy_price) > 0 && parseFloat(form.buy_qty) > 0) && (
                <div className="bg-blue-50 rounded-lg px-4 py-3">
                  <p className="text-sm text-blue-800 font-medium">
                    Cost per {form.base_unit || 'unit'}: {new Intl.NumberFormat('id-ID', { style: 'currency', currency: 'IDR', maximumFractionDigits: 2 }).format(parseFloat(form.buy_price) / parseFloat(form.buy_qty))}
                  </p>
                </div>
              )}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Tipe</label>
                <select value={form.ingredient_type} onChange={e => setForm({ ...form, ingredient_type: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg">
                  <option value="recipe">Resep (bahan langsung)</option>
                  <option value="overhead">Overhead (biaya harian)</option>
                </select>
              </div>
              {form.ingredient_type === 'overhead' && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Biaya Overhead/Hari (Rp)</label>
                  <input type="number" value={form.overhead_cost_per_day} onChange={e => setForm({ ...form, overhead_cost_per_day: e.target.value })}
                    className="w-full px-3 py-2 border rounded-lg" placeholder="50000" />
                </div>
              )}
            </div>
            <div className="flex justify-end gap-3 pt-2">
              <button onClick={() => { setShowModal(false); resetForm(); }} className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg">Batal</button>
              <button onClick={handleSave} disabled={!form.name || !form.base_unit}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50">
                {editingId ? 'Simpan' : 'Tambah'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Restock Modal */}
      {showRestockModal && restockTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-white rounded-2xl w-full max-w-md p-6 space-y-4">
            <h2 className="text-lg font-bold">Restock: {restockTarget.name}</h2>
            <p className="text-sm text-gray-500">
              Stok saat ini: {restockTarget.current_stock ?? 0} {restockTarget.base_unit}
            </p>
            {error && <p className="text-red-600 text-sm">{error}</p>}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Jumlah Restock ({restockTarget.base_unit}) *</label>
              <input type="number" value={restockForm.quantity} onChange={e => setRestockForm({ ...restockForm, quantity: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg" placeholder="1000" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Catatan</label>
              <input value={restockForm.notes} onChange={e => setRestockForm({ ...restockForm, notes: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg" placeholder="Beli dari supplier X" />
            </div>
            <div className="flex justify-end gap-3 pt-2">
              <button onClick={() => setShowRestockModal(false)} className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg">Batal</button>
              <button onClick={handleRestock} disabled={!restockForm.quantity || parseFloat(restockForm.quantity) <= 0}
                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50">
                Restock
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
