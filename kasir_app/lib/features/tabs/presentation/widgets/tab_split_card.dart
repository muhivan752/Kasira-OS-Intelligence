import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
import '../../../../core/theme/kasira_ds.dart';
import '../../providers/tab_provider.dart';

class TabSplitCard extends StatelessWidget {
  final TabSplitModel split;
  final NumberFormat currency;
  final VoidCallback? onPay;

  const TabSplitCard({
    super.key,
    required this.split,
    required this.currency,
    this.onPay,
  });

  @override
  Widget build(BuildContext context) {
    final isPaid = split.isPaid;
    return Card(
      elevation: 0,
      margin: const EdgeInsets.only(bottom: 8),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(color: isPaid ? KasiraDS.success.withOpacity(0.3) : KasiraDS.borderSubtle),
      ),
      child: ListTile(
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
        leading: CircleAvatar(
          backgroundColor: isPaid ? KasiraDS.success.withOpacity(0.1) : KasiraDS.brandPrimary.withOpacity(0.1),
          child: Icon(
            isPaid ? LucideIcons.checkCircle2 : LucideIcons.user,
            color: isPaid ? KasiraDS.success : KasiraDS.brandPrimary,
            size: 20,
          ),
        ),
        title: Text(split.label, style: const TextStyle(fontWeight: FontWeight.w600)),
        subtitle: Text(
          currency.format(split.amount),
          style: TextStyle(
            fontWeight: FontWeight.bold,
            color: isPaid ? KasiraDS.success : KasiraDS.textStrong,
          ),
        ),
        trailing: isPaid
            ? Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: KasiraDS.success.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Text('Lunas', style: TextStyle(color: KasiraDS.success, fontWeight: FontWeight.bold, fontSize: 12)),
              )
            : FilledButton(
                onPressed: onPay,
                style: FilledButton.styleFrom(
                  backgroundColor: KasiraDS.brandPrimary,
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                ),
                child: const Text('Bayar', style: TextStyle(fontSize: 13)),
              ),
      ),
    );
  }
}
