import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:lucide_icons/lucide_icons.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/sync/sync_provider.dart';
import '../../../products/providers/products_provider.dart';
import '../../../dashboard/providers/dashboard_provider.dart';
import '../../../orders/providers/orders_provider.dart';
import '../../providers/cart_provider.dart';
import '../widgets/product_card.dart';
import '../widgets/cart_panel.dart';
import '../../../products/presentation/widgets/product_detail_sheet.dart';

class PosPage extends ConsumerStatefulWidget {
  const PosPage({super.key});

  @override
  ConsumerState<PosPage> createState() => _PosPageState();
}

class _PosPageState extends ConsumerState<PosPage> {
  String _selectedCategoryId = 'all';
  String _searchQuery = '';
  bool _isOffline = false;
  StreamSubscription<List<ConnectivityResult>>? _connectivitySub;
  final _searchController = TextEditingController();
  late Timer _clockTimer;
  String _timeString = '';

  @override
  void initState() {
    super.initState();
    _updateClock();
    _clockTimer = Timer.periodic(const Duration(minutes: 1), (_) => _updateClock());
    _initConnectivity();
    _connectivitySub =
        Connectivity().onConnectivityChanged.listen(_updateConnectionStatus);
  }

  void _updateClock() {
    final now = DateTime.now();
    final days = ['Min', 'Sen', 'Sel', 'Rab', 'Kam', 'Jum', 'Sab'];
    final months = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agt', 'Sep', 'Okt', 'Nov', 'Des'];
    setState(() {
      _timeString =
          '${days[now.weekday % 7]}, ${now.day} ${months[now.month - 1]} · ${now.hour.toString().padLeft(2, '0')}:${now.minute.toString().padLeft(2, '0')}';
    });
  }

  Future<void> _initConnectivity() async {
    try {
      final result = await Connectivity().checkConnectivity();
      if (mounted) _updateConnectionStatus(result);
    } catch (_) {}
  }

  void _updateConnectionStatus(List<ConnectivityResult> result) {
    final offline = result.contains(ConnectivityResult.none) || result.isEmpty;
    if (_isOffline && !offline) {
      ref.read(syncServiceProvider).sync().then((_) {
        // Setelah sync selesai, invalidate semua provider supaya data fresh
        ref.invalidate(dashboardProvider);
        ref.invalidate(ordersProvider);
        ref.invalidate(productsProvider);
      }).catchError((_) {});
    }
    if (mounted) setState(() => _isOffline = offline);
  }

  @override
  void dispose() {
    _connectivitySub?.cancel();
    _searchController.dispose();
    _clockTimer.cancel();
    super.dispose();
  }

  void _openCartSheet(BuildContext context) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => DraggableScrollableSheet(
        initialChildSize: 0.85,
        maxChildSize: 0.95,
        minChildSize: 0.4,
        builder: (_, controller) => Container(
          decoration: const BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
          ),
          child: Column(
            children: [
              const SizedBox(height: 12),
              Container(
                width: 36,
                height: 4,
                decoration: BoxDecoration(
                  color: AppColors.border,
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
              const SizedBox(height: 8),
              const Expanded(child: CartPanel()),
            ],
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final isWide = MediaQuery.of(context).size.shortestSide >= 600;
    final productsAsync = ref.watch(productsProvider);
    final cart = ref.watch(cartProvider);
    final itemCount = cart.items.fold<int>(0, (sum, item) => sum + item.qty);

    return Scaffold(
      backgroundColor: const Color(0xFFF0F2F5),
      body: Column(
        children: [
          if (_isOffline)
            Container(
              width: double.infinity,
              color: AppColors.warning,
              padding: const EdgeInsets.symmetric(vertical: 6),
              child: const Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(LucideIcons.wifiOff, size: 14, color: Colors.white),
                  SizedBox(width: 6),
                  Text(
                    'Mode Offline — Transaksi disimpan & sync saat online',
                    style: TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.w600,
                        fontSize: 12),
                  ),
                ],
              ),
            ),
          Expanded(
            child: isWide
                ? _buildTabletLayout(productsAsync)
                : _buildPhoneLayout(context, productsAsync),
          ),
        ],
      ),
      floatingActionButton: isWide
          ? null
          : FloatingActionButton.extended(
              onPressed: () => _openCartSheet(context),
              icon: Badge(
                label: itemCount > 0 ? Text('$itemCount') : null,
                isLabelVisible: itemCount > 0,
                backgroundColor: Colors.white,
                textColor: AppColors.primary,
                child: const Icon(LucideIcons.shoppingCart),
              ),
              label: itemCount > 0
                  ? Text('Keranjang ($itemCount)')
                  : const Text('Keranjang'),
              backgroundColor: AppColors.primary,
              elevation: 4,
            ),
    );
  }

