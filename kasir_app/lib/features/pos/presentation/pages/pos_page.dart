import 'dart:async';
import 'package:flutter/material.dart';
import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:lucide_icons/lucide_icons.dart';
import '../../../../core/theme/app_colors.dart';
import '../widgets/product_card.dart';
import '../widgets/cart_panel.dart';

class PosPage extends StatefulWidget {
  const PosPage({super.key});

  @override
  State<PosPage> createState() => _PosPageState();
}

class _PosPageState extends State<PosPage> {
  int _selectedCategoryIndex = 0;
  final List<String> _categories = ['Semua', 'Kopi', 'Non-Kopi', 'Makanan', 'Snack', 'Dessert'];

  bool _isOffline = false;
  StreamSubscription<List<ConnectivityResult>>? _connectivitySubscription;

  @override
  void initState() {
    super.initState();
    _initConnectivity();
    _connectivitySubscription = Connectivity().onConnectivityChanged.listen((List<ConnectivityResult> result) {
      _updateConnectionStatus(result);
    });
  }

  Future<void> _initConnectivity() async {
    late List<ConnectivityResult> result;
    try {
      result = await Connectivity().checkConnectivity();
    } catch (e) {
      return;
    }
    if (!mounted) {
      return;
    }
    _updateConnectionStatus(result);
  }

  void _updateConnectionStatus(List<ConnectivityResult> result) {
    final isOffline = result.contains(ConnectivityResult.none) || result.isEmpty;
    
    if (_isOffline && !isOffline) {
      // Trigger sync to server when back online
      _syncToServer();
    }
    
    setState(() {
      _isOffline = isOffline;
    });
  }

  void _syncToServer() {
    // TODO: Implement sync logic
    debugPrint("Syncing to server...");
  }

  @override
  void dispose() {
    _connectivitySubscription?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      body: Column(
        children: [
          if (_isOffline)
            Container(
              width: double.infinity,
              color: Colors.red,
              padding: const EdgeInsets.symmetric(vertical: 8),
              child: const Text(
                "Mode Offline - Transaksi tersimpan, sync saat online",
                textAlign: TextAlign.center,
                style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold),
              ),
            ),
          Expanded(
            child: Row(
              children: [
                // LEFT PANEL: Products & Categories
                Expanded(
                  flex: 7,
                  child: Column(
                    children: [
                // Header
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
                  color: Colors.white,
                  child: Row(
                    children: [
                      const Icon(LucideIcons.store, color: AppColors.primary),
                      const SizedBox(width: 12),
                      Text(
                        'Kasira Outlet Sudirman',
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                      const Spacer(),
                      // Search Bar
                      Container(
                        width: 300,
                        height: 44,
                        decoration: BoxDecoration(
                          color: AppColors.surfaceVariant,
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: TextField(
                          decoration: InputDecoration(
                            hintText: 'Cari produk...',
                            prefixIcon: const Icon(LucideIcons.search, size: 20, color: AppColors.textTertiary),
                            border: InputBorder.none,
                            enabledBorder: InputBorder.none,
                            focusedBorder: InputBorder.none,
                            fillColor: Colors.transparent,
                            contentPadding: const EdgeInsets.symmetric(vertical: 12),
                          ),
                        ),
                      ),
                      const SizedBox(width: 16),
                      IconButton(
                        onPressed: () {},
                        icon: const Icon(LucideIcons.menu),
                      ),
                    ],
                  ),
                ),
                
                // Categories
                Container(
                  height: 70,
                  padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 24),
                  child: ListView.builder(
                    scrollDirection: Axis.horizontal,
                    itemCount: _categories.length,
                    itemBuilder: (context, index) {
                      final isSelected = _selectedCategoryIndex == index;
                      return Padding(
                        padding: const EdgeInsets.only(right: 12),
                        child: ChoiceChip(
                          label: Text(_categories[index]),
                          selected: isSelected,
                          onSelected: (selected) {
                            setState(() => _selectedCategoryIndex = index);
                          },
                          backgroundColor: Colors.white,
                          selectedColor: AppColors.primary,
                          labelStyle: TextStyle(
                            color: isSelected ? Colors.white : AppColors.textPrimary,
                            fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                          ),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(24),
                            side: BorderSide(
                              color: isSelected ? AppColors.primary : AppColors.border,
                            ),
                          ),
                        ),
                      );
                    },
                  ),
                ),

                // Product Grid
                Expanded(
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 24),
                    child: GridView.builder(
                      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                        crossAxisCount: 4,
                        childAspectRatio: 0.75,
                        crossAxisSpacing: 16,
                        mainAxisSpacing: 16,
                      ),
                      itemCount: 12, // Dummy count
                      itemBuilder: (context, index) {
                        return ProductCard(
                          name: 'Kopi Susu Gula Aren ${index + 1}',
                          price: 25000.0 + (index * 2000),
                          stock: index == 3 ? 0 : 15,
                          imageUrl: 'https://picsum.photos/seed/coffee$index/200/200',
                          onTap: () {
                            // Add to cart logic
                          },
                        );
                      },
                    ),
                  ),
                ),
              ],
            ),
          ),

                // RIGHT PANEL: Cart / Order Summary
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
}
