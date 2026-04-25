import 'package:flutter/material.dart';
import 'package:lucide_icons/lucide_icons.dart';
import '../../../../core/theme/app_colors.dart';
import '../../providers/tab_provider.dart';

class TabInfoCard extends StatelessWidget {
  final TabModel tab;

  const TabInfoCard({super.key, required this.tab});

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 0,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(LucideIcons.info, size: 18, color: AppColors.primary),
                const SizedBox(width: 8),
                const Text('Info Tab', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
              ],
            ),
            const SizedBox(height: 12),
            if (tab.tableName != null)
              _buildInfoRow(LucideIcons.armchair, 'Meja', tab.tableName!),
            _buildInfoRow(LucideIcons.users, 'Jumlah Tamu', '${tab.guestCount} orang'),
            _buildInfoRow(LucideIcons.shoppingCart, 'Total Pesanan',
                '${tab.orderIds.length} pesanan'),
            if (tab.splits.isNotEmpty) ...[
              _buildInfoRow(
                LucideIcons.split,
                'Pembayaran',
                _buildPaymentSummary(tab),
                valueColor: tab.splits.any((s) => !s.isPaid) ? AppColors.warning : AppColors.success,
              ),
            ] else if (tab.splitMethod != null)
              _buildInfoRow(LucideIcons.split, 'Metode Split', _splitLabel(tab.splitMethod!)),
            if (tab.notes != null)
              _buildInfoRow(LucideIcons.stickyNote, 'Catatan', tab.notes!),
          ],
        ),
      ),
    );
  }

  Widget _buildInfoRow(IconData icon, String label, String value, {Color? valueColor}) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        children: [
          Icon(icon, size: 16, color: AppColors.textSecondary),
          const SizedBox(width: 8),
          Text('$label: ', style: const TextStyle(color: AppColors.textSecondary, fontSize: 13)),
          Expanded(
            child: Text(
              value,
              style: TextStyle(
                fontWeight: FontWeight.w600,
                fontSize: 13,
                color: valueColor ?? AppColors.textPrimary,
              ),
            ),
          ),
        ],
      ),
    );
  }

  /// Summary string utk row "Pembayaran" — show split count + paid/unpaid.
  /// Contoh output: "2 split (1 lunas, 1 belum)"
  String _buildPaymentSummary(TabModel tab) {
    final total = tab.splits.length;
    final paid = tab.splits.where((s) => s.isPaid).length;
    final unpaid = total - paid;
    if (paid == 0) return '$total split (semua belum lunas)';
    if (unpaid == 0) return '$total split (semua lunas ✓)';
    return '$total split ($paid lunas, $unpaid belum)';
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
}
