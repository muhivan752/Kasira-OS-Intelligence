import 'package:flutter/material.dart';
import 'package:lucide_icons/lucide_icons.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../pos/presentation/pages/pos_page.dart';
import '../../../orders/presentation/pages/order_list_page.dart';
import '../../../shift/presentation/pages/shift_page.dart';
import '../../../products/presentation/pages/product_management_page.dart';
import '../../../settings/presentation/pages/settings_page.dart';

class DashboardPage extends StatefulWidget {
  const DashboardPage({super.key});

  @override
  State<DashboardPage> createState() => _DashboardPageState();
}

class _DashboardPageState extends State<DashboardPage> {
  int _selectedIndex = 0;

  final List<Widget> _pages = [
    const _DashboardContent(),
    const PosPage(),
    const OrderListPage(),
    const ProductManagementPage(),
    const SettingsPage(),
  ];

  static const _navItems = [
    (icon: LucideIcons.layoutDashboard, label: 'Beranda'),
    (icon: LucideIcons.monitorPlay, label: 'POS'),
    (icon: LucideIcons.receipt, label: 'Pesanan'),
    (icon: LucideIcons.package, label: 'Produk'),
    (icon: LucideIcons.settings, label: 'Setting'),
  ];

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
            color: Colors.white,
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
                _buildSideNavItem(4),
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
        onTap: (i) => setState(() => _selectedIndex = i),
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
    return InkWell(
      onTap: () => setState(() => _selectedIndex = index),
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
            Icon(item.icon,
                color: isSelected ? AppColors.primary : AppColors.textTertiary,
                size: 28),
            const SizedBox(height: 8),
            Text(
              item.label,
              style: TextStyle(
                color: isSelected ? AppColors.primary : AppColors.textTertiary,
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

class _DashboardContent extends StatelessWidget {
  const _DashboardContent();

  @override
  Widget build(BuildContext context) {
    final isWide = MediaQuery.of(context).size.width >= 600;
    return isWide ? _buildWide(context) : _buildPhone(context);
  }

  Widget _buildWide(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(32.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildHeader(context),
          const SizedBox(height: 40),
          _buildStatsRow(context),
          const SizedBox(height: 40),
          Text('Transaksi Terakhir', style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 16),
          Expanded(child: _buildOrderList(context)),
        ],
      ),
    );
  }

  Widget _buildPhone(BuildContext context) {
    return SafeArea(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildHeader(context),
            const SizedBox(height: 24),
            _buildStatsColumn(context),
            const SizedBox(height: 24),
            Text('Transaksi Terakhir', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 12),
            _buildOrderList(context),
          ],
        ),
      ),
    );
  }

  Widget _buildHeader(BuildContext context) {
    final isWide = MediaQuery.of(context).size.width >= 600;
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
              const Text(
                'Kasira POS',
                style: TextStyle(color: AppColors.textSecondary, fontSize: 14),
              ),
            ],
          ),
        ),
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
    );
  }

  Widget _buildStatsRow(BuildContext context) {
    return Row(
      children: [
        _buildStatCard(context, 'Pendapatan', 'Rp 2.450.000', LucideIcons.wallet, AppColors.success),
        const SizedBox(width: 24),
        _buildStatCard(context, 'Transaksi', '48', LucideIcons.receipt, AppColors.info),
        const SizedBox(width: 24),
        _buildStatCard(context, 'Rata-rata', 'Rp 51.000', LucideIcons.barChart2, AppColors.warning),
      ],
    );
  }

  Widget _buildStatsColumn(BuildContext context) {
    return Column(
      children: [
        Row(
          children: [
            Expanded(child: _buildStatCard(context, 'Pendapatan', 'Rp 2.450.000', LucideIcons.wallet, AppColors.success)),
            const SizedBox(width: 12),
            Expanded(child: _buildStatCard(context, 'Transaksi', '48', LucideIcons.receipt, AppColors.info)),
          ],
        ),
        const SizedBox(height: 12),
        _buildStatCard(context, 'Rata-rata Transaksi', 'Rp 51.000', LucideIcons.barChart2, AppColors.warning),
      ],
    );
  }

  Widget _buildStatCard(BuildContext context, String title, String value, IconData icon, Color color) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: AppColors.border),
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

  Widget _buildOrderList(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.border),
      ),
      child: ListView.separated(
        shrinkWrap: true,
        physics: const NeverScrollableScrollPhysics(),
        itemCount: 5,
        separatorBuilder: (_, __) => const Divider(height: 1, color: AppColors.border),
        itemBuilder: (context, index) {
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
            title: Text('ORD-2026-${1000 + index}',
                style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
            subtitle: Text('Dine In • ${index + 1} items', style: const TextStyle(fontSize: 12)),
            trailing: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                const Text('Rp 75.000',
                    style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                Text('Selesai',
                    style: TextStyle(color: AppColors.success, fontSize: 11, fontWeight: FontWeight.bold)),
              ],
            ),
          );
        },
      ),
    );
  }
}
