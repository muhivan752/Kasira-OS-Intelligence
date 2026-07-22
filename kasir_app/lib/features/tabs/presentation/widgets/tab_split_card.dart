import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
import '../../../../core/theme/kasira_ds.dart';
import '../../providers/tab_provider.dart';

/// Satu baris split bill. Nominal jadi elemen paling besar (itu yang dibaca
/// kasir waktu nagih), tombol Bayar dinaikin ke 44px biar ke-tap sekali.
class TabSplitCard extends StatelessWidget {
  final TabSplitModel split;
  final NumberFormat currency;
  final VoidCallback? onPay;

  /// Dipanggil waktu kasir mencet ikon struk di split yang udah lunas.
  ///
  /// Ini satu-satunya jalan ke struk PER-ORANG: Riwayat cuma nyimpen struk order
  /// penuh, jadi kalau yang bayar split minta struknya sendiri, gak ada pintu
  /// lain. Sebelumnya struk split cuma sempat keluar sekali di detik pembayaran.
  final VoidCallback? onReceipt;

  const TabSplitCard({
    super.key,
    required this.split,
    required this.currency,
    this.onPay,
    this.onReceipt,
  });

  @override
  Widget build(BuildContext context) {
    final isPaid = split.isPaid;
    final accent = isPaid ? KasiraDS.success : KasiraDS.brandPrimary;

    return Container(
      margin: const EdgeInsets.only(bottom: KasiraDS.space2),
      padding: const EdgeInsets.all(KasiraDS.space3),
      decoration: BoxDecoration(
        color: KasiraDS.surfaceCard,
        borderRadius: KasiraDS.brLg,
        border: Border.all(
          color: isPaid ? KasiraDS.success.withOpacity(0.35) : KasiraDS.borderSubtle,
        ),
        boxShadow: KasiraDS.shadowXs,
      ),
      child: Row(
        children: [
          Container(
            width: 44,
            height: 44,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              color: accent.withOpacity(0.12),
              borderRadius: KasiraDS.brMd,
            ),
            child: Icon(
              isPaid ? LucideIcons.checkCheck : LucideIcons.user,
              color: accent,
              size: 21,
            ),
          ),
          const SizedBox(width: KasiraDS.space3),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  split.label,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: KasiraDS.sans(
                    size: 13,
                    weight: FontWeight.w600,
                    color: KasiraDS.textMuted,
                  ),
                ),
                const SizedBox(height: 2),
                FittedBox(
                  fit: BoxFit.scaleDown,
                  alignment: Alignment.centerLeft,
                  child: Text(
                    currency.format(split.amount),
                    style: KasiraDS.display(
                      size: 20,
                      color: isPaid ? KasiraDS.success : KasiraDS.textStrong,
                    ),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: KasiraDS.space2),
          if (isPaid)
            Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: KasiraDS.space3,
                    vertical: 6,
                  ),
                  decoration: BoxDecoration(
                    color: KasiraDS.success.withOpacity(0.12),
                    borderRadius: KasiraDS.brPill,
                  ),
                  child: Text(
                    'Lunas',
                    style: KasiraDS.sans(
                      size: 12,
                      weight: FontWeight.w700,
                      color: KasiraDS.success,
                    ),
                  ),
                ),
                if (onReceipt != null) ...[
                  const SizedBox(width: KasiraDS.space2),
                  InkWell(
                    onTap: onReceipt,
                    borderRadius: KasiraDS.brMd,
                    child: Container(
                      width: 44,
                      height: 44,
                      alignment: Alignment.center,
                      decoration: BoxDecoration(
                        borderRadius: KasiraDS.brMd,
                        border: Border.all(color: KasiraDS.borderSubtle),
                      ),
                      child: const Icon(LucideIcons.receipt,
                          size: 18, color: KasiraDS.brandPrimary),
                    ),
                  ),
                ],
              ],
            )
          else
            GestureDetector(
              onTap: onPay,
              child: Container(
                height: 44,
                padding: const EdgeInsets.symmetric(horizontal: KasiraDS.space5),
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  gradient: KasiraDS.gradientFrekuensi,
                  borderRadius: KasiraDS.brMd,
                  boxShadow: KasiraDS.glowPink,
                ),
                child: Text(
                  'Bayar',
                  style: KasiraDS.sans(
                    size: 14.5,
                    weight: FontWeight.w700,
                    color: KasiraDS.textOnBrand,
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}
