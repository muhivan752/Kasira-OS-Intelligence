import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
import '../../../../core/theme/kasira_ds.dart';
import '../../providers/tab_provider.dart';

/// Header halaman Tab — panel gradient dengan "sisa tagihan" sebagai angka hero.
///
/// Versi sebelumnya nampilin Total/Dibayar/Sisa sebagai tiga angka 15px yang
/// sama besar, jadi kasir harus baca ketiganya buat tau yang penting: masih
/// kurang berapa. Sekarang sisa jadi angka besar, total & dibayar turun jadi
/// baris pendukung.
class TabHeader extends StatelessWidget {
  final TabModel tab;
  final NumberFormat currency;

  /// Pindah meja — aksi level meja yang jarang dipakai, ditaruh di menu header
  /// biar grid aksi bawah tetap empat yang dipakai tiap hari.
  final VoidCallback? onMoveTable;

  const TabHeader({
    super.key,
    required this.tab,
    required this.currency,
    this.onMoveTable,
  });

  @override
  Widget build(BuildContext context) {
    final paid = tab.totalAmount - tab.remainingAmount;
    final lunas = tab.remainingAmount <= 0;

    return Container(
      decoration: const BoxDecoration(
        gradient: KasiraDS.gradientFrekuensi,
        borderRadius: BorderRadius.vertical(bottom: Radius.circular(KasiraDS.radiusXl)),
      ),
      child: SafeArea(
        bottom: false,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(
            KasiraDS.space2,
            KasiraDS.space2,
            KasiraDS.space4,
            KasiraDS.space5,
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  IconButton(
                    icon: const Icon(LucideIcons.arrowLeft, color: KasiraDS.textOnBrand),
                    onPressed: () => Navigator.pop(context),
                  ),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          tab.tableName ?? tab.tabNumber,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: KasiraDS.display(size: 22, color: KasiraDS.textOnBrand),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          [
                            tab.tabNumber,
                            '${tab.guestCount} org',
                            if (tab.customerName != null) tab.customerName!,
                          ].join(' · '),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: KasiraDS.sans(
                            size: 12.5,
                            color: KasiraDS.textOnBrand.withOpacity(0.75),
                          ),
                        ),
                      ],
                    ),
                  ),
                  TabStatusBadge(status: tab.status),
                  if (onMoveTable != null)
                    IconButton(
                      tooltip: 'Pindah meja',
                      icon: const Icon(
                        LucideIcons.arrowRightLeft,
                        color: KasiraDS.textOnBrand,
                        size: 20,
                      ),
                      onPressed: onMoveTable,
                    ),
                ],
              ),
              const SizedBox(height: KasiraDS.space4),

              // Angka hero — yang kasir cari duluan.
              Padding(
                padding: const EdgeInsets.only(left: KasiraDS.space2),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      lunas ? 'SUDAH LUNAS' : 'SISA TAGIHAN',
                      style: KasiraDS.eyebrow(
                        color: KasiraDS.textOnBrand.withOpacity(0.8),
                      ),
                    ),
                    const SizedBox(height: KasiraDS.space2),
                    FittedBox(
                      fit: BoxFit.scaleDown,
                      alignment: Alignment.centerLeft,
                      child: Text(
                        currency.format(lunas ? tab.totalAmount : tab.remainingAmount),
                        style: KasiraDS.display(size: 40, color: KasiraDS.textOnBrand),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: KasiraDS.space4),

              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: KasiraDS.space4,
                  vertical: KasiraDS.space3,
                ),
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.16),
                  borderRadius: KasiraDS.brMd,
                ),
                child: Row(
                  children: [
                    _stat('Total', currency.format(tab.totalAmount)),
                    Container(
                      width: 1,
                      height: 28,
                      color: Colors.white.withOpacity(0.25),
                    ),
                    // "Dibayar" = total - sisa. Pakai computed (bukan tab.paidAmount
                    // raw) karena pay-items adhoc gak update tab.paid_amount (warkop
                    // pattern, source of truth = items.paid_at). Backend
                    // remaining_amount sudah include semua: split/full + items adhoc.
                    _stat('Dibayar', currency.format(paid)),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _stat(String label, String value) {
    return Expanded(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: KasiraDS.sans(
              size: 11.5,
              color: KasiraDS.textOnBrand.withOpacity(0.75),
            ),
          ),
          const SizedBox(height: 3),
          FittedBox(
            fit: BoxFit.scaleDown,
            alignment: Alignment.centerLeft,
            child: Text(
              value,
              style: KasiraDS.sans(
                size: 17,
                weight: FontWeight.w800,
                color: KasiraDS.textOnBrand,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class TabStatusBadge extends StatelessWidget {
  final String status;

  /// Header pakai gradient gelap, sedangkan badge yang sama juga dipakai di
  /// atas surface terang (daftar tab). `onBrand` nentuin kontrasnya.
  final bool onBrand;

  const TabStatusBadge({super.key, required this.status, this.onBrand = true});

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
      padding: const EdgeInsets.symmetric(
        horizontal: KasiraDS.space3,
        vertical: 6,
      ),
      decoration: BoxDecoration(
        color: onBrand ? Colors.white.withOpacity(0.22) : c.$2.withOpacity(0.12),
        borderRadius: KasiraDS.brPill,
      ),
      child: Text(
        c.$1,
        style: KasiraDS.sans(
          size: 12,
          weight: FontWeight.w700,
          color: onBrand ? KasiraDS.textOnBrand : c.$2,
        ),
      ),
    );
  }
}
