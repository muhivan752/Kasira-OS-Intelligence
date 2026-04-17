import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:lucide_icons/lucide_icons.dart';
import '../../../../core/theme/app_colors.dart';
import '../../providers/tab_provider.dart';

class TabHeader extends StatelessWidget {
  final TabModel tab;
  final NumberFormat currency;

  const TabHeader({super.key, required this.tab, required this.currency});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(8, 8, 16, 16),
      color: AppColors.surface,
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
                  Text('• ${tab.customerName}', style: const TextStyle(color: AppColors.textSecondary)),
                ],
                const Spacer(),
                TabStatusBadge(status: tab.status),
              ],
            ),
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: AppColors.primary.withOpacity(0.05),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Row(
                children: [
                  _buildSummaryItem('Total', currency.format(tab.totalAmount), AppColors.textPrimary),
                  Container(width: 1, height: 32, color: AppColors.border),
                  _buildSummaryItem('Dibayar', currency.format(tab.paidAmount), AppColors.success),
                  Container(width: 1, height: 32, color: AppColors.border),
                  _buildSummaryItem('Sisa', currency.format(tab.remainingAmount),
                      tab.remainingAmount > 0 ? AppColors.warning : AppColors.success),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSummaryItem(String label, String value, Color color) {
    return Expanded(
      child: Column(
        children: [
          Text(label, style: const TextStyle(color: AppColors.textSecondary, fontSize: 12)),
          const SizedBox(height: 4),
          Text(value, style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15, color: color)),
        ],
      ),
    );
  }
}

class TabStatusBadge extends StatelessWidget {
  final String status;

  const TabStatusBadge({super.key, required this.status});

  @override
  Widget build(BuildContext context) {
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
}
