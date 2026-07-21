import 'dart:async';
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:go_router/go_router.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
import '../../../../core/config/app_config.dart';
import '../../../../core/services/session_cache.dart';
import '../../../../core/theme/kasira_ds.dart';
import '../../../../core/localization/business_labels.dart';
import '../../../../core/sync/sync_provider.dart';
import '../../../products/providers/products_provider.dart';
import '../../../dashboard/providers/dashboard_provider.dart';
import '../../../orders/providers/orders_provider.dart';
import '../../providers/cart_provider.dart';
import '../../providers/tax_config_provider.dart';
import '../../utils/post_payment_refresh.dart';
import '../widgets/product_card.dart';
import '../widgets/cart_panel.dart';
import '../../../tables/presentation/pages/table_grid_page.dart';
import '../../../products/presentation/widgets/product_detail_sheet.dart';
import '../../providers/pos_mode_provider.dart';
import '../../../tabs/providers/tab_provider.dart';
import '../../../tabs/presentation/widgets/guest_count_sheet.dart';

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
  // P3 Quick Win #6: debounce search 250ms — pre-fix tiap keystroke trigger
  // products.where().toLowerCase() filter di build() = rebuild + alloc list +
  // lowercase tiap product. 250ms < typing pause threshold = UX gak kerasa.
  Timer? _searchDebounce;
  // P2 Quick Win #2: clock fields PINDAH ke _PosClock widget bawah file.
  // Pre-fix: Timer.periodic(1min) → setState() → rebuild SELURUH PosPage tree
  // (897 lines, ProductGrid + cart + cat). 8 jam shift = 480x rebuild.
  // Post-fix: clock isolated widget rebuild only itself per minute.

  @override
  void initState() {
    super.initState();
    _initConnectivity();
    _connectivitySub =
        Connectivity().onConnectivityChanged.listen(_updateConnectionStatus);
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
      final syncSvc = ref.read(syncServiceProvider);
      syncSvc.sync().then((_) {
        // P3 Quick Win #1: defer cascade ke microtask via shared helper
        schedulePostPaymentRefresh(ref);
        // Notify user if stock mode changed via dashboard
        if (syncSvc.stockModeChanged && mounted) {
          final mode = syncSvc.newStockMode == 'recipe' ? 'Resep & HPP' : 'Stok Sederhana';
          syncSvc.clearStockModeChanged();
          ScaffoldMessenger.of(context).showSnackBar(SnackBar(
            content: Text('Mode stok diubah ke $mode oleh owner. Data produk akan diperbarui.'),
            duration: const Duration(seconds: 5),
            behavior: SnackBarBehavior.floating,
          ));
        }
      }).catchError((e) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(SnackBar(
            content: const Row(children: [
              Icon(LucideIcons.cloudOff, color: Colors.white, size: 16),
              SizedBox(width: 8),
              Text('Sinkronisasi gagal, coba lagi nanti'),
            ]),
            duration: const Duration(seconds: 3),
            behavior: SnackBarBehavior.floating,
            backgroundColor: KasiraDS.danger,
          ));
        }
      });
    }
    if (mounted) setState(() => _isOffline = offline);
  }

  @override
  void dispose() {
    _connectivitySub?.cancel();
    _searchController.dispose();
    _searchDebounce?.cancel();
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
            color: KasiraDS.surfaceCard,
            borderRadius: BorderRadius.vertical(top: Radius.circular(28)),
          ),
          child: Column(
            children: [
              const SizedBox(height: 12),
              Container(
                width: 40,
                height: 5,
                decoration: BoxDecoration(
                  color: KasiraDS.borderDefault,
                  borderRadius: BorderRadius.circular(999),
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

  void _goBackToModeSelection() {
    final cart = ref.read(cartProvider);
    if (cart.items.isNotEmpty) {
      showDialog(
        context: context,
        builder: (ctx) => AlertDialog(
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
          title: const Text('Kembali ke Pilihan?'),
          content: const Text('Keranjang belum kosong. Item akan tetap tersimpan.'),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Batal')),
            ElevatedButton(
              onPressed: () {
                Navigator.pop(ctx);
                ref.read(posModeProvider.notifier).state = PosMode.selection;
              },
              child: const Text('Kembali'),
            ),
          ],
        ),
      );
    } else {
      ref.read(cartProvider.notifier).clearCart();
      ref.read(posModeProvider.notifier).state = PosMode.selection;
    }
  }

  /// Handler tap meja di POS dine-in mode.
  /// - Available: langsung set table di cart + masuk product menu (existing flow)
  /// - Occupied: cek tab aktif via /tabs/by-table/{id}. Kalau ada tab → navigate
  ///   ke /tabs/{id} biar user lihat tab existing dulu (tombol "Tambah Pesanan"
  ///   di tab detail bakal lanjut flow add-order properly). Kalau gak ada tab
  ///   (orphan occupied state, edge case), fallback ke set table langsung +
  ///   snackbar warning supaya user aware.
  /// - Reserved/dirty: snackbar info, no action.
  Future<void> _onPosTableSelected(TableModel table) async {
    if (table.status == TableStatus.available) {
      // Tanya jumlah tamu dulu sebelum masuk dine-in mode.
      // Reality warkop/cafe Indonesia: tiap meja bisa 1-6+ orang, default 1
      // bikin split bill humanity gak akurat (kasir lupa update guest_count
      // sampai checkout → tab udah ke-create dengan guest_count=1 hardcoded).
      final guestCount = await showGuestCountSheet(context, tableName: table.name);
      if (guestCount == null) return; // user cancel
      ref.read(cartProvider.notifier).setTable(
            table.id,
            name: table.name,
            guestCount: guestCount,
          );
      ref.read(posModeProvider.notifier).state = PosMode.dineInOrdering;
      return;
    }

    if (table.status == TableStatus.occupied) {
      // Show loading dialog while fetching tab info
      final loadingDialog = showDialog(
        context: context,
        barrierDismissible: false,
        builder: (_) => const Center(child: CircularProgressIndicator()),
      );

      try {
        final cache = SessionCache.instance;
        final dio = Dio(BaseOptions(
          baseUrl: AppConfig.apiV1,
          connectTimeout: const Duration(seconds: 8),
          receiveTimeout: const Duration(seconds: 8),
        ));
        final res = await dio.get(
          '/tabs/by-table/${table.id}',
          queryParameters: {'outlet_id': cache.outletId},
          options: Options(headers: cache.authHeaders),
        );

        if (mounted) Navigator.of(context, rootNavigator: true).pop();
        loadingDialog.ignore();

        final tabData = res.data['data'];
        if (tabData != null) {
          // Langsung ke halaman Tab. Dulu di sini muncul bottom sheet ringkas
          // yang cuma punya 4 aksi (bayar semua / bayar sebagian / tambah /
          // detail), sementara tambah orang, gabung meja, pindah meja, dan
          // batalkan cuma ada di halaman Tab — kasir gak nemu aksinya dari
          // jalur ini. Satu tempat aja biar gak kebagi dua.
          final tabId = tabData['id'] as String;
          if (mounted) context.push('/tabs/$tabId');
          return;
        }

        // Orphan state: meja occupied tapi gak ada tab aktif. Defensive
        // fallback: tetap allow user lanjut tapi kasih warning.
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(
                '${BusinessLabels.getLabel('table')} ${table.name} ditandai terisi tapi tidak ada tab aktif. Lanjut buat order baru.',
              ),
              backgroundColor: KasiraDS.warning,
              duration: const Duration(seconds: 4),
            ),
          );
          // Tetap tanya jumlah tamu — jalur ini bikin tab baru juga, jadi
          // kalau di-skip guest_count-nya ikut kekunci di 1.
          final guestCount = await showGuestCountSheet(context, tableName: table.name);
          if (guestCount == null || !mounted) return;
          ref.read(cartProvider.notifier).setTable(
                table.id,
                name: table.name,
                guestCount: guestCount,
              );
          ref.read(posModeProvider.notifier).state = PosMode.dineInOrdering;
        }
      } catch (e) {
        if (mounted) Navigator.of(context, rootNavigator: true).pop();
        loadingDialog.ignore();
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('Gagal cek tab di ${table.name}: ${e.toString()}'),
              backgroundColor: KasiraDS.danger,
            ),
          );
        }
      }
      return;
    }

    // Reserved / dirty / other states
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            '${BusinessLabels.getLabel('table')} ${table.name} sedang ${table.status.name}',
          ),
          backgroundColor: KasiraDS.danger,
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final isWide = MediaQuery.of(context).size.shortestSide >= 600;
    final productsAsync = ref.watch(productsProvider);
    final cart = ref.watch(cartProvider);
    final posMode = ref.watch(posModeProvider);
    // Trigger tax config fetch (feeds into cart calculations)
    ref.watch(taxConfigProvider);
    final itemCount = cart.items.fold<int>(0, (sum, item) => sum + item.qty);
    // selection = default view Kasir (takeaway grid) — cart bar HARUS muncul juga.
    final showFab = !isWide &&
        (posMode == PosMode.selection ||
            posMode == PosMode.takeaway ||
            posMode == PosMode.dineInOrdering);

    final addOrderCtx = ref.watch(addOrderContextProvider);

    return Scaffold(
      backgroundColor: KasiraDS.bgBase,
      body: Column(
        children: [
          if (addOrderCtx != null)
            _AddOrderBanner(context_: addOrderCtx),
          if (_isOffline)
            Container(
              width: double.infinity,
              color: KasiraDS.warning,
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
                ? _buildTabletLayout(productsAsync, posMode)
                : _buildPhoneLayout(context, productsAsync, posMode),
          ),
        ],
      ),
      floatingActionButton: (showFab && itemCount > 0)
          ? _buildCartBar(context, itemCount, cart.total)
          : null,
      floatingActionButtonLocation: FloatingActionButtonLocation.centerFloat,
    );
  }

  /// Floating cart bar — ports the "Kasira POS.dc.html" Kasir bottom bar:
  /// gradient-frekuensi pill, count badge + total + "Lihat pesanan →".
  Widget _buildCartBar(BuildContext context, int itemCount, double total) {
    final rp = NumberFormat.currency(
        locale: 'id_ID', symbol: 'Rp', decimalDigits: 0);
    return Container(
      width: MediaQuery.of(context).size.width - 32,
      decoration: BoxDecoration(
        gradient: KasiraDS.gradientFrekuensi,
        borderRadius: BorderRadius.circular(18),
        boxShadow: KasiraDS.glowBrand,
      ),
      clipBehavior: Clip.antiAlias,
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: () => _openCartSheet(context),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  children: [
                    Container(
                      width: 30,
                      height: 30,
                      alignment: Alignment.center,
                      decoration: BoxDecoration(
                        color: Colors.white.withOpacity(0.22),
                        shape: BoxShape.circle,
                      ),
                      child: Text('$itemCount',
                          style: KasiraDS.sans(
                              size: 13,
                              weight: FontWeight.w800,
                              color: Colors.white)),
                    ),
                    const SizedBox(width: 10),
                    Text(rp.format(total),
                        style: KasiraDS.sans(
                            size: 15,
                            weight: FontWeight.w800,
                            color: Colors.white)),
                  ],
                ),
                Row(
                  children: [
                    Text('Lihat pesanan',
                        style: KasiraDS.sans(
                            size: 14,
                            weight: FontWeight.w700,
                            color: Colors.white)),
                    const SizedBox(width: 6),
                    const Icon(LucideIcons.arrowRight,
                        size: 18, color: Colors.white),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildMainContent(AsyncValue<List<ProductModel>> productsAsync, PosMode posMode, {required bool isWide}) {
    final crossAxisCount = isWide ? 4 : 2;
    switch (posMode) {
      case PosMode.dineInTableSelect:
        return Expanded(
          child: Column(
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
                decoration: const BoxDecoration(
                  color: KasiraDS.surfaceCard,
                  border: Border(bottom: BorderSide(color: KasiraDS.borderSubtle)),
                ),
                child: Row(
                  children: [
                    const Icon(LucideIcons.utensils, size: 16, color: KasiraDS.brandPrimary),
                    const SizedBox(width: 8),
                    Text(
                      '${BusinessLabels.getLabel('select_table')} — Dine In',
                      style: KasiraDS.sans(size: 14, weight: FontWeight.w700, color: KasiraDS.textStrong),
                    ),
                    const Spacer(),
                    TextButton.icon(
                      onPressed: _goBackToModeSelection,
                      icon: const Icon(LucideIcons.arrowLeft, size: 14),
                      label: const Text('Kembali', style: TextStyle(fontSize: 12)),
                    ),
                  ],
                ),
              ),
              Expanded(
                child: TableGridPage(
                  onTableSelected: _onPosTableSelected,
                ),
              ),
            ],
          ),
        );
      case PosMode.selection:
      case PosMode.takeaway:
      case PosMode.dineInOrdering:
        return Expanded(
          child: Column(
            children: [
              _buildCategories(productsAsync),
              Expanded(child: _buildProductGrid(productsAsync, crossAxisCount: crossAxisCount)),
            ],
          ),
        );
    }
  }

  Widget _buildTabletLayout(AsyncValue<List<ProductModel>> productsAsync, PosMode posMode) {
    return Row(
      children: [
        // Left: mode-dependent content
        Expanded(
          flex: 7,
          child: Column(
            children: [
              _buildHeader(isWide: true, posMode: posMode),
              _buildMainContent(productsAsync, posMode, isWide: true),
            ],
          ),
        ),
        // Right: cart
        Container(
          width: 380,
          decoration: const BoxDecoration(
            color: KasiraDS.surfaceCard,
            border: Border(left: BorderSide(color: KasiraDS.borderSubtle)),
          ),
          child: const CartPanel(),
        ),
      ],
    );
  }

  Widget _buildPhoneLayout(
      BuildContext context, AsyncValue<List<ProductModel>> productsAsync, PosMode posMode) {
    return Column(
      children: [
        _buildHeader(isWide: false, posMode: posMode),
        _buildMainContent(productsAsync, posMode, isWide: false),
      ],
    );
  }

  Widget _buildHeader({required bool isWide, required PosMode posMode}) {
    // Desain: Kasir langsung ke grid (takeaway). Dine-in lewat tab Meja.
    // selection = default view Kasir = grid takeaway (bukan layar pilih mode).
    final showSearch = posMode == PosMode.selection ||
        posMode == PosMode.takeaway ||
        posMode == PosMode.dineInOrdering;
    final showBack = posMode == PosMode.dineInTableSelect || posMode == PosMode.dineInOrdering;
    final title = 'Kasir';

    return Container(
      decoration: const BoxDecoration(
        color: KasiraDS.surfaceCard,
        border: Border(bottom: BorderSide(color: KasiraDS.borderSubtle)),
      ),
      padding: EdgeInsets.only(
        top: isWide ? 0 : MediaQuery.of(context).padding.top,
      ),
      child: SafeArea(
        bottom: false,
        child: Padding(
          padding: EdgeInsets.symmetric(
            horizontal: isWide ? 20 : 16,
            vertical: isWide ? 14 : 12,
          ),
          child: Column(
            children: [
              Row(
                children: [
                  if (showBack) ...[
                    _circleIconBtn(LucideIcons.arrowLeft, _goBackToModeSelection),
                    const SizedBox(width: 10),
                  ] else ...[
                    // Aurora brand mark
                    Container(
                      width: 36,
                      height: 36,
                      decoration: BoxDecoration(
                        gradient: KasiraDS.gradientAurora,
                        borderRadius: BorderRadius.circular(10),
                        boxShadow: KasiraDS.glowPink,
                      ),
                      child: const Icon(LucideIcons.store,
                          color: Colors.white, size: 18),
                    ),
                    const SizedBox(width: 12),
                  ],
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(title,
                            style: KasiraDS.display(
                                size: isWide ? 20 : 22,
                                color: KasiraDS.textStrong)),
                        const _PosClock(),
                      ],
                    ),
                  ),
                  if (showSearch) ...[
                    _ctxPill(),
                    const SizedBox(width: 8),
                    _circleIconBtn(LucideIcons.refreshCw, () {
                      _searchDebounce?.cancel();
                      _searchController.clear();
                      setState(() => _searchQuery = '');
                      ref.read(productsProvider.notifier).refresh();
                    }),
                  ],
                ],
              ),
              // Full-width search field (design: surface-card, 1.5px border, r14)
              if (showSearch) ...[
                const SizedBox(height: 12),
                Container(
                  constraints: const BoxConstraints(minHeight: 46),
                  padding: const EdgeInsets.symmetric(horizontal: 14),
                  decoration: BoxDecoration(
                    color: KasiraDS.surfaceCard,
                    borderRadius: KasiraDS.brMd,
                    border: Border.all(color: KasiraDS.borderDefault, width: 1.5),
                  ),
                  child: Row(
                    children: [
                      const Icon(LucideIcons.search,
                          size: 19, color: KasiraDS.textMuted),
                      const SizedBox(width: 10),
                      Expanded(
                        child: TextField(
                          controller: _searchController,
                          style: KasiraDS.sans(
                              size: 15, color: KasiraDS.textStrong),
                          decoration: InputDecoration(
                            hintText: 'Cari menu...',
                            hintStyle: KasiraDS.sans(
                                size: 15, color: KasiraDS.textMuted),
                            border: InputBorder.none,
                            isCollapsed: true,
                            contentPadding:
                                const EdgeInsets.symmetric(vertical: 13),
                          ),
                          onChanged: (val) {
                            _searchDebounce?.cancel();
                            _searchDebounce = Timer(
                              const Duration(milliseconds: 250),
                              () {
                                if (mounted) {
                                  setState(
                                      () => _searchQuery = val.toLowerCase());
                                }
                              },
                            );
                          },
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }

  /// Small circular icon button — surface-card + subtle border (design chrome).
  Widget _circleIconBtn(IconData icon, VoidCallback onTap) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(999),
      child: Container(
        width: 40,
        height: 40,
        alignment: Alignment.center,
        decoration: BoxDecoration(
          color: KasiraDS.surfaceCard,
          shape: BoxShape.circle,
          border: Border.all(color: KasiraDS.borderSubtle),
          boxShadow: KasiraDS.shadowSm,
        ),
        child: Icon(icon, size: 19, color: KasiraDS.textStrong),
      ),
    );
  }

  /// Context pill header Kasir (desain: orderCtxLabel). "Take away" default,
  /// "{Meja} · dine-in" kalau ada meja. Tap → pindah ke tab Meja (Pro) buat
  /// pilih meja = mulai dine-in.
  Widget _ctxPill() {
    final cart = ref.watch(cartProvider);
    final isDinein = cart.tableId != null;
    final label = isDinein
        ? '${cart.tableName ?? BusinessLabels.getLabel('table')} · dine-in'
        : 'Take away';
    return GestureDetector(
      onTap: () {
        if (SessionCache.instance.isPro) {
          ref.read(pendingNavigateToMejaProvider.notifier).state = true;
        } else {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Dine-in (kelola meja) tersedia di paket Pro'),
              behavior: SnackBarBehavior.floating,
            ),
          );
        }
      },
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 9),
        decoration: BoxDecoration(
          color: KasiraDS.surfaceCard,
          borderRadius: KasiraDS.brPill,
          border: Border.all(color: KasiraDS.borderDefault),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(isDinein ? LucideIcons.utensils : LucideIcons.shoppingBag,
                size: 14, color: KasiraDS.brandPrimary),
            const SizedBox(width: 5),
            ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 110),
              child: Text(label,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: KasiraDS.sans(size: 12, weight: FontWeight.w700, color: KasiraDS.textStrong)),
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
      height: 54,
      color: KasiraDS.bgBase,
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
                duration: KasiraDS.durBase,
                alignment: Alignment.center,
                padding:
                    const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
                decoration: BoxDecoration(
                  gradient: isSelected ? KasiraDS.gradientFrekuensi : null,
                  color: isSelected ? null : KasiraDS.surfaceCard,
                  borderRadius: KasiraDS.brPill,
                  border: Border.all(
                    color: isSelected
                        ? Colors.transparent
                        : KasiraDS.borderSubtle,
                  ),
                  boxShadow: isSelected ? KasiraDS.glowPink : null,
                ),
                child: Text(
                  entry.value,
                  style: KasiraDS.sans(
                    size: 13,
                    weight: isSelected ? FontWeight.w700 : FontWeight.w600,
                    color: isSelected ? Colors.white : KasiraDS.textMuted,
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
                color: KasiraDS.surfaceSunken,
                shape: BoxShape.circle,
              ),
              child: const Icon(LucideIcons.wifiOff,
                  size: 32, color: KasiraDS.textMuted),
            ),
            const SizedBox(height: 16),
            const Text('Gagal memuat produk',
                style: TextStyle(color: KasiraDS.textMuted)),
            const SizedBox(height: 12),
            ElevatedButton.icon(
              onPressed: () => ref.read(productsProvider.notifier).refresh(),
              icon: const Icon(LucideIcons.refreshCw, size: 16),
              label: const Text('Coba lagi'),
              style: ElevatedButton.styleFrom(
                backgroundColor: KasiraDS.brandPrimary,
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
                    size: 40, color: KasiraDS.textMuted),
                const SizedBox(height: 12),
                Text(
                  _searchQuery.isNotEmpty
                      ? 'Produk "$_searchQuery" tidak ditemukan'
                      : 'Belum ada produk',
                  style:
                      const TextStyle(color: KasiraDS.textMuted),
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
                isAvailable: product.isAvailable,
                imageUrl: product.imageUrl ?? '',
                isBestSeller: product.isBestSeller,
                onLongPress: () => ProductDetailSheet.show(
                  context,
                  productId: product.id,
                  productName: product.name,
                  sellingPrice: product.price,
                ),
                onTap: () {
                  final cartNotifier = ref.read(cartProvider.notifier);
                  // Tanpa meja = takeaway (default cart 'Dine In', jadi harus di-set).
                  final cartState = ref.read(cartProvider);
                  if (cartState.tableId == null && cartState.orderType != 'Takeaway') {
                    cartNotifier.setOrderType('Takeaway');
                  }
                  cartNotifier.addItem(CartItem(
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
                        backgroundColor: KasiraDS.success,
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

class _AddOrderBanner extends ConsumerWidget {
  final AddOrderContext context_;
  const _AddOrderBanner({required this.context_});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Container(
      width: double.infinity,
      color: KasiraDS.brandPrimary.withOpacity(0.12),
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Row(
        children: [
          const Icon(LucideIcons.plusCircle, size: 14, color: KasiraDS.brandPrimary),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              'Tambah ${BusinessLabels.getLabel('order')} → ${context_.tabNumber}'
              '${context_.tableName != null ? " · ${BusinessLabels.getLabel('table')} ${context_.tableName}" : ""}',
              style: const TextStyle(
                color: KasiraDS.brandPrimary,
                fontWeight: FontWeight.w600,
                fontSize: 12,
              ),
            ),
          ),
          TextButton(
            onPressed: () {
              ref.read(addOrderContextProvider.notifier).state = null;
              ref.read(cartProvider.notifier).clearCart();
              ref.read(posModeProvider.notifier).state = PosMode.selection;
            },
            style: TextButton.styleFrom(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 0),
              minimumSize: const Size(0, 28),
              foregroundColor: KasiraDS.brandPrimary,
            ),
            child: const Text('Batal', style: TextStyle(fontSize: 12)),
          ),
        ],
      ),
    );
  }
}

/// Isolated clock widget — refresh per-minute SETSTATE hanya rebuild widget ini,
/// bukan seluruh PosPage tree (897 lines). Pre-fix: setState clock di
/// _PosPageState bikin full tree rebuild 480x per shift 8 jam.
class _PosClock extends StatefulWidget {
  const _PosClock();

  @override
  State<_PosClock> createState() => _PosClockState();
}

class _PosClockState extends State<_PosClock> {
  static const _days = ['Min', 'Sen', 'Sel', 'Rab', 'Kam', 'Jum', 'Sab'];
  static const _months = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agt', 'Sep', 'Okt', 'Nov', 'Des'];

  late Timer _timer;
  String _text = '';

  @override
  void initState() {
    super.initState();
    _update();
    _timer = Timer.periodic(const Duration(minutes: 1), (_) => _update());
  }

  void _update() {
    final now = DateTime.now();
    final next = '${_days[now.weekday % 7]}, ${now.day} ${_months[now.month - 1]} · '
        '${now.hour.toString().padLeft(2, '0')}:${now.minute.toString().padLeft(2, '0')}';
    if (next != _text && mounted) {
      setState(() => _text = next);
    }
  }

  @override
  void dispose() {
    _timer.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (_text.isEmpty) return const SizedBox.shrink();
    return Text(
      _text,
      style: const TextStyle(
        fontSize: 11,
        color: KasiraDS.textMuted,
      ),
    );
  }
}
