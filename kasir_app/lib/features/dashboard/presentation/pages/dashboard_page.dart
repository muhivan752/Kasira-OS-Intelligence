import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:lucide_icons/lucide_icons.dart';
import '../../../../core/services/session_cache.dart';
import 'package:intl/intl.dart';
import 'package:url_launcher/url_launcher.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../pos/presentation/pages/pos_page.dart';
import '../../../orders/presentation/pages/order_list_page.dart';
import '../../../shift/presentation/pages/shift_page.dart';
import '../../../products/presentation/pages/product_management_page.dart';
import '../../../settings/presentation/pages/settings_page.dart';
import '../../../reservations/presentation/pages/reservation_list_page.dart';
import '../../../ai/presentation/pages/ai_chat_page.dart';
import 'package:go_router/go_router.dart';
import '../../providers/dashboard_provider.dart';
import '../../../orders/providers/orders_provider.dart';

final _currencyFmt = NumberFormat.currency(locale: 'id_ID', symbol: 'Rp ', decimalDigits: 0);

const _proTiers = {'pro', 'business', 'enterprise'};

// Tier now from SessionCache (0ms sync read)

class DashboardPage extends StatefulWidget {
  const DashboardPage({super.key});

  @override
  State<DashboardPage> createState() => _DashboardPageState();
}

class _DashboardPageState extends State<DashboardPage> {
  int _selectedIndex = 0;
  bool _isPro = false;

  @override
  void initState() {
    super.initState();
    _loadTier();
  }

  Future<void> _loadTier() async {
    if (mounted) setState(() => _isPro = SessionCache.instance.isPro);
  }

  List<Widget> get _pages => [
    const _DashboardContent(),
    const PosPage(),
    const OrderListPage(),
    const ReservationListPage(),
    const AiChatPage(),
    const ProductManagementPage(),
    const SettingsPage(),
  ];

  List<({IconData icon, String label})> get _navItems => [
    (icon: LucideIcons.layoutDashboard, label: 'Beranda'),
    (icon: LucideIcons.monitorPlay, label: 'POS'),
    (icon: LucideIcons.receipt, label: 'Pesanan'),
    (icon: LucideIcons.calendarCheck, label: 'Reservasi'),
    (icon: LucideIcons.bot, label: 'AI'),
    (icon: LucideIcons.package, label: 'Produk'),
    (icon: LucideIcons.settings, label: 'Setting'),
  ];

  /// Index nav items yang Pro-only (Reservasi = index 3, AI = index 4)
  static const _proNavIndexes = {3, 4};

  static const _proFeatureNames = {
    3: 'Reservasi & Booking',
    4: 'AI Asisten',
  };

  void _onNavTap(int index) {
    if (!_isPro && _proNavIndexes.contains(index)) {
      _showUpgradeSheet(context, _proFeatureNames[index] ?? 'Fitur Pro');
      return;
    }
    setState(() => _selectedIndex = index);
  }

