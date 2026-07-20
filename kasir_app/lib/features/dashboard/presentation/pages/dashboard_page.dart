import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
import '../../../../core/services/session_cache.dart';
import '../../../../core/services/waitlist_service.dart';
import '../../../../core/localization/business_labels.dart';
import 'package:intl/intl.dart';
import 'package:url_launcher/url_launcher.dart';
import '../../../../core/theme/kasira_ds.dart';
import '../../../pos/presentation/pages/pos_page.dart';
import '../../../orders/presentation/pages/order_list_page.dart';
import '../../../shift/presentation/pages/shift_page.dart';
import '../../../products/presentation/pages/product_management_page.dart';
import '../../../settings/presentation/pages/settings_page.dart';
import '../../../reservations/presentation/pages/reservation_list_page.dart';
import '../../../tables/presentation/pages/table_grid_page.dart';
import '../../../tabs/providers/tab_provider.dart';
import '../../../ai/presentation/pages/ai_chat_page.dart';
import 'package:go_router/go_router.dart';
import '../../providers/dashboard_provider.dart';
import '../../../orders/providers/orders_provider.dart';
import '../../../pos/providers/pos_mode_provider.dart';

final _currencyFmt = NumberFormat.currency(locale: 'id_ID', symbol: 'Rp ', decimalDigits: 0);

const _proTiers = {'pro', 'business', 'enterprise'};

// Tier now from SessionCache (0ms sync read)

class DashboardPage extends ConsumerStatefulWidget {
  const DashboardPage({super.key});

  @override
  ConsumerState<DashboardPage> createState() => _DashboardPageState();
}

class _DashboardPageState extends ConsumerState<DashboardPage> {
  int _selectedIndex = 0;
  bool _isPro = false;

