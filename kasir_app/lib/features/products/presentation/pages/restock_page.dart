import 'package:drift/drift.dart' as drift;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:dio/dio.dart';
import 'package:lucide_icons/lucide_icons.dart';

import '../../../../core/config/app_config.dart';
import '../../../../core/database/app_database.dart';
import '../../../../core/sync/sync_provider.dart';
import '../../../../core/services/session_cache.dart';
import '../../../../core/theme/app_colors.dart';

/// Restock page — support simple & recipe mode.
/// Simple mode: list product stock_enabled, tap → restock product.
/// Recipe mode: list ingredient + current outlet_stock, tap → restock ingredient.
class RestockPage extends ConsumerStatefulWidget {
  /// Jika `true`, page di-render tanpa Scaffold+AppBar — dipake saat embed
  /// di dalam TabBarView ProductManagementPage. Default `false` (standalone).
  final bool embedded;
  const RestockPage({super.key, this.embedded = false});

  @override
  ConsumerState<RestockPage> createState() => _RestockPageState();
}

class _RestockPageState extends ConsumerState<RestockPage> {
  final _searchController = TextEditingController();
  String _searchQuery = '';
  late final String _stockMode;
  Future<List<_RestockItem>>? _itemsFuture;

  @override
  void initState() {
    super.initState();
    _stockMode = SessionCache.instance.stockMode ?? 'simple';
    _itemsFuture = _loadItems();
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<List<_RestockItem>> _loadItems() async {
    final db = ref.read(databaseProvider);
    final outletId = SessionCache.instance.outletId ?? '';

    if (_stockMode == 'recipe') {
      final ingredients = await (db.select(db.ingredients)
            ..where((i) => i.isDeleted.equals(false))
            ..orderBy([(i) => drift.OrderingTerm.asc(i.name)]))
          .get();
      final stocks = await (db.select(db.outletStocks)
            ..where((os) => os.outletId.equals(outletId))
            ..where((os) => os.isDeleted.equals(false)))
          .get();
      final stockMap = {for (final s in stocks) s.ingredientId: s.computedStock};

      return ingredients
          .map((ing) => _RestockItem(
                id: ing.id,
                name: ing.name,
                currentStock: stockMap[ing.id] ?? 0.0,
                unit: ing.baseUnit,
                isRecipe: true,
              ))
          .toList();
    }

    // Simple mode — list products
    final products = await (db.select(db.products)
          ..where((p) => p.isDeleted.equals(false))
          ..where((p) => p.stockEnabled.equals(true))
          ..orderBy([(p) => drift.OrderingTerm.asc(p.name)]))
        .get();
    return products
        .map((p) => _RestockItem(
              id: p.id,
              name: p.name,
              currentStock: p.stockQty.toDouble(),
              unit: 'pcs',
              isRecipe: false,
              rowVersion: p.rowVersion,
              currentBuyPrice: p.buyPrice,
            ))
        .toList();
  }

  Future<void> _refresh() async {
    setState(() => _itemsFuture = _loadItems());
  }

  Future<void> _openRestockSheet(_RestockItem item) async {
    final result = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => _RestockSheet(item: item),
    );
    if (result == true && mounted) {
      await _refresh();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Stok ${item.name} berhasil ditambah'),
            backgroundColor: AppColors.success,
            behavior: SnackBarBehavior.floating,
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final body = Column(
        children: [
          // Mode banner
          Container(
            width: double.infinity,
            color: _stockMode == 'recipe'
                ? AppColors.primary.withOpacity(0.06)
                : AppColors.surface,
            padding: const EdgeInsets.fromLTRB(20, 12, 20, 12),
            child: Row(
              children: [
                Icon(
                  _stockMode == 'recipe' ? LucideIcons.package : LucideIcons.box,
                  size: 16,
                  color: AppColors.textSecondary,
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    _stockMode == 'recipe'
                        ? 'Mode Resep — restock bahan baku'
                        : 'Mode Sederhana — restock produk langsung',
                    style: const TextStyle(
                      fontSize: 12,
                      color: AppColors.textSecondary,
                    ),
                  ),
                ),
              ],
            ),
          ),

          // Search
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 12, 20, 8),
            child: TextField(
              controller: _searchController,
              decoration: InputDecoration(
                hintText: _stockMode == 'recipe'
                    ? 'Cari bahan baku...'
                    : 'Cari produk...',
                prefixIcon: const Icon(LucideIcons.search,
                    color: AppColors.textTertiary, size: 18),
                filled: true,
                fillColor: AppColors.surfaceVariant,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(10),
                  borderSide: BorderSide.none,
                ),
                contentPadding: const EdgeInsets.symmetric(vertical: 10),
                isDense: true,
              ),
              onChanged: (val) =>
                  setState(() => _searchQuery = val.toLowerCase()),
            ),
          ),

