'use client';

import { useState, useEffect } from 'react';
import {
  getOutlets, getProducts, getCategories,
  toggleProductActive, createProduct, updateProduct, deleteProduct,
  createCategory, updateCategory, deleteCategory,
  getIngredients, getRecipes, createRecipe, updateRecipe, getCurrentUser,
} from '@/app/actions/api';
import { Plus, Search, Edit2, Loader2, X, Trash2, Tag, Upload, ImageOff, Package, FlaskConical } from 'lucide-react';
import { useRef } from 'react';

export default function MenuPage() {
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'produk' | 'kategori'>('produk');

  const [products, setProducts] = useState<any[]>([]);
  const [categories, setCategories] = useState<any[]>([]);
  const [brandId, setBrandId] = useState('');
  const [outletId, setOutletId] = useState('');
  const [stockMode, setStockMode] = useState('simple');
  const [isPro, setIsPro] = useState(false);
  const [search, setSearch] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');

  // Product modal
  const [isProductModalOpen, setIsProductModalOpen] = useState(false);
  const [editingProduct, setEditingProduct] = useState<any>(null);
  const [productForm, setProductForm] = useState({
    name: '', description: '', base_price: '', stock_qty: '',
    category_id: '', image_url: '', is_active: true,
  });
  const [savingProduct, setSavingProduct] = useState(false);
  const [uploadingImage, setUploadingImage] = useState(false);
  const [deletingProductId, setDeletingProductId] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Recipe state (inside product modal)
  const [modalTab, setModalTab] = useState<'info' | 'resep'>('info');
  const [allIngredients, setAllIngredients] = useState<any[]>([]);
  const [recipeIngredients, setRecipeIngredients] = useState<any[]>([]);
  const [existingRecipeId, setExistingRecipeId] = useState<string | null>(null);
  const [savingRecipe, setSavingRecipe] = useState(false);
  const [recipeError, setRecipeError] = useState('');

  // Category modal
  const [isCatModalOpen, setIsCatModalOpen] = useState(false);
  const [editingCat, setEditingCat] = useState<any>(null);
  const [catForm, setCatForm] = useState({ name: '', is_active: true });
  const [savingCat, setSavingCat] = useState(false);
  const [deletingCatId, setDeletingCatId] = useState<string | null>(null);

  useEffect(() => { loadData(); }, []);

  async function loadData() {
    setLoading(true);
    try {
      const [outlets, user] = await Promise.all([getOutlets(), getCurrentUser()]);
      if (outlets?.length > 0) {
        const outlet = outlets[0];
        setBrandId(outlet.brand_id);
        setOutletId(outlet.id);
        setStockMode(outlet.stock_mode || 'simple');
        const [prods, cats] = await Promise.all([
          getProducts(outlet.brand_id),
          getCategories(outlet.brand_id),
        ]);
        setProducts(prods || []);
        setCategories(cats || []);
      }
      if (user) {
        const tier = user.subscription_tier || 'starter';
        setIsPro(['pro', 'business', 'enterprise'].includes(tier));
      }
    } finally {
      setLoading(false);
    }
  }

  // ── Product handlers ────────────────────────────────────────────────────────

  const handleToggleActive = async (product: any) => {
    const newStatus = !product.is_active;
    setProducts(products.map(p => p.id === product.id ? { ...p, is_active: newStatus } : p));
    const ok = await toggleProductActive(product.id, newStatus, product.row_version);
    if (!ok) {
      setProducts(products.map(p => p.id === product.id ? { ...p, is_active: product.is_active } : p));
      alert('Gagal mengubah status produk');
    }
  };

  const handleDeleteProduct = async (product: any) => {
    if (!window.confirm(`Hapus produk "${product.name}"? Tindakan ini tidak bisa dibatalkan.`)) return;
    setDeletingProductId(product.id);
    const ok = await deleteProduct(product.id);
    if (ok) {
      setProducts(products.filter(p => p.id !== product.id));
    } else {
      alert('Gagal menghapus produk');
    }
    setDeletingProductId(null);
  };

  const openProductModal = async (product: any = null) => {
    setModalTab('info');
    setRecipeIngredients([]);
    setExistingRecipeId(null);
    setRecipeError('');

    if (product) {
      setEditingProduct(product);
      setProductForm({
        name: product.name,
        description: product.description || '',
        base_price: product.base_price.toString(),
        stock_qty: product.stock_qty.toString(),
        category_id: product.category_id || '',
        image_url: product.image_url || '',
        is_active: product.is_active,
      });
      // Load recipe & ingredients for Pro
      if (isPro) {
        const [ings, recipes] = await Promise.all([
          getIngredients(brandId),
          getRecipes({ product_id: product.id }),
        ]);
        setAllIngredients(ings || []);
        if (recipes?.length > 0) {
          const recipe = recipes[0];
          setExistingRecipeId(recipe.id);
          setRecipeIngredients(
            recipe.ingredients.map((ri: any) => ({
              ingredient_id: ri.ingredient_id,
              name: ri.ingredient_name || '',
              quantity: ri.quantity,
              quantity_unit: ri.quantity_unit,
              is_optional: ri.is_optional,
              cost: ri.ingredient_cost || 0,
            }))
          );
        }
      }
    } else {
      setEditingProduct(null);
      setProductForm({
        name: '', description: '', base_price: '', stock_qty: '',
        category_id: categories.length > 0 ? categories[0].id : '',
        image_url: '', is_active: true,
      });
      if (isPro) {
        const ings = await getIngredients(brandId);
        setAllIngredients(ings || []);
      }
    }
    setIsProductModalOpen(true);
  };

  const handleImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadingImage(true);
    try {
      const fd = new FormData();
      fd.append('file', file);
      const res = await fetch('/api/upload', { method: 'POST', body: fd });
      const data = await res.json();
      if (res.ok && data.url) {
        const baseUrl = process.env.NEXT_PUBLIC_API_URL?.replace('/api/v1', '') || '';
        setProductForm(f => ({ ...f, image_url: `${baseUrl}${data.url}` }));
      } else {
        alert(data.detail || 'Gagal upload gambar');
      }
    } catch {
      alert('Gagal upload gambar');
    } finally {
      setUploadingImage(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleProductSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSavingProduct(true);
    const payload: any = {
      brand_id: brandId,
      name: productForm.name,
      description: productForm.description || null,
      base_price: parseFloat(productForm.base_price),
      stock_qty: stockMode === 'recipe' ? 0 : parseInt(productForm.stock_qty || '0'),
      stock_enabled: stockMode === 'simple',
      category_id: productForm.category_id || null,
      image_url: productForm.image_url || null,
      is_active: productForm.is_active,
    };
    if (editingProduct) payload.row_version = editingProduct.row_version;
    const res = editingProduct
      ? await updateProduct(editingProduct.id, payload)
      : await createProduct(payload);
    if (res.success) {
      setIsProductModalOpen(false);
      loadData();
    } else {
      alert(res.message || 'Gagal menyimpan produk');
    }
    setSavingProduct(false);
  };

  // ── Category handlers ───────────────────────────────────────────────────────

  const openCatModal = (cat: any = null) => {
    if (cat) {
      setEditingCat(cat);
      setCatForm({ name: cat.name, is_active: cat.is_active });
    } else {
      setEditingCat(null);
      setCatForm({ name: '', is_active: true });
    }
    setIsCatModalOpen(true);
  };

  const handleCatSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!catForm.name.trim()) return;
    setSavingCat(true);
    const res = editingCat
      ? await updateCategory(editingCat.id, { name: catForm.name.trim(), is_active: catForm.is_active })
      : await createCategory(brandId, catForm.name.trim());
    if (res.success) {
      setIsCatModalOpen(false);
      const cats = await getCategories(brandId);
      setCategories(cats || []);
    } else {
      alert(res.message || 'Gagal menyimpan kategori');
    }
    setSavingCat(false);
  };

  const handleToggleCatActive = async (cat: any) => {
    const newStatus = !cat.is_active;
    setCategories(categories.map(c => c.id === cat.id ? { ...c, is_active: newStatus } : c));
    const res = await updateCategory(cat.id, { is_active: newStatus });
    if (!res.success) {
      setCategories(categories.map(c => c.id === cat.id ? { ...c, is_active: cat.is_active } : c));
      alert('Gagal mengubah status kategori');
    }
  };

  const handleDeleteCat = async (cat: any) => {
    const count = products.filter(p => p.category_id === cat.id).length;
    const msg = count > 0
      ? `Kategori "${cat.name}" dipakai ${count} produk. Produk tidak ikut terhapus. Lanjut?`
      : `Hapus kategori "${cat.name}"?`;
    if (!window.confirm(msg)) return;
    setDeletingCatId(cat.id);
    const ok = await deleteCategory(cat.id);
    if (ok) {
      setCategories(categories.filter(c => c.id !== cat.id));
    } else {
      alert('Gagal menghapus kategori');
    }
    setDeletingCatId(null);
  };

  // ── Helpers ─────────────────────────────────────────────────────────────────

  const filteredProducts = products.filter(p => {
    const matchSearch = p.name.toLowerCase().includes(search.toLowerCase());
    const matchCat = selectedCategory === 'all' || p.category_id === selectedCategory;
    return matchSearch && matchCat;
  });

  const fmt = (n: number) =>
    new Intl.NumberFormat('id-ID', { style: 'currency', currency: 'IDR', maximumFractionDigits: 0 }).format(n || 0);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-6 h-6 animate-spin text-blue-500" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Menu &amp; Kategori</h1>
          <p className="text-gray-500">Kelola produk, stok, dan kategori outlet Anda.</p>
        </div>
        {activeTab === 'produk' ? (
          <button onClick={() => openProductModal()}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium">
            <Plus className="w-4 h-4" /> Tambah Produk
          </button>
        ) : (
          <button onClick={() => openCatModal()}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium">
            <Plus className="w-4 h-4" /> Tambah Kategori
          </button>
        )}
      </div>

      {/* Tabs */}
      <div className="flex border-b border-gray-200">
        {(['produk', 'kategori'] as const).map(tab => (
          <button key={tab} onClick={() => setActiveTab(tab)}
            className={`px-5 py-2.5 text-sm font-medium border-b-2 transition-colors capitalize ${
              activeTab === tab
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}>
            {tab === 'produk' ? 'Produk' : 'Kategori'}
            <span className="ml-2 px-2 py-0.5 rounded-full bg-gray-100 text-xs text-gray-600">
              {tab === 'produk' ? products.length : categories.length}
            </span>
          </button>
        ))}
      </div>

      {/* ── Tab Produk ── */}
      {activeTab === 'produk' && (
        <>
          {/* Filters */}
          <div className="flex flex-col sm:flex-row gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input type="text" placeholder="Cari produk..."
                value={search} onChange={e => setSearch(e.target.value)}
                className="w-full pl-9 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none" />
            </div>
            <select value={selectedCategory} onChange={e => setSelectedCategory(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none bg-white">
              <option value="all">Semua Kategori</option>
              {categories.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </div>

          {/* Product table */}
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left">
                <thead>
                  <tr className="bg-gray-50 border-b border-gray-200 text-xs font-medium text-gray-500 uppercase tracking-wide">
                    <th className="px-4 py-3">Produk</th>
                    <th className="px-4 py-3">Kategori</th>
                    <th className="px-4 py-3">Harga</th>
                    {stockMode === 'simple' && <th className="px-4 py-3">Stok</th>}
                    <th className="px-4 py-3">Aktif</th>
                    <th className="px-4 py-3 text-right">Aksi</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {filteredProducts.length > 0 ? filteredProducts.map(p => (
                    <tr key={p.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-3">
                          <div className="w-9 h-9 rounded-lg bg-gray-100 flex-shrink-0 overflow-hidden flex items-center justify-center">
                            {p.image_url
                              ? <img src={p.image_url} alt={p.name} className="w-full h-full object-cover" />
                              : <span className="text-gray-400 text-sm font-medium">{p.name.charAt(0)}</span>}
                          </div>
                          <div className="min-w-0">
                            <p className="text-sm font-medium text-gray-900 truncate">{p.name}</p>
                            {p.description && <p className="text-xs text-gray-400 truncate max-w-[180px]">{p.description}</p>}
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600">
                        {categories.find(c => c.id === p.category_id)?.name
                          || <span className="text-gray-300 italic text-xs">—</span>}
                      </td>
                      <td className="px-4 py-3 text-sm font-medium text-gray-900">{fmt(p.base_price)}</td>
                      {stockMode === 'simple' && (
                        <td className="px-4 py-3">
                          <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                            p.stock_qty <= 5 ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'
                          }`}>{p.stock_qty}</span>
                        </td>
                      )}
                      <td className="px-4 py-3">
                        <button onClick={() => handleToggleActive(p)}
                          className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
                            p.is_active ? 'bg-blue-600' : 'bg-gray-200'
                          }`}>
                          <span className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform ${
                            p.is_active ? 'translate-x-4' : 'translate-x-0.5'
                          }`} />
                        </button>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center justify-end gap-1">
                          <button onClick={() => openProductModal(p)}
                            className="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors" title="Edit">
                            <Edit2 className="w-4 h-4" />
                          </button>
                          <button onClick={() => handleDeleteProduct(p)}
                            disabled={deletingProductId === p.id}
                            className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors disabled:opacity-50" title="Hapus">
                            {deletingProductId === p.id
                              ? <Loader2 className="w-4 h-4 animate-spin" />
                              : <Trash2 className="w-4 h-4" />}
                          </button>
                        </div>
                      </td>
                    </tr>
                  )) : (
                    <tr>
                      <td colSpan={6} className="px-4 py-10 text-center text-sm text-gray-400">
                        Tidak ada produk ditemukan
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {/* ── Tab Kategori ── */}
      {activeTab === 'kategori' && (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          {categories.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-gray-400">
              <Tag className="w-10 h-10 mb-3 opacity-30" />
              <p className="text-sm">Belum ada kategori.</p>
              <button onClick={() => openCatModal()}
                className="mt-4 flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm">
                <Plus className="w-4 h-4" /> Tambah Kategori Pertama
              </button>
            </div>
          ) : (
            /* Card list — tidak pakai tabel supaya tombol aksi selalu kelihatan */
            <ul className="divide-y divide-gray-100">
              {categories.map(cat => {
                const count = products.filter(p => p.category_id === cat.id).length;
                return (
                  <li key={cat.id} className="flex items-center gap-3 px-4 py-3 hover:bg-gray-50">
                    <Tag className="w-4 h-4 text-blue-400 flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate">{cat.name}</p>
                      <p className="text-xs text-gray-400">{count} produk</p>
                    </div>
                    {/* Toggle aktif */}
                    <button onClick={() => handleToggleCatActive(cat)}
                      className={`relative inline-flex h-5 w-9 flex-shrink-0 items-center rounded-full transition-colors ${
                        cat.is_active ? 'bg-blue-600' : 'bg-gray-200'
                      }`}>
                      <span className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform ${
                        cat.is_active ? 'translate-x-4' : 'translate-x-0.5'
                      }`} />
                    </button>
                    {/* Edit */}
                    <button onClick={() => openCatModal(cat)}
                      className="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors flex-shrink-0" title="Edit">
                      <Edit2 className="w-4 h-4" />
                    </button>
                    {/* Hapus */}
                    <button onClick={() => handleDeleteCat(cat)}
                      disabled={deletingCatId === cat.id}
                      className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors flex-shrink-0 disabled:opacity-50" title="Hapus">
                      {deletingCatId === cat.id
                        ? <Loader2 className="w-4 h-4 animate-spin" />
                        : <Trash2 className="w-4 h-4" />}
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      )}

      {/* ── Modal Produk ── */}
      {isProductModalOpen && (
        <div className="fixed inset-0 z-50 flex items-start justify-center p-4 pt-10 bg-gray-900/50 overflow-y-auto">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-lg">
            <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200">
              <h3 className="text-base font-bold text-gray-900">
                {editingProduct ? 'Edit Produk' : 'Tambah Produk'}
              </h3>
              <button onClick={() => setIsProductModalOpen(false)} className="text-gray-400 hover:text-gray-600">
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Tabs — Info / Resep */}
            {isPro && editingProduct && (
              <div className="flex border-b border-gray-200 px-5">
                <button onClick={() => setModalTab('info')}
                  className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                    modalTab === 'info' ? 'border-blue-600 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700'
                  }`}>
                  Info Produk
                </button>
                <button onClick={() => setModalTab('resep')}
                  className={`flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                    modalTab === 'resep' ? 'border-blue-600 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700'
                  }`}>
                  <FlaskConical className="w-3.5 h-3.5" />
                  Resep
                  {recipeIngredients.length > 0 && (
                    <span className="px-1.5 py-0.5 bg-blue-100 text-blue-700 text-xs rounded-full">{recipeIngredients.length}</span>
                  )}
                </button>
              </div>
            )}

            {/* Tab: Info Produk */}
            {modalTab === 'info' && (
              <form onSubmit={handleProductSubmit} className="p-5 space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Nama Produk <span className="text-red-500">*</span></label>
                  <input type="text" required autoFocus
                    value={productForm.name} onChange={e => setProductForm({ ...productForm, name: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Kategori
                    {categories.length === 0 && <span className="ml-1 text-xs text-amber-500">— tambah dulu di tab Kategori</span>}
                  </label>
                  <select value={productForm.category_id}
                    onChange={e => setProductForm({ ...productForm, category_id: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none bg-white">
                    <option value="">Tanpa Kategori</option>
                    {categories.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                  </select>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Harga (Rp) <span className="text-red-500">*</span></label>
                    <input type="number" required min="0"
                      value={productForm.base_price} onChange={e => setProductForm({ ...productForm, base_price: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none" />
                  </div>
                  {stockMode === 'simple' && (
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Stok <span className="text-red-500">*</span></label>
                      <input type="number" required min="0"
                        value={productForm.stock_qty} onChange={e => setProductForm({ ...productForm, stock_qty: e.target.value })}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none" />
                    </div>
                  )}
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Foto Produk (Opsional)</label>
                  <input ref={fileInputRef} type="file" accept="image/*" className="hidden" onChange={handleImageUpload} />
                  {productForm.image_url ? (
                    <div className="flex items-center gap-3">
                      <img src={productForm.image_url} alt="preview"
                        className="h-20 w-20 rounded-lg object-cover border border-gray-200 flex-shrink-0"
                        onError={e => { (e.target as HTMLImageElement).style.display = 'none'; }} />
                      <div className="flex flex-col gap-1.5">
                        <button type="button" onClick={() => fileInputRef.current?.click()}
                          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-blue-600 border border-blue-300 rounded-lg hover:bg-blue-50">
                          {uploadingImage ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Upload className="w-3.5 h-3.5" />}
                          Ganti foto
                        </button>
                        <button type="button" onClick={() => setProductForm(f => ({ ...f, image_url: '' }))}
                          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-red-500 border border-red-200 rounded-lg hover:bg-red-50">
                          <ImageOff className="w-3.5 h-3.5" /> Hapus foto
                        </button>
                      </div>
                    </div>
                  ) : (
                    <button type="button" onClick={() => fileInputRef.current?.click()} disabled={uploadingImage}
                      className="w-full flex flex-col items-center justify-center gap-2 h-24 border-2 border-dashed border-gray-300 rounded-lg hover:border-blue-400 hover:bg-blue-50 transition-colors disabled:opacity-50">
                      {uploadingImage ? <Loader2 className="w-6 h-6 animate-spin text-blue-500" /> : <Upload className="w-6 h-6 text-gray-400" />}
                      <span className="text-xs text-gray-500">{uploadingImage ? 'Mengupload...' : 'Klik untuk pilih foto dari perangkat'}</span>
                    </button>
                  )}
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Deskripsi (Opsional)</label>
                  <textarea rows={2}
                    value={productForm.description} onChange={e => setProductForm({ ...productForm, description: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none resize-none" />
                </div>
                <div className="flex items-center gap-3">
                  <button type="button" onClick={() => setProductForm({ ...productForm, is_active: !productForm.is_active })}
                    className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
                      productForm.is_active ? 'bg-blue-600' : 'bg-gray-200'
                    }`}>
                    <span className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform ${
                      productForm.is_active ? 'translate-x-4' : 'translate-x-0.5'
                    }`} />
                  </button>
                  <span className="text-sm text-gray-600">{productForm.is_active ? 'Aktif di kasir' : 'Disembunyikan'}</span>
                </div>
                <div className="flex justify-end gap-3 pt-2">
                  <button type="button" onClick={() => setIsProductModalOpen(false)}
                    className="px-4 py-2 text-sm text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50">Batal</button>
                  <button type="submit" disabled={savingProduct}
                    className="flex items-center px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50">
                    {savingProduct && <Loader2 className="w-4 h-4 animate-spin mr-2" />}
                    Simpan
                  </button>
                </div>
              </form>
            )}

            {/* Tab: Resep / Recipe Builder */}
            {modalTab === 'resep' && editingProduct && (
              <div className="p-5 space-y-4">
                {recipeError && <p className="text-sm text-red-600">{recipeError}</p>}

                {allIngredients.length === 0 ? (
                  <div className="text-center py-8 text-gray-400">
                    <Package className="w-8 h-8 mx-auto mb-2 text-gray-300" />
                    <p className="text-sm">Belum ada bahan baku. Tambahkan di halaman Bahan Baku.</p>
                  </div>
                ) : (
                  <>
                    {/* Add ingredient row */}
                    <div className="flex gap-2">
                      <select id="add-ingredient" className="flex-1 px-3 py-2 border rounded-lg text-sm bg-white">
                        <option value="">Pilih bahan baku...</option>
                        {allIngredients
                          .filter(ing => !recipeIngredients.some(ri => ri.ingredient_id === ing.id))
                          .map(ing => (
                            <option key={ing.id} value={ing.id}>{ing.name} ({ing.base_unit})</option>
                          ))}
                      </select>
                      <button type="button" onClick={() => {
                        const sel = document.getElementById('add-ingredient') as HTMLSelectElement;
                        const ingId = sel.value;
                        if (!ingId) return;
                        const ing = allIngredients.find(i => i.id === ingId);
                        if (!ing) return;
                        setRecipeIngredients([...recipeIngredients, {
                          ingredient_id: ing.id, name: ing.name,
                          quantity: 0, quantity_unit: ing.base_unit,
                          is_optional: false, cost: ing.cost_per_base_unit || 0,
                          buy_price: ing.buy_price || 0, buy_qty: ing.buy_qty || 1,
                        }]);
                        sel.value = '';
                      }}
                        className="px-3 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700">
                        <Plus className="w-4 h-4" />
                      </button>
                    </div>

                    {/* Ingredient list */}
                    {recipeIngredients.length === 0 ? (
                      <p className="text-sm text-gray-400 text-center py-4">Belum ada bahan. Pilih dari dropdown di atas.</p>
                    ) : (
                      <div className="space-y-2">
                        {recipeIngredients.map((ri, idx) => {
                          const lineCost = ri.quantity * ri.cost;
                          return (
                            <div key={ri.ingredient_id} className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                              <div className="flex-1 min-w-0">
                                <p className="text-sm font-medium text-gray-900 truncate">{ri.name}</p>
                                <p className="text-xs text-gray-400">
                                  {ri.buy_price > 0 && `${fmt(ri.buy_price)}/${ri.buy_qty}${ri.quantity_unit} → `}
                                  {fmt(ri.cost)}/{ri.quantity_unit}
                                  {ri.quantity > 0 && ` = ${fmt(lineCost)}`}
                                </p>
                              </div>
                              <div className="flex items-center gap-1">
                                <input type="number" step="any" min="0" placeholder="Qty"
                                  value={ri.quantity || ''}
                                  onChange={e => {
                                    const updated = [...recipeIngredients];
                                    updated[idx] = { ...updated[idx], quantity: parseFloat(e.target.value) || 0 };
                                    setRecipeIngredients(updated);
                                  }}
                                  className="w-20 px-2 py-1.5 border rounded-lg text-sm text-right" />
                                <span className="text-xs text-gray-500 w-10">{ri.quantity_unit}</span>
                              </div>
                              <button type="button" onClick={() => {
                                setRecipeIngredients(recipeIngredients.filter((_, i) => i !== idx));
                              }} className="p-1 text-red-400 hover:text-red-600">
                                <Trash2 className="w-4 h-4" />
                              </button>
                            </div>
                          );
                        })}
                      </div>
                    )}

                    {/* HPP Summary */}
                    {recipeIngredients.length > 0 && (
                      <div className="bg-blue-50 rounded-lg p-4 space-y-2">
                        <div className="flex justify-between text-sm">
                          <span className="text-gray-600">HPP (Harga Pokok)</span>
                          <span className="font-bold text-gray-900">
                            {fmt(recipeIngredients.reduce((s, ri) => s + ri.quantity * ri.cost, 0))}
                          </span>
                        </div>
                        <div className="flex justify-between text-sm">
                          <span className="text-gray-600">Harga Jual</span>
                          <span className="font-medium text-gray-900">{fmt(parseFloat(productForm.base_price) || 0)}</span>
                        </div>
                        {(() => {
                          const hpp = recipeIngredients.reduce((s, ri) => s + ri.quantity * ri.cost, 0);
                          const price = parseFloat(productForm.base_price) || 0;
                          const margin = price - hpp;
                          const pct = price > 0 ? (margin / price * 100) : 0;
                          return (
                            <div className="flex justify-between text-sm pt-2 border-t border-blue-200">
                              <span className="text-gray-600">Margin</span>
                              <span className={`font-bold ${pct < 20 ? 'text-red-600' : pct < 40 ? 'text-amber-600' : 'text-green-600'}`}>
                                {fmt(margin)} ({pct.toFixed(1)}%)
                              </span>
                            </div>
                          );
                        })()}
                      </div>
                    )}
                  </>
                )}

                <div className="flex justify-end gap-3 pt-2">
                  <button type="button" onClick={() => setIsProductModalOpen(false)}
                    className="px-4 py-2 text-sm text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50">Batal</button>
                  <button type="button" disabled={savingRecipe || recipeIngredients.length === 0}
                    onClick={async () => {
                      setSavingRecipe(true);
                      setRecipeError('');
                      try {
                        const payload = {
                          product_id: editingProduct.id,
                          ingredients: recipeIngredients.map(ri => ({
                            ingredient_id: ri.ingredient_id,
                            quantity: ri.quantity,
                            quantity_unit: ri.quantity_unit,
                            is_optional: ri.is_optional,
                          })),
                        };
                        if (existingRecipeId) {
                          await updateRecipe(existingRecipeId, { ingredients: payload.ingredients });
                        } else {
                          await createRecipe(payload);
                        }
                        setIsProductModalOpen(false);
                      } catch (e: any) {
                        setRecipeError(e.message);
                      }
                      setSavingRecipe(false);
                    }}
                    className="flex items-center px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50">
                    {savingRecipe && <Loader2 className="w-4 h-4 animate-spin mr-2" />}
                    Simpan Resep
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── Modal Kategori ── */}
      {isCatModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-gray-900/50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-sm">
            <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200">
              <h3 className="text-base font-bold text-gray-900">
                {editingCat ? 'Edit Kategori' : 'Tambah Kategori'}
              </h3>
              <button onClick={() => setIsCatModalOpen(false)} className="text-gray-400 hover:text-gray-600">
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleCatSubmit} className="p-5 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Nama Kategori <span className="text-red-500">*</span></label>
                <input type="text" required autoFocus placeholder="cth: Minuman, Makanan, Snack..."
                  value={catForm.name} onChange={e => setCatForm({ ...catForm, name: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none" />
              </div>
              {editingCat && (
                <div className="flex items-center gap-3">
                  <button type="button" onClick={() => setCatForm({ ...catForm, is_active: !catForm.is_active })}
                    className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
                      catForm.is_active ? 'bg-blue-600' : 'bg-gray-200'
                    }`}>
                    <span className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform ${
                      catForm.is_active ? 'translate-x-4' : 'translate-x-0.5'
                    }`} />
                  </button>
                  <span className="text-sm text-gray-600">{catForm.is_active ? 'Aktif' : 'Non-aktif'}</span>
                </div>
              )}
              <div className="flex justify-end gap-3 pt-1">
                <button type="button" onClick={() => setIsCatModalOpen(false)}
                  className="px-4 py-2 text-sm text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50">
                  Batal
                </button>
                <button type="submit" disabled={savingCat}
                  className="flex items-center px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50">
                  {savingCat && <Loader2 className="w-4 h-4 animate-spin mr-2" />}
                  Simpan
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
