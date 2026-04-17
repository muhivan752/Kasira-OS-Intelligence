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
          Text('$label: ', style: const TextStyle(color: AppColors.textSecondary, fontSize: 13)),
          Text(value, style: const TextStyle(fontWeight: FontWeight.w500, fontSize: 13)),
        ],
      ),
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
}