  Widget _buildTabletLayout(AsyncValue<List<ProductModel>> productsAsync) {
    return Row(
      children: [
        // Left: product area
        Expanded(
          flex: 7,
          child: Column(
            children: [
              _buildHeader(isWide: true),
              _buildCategories(productsAsync),
              Expanded(child: _buildProductGrid(productsAsync, crossAxisCount: 4)),
            ],
          ),
        ),
        // Right: cart
        Container(
          width: 380,
          decoration: BoxDecoration(
            color: Colors.white,
            boxShadow: [
              BoxShadow(
                  color: Colors.black.withOpacity(0.06),
                  blurRadius: 16,
                  offset: const Offset(-2, 0)),
            ],
          ),
          child: const CartPanel(),
        ),
      ],
    );
  }

  Widget _buildPhoneLayout(
      BuildContext context, AsyncValue<List<ProductModel>> productsAsync) {
    return Column(
      children: [
        _buildHeader(isWide: false),
        _buildCategories(productsAsync),
        Expanded(child: _buildProductGrid(productsAsync, crossAxisCount: 2)),
      ],
    );
  }

  Widget _buildHeader({required bool isWide}) {
    return Container(
      decoration: const BoxDecoration(
        color: Colors.white,
        border: Border(bottom: BorderSide(color: AppColors.border, width: 1)),
      ),
      padding: EdgeInsets.only(
        top: isWide ? 0 : MediaQuery.of(context).padding.top,
      ),
      child: SafeArea(
        bottom: false,
        child: Padding(
          padding: EdgeInsets.symmetric(
            horizontal: isWide ? 20 : 16,
            vertical: isWide ? 14 : 10,
          ),
          child: Row(
            children: [
              // Brand mark
              Container(
                width: 36,
                height: 36,
                decoration: BoxDecoration(
                  color: AppColors.primary,
                  borderRadius: BorderRadius.circular(10),
                ),
                child: const Icon(LucideIcons.store, color: Colors.white, size: 18),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Kasira POS',
                      style: TextStyle(
                        fontSize: isWide ? 16 : 14,
                        fontWeight: FontWeight.bold,
                        color: AppColors.textPrimary,
                      ),
                    ),
                    if (_timeString.isNotEmpty)
                      Text(
                        _timeString,
                        style: const TextStyle(
                          fontSize: 11,
                          color: AppColors.textTertiary,
                        ),
                      ),
                  ],
                ),
              ),
              // Search bar
              Container(
                width: isWide ? 260 : 150,
                height: 38,
                decoration: BoxDecoration(
                  color: const Color(0xFFF0F2F5),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: TextField(
                  controller: _searchController,
                  decoration: const InputDecoration(
                    hintText: 'Cari produk...',
                    hintStyle: TextStyle(color: AppColors.textTertiary, fontSize: 13),
                    prefixIcon: Icon(LucideIcons.search,
                        size: 16, color: AppColors.textTertiary),
                    border: InputBorder.none,
                    enabledBorder: InputBorder.none,
                    focusedBorder: InputBorder.none,
                    contentPadding: EdgeInsets.symmetric(vertical: 10),
                    isDense: true,
                  ),
                  style: const TextStyle(fontSize: 13),
                  onChanged: (val) =>
                      setState(() => _searchQuery = val.toLowerCase()),
                ),
              ),
              const SizedBox(width: 6),
              SizedBox(
                width: 36,
                height: 36,
                child: IconButton(
                  padding: EdgeInsets.zero,
                  onPressed: () {
                    _searchController.clear();
                    setState(() => _searchQuery = '');
                    ref.read(productsProvider.notifier).refresh();
                  },
                  icon: const Icon(LucideIcons.refreshCw,
                      color: AppColors.textSecondary, size: 18),
                  tooltip: 'Refresh',
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildCategories(AsyncValue<List<ProductModel>> productsAsync) {
    final categories = <String, String>{'all': 'Semua'};
    productsAsync.whenData((products) {
      for (final p in products) {
        if (p.categoryId != null && p.categoryName != null) {
          categories[p.categoryId!] = p.categoryName!;
        }
      }
    });

    return Container(
      height: 50,
      color: Colors.white,
      padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 16),
      child: ListView(
        scrollDirection: Axis.horizontal,
        children: categories.entries.map((entry) {
          final isSelected = _selectedCategoryId == entry.key;
          return Padding(
            padding: const EdgeInsets.only(right: 8),
            child: GestureDetector(
              onTap: () {
                setState(() => _selectedCategoryId = entry.key);
              },
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 150),
                padding:
                    const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
                decoration: BoxDecoration(
                  color: isSelected ? AppColors.primary : Colors.white,
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(
                    color: isSelected ? AppColors.primary : AppColors.border,
                  ),
                  boxShadow: isSelected
                      ? [
                          BoxShadow(
                            color: AppColors.primary.withOpacity(0.25),
                            blurRadius: 6,
                            offset: const Offset(0, 2),
                          )
                        ]
                      : [],
                ),
                child: Text(
                  entry.value,
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight:
                        isSelected ? FontWeight.bold : FontWeight.w500,
                    color: isSelected ? Colors.white : AppColors.textSecondary,
                  ),
                ),
              ),
            ),
          );
        }).toList(),
      ),
    );
  }

  Widget _buildProductGrid(
    AsyncValue<List<ProductModel>> productsAsync, {
    required int crossAxisCount,
  }) {
    return productsAsync.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (err, _) => Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              padding: const EdgeInsets.all(20),
              decoration: const BoxDecoration(
                color: AppColors.surfaceVariant,
                shape: BoxShape.circle,
              ),
              child: const Icon(LucideIcons.wifiOff,
                  size: 32, color: AppColors.textTertiary),
            ),
            const SizedBox(height: 16),
            const Text('Gagal memuat produk',
                style: TextStyle(color: AppColors.textSecondary)),
            const SizedBox(height: 12),
            ElevatedButton.icon(
              onPressed: () => ref.read(productsProvider.notifier).refresh(),
              icon: const Icon(LucideIcons.refreshCw, size: 16),
              label: const Text('Coba lagi'),
              style: ElevatedButton.styleFrom(
                backgroundColor: AppColors.primary,
                shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(10)),
              ),
            ),
          ],
        ),
      ),
      data: (products) {
        final categoryFiltered = _selectedCategoryId == 'all'
            ? products
            : products.where((p) => p.categoryId == _selectedCategoryId).toList();
        final filtered = _searchQuery.isEmpty
            ? categoryFiltered
            : categoryFiltered
                .where((p) => p.name.toLowerCase().contains(_searchQuery))
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
                      ? 'Produk "$_searchQuery" tidak ditemukan'
                      : 'Belum ada produk',
                  style:
                      const TextStyle(color: AppColors.textSecondary),
                ),
              ],
            ),
          );
        }

        return Padding(
          padding: const EdgeInsets.fromLTRB(12, 12, 12, 80),
          child: GridView.builder(
            gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
              crossAxisCount: crossAxisCount,
              childAspectRatio: crossAxisCount == 2 ? 0.82 : 0.72,
              crossAxisSpacing: 10,
              mainAxisSpacing: 10,
            ),
            itemCount: filtered.length,
            itemBuilder: (context, index) {
              final product = filtered[index];
              return ProductCard(
                name: product.name,
                price: product.price,
                stock: product.stock,
                stockEnabled: product.stockEnabled,
                imageUrl: product.imageUrl ?? '',
                isBestSeller: product.isBestSeller,
                onLongPress: () => ProductDetailSheet.show(
                  context,
                  productId: product.id,
                  productName: product.name,
                  sellingPrice: product.price,
                ),
                onTap: () {
                  ref.read(cartProvider.notifier).addItem(CartItem(
                        productId: product.id,
                        name: product.name,
                        price: product.price,
                        stockQty: product.stockEnabled ? product.stock.toDouble() : null,
                      ));
                  if (MediaQuery.of(context).size.width < 700) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(
                        content: Row(
                          children: [
                            const Icon(LucideIcons.check,
                                color: Colors.white, size: 16),
                            const SizedBox(width: 8),
                            Text('${product.name} ditambahkan'),
                          ],
                        ),
                        duration: const Duration(milliseconds: 900),
                        behavior: SnackBarBehavior.floating,
                        backgroundColor: AppColors.success,
                        shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(10)),
                        margin: const EdgeInsets.fromLTRB(16, 0, 16, 90),
                      ),
                    );
                  }
                },
              );
            },
          ),
        );
      },
    );
  }
}