  @override
  void initState() {
    super.initState();
    _loadTier();
    // If POS mode was pre-set (e.g. from "Tambah Pesanan" in tab detail),
    // auto-switch to POS tab
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final mode = ref.read(posModeProvider);
      if (mode != PosMode.selection && _selectedIndex != 1) {
        setState(() => _selectedIndex = 1);
      }
    });
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
    (icon: LucideIcons.receipt, label: BusinessLabels.getLabel('order')),
    (icon: LucideIcons.calendarCheck, label: 'Reservasi'),
    (icon: LucideIcons.bot, label: 'AI'),
    (icon: LucideIcons.packageSearch, label: 'Produk & Stok'),
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
    // Adaptive per-domain (Batch #27): F&B = Pro bayar langsung, Non-F&B =
    // Waitlist teaser mode (Pro-Retail/Pro-Service belum ship).
    final domain = SessionCache.instance.businessDomain ?? 'fnb';
    if (domain == 'retail' || domain == 'service') {
      _showWaitlistTeaserSheet(context, featureName, domain);
    } else {
      _showFnbUpgradeSheet(context, featureName);
    }
  }

  static void _showFnbUpgradeSheet(BuildContext context, String featureName) {
    showModalBottomSheet(
      context: context,
      backgroundColor: KasiraDS.surfaceCard,
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
              decoration: BoxDecoration(color: KasiraDS.borderDefault, borderRadius: BorderRadius.circular(2)),
            ),
            const SizedBox(height: 20),
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                gradient: KasiraDS.gradientFrekuensi,
                borderRadius: BorderRadius.circular(16),
              ),
              child: const Icon(LucideIcons.lock, color: Colors.white, size: 32),
            ),
            const SizedBox(height: 16),
            const Text('Upgrade ke Pro', style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: KasiraDS.textStrong)),
            const SizedBox(height: 8),
            Text(
              '$featureName hanya tersedia di paket Pro.',
              textAlign: TextAlign.center,
              style: const TextStyle(color: KasiraDS.textMuted, fontSize: 14),
            ),
            const SizedBox(height: 4),
            const Text(
              'Rp 299.000/bulan',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: KasiraDS.brandPrimary),
            ),
            const SizedBox(height: 12),
            // F&B hero features
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: KasiraDS.brandPrimary.withOpacity(0.06),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: KasiraDS.brandPrimary.withOpacity(0.2)),
              ),
              child: const Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _ProFeatureRow(icon: LucideIcons.bot, text: 'AI Kopi Asisten — setup menu 5 menit'),
                  SizedBox(height: 6),
                  _ProFeatureRow(icon: LucideIcons.book, text: 'Recipe Builder + HPP otomatis'),
                  SizedBox(height: 6),
                  _ProFeatureRow(icon: LucideIcons.layoutGrid, text: 'Meja, Tab & Split Bill'),
                  SizedBox(height: 6),
                  _ProFeatureRow(icon: LucideIcons.trendingUp, text: 'Menu Engineering (BCG Matrix)'),
                ],
              ),
            ),
            const SizedBox(height: 14),
            // Bank transfer info
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: KasiraDS.surfaceSunken,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: KasiraDS.borderSubtle),
              ),
              child: const Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Transfer ke:', style: TextStyle(color: KasiraDS.textMuted, fontSize: 12)),
                  SizedBox(height: 8),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text('Bank', style: TextStyle(color: KasiraDS.textMuted, fontSize: 13)),
                      Text('Mandiri', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                    ],
                  ),
                  SizedBox(height: 4),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text('No. Rek', style: TextStyle(color: KasiraDS.textMuted, fontSize: 13)),
                      Text('1060021987147', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13, fontFamily: 'monospace')),
                    ],
                  ),
                  SizedBox(height: 4),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text('a.n.', style: TextStyle(color: KasiraDS.textMuted, fontSize: 13)),
                      Text('MIRFAN', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: 6),
            const Text(
              'Konfirmasi via WhatsApp setelah transfer',
              style: TextStyle(color: KasiraDS.textMuted, fontSize: 11),
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
                  backgroundColor: KasiraDS.brandPrimary,
                  foregroundColor: KasiraDS.bgBase,
                  padding: const EdgeInsets.symmetric(vertical: 14),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                ),
              ),
            ),
            const SizedBox(height: 10),
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Nanti saja', style: TextStyle(color: KasiraDS.textMuted)),
            ),
          ],
        ),
      ),
    );
  }

  /// Non-F&B waitlist teaser — Pro-Retail/Pro-Service belum ship, diarahkan
  /// ke waitlist + diskon 50% saat launch.
  static void _showWaitlistTeaserSheet(BuildContext context, String featureName, String domain) {
    final isRetail = domain == 'retail';
    final domainLabel = isRetail ? 'Retail' : 'Service';
    final emoji = isRetail ? '🛒' : '💈';

    // Future features per domain — teaser-grade, biar user ngerti value prop
    final teaserFeatures = isRetail
        ? const [
            (LucideIcons.qrCode, 'Scan Barcode & Stok Otomatis'),
            (LucideIcons.box, 'Manajemen Supplier & PO'),
            (LucideIcons.package, 'Multi-Gudang & Transfer Stok'),
            (LucideIcons.trendingUp, 'Laporan Margin per Kategori'),
          ]
        : const [
            (LucideIcons.calendarCheck, 'Booking Jadwal & Antrean Digital'),
            (LucideIcons.users, 'Jadwal Teknisi & Kapasitas'),
            (LucideIcons.bellRing, 'Reminder Customer via WA'),
            (LucideIcons.calendarCheck2, 'Follow-up Servis Berkala'),
          ];

    showModalBottomSheet(
      context: context,
      backgroundColor: KasiraDS.surfaceCard,
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
              decoration: BoxDecoration(color: KasiraDS.borderDefault, borderRadius: BorderRadius.circular(2)),
            ),
            const SizedBox(height: 20),
            Text(emoji, style: const TextStyle(fontSize: 44)),
            const SizedBox(height: 12),
            Text(
              'Kasira Pro untuk $domainLabel\nsedang disiapkan!',
              textAlign: TextAlign.center,
              style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: KasiraDS.textStrong, height: 1.3),
            ),
            const SizedBox(height: 8),
            Text(
              '$featureName adalah fitur F&B — tapi kami lagi ngebangun versi $domainLabel yang khusus buat kamu:',
              textAlign: TextAlign.center,
              style: const TextStyle(color: KasiraDS.textMuted, fontSize: 13, height: 1.4),
            ),
            const SizedBox(height: 16),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: KasiraDS.brandPrimary.withOpacity(0.08),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: KasiraDS.brandPrimary.withOpacity(0.3)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: teaserFeatures
                    .map((f) => Padding(
                          padding: const EdgeInsets.symmetric(vertical: 4),
                          child: _ProFeatureRow(icon: f.$1, text: f.$2),
                        ))
                    .toList(),
              ),
            ),
            const SizedBox(height: 16),
            // Diskon banner
            Container(
              width: double.infinity,
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
              decoration: BoxDecoration(
                color: KasiraDS.success.withOpacity(0.12),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: KasiraDS.success.withOpacity(0.4)),
              ),
              child: const Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(LucideIcons.percent, size: 16, color: KasiraDS.success),
                  SizedBox(width: 6),
                  Text(
                    'Waitlist dapet diskon 50% saat launch',
                    style: TextStyle(color: KasiraDS.success, fontSize: 13, fontWeight: FontWeight.w600),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),
            _WaitlistJoinButton(domain: domain),
            const SizedBox(height: 6),
            const Text(
              'Kami kabari via WhatsApp saat fiturnya rilis.',
              style: TextStyle(color: KasiraDS.textMuted, fontSize: 11),
            ),
            const SizedBox(height: 10),
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Nanti saja', style: TextStyle(color: KasiraDS.textMuted)),
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
    // One-shot redirect ke POS tab kalau pendingNavigateToPos=true (di-set oleh
    // tab_detail_page.dart saat user tap "Tambah Pesanan"). Setelah consume,
    // clear provider — gak persistent jadi user tetap bisa navigate balik ke
    // dashboard kapan aja walau posMode masih dineInOrdering.
    final pendingNavigate = ref.watch(pendingNavigateToPosProvider);
    if (pendingNavigate && _selectedIndex != 1) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) {
          setState(() => _selectedIndex = 1);
          ref.read(pendingNavigateToPosProvider.notifier).state = false;
        }
      });
    } else if (pendingNavigate) {
      // Already di POS tab tapi flag masih true — clear aja
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) {
          ref.read(pendingNavigateToPosProvider.notifier).state = false;
        }
      });
    }

    final isWide = MediaQuery.of(context).size.width >= 600;

    if (isWide) {
      return _buildTabletLayout();
    } else {
      return _buildPhoneLayout();
    }
  }

  Widget _buildTabletLayout() {
    return Scaffold(
      backgroundColor: KasiraDS.bgBase,
      body: Row(
        children: [
          Container(
            width: 100,
            color: KasiraDS.surfaceCard,
            child: Column(
              children: [
                const SizedBox(height: 24),
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: KasiraDS.brandPrimary.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(16),
                  ),
                  child: const Icon(Icons.point_of_sale_rounded, color: KasiraDS.brandPrimary, size: 32),
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
      backgroundColor: KasiraDS.bgBase,
      body: _pages[_selectedIndex],
      bottomNavigationBar: DecoratedBox(
        decoration: const BoxDecoration(
          color: KasiraDS.surfaceCard,
          border: Border(top: BorderSide(color: KasiraDS.borderSubtle)),
        ),
        child: BottomNavigationBar(
          currentIndex: _selectedIndex,
          onTap: _onNavTap,
          type: BottomNavigationBarType.fixed,
          backgroundColor: Colors.transparent,
          elevation: 0,
          selectedItemColor: KasiraDS.brandPrimary,
          unselectedItemColor: KasiraDS.textMuted,
          selectedFontSize: 11,
          unselectedFontSize: 11,
          items: _navItems
              .map((item) => BottomNavigationBarItem(
                    icon: Icon(item.icon),
                    label: item.label,
                  ))
              .toList(),
        ),
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
              color: isSelected ? KasiraDS.brandPrimary : Colors.transparent,
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
                    color: isLocked ? Colors.grey[350] : (isSelected ? KasiraDS.brandPrimary : KasiraDS.textMuted),
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
                color: isLocked ? Colors.grey[400] : (isSelected ? KasiraDS.brandPrimary : KasiraDS.textMuted),
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
          const SizedBox(height: 20),
          const _ComingSoonBanner(),
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

  // ── BERANDA (Aurora) — greeting + shift + sales hero + quick stats + CTA ──
  Widget _buildPhone(BuildContext context, WidgetRef ref,
      AsyncValue<DashboardStats> statsAsync, OrdersState ordersState) {
    return SafeArea(
      child: RefreshIndicator(
        color: KasiraDS.brandPrimary,
        onRefresh: () async {
          ref.read(dashboardProvider.notifier).refresh();
          ref.read(ordersProvider.notifier).fetch();
        },
        child: SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.fromLTRB(16, 4, 16, 28),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _berandaHeader(context, ref),
              const SizedBox(height: 14),
              statsAsync.when(
                loading: () => const Padding(
                  padding: EdgeInsets.symmetric(vertical: 40),
                  child: Center(child: CircularProgressIndicator(color: KasiraDS.brandPrimary)),
                ),
                error: (_, __) => _buildStatsError(ref),
                data: (stats) => Column(
                  children: [
                    _shiftCard(context, stats),
                    const SizedBox(height: 14),
                    _salesHero(context, stats),
                    const SizedBox(height: 14),
                    _quickStats(context, ref, stats),
                  ],
                ),
              ),
              const SizedBox(height: 18),
              _bukaKasirCta(ref),
              const SizedBox(height: 26),
              Text('Transaksi Terakhir',
                  style: KasiraDS.display(size: 16, color: KasiraDS.textStrong)),
              const SizedBox(height: 12),
              _buildOrderList(context, ordersState, ref),
            ],
          ),
        ),
      ),
    );
  }

  static const _days = ['Min', 'Sen', 'Sel', 'Rab', 'Kam', 'Jum', 'Sab'];
  static const _months = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agt', 'Sep', 'Okt', 'Nov', 'Des'];

  Widget _berandaHeader(BuildContext context, WidgetRef ref) {
    final now = DateTime.now();
    final dateLabel = '${_days[now.weekday % 7]}, ${now.day} ${_months[now.month - 1]} ${now.year}';
    final outlet = SessionCache.instance.outletName ?? 'Toko kamu';
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('// $dateLabel'.toUpperCase(),
                  style: KasiraDS.eyebrow(color: KasiraDS.textMuted)),
              const SizedBox(height: 3),
              Text('Halo 👋', style: KasiraDS.display(size: 24, color: KasiraDS.textStrong)),
              const SizedBox(height: 1),
              Text(outlet,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: KasiraDS.sans(size: 13, color: KasiraDS.textMuted)),
            ],
          ),
        ),
        const SizedBox(width: 10),
        _circleBtn(LucideIcons.refreshCw, () {
          ref.read(dashboardProvider.notifier).refresh();
          ref.read(ordersProvider.notifier).fetch();
          if (SessionCache.instance.isPro) {
            ref.read(tabProvider.notifier).fetchTabs();
          }
        }),
      ],
    );
  }

  Widget _circleBtn(IconData icon, VoidCallback onTap) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(999),
      child: Container(
        width: 44,
        height: 44,
        alignment: Alignment.center,
        decoration: BoxDecoration(
          color: KasiraDS.surfaceCard,
          shape: BoxShape.circle,
          border: Border.all(color: KasiraDS.borderSubtle),
          boxShadow: KasiraDS.shadowSm,
        ),
        child: Icon(icon, size: 20, color: KasiraDS.textStrong),
      ),
    );
  }

  Widget _shiftCard(BuildContext context, DashboardStats stats) {
    final isOpen = stats.shiftStatus == 'open';
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: KasiraDS.surfaceCard,
        borderRadius: KasiraDS.brLg,
        border: Border.all(color: KasiraDS.borderSubtle),
        boxShadow: KasiraDS.shadowSm,
      ),
      child: Row(
        children: [
          Container(
            width: 40,
            height: 40,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              color: (isOpen ? KasiraDS.success : KasiraDS.textMuted).withOpacity(0.13),
              borderRadius: KasiraDS.brMd,
            ),
            child: Container(
              width: 11,
              height: 11,
              decoration: BoxDecoration(
                color: isOpen ? KasiraDS.success : KasiraDS.textMuted,
                shape: BoxShape.circle,
              ),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(isOpen ? 'Shift aktif' : 'Shift tertutup',
                    style: KasiraDS.sans(size: 13.5, weight: FontWeight.w700, color: KasiraDS.textStrong)),
                const SizedBox(height: 2),
                Text(isOpen ? 'Kasir sedang buka' : 'Buka kasir buat mulai transaksi',
                    style: KasiraDS.sans(size: 11.5, color: KasiraDS.textMuted)),
              ],
            ),
          ),
          OutlinedButton(
            onPressed: () {
              Navigator.push(context, MaterialPageRoute(builder: (_) => const ShiftPage()));
            },
            style: OutlinedButton.styleFrom(
              foregroundColor: KasiraDS.textStrong,
              side: const BorderSide(color: KasiraDS.borderDefault),
              shape: RoundedRectangleBorder(borderRadius: KasiraDS.brPill),
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 9),
            ),
            child: Text(isOpen ? 'Tutup kasir' : 'Buka',
                style: KasiraDS.sans(size: 12.5, weight: FontWeight.w700, color: KasiraDS.textStrong)),
          ),
        ],
      ),
    );
  }

  Widget _salesHero(BuildContext context, DashboardStats stats) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(22),
      decoration: BoxDecoration(
        gradient: KasiraDS.gradientAurora,
        borderRadius: KasiraDS.brXl,
        boxShadow: KasiraDS.glowBrand,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('// PENJUALAN HARI INI',
              style: KasiraDS.eyebrow(color: Colors.white).copyWith(color: Colors.white70)),
          const SizedBox(height: 6),
          Text(_currencyFmt.format(stats.revenueToday),
              style: KasiraDS.display(size: 36, color: Colors.white, height: 1.0)),
          const SizedBox(height: 12),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 5),
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.18),
              borderRadius: KasiraDS.brPill,
              border: Border.all(color: Colors.white.withOpacity(0.25)),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(LucideIcons.receipt, size: 13, color: Colors.white),
                const SizedBox(width: 5),
                Text('${stats.orderCount} transaksi',
                    style: KasiraDS.sans(size: 12, weight: FontWeight.w700, color: Colors.white)),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _quickStats(BuildContext context, WidgetRef ref, DashboardStats stats) {
    final isPro = SessionCache.instance.isPro;
    final tabs = isPro ? ref.watch(activeTabsCountProvider) : 0;
    return Row(
      children: [
        Expanded(child: _statTile('${stats.orderCount}', 'Transaksi')),
        const SizedBox(width: 10),
        Expanded(child: _statTile(_currencyFmt.format(stats.avgOrderValue), 'Rata-rata')),
        if (isPro) ...[
          const SizedBox(width: 10),
          Expanded(child: _statTile('$tabs', 'Tab aktif')),
        ],
      ],
    );
  }

  Widget _statTile(String value, String label) {
    return Container(
      padding: const EdgeInsets.fromLTRB(12, 12, 12, 13),
      decoration: BoxDecoration(
        color: KasiraDS.surfaceCard,
        borderRadius: KasiraDS.brLg,
        border: Border.all(color: KasiraDS.borderSubtle),
        boxShadow: KasiraDS.shadowSm,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(value,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: KasiraDS.display(size: 18, color: KasiraDS.textStrong)),
          const SizedBox(height: 2),
          Text(label, style: KasiraDS.sans(size: 11, weight: FontWeight.w600, color: KasiraDS.textMuted)),
        ],
      ),
    );
  }

  Widget _bukaKasirCta(WidgetRef ref) {
    return SizedBox(
      width: double.infinity,
      height: 54,
      child: DecoratedBox(
        decoration: BoxDecoration(
          gradient: KasiraDS.gradientFrekuensi,
          borderRadius: KasiraDS.brMd,
          boxShadow: KasiraDS.glowBrand,
        ),
        child: Material(
          color: Colors.transparent,
          child: InkWell(
            onTap: () => ref.read(pendingNavigateToPosProvider.notifier).state = true,
            borderRadius: KasiraDS.brMd,
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const Icon(LucideIcons.shoppingCart, size: 19, color: Colors.white),
                const SizedBox(width: 9),
                Text('Buka Kasir',
                    style: KasiraDS.sans(size: 15, weight: FontWeight.w800, color: Colors.white)),
              ],
            ),
          ),
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
                loading: () => const Text('Memuat...', style: TextStyle(color: KasiraDS.textMuted, fontSize: 13)),
                error: (_, __) => const SizedBox.shrink(),
                data: (stats) => Text(
                  'Shift: ${stats.shiftStatus == "open" ? "Buka" : "Tutup"}',
                  style: TextStyle(
                    color: stats.shiftStatus == 'open' ? KasiraDS.success : KasiraDS.textMuted,
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
                if (SessionCache.instance.isPro) {
                  ref.read(tabProvider.notifier).fetchTabs();
                }
              },
              icon: const Icon(LucideIcons.refreshCw, color: KasiraDS.textMuted),
              tooltip: 'Refresh',
            ),
            const SizedBox(width: 8),
            _ActiveTabsBadge(isWide: isWide),
            const SizedBox(width: 8),
            ElevatedButton.icon(
              onPressed: () {
                Navigator.push(context, MaterialPageRoute(builder: (_) => const ShiftPage()));
              },
              icon: const Icon(LucideIcons.logOut, size: 16),
              label: Text(isWide ? 'Tutup Shift' : 'Shift'),
              style: ElevatedButton.styleFrom(
                backgroundColor: KasiraDS.danger,
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
            LucideIcons.wallet, KasiraDS.success),
        const SizedBox(width: 24),
        _buildStatCard(context, 'Transaksi', '${stats.orderCount}',
            LucideIcons.receipt, KasiraDS.info),
        const SizedBox(width: 24),
        _buildStatCard(context, 'Rata-rata', _currencyFmt.format(stats.avgOrderValue),
            LucideIcons.barChart2, KasiraDS.warning),
      ],
    );
  }

  Widget _buildStatsColumn(BuildContext context, DashboardStats stats) {
    return Column(
      children: [
        Row(
          children: [
            Expanded(child: _buildStatCard(context, 'Pendapatan',
                _currencyFmt.format(stats.revenueToday), LucideIcons.wallet, KasiraDS.success)),
            const SizedBox(width: 12),
            Expanded(child: _buildStatCard(context, 'Transaksi',
                '${stats.orderCount}', LucideIcons.receipt, KasiraDS.info)),
          ],
        ),
        const SizedBox(height: 12),
        _buildStatCard(context, 'Rata-rata Transaksi',
            _currencyFmt.format(stats.avgOrderValue), LucideIcons.barChart2, KasiraDS.warning),
      ],
    );
  }

  Widget _buildStatCard(BuildContext context, String title, String value, IconData icon, Color color) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: KasiraDS.surfaceCard,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: KasiraDS.borderSubtle, width: 0.5),
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
                      style: const TextStyle(color: KasiraDS.textMuted, fontSize: 12),
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
          color: KasiraDS.surfaceCard,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: KasiraDS.borderSubtle, width: 0.5),
        ),
        child: const Center(child: Text('Belum ada transaksi hari ini')),
      );
    }
    return Container(
      decoration: BoxDecoration(
        color: KasiraDS.surfaceCard,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: KasiraDS.borderSubtle),
      ),
      child: ListView.separated(
        shrinkWrap: true,
        physics: const NeverScrollableScrollPhysics(),
        itemCount: recent.length,
        separatorBuilder: (_, __) => const Divider(height: 1, color: KasiraDS.borderSubtle),
        itemBuilder: (context, index) {
          final order = recent[index];
          final statusColor = order.status == 'completed'
              ? KasiraDS.success
              : order.status == 'cancelled'
                  ? KasiraDS.danger
                  : KasiraDS.warning;
          return ListTile(
            contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
            leading: Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: KasiraDS.surfaceSunken,
                borderRadius: BorderRadius.circular(8),
              ),
              child: const Icon(LucideIcons.receipt, color: KasiraDS.textMuted, size: 20),
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

class _ActiveTabsBadge extends ConsumerStatefulWidget {
  final bool isWide;
  const _ActiveTabsBadge({required this.isWide});

  @override
  ConsumerState<_ActiveTabsBadge> createState() => _ActiveTabsBadgeState();
}

class _ActiveTabsBadgeState extends ConsumerState<_ActiveTabsBadge> {
  @override
  void initState() {
    super.initState();
    // Seed tabProvider once — count derives from it
    if (SessionCache.instance.isPro) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) ref.read(tabProvider.notifier).fetchTabs();
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final isPro = SessionCache.instance.isPro;
    final count = isPro ? ref.watch(activeTabsCountProvider) : 0;
    final hasActive = count > 0;
    final isWide = widget.isWide;

    return InkWell(
      borderRadius: BorderRadius.circular(10),
      onTap: () {
        if (!isPro) {
          _DashboardPageState._showUpgradeSheet(context, '${BusinessLabels.getLabel('active_tables')} & Tab');
          return;
        }
        context.push('/tabs');
      },
      child: Container(
        padding: isWide
            ? const EdgeInsets.symmetric(horizontal: 16, vertical: 10)
            : const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        decoration: BoxDecoration(
          color: hasActive ? KasiraDS.success.withOpacity(0.12) : KasiraDS.surfaceSunken,
          borderRadius: BorderRadius.circular(10),
          border: Border.all(
            color: hasActive ? KasiraDS.success : KasiraDS.borderSubtle,
            width: hasActive ? 1.2 : 0.5,
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Stack(
              clipBehavior: Clip.none,
              children: [
                Icon(
                  LucideIcons.coffee,
                  size: 16,
                  color: hasActive ? KasiraDS.success : KasiraDS.textMuted,
                ),
                if (hasActive)
                  Positioned(
                    right: -5,
                    top: -4,
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 1),
                      constraints: const BoxConstraints(minWidth: 14, minHeight: 14),
                      decoration: BoxDecoration(
                        color: KasiraDS.success,
                        borderRadius: BorderRadius.circular(7),
                      ),
                      child: Text(
                        count > 99 ? '99+' : '$count',
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 9,
                          fontWeight: FontWeight.bold,
                        ),
                        textAlign: TextAlign.center,
                      ),
                    ),
                  ),
              ],
            ),
            const SizedBox(width: 8),
            Text(
              isWide
                  ? (hasActive ? '$count ${BusinessLabels.getLabel('active_tables')}' : BusinessLabels.getLabel('active_tables'))
                  : (hasActive ? '$count' : BusinessLabels.getLabel('table'))
              ,
              style: TextStyle(
                fontWeight: FontWeight.w600,
                fontSize: 13,
                color: hasActive ? KasiraDS.success : KasiraDS.textMuted,
              ),
            ),
          ],
        ),
      ),
    );
  }
}


