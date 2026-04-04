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
      // kembali online → sync
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

  @override
  Widget build(BuildContext context) {
    final productsAsync = ref.watch(productsProvider);

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
                style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold),
              ),
            ),
          Expanded(
            child: Row(
              children: [
                // LEFT: Products
                Expanded(
                  flex: 7,
                  child: Column(
                    children: [
                      _buildHeader(),
                      _buildCategories(productsAsync),
                      Expanded(child: _buildProductGrid(productsAsync)),
                    ],
                  ),
                ),
                // RIGHT: Cart
                Container(
                  width: 400,
                  decoration: const BoxDecoration(
                    color: Colors.white,
                    border: Border(left: BorderSide(color: AppColors.border)),
                  ),
                  child: const CartPanel(),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildHeader() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
      color: Colors.white,
      child: Row(
        children: [
          const Icon(LucideIcons.store, color: AppColors.primary),
          const SizedBox(width: 12),
          Text('Kasir', style: Theme.of(context).textTheme.titleLarge),
          const Spacer(),
          // Search
          Container(
            width: 280,
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
          const SizedBox(width: 12),
          IconButton(
            onPressed: () => ref.read(productsProvider.notifier).refresh(),
            icon: const Icon(LucideIcons.refreshCw, color: AppColors.textSecondary),
            tooltip: 'Refresh produk',
          ),
        ],
      ),
    );
  }

  Widget _buildCategories(AsyncValue<List<ProductModel>> productsAsync) {
    // Kumpulkan kategori unik dari produk
    final categories = <String, String>{'all': 'Semua'};
    productsAsync.whenData((products) {
      for (final p in products) {
        if (p.categoryId != null && p.categoryName != null) {
          categories[p.categoryId!] = p.categoryName!;
        }
      }
    });

    return Container(
      height: 60,
      padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 24),
      child: ListView(
        scrollDirection: Axis.horizontal,
        children: categories.entries.map((entry) {
          final isSelected = _selectedCategoryId == entry.key;
          return Padding(
            padding: const EdgeInsets.only(right: 10),
            child: ChoiceChip(
              label: Text(entry.value),
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

  Widget _buildProductGrid(AsyncValue<List<ProductModel>> productsAsync) {
    return productsAsync.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (err, _) => Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(LucideIcons.wifiOff, size: 40, color: AppColors.textTertiary),
            const SizedBox(height: 12),
            Text('Gagal memuat produk', style: Theme.of(context).textTheme.titleMedium),
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
          padding: const EdgeInsets.all(16),
          child: GridView.builder(
            gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
              crossAxisCount: 4,
              childAspectRatio: 0.75,
              crossAxisSpacing: 12,
              mainAxisSpacing: 12,
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
                },
              );
            },
          ),
        );
      },
    );
  }
}
