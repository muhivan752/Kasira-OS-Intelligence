import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
import 'package:intl/intl.dart';
import 'package:cached_network_image/cached_network_image.dart';
import '../../../../core/theme/kasira_ds.dart';
import '../../../../core/database/app_database.dart';
import '../../../../core/sync/sync_provider.dart';
import '../../../../core/services/session_cache.dart';
import '../../providers/products_provider.dart';
import '../widgets/product_detail_sheet.dart';
import 'restock_page.dart';
import 'margin_report_page.dart';

class ProductManagementPage extends ConsumerStatefulWidget {
  const ProductManagementPage({super.key});

  @override
  ConsumerState<ProductManagementPage> createState() => _ProductManagementPageState();
}

class _ProductManagementPageState extends ConsumerState<ProductManagementPage> {
  String _searchQuery = '';
  final _searchController = TextEditingController();
  final _currency = NumberFormat.currency(locale: 'id_ID', symbol: 'Rp ', decimalDigits: 0);
  int _lowStockCount = 0;

  @override
  void initState() {
    super.initState();
    _loadLowStockCount();
  }

  Future<void> _loadLowStockCount() async {
    final db = ref.read(databaseProvider);
    final outletId = SessionCache.instance.outletId ?? '';
    final stockMode = SessionCache.instance.stockMode ?? 'simple';

    int count = 0;
    try {
      if (stockMode == 'recipe' && outletId.isNotEmpty) {
        final stocks = await (db.select(db.outletStocks)
              ..where((os) => os.outletId.equals(outletId))
              ..where((os) => os.isDeleted.equals(false)))
            .get();
        count = stocks.where((s) => s.computedStock <= 0).length;
      } else {
        final products = await (db.select(db.products)
              ..where((p) => p.isDeleted.equals(false))
              ..where((p) => p.stockEnabled.equals(true)))
            .get();
        count = products.where((p) => p.stockQty <= 0).length;
      }
    } catch (_) {
      count = 0; // fail-silent — badge hilang kalau query gagal, bukan crash
    }

    if (mounted) setState(() => _lowStockCount = count);
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _toggleAvailability(ProductModel product) async {
    try {
      await ref.read(productsProvider.notifier).toggleAvailability(
            product.id,
            !product.isAvailable,
            product.rowVersion,
          );
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Gagal mengubah status: $e'),
            backgroundColor: KasiraDS.danger,
            behavior: SnackBarBehavior.floating,
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final productsAsync = ref.watch(productsProvider);

    return DefaultTabController(
      length: 3,
      child: Scaffold(
        backgroundColor: KasiraDS.bgBase,
        body: Column(
          children: [
            // Header
            Container(
              padding: const EdgeInsets.all(20),
              color: KasiraDS.surfaceCard,
              child: Row(
                children: [
                  Text('Produk & Stok',
                      style: Theme.of(context).textTheme.headlineMedium),
                  const Spacer(),
                  SizedBox(
                    width: 260,
                    child: TextField(
                      controller: _searchController,
                      decoration: InputDecoration(
                        hintText: 'Cari produk...',
                        prefixIcon: const Icon(LucideIcons.search,
                            color: KasiraDS.textMuted, size: 18),
                        filled: true,
                        fillColor: KasiraDS.surfaceSunken,
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(10),
                          borderSide: BorderSide.none,
                        ),
                        contentPadding:
                            const EdgeInsets.symmetric(vertical: 10),
                        isDense: true,
                      ),
                      onChanged: (val) =>
                          setState(() => _searchQuery = val.toLowerCase()),
                    ),
                  ),
                  const SizedBox(width: 8),
                  IconButton(
                    onPressed: () {
                      ref.read(productsProvider.notifier).refresh();
                      _loadLowStockCount();
                    },
                    icon: const Icon(LucideIcons.refreshCw,
                        color: KasiraDS.textMuted, size: 18),
                    tooltip: 'Refresh',
                  ),
                ],
              ),
            ),

            // TabBar — Produk | Stok (dengan badge low-stock kalau ada)
            Material(
              color: KasiraDS.surfaceCard,
              child: TabBar(
                labelColor: KasiraDS.brandPrimary,
                unselectedLabelColor: KasiraDS.textMuted,
                indicatorColor: KasiraDS.brandPrimary,
                indicatorWeight: 2.5,
                labelStyle: const TextStyle(
                    fontWeight: FontWeight.w600, fontSize: 13),
                unselectedLabelStyle: const TextStyle(fontSize: 13),
                tabs: [
                  const Tab(height: 40, text: 'Produk'),
                  Tab(
                    height: 40,
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Text('Stok'),
                        if (_lowStockCount > 0) ...[
                          const SizedBox(width: 6),
                          Container(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 6, vertical: 2),
                            decoration: BoxDecoration(
                              color: KasiraDS.danger,
                              borderRadius: BorderRadius.circular(10),
                            ),
                            child: Text(
                              '$_lowStockCount',
                              style: const TextStyle(
                                color: Colors.white,
                                fontSize: 10,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ),
                        ],
                      ],
                    ),
                  ),
                  const Tab(height: 40, text: 'Untung-Rugi'),
                ],
              ),
            ),

            // Content
            Expanded(
              child: TabBarView(
                physics: const ClampingScrollPhysics(),
                children: [
                  _buildProductsTab(productsAsync),
                  const RestockPage(embedded: true),
                  const MarginReportPage(embedded: true),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildProductsTab(AsyncValue<List<ProductModel>> productsAsync) {
    return productsAsync.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (err, _) => Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(LucideIcons.wifiOff,
                size: 40, color: KasiraDS.textMuted),
            const SizedBox(height: 12),
            const Text('Gagal memuat produk',
                style: TextStyle(color: KasiraDS.textMuted)),
            const SizedBox(height: 12),
            ElevatedButton.icon(
              onPressed: () => ref.read(productsProvider.notifier).refresh(),
              icon: const Icon(LucideIcons.refreshCw, size: 16),
              label: const Text('Coba lagi'),
              style: ElevatedButton.styleFrom(
                backgroundColor: KasiraDS.brandPrimary,
              ),
            ),
          ],
        ),
      ),
      data: (products) {
        final filtered = _searchQuery.isEmpty
            ? products
            : products
                .where((p) => p.name.toLowerCase().contains(_searchQuery))
                .toList();

        if (filtered.isEmpty) {
          return Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const Icon(LucideIcons.packageSearch,
                    size: 40, color: KasiraDS.textMuted),
                const SizedBox(height: 12),
                Text(
                  _searchQuery.isNotEmpty
                      ? 'Produk "$_searchQuery" tidak ditemukan'
                      : 'Belum ada produk',
                  style: const TextStyle(color: KasiraDS.textMuted),
                ),
              ],
            ),
          );
        }

        return ListView.builder(
          padding: const EdgeInsets.all(20),
          itemCount: filtered.length,
          itemBuilder: (context, index) {
            final product = filtered[index];
            return _ProductTile(
              product: product,
              currency: _currency,
              onToggle: () async => _toggleAvailability(product),
              onTap: () => ProductDetailSheet.show(
                context,
                productId: product.id,
                productName: product.name,
                sellingPrice: product.price,
              ),
            );
          },
        );
      },
    );
  }
}

class _ProductTile extends StatefulWidget {
  final ProductModel product;
  final NumberFormat currency;
  final Future<void> Function() onToggle;
  final VoidCallback? onTap;

