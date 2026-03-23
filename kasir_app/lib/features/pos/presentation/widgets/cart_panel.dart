import 'package:flutter/material.dart';
import 'package:lucide_icons/lucide_icons.dart';
import 'package:intl/intl.dart';
import '../../../../core/theme/app_colors.dart';
import 'payment_modal.dart';
import '../../../customers/presentation/widgets/customer_selection_modal.dart';

class CartPanel extends StatefulWidget {
  const CartPanel({super.key});

  @override
  State<CartPanel> createState() => _CartPanelState();
}

class _CartPanelState extends State<CartPanel> {
  String _orderType = 'Dine In';
  final currencyFormatter = NumberFormat.currency(locale: 'id_ID', symbol: 'Rp ', decimalDigits: 0);

  void _showPaymentModal(BuildContext context) {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => PaymentModal(
        totalAmount: 82500,
        onPaymentSuccess: () {
          // Show success snackbar or navigate
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Pembayaran Berhasil!'),
              backgroundColor: AppColors.success,
            ),
          );
        },
      ),
    );
  }

  void _showCustomerSelectionModal() {
    showDialog(
      context: context,
      builder: (context) => const CustomerSelectionModal(),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        // Header
        Container(
          padding: const EdgeInsets.all(24),
          decoration: const BoxDecoration(
            border: Border(bottom: BorderSide(color: AppColors.border)),
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'Pesanan Saat Ini',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              IconButton(
                onPressed: () {},
                icon: const Icon(LucideIcons.trash2, color: AppColors.error),
              ),
            ],
          ),
        ),

        // Order Type Selector
        Padding(
          padding: const EdgeInsets.all(24),
          child: Row(
            children: [
              _buildOrderTypeBtn('Dine In', LucideIcons.utensils),
              const SizedBox(width: 12),
              _buildOrderTypeBtn('Takeaway', LucideIcons.shoppingBag),
            ],
          ),
        ),

        // Customer Selection
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 24),
          child: InkWell(
            onTap: _showCustomerSelectionModal,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              decoration: BoxDecoration(
                color: AppColors.surfaceVariant,
                borderRadius: BorderRadius.circular(12),
              ),
              child: const Row(
                children: [
                  Icon(LucideIcons.user, color: AppColors.textSecondary, size: 20),
                  SizedBox(width: 12),
                  Text('Pilih Pelanggan', style: TextStyle(color: AppColors.textSecondary)),
                  Spacer(),
                  Icon(LucideIcons.chevronRight, color: AppColors.textSecondary, size: 20),
                ],
              ),
            ),
          ),
        ),

        const SizedBox(height: 16),

        // Cart Items
        Expanded(
          child: ListView.builder(
            padding: const EdgeInsets.symmetric(horizontal: 24),
            itemCount: 3, // Dummy items
            itemBuilder: (context, index) {
              return _buildCartItem(
                name: 'Kopi Susu Gula Aren ${index + 1}',
                price: 25000.0,
                qty: 1,
              );
            },
          ),
        ),

        // Summary & Pay Button
        Container(
          padding: const EdgeInsets.all(24),
          decoration: BoxDecoration(
            color: Colors.white,
            boxShadow: [
              BoxShadow(
                color: Colors.black.withOpacity(0.05),
                blurRadius: 10,
                offset: const Offset(0, -5),
              ),
            ],
          ),
          child: Column(
            children: [
              _buildSummaryRow('Subtotal', 75000),
              const SizedBox(height: 8),
              _buildSummaryRow('Pajak (10%)', 7500),
              const Divider(height: 32),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    'Total',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  Text(
                    currencyFormatter.format(82500),
                    style: Theme.of(context).textTheme.titleLarge?.copyWith(
                          color: AppColors.primary,
                          fontWeight: FontWeight.bold,
                        ),
                  ),
                ],
              ),
              const SizedBox(height: 24),
              SizedBox(
                width: double.infinity,
                height: 56,
                child: ElevatedButton(
                  onPressed: () => _showPaymentModal(context),
                  child: const Text('BAYAR SEKARANG'),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildOrderTypeBtn(String label, IconData icon) {
    final isSelected = _orderType == label;
    return Expanded(
      child: InkWell(
        onTap: () => setState(() => _orderType = label),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 12),
          decoration: BoxDecoration(
            color: isSelected ? AppColors.primary.withOpacity(0.1) : Colors.white,
            border: Border.all(
              color: isSelected ? AppColors.primary : AppColors.border,
            ),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(
                icon,
                size: 18,
                color: isSelected ? AppColors.primary : AppColors.textSecondary,
              ),
              const SizedBox(width: 8),
              Text(
                label,
                style: TextStyle(
                  color: isSelected ? AppColors.primary : AppColors.textSecondary,
                  fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildCartItem({required String name, required double price, required int qty}) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Qty Controls
          Container(
            decoration: BoxDecoration(
              border: Border.all(color: AppColors.border),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Column(
              children: [
                InkWell(
                  onTap: () {},
                  child: const Padding(
                    padding: EdgeInsets.all(4),
                    child: Icon(LucideIcons.plus, size: 16),
                  ),
                ),
                Text('$qty', style: const TextStyle(fontWeight: FontWeight.bold)),
                InkWell(
                  onTap: () {},
                  child: const Padding(
                    padding: EdgeInsets.all(4),
                    child: Icon(LucideIcons.minus, size: 16),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 16),
          // Item Details
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  name,
                  style: const TextStyle(fontWeight: FontWeight.w600),
                ),
                const SizedBox(height: 4),
                Text(
                  currencyFormatter.format(price),
                  style: const TextStyle(color: AppColors.primary, fontWeight: FontWeight.bold),
                ),
              ],
            ),
          ),
          // Total Price
          Text(
            currencyFormatter.format(price * qty),
            style: const TextStyle(fontWeight: FontWeight.bold),
          ),
        ],
      ),
    );
  }

  Widget _buildSummaryRow(String label, double amount) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(label, style: const TextStyle(color: AppColors.textSecondary)),
        Text(currencyFormatter.format(amount), style: const TextStyle(fontWeight: FontWeight.w600)),
      ],
    );
  }
}