  static void _showUpgradeSheet(BuildContext context, String featureName) {
    showModalBottomSheet(
      context: context,
      backgroundColor: AppColors.surface,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (_) => Padding(
        padding: const EdgeInsets.fromLTRB(24, 20, 24, 32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 40, height: 4,
              decoration: BoxDecoration(color: AppColors.borderLight, borderRadius: BorderRadius.circular(2)),
            ),
            const SizedBox(height: 20),
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                gradient: AppColors.primaryGradient,
                borderRadius: BorderRadius.circular(16),
              ),
              child: const Icon(LucideIcons.lock, color: Colors.white, size: 32),
            ),
            const SizedBox(height: 16),
            const Text('Upgrade ke Pro', style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: AppColors.textPrimary)),
            const SizedBox(height: 8),
            Text(
              '$featureName hanya tersedia di paket Pro.',
              textAlign: TextAlign.center,
              style: const TextStyle(color: AppColors.textSecondary, fontSize: 14),
            ),
            const SizedBox(height: 4),
            const Text(
              'Rp 299.000/bulan',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: AppColors.primary),
            ),
            const SizedBox(height: 16),
            // Bank transfer info
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: AppColors.surfaceVariant,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: AppColors.border),
              ),
              child: const Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Transfer ke:', style: TextStyle(color: AppColors.textSecondary, fontSize: 12)),
                  SizedBox(height: 8),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text('Bank', style: TextStyle(color: AppColors.textSecondary, fontSize: 13)),
                      Text('Mandiri', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                    ],
                  ),
                  SizedBox(height: 4),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text('No. Rek', style: TextStyle(color: AppColors.textSecondary, fontSize: 13)),
                      Text('1060021987147', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13, fontFamily: 'monospace')),
                    ],
                  ),
                  SizedBox(height: 4),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text('a.n.', style: TextStyle(color: AppColors.textSecondary, fontSize: 13)),
                      Text('MIRFAN', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: 6),
            const Text(
              'Konfirmasi via WhatsApp setelah transfer',
              style: TextStyle(color: AppColors.textTertiary, fontSize: 11),
            ),
            const SizedBox(height: 16),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton.icon(
                onPressed: () {
                  Navigator.pop(context);
                  _openWhatsApp();
                },
                icon: const Icon(LucideIcons.messageCircle, size: 18),
                label: const Text('Konfirmasi via WhatsApp'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppColors.primary,
                  foregroundColor: AppColors.background,
                  padding: const EdgeInsets.symmetric(vertical: 14),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                ),
              ),
            ),
            const SizedBox(height: 10),
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Nanti saja', style: TextStyle(color: AppColors.textTertiary)),
            ),
          ],
        ),
      ),
    );
  }

  static void _openWhatsApp() {
    final uri = Uri.parse('https://wa.me/6285270782220?text=${Uri.encodeComponent("Halo Kasira, saya sudah transfer untuk upgrade Pro. Mohon diaktivasi.")}');
    launchUrl(uri, mode: LaunchMode.externalApplication);
  }

  @override
  Widget build(BuildContext context) {
    final isWide = MediaQuery.of(context).size.width >= 600;

    if (isWide) {
      return _buildTabletLayout();
    } else {
      return _buildPhoneLayout();
    }
  }

  Widget _buildTabletLayout() {
    return Scaffold(
      backgroundColor: AppColors.background,
      body: Row(
        children: [
          Container(
            width: 100,
            color: AppColors.surface,
            child: Column(
              children: [
                const SizedBox(height: 24),
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: AppColors.primary.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(16),
                  ),
                  child: const Icon(Icons.point_of_sale_rounded, color: AppColors.primary, size: 32),
                ),
                const SizedBox(height: 48),
                ...List.generate(_navItems.length - 1, (i) => _buildSideNavItem(i)),
                const Spacer(),
                _buildSideNavItem(_navItems.length - 1),
                const SizedBox(height: 24),
              ],
            ),
          ),
          Expanded(child: _pages[_selectedIndex]),
        ],
      ),
    );
  }

  Widget _buildPhoneLayout() {
    return Scaffold(
      backgroundColor: AppColors.background,
      body: _pages[_selectedIndex],
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _selectedIndex,
        onTap: _onNavTap,
        type: BottomNavigationBarType.fixed,
        selectedItemColor: AppColors.primary,
        unselectedItemColor: AppColors.textTertiary,
        selectedFontSize: 11,
        unselectedFontSize: 11,
        items: _navItems
            .map((item) => BottomNavigationBarItem(
                  icon: Icon(item.icon),
                  label: item.label,
                ))
            .toList(),
      ),
    );
  }

  Widget _buildSideNavItem(int index) {
    final item = _navItems[index];
    final isSelected = _selectedIndex == index;
    final isLocked = !_isPro && _proNavIndexes.contains(index);
    return InkWell(
      onTap: () => _onNavTap(index),
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(vertical: 20),
        decoration: BoxDecoration(
          border: Border(
            right: BorderSide(
              color: isSelected ? AppColors.primary : Colors.transparent,
              width: 4,
            ),
          ),
        ),
        child: Column(
          children: [
            Stack(
              clipBehavior: Clip.none,
              children: [
                Icon(item.icon,
                    color: isLocked ? Colors.grey[350] : (isSelected ? AppColors.primary : AppColors.textTertiary),
                    size: 28),
                if (isLocked)
                  Positioned(
                    right: -6, top: -4,
                    child: Icon(LucideIcons.lock, size: 12, color: Colors.amber.shade700),
                  ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              item.label,
              style: TextStyle(
                color: isLocked ? Colors.grey[400] : (isSelected ? AppColors.primary : AppColors.textTertiary),
                fontSize: 12,
                fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ── Dashboard Content (real data) ────────────────────────────────────────────

class _DashboardContent extends ConsumerWidget {
  const _DashboardContent();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final isWide = MediaQuery.of(context).size.width >= 600;
    final statsAsync = ref.watch(dashboardProvider);
    final ordersState = ref.watch(ordersProvider);

    return isWide
        ? _buildWide(context, ref, statsAsync, ordersState)
        : _buildPhone(context, ref, statsAsync, ordersState);
  }

  Widget _buildWide(BuildContext context, WidgetRef ref,
      AsyncValue<DashboardStats> statsAsync, OrdersState ordersState) {
    return Padding(
      padding: const EdgeInsets.all(32.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildHeader(context, ref, statsAsync, isWide: true),
          const SizedBox(height: 40),
          statsAsync.when(
            loading: () => const LinearProgressIndicator(),
            error: (_, __) => _buildStatsError(ref),
            data: (stats) => _buildStatsRow(context, stats),
          ),
          const SizedBox(height: 40),
          Text('Transaksi Terakhir', style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 16),
          Expanded(child: _buildOrderList(context, ordersState, ref)),
        ],
      ),
    );
  }

  Widget _buildPhone(BuildContext context, WidgetRef ref,
      AsyncValue<DashboardStats> statsAsync, OrdersState ordersState) {
    return SafeArea(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildHeader(context, ref, statsAsync, isWide: false),
            const SizedBox(height: 24),
            statsAsync.when(
              loading: () => const LinearProgressIndicator(),
              error: (_, __) => _buildStatsError(ref),
              data: (stats) => _buildStatsColumn(context, stats),
            ),
            const SizedBox(height: 24),
            Text('Transaksi Terakhir', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 12),
            _buildOrderList(context, ordersState, ref),
          ],
        ),
      ),
    );
  }

  Widget _buildHeader(BuildContext context, WidgetRef ref,
      AsyncValue<DashboardStats> statsAsync, {required bool isWide}) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Selamat Datang!',
                style: isWide
                    ? Theme.of(context).textTheme.displaySmall
                    : Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 4),
              statsAsync.when(
                loading: () => const Text('Memuat...', style: TextStyle(color: AppColors.textSecondary, fontSize: 13)),
                error: (_, __) => const SizedBox.shrink(),
                data: (stats) => Text(
                  'Shift: ${stats.shiftStatus == "open" ? "Buka" : "Tutup"}',
                  style: TextStyle(
                    color: stats.shiftStatus == 'open' ? AppColors.success : AppColors.textSecondary,
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ],
          ),
        ),
        Row(
          children: [
            IconButton(
              onPressed: () {
                ref.read(dashboardProvider.notifier).refresh();
                ref.read(ordersProvider.notifier).fetch();
              },
              icon: const Icon(LucideIcons.refreshCw, color: AppColors.textSecondary),
              tooltip: 'Refresh',
            ),
            const SizedBox(width: 8),
            ElevatedButton.icon(
              onPressed: () {
                if (SessionCache.instance.isPro) {
                  context.push('/tabs');
                } else {
                  _DashboardPageState._showUpgradeSheet(context, 'Tab / Split Bill');
                }
              },
              icon: const Icon(LucideIcons.split, size: 16),
              label: Text(isWide ? 'Tab / Bon' : 'Tab'),
              style: ElevatedButton.styleFrom(
                backgroundColor: AppColors.info,
                padding: isWide
                    ? const EdgeInsets.symmetric(horizontal: 20, vertical: 12)
                    : const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              ),
            ),
            const SizedBox(width: 8),
            ElevatedButton.icon(
              onPressed: () {
                Navigator.push(context, MaterialPageRoute(builder: (_) => const ShiftPage()));
              },
              icon: const Icon(LucideIcons.logOut, size: 16),
              label: Text(isWide ? 'Tutup Shift' : 'Shift'),
              style: ElevatedButton.styleFrom(
                backgroundColor: AppColors.error,
                padding: isWide
                    ? const EdgeInsets.symmetric(horizontal: 20, vertical: 12)
                    : const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildStatsError(WidgetRef ref) {
    return TextButton.icon(
      onPressed: () => ref.read(dashboardProvider.notifier).refresh(),
      icon: const Icon(LucideIcons.refreshCw, size: 16),
      label: const Text('Gagal memuat statistik — tap untuk retry'),
    );
  }

  Widget _buildStatsRow(BuildContext context, DashboardStats stats) {
    return Row(
      children: [
        _buildStatCard(context, 'Pendapatan', _currencyFmt.format(stats.revenueToday),
            LucideIcons.wallet, AppColors.success),
        const SizedBox(width: 24),
        _buildStatCard(context, 'Transaksi', '${stats.orderCount}',
            LucideIcons.receipt, AppColors.info),
        const SizedBox(width: 24),
        _buildStatCard(context, 'Rata-rata', _currencyFmt.format(stats.avgOrderValue),
            LucideIcons.barChart2, AppColors.warning),
      ],
    );
  }

  Widget _buildStatsColumn(BuildContext context, DashboardStats stats) {
    return Column(
      children: [
        Row(
          children: [
            Expanded(child: _buildStatCard(context, 'Pendapatan',
                _currencyFmt.format(stats.revenueToday), LucideIcons.wallet, AppColors.success)),
            const SizedBox(width: 12),
            Expanded(child: _buildStatCard(context, 'Transaksi',
                '${stats.orderCount}', LucideIcons.receipt, AppColors.info)),
          ],
        ),
        const SizedBox(height: 12),
        _buildStatCard(context, 'Rata-rata Transaksi',
            _currencyFmt.format(stats.avgOrderValue), LucideIcons.barChart2, AppColors.warning),
      ],
    );
  }

  Widget _buildStatCard(BuildContext context, String title, String value, IconData icon, Color color) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: AppColors.surface,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: AppColors.border, width: 0.5),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: color.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Icon(icon, color: color, size: 18),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(title,
                      style: const TextStyle(color: AppColors.textSecondary, fontSize: 12),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Text(
              value,
              style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildOrderList(BuildContext context, OrdersState state, WidgetRef ref) {
    if (state.isLoading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (state.error != null) {
      return Center(
        child: TextButton.icon(
          onPressed: () => ref.read(ordersProvider.notifier).fetch(),
          icon: const Icon(LucideIcons.refreshCw, size: 16),
          label: Text('Gagal: ${state.error} — tap retry'),
        ),
      );
    }
    final recent = state.orders.take(5).toList();
    if (recent.isEmpty) {
      return Container(
        padding: const EdgeInsets.all(24),
        decoration: BoxDecoration(
          color: AppColors.surface,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: AppColors.border, width: 0.5),
        ),
        child: const Center(child: Text('Belum ada transaksi hari ini')),
      );
    }
    return Container(
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.border),
      ),
      child: ListView.separated(
        shrinkWrap: true,
        physics: const NeverScrollableScrollPhysics(),
        itemCount: recent.length,
        separatorBuilder: (_, __) => const Divider(height: 1, color: AppColors.border),
        itemBuilder: (context, index) {
          final order = recent[index];
          final statusColor = order.status == 'completed'
              ? AppColors.success
              : order.status == 'cancelled'
                  ? AppColors.error
                  : AppColors.warning;
          return ListTile(
            contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
            leading: Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: AppColors.surfaceVariant,
                borderRadius: BorderRadius.circular(8),
              ),
              child: const Icon(LucideIcons.receipt, color: AppColors.textSecondary, size: 20),
            ),
            title: Text(order.orderNumber,
                style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
            subtitle: Text(
              '${order.orderTypeLabel} • ${order.items.length} item',
              style: const TextStyle(fontSize: 12),
            ),
            trailing: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Text(_currencyFmt.format(order.totalAmount),
                    style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                Text(order.statusLabel,
                    style: TextStyle(color: statusColor, fontSize: 11, fontWeight: FontWeight.bold)),
              ],
            ),
          );
        },
      ),
    );
  }
}
