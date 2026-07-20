import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
import '../../../../core/theme/kasira_ds.dart';
import '../../providers/tab_provider.dart';

class TabBottomActions extends StatelessWidget {
  final TabModel tab;
  final NumberFormat currency;
  final VoidCallback onAddOrder;
  final VoidCallback onMoveTable;
  final VoidCallback onMergeTab;
  final VoidCallback onCancel;
  final VoidCallback onPayFull;
  final VoidCallback onSplitBill;

  const TabBottomActions({
    super.key,
    required this.tab,
    required this.currency,
    required this.onAddOrder,
    required this.onMoveTable,
    required this.onMergeTab,
    required this.onCancel,
    required this.onPayFull,
    required this.onSplitBill,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: KasiraDS.surfaceCard,
        border: Border(top: BorderSide(color: KasiraDS.borderSubtle)),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (tab.isOpen)
            Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: Row(
                children: [
                  _buildActionChip(LucideIcons.plus, 'Tambah\nPesanan', const Color(0xFF059669), onAddOrder),
                  const SizedBox(width: 8),
                  _buildActionChip(LucideIcons.arrowRightLeft, 'Pindah\nMeja', KasiraDS.info, onMoveTable),
                  const SizedBox(width: 8),
                  _buildActionChip(LucideIcons.merge, 'Gabung\nMeja', KasiraDS.warning, onMergeTab),
                  if (tab.paidAmount == 0) ...[
                    const SizedBox(width: 8),
                    _buildActionChip(LucideIcons.x, 'Batalkan', KasiraDS.danger, onCancel),
                  ],
                ],
              ),
            ),
          Row(
            children: [
              if (tab.isOpen && tab.totalAmount > 0) ...[
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: onPayFull,
                    icon: const Icon(LucideIcons.banknote, size: 18),
                    label: const Text('Bayar Lunas'),
                    style: OutlinedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(vertical: 14),
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: FilledButton.icon(
                    onPressed: onSplitBill,
                    icon: const Icon(LucideIcons.split, size: 18),
                    label: const Text('Split Bill'),
                    style: FilledButton.styleFrom(
                      backgroundColor: KasiraDS.brandPrimary,
                      padding: const EdgeInsets.symmetric(vertical: 14),
                    ),
                  ),
                ),
              ] else if (tab.isSplitting && tab.remainingAmount > 0)
                Expanded(
                  child: FilledButton.icon(
                    onPressed: onPayFull,
                    icon: const Icon(LucideIcons.banknote, size: 18),
                    label: Text('Bayar Sisa ${currency.format(tab.remainingAmount)}'),
                    style: FilledButton.styleFrom(
                      backgroundColor: KasiraDS.success,
                      padding: const EdgeInsets.symmetric(vertical: 14),
                    ),
                  ),
                ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildActionChip(IconData icon, String label, Color color, VoidCallback onTap) {
    return Expanded(
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(10),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 8),
          decoration: BoxDecoration(
            color: color.withOpacity(0.08),
            border: Border.all(color: color.withOpacity(0.3)),
            borderRadius: BorderRadius.circular(10),
          ),
          child: Column(
            children: [
              Icon(icon, size: 18, color: color),
              const SizedBox(height: 4),
              Text(
                label,
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 10, fontWeight: FontWeight.w600, color: color, height: 1.2),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