/// Reusable feature row di upgrade sheet — icon + text.
class _ProFeatureRow extends StatelessWidget {
  final IconData icon;
  final String text;
  const _ProFeatureRow({required this.icon, required this.text});

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Icon(icon, size: 15, color: KasiraDS.brandPrimary),
        const SizedBox(width: 8),
        Expanded(
          child: Text(
            text,
            style: const TextStyle(fontSize: 13, color: KasiraDS.textStrong),
          ),
        ),
      ],
    );
  }
}

/// CTA button di sheet waitlist Non-F&B — async join + snackbar feedback.
class _WaitlistJoinButton extends StatefulWidget {
  final String domain;
  const _WaitlistJoinButton({required this.domain});

  @override
  State<_WaitlistJoinButton> createState() => _WaitlistJoinButtonState();
}

class _WaitlistJoinButtonState extends State<_WaitlistJoinButton> {
  bool _loading = false;
  bool? _alreadyJoined;

  @override
  void initState() {
    super.initState();
    WaitlistService.hasJoined(widget.domain).then((v) {
      if (mounted) setState(() => _alreadyJoined = v);
    });
  }

  Future<void> _onTap() async {
    if (_loading) return;
    setState(() => _loading = true);
    final isFirstTime = await WaitlistService.join(
      domain: widget.domain,
      source: 'upgrade_sheet',
    );
    if (!mounted) return;
    setState(() => _loading = false);
    Navigator.pop(context);
    // Snackbar muncul di scaffold parent (dashboard) setelah sheet close
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          isFirstTime
              ? 'Mantap! Kamu masuk antrean prioritas. Kami kabari via WhatsApp saat fiturnya rilis.'
              : 'Kamu sudah ada di waitlist — tunggu kabar dari kami ya.',
        ),
        backgroundColor: KasiraDS.success,
        behavior: SnackBarBehavior.floating,
        duration: const Duration(seconds: 4),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final isJoined = _alreadyJoined == true;
    return SizedBox(
      width: double.infinity,
      child: ElevatedButton.icon(
        onPressed: _loading ? null : _onTap,
        icon: _loading
            ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
            : Icon(isJoined ? LucideIcons.check : LucideIcons.bellRing, size: 18),
        label: Text(
          isJoined
              ? 'Sudah di Waitlist'
              : 'Daftar Waitlist & Dapatkan Diskon 50%',
        ),
        style: ElevatedButton.styleFrom(
          backgroundColor: KasiraDS.brandPrimary,
          foregroundColor: Colors.white,
          padding: const EdgeInsets.symmetric(vertical: 14),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        ),
      ),
    );
  }
}

