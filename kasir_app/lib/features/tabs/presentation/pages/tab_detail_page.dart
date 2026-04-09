import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:lucide_icons/lucide_icons.dart';
import '../../../../core/theme/app_colors.dart';
import '../../providers/tab_provider.dart';
import '../widgets/split_bill_modal.dart';
import '../widgets/pay_split_modal.dart';

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
          // Header
          Container(
            padding: const EdgeInsets.fromLTRB(8, 8, 16, 16),
            color: Colors.white,
            child: SafeArea(
              bottom: false,
              child: Column(
                children: [
                  Row(
                    children: [
                      IconButton(
                        icon: const Icon(LucideIcons.arrowLeft),
                        onPressed: () => Navigator.pop(context),
                      ),
                      Text(tab.tabNumber,
                          style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold)),
                      if (tab.customerName != null) ...[
                        const SizedBox(width: 8),
                        Text('• ${tab.customerName}', style: TextStyle(color: AppColors.textSecondary)),
                      ],
                      const Spacer(),
                      _buildStatusBadge(tab.status),
                    ],
                  ),
                  const SizedBox(height: 12),
                  // Summary bar
                  Container(
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: AppColors.primary.withOpacity(0.05),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Row(
                      children: [
                        _buildSummaryItem('Total', _currency.format(tab.totalAmount), AppColors.textPrimary),
                        Container(width: 1, height: 32, color: AppColors.border),
                        _buildSummaryItem('Dibayar', _currency.format(tab.paidAmount), AppColors.success),
                        Container(width: 1, height: 32, color: AppColors.border),
                        _buildSummaryItem('Sisa', _currency.format(tab.remainingAmount),
                            tab.remainingAmount > 0 ? AppColors.warning : AppColors.success),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),

          // Content
          Expanded(
            child: RefreshIndicator(
              onRefresh: _loadTab,
              child: ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  // Info card
                  _buildInfoCard(tab),
                  const SizedBox(height: 16),

                  // Splits section
                  if (tab.splits.isNotEmpty) ...[
                    _buildSectionHeader('Split Bill', LucideIcons.split),
                    const SizedBox(height: 8),
                    ...tab.splits.map((s) => _buildSplitCard(tab, s)),
                    const SizedBox(height: 16),
                  ],
                ],
              ),
            ),
          ),

          // Bottom action bar
          if (tab.isOpen || tab.isSplitting) _buildBottomActions(tab),
        ],
      ),
    );
  }

  Widget _buildSummaryItem(String label, String value, Color color) {
    return Expanded(
      child: Column(
        children: [
          Text(label, style: TextStyle(color: AppColors.textSecondary, fontSize: 12)),
          const SizedBox(height: 4),
          Text(value, style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15, color: color)),
        ],
      ),
    );
  }

  Widget _buildInfoCard(TabModel tab) {
    return Card(
      elevation: 0,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildSectionHeader('Info Tab', LucideIcons.info),
            const SizedBox(height: 12),
            _buildInfoRow(LucideIcons.users, 'Jumlah Tamu', '${tab.guestCount} orang'),
            _buildInfoRow(LucideIcons.shoppingCart, 'Jumlah Order', '${tab.orderIds.length}'),
            if (tab.splitMethod != null)
              _buildInfoRow(LucideIcons.split, 'Metode Split', _splitLabel(tab.splitMethod!)),
            if (tab.notes != null)
              _buildInfoRow(LucideIcons.stickyNote, 'Catatan', tab.notes!),
          ],
        ),
      ),
    );
  }

  Widget _buildInfoRow(IconData icon, String label, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        children: [
          Icon(icon, size: 16, color: AppColors.textSecondary),
          const SizedBox(width: 8),
          Text('$label: ', style: TextStyle(color: AppColors.textSecondary, fontSize: 13)),
          Text(value, style: const TextStyle(fontWeight: FontWeight.w500, fontSize: 13)),
        ],
      ),
    );
  }

  Widget _buildSectionHeader(String title, IconData icon) {
    return Row(
      children: [
        Icon(icon, size: 18, color: AppColors.primary),
        const SizedBox(width: 8),
        Text(title, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
      ],
    );
  }

  Widget _buildSplitCard(TabModel tab, TabSplitModel split) {
    final isPaid = split.isPaid;
    return Card(
      elevation: 0,
      margin: const EdgeInsets.only(bottom: 8),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(color: isPaid ? AppColors.success.withOpacity(0.3) : AppColors.border),
      ),
      child: ListTile(
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
        leading: CircleAvatar(
          backgroundColor: isPaid ? AppColors.success.withOpacity(0.1) : AppColors.primary.withOpacity(0.1),
          child: Icon(
            isPaid ? LucideIcons.checkCircle2 : LucideIcons.user,
            color: isPaid ? AppColors.success : AppColors.primary,
            size: 20,
          ),
        ),
        title: Text(split.label, style: const TextStyle(fontWeight: FontWeight.w600)),
        subtitle: Text(
          _currency.format(split.amount),
          style: TextStyle(
            fontWeight: FontWeight.bold,
            color: isPaid ? AppColors.success : AppColors.textPrimary,
          ),
        ),
        trailing: isPaid
            ? Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: AppColors.success.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Text('Lunas', style: TextStyle(color: AppColors.success, fontWeight: FontWeight.bold, fontSize: 12)),
              )
            : FilledButton(
                onPressed: () => _showPaySplitModal(tab, split),
                style: FilledButton.styleFrom(
                  backgroundColor: AppColors.primary,
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                ),
                child: const Text('Bayar', style: TextStyle(fontSize: 13)),
              ),
      ),
    );
  }

  Widget _buildBottomActions(TabModel tab) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        border: Border(top: BorderSide(color: AppColors.border)),
      ),
      child: Row(
        children: [
          if (tab.isOpen && tab.paidAmount == 0) ...[
            Expanded(
              child: OutlinedButton.icon(
                onPressed: () => _confirmCancel(tab),
                icon: const Icon(LucideIcons.x, size: 18),
                label: const Text('Batalkan'),
                style: OutlinedButton.styleFrom(
                  foregroundColor: AppColors.error,
                  side: const BorderSide(color: AppColors.error),
                  padding: const EdgeInsets.symmetric(vertical: 14),
                ),
              ),
            ),
            const SizedBox(width: 12),
          ],
          Expanded(
            flex: 2,
            child: tab.isOpen
                ? FilledButton.icon(
                    onPressed: tab.totalAmount > 0 ? () => _showSplitBillModal(tab) : null,
                    icon: const Icon(LucideIcons.split, size: 18),
                    label: const Text('Split Bill'),
                    style: FilledButton.styleFrom(
                      backgroundColor: AppColors.primary,
                      padding: const EdgeInsets.symmetric(vertical: 14),
                    ),
                  )
                : FilledButton.icon(
                    onPressed: tab.remainingAmount > 0
                        ? () => _showPayFullModal(tab)
                        : null,
                    icon: const Icon(LucideIcons.banknote, size: 18),
                    label: Text('Bayar Sisa ${_currency.format(tab.remainingAmount)}'),
                    style: FilledButton.styleFrom(
                      backgroundColor: AppColors.success,
                      padding: const EdgeInsets.symmetric(vertical: 14),
                    ),
                  ),
          ),
        ],
      ),
    );
  }

  Widget _buildStatusBadge(String status) {
    final config = {
      'open': ('Aktif', AppColors.info),
      'asking_bill': ('Minta Bill', AppColors.warning),
      'splitting': ('Split Bill', AppColors.primary),
      'paid': ('Lunas', AppColors.success),
      'cancelled': ('Batal', AppColors.error),
    };
    final c = config[status] ?? (status, AppColors.textSecondary);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: c.$2.withOpacity(0.1),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Text(c.$1, style: TextStyle(color: c.$2, fontWeight: FontWeight.bold, fontSize: 12)),
    );
  }

  String _splitLabel(String method) {
    switch (method) {
      case 'equal': return 'Bagi Rata';
      case 'per_item': return 'Per Item';
      case 'custom': return 'Custom';
      case 'full': return 'Bayar Penuh';
      default: return method;
    }
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
        onSplitDone: (updatedTab) {
          setState(() => _tab = updatedTab);
        },
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
        onPaid: (updatedTab) {
          setState(() => _tab = updatedTab);
        },
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
        split: null, // null = pay full remaining
        onPaid: (updatedTab) {
          setState(() => _tab = updatedTab);
        },
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
