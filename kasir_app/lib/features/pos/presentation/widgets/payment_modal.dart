import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:lucide_icons/lucide_icons.dart';
import '../../../../core/theme/app_colors.dart';

class PaymentModal extends StatefulWidget {
  final double totalAmount;
  final VoidCallback onPaymentSuccess;

  const PaymentModal({
    super.key,
    required this.totalAmount,
    required this.onPaymentSuccess,
  });

  @override
  State<PaymentModal> createState() => _PaymentModalState();
}

class _PaymentModalState extends State<PaymentModal> {
  String _paymentMethod = 'Cash';
  double _amountReceived = 0.0;
  final _amountController = TextEditingController();
  final currencyFormatter = NumberFormat.currency(locale: 'id_ID', symbol: 'Rp ', decimalDigits: 0);

  @override
  void initState() {
    super.initState();
    _amountReceived = widget.totalAmount;
    _amountController.text = widget.totalAmount.toInt().toString();
  }

  @override
  void dispose() {
    _amountController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final change = _amountReceived - widget.totalAmount;
    final isCash = _paymentMethod == 'Cash';

    return Dialog(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24)),
      child: Container(
        width: 800,
        height: 600,
        padding: const EdgeInsets.all(0),
        child: Row(
          children: [
            // Left Side: Payment Methods
            Expanded(
              flex: 4,
              child: Container(
                padding: const EdgeInsets.all(32),
                decoration: const BoxDecoration(
                  color: AppColors.surfaceVariant,
                  borderRadius: BorderRadius.horizontal(left: Radius.circular(24)),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Pilih Metode',
                      style: Theme.of(context).textTheme.headlineMedium,
                    ),
                    const SizedBox(height: 32),
                    _buildMethodBtn('Cash', LucideIcons.banknote),
                    const SizedBox(height: 16),
                    _buildMethodBtn('QRIS', LucideIcons.qrCode),
                    const SizedBox(height: 16),
                    _buildMethodBtn('Kartu Debit/Kredit', LucideIcons.creditCard),
                  ],
                ),
              ),
            ),
            
            // Right Side: Payment Details
            Expanded(
              flex: 6,
              child: Container(
                padding: const EdgeInsets.all(32),
                decoration: const BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.horizontal(right: Radius.circular(24)),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text(
                          'Total Tagihan',
                          style: Theme.of(context).textTheme.titleLarge?.copyWith(color: AppColors.textSecondary),
                        ),
                        IconButton(
                          onPressed: () => Navigator.pop(context),
                          icon: const Icon(LucideIcons.x),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Text(
                      currencyFormatter.format(widget.totalAmount),
                      style: Theme.of(context).textTheme.displayMedium?.copyWith(
                            color: AppColors.primary,
                            fontWeight: FontWeight.bold,
                          ),
                    ),
                    const Divider(height: 48, color: AppColors.border),
                    
                    if (isCash) ...[
                      Text('Uang Diterima', style: Theme.of(context).textTheme.titleMedium),
                      const SizedBox(height: 16),
                      TextField(
                        controller: _amountController,
                        keyboardType: TextInputType.number,
                        style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
                        decoration: const InputDecoration(
                          prefixText: 'Rp ',
                        ),
                        onChanged: (val) {
                          setState(() {
                            _amountReceived = double.tryParse(val) ?? 0.0;
                          });
                        },
                      ),
                      const SizedBox(height: 16),
                      // Quick Cash Buttons
                      Row(
                        children: [
                          _buildQuickCashBtn(widget.totalAmount),
                          const SizedBox(width: 8),
                          _buildQuickCashBtn(100000),
                          const SizedBox(width: 8),
                          _buildQuickCashBtn(50000),
                        ],
                      ),
                      const SizedBox(height: 32),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text('Kembalian', style: Theme.of(context).textTheme.titleLarge),
                          Text(
                            currencyFormatter.format(change > 0 ? change : 0),
                            style: Theme.of(context).textTheme.titleLarge?.copyWith(
                                  color: change >= 0 ? AppColors.success : AppColors.error,
                                  fontWeight: FontWeight.bold,
                                ),
                          ),
                        ],
                      ),
                    ] else ...[
                      // QRIS Mock UI
                      Center(
                        child: Column(
                          children: [
                            Container(
                              width: 200,
                              height: 200,
                              decoration: BoxDecoration(
                                color: AppColors.surfaceVariant,
                                borderRadius: BorderRadius.circular(16),
                                border: Border.all(color: AppColors.border),
                              ),
                              child: const Center(
                                child: Icon(LucideIcons.qrCode, size: 64, color: AppColors.textTertiary),
                              ),
                            ),
                            const SizedBox(height: 24),
                            const Text('Menunggu pembayaran dari pelanggan...'),
                            const SizedBox(height: 16),
                            const CircularProgressIndicator(),
                          ],
                        ),
                      )
                    ],
                    
                    const Spacer(),
                    SizedBox(
                      width: double.infinity,
                      height: 56,
                      child: ElevatedButton(
                        onPressed: (isCash && change < 0) ? null : () {
                          // TODO: Call API to create payment
                          widget.onPaymentSuccess();
                          Navigator.pop(context);
                        },
                        style: ElevatedButton.styleFrom(
                          backgroundColor: (isCash && change < 0) ? AppColors.border : AppColors.primary,
                        ),
                        child: const Text('SELESAIKAN PEMBAYARAN'),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildMethodBtn(String label, IconData icon) {
    final isSelected = _paymentMethod == label;
    return InkWell(
      onTap: () => setState(() => _paymentMethod = label),
      child: Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: isSelected ? AppColors.primary.withOpacity(0.1) : Colors.white,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: isSelected ? AppColors.primary : AppColors.border,
            width: 2,
          ),
        ),
        child: Row(
          children: [
            Icon(icon, color: isSelected ? AppColors.primary : AppColors.textSecondary),
            const SizedBox(width: 16),
            Text(
              label,
              style: TextStyle(
                fontSize: 18,
                fontWeight: isSelected ? FontWeight.bold : FontWeight.w500,
                color: isSelected ? AppColors.primary : AppColors.textPrimary,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildQuickCashBtn(double amount) {
    return Expanded(
      child: OutlinedButton(
        onPressed: () {
          setState(() {
            _amountReceived = amount;
            _amountController.text = amount.toInt().toString();
          });
        },
        style: OutlinedButton.styleFrom(
          padding: const EdgeInsets.symmetric(vertical: 12),
        ),
        child: Text(
          amount == widget.totalAmount ? 'Uang Pas' : currencyFormatter.format(amount),
          style: const TextStyle(fontSize: 14),
        ),
      ),
    );
  }
}