  const _ProductTile({
    required this.product,
    required this.currency,
    required this.onToggle,
    this.onTap,
  });

  @override
  State<_ProductTile> createState() => _ProductTileState();
}

class _ProductTileState extends State<_ProductTile> {
  bool _isToggling = false;

  @override
  Widget build(BuildContext context) {
    final product = widget.product;
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: InkWell(
        onTap: widget.onTap,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
          children: [
            // Product image / icon
            Container(
              width: 56,
              height: 56,
              decoration: BoxDecoration(
                color: KasiraDS.surfaceSunken,
                borderRadius: BorderRadius.circular(10),
              ),
              child: product.imageUrl != null && product.imageUrl!.isNotEmpty
                  ? ClipRRect(
                      borderRadius: BorderRadius.circular(10),
                      child: CachedNetworkImage(
                        // P1 Quick Win #8: pre-fix Image.network = redownload
                        // tiap buka page (50 produk = 50 download). Post-fix
                        // disk+memory cache via cached_network_image package.
                        imageUrl: product.imageUrl!,
                        fit: BoxFit.cover,
                        errorWidget: (_, __, ___) => const Icon(
                            LucideIcons.coffee,
                            color: KasiraDS.textMuted),
                        placeholder: (_, __) => const SizedBox.shrink(),
                      ),
                    )
                  : const Icon(LucideIcons.coffee,
                      color: KasiraDS.textMuted),
            ),
            const SizedBox(width: 16),

            // Name + category
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    product.name,
                    style: const TextStyle(
                        fontWeight: FontWeight.bold, fontSize: 15),
                  ),
                  const SizedBox(height: 2),
                  if (product.categoryName != null)
                    Text(
                      product.categoryName!,
                      style: const TextStyle(
                          color: KasiraDS.textMuted, fontSize: 12),
                    ),
                  const SizedBox(height: 2),
                  Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 6, vertical: 2),
                        decoration: BoxDecoration(
                          color: product.stock > 0
                              ? KasiraDS.success.withOpacity(0.1)
                              : KasiraDS.danger.withOpacity(0.1),
                          borderRadius: BorderRadius.circular(6),
                        ),
                        child: Text(
                          'Stok: ${product.stock}',
                          style: TextStyle(
                            fontSize: 11,
                            color: product.stock > 0
                                ? KasiraDS.success
                                : KasiraDS.danger,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),

            // Price + margin (subtle, owner-context only — POS card sengaja
            // tidak menampilkan margin agar tidak terlihat customer/cashier).
            Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  widget.currency.format(product.price),
                  style: const TextStyle(
                      fontWeight: FontWeight.bold, fontSize: 14),
                ),
                if (product.margin != null && product.marginPct != null) ...[
                  const SizedBox(height: 2),
                  Text(
                    'Margin ${widget.currency.format(product.margin)} (${product.marginPct!.toStringAsFixed(0)}%)',
                    style: TextStyle(
                      fontSize: 10,
                      color: product.margin! < 0
                          ? KasiraDS.danger
                          : KasiraDS.textMuted,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ],
              ],
            ),
            const SizedBox(width: 20),

            // Toggle
            Column(
              children: [
                Text(
                  product.isAvailable ? 'Tersedia' : 'Nonaktif',
                  style: TextStyle(
                    color: product.isAvailable
                        ? KasiraDS.success
                        : KasiraDS.danger,
                    fontWeight: FontWeight.bold,
                    fontSize: 11,
                  ),
                ),
                const SizedBox(height: 4),
                _isToggling
                    ? const SizedBox(
                        width: 36,
                        height: 24,
                        child: Center(
                          child: SizedBox(
                            width: 16,
                            height: 16,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          ),
                        ),
                      )
                    : Switch(
                        value: product.isAvailable,
                        onChanged: (_) async {
                          setState(() => _isToggling = true);
                          await widget.onToggle();
                          if (mounted) setState(() => _isToggling = false);
                        },
                        activeColor: KasiraDS.success,
                      ),
              ],
            ),
          ],
        ),
      ),
      ),
    );
  }
}
