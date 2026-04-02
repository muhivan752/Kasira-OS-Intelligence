import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:lucide_icons/lucide_icons.dart';
import '../../../../core/theme/app_colors.dart';
import '../../providers/cart_provider.dart';
import 'payment_modal.dart';
import '../../../customers/presentation/widgets/customer_selection_modal.dart';

class CartPanel extends ConsumerWidget {
  const CartPanel({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final cart = ref.watch(cartProvider);
    final currency = NumberFormat.currency(locale: 'id_ID', symbol: 'Rp ', decimalDigits: 0);

    return Column(
      children: [
        // Header
        Container(
          padding: const EdgeInsets.fromLTRB(24, 20, 16, 20),
          decoration: const BoxDecoration(
            border: Border(bottom: BorderSide(color: AppColors.border)),
          ),
          child: Row(
            children: [
              Text('Pesanan', style: Theme.of(context).textTheme.titleLarge),
              if (cart.items.isNotEmpty) ...[
                const SizedBox(width: 8),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                  decoration: BoxDecoration(
                    color: AppColors.primary,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Text(
                    '${cart.items.length}',
                    style: const TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.bold),
                  ),
                ),
              ],
              const Spacer(),
              if (cart.items.isNotEmpty)
                IconButton(
                  onPressed: () => _confirmClear(context, ref),
                  icon: const Icon(LucideIcons.trash2, color: AppColors.error, size: 20),
                  tooltip: 'Kosongkan',
                ),
            ],
          ),
        ),

        // Order Type
        Padding(
          padding: const EdgeInsets.fromLTRB(24, 16, 24, 0),
          child: Row(
            children: [
              _OrderTypeBtn(
                label: 'Dine In',
                icon: LucideIcons.utensils,
                isSelected: cart.orderType == 'Dine In',
                onTap: () => ref.read(cartProvider.notifier).setOrderType('Dine In'),
              ),
              const SizedBox(width: 12),
              _OrderTypeBtn(
                label: 'Takeaway',
                icon: LucideIcons.shoppingBag,
                isSelected: cart.orderType == 'Takeaway',
                onTap: () => ref.read(cartProvider.notifier).setOrderType('Takeaway'),
              ),
            ],
          ),
        ),

        // Customer
        Padding(
          padding: const EdgeInsets.fromLTRB(24, 12, 24, 0),
          child: InkWell(
            onTap: () => showDialog(
              context: context,
              builder: (_) => const CustomerSelectionModal(),
            ),
            borderRadius: BorderRadius.circular(12),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
              decoration: BoxDecoration(
                color: AppColors.surfaceVariant,
                borderRadius: BorderRadius.circular(12),
              ),
              child: Row(
                children: [
                  const Icon(LucideIcons.user, color: AppColors.textSecondary, size: 18),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      cart.customerId != null ? 'Pelanggan dipilih' : 'Pilih Pelanggan (opsional)',
                      style: const TextStyle(color: AppColors.textSecondary, fontSize: 13),
                    ),
                  ),
                  const Icon(LucideIcons.chevronRight, color: AppColors.textSecondary, size: 16),
                ],
              ),
            ),
          ),
        ),

        const SizedBox(height: 8),

        // Cart items
        Expanded(
          child: cart.items.isEmpty
              ? _buildEmptyCart()
              : ListView.builder(
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                  itemCount: cart.items.length,
                  itemBuilder: (_, i) => _CartItemTile(
                    item: cart.items[i],
                    currency: currency,
                    onIncrement: () => ref.read(cartProvider.notifier).incrementItem(cart.items[i].productId),
                    onDecrement: () => ref.read(cartProvider.notifier).decrementItem(cart.items[i].productId),
                  ),
                ),
        ),

