import 'package:flutter/material.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
import '../../../../core/theme/kasira_ds.dart';
import '../../providers/tab_provider.dart';

/// Kartu info tab. Meja / jumlah tamu / jumlah pesanan naik jadi tiga tile
/// sejajar biar kebaca sekilas; sisanya (metode split, catatan) turun jadi
/// baris teks. Sebelumnya semua disamain sebagai baris ikon 13px.
class TabInfoCard extends StatelessWidget {
  final TabModel tab;

  const TabInfoCard({super.key, required this.tab});

  @override
  Widget build(BuildContext context) {
    final extraRows = <Widget>[
      if (tab.splits.isNotEmpty)
        _row(
          LucideIcons.split,
          'Pembayaran',
          _paymentSummary(tab),
          valueColor:
              tab.splits.any((s) => !s.isPaid) ? KasiraDS.warning : KasiraDS.success,
        )
      else if (tab.splitMethod != null)
        _row(LucideIcons.split, 'Metode split', _splitLabel(tab.splitMethod!)),
      if (tab.notes != null) _row(LucideIcons.stickyNote, 'Catatan', tab.notes!),
    ];

    return Container(
      padding: const EdgeInsets.all(KasiraDS.space4),
      decoration: BoxDecoration(
        color: KasiraDS.surfaceCard,
        borderRadius: KasiraDS.brLg,
        border: Border.all(color: KasiraDS.borderSubtle),
        boxShadow: KasiraDS.shadowXs,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: _Tile(
                  icon: LucideIcons.armchair,
                  label: 'Meja',
                  value: tab.tableName ?? '—',
                ),
              ),
              const SizedBox(width: KasiraDS.space2),
              Expanded(
                child: _Tile(
                  icon: LucideIcons.users,
                  label: 'Tamu',
                  value: '${tab.guestCount}',
                  suffix: 'org',
                  highlight: true,
                ),
              ),
              const SizedBox(width: KasiraDS.space2),
              Expanded(
                child: _Tile(
                  icon: LucideIcons.shoppingCart,
                  label: 'Pesanan',
                  value: '${tab.orderIds.length}',
                ),
              ),
            ],
          ),
          if (extraRows.isNotEmpty) ...[
            const SizedBox(height: KasiraDS.space4),
            ...extraRows,
          ],
        ],
      ),
    );
  }

  Widget _row(IconData icon, String label, String value, {Color? valueColor}) {
    return Padding(
      padding: const EdgeInsets.only(top: KasiraDS.space2),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, size: 16, color: KasiraDS.textMuted),
          const SizedBox(width: KasiraDS.space2),
          Text('$label ', style: KasiraDS.sans(size: 13, color: KasiraDS.textMuted)),
          Expanded(
            child: Text(
              value,
              style: KasiraDS.sans(
                size: 13,
                weight: FontWeight.w600,
                color: valueColor ?? KasiraDS.textStrong,
              ),
            ),
          ),
        ],
      ),
    );
  }

  /// Contoh output: "2 split (1 lunas, 1 belum)"
  String _paymentSummary(TabModel tab) {
    final total = tab.splits.length;
    final paid = tab.splits.where((s) => s.isPaid).length;
    final unpaid = total - paid;
    if (paid == 0) return '$total split (semua belum lunas)';
    if (unpaid == 0) return '$total split (semua lunas ✓)';
    return '$total split ($paid lunas, $unpaid belum)';
  }

  String _splitLabel(String method) {
    switch (method) {
      case 'equal':
        return 'Bagi Rata';
      case 'per_item':
        return 'Per Item';
      case 'custom':
        return 'Nominal Custom';
      case 'full':
        return 'Bayar Penuh';
      default:
        return method;
    }
  }
}

class _Tile extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;
  final String? suffix;
  final bool highlight;

  const _Tile({
    required this.icon,
    required this.label,
    required this.value,
    this.suffix,
    this.highlight = false,
  });

  @override
  Widget build(BuildContext context) {
    final tint = highlight ? KasiraDS.brandPrimary : KasiraDS.textMuted;
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: KasiraDS.space3,
        vertical: KasiraDS.space3,
      ),
      decoration: BoxDecoration(
        color: highlight
            ? KasiraDS.brandPrimary.withOpacity(0.07)
            : KasiraDS.surfaceSunken,
        borderRadius: KasiraDS.brMd,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, size: 14, color: tint),
              const SizedBox(width: 5),
              Flexible(
                child: Text(
                  label,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: KasiraDS.sans(size: 11.5, color: tint),
                ),
              ),
            ],
          ),
          const SizedBox(height: KasiraDS.space1),
          Row(
            crossAxisAlignment: CrossAxisAlignment.baseline,
            textBaseline: TextBaseline.alphabetic,
            children: [
              Flexible(
                child: Text(
                  value,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: KasiraDS.display(
                    size: 18,
                    color: highlight ? KasiraDS.brandPrimary : KasiraDS.textStrong,
                  ),
                ),
              ),
              if (suffix != null) ...[
                const SizedBox(width: 3),
                Text(
                  suffix!,
                  style: KasiraDS.sans(size: 11, color: KasiraDS.textMuted),
                ),
              ],
            ],
          ),
        ],
      ),
    );
  }
}
