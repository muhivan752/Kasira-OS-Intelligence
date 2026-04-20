import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:lucide_icons/lucide_icons.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/services/session_cache.dart';
import '../../providers/cart_provider.dart';
import '../../providers/pos_mode_provider.dart';
import '../../presentation/pages/receipt_preview_page.dart';
import 'payment_modal.dart';
import '../../../customers/presentation/widgets/customer_selection_modal.dart';
import '../../../dashboard/providers/dashboard_provider.dart';
import '../../../orders/providers/orders_provider.dart';
import '../../../products/providers/products_provider.dart';
import '../../../tabs/providers/tab_provider.dart';

// Tier is now read from SessionCache (0ms, in-memory)

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

        // Mode + Table info bar
        _PosModeBadge(cart: cart),

        // Customer
        Padding(
          padding: const EdgeInsets.fromLTRB(24, 12, 24, 0),
          child: InkWell(
            onTap: () => showDialog(
              context: context,
              builder: (_) => CustomerSelectionModal(
                onSelected: (id, name) {
                  ref.read(cartProvider.notifier).setCustomer(id, name: name);
                },
              ),
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
                      cart.customerName ?? (cart.customerId != null ? 'Pelanggan dipilih' : 'Pilih Pelanggan (opsional)'),
                      style: TextStyle(
                        color: cart.customerId != null ? AppColors.primary : AppColors.textSecondary,
                        fontSize: 13,
                        fontWeight: cart.customerId != null ? FontWeight.w600 : FontWeight.normal,
                      ),
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
            decoration: const BoxDecoration(
              color: AppColors.surfaceVariant,
              border: Border(top: BorderSide(color: AppColors.border, width: 0.5)),
            ),
            child: Column(
              children: [
                _SummaryRow(label: 'Subtotal', value: currency.format(cart.subtotal)),
                if (cart.discountAmount > 0)
                  _SummaryRow(
                    label: 'Diskon',
                    value: '- ${currency.format(cart.discountAmount)}',
                    isDiscount: true,
                  ),
                if (cart.serviceChargeAmount > 0)
                  _SummaryRow(
                    label: 'Service Charge',
                    value: currency.format(cart.serviceChargeAmount),
                  ),
                if (cart.taxAmount > 0)
                  _SummaryRow(
                    label: cart.taxInclusive ? 'Pajak (inklusif)' : 'Pajak',
                    value: currency.format(cart.taxAmount),
                  ),
                const Divider(height: 20, color: AppColors.border),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text('Total', style: Theme.of(context).textTheme.titleLarge),
                    Text(
                      currency.format(cart.total),
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
                    child: Container(
                      padding: const EdgeInsets.all(10),
                      decoration: BoxDecoration(
                        color: AppColors.error.withOpacity(0.1),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Row(
                        children: [
                          const Icon(LucideIcons.alertCircle, color: AppColors.error, size: 16),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(cart.error!,
                                style: const TextStyle(color: AppColors.error, fontSize: 12),
                                textAlign: TextAlign.left),
                          ),
                        ],
                      ),
                    ),
                  ),
                _PaymentButtons(
                  cart: cart,
                  onPayNow: () => _handlePayment(context, ref, cart),
                  onPayLater: () => _handleDineIn(context, ref, cart),
                ),
              ],
            ),
          ),
      ],
    );
  }

  /// Dine-in: kirim order ke dapur, link ke tab — bayar nanti
  Future<void> _handleDineIn(BuildContext context, WidgetRef ref, CartState cart) async {
    final tableName = cart.tableName ?? 'Meja';
    final addOrderCtx = ref.read(addOrderContextProvider);

    // Safety net: submitDineInOrder() sudah catch internal & set state.error,
    // tapi kalau ada exception tak terduga (SessionCache null, cast error, dll)
    // bungkus di sini biar app gak force-close di lapangan.
    Map<String, dynamic>? result;
    try {
      result = await ref.read(cartProvider.notifier).submitDineInOrder();
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Gagal kirim pesanan: ${_shortError(e)}'),
            backgroundColor: AppColors.error,
            behavior: SnackBarBehavior.floating,
            duration: const Duration(seconds: 4),
          ),
        );
      }
      return;
    }

    if (result == null) {
      // submitDineInOrder() sudah set state.error (inline error box),
      // tambahin snackbar biar user langsung ngeh di tombol yang baru aja ditekan.
      final errMsg = ref.read(cartProvider).error ?? 'Gagal kirim pesanan';
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(errMsg),
            backgroundColor: AppColors.error,
            behavior: SnackBarBehavior.floating,
            duration: const Duration(seconds: 4),
          ),
        );
      }
      return;
    }
    if (!context.mounted) return;

    final tabNumber = result['tabNumber']?.toString() ?? '';
    final tabId = result['tabId']?.toString() ?? '';

    ref.read(cartProvider.notifier).clearCart();
    ref.read(posModeProvider.notifier).state = PosMode.selection;
    ref.invalidate(dashboardProvider);
    ref.invalidate(ordersProvider);
    ref.invalidate(productsProvider);
    ref.invalidate(activeTabsCountProvider);

    // If this was a "tambah pesanan" flow (coming from tab detail), auto-return
    if (addOrderCtx != null && context.mounted) {
      ref.read(addOrderContextProvider.notifier).state = null;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Pesanan ditambahkan ke ${addOrderCtx.tabNumber}'),
          backgroundColor: AppColors.success,
          behavior: SnackBarBehavior.floating,
          duration: const Duration(seconds: 2),
        ),
      );
      context.go('/tabs/${addOrderCtx.tabId}');
      return;
    }

    if (context.mounted) {
      showDialog(
        context: context,
        builder: (ctx) => AlertDialog(
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
          icon: const Icon(LucideIcons.chefHat, color: Color(0xFF059669), size: 40),
          title: const Text('Pesanan Dikirim!'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                '$tableName — $tabNumber',
                style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 8),
              const Text(
                'Pesanan sudah masuk ke dapur.\nBisa tambah pesanan lagi atau bayar nanti di Tab/Bon.',
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 13, color: Colors.grey),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: const Text('OK'),
            ),
            ElevatedButton(
              onPressed: () {
                Navigator.pop(ctx);
                context.push('/tabs/$tabId');
              },
              child: const Text('Lihat Tab'),
            ),
          ],
        ),
      );
    }
  }

  Future<void> _handlePayment(BuildContext context, WidgetRef ref, CartState cart) async {
    // 1. Submit order ke backend — bungkus UI-level try/catch sbg safety net.
    // submitOrder() punya catch internal, tapi kalau ada exception sinkron
    // (invalid state, null deref di getter), lebih baik show snackbar manusiawi
    // daripada crash zone error boundary.
    String? orderId;
    try {
      orderId = await ref.read(cartProvider.notifier).submitOrder();
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Gagal proses pembayaran: ${_shortError(e)}'),
            backgroundColor: AppColors.error,
            behavior: SnackBarBehavior.floating,
            duration: const Duration(seconds: 4),
          ),
        );
      }
      return;
    }

    if (orderId == null) {
      // submitOrder() sudah set state.error — amplify via snackbar biar user
      // langsung tau, terutama kalau panel error message ke-scroll.
      final errMsg = ref.read(cartProvider).error ?? 'Gagal proses pembayaran';
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(errMsg),
            backgroundColor: AppColors.error,
            behavior: SnackBarBehavior.floating,
            duration: const Duration(seconds: 4),
          ),
        );
      }
      return;
    }

    // 2. Buka payment modal — capture orderId ke non-null local biar
    // Dart flow analysis gak kehilangan non-null promotion di dalam closure.
    final confirmedOrderId = orderId;
    if (context.mounted) {
      showDialog(
        context: context,
        barrierDismissible: false,
        builder: (_) => PaymentModal(
          totalAmount: cart.total,
          orderId: confirmedOrderId,
          onPaymentSuccess: (String paymentMethod, double amountPaid) {
            final receiptItems = cart.items.map((i) => ReceiptItem(
              name: i.name,
              qty: i.qty,
              price: i.price,
            )).toList();
            final taxAmount = cart.taxAmount;
            final serviceChargeAmount = cart.serviceChargeAmount;
            final discountAmount = cart.discountAmount;
            final taxInclusive = cart.taxInclusive;
            final totalAmount = cart.total;
            final customerId = cart.customerId;
            final customerName = cart.customerName;
            ref.read(cartProvider.notifier).clearCart();
            ref.read(posModeProvider.notifier).state = PosMode.selection;
            // Invalidate providers supaya dashboard & order list langsung update
            ref.invalidate(dashboardProvider);
            ref.invalidate(ordersProvider);
            ref.invalidate(productsProvider);
            if (context.mounted) {
              context.push('/payment/success', extra: {
                'totalAmount': totalAmount,
                'amountPaid': amountPaid,
                'changeAmount': amountPaid - totalAmount,
                'paymentMethod': paymentMethod,
                'orderId': confirmedOrderId,
                'displayNumber': confirmedOrderId.substring(0, 8).toUpperCase(),
                'items': receiptItems,
                'tax': taxAmount,
                'serviceCharge': serviceChargeAmount,
                'discount': discountAmount,
                'taxInclusive': taxInclusive,
                'customerId': customerId,
                'customerName': customerName,
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

  /// Ambil pesan error pendek dari Exception — jangan kasih lihat raw stack
  /// ke kasir di lapangan. Format: "Jenis — ringkasan".
  static String _shortError(Object e) {
    final raw = e.toString();
    // Trim "Exception: " prefix + batasi panjang
    final cleaned = raw.replaceFirst(RegExp(r'^Exception:\s*'), '');
    return cleaned.length > 120 ? '${cleaned.substring(0, 117)}...' : cleaned;
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

class _PosModeBadge extends ConsumerWidget {
  final CartState cart;

  const _PosModeBadge({required this.cart});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final posMode = ref.watch(posModeProvider);
    final isDineIn = posMode == PosMode.dineInOrdering || posMode == PosMode.dineInTableSelect;
    final isTakeaway = posMode == PosMode.takeaway;

    // Don't show anything in selection mode
    if (posMode == PosMode.selection) return const SizedBox.shrink();

    return Padding(
      padding: const EdgeInsets.fromLTRB(24, 16, 24, 0),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        decoration: BoxDecoration(
          color: isDineIn
              ? AppColors.primary.withOpacity(0.08)
              : AppColors.accent.withOpacity(0.08),
          border: Border.all(
            color: isDineIn ? AppColors.primary : AppColors.accent,
          ),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Row(
          children: [
            Icon(
              isDineIn ? LucideIcons.utensils : LucideIcons.shoppingBag,
              color: isDineIn ? AppColors.primary : AppColors.accent,
              size: 16,
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    isTakeaway ? 'Takeaway' : 'Dine In',
                    style: TextStyle(
                      color: isDineIn ? AppColors.primary : AppColors.accent,
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  if (isDineIn && cart.tableName != null)
                    Text(
                      cart.tableName!,
                      style: const TextStyle(fontSize: 11, color: AppColors.textSecondary),
                    ),
                ],
              ),
            ),
            if (isDineIn && cart.tableName != null)
              GestureDetector(
                onTap: () {
                  ref.read(cartProvider.notifier).setTable(null);
                  ref.read(posModeProvider.notifier).state = PosMode.dineInTableSelect;
                },
                child: const Text('Ganti', style: TextStyle(fontSize: 12, color: AppColors.primary)),
              ),
          ],
        ),
      ),
    );
  }
}

class _PaymentButtons extends ConsumerWidget {
  final CartState cart;
  final VoidCallback onPayNow;
  final VoidCallback onPayLater;

  const _PaymentButtons({
    required this.cart,
    required this.onPayNow,
    required this.onPayLater,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final posMode = ref.watch(posModeProvider);
    final isDineInPro = posMode == PosMode.dineInOrdering && SessionCache.instance.isPro;

    if (cart.isSubmitting) {
      return const SizedBox(
        width: double.infinity,
        height: 50,
        child: Center(child: CircularProgressIndicator()),
      );
    }

    // Pro Dine-In: two buttons side by side
    if (isDineInPro) {
      return Row(
        children: [
          Expanded(
            child: SizedBox(
              height: 50,
              child: ElevatedButton.icon(
                onPressed: onPayNow,
                icon: const Icon(LucideIcons.creditCard, size: 16),
                label: const Text('BAYAR\nLANGSUNG', textAlign: TextAlign.center,
                    style: TextStyle(fontWeight: FontWeight.bold, fontSize: 11)),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppColors.primary,
                  padding: const EdgeInsets.symmetric(horizontal: 8),
                ),
              ),
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: SizedBox(
              height: 50,
              child: ElevatedButton.icon(
                onPressed: onPayLater,
                icon: const Icon(LucideIcons.chefHat, size: 16),
                label: const Text('BAYAR\nNANTI', textAlign: TextAlign.center,
                    style: TextStyle(fontWeight: FontWeight.bold, fontSize: 11)),
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF059669),
                  padding: const EdgeInsets.symmetric(horizontal: 8),
                ),
              ),
            ),
          ),
        ],
      );
    }

    // Takeaway or Starter dine-in: single pay button
    return SizedBox(
      width: double.infinity,
      height: 50,
      child: ElevatedButton(
        onPressed: onPayNow,
        child: const Text('BAYAR SEKARANG', style: TextStyle(fontWeight: FontWeight.bold)),
      ),
    );
  }
}

class _SummaryRow extends StatelessWidget {
  final String label;
  final String value;
  final bool isDiscount;

  const _SummaryRow({required this.label, required this.value, this.isDiscount = false});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: const TextStyle(color: AppColors.textSecondary, fontSize: 13)),
          Text(
            value,
            style: TextStyle(
              fontWeight: FontWeight.w600,
              fontSize: 13,
              color: isDiscount ? AppColors.error : null,
            ),
          ),
        ],
      ),
    );
  }
}
