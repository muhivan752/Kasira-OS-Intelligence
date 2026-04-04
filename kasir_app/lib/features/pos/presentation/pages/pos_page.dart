import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:lucide_icons/lucide_icons.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/sync/sync_provider.dart';
import '../../../products/providers/products_provider.dart';
import '../../providers/cart_provider.dart';
import '../widgets/product_card.dart';
import '../widgets/cart_panel.dart';

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

  @override
  void initState() {
    super.initState();
    _initConnectivity();
    _connectivitySub = Connectivity().onConnectivityChanged.listen(_updateConnectionStatus);
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
      ref.read(syncServiceProvider).sync().catchError((_) {});
    }
    if (mounted) setState(() => _isOffline = offline);
  }

  @override
  void dispose() {
    _connectivitySub?.cancel();
    _searchController.dispose();
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
            borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
          ),
          child: Column(
            children: [
              const SizedBox(height: 8),
              Container(
                width: 40, height: 4,
                decoration: BoxDecoration(
                  color: Colors.grey.shade300,
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
    final isWide = MediaQuery.of(context).size.width >= 700;
    final productsAsync = ref.watch(productsProvider);
    final cart = ref.watch(cartProvider);
    final itemCount = cart.items.fold<int>(0, (sum, item) => sum + item.qty);

    return Scaffold(
      backgroundColor: AppColors.background,
      body: Column(
        children: [
          if (_isOffline)
            Container(
              width: double.infinity,
              color: AppColors.error,
              padding: const EdgeInsets.symmetric(vertical: 8),
              child: const Text(
                'Mode Offline — Transaksi tersimpan, sync saat online',
                textAlign: TextAlign.center,
                style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 12),
              ),
            ),
          Expanded(
            child: isWide
                ? _buildTabletLayout(productsAsync)
                : _buildPhoneLayout(context, productsAsync),
          ),
        ],
      ),
      // Phone: floating cart button
      floatingActionButton: isWide
          ? null
          : FloatingActionButton.extended(
              onPressed: () => _openCartSheet(context),
              icon: Badge(
                label: itemCount > 0 ? Text('$itemCount') : null,
                isLabelVisible: itemCount > 0,
                child: const Icon(LucideIcons.shoppingCart),
              ),
              label: const Text('Keranjang'),
              backgroundColor: AppColors.primary,
            ),
    );
  }

  Widget _buildTabletLayout(AsyncValue<List<ProductModel>> productsAsync) {
    return Row(
      children: [
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
        Container(
          width: 400,
          decoration: const BoxDecoration(
            color: Colors.white,
            border: Border(left: BorderSide(color: AppColors.border)),
          ),
          child: const CartPanel(),
        ),
      ],
    );
  }

  Widget _buildPhoneLayout(BuildContext context, AsyncValue<List<ProductModel>> productsAsync) {
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
      padding: EdgeInsets.symmetric(
        horizontal: isWide ? 24 : 16,
        vertical: isWide ? 16 : 12,
      ),
      color: Colors.white,
      child: SafeArea(
        bottom: false,
        child: Row(
          children: [
            const Icon(LucideIcons.store, color: AppColors.primary),
            const SizedBox(width: 12),
            Text('Kasir', style: TextStyle(fontSize: isWide ? 18 : 16, fontWeight: FontWeight.bold)),
            const Spacer(),
            Container(
              width: isWide ? 280 : 160,
              height: 40,
              decoration: BoxDecoration(
                color: AppColors.surfaceVariant,
                borderRadius: BorderRadius.circular(8),
              ),
              child: TextField(
                controller: _searchController,
                decoration: const InputDecoration(
                  hintText: 'Cari produk...',
                  prefixIcon: Icon(LucideIcons.search, size: 18, color: AppColors.textTertiary),
                  border: InputBorder.none,
                  enabledBorder: InputBorder.none,
                  focusedBorder: InputBorder.none,
                  contentPadding: EdgeInsets.symmetric(vertical: 10),
                ),
                onChanged: (val) => setState(() => _searchQuery = val.toLowerCase()),
              ),
            ),
            const SizedBox(width: 8),
            IconButton(
              onPressed: () => ref.read(productsProvider.notifier).refresh(),
              icon: const Icon(LucideIcons.refreshCw, color: AppColors.textSecondary),
              tooltip: 'Refresh',
            ),
          ],
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
      height: 56,
      padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 16),
      child: ListView(
        scrollDirection: Axis.horizontal,
        children: categories.entries.map((entry) {
          final isSelected = _selectedCategoryId == entry.key;
          return Padding(
            padding: const EdgeInsets.only(right: 8),
            child: ChoiceChip(
              label: Text(entry.value, style: const TextStyle(fontSize: 13)),
              selected: isSelected,
              onSelected: (_) {
                setState(() => _selectedCategoryId = entry.key);
                ref.read(productsProvider.notifier).refresh(categoryId: entry.key);
              },
              backgroundColor: Colors.white,
              selectedColor: AppColors.primary,
              labelStyle: TextStyle(
                color: isSelected ? Colors.white : AppColors.textPrimary,
                fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
              ),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(24),
                side: BorderSide(color: isSelected ? AppColors.primary : AppColors.border),
              ),
            ),
          );
        }).toList(),
      ),
    );
  }

  Widget _buildProductGrid(AsyncValue<List<ProductModel>> productsAsync, {required int crossAxisCount}) {
    return productsAsync.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (err, _) => Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(LucideIcons.wifiOff, size: 40, color: AppColors.textTertiary),
            const SizedBox(height: 12),
            const Text('Gagal memuat produk'),
            const SizedBox(height: 8),
            TextButton(
              onPressed: () => ref.read(productsProvider.notifier).refresh(),
              child: const Text('Coba lagi'),
            ),
          ],
        ),
      ),
      data: (products) {
        final filtered = _searchQuery.isEmpty
            ? products
            : products.where((p) => p.name.toLowerCase().contains(_searchQuery)).toList();

        if (filtered.isEmpty) {
          return Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const Icon(LucideIcons.packageSearch, size: 40, color: AppColors.textTertiary),
                const SizedBox(height: 12),
                Text(
                  _searchQuery.isNotEmpty ? 'Produk tidak ditemukan' : 'Belum ada produk',
                  style: const TextStyle(color: AppColors.textSecondary),
                ),
              ],
            ),
          );
        }

        return Padding(
          padding: const EdgeInsets.all(12),
          child: GridView.builder(
            gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
              crossAxisCount: crossAxisCount,
              childAspectRatio: crossAxisCount == 2 ? 0.85 : 0.75,
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
                imageUrl: product.imageUrl ?? '',
                onTap: () {
                  ref.read(cartProvider.notifier).addItem(CartItem(
                    productId: product.id,
                    name: product.name,
                    price: product.price,
                  ));
                  // Phone: tampilkan snackbar singkat
                  if (MediaQuery.of(context).size.width < 700) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(
                        content: Text('${product.name} ditambahkan'),
                        duration: const Duration(milliseconds: 800),
                        behavior: SnackBarBehavior.floating,
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
