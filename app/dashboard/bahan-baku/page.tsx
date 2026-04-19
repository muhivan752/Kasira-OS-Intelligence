'use client';

import { useEffect, useState } from 'react';
import { Package, Plus, RefreshCw, Pencil, Trash2, AlertTriangle, Droplet, Scale, Boxes, ArrowLeft, CheckCircle2, Sparkles } from 'lucide-react';
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

const UNIT_OPTIONS = [
  { value: 'gram', label: 'Gram (g)', type: 'WEIGHT', example: 'Kopi, Gula, Tepung' },
  { value: 'kg', label: 'Kilogram (kg)', type: 'WEIGHT', example: 'Beras, Ayam, Sayur' },
  { value: 'ml', label: 'Mililiter (ml)', type: 'VOLUME', example: 'Susu, Kecap, Minyak' },
  { value: 'liter', label: 'Liter (L)', type: 'VOLUME', example: 'Air, Minyak Goreng' },
  { value: 'pcs', label: 'Butir / Pcs', type: 'COUNT', example: 'Telur, Teh Celup, Roti' },
  { value: 'bungkus', label: 'Bungkus', type: 'COUNT', example: 'Bumbu, Mie Instan' },
];

type UnitType = 'WEIGHT' | 'VOLUME' | 'COUNT';

const UNIT_CATEGORIES: { id: UnitType; label: string; desc: string; icon: any; units: { value: string; label: string }[] }[] = [
  {
    id: 'VOLUME',
    label: 'Cairan',
    desc: 'susu, sirup, minyak, air',
    icon: Droplet,
    units: [
      { value: 'ml', label: 'ml' },
      { value: 'liter', label: 'Liter' },
    ],
  },
  {
    id: 'WEIGHT',
    label: 'Ditimbang',
    desc: 'kopi, gula, tepung, coklat',
    icon: Scale,
    units: [
      { value: 'gram', label: 'gram' },
      { value: 'kg', label: 'kg' },
    ],
  },
  {
    id: 'COUNT',
    label: 'Hitungan',
    desc: 'telur, roti, teh celup',
    icon: Boxes,
    units: [
      { value: 'pcs', label: 'pcs/butir' },
      { value: 'bungkus', label: 'bungkus' },
    ],
  },
];

interface Preset {
  id: string;
  name: string;
  emoji: string;
  base_unit: string;
  unit_type: UnitType;
  hint?: string;
  buy_price_hint?: number;
  buy_qty_hint?: number;
}

const PRESETS: Preset[] = [
  { id: 'kopi', name: 'Kopi', emoji: '☕', base_unit: 'gram', unit_type: 'WEIGHT', hint: '1 kg ~Rp120rb', buy_price_hint: 120000, buy_qty_hint: 1000 },
  { id: 'susu-uht', name: 'Susu UHT', emoji: '🥛', base_unit: 'ml', unit_type: 'VOLUME', hint: '1 liter ~Rp18rb', buy_price_hint: 18000, buy_qty_hint: 1000 },
  { id: 'gula', name: 'Gula Pasir', emoji: '🍯', base_unit: 'gram', unit_type: 'WEIGHT', hint: '1 kg ~Rp14rb', buy_price_hint: 14000, buy_qty_hint: 1000 },
  { id: 'teh', name: 'Teh Celup', emoji: '🫖', base_unit: 'pcs', unit_type: 'COUNT', hint: '1 pak 25pcs ~Rp12rb', buy_price_hint: 12000, buy_qty_hint: 25 },
  { id: 'es', name: 'Es Batu', emoji: '🧊', base_unit: 'kg', unit_type: 'WEIGHT', hint: '1 kg ~Rp5rb', buy_price_hint: 5000, buy_qty_hint: 1 },
  { id: 'sirup', name: 'Sirup', emoji: '🍹', base_unit: 'ml', unit_type: 'VOLUME', hint: '1 botol 1L ~Rp35rb', buy_price_hint: 35000, buy_qty_hint: 1000 },
  { id: 'telur', name: 'Telur', emoji: '🥚', base_unit: 'pcs', unit_type: 'COUNT', hint: '1 tray 30pcs ~Rp55rb', buy_price_hint: 55000, buy_qty_hint: 30 },
  { id: 'tepung', name: 'Tepung Terigu', emoji: '🌾', base_unit: 'gram', unit_type: 'WEIGHT', hint: '1 kg ~Rp13rb', buy_price_hint: 13000, buy_qty_hint: 1000 },
  { id: 'coklat', name: 'Bubuk Coklat', emoji: '🍫', base_unit: 'gram', unit_type: 'WEIGHT', hint: '500g ~Rp45rb', buy_price_hint: 45000, buy_qty_hint: 500 },
  { id: 'keju', name: 'Keju', emoji: '🧀', base_unit: 'gram', unit_type: 'WEIGHT', hint: '170g ~Rp30rb', buy_price_hint: 30000, buy_qty_hint: 170 },
  { id: 'butter', name: 'Butter', emoji: '🧈', base_unit: 'gram', unit_type: 'WEIGHT', hint: '500g ~Rp35rb', buy_price_hint: 35000, buy_qty_hint: 500 },
  { id: 'minyak', name: 'Minyak Goreng', emoji: '🫒', base_unit: 'ml', unit_type: 'VOLUME', hint: '1 liter ~Rp25rb', buy_price_hint: 25000, buy_qty_hint: 1000 },
  { id: 'roti', name: 'Roti Tawar', emoji: '🍞', base_unit: 'pcs', unit_type: 'COUNT', hint: '1 pak 10pcs ~Rp15rb', buy_price_hint: 15000, buy_qty_hint: 10 },
  { id: 'air', name: 'Air Mineral', emoji: '💧', base_unit: 'ml', unit_type: 'VOLUME', hint: '600ml ~Rp3rb', buy_price_hint: 3000, buy_qty_hint: 600 },
];

