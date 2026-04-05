import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:lucide_icons/lucide_icons.dart';
import 'package:go_router/go_router.dart';
import '../../../../core/theme/app_colors.dart';
import 'receipt_preview_page.dart';

class PaymentSuccessPage extends StatefulWidget {
  final double totalAmount;
  final double amountPaid;
  final String paymentMethod;
  final String orderId;
  final String displayNumber;
  final List<ReceiptItem> items;

  const PaymentSuccessPage({
    super.key,
    required this.totalAmount,
    required this.amountPaid,
    required this.paymentMethod,
    required this.orderId,
    required this.displayNumber,
    this.items = const [],
  });

  @override
  State<PaymentSuccessPage> createState() => _PaymentSuccessPageState();
}

class _PaymentSuccessPageState extends State<PaymentSuccessPage>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _scaleAnim;
  late Animation<double> _fadeAnim;

  final _currency = NumberFormat.currency(locale: 'id_ID', symbol: 'Rp ', decimalDigits: 0);

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 500),
    );
    _scaleAnim = Tween<double>(begin: 0.5, end: 1.0).animate(
      CurvedAnimation(parent: _controller, curve: Curves.elasticOut),
    );
    _fadeAnim = CurvedAnimation(parent: _controller, curve: Curves.easeIn);
    _controller.forward();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  double get _change => widget.amountPaid - widget.totalAmount;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF0FDF4),
      body: Center(
        child: FadeTransition(
          opacity: _fadeAnim,
          child: Container(
            width: 480,
            padding: const EdgeInsets.all(48),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(28),
              boxShadow: [
                BoxShadow(
                  color: AppColors.success.withOpacity(0.15),
                  blurRadius: 40,
                  offset: const Offset(0, 10),
                ),
              ],
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                // Success icon
                ScaleTransition(
                  scale: _scaleAnim,
                  child: Container(
                    width: 100,
                    height: 100,
                    decoration: const BoxDecoration(
                      color: AppColors.success,
                      shape: BoxShape.circle,
                    ),
                    child: const Icon(LucideIcons.check, color: Colors.white, size: 52),
                  ),
                ),
                const SizedBox(height: 28),
                Text(
                  'Pembayaran Berhasil!',
                  style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                        fontWeight: FontWeight.bold,
                        color: AppColors.success,
                      ),
                ),
                const SizedBox(height: 8),
                Text(
                  'Order #${widget.displayNumber}',
                  style: const TextStyle(color: AppColors.textSecondary, fontSize: 16),
                ),
                const SizedBox(height: 32),

                // Payment details card
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(24),
                  decoration: BoxDecoration(
                    color: AppColors.surfaceVariant,
                    borderRadius: BorderRadius.circular(16),
                  ),
                  child: Column(
                    children: [
                      _buildRow('Total Tagihan', _currency.format(widget.totalAmount),
                          isBold: true, valueColor: AppColors.textPrimary),
                      const SizedBox(height: 12),
                      _buildRow(
                        'Metode Pembayaran',
                        widget.paymentMethod,
                        valueColor: AppColors.primary,
                      ),
                      if (widget.paymentMethod == 'Cash') ...[
                        const SizedBox(height: 12),
                        _buildRow('Uang Diterima', _currency.format(widget.amountPaid)),
                        const Divider(height: 24, color: AppColors.border),
                        _buildRow(
                          'Kembalian',
                          _currency.format(_change > 0 ? _change : 0),
                          isBold: true,
                          valueColor: AppColors.success,
                        ),
                      ],
                    ],
                  ),
                ),
                const SizedBox(height: 32),

                // Action buttons
                Row(
                  children: [
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: () {
                          context.push('/receipt', extra: {
                            'orderId': widget.orderId,
                            'displayNumber': widget.displayNumber,
                            'totalAmount': widget.totalAmount,
                            'amountPaid': widget.amountPaid,
                            'changeAmount': widget.amountPaid - widget.totalAmount,
                            'paymentMethod': widget.paymentMethod,
                            'items': widget.items,
                          });
                        },
                        icon: const Icon(LucideIcons.receipt, size: 18),
                        label: const Text('Lihat Struk'),
                        style: OutlinedButton.styleFrom(
                          padding: const EdgeInsets.symmetric(vertical: 14),
                        ),
                      ),
                    ),
                    const SizedBox(width: 16),
                    Expanded(
                      child: ElevatedButton.icon(
                        onPressed: () {
                          context.go('/dashboard');
                        },
                        icon: const Icon(LucideIcons.arrowRight, size: 18),
                        label: const Text('Transaksi Baru'),
                        style: ElevatedButton.styleFrom(
                          padding: const EdgeInsets.symmetric(vertical: 14),
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildRow(String label, String value,
      {bool isBold = false, Color? valueColor}) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(
          label,
          style: TextStyle(
            color: AppColors.textSecondary,
            fontWeight: isBold ? FontWeight.bold : FontWeight.normal,
          ),
        ),
        Text(
          value,
          style: TextStyle(
            color: valueColor ?? AppColors.textPrimary,
            fontWeight: isBold ? FontWeight.bold : FontWeight.w600,
            fontSize: isBold ? 18 : 14,
          ),
        ),
      ],
    );
  }
}
