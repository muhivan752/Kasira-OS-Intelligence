import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:lucide_icons/lucide_icons.dart';
import '../../../../core/theme/app_colors.dart';
import '../../providers/tab_provider.dart';

class ActiveTabsListPage extends ConsumerStatefulWidget {
  const ActiveTabsListPage({super.key});

  @override
  ConsumerState<ActiveTabsListPage> createState() => _ActiveTabsListPageState();
}

class _ActiveTabsListPageState extends ConsumerState<ActiveTabsListPage> {
  final _currency = NumberFormat.currency(locale: 'id_ID', symbol: 'Rp ', decimalDigits: 0);

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _load());
  }

  Future<void> _load() async {
    await ref.read(tabProvider.notifier).fetchTabs();
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(tabProvider);
    final activeTabs = state.tabs.where((t) => t.isOpen).toList()
      ..sort((a, b) => b.createdAt.compareTo(a.createdAt));

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: const Text('Meja Aktif'),
        actions: [
          IconButton(
            icon: const Icon(LucideIcons.refreshCw),
            onPressed: _load,
            tooltip: 'Refresh',
          ),
        ],
      ),
      body: state.isLoading && activeTabs.isEmpty
          ? const Center(child: CircularProgressIndicator())
          : activeTabs.isEmpty
              ? _buildEmpty()
              : RefreshIndicator(
                  onRefresh: _load,
                  child: ListView.separated(
                    padding: const EdgeInsets.all(16),
                    itemCount: activeTabs.length,
                    separatorBuilder: (_, __) => const SizedBox(height: 10),
                    itemBuilder: (_, i) => _buildTabCard(activeTabs[i]),
                  ),
                ),
    );
  }

  Widget _buildEmpty() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: AppColors.surfaceVariant,
              shape: BoxShape.circle,
            ),
            child: const Icon(LucideIcons.coffee, size: 36, color: AppColors.textTertiary),
          ),
          const SizedBox(height: 16),
          const Text(
            'Belum ada meja aktif',
            style: TextStyle(fontSize: 15, color: AppColors.textSecondary),
          ),
          const SizedBox(height: 6),
          const Text(
            'Mulai dine-in dari POS untuk membuka tab baru',
            style: TextStyle(fontSize: 12, color: AppColors.textTertiary),
          ),
        ],
      ),
    );
  }

  Widget _buildTabCard(TabModel tab) {
    // Status mapping per tab.status: open/asking_bill/splitting (active states)
    final Color statusColor;
    final String statusLabel;
    switch (tab.status) {
      case 'asking_bill':
        statusColor = AppColors.warning;
        statusLabel = 'Minta Bill';
        break;
      case 'splitting':
        statusColor = AppColors.info;
        statusLabel = 'Split Bill';
        break;
      default:
        statusColor = AppColors.success;
        statusLabel = 'Aktif';
    }
    final elapsed = DateTime.now().difference(tab.createdAt);
    final elapsedLabel = elapsed.inHours > 0
        ? '${elapsed.inHours}j ${elapsed.inMinutes % 60}m'
        : '${elapsed.inMinutes}m';

    return InkWell(
      onTap: () => context.push('/tabs/${tab.id}'),
      borderRadius: BorderRadius.circular(14),
      child: Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: AppColors.surface,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: AppColors.border.withOpacity(0.5), width: 0.5),
        ),
        child: Row(
          children: [
            Container(
              width: 46,
              height: 46,
              decoration: BoxDecoration(
                color: AppColors.primary.withOpacity(0.1),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Center(
                child: Text(
                  tab.tableName ?? '—',
                  style: const TextStyle(
                    fontWeight: FontWeight.bold,
                    fontSize: 14,
                    color: AppColors.primary,
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Text(
                        tab.tabNumber,
                        style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
                      ),
                      const SizedBox(width: 8),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                        decoration: BoxDecoration(
                          color: statusColor.withOpacity(0.15),
                          borderRadius: BorderRadius.circular(4),
                        ),
                        child: Text(
                          statusLabel,
                          style: TextStyle(
                            fontSize: 10,
                            color: statusColor,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 4),
                  Row(
                    children: [
                      const Icon(LucideIcons.users, size: 12, color: AppColors.textTertiary),
                      const SizedBox(width: 4),
                      Text(
                        '${tab.guestCount}',
                        style: const TextStyle(fontSize: 11, color: AppColors.textSecondary),
                      ),
                      const SizedBox(width: 10),
                      const Icon(LucideIcons.clock, size: 12, color: AppColors.textTertiary),
                      const SizedBox(width: 4),
                      Text(
                        elapsedLabel,
                        style: const TextStyle(fontSize: 11, color: AppColors.textSecondary),
                      ),
                      if (tab.customerName != null && tab.customerName!.isNotEmpty) ...[
                        const SizedBox(width: 10),
                        const Icon(LucideIcons.user, size: 12, color: AppColors.textTertiary),
                        const SizedBox(width: 4),
                        Expanded(
                          child: Text(
                            tab.customerName!,
                            style: const TextStyle(fontSize: 11, color: AppColors.textSecondary),
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                      ],
                    ],
                  ),
                ],
              ),
            ),
            Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Text(
                  _currency.format(tab.totalAmount),
                  style: const TextStyle(
                    fontWeight: FontWeight.bold,
                    fontSize: 14,
                    color: AppColors.textPrimary,
                  ),
                ),
                if (tab.remainingAmount < tab.totalAmount && tab.paidAmount > 0)
                  Text(
                    'Sisa ${_currency.format(tab.remainingAmount)}',
                    style: const TextStyle(fontSize: 10, color: AppColors.warning),
                  ),
              ],
            ),
            const SizedBox(width: 8),
            const Icon(LucideIcons.chevronRight, size: 18, color: AppColors.textTertiary),
          ],
        ),
      ),
    );
  }
}
