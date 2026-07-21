import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../../../../core/localization/business_labels.dart';
import '../../../../core/theme/kasira_ds.dart';

/// Pemilih jumlah tamu — SATU-SATUNYA tempat jumlah orang ditanya.
///
/// Sebelumnya tiap flow nanya sendiri-sendiri, dan flow tab "Meja" kelewat
/// nanya sama sekali sehingga tab kebuat dengan `guest_count = 1` dan bagi
/// rata jadi gak kepake. Dijadiin satu widget biar bug itu gak bisa kambuh
/// cuma di salah satu cabang.
///
/// Dipakai dua skenario:
///  - buka meja kosong (`initial` default 2 — paling umum di warkop/cafe)
///  - ubah jumlah tamu di tab yang lagi jalan (`initial` = guest_count sekarang)
Future<int?> showGuestCountSheet(
  BuildContext context, {
  required String tableName,
  int initial = 2,
  String title = 'Berapa orang?',
  String confirmLabel = 'Lanjut',
  IconData confirmIcon = LucideIcons.arrowRight,
}) {
  return showModalBottomSheet<int>(
    context: context,
    isScrollControlled: true,
    backgroundColor: Colors.transparent,
    builder: (_) => _GuestCountSheet(
      tableName: tableName,
      initial: initial.clamp(1, 50),
      title: title,
      confirmLabel: confirmLabel,
      confirmIcon: confirmIcon,
    ),
  );
}

class _GuestCountSheet extends StatefulWidget {
  final String tableName;
  final int initial;
  final String title;
  final String confirmLabel;
  final IconData confirmIcon;

  const _GuestCountSheet({
    required this.tableName,
    required this.initial,
    required this.title,
    required this.confirmLabel,
    required this.confirmIcon,
  });

  @override
  State<_GuestCountSheet> createState() => _GuestCountSheetState();
}

class _GuestCountSheetState extends State<_GuestCountSheet> {
  late int _count = widget.initial;

  static const _quickPicks = [1, 2, 3, 4, 5, 6, 8, 10];

  void _set(int n) {
    final clamped = n.clamp(1, 50);
    if (clamped == _count) return;
    HapticFeedback.selectionClick();
    setState(() => _count = clamped);
  }

