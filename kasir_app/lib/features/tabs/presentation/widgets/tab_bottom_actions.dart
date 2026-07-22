import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
import '../../../../core/theme/kasira_ds.dart';
import '../../providers/tab_provider.dart';

/// Bar aksi bawah halaman Tab.
///
/// Ditata 2×2, bukan 4-in-a-row seperti sebelumnya: di layar 360dp satu baris
/// isi 4 chip cuma nyisain ~76px per chip, yang maksa label 10px dua baris dan
/// tinggi tap 40px — di bawah ambang 44px dan susah dipencet sambil berdiri di
/// depan kasir. Grid 2×2 ngasih ~150×68px per tile.
///
/// "Pindah Meja" sengaja gak ikut di grid ini — dia aksi level meja yang jarang
/// dipakai, jadi ditaruh di menu header. Yang di sini cuma empat yang dipakai
/// tiap hari.
class TabBottomActions extends StatelessWidget {
  final TabModel tab;
  final NumberFormat currency;
  final VoidCallback onAddOrder;
  final VoidCallback onAddGuests;
  final VoidCallback onMergeTab;
  final VoidCallback onCancel;
  final VoidCallback onPayFull;
  final VoidCallback onSplitBill;

  /// Struk seluruh tab. Wajib ada waktu tab udah lunas: sebelumnya bar ini
  /// render KOSONG begitu status jadi `paid` (dua cabang di bawah dua-duanya
  /// gak match), jadi customer yang minta struk sesudah bayar mentok total.
  final VoidCallback onReceipt;

  const TabBottomActions({
    super.key,
    required this.tab,
    required this.currency,
    required this.onAddOrder,
    required this.onAddGuests,
    required this.onMergeTab,
    required this.onCancel,
    required this.onPayFull,
    required this.onSplitBill,
    required this.onReceipt,
  });

  @override
  Widget build(BuildContext context) {
    final canCancel = tab.paidAmount == 0;

    return Container(
      padding: EdgeInsets.fromLTRB(
        KasiraDS.space4,
        KasiraDS.space4,
        KasiraDS.space4,
        MediaQuery.of(context).padding.bottom + KasiraDS.space4,
      ),
      decoration: BoxDecoration(
        color: KasiraDS.surfaceCard,
        border: const Border(top: BorderSide(color: KasiraDS.borderSubtle)),
        boxShadow: KasiraDS.shadowMd,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (tab.isOpen) ...[
            Row(
              children: [
                Expanded(
                  child: _ActionTile(
                    icon: LucideIcons.plus,
                    label: 'Tambah Pesanan',
                    color: KasiraDS.success,
                    onTap: onAddOrder,
                  ),
                ),
                const SizedBox(width: KasiraDS.space3),
                Expanded(
                  child: _ActionTile(
                    icon: LucideIcons.userPlus,
                    label: 'Tambah Orang',
                    color: KasiraDS.brandSecondary,
                    badge: '${tab.guestCount}',
                    onTap: onAddGuests,
                  ),
                ),
              ],
            ),
            const SizedBox(height: KasiraDS.space3),
            Row(
              children: [
                Expanded(
                  child: _ActionTile(
                    icon: LucideIcons.merge,
                    label: 'Gabung Meja',
                    color: KasiraDS.warning,
                    onTap: onMergeTab,
                  ),
                ),
                const SizedBox(width: KasiraDS.space3),
                Expanded(
                  child: _ActionTile(
                    icon: LucideIcons.x,
                    label: 'Batalkan',
                    color: KasiraDS.danger,
                    onTap: canCancel ? onCancel : null,
                    disabledHint: 'Sudah ada\nyang bayar',
                  ),
                ),
              ],
            ),
            const SizedBox(height: KasiraDS.space4),
          ],
          if (tab.isOpen && tab.totalAmount > 0)
            Row(
              children: [
                Expanded(
                  child: _SecondaryButton(
                    icon: LucideIcons.banknote,
                    label: 'Bayar Lunas',
                    onTap: onPayFull,
                  ),
                ),
                const SizedBox(width: KasiraDS.space3),
                Expanded(
                  child: _PrimaryButton(
                    icon: LucideIcons.split,
                    label: 'Split Bill',
                    onTap: onSplitBill,
                  ),
                ),
                // Pola warkop: item dibayar satu-satu sementara tab-nya masih
                // buka. Yang udah bayar berhak minta struknya sekarang, bukan
                // nunggu semua orang kelar.
                if (tab.paidAmount > 0) ...[
                  const SizedBox(width: KasiraDS.space3),
                  _ReceiptButton(onTap: onReceipt),
                ],
              ],
            )
          else if (tab.isSplitting && tab.remainingAmount > 0)
            Row(
              children: [
                Expanded(
                  child: _PrimaryButton(
                    icon: LucideIcons.banknote,
                    label: 'Bayar Sisa ${currency.format(tab.remainingAmount)}',
                    onTap: onPayFull,
                  ),
                ),
                // Sebagian orang udah bayar duluan di mode split — mereka bisa
                // minta struk kapan aja, gak usah nunggu tab-nya lunas.
                if (tab.paidAmount > 0) ...[
                  const SizedBox(width: KasiraDS.space3),
                  _ReceiptButton(onTap: onReceipt),
                ],
              ],
            )
          else if (tab.paidAmount > 0)
            _SecondaryButton(
              icon: LucideIcons.receipt,
              label: 'Struk',
              onTap: onReceipt,
            ),
        ],
      ),
    );
  }
}

