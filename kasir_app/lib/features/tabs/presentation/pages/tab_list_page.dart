import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:lucide_icons/lucide_icons.dart';
import '../../../../core/theme/app_colors.dart';
import '../../providers/tab_provider.dart';
import '../widgets/open_tab_modal.dart';
import 'tab_detail_page.dart';

class TabListPage extends ConsumerStatefulWidget {
  const TabListPage({super.key});

  @override
  ConsumerState<TabListPage> createState() => _TabListPageState();
}

class _TabListPageState extends ConsumerState<TabListPage> with SingleTickerProviderStateMixin {
  late TabController _tabController;
  final _currency = NumberFormat.currency(locale: 'id_ID', symbol: 'Rp ', decimalDigits: 0);

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
    _tabController.addListener(() {
      if (!_tabController.indexIsChanging) _refresh();
    });
    Future.microtask(() => _refresh());
  }

  void _refresh() {
    final statuses = [null, 'open', 'paid'];
    ref.read(tabProvider.notifier).fetchTabs(status: statuses[_tabController.index]);
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final tabState = ref.watch(tabProvider);

    return Scaffold(
      backgroundColor: AppColors.background,
      body: Column(
        children: [
          // Header
          Container(
            padding: const EdgeInsets.fromLTRB(24, 16, 16, 0),
            color: Colors.white,
            child: Column(
              children: [
                Row(
                  children: [
                    IconButton(
                      icon: const Icon(LucideIcons.arrowLeft),
                      onPressed: () => Navigator.pop(context),
                    ),
                    const SizedBox(width: 8),
                    const Icon(LucideIcons.receipt, color: AppColors.primary),
                    const SizedBox(width: 12),
                    Text('Tab / Bon', style: Theme.of(context).textTheme.titleLarge),
                    const Spacer(),
                    FilledButton.icon(
                      onPressed: () => _showOpenTabModal(context),
                      icon: const Icon(LucideIcons.plus, size: 18),
                      label: const Text('Buka Tab'),
                      style: FilledButton.styleFrom(
                        backgroundColor: AppColors.primary,
                        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                TabBar(
                  controller: _tabController,
                  labelColor: AppColors.primary,
                  unselectedLabelColor: AppColors.textSecondary,
                  indicatorColor: AppColors.primary,
                  tabs: const [
                    Tab(text: 'Semua'),
                    Tab(text: 'Aktif'),
                    Tab(text: 'Selesai'),
                  ],
                ),
              ],
            ),
          ),

          // Content
          Expanded(
            child: tabState.isLoading
                ? const Center(child: CircularProgressIndicator())
                : tabState.tabs.isEmpty
                    ? Center(
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(LucideIcons.receipt, size: 64, color: AppColors.textTertiary),
                            const SizedBox(height: 16),
                            Text(
                              'Belum ada tab',
                              style: TextStyle(color: AppColors.textSecondary, fontSize: 16),
                            ),
                            const SizedBox(height: 8),
                            Text(
                              'Buka tab baru untuk mulai',
                              style: TextStyle(color: AppColors.textTertiary, fontSize: 14),
                            ),
                          ],
                        ),
                      )
                    : RefreshIndicator(
                        onRefresh: () async => _refresh(),
                        child: ListView.builder(
                          padding: const EdgeInsets.all(16),
                          itemCount: tabState.tabs.length,
                          itemBuilder: (context, index) => _buildTabCard(tabState.tabs[index]),
                        ),
                      ),
          ),
        ],
      ),
    );
  }

  Widget _buildTabCard(TabModel tab) {
    final statusConfig = _getStatusConfig(tab.status);

    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      elevation: 0,
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: () async {
          await Navigator.push(
            context,
            MaterialPageRoute(builder: (_) => TabDetailPage(tabId: tab.id)),
          );
          _refresh();
        },
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Top row: tab number + status
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                    decoration: BoxDecoration(
                      color: AppColors.primary.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Text(
                      tab.tabNumber,
                      style: const TextStyle(
                        color: AppColors.primary,
                        fontWeight: FontWeight.bold,
                        fontSize: 14,
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  if (tab.customerName != null) ...[
                    Icon(LucideIcons.user, size: 14, color: AppColors.textSecondary),
                    const SizedBox(width: 4),
                    Text(tab.customerName!, style: TextStyle(color: AppColors.textSecondary, fontSize: 13)),
                  ],
                  const Spacer(),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                    decoration: BoxDecoration(
                      color: statusConfig.bgColor,
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: Text(
                      statusConfig.label,
                      style: TextStyle(color: statusConfig.textColor, fontSize: 11, fontWeight: FontWeight.bold),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              // Info row
              Row(
                children: [
                  _buildInfoChip(LucideIcons.users, '${tab.guestCount} tamu'),
                  const SizedBox(width: 12),
                  _buildInfoChip(LucideIcons.shoppingCart, '${tab.orderIds.length} order'),
                  if (tab.splitMethod != null) ...[
                    const SizedBox(width: 12),
                    _buildInfoChip(LucideIcons.split, _splitMethodLabel(tab.splitMethod!)),
                  ],
                ],
              ),
              const Divider(height: 24),
              // Bottom: total + paid
              Row(
                children: [
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Total', style: TextStyle(color: AppColors.textSecondary, fontSize: 12)),
                      Text(
                        _currency.format(tab.totalAmount),
                        style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                      ),
                    ],
                  ),
                  const Spacer(),
                  if (tab.isSplitting || (tab.paidAmount > 0 && !tab.isPaid)) ...[
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.end,
                      children: [
                        Text('Sisa', style: TextStyle(color: AppColors.textSecondary, fontSize: 12)),
                        Text(
                          _currency.format(tab.remainingAmount),
                          style: TextStyle(
                            fontWeight: FontWeight.bold,
                            fontSize: 16,
                            color: tab.remainingAmount > 0 ? AppColors.warning : AppColors.success,
                          ),
                        ),
                      ],
                    ),
                  ] else if (tab.isPaid) ...[
                    const Icon(LucideIcons.checkCircle2, color: AppColors.success, size: 20),
                    const SizedBox(width: 6),
                    Text('Lunas', style: TextStyle(color: AppColors.success, fontWeight: FontWeight.bold)),
                  ],
                  const SizedBox(width: 8),
                  Icon(LucideIcons.chevronRight, color: AppColors.textTertiary, size: 20),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildInfoChip(IconData icon, String text) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 14, color: AppColors.textSecondary),
        const SizedBox(width: 4),
        Text(text, style: TextStyle(color: AppColors.textSecondary, fontSize: 13)),
      ],
    );
  }

  String _splitMethodLabel(String method) {
    switch (method) {
      case 'equal':
        return 'Bagi Rata';
      case 'per_item':
        return 'Per Item';
      case 'custom':
        return 'Custom';
      case 'full':
        return 'Penuh';
      default:
        return method;
    }
  }

  _StatusConfig _getStatusConfig(String status) {
    switch (status) {
      case 'open':
        return _StatusConfig('Aktif', AppColors.info.withOpacity(0.1), AppColors.info);
      case 'asking_bill':
        return _StatusConfig('Minta Bill', AppColors.warning.withOpacity(0.1), AppColors.warning);
      case 'splitting':
        return _StatusConfig('Split Bill', AppColors.primary.withOpacity(0.1), AppColors.primary);
      case 'paid':
        return _StatusConfig('Lunas', AppColors.success.withOpacity(0.1), AppColors.success);
      case 'cancelled':
        return _StatusConfig('Batal', AppColors.error.withOpacity(0.1), AppColors.error);
      default:
        return _StatusConfig(status, AppColors.surfaceVariant, AppColors.textSecondary);
    }
  }

  void _showOpenTabModal(BuildContext context) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (_) => OpenTabModal(
        onTabOpened: (tab) {
          _refresh();
          Navigator.push(
            context,
            MaterialPageRoute(builder: (_) => TabDetailPage(tabId: tab.id)),
          );
        },
      ),
    );
  }
}

class _StatusConfig {
  final String label;
  final Color bgColor;
  final Color textColor;
  _StatusConfig(this.label, this.bgColor, this.textColor);
}