  @override
  Widget build(BuildContext context) {
    final tableLabel = BusinessLabels.getLabel('table');

    return Container(
      decoration: const BoxDecoration(
        color: KasiraDS.surfaceCard,
        borderRadius: BorderRadius.vertical(top: Radius.circular(KasiraDS.radiusXl)),
      ),
      padding: EdgeInsets.only(
        left: KasiraDS.space5,
        right: KasiraDS.space5,
        top: KasiraDS.space3,
        bottom: MediaQuery.of(context).viewInsets.bottom + KasiraDS.space6,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Center(
            child: Container(
              width: 44,
              height: 5,
              decoration: BoxDecoration(
                color: KasiraDS.borderDefault,
                borderRadius: KasiraDS.brPill,
              ),
            ),
          ),
          const SizedBox(height: KasiraDS.space5),
          Text(
            '$tableLabel ${widget.tableName}'.toUpperCase(),
            style: KasiraDS.eyebrow(color: KasiraDS.brandPrimary),
          ),
          const SizedBox(height: KasiraDS.space2),
          Text(widget.title, style: KasiraDS.display(size: 28)),
          const SizedBox(height: KasiraDS.space5),

          // Stepper — angka besar, tombol 56px biar gampang ke-tap sambil berdiri.
          Container(
            padding: const EdgeInsets.symmetric(
              horizontal: KasiraDS.space3,
              vertical: KasiraDS.space3,
            ),
            decoration: BoxDecoration(
              color: KasiraDS.surfaceSunken,
              borderRadius: KasiraDS.brLg,
              border: Border.all(color: KasiraDS.borderSubtle),
            ),
            child: Row(
              children: [
                _StepperButton(
                  icon: LucideIcons.minus,
                  onTap: _count > 1 ? () => _set(_count - 1) : null,
                ),
                Expanded(
                  child: Column(
                    children: [
                      Text(
                        '$_count',
                        style: KasiraDS.display(size: 46, color: KasiraDS.textStrong),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        'orang',
                        style: KasiraDS.sans(size: 13, color: KasiraDS.textMuted),
                      ),
                    ],
                  ),
                ),
                _StepperButton(
                  icon: LucideIcons.plus,
                  onTap: _count < 50 ? () => _set(_count + 1) : null,
                ),
              ],
            ),
          ),
          const SizedBox(height: KasiraDS.space4),

          Text('Pilih cepat', style: KasiraDS.sans(size: 13, color: KasiraDS.textMuted)),
          const SizedBox(height: KasiraDS.space2),
          Wrap(
            spacing: KasiraDS.space2,
            runSpacing: KasiraDS.space2,
            children: _quickPicks.map((n) {
              final active = _count == n;
              return GestureDetector(
                onTap: () => _set(n),
                child: AnimatedContainer(
                  duration: KasiraDS.durFast,
                  curve: KasiraDS.easeStandard,
                  width: 52,
                  height: 52,
                  alignment: Alignment.center,
                  decoration: BoxDecoration(
                    gradient: active ? KasiraDS.gradientFrekuensi : null,
                    color: active ? null : KasiraDS.surfaceSunken,
                    borderRadius: KasiraDS.brMd,
                    border: Border.all(
                      color: active ? Colors.transparent : KasiraDS.borderSubtle,
                    ),
                    boxShadow: active ? KasiraDS.glowPink : null,
                  ),
                  child: Text(
                    '$n',
                    style: KasiraDS.sans(
                      size: 18,
                      weight: FontWeight.w700,
                      color: active ? KasiraDS.textOnBrand : KasiraDS.textStrong,
                    ),
                  ),
                ),
              );
            }).toList(),
          ),
          const SizedBox(height: KasiraDS.space6),

          Row(
            children: [
              Expanded(
                child: SizedBox(
                  height: 56,
                  child: OutlinedButton(
                    onPressed: () => Navigator.pop(context),
                    style: OutlinedButton.styleFrom(
                      side: const BorderSide(color: KasiraDS.borderDefault),
                      shape: RoundedRectangleBorder(borderRadius: KasiraDS.brMd),
                    ),
                    child: Text(
                      'Batal',
                      style: KasiraDS.sans(size: 15, weight: FontWeight.w600),
                    ),
                  ),
                ),
              ),
              const SizedBox(width: KasiraDS.space3),
              Expanded(
                flex: 2,
                child: GestureDetector(
                  onTap: () => Navigator.pop(context, _count),
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
                        Text(
                          '${widget.confirmLabel} · $_count org',
                          style: KasiraDS.sans(
                            size: 16,
                            weight: FontWeight.w700,
                            color: KasiraDS.textOnBrand,
                          ),
                        ),
                        const SizedBox(width: KasiraDS.space2),
                        Icon(widget.confirmIcon, size: 18, color: KasiraDS.textOnBrand),
                      ],
                    ),
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _StepperButton extends StatelessWidget {
  final IconData icon;
  final VoidCallback? onTap;

  const _StepperButton({required this.icon, required this.onTap});

  @override
  Widget build(BuildContext context) {
    final enabled = onTap != null;
    return Material(
      color: enabled ? KasiraDS.surfaceCard : KasiraDS.surfaceSunken,
      borderRadius: KasiraDS.brMd,
      child: InkWell(
        onTap: onTap,
        borderRadius: KasiraDS.brMd,
        child: Container(
          width: 56,
          height: 56,
          alignment: Alignment.center,
          decoration: BoxDecoration(
            borderRadius: KasiraDS.brMd,
            border: Border.all(
              color: enabled ? KasiraDS.borderDefault : KasiraDS.borderSubtle,
            ),
          ),
          child: Icon(
            icon,
            size: 22,
            color: enabled ? KasiraDS.textStrong : KasiraDS.neutral300,
          ),
        ),
      ),
    );
  }
}