          // List
          Expanded(
            child: FutureBuilder<List<_RestockItem>>(
              future: _itemsFuture,
              builder: (context, snapshot) {
                if (snapshot.connectionState == ConnectionState.waiting) {
                  return const Center(child: CircularProgressIndicator());
                }
                if (snapshot.hasError) {
                  return Center(child: Text('Gagal memuat: ${snapshot.error}'));
                }
                final items = snapshot.data ?? [];
                final filtered = _searchQuery.isEmpty
                    ? items
                    : items
                        .where(
                            (i) => i.name.toLowerCase().contains(_searchQuery))
                        .toList();

                if (filtered.isEmpty) {
                  return Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const Icon(LucideIcons.packageSearch,
                            size: 40, color: AppColors.textTertiary),
                        const SizedBox(height: 12),
                        Text(
                          _searchQuery.isNotEmpty
                              ? 'Tidak ditemukan "$_searchQuery"'
                              : _stockMode == 'recipe'
                                  ? 'Belum ada bahan baku'
                                  : 'Belum ada produk dengan stok aktif',
                          style: const TextStyle(
                              color: AppColors.textSecondary),
                        ),
                      ],
                    ),
                  );
                }

                return RefreshIndicator(
                  onRefresh: _refresh,
                  child: ListView.builder(
                    padding: const EdgeInsets.all(16),
                    itemCount: filtered.length,
                    itemBuilder: (ctx, i) {
                      final item = filtered[i];
                      return _RestockTile(
                        item: item,
                        onTap: () => _openRestockSheet(item),
                      );
                    },
                  ),
                );
              },
            ),
          ),
        ],
      );

    if (widget.embedded) {
      return body;
    }
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: const Text('Restock Stok'),
        backgroundColor: AppColors.surface,
        foregroundColor: AppColors.textPrimary,
        elevation: 0,
        iconTheme: const IconThemeData(color: AppColors.textPrimary),
      ),
      body: body,
    );
  }
}

class _RestockItem {
  final String id;
  final String name;
  final double currentStock;
  final String unit;
  final bool isRecipe;
  final int rowVersion;
  /// Snapshot harga beli terakhir (nullable, hanya untuk simple-mode product).
  /// Recipe-mode pakai ingredient.buy_price flow yang lain — tidak relevan disini.
  final double? currentBuyPrice;

  _RestockItem({
    required this.id,
    required this.name,
    required this.currentStock,
    required this.unit,
    required this.isRecipe,
    this.rowVersion = 0,
    this.currentBuyPrice,
  });
}

class _RestockTile extends StatelessWidget {
  final _RestockItem item;
  final VoidCallback onTap;

  const _RestockTile({required this.item, required this.onTap});