        // Footer
        if (cart.items.isNotEmpty)
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: Colors.white,
              boxShadow: [
                BoxShadow(color: Colors.black.withOpacity(0.06), blurRadius: 12, offset: const Offset(0, -4)),
              ],
            ),
            child: Column(
              children: [
                _SummaryRow(label: 'Subtotal', value: currency.format(cart.subtotal)),
                const Divider(height: 20, color: AppColors.border),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text('Total', style: Theme.of(context).textTheme.titleLarge),
                    Text(
                      currency.format(cart.subtotal),
                      style: Theme.of(context)
                          .textTheme
                          .titleLarge
                          ?.copyWith(color: AppColors.primary, fontWeight: FontWeight.bold),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                // Error
                if (cart.error != null)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 10),
                    child: Text(cart.error!,
                        style: const TextStyle(color: AppColors.error, fontSize: 13),
                        textAlign: TextAlign.center),
                  ),
                SizedBox(
                  width: double.infinity,
                  height: 50,
                  child: ElevatedButton(
                    onPressed: cart.isSubmitting
                        ? null
                        : () => _handlePayment(context, ref, cart),
                    child: cart.isSubmitting
                        ? const SizedBox(
                            width: 20,
                            height: 20,
                            child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2),
                          )
                        : const Text('BAYAR SEKARANG', style: TextStyle(fontWeight: FontWeight.bold)),
                  ),
                ),
              ],
            ),
          ),
      ],
    );
  }

  Future<void> _handlePayment(BuildContext context, WidgetRef ref, CartState cart) async {
    // 1. Submit order ke backend
    final orderId = await ref.read(cartProvider.notifier).submitOrder();
    if (orderId == null) return; // error sudah ditampilkan di state

    // 2. Buka payment modal
    if (context.mounted) {
      showDialog(
        context: context,
        barrierDismissible: false,
        builder: (_) => PaymentModal(
          totalAmount: cart.subtotal,
          orderId: orderId,
          onPaymentSuccess: (String paymentMethod, double amountPaid) {
            ref.read(cartProvider.notifier).clearCart();
            if (context.mounted) {
              context.push('/payment/success', extra: {
                'totalAmount': cart.subtotal,
                'amountPaid': amountPaid,
                'changeAmount': amountPaid - cart.subtotal,
                'paymentMethod': paymentMethod,
                'orderId': orderId,
                'displayNumber': orderId.substring(0, 8).toUpperCase(),
              });
            }
          },
        ),
      );
    }
  }

  Widget _buildEmptyCart() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: AppColors.surfaceVariant,
              shape: BoxShape.circle,
            ),
            child: const Icon(LucideIcons.shoppingCart, size: 36, color: AppColors.textTertiary),
          ),
          const SizedBox(height: 16),
          const Text('Keranjang kosong', style: TextStyle(color: AppColors.textSecondary, fontWeight: FontWeight.w500)),
          const SizedBox(height: 4),
          const Text('Pilih produk untuk memulai', style: TextStyle(color: AppColors.textTertiary, fontSize: 12)),
        ],
      ),
    );
  }

  void _confirmClear(BuildContext context, WidgetRef ref) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: const Text('Kosongkan Pesanan?'),
        content: const Text('Semua item akan dihapus dari keranjang.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Batal')),
          ElevatedButton(
            onPressed: () {
              ref.read(cartProvider.notifier).clearCart();
              Navigator.pop(ctx);
            },
            style: ElevatedButton.styleFrom(backgroundColor: AppColors.error),
            child: const Text('Hapus'),
          ),
        ],
      ),
    );
  }
}

class _CartItemTile extends StatelessWidget {
  final CartItem item;
  final NumberFormat currency;
  final VoidCallback onIncrement;
  final VoidCallback onDecrement;

  const _CartItemTile({
    required this.item,
    required this.currency,
    required this.onIncrement,
    required this.onDecrement,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6, horizontal: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Qty stepper
          Container(
            decoration: BoxDecoration(
              border: Border.all(color: AppColors.border),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Column(
              children: [
                InkWell(
                  onTap: onIncrement,
                  borderRadius: const BorderRadius.vertical(top: Radius.circular(8)),
                  child: const Padding(padding: EdgeInsets.all(5), child: Icon(LucideIcons.plus, size: 14)),
                ),
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                  child: Text('${item.qty}', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
                ),
                InkWell(
                  onTap: onDecrement,
                  borderRadius: const BorderRadius.vertical(bottom: Radius.circular(8)),
                  child: const Padding(padding: EdgeInsets.all(5), child: Icon(LucideIcons.minus, size: 14)),
                ),
              ],
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(item.name, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
                const SizedBox(height: 2),
                Text(currency.format(item.price), style: const TextStyle(color: AppColors.primary, fontSize: 12)),
              ],
            ),
          ),
          Text(
            currency.format(item.subtotal),
            style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13),
          ),
        ],
      ),
    );
  }
}

class _OrderTypeBtn extends StatelessWidget {
  final String label;
  final IconData icon;
  final bool isSelected;
  final VoidCallback onTap;

  const _OrderTypeBtn({
    required this.label,
    required this.icon,
    required this.isSelected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(10),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 10),
          decoration: BoxDecoration(
            color: isSelected ? AppColors.primary.withOpacity(0.08) : Colors.white,
            border: Border.all(color: isSelected ? AppColors.primary : AppColors.border),
            borderRadius: BorderRadius.circular(10),
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(icon, size: 16, color: isSelected ? AppColors.primary : AppColors.textSecondary),
              const SizedBox(width: 6),
              Text(
                label,
                style: TextStyle(
                  color: isSelected ? AppColors.primary : AppColors.textSecondary,
                  fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                  fontSize: 13,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _SummaryRow extends StatelessWidget {
  final String label;
  final String value;

  const _SummaryRow({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(label, style: const TextStyle(color: AppColors.textSecondary, fontSize: 13)),
        Text(value, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
      ],
    );
  }
}
