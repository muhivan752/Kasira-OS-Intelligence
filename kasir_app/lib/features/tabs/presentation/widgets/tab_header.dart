import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
import '../../../../core/theme/kasira_ds.dart';
import '../../providers/tab_provider.dart';

class TabHeader extends StatelessWidget {
  final TabModel tab;
  final NumberFormat currency;

  const TabHeader({super.key, required this.tab, required this.currency});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(8, 8, 16, 16),
      color: KasiraDS.surfaceCard,
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
                  Text('• ${tab.customerName}', style: const TextStyle(color: KasiraDS.textMuted)),
                ],
                const Spacer(),
                TabStatusBadge(status: tab.status),
              ],
            ),
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: KasiraDS.brandPrimary.withOpacity(0.05),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Row(
                children: [
                  _buildSummaryItem('Total', currency.format(tab.totalAmount), KasiraDS.textStrong),
                  Container(width: 1, height: 32, color: KasiraDS.borderSubtle),
                  // "Dibayar" = total - sisa. Pakai computed (bukan tab.paidAmount raw)
                  // karena pay-items adhoc gak update tab.paid_amount (warkop pattern,
                  // source of truth = items.paid_at). Backend remaining_amount sudah
                  // include semua: split/full + items adhoc.
                  _buildSummaryItem('Dibayar',
                      currency.format(tab.totalAmount - tab.remainingAmount),
                      KasiraDS.success),
                  Container(width: 1, height: 32, color: KasiraDS.borderSubtle),
                  _buildSummaryItem('Sisa', currency.format(tab.remainingAmount),
                      tab.remainingAmount > 0 ? KasiraDS.warning : KasiraDS.success),
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
          Text(label, style: const TextStyle(color: KasiraDS.textMuted, fontSize: 12)),
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
      'open': ('Aktif', KasiraDS.info),
      'asking_bill': ('Minta Bill', KasiraDS.warning),
      'splitting': ('Split Bill', KasiraDS.brandPrimary),
      'paid': ('Lunas', KasiraDS.success),
      'cancelled': ('Batal', KasiraDS.danger),
    };
    final c = config[status] ?? (status, KasiraDS.textMuted);
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