/// Coming Soon banner di dashboard home — muncul HANYA untuk user Non-F&B.
/// Subtle, tappable → trigger waitlist sheet. Kalau udah joined → tampilin
/// "Kamu di waitlist ✓" status.
class _ComingSoonBanner extends StatefulWidget {
  const _ComingSoonBanner();

  @override
  State<_ComingSoonBanner> createState() => _ComingSoonBannerState();
}

class _ComingSoonBannerState extends State<_ComingSoonBanner> {
  bool _joined = false;

  @override
  void initState() {
    super.initState();
    final domain = SessionCache.instance.businessDomain;
    if (domain != null) {
      WaitlistService.hasJoined(domain).then((v) {
        if (mounted) setState(() => _joined = v);
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final domain = SessionCache.instance.businessDomain;
    if (domain == null || domain == 'fnb') return const SizedBox.shrink();
    final isRetail = domain == 'retail';
    final featureTitle = isRetail ? 'Stok & Barcode Retail' : 'Booking & Antrean Servis';
    final emoji = isRetail ? '🛒' : '💈';

    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      decoration: BoxDecoration(
        color: KasiraDS.brandPrimary.withOpacity(0.07),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: KasiraDS.brandPrimary.withOpacity(0.25)),
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          borderRadius: BorderRadius.circular(12),
          onTap: () {
            _DashboardPageState._showWaitlistTeaserSheet(
              context,
              featureTitle,
              domain,
            );
          },
          child: Padding(
            padding: const EdgeInsets.fromLTRB(14, 12, 12, 12),
            child: Row(
              children: [
                Text(emoji, style: const TextStyle(fontSize: 22)),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          const Text(
                            'Segera Hadir',
                            style: TextStyle(
                              fontSize: 11,
                              fontWeight: FontWeight.w600,
                              color: KasiraDS.brandPrimary,
                              letterSpacing: 0.4,
                            ),
                          ),
                          if (_joined) ...[
                            const SizedBox(width: 6),
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
                              decoration: BoxDecoration(
                                color: KasiraDS.success.withOpacity(0.2),
                                borderRadius: BorderRadius.circular(4),
                              ),
                              child: const Text(
                                '✓ Waitlist',
                                style: TextStyle(fontSize: 9, color: KasiraDS.success, fontWeight: FontWeight.w700),
                              ),
                            ),
                          ],
                        ],
                      ),
                      const SizedBox(height: 2),
                      Text(
                        featureTitle,
                        style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: KasiraDS.textStrong),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        _joined
                            ? 'Kami kabari saat fiturnya rilis'
                            : 'Daftar waitlist → dapet diskon 50% saat launch',
                        style: const TextStyle(fontSize: 11, color: KasiraDS.textMuted),
                      ),
                    ],
                  ),
                ),
                const Icon(LucideIcons.chevronRight, size: 18, color: KasiraDS.textMuted),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
