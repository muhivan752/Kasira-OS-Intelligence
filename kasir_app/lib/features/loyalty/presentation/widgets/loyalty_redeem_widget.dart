import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:lucide_icons/lucide_icons.dart';
import '../../../../core/theme/app_colors.dart';
import '../../providers/loyalty_provider.dart';

/// Widget yang muncul di CartPanel ketika pelanggan dipilih.
/// Menampilkan saldo poin + slider untuk redeem.
class LoyaltyRedeemWidget extends ConsumerStatefulWidget {
  final String customerId;
  final double orderTotal;
  final void Function(double pointsToRedeem, double discountRp) onRedeemChanged;

  const LoyaltyRedeemWidget({
    super.key,
    required this.customerId,
    required this.orderTotal,
    required this.onRedeemChanged,
  });

  @override
  ConsumerState<LoyaltyRedeemWidget> createState() => _LoyaltyRedeemWidgetState();
}

class _LoyaltyRedeemWidgetState extends ConsumerState<LoyaltyRedeemWidget> {
  bool _usePoints = false;
  double _pointsToRedeem = 0;

  static const double _redeemRate = 100; // 1 poin = Rp 100
  static const double _minRedeem = 10;

  final _currency = NumberFormat.currency(locale: 'id_ID', symbol: 'Rp ', decimalDigits: 0);

  @override
  Widget build(BuildContext context) {
    final balanceAsync = ref.watch(loyaltyBalanceProvider(widget.customerId));

    return balanceAsync.when(
      loading: () => const Padding(
        padding: EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        child: LinearProgressIndicator(),
      ),
      error: (_, __) => const SizedBox.shrink(),
      data: (balance) {
        if (balance == null || balance.balance < _minRedeem) {
          return Padding(
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
              decoration: BoxDecoration(
                color: AppColors.surfaceVariant,
                borderRadius: BorderRadius.circular(10),
              ),
              child: Row(
                children: [
                  const Icon(LucideIcons.star, size: 16, color: AppColors.textTertiary),
                  const SizedBox(width: 8),
                  Text(
                    balance == null
                        ? 'Memuat poin...'
                        : 'Poin: ${balance.balance.toInt()} (min. redeem ${_minRedeem.toInt()})',
                    style: const TextStyle(color: AppColors.textTertiary, fontSize: 12),
                  ),
                ],
              ),
            ),
          );
        }

        final maxRedeem = balance.balance.clamp(0, widget.orderTotal / _redeemRate).toDouble();

        return Padding(
          padding: const EdgeInsets.fromLTRB(16, 0, 16, 4),
          child: Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: _usePoints
                  ? AppColors.primary.withOpacity(0.06)
                  : AppColors.surfaceVariant,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(
                color: _usePoints ? AppColors.primary.withOpacity(0.4) : AppColors.border,
              ),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Icon(LucideIcons.star,
                        size: 16,
                        color: _usePoints ? AppColors.primary : AppColors.warning),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        '${balance.balance.toInt()} poin  ·  nilai ${_currency.format(balance.redeemValueRp)}',
                        style: TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.w600,
                          color: _usePoints ? AppColors.primary : AppColors.textPrimary,
                        ),
                      ),
                    ),
                    Switch.adaptive(
                      value: _usePoints,
                      activeColor: AppColors.primary,
                      onChanged: (val) {
                        setState(() {
                          _usePoints = val;
                          _pointsToRedeem = val ? maxRedeem : 0;
                        });
                        widget.onRedeemChanged(
                          _usePoints ? _pointsToRedeem : 0,
                          _usePoints ? _pointsToRedeem * _redeemRate : 0,
                        );
                      },
                    ),
                  ],
                ),
                if (_usePoints) ...[
                  const SizedBox(height: 8),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text('Redeem ${_pointsToRedeem.toInt()} poin',
                          style: const TextStyle(fontSize: 12, color: AppColors.textSecondary)),
                      Text(
                        '- ${_currency.format(_pointsToRedeem * _redeemRate)}',
                        style: const TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.bold,
                          color: AppColors.success,
                        ),
                      ),
                    ],
                  ),
                  Slider(
                    value: _pointsToRedeem,
                    min: _minRedeem,
                    max: maxRedeem,
                    divisions: maxRedeem > _minRedeem
                        ? (maxRedeem - _minRedeem).toInt()
                        : 1,
                    activeColor: AppColors.primary,
                    onChanged: (val) {
                      setState(() => _pointsToRedeem = val.floorToDouble());
                      widget.onRedeemChanged(
                        _pointsToRedeem,
                        _pointsToRedeem * _redeemRate,
                      );
                    },
                  ),
                ],
              ],
            ),
          ),
        );
      },
    );
  }
}