  @override
  Widget build(BuildContext context) {
    final stockStr = item.currentStock % 1 == 0
        ? item.currentStock.toInt().toString()
        : item.currentStock.toStringAsFixed(1);
    final lowStock = item.currentStock <= 0;

    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
      child: InkWell(
        borderRadius: BorderRadius.circular(10),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Row(
            children: [
              Container(
                width: 40,
                height: 40,
                decoration: BoxDecoration(
                  color: AppColors.primary.withOpacity(0.08),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Icon(
                  item.isRecipe ? LucideIcons.package : LucideIcons.box,
                  color: AppColors.primary,
                  size: 18,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      item.name,
                      style: const TextStyle(
                          fontWeight: FontWeight.w600, fontSize: 14),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      'Stok sekarang: $stockStr ${item.unit}',
                      style: TextStyle(
                        fontSize: 12,
                        color: lowStock
                            ? AppColors.error
                            : AppColors.textSecondary,
                        fontWeight:
                            lowStock ? FontWeight.w600 : FontWeight.normal,
                      ),
                    ),
                  ],
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(
                    horizontal: 10, vertical: 6),
                decoration: BoxDecoration(
                  color: AppColors.primary,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(LucideIcons.plus, size: 14, color: Colors.white),
                    SizedBox(width: 4),
                    Text(
                      'Restock',
                      style: TextStyle(
                          color: Colors.white,
                          fontSize: 12,
                          fontWeight: FontWeight.w600),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _RestockSheet extends ConsumerStatefulWidget {
  final _RestockItem item;
  const _RestockSheet({required this.item});

  @override
  ConsumerState<_RestockSheet> createState() => _RestockSheetState();
}

class _RestockSheetState extends ConsumerState<_RestockSheet> {
  final _qtyController = TextEditingController();
  final _notesController = TextEditingController();
  final _buyPriceController = TextEditingController();
  final _qtyFocus = FocusNode();
  bool _submitting = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    // Pre-fill harga beli dengan snapshot terakhir kalau ada — user
    // tinggal konfirmasi atau ubah. Skip untuk recipe (endpoint lain).
    if (!widget.item.isRecipe && widget.item.currentBuyPrice != null) {
      final bp = widget.item.currentBuyPrice!;
      _buyPriceController.text = bp % 1 == 0
          ? bp.toInt().toString()
          : bp.toStringAsFixed(2);
    }
    // Auto-focus + select all on open biar gampang ngetik di mobile.
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _qtyFocus.requestFocus();
    });
  }

  @override
  void dispose() {
    _qtyController.dispose();
    _notesController.dispose();
    _buyPriceController.dispose();
    _qtyFocus.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final raw = _qtyController.text.trim();
    final qty = double.tryParse(raw.replaceAll(',', '.'));
    if (qty == null || qty <= 0) {
      setState(() => _error = 'Jumlah tidak valid');
      return;
    }

    // Parse harga beli (opsional). Skip untuk recipe — endpoint ingredient
    // tidak terima unit_buy_price field di body schema.
    // Input restricted ke digitsOnly (integer Rupiah) — gak ada decimal ambig.
    double? unitBuyPrice;
    if (!widget.item.isRecipe) {
      final bpRaw = _buyPriceController.text.trim();
      if (bpRaw.isNotEmpty) {
        final parsed = int.tryParse(bpRaw);
        if (parsed == null || parsed < 0) {
          setState(() => _error = 'Harga beli tidak valid');
          return;
        }
        unitBuyPrice = parsed.toDouble();
      }
    }

    setState(() {
      _submitting = true;
      _error = null;
    });

    try {
      final cache = SessionCache.instance;
      final outletId = cache.outletId;
      if (outletId == null) {
        setState(() {
          _error = 'Outlet belum tersedia — silakan login ulang';
          _submitting = false;
        });
        return;
      }

      final dio = Dio(BaseOptions(
        baseUrl: AppConfig.apiV1,
        connectTimeout: const Duration(seconds: 15),
        receiveTimeout: const Duration(seconds: 15),
      ));

      final path = widget.item.isRecipe
          ? '/ingredients/${widget.item.id}/restock'
          : '/products/${widget.item.id}/restock';

      await dio.post(
        path,
        options: Options(headers: cache.authHeaders),
        data: {
          'outlet_id': outletId,
          'quantity': widget.item.isRecipe ? qty : qty.toInt(),
          if (_notesController.text.trim().isNotEmpty)
            'notes': _notesController.text.trim(),
          if (unitBuyPrice != null) 'unit_buy_price': unitBuyPrice,
        },
      );

      // Trigger sync agar local DB catch up dengan backend state
      try {
        await ref.read(syncServiceProvider).sync();
      } catch (_) {}

      if (mounted) Navigator.pop(context, true);
    } on DioException catch (e) {
      final raw = e.response?.data?['detail'];
      String msg;
      if (raw is String) {
        msg = raw;
      } else if (raw is Map) {
        msg = raw['message']?.toString() ?? 'Gagal menambah stok';
      } else {
        msg = 'Gagal menambah stok';
      }
      setState(() {
        _error = msg;
        _submitting = false;
      });
    } catch (_) {
      setState(() {
        _error = 'Koneksi bermasalah. Coba lagi.';
        _submitting = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final bottomInset = MediaQuery.of(context).viewInsets.bottom;
    final stockStr = widget.item.currentStock % 1 == 0
        ? widget.item.currentStock.toInt().toString()
        : widget.item.currentStock.toStringAsFixed(1);

    return Padding(
      padding: EdgeInsets.only(bottom: bottomInset),
      child: Container(
        decoration: const BoxDecoration(
          color: AppColors.surface,
          borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              margin: const EdgeInsets.only(top: 12),
              width: 40,
              height: 4,
              decoration: BoxDecoration(
                color: AppColors.border,
                borderRadius: BorderRadius.circular(2),
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 16, 20, 20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(widget.item.name,
                                style: const TextStyle(
                                    fontWeight: FontWeight.bold, fontSize: 16)),
                            const SizedBox(height: 4),
                            Text(
                              'Stok sekarang: $stockStr ${widget.item.unit}',
                              style: const TextStyle(
                                  color: AppColors.textSecondary, fontSize: 13),
                            ),
                          ],
                        ),
                      ),
                      IconButton(
                        onPressed: _submitting
                            ? null
                            : () => Navigator.pop(context, false),
                        icon: const Icon(LucideIcons.x, size: 20),
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),
                  Text(
                    'Jumlah yang diterima (${widget.item.unit})',
                    style: const TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                        color: AppColors.textSecondary),
                  ),
                  const SizedBox(height: 6),
                  TextField(
                    controller: _qtyController,
                    focusNode: _qtyFocus,
                    keyboardType: widget.item.isRecipe
                        ? const TextInputType.numberWithOptions(decimal: true)
                        : TextInputType.number,
                    inputFormatters: widget.item.isRecipe
                        ? [
                            FilteringTextInputFormatter.allow(
                                RegExp(r'[0-9.,]')),
                          ]
                        : [FilteringTextInputFormatter.digitsOnly],
                    onTap: () => _qtyController.selection = TextSelection(
                        baseOffset: 0,
                        extentOffset: _qtyController.text.length),
                    decoration: InputDecoration(
                      hintText: '0',
                      suffixText: widget.item.unit,
                      filled: true,
                      fillColor: AppColors.surfaceVariant,
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(10),
                        borderSide: BorderSide.none,
                      ),
                      contentPadding: const EdgeInsets.symmetric(
                          horizontal: 14, vertical: 14),
                    ),
                    style: const TextStyle(
                        fontSize: 18, fontWeight: FontWeight.w600),
                  ),
                  // Harga Beli — hanya untuk simple-mode product. Recipe
                  // mode (ingredient) pakai field buy_price di endpoint
                  // ingredient sendiri, bukan disini.
                  if (!widget.item.isRecipe) ...[
                    const SizedBox(height: 12),
                    const Text(
                      'Harga Beli per Unit (opsional)',
                      style: TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.w600,
                          color: AppColors.textSecondary),
                    ),
                    const SizedBox(height: 6),
                    TextField(
                      controller: _buyPriceController,
                      // Integer Rupiah only — Indonesian cafe gak input cents.
                      // Hindari ambigu "8.500" (= 8.5 atau 8500?) dgn restrict
                      // ke digits saja. User ngetik 8500, jelas = Rp 8.500.
                      keyboardType: TextInputType.number,
                      inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                      decoration: InputDecoration(
                        hintText: '0',
                        prefixText: 'Rp ',
                        helperText:
                            'Diisi = update modal & track margin. Kosong = harga modal lama tetap.',
                        helperMaxLines: 2,
                        helperStyle: const TextStyle(
                            fontSize: 11, color: AppColors.textTertiary),
                        filled: true,
                        fillColor: AppColors.surfaceVariant,
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(10),
                          borderSide: BorderSide.none,
                        ),
                        contentPadding: const EdgeInsets.symmetric(
                            horizontal: 14, vertical: 12),
                      ),
                      style: const TextStyle(fontSize: 15),
                    ),
                  ],
                  const SizedBox(height: 12),
                  const Text(
                    'Catatan (opsional)',
                    style: TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                        color: AppColors.textSecondary),
                  ),
                  const SizedBox(height: 6),
                  TextField(
                    controller: _notesController,
                    maxLines: 2,
                    decoration: InputDecoration(
                      hintText: 'Misal: terima dari supplier A',
                      filled: true,
                      fillColor: AppColors.surfaceVariant,
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(10),
                        borderSide: BorderSide.none,
                      ),
                      contentPadding: const EdgeInsets.symmetric(
                          horizontal: 14, vertical: 12),
                    ),
                  ),
                  if (_error != null) ...[
                    const SizedBox(height: 12),
                    Container(
                      padding: const EdgeInsets.all(10),
                      decoration: BoxDecoration(
                        color: AppColors.error.withOpacity(0.1),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Row(
                        children: [
                          const Icon(LucideIcons.alertCircle,
                              size: 14, color: AppColors.error),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              _error!,
                              style: const TextStyle(
                                  color: AppColors.error, fontSize: 12),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                  const SizedBox(height: 20),
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton(
                      onPressed: _submitting ? null : _submit,
                      style: ElevatedButton.styleFrom(
                        backgroundColor: AppColors.primary,
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(vertical: 14),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(10),
                        ),
                      ),
                      child: _submitting
                          ? const SizedBox(
                              width: 18,
                              height: 18,
                              child: CircularProgressIndicator(
                                  strokeWidth: 2, color: Colors.white),
                            )
                          : const Text(
                              'Simpan Restock',
                              style: TextStyle(
                                  fontWeight: FontWeight.w600, fontSize: 14),
                            ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