export default function BahanBakuPage() {
  const allowed = useProGuard('Bahan Baku & HPP');
  const [ingredients, setIngredients] = useState<Ingredient[]>([]);
  const [loading, setLoading] = useState(true);
  const [brandId, setBrandId] = useState('');
  const [outletId, setOutletId] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [showRestockModal, setShowRestockModal] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [restockTarget, setRestockTarget] = useState<Ingredient | null>(null);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  const [modalStep, setModalStep] = useState<'preset' | 'form'>('preset');
  const [form, setForm] = useState({
    name: '', base_unit: '', unit_type: 'WEIGHT', buy_price: '', buy_qty: '',
    ingredient_type: 'recipe', overhead_cost_per_day: '', row_version: 0,
    initial_stock: '',
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
    if (!form.name.trim()) {
      setError('Nama bahan harus diisi');
      return;
    }
    if (!form.base_unit) {
      setError('Pilih bentuk & satuan bahan');
      return;
    }
    if (form.ingredient_type !== 'overhead') {
      if (!form.buy_price || parseFloat(form.buy_price) <= 0) {
        setError('Harga beli harus diisi dan lebih dari 0');
        return;
      }
      if (!form.buy_qty || parseFloat(form.buy_qty) <= 0) {
        setError('Isi per beli harus diisi dan lebih dari 0');
        return;
      }
    }
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
        const created = await createIngredient({
          brand_id: brandId, name: form.name, base_unit: form.base_unit,
          unit_type: form.unit_type, tracking_mode: 'simple',
          buy_price: parseFloat(form.buy_price) || 0,
          buy_qty: parseFloat(form.buy_qty) || 1,
          ingredient_type: form.ingredient_type,
          overhead_cost_per_day: form.overhead_cost_per_day ? parseFloat(form.overhead_cost_per_day) : null,
        });
        // Auto-restock with initial stock if provided
        const initQty = parseFloat(form.initial_stock);
        if (created?.id && !isNaN(initQty) && initQty > 0 && outletId) {
          try {
            await restockIngredient(created.id, {
              outlet_id: outletId,
              quantity: initQty,
              notes: 'Stok awal',
            });
          } catch { /* non-fatal */ }
        }
        setSuccessMsg(`✅ ${form.name} berhasil ditambah${initQty > 0 ? ` (stok: ${initQty} ${form.base_unit})` : ''}`);
        setTimeout(() => setSuccessMsg(''), 4000);
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
      buy_price: ing.buy_price > 0 ? String(ing.buy_price) : '',
      buy_qty: ing.buy_qty > 0 ? String(ing.buy_qty) : '',
      ingredient_type: ing.ingredient_type,
      overhead_cost_per_day: ing.overhead_cost_per_day ? String(ing.overhead_cost_per_day) : '',
      row_version: ing.row_version,
      initial_stock: '',
    });
    setModalStep('form');
    setShowModal(true);
  }

  function openCreate(type: 'recipe' | 'overhead' = 'recipe') {
    resetForm();
    setForm(f => ({ ...f, ingredient_type: type }));
    setModalStep(type === 'recipe' ? 'preset' : 'form');
    setShowModal(true);
  }

  function pickPreset(preset: Preset) {
    setForm(f => ({
      ...f,
      name: preset.name,
      base_unit: preset.base_unit,
      unit_type: preset.unit_type,
      buy_price: preset.buy_price_hint ? String(preset.buy_price_hint) : '',
      buy_qty: preset.buy_qty_hint ? String(preset.buy_qty_hint) : '',
      ingredient_type: 'recipe',
    }));
    setModalStep('form');
  }

  function pickCustom() {
    setModalStep('form');
  }

  function openRestock(ing: Ingredient) {
    setRestockTarget(ing);
    setRestockForm({ quantity: '', notes: '' });
    setShowRestockModal(true);
  }

  function resetForm() {
    setEditingId(null);
    setForm({ name: '', base_unit: '', unit_type: 'WEIGHT', buy_price: '', buy_qty: '', ingredient_type: 'recipe', overhead_cost_per_day: '', row_version: 0, initial_stock: '' });
    setError('');
    setModalStep('preset');
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
          onClick={() => openCreate('recipe')}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
        >
          <Plus className="w-4 h-4" /> Tambah Bahan
        </button>
      </div>

      {/* Success toast */}
      {successMsg && (
        <div className="bg-green-50 border border-green-200 rounded-lg px-4 py-3 text-sm text-green-800 flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 shrink-0" />
          <span>{successMsg}</span>
        </div>
      )}

      {/* Summary */}
      {ingredients.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          <div className="bg-white p-4 rounded-xl border border-gray-200">
            <p className="text-xs text-gray-500">Total Bahan</p>
            <p className="text-xl font-bold mt-1">{ingredients.length}</p>
          </div>
          <div className="bg-white p-4 rounded-xl border border-gray-200">
            <p className="text-xs text-gray-500">Terhubung ke Menu</p>
            <p className="text-xl font-bold text-green-600 mt-1">{ingredients.filter(i => i.used_in && i.used_in.length > 0).length}</p>
          </div>
          <div className="bg-white p-4 rounded-xl border border-gray-200">
            <p className="text-xs text-gray-500">Belum Terhubung</p>
            <p className="text-xl font-bold text-amber-500 mt-1">{ingredients.filter(i => !i.used_in || i.used_in.length === 0).length}</p>
          </div>
        </div>
      )}

      {/* Ingredient Cards */}
      {ingredients.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-200 p-6 sm:p-8">
          <div className="max-w-lg mx-auto">
            <div className="text-center mb-6">
              <Package className="w-12 h-12 mx-auto mb-3 text-blue-400" />
              <h2 className="text-lg font-bold text-gray-900">Mulai Kelola Bahan Baku</h2>
              <p className="text-sm text-gray-500 mt-1">Dengan bahan baku, sistem otomatis hitung HPP dan kurangi stok saat ada pesanan.</p>
            </div>
            <div className="space-y-4 mb-6">
              <div className="flex gap-3 items-start">
                <div className="w-7 h-7 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center text-sm font-bold shrink-0">1</div>
                <div>
                  <p className="text-sm font-medium text-gray-900">Tambah bahan baku</p>
                  <p className="text-xs text-gray-500">Klik "Tambah Bahan" di atas. Pilih dari daftar bahan umum atau isi manual.</p>
                  <p className="text-xs text-gray-400 mt-0.5">Contoh: Kopi Arabica — Rp120.000 / 1 kg</p>
                </div>
              </div>
              <div className="flex gap-3 items-start">
                <div className="w-7 h-7 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center text-sm font-bold shrink-0">2</div>
                <div>
                  <p className="text-sm font-medium text-gray-900">Isi stok awal</p>
                  <p className="text-xs text-gray-500">Di form yang sama, isi "Stok Awal" sesuai jumlah bahan yang lo punya sekarang. Langsung siap pake.</p>
                </div>
              </div>
              <div className="flex gap-3 items-start">
                <div className="w-7 h-7 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center text-sm font-bold shrink-0">3</div>
                <div>
                  <p className="text-sm font-medium text-gray-900">Hubungkan ke menu (Resep)</p>
                  <p className="text-xs text-gray-500">Buka halaman <a href="/dashboard/menu" className="text-blue-600 underline font-medium">Menu</a> → edit produk → tab Resep → pilih bahan dan isi jumlah per porsi.</p>
                  <p className="text-xs text-gray-400 mt-0.5">Contoh: Kopi Hitam butuh 15g Kopi Arabica + 10g Gula per porsi</p>
                </div>
              </div>
              <div className="flex gap-3 items-start">
                <div className="w-7 h-7 rounded-full bg-green-100 text-green-700 flex items-center justify-center text-sm font-bold shrink-0">4</div>
                <div>
                  <p className="text-sm font-medium text-gray-900">Otomatis!</p>
                  <p className="text-xs text-gray-500">Setiap pesanan masuk, stok bahan baku berkurang otomatis sesuai resep. Anda tinggal pantau dan restock.</p>
                </div>
              </div>
            </div>
            <div className="text-center">
              <button
                onClick={() => openCreate('recipe')}
                className="inline-flex items-center gap-2 px-5 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition font-medium"
              >
                <Plus className="w-4 h-4" /> Tambah Bahan Pertama
              </button>
            </div>
          </div>
        </div>
      ) : (
        <div className="space-y-3">
          {ingredients.map((ing) => {
            const isLow = ing.current_stock !== undefined && ing.min_stock !== undefined && ing.current_stock <= ing.min_stock;
            return (
              <div key={ing.id} className="bg-white rounded-xl border border-gray-200 p-4 space-y-3">
                {/* Header: name + badge + actions */}
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <h3 className="font-semibold text-gray-900">{ing.name}</h3>
                      {isLow && <AlertTriangle className="w-4 h-4 text-amber-500 shrink-0" />}
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                        ing.ingredient_type === 'recipe' ? 'bg-blue-50 text-blue-700' : 'bg-gray-100 text-gray-600'
                      }`}>
                        {ing.ingredient_type === 'recipe' ? 'Resep' : 'Overhead'}
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center gap-1 shrink-0">
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
                </div>

                {/* Info grid: stok + harga */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
                  <div>
                    <p className="text-xs text-gray-400">Stok</p>
                    <p className={`font-semibold ${isLow ? 'text-red-600' : 'text-gray-900'}`}>
                      {ing.current_stock !== undefined ? `${ing.current_stock} ${ing.base_unit}` : '-'}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-400">Cost/Unit</p>
                    <p className="font-medium text-gray-900">{formatCurrency(ing.cost_per_base_unit)}/{ing.base_unit}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-400">Harga Beli</p>
                    <p className="text-gray-600">
                      {ing.buy_price > 0 ? `${formatCurrency(ing.buy_price)} / ${ing.buy_qty}${ing.base_unit}` : <span className="text-amber-500">Belum diisi</span>}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-400">Satuan</p>
                    <p className="text-gray-600">{ing.base_unit} ({ing.unit_type})</p>
                  </div>
                </div>

                {/* Pemakaian per menu — SOURCE OF TRUTH */}
                <div className="border-t border-gray-100 pt-3">
                  <p className="text-xs font-semibold text-gray-500 uppercase mb-2">Pemakaian per Porsi</p>
                  {ing.used_in && ing.used_in.length > 0 ? (
                    <div className="flex flex-wrap gap-2">
                      {ing.used_in.map((u, idx) => (
                        <a key={idx} href="/dashboard/menu" className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-blue-50 text-blue-700 rounded-lg text-sm hover:bg-blue-100 transition">
                          <span className="font-medium">{u.product_name}</span>
                          <span className="text-blue-500">{u.qty_per_serving} {u.unit}</span>
                        </a>
                      ))}
                    </div>
                  ) : (
                    <div className="flex items-center gap-2 text-sm text-amber-600 bg-amber-50 px-3 py-2 rounded-lg">
                      <AlertTriangle className="w-4 h-4 shrink-0" />
                      <span>Belum terhubung ke menu. <a href="/dashboard/menu" className="underline font-medium">Buat resep di halaman Menu</a></span>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
          {/* Secondary: add overhead */}
          <div className="pt-2 text-center">
            <button
              onClick={() => openCreate('overhead')}
              className="text-xs text-gray-500 hover:text-gray-700 underline"
            >
              + Tambah Biaya Operasional (es, gas, listrik)
            </button>
          </div>
        </div>
      )}

      {/* Create/Edit Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="bg-white rounded-2xl w-full max-w-lg p-6 space-y-4 max-h-[90vh] overflow-y-auto">
            {/* Header — different for preset vs form step */}
            {modalStep === 'preset' ? (
              <div>
                <h2 className="text-lg font-bold">Mau nambah bahan apa?</h2>
                <p className="text-xs text-gray-500 mt-0.5">Pilih dari daftar di bawah buat isi cepat, atau klik "Lainnya" kalau gak ada.</p>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                {!editingId && form.ingredient_type === 'recipe' && (
                  <button onClick={() => setModalStep('preset')} className="p-1.5 hover:bg-gray-100 rounded-lg text-gray-500" title="Kembali">
                    <ArrowLeft className="w-4 h-4" />
                  </button>
                )}
                <h2 className="text-lg font-bold">
                  {editingId ? 'Edit Bahan Baku' : form.ingredient_type === 'overhead' ? 'Tambah Biaya Operasional' : 'Detail Bahan'}
                </h2>
              </div>
            )}
            {error && <p className="text-red-600 text-sm bg-red-50 border border-red-200 rounded-lg px-3 py-2">{error}</p>}

            {/* STEP: Preset selection */}
            {modalStep === 'preset' && !editingId && (
              <div className="space-y-3">
                <div className="grid grid-cols-3 sm:grid-cols-4 gap-2">
                  {PRESETS.map(p => (
                    <button
                      key={p.id}
                      onClick={() => pickPreset(p)}
                      className="flex flex-col items-center justify-center p-3 rounded-xl border-2 border-gray-200 hover:border-blue-400 hover:bg-blue-50 transition text-center"
                    >
                      <span className="text-2xl mb-1">{p.emoji}</span>
                      <span className="text-xs font-medium text-gray-900 leading-tight">{p.name}</span>
                    </button>
                  ))}
                  <button
                    onClick={pickCustom}
                    className="flex flex-col items-center justify-center p-3 rounded-xl border-2 border-dashed border-gray-300 hover:border-blue-400 hover:bg-blue-50 transition text-center"
                  >
                    <Plus className="w-6 h-6 text-gray-400 mb-1" />
                    <span className="text-xs font-medium text-gray-700">Lainnya</span>
                  </button>
                </div>
                <p className="text-xs text-gray-400 text-center">Nanti lo masih bisa edit nama & harga sesuai pembelian asli.</p>
              </div>
            )}

            {/* STEP: Form */}
            {modalStep === 'form' && (
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Nama Bahan *</label>
                  <input value={form.name} onChange={e => setForm({ ...form, name: e.target.value })}
                    className="w-full px-3 py-2.5 border rounded-lg text-base" placeholder="Contoh: Kopi Arabica" />
                </div>

                {/* Overhead-specific section */}
                {form.ingredient_type === 'overhead' ? (
                  <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 space-y-2">
                    <p className="text-xs text-amber-800 leading-relaxed">
                      <strong>Biaya operasional tetap</strong> (es batu, gas, listrik, air) yang susah dihitung per porsi.
                      Kasira <strong>tidak mengurangi stok</strong> bahan ini per pesanan — cuma dicatat sebagai biaya tetap harian.
                    </p>
                    <div>
                      <label className="block text-xs font-medium text-amber-700 mb-1">Estimasi Biaya per Hari (Rp)</label>
                      <input type="number" value={form.overhead_cost_per_day} onChange={e => setForm({ ...form, overhead_cost_per_day: e.target.value })}
                        className="w-full px-3 py-2 border border-amber-300 rounded-lg text-sm" placeholder="50000" />
                      <p className="text-xs text-amber-600 mt-1">
                        💡 Contoh: gas Rp50.000/hari. Kalau rata-rata 100 porsi/hari, alokasi ~Rp500/porsi.
                      </p>
                    </div>
                  </div>
                ) : null}

                {/* Bentuk bahan — 3 categories */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Bentuk Bahan *</label>
                  <div className="grid grid-cols-3 gap-2">
                    {UNIT_CATEGORIES.map(cat => {
                      const Icon = cat.icon;
                      const isActive = form.unit_type === cat.id;
                      return (
                        <button
                          key={cat.id}
                          type="button"
                          onClick={() => setForm({ ...form, unit_type: cat.id, base_unit: cat.units[0].value })}
                          className={`flex flex-col items-center p-3 cursor-pointer rounded-lg border-2 transition-all ${
                            isActive ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:border-blue-300'
                          }`}
                        >
                          <Icon className={`w-5 h-5 mb-1 ${isActive ? 'text-blue-600' : 'text-gray-400'}`} />
                          <span className={`text-sm font-medium ${isActive ? 'text-blue-700' : 'text-gray-900'}`}>{cat.label}</span>
                          <span className="text-[10px] text-gray-400 mt-0.5 leading-tight">{cat.desc}</span>
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Satuan sub-selector */}
                {form.unit_type && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Satuan Detail *</label>
                    <div className="grid grid-cols-2 gap-2">
                      {(UNIT_CATEGORIES.find(c => c.id === form.unit_type)?.units || []).map(u => (
                        <label key={u.value} className={`flex items-center justify-center p-2.5 cursor-pointer rounded-lg border-2 transition-all ${
                          form.base_unit === u.value ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:border-blue-300'
                        }`}>
                          <input type="radio" name="unit" value={u.value} checked={form.base_unit === u.value}
                            onChange={() => setForm({ ...form, base_unit: u.value })} className="sr-only" />
                          <span className={`text-sm font-medium ${form.base_unit === u.value ? 'text-blue-700' : 'text-gray-900'}`}>{u.label}</span>
                        </label>
                      ))}
                    </div>
                  </div>
                )}

                {/* Harga Beli */}
                {form.ingredient_type !== 'overhead' && (
                  <div className="bg-gray-50 rounded-lg p-4 space-y-3">
                    <p className="text-sm font-medium text-gray-700">💰 Harga Beli</p>
                    <p className="text-xs text-gray-500">Isi sesuai nota belanja. Contoh: beli 1 kg gula seharga Rp14.000.</p>
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-xs text-gray-500 mb-1">Total Harga (Rp) *</label>
                        <input type="number" value={form.buy_price} onChange={e => setForm({ ...form, buy_price: e.target.value })}
                          className="w-full px-3 py-2.5 border rounded-lg text-base" placeholder="14000" />
                      </div>
                      <div>
                        <label className="block text-xs text-gray-500 mb-1">Dapat ({form.base_unit || '...'}) *</label>
                        <input type="number" step="any" value={form.buy_qty} onChange={e => setForm({ ...form, buy_qty: e.target.value })}
                          className="w-full px-3 py-2.5 border rounded-lg text-base" placeholder="1000" />
                      </div>
                    </div>
                    {(parseFloat(form.buy_price) > 0 && parseFloat(form.buy_qty) > 0) && (
                      <div className="bg-green-50 border border-green-200 rounded-lg px-3 py-2">
                        <p className="text-sm text-green-800 font-medium">
                          Harga per {form.base_unit || 'unit'}: {new Intl.NumberFormat('id-ID', { style: 'currency', currency: 'IDR', maximumFractionDigits: 2 }).format(parseFloat(form.buy_price) / parseFloat(form.buy_qty))}
                        </p>
                      </div>
                    )}
                  </div>
                )}

                {/* Init stock — create mode only, recipe only */}
                {!editingId && form.ingredient_type !== 'overhead' && (
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 space-y-2">
                    <div className="flex items-center gap-2">
                      <Sparkles className="w-4 h-4 text-blue-600" />
                      <p className="text-sm font-medium text-blue-900">Stok Awal</p>
                      <span className="text-xs text-blue-600">(opsional)</span>
                    </div>
                    <p className="text-xs text-blue-700">Sekarang ada berapa di outlet? Biar langsung siap pake, gak perlu restock manual nanti.</p>
                    <div className="flex items-center gap-2">
                      <input type="number" step="any" value={form.initial_stock} onChange={e => setForm({ ...form, initial_stock: e.target.value })}
                        className="flex-1 px-3 py-2.5 border border-blue-300 rounded-lg text-base" placeholder="0" />
                      <span className="text-sm font-medium text-blue-700 shrink-0">{form.base_unit || 'unit'}</span>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Action buttons — only in form step */}
            {modalStep === 'form' && (
              <div className="flex justify-end gap-3 pt-2">
                <button onClick={() => { setShowModal(false); resetForm(); }} className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg">Batal</button>
                <button onClick={handleSave}
                  disabled={!form.name || !form.base_unit || (form.ingredient_type !== 'overhead' && (!form.buy_price || !form.buy_qty))}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50">
                  {editingId ? 'Simpan' : 'Tambah Bahan'}
                </button>
              </div>
            )}
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
