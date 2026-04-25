import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:lucide_icons/lucide_icons.dart';
import '../../../../core/theme/app_colors.dart';
import '../../providers/tab_provider.dart';
import '../../../tables/presentation/pages/table_grid_page.dart';
import '../../../pos/providers/cart_provider.dart';
import '../../../pos/providers/pos_mode_provider.dart';
import '../widgets/split_bill_modal.dart';
import '../widgets/pay_split_modal.dart';
import '../widgets/tab_header.dart';
import '../widgets/tab_info_card.dart';
import '../widgets/tab_split_card.dart';
import '../widgets/tab_bottom_actions.dart';

class TabDetailPage extends ConsumerStatefulWidget {
  final String tabId;
  const TabDetailPage({super.key, required this.tabId});

  @override
  ConsumerState<TabDetailPage> createState() => _TabDetailPageState();
}

class _TabDetailPageState extends ConsumerState<TabDetailPage> {
  final _currency = NumberFormat.currency(locale: 'id_ID', symbol: 'Rp ', decimalDigits: 0);
  TabModel? _tab;
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadTab();
  }

  Future<void> _loadTab() async {
    setState(() => _isLoading = true);
    final tab = await ref.read(tabProvider.notifier).getTab(widget.tabId);
    if (mounted) setState(() { _tab = tab; _isLoading = false; });
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return Scaffold(
        backgroundColor: AppColors.background,
        appBar: AppBar(title: const Text('Tab Detail')),
        body: const Center(child: CircularProgressIndicator()),
      );
    }

    if (_tab == null) {
      return Scaffold(
        backgroundColor: AppColors.background,
        appBar: AppBar(title: const Text('Tab Detail')),
        body: const Center(child: Text('Tab tidak ditemukan')),
      );
    }

    final tab = _tab!;

    return Scaffold(
      backgroundColor: AppColors.background,
      body: Column(
        children: [
          TabHeader(tab: tab, currency: _currency),
          Expanded(
            child: RefreshIndicator(
              onRefresh: _loadTab,
              child: ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  TabInfoCard(tab: tab),
                  const SizedBox(height: 16),
                  if (tab.splits.isNotEmpty) ...[
                    Row(
                      children: [
                        const Icon(LucideIcons.split, size: 18, color: AppColors.primary),
                        const SizedBox(width: 8),
                        const Text('Split Bill', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                      ],
                    ),
                    const SizedBox(height: 8),
                    ...tab.splits.map((s) => TabSplitCard(
                      split: s,
                      currency: _currency,
                      onPay: () => _showPaySplitModal(tab, s),
                    )),
                    const SizedBox(height: 16),
                  ],
                ],
              ),
            ),
          ),
          if (tab.isOpen || tab.isSplitting)
            TabBottomActions(
              tab: tab,
              currency: _currency,
              onAddOrder: () {
                // Pre-set POS to dine-in ordering with this table + set context banner
                ref.read(cartProvider.notifier).setOrderType('Dine In');
                if (tab.tableId != null) {
                  ref.read(cartProvider.notifier).setTable(tab.tableId!, name: tab.tableName);
                }
                ref.read(posModeProvider.notifier).state = PosMode.dineInOrdering;
                ref.read(addOrderContextProvider.notifier).state = AddOrderContext(
                  tabId: tab.id,
                  tabNumber: tab.tabNumber,
                  tableName: tab.tableName,
                );
                // One-shot signal — dashboard akan switch ke POS tab sekali, lalu clear.
                // Beda dari watch posModeProvider persistent yg bikin user stuck di POS tab.
                ref.read(pendingNavigateToPosProvider.notifier).state = true;
                context.go('/dashboard');
              },
              onMoveTable: () => _showMoveTableModal(tab),
              onMergeTab: () => _showMergeTabModal(tab),
              onCancel: () => _confirmCancel(tab),
              onPayFull: () => _showPayFullModal(tab),
              onSplitBill: () => _showSplitBillModal(tab),
            ),
        ],
      ),
    );
  }

  void _showSplitBillModal(TabModel tab) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (_) => SplitBillModal(
        tab: tab,
        onSplitDone: (updatedTab) => setState(() => _tab = updatedTab),
      ),
    );
  }

  void _showPaySplitModal(TabModel tab, TabSplitModel split) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (_) => PaySplitModal(
        tab: tab,
        split: split,
        onPaid: (updatedTab) => setState(() => _tab = updatedTab),
      ),
    );
  }

  void _showPayFullModal(TabModel tab) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (_) => PaySplitModal(
        tab: tab,
        split: null,
        onPaid: (updatedTab) => setState(() => _tab = updatedTab),
      ),
    );
  }

  void _showMoveTableModal(TabModel tab) {
    showDialog(
      context: context,
      builder: (ctx) => Dialog(
        insetPadding: const EdgeInsets.all(16),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        child: SizedBox(
          width: double.maxFinite,
          height: MediaQuery.of(context).size.height * 0.7,
          child: Column(
            children: [
              Padding(
                padding: const EdgeInsets.all(16),
                child: Row(
                  children: [
                    const Icon(LucideIcons.arrowRightLeft, size: 20),
                    const SizedBox(width: 8),
                    const Text('Pilih Meja Tujuan', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                    const Spacer(),
                    IconButton(icon: const Icon(LucideIcons.x), onPressed: () => Navigator.pop(ctx)),
                  ],
                ),
              ),
              Expanded(
                child: ClipRRect(
                  borderRadius: const BorderRadius.vertical(bottom: Radius.circular(16)),
                  child: TableGridPage(
                    onTableSelected: (table) async {
                      if (table.id == tab.tableId) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(content: Text('Sudah di meja ini'), backgroundColor: AppColors.warning),
                        );
                        return;
                      }
                      if (table.status != TableStatus.available) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(
                            content: Text('Meja ${table.name} sedang ${table.status.name}'),
                            backgroundColor: AppColors.error,
                          ),
                        );
                        return;
                      }
                      Navigator.pop(ctx);
                      final result = await ref.read(tabProvider.notifier).moveTable(
                        tab.id, table.id, tab.rowVersion,
                      );
                      if (result != null && mounted) {
                        setState(() => _tab = result);
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(
                            content: Text('Pindah ke Meja ${table.name}'),
                            backgroundColor: AppColors.success,
                          ),
                        );
                      }
                    },
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _showMergeTabModal(TabModel tab) async {
    await ref.read(tabProvider.notifier).fetchTabs(status: 'open');
    final allTabs = ref.read(tabProvider).tabs;
    final otherTabs = allTabs.where((t) => t.id != tab.id && t.isOpen).toList();

    if (!mounted) return;
    if (otherTabs.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Tidak ada tab aktif lain untuk digabung'), backgroundColor: AppColors.warning),
      );
      return;
    }

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (ctx) => Padding(
        padding: EdgeInsets.only(bottom: MediaQuery.of(ctx).viewInsets.bottom),
        child: Container(
          constraints: BoxConstraints(maxHeight: MediaQuery.of(context).size.height * 0.5),
          padding: const EdgeInsets.all(20),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  const Icon(LucideIcons.merge, color: AppColors.warning),
                  const SizedBox(width: 8),
                  const Text('Gabung Tab', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
                  const Spacer(),
                  IconButton(icon: const Icon(LucideIcons.x), onPressed: () => Navigator.pop(ctx)),
                ],
              ),
              const SizedBox(height: 4),
              Text(
                'Pilih tab yang mau digabung ke ${tab.tabNumber}:',
                style: const TextStyle(color: AppColors.textSecondary, fontSize: 13),
              ),
              const SizedBox(height: 16),
              Flexible(
                child: ListView.builder(
                  shrinkWrap: true,
                  itemCount: otherTabs.length,
                  itemBuilder: (_, i) {
                    final src = otherTabs[i];
                    return Card(
                      elevation: 0,
                      margin: const EdgeInsets.only(bottom: 8),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12),
                        side: BorderSide(color: AppColors.border),
                      ),
                      child: ListTile(
                        leading: CircleAvatar(
                          backgroundColor: AppColors.primary.withOpacity(0.1),
                          child: const Icon(LucideIcons.receipt, color: AppColors.primary, size: 20),
                        ),
                        title: Text(src.tabNumber, style: const TextStyle(fontWeight: FontWeight.bold)),
                        subtitle: Text(
                          '${src.tableName ?? "Tanpa meja"} — ${_currency.format(src.totalAmount)} — ${src.guestCount} tamu',
                          style: const TextStyle(fontSize: 12),
                        ),
                        trailing: FilledButton(
                          onPressed: () async {
                            Navigator.pop(ctx);
                            final result = await ref.read(tabProvider.notifier).mergeTab(
                              tab.id, src.id, tab.rowVersion,
                            );
                            if (result != null && mounted) {
                              setState(() => _tab = result);
                              ScaffoldMessenger.of(context).showSnackBar(
                                SnackBar(
                                  content: Text('${src.tabNumber} digabung'),
                                  backgroundColor: AppColors.success,
                                ),
                              );
                            }
                          },
                          style: FilledButton.styleFrom(
                            backgroundColor: AppColors.warning,
                            padding: const EdgeInsets.symmetric(horizontal: 16),
                          ),
                          child: const Text('Gabung', style: TextStyle(fontSize: 13)),
                        ),
                      ),
                    );
                  },
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _confirmCancel(TabModel tab) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: const Text('Batalkan Tab?'),
        content: Text('Tab ${tab.tabNumber} akan dibatalkan. Lanjutkan?'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Tidak')),
          FilledButton(
            onPressed: () async {
              Navigator.pop(ctx);
              final result = await ref.read(tabProvider.notifier).cancelTab(tab.id);
              if (result != null && mounted) {
                setState(() => _tab = result);
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Tab dibatalkan'), backgroundColor: AppColors.error),
                );
              }
            },
            style: FilledButton.styleFrom(backgroundColor: AppColors.error),
            child: const Text('Batalkan'),
          ),
        ],
      ),
    );
  }
}