class _ActionTile extends StatelessWidget {
  final IconData icon;
  final String label;
  final Color color;
  final VoidCallback? onTap;
  final String? badge;
  final String? disabledHint;

  const _ActionTile({
    required this.icon,
    required this.label,
    required this.color,
    required this.onTap,
    this.badge,
    this.disabledHint,
  });

  @override
  Widget build(BuildContext context) {
    final enabled = onTap != null;
    final tint = enabled ? color : KasiraDS.neutral400;

    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: KasiraDS.brMd,
        child: Container(
          height: 68,
          padding: const EdgeInsets.symmetric(horizontal: KasiraDS.space3),
          decoration: BoxDecoration(
            color: tint.withOpacity(enabled ? 0.08 : 0.04),
            border: Border.all(color: tint.withOpacity(enabled ? 0.32 : 0.16)),
            borderRadius: KasiraDS.brMd,
          ),
          child: Row(
            children: [
              Container(
                width: 38,
                height: 38,
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  color: tint.withOpacity(enabled ? 0.14 : 0.08),
                  borderRadius: KasiraDS.brSm,
                ),
                child: Icon(icon, size: 20, color: tint),
              ),
              const SizedBox(width: KasiraDS.space2),
              Expanded(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      label,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: KasiraDS.sans(
                        size: 13.5,
                        weight: FontWeight.w700,
                        color: tint,
                        height: 1.15,
                      ),
                    ),
                    if (!enabled && disabledHint != null)
                      Text(
                        disabledHint!.replaceAll('\n', ' '),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: KasiraDS.sans(size: 10.5, color: KasiraDS.textMuted),
                      ),
                  ],
                ),
              ),
              if (badge != null && enabled)
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(
                    color: tint,
                    borderRadius: KasiraDS.brPill,
                  ),
                  child: Text(
                    badge!,
                    style: KasiraDS.sans(
                      size: 12,
                      weight: FontWeight.w800,
                      color: KasiraDS.textOnBrand,
                    ),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}

class _PrimaryButton extends StatelessWidget {
  final IconData icon;
  final String label;
  final VoidCallback onTap;

  const _PrimaryButton({required this.icon, required this.label, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        height: 56,
        alignment: Alignment.center,
        decoration: BoxDecoration(
          gradient: KasiraDS.gradientFrekuensi,
          borderRadius: KasiraDS.brMd,
          boxShadow: KasiraDS.glowBrand,
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, size: 19, color: KasiraDS.textOnBrand),
            const SizedBox(width: KasiraDS.space2),
            Flexible(
              child: Text(
                label,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: KasiraDS.sans(
                  size: 16,
                  weight: FontWeight.w700,
                  color: KasiraDS.textOnBrand,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _SecondaryButton extends StatelessWidget {
  final IconData icon;
  final String label;
  final VoidCallback onTap;

  const _SecondaryButton({required this.icon, required this.label, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        height: 56,
        alignment: Alignment.center,
        decoration: BoxDecoration(
          color: KasiraDS.surfaceCard,
          borderRadius: KasiraDS.brMd,
          border: Border.all(color: KasiraDS.borderDefault),
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, size: 19, color: KasiraDS.textStrong),
            const SizedBox(width: KasiraDS.space2),
            Flexible(
              child: Text(
                label,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: KasiraDS.sans(
                  size: 16,
                  weight: FontWeight.w700,
                  color: KasiraDS.textStrong,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Tombol struk versi ringkas — dipakai waktu dia numpang di baris yang udah
/// keisi tombol bayar, biar label "Bayar Sisa Rp xxx" gak keremas.
class _ReceiptButton extends StatelessWidget {
  final VoidCallback onTap;

  const _ReceiptButton({required this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: 56,
        height: 56,
        alignment: Alignment.center,
        decoration: BoxDecoration(
          color: KasiraDS.surfaceCard,
          borderRadius: KasiraDS.brMd,
          border: Border.all(color: KasiraDS.borderDefault),
        ),
        child: const Icon(LucideIcons.receipt, size: 20, color: KasiraDS.textStrong),
      ),
    );
  }
}
