import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
import '../../../../core/theme/kasira_ds.dart';
import '../../../../core/localization/business_labels.dart';
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
import '../../utils/post_payment_refresh.dart';

// Tier is now read from SessionCache (0ms, in-memory)

/// Cart panel — ports the "Kasira POS.dc.html" CART SHEET (Pesanan):
/// item rows with icon tile + gradient stepper pill, dashed-border totals,
/// and gradient-frekuensi checkout buttons. Aurora light theme (KasiraDS).
class CartPanel extends ConsumerWidget {
  const CartPanel({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final cart = ref.watch(cartProvider);
    final currency = NumberFormat.currency(locale: 'id_ID', symbol: 'Rp ', decimalDigits: 0);

    return Column(
      children: [
        // ── Header ──
        Container(
          padding: const EdgeInsets.fromLTRB(20, 18, 12, 16),
          decoration: const BoxDecoration(
            color: KasiraDS.surfaceCard,
            border: Border(bottom: BorderSide(color: KasiraDS.borderSubtle)),
          ),
          child: Row(
            children: [
              Text('Pesanan', style: KasiraDS.display(size: 19, color: KasiraDS.textStrong)),
              if (cart.items.isNotEmpty) ...[
                const SizedBox(width: 9),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 3),
                  decoration: BoxDecoration(
                    gradient: KasiraDS.gradientFrekuensi,
                    borderRadius: KasiraDS.brPill,
                  ),
                  child: Text(
                    '${cart.items.length}',
                    style: KasiraDS.sans(size: 11.5, weight: FontWeight.w800, color: Colors.white),
                  ),
                ),
              ],
              const Spacer(),
              if (cart.items.isNotEmpty)
                IconButton(
                  onPressed: () => _confirmClear(context, ref),
                  icon: const Icon(LucideIcons.trash2, color: KasiraDS.danger, size: 20),
                  tooltip: 'Kosongkan',
                ),
            ],
          ),
        ),

        // Mode + Table info bar
        _PosModeBadge(cart: cart),

        // Customer
        Padding(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 0),
          child: InkWell(
            onTap: () => showDialog(
              context: context,
              builder: (_) => CustomerSelectionModal(
                onSelected: (id, name) {
                  ref.read(cartProvider.notifier).setCustomer(id, name: name);
                },
              ),
            ),
            borderRadius: KasiraDS.brMd,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 11),
              decoration: BoxDecoration(
                color: KasiraDS.surfaceSunken,
                borderRadius: KasiraDS.brMd,
              ),
              child: Row(
                children: [
                  Icon(LucideIcons.user,
                      color: cart.customerId != null ? KasiraDS.brandPrimary : KasiraDS.textMuted,
                      size: 18),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      cart.customerName ?? (cart.customerId != null ? 'Pelanggan dipilih' : 'Pilih Pelanggan (opsional)'),
                      style: KasiraDS.sans(
                        size: 13,
                        weight: cart.customerId != null ? FontWeight.w700 : FontWeight.w500,
                        color: cart.customerId != null ? KasiraDS.brandPrimary : KasiraDS.textMuted,
                      ),
                    ),
                  ),
                  const Icon(LucideIcons.chevronRight, color: KasiraDS.textMuted, size: 16),
                ],
              ),
            ),
          ),
        ),

        const SizedBox(height: 8),

        // Cart items + upsell + promo (scrollable area)
        Expanded(
          child: cart.items.isEmpty
              ? _buildEmptyCart()
              : ListView(
                  padding: const EdgeInsets.fromLTRB(20, 8, 20, 8),
                  children: [
                    for (int i = 0; i < cart.items.length; i++) ...[
                      _CartItemTile(
                        item: cart.items[i],
                        currency: currency,
                        onIncrement: () => ref.read(cartProvider.notifier).incrementItem(cart.items[i].productId),
                        onDecrement: () => ref.read(cartProvider.notifier).decrementItem(cart.items[i].productId),
                      ),
                      if (i != cart.items.length - 1) const SizedBox(height: 12),
                    ],
                    _upsellSection(ref, cart),
                    _promoSection(ref, cart, currency),
                  ],
                ),
        ),

        // Footer
        if (cart.items.isNotEmpty)
          Container(
            padding: const EdgeInsets.fromLTRB(20, 16, 20, 20),
            decoration: const BoxDecoration(
              color: KasiraDS.surfaceCard,
              border: Border(top: BorderSide(color: KasiraDS.borderSubtle)),
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
                const Padding(
                  padding: EdgeInsets.symmetric(vertical: 12),
                  child: Divider(height: 1, thickness: 1, color: KasiraDS.borderSubtle),
                ),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text('Total', style: KasiraDS.sans(size: 15, weight: FontWeight.w700, color: KasiraDS.textStrong)),
                    Text(
                      currency.format(cart.total),
                      style: KasiraDS.display(size: 22, color: KasiraDS.textStrong),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                // Error
                if (cart.error != null)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 10),
                    child: Container(
                      padding: const EdgeInsets.all(11),
                      decoration: BoxDecoration(
                        color: KasiraDS.danger.withOpacity(0.1),
                        borderRadius: KasiraDS.brSm,
                      ),
                      child: Row(
                        children: [
                          const Icon(LucideIcons.alertCircle, color: KasiraDS.danger, size: 16),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(cart.error!,
                                style: KasiraDS.sans(size: 12, color: KasiraDS.danger),
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
    final tableName = cart.tableName ?? BusinessLabels.getLabel('table');
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
            backgroundColor: KasiraDS.danger,
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
            backgroundColor: KasiraDS.danger,
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
    // P3 Quick Win #1: defer cascade invalidate ke microtask — paint navigation
    // dulu (snackbar + UI return), provider refresh di background.
    schedulePostPaymentRefresh(ref, includeTabs: true);

    // If this was a "tambah pesanan" flow (coming from tab detail), auto-return
    if (addOrderCtx != null && context.mounted) {
      ref.read(addOrderContextProvider.notifier).state = null;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Pesanan ditambahkan ke ${addOrderCtx.tabNumber}'),
          backgroundColor: KasiraDS.success,
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
          shape: RoundedRectangleBorder(borderRadius: KasiraDS.brLg),
          icon: const Icon(LucideIcons.chefHat, color: KasiraDS.success, size: 40),
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
                style: TextStyle(fontSize: 13, color: KasiraDS.textMuted),
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
    // Cara A (optimistic online): buka payment modal LANGSUNG sambil submitOrder
    // jalan di background. Latensi POST /orders kesembunyiin di belakang waktu
    // kasir milih metode + ketik uang. Modal resolve orderId pas benar-benar
    // butuh (QRIS generate / konfirmasi bayar). Gak nyentuh logic pembayaran.
    final orderIdFuture = ref.read(cartProvider.notifier).submitOrder();

    // Snapshot cart SEKARANG (sebelum clearCart di onPaymentSuccess).
    final receiptItems = cart.items
        .map((i) => ReceiptItem(name: i.name, qty: i.qty, price: i.price))
        .toList();
    final taxAmount = cart.taxAmount;
    final serviceChargeAmount = cart.serviceChargeAmount;
    final discountAmount = cart.discountAmount;
    final taxInclusive = cart.taxInclusive;
    final totalAmount = cart.total;
    final customerId = cart.customerId;
    final customerName = cart.customerName;

    if (context.mounted) {
      showDialog(
        context: context,
        barrierDismissible: false,
        builder: (_) => PaymentModal(
          totalAmount: totalAmount,
          orderIdFuture: orderIdFuture,
          orderErrorGetter: () => ref.read(cartProvider).error,
          onPaymentSuccess: (String paymentMethod, double amountPaid, String orderId) {
            ref.read(cartProvider.notifier).clearCart();
            ref.read(posModeProvider.notifier).state = PosMode.selection;
            // P3 Quick Win #1: defer ke microtask (helper) — paint UI dulu
            schedulePostPaymentRefresh(ref);
            if (context.mounted) {
              context.push('/payment/success', extra: {
                'totalAmount': totalAmount,
                'amountPaid': amountPaid,
                'changeAmount': amountPaid - totalAmount,
                'paymentMethod': paymentMethod,
                'orderId': orderId,
                'displayNumber': orderId.substring(0, 8).toUpperCase(),
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
            padding: const EdgeInsets.all(22),
            decoration: const BoxDecoration(
              color: KasiraDS.brandTint,
              shape: BoxShape.circle,
            ),
            child: const Icon(LucideIcons.shoppingCart, size: 36, color: KasiraDS.brandPrimary),
          ),
          const SizedBox(height: 16),
          Text('Keranjang kosong',
              style: KasiraDS.sans(size: 15, weight: FontWeight.w700, color: KasiraDS.textStrong)),
          const SizedBox(height: 4),
          Text('Pilih produk untuk memulai',
              style: KasiraDS.sans(size: 12, color: KasiraDS.textMuted)),
        ],
      ),
    );
  }

  /// Upsell "sering dibeli bareng" — best-seller yang belum di keranjang.
  /// Heuristik lokal (bukan combo-detection backend) supaya cepat + offline-safe.
  Widget _upsellSection(WidgetRef ref, CartState cart) {
    final products = ref.watch(productsProvider).valueOrNull ?? const <ProductModel>[];
    final inCart = cart.items.map((e) => e.productId).toSet();
    final upsell = products
        .where((p) => p.isBestSeller && p.isAvailable && !inCart.contains(p.id))
        .take(3)
        .toList();
    if (upsell.isEmpty) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.only(top: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [
            const Icon(LucideIcons.sparkles, size: 14, color: KasiraDS.brandPrimary),
            const SizedBox(width: 6),
            Text('Sering dibeli bareng',
                style: KasiraDS.sans(size: 12, weight: FontWeight.w700, color: KasiraDS.textBody)),
          ]),
          const SizedBox(height: 9),
          Wrap(spacing: 8, runSpacing: 8, children: upsell.map((p) => _upsellChip(ref, p)).toList()),
        ],
      ),
    );
  }

  Widget _upsellChip(WidgetRef ref, ProductModel p) {
    return GestureDetector(
      onTap: () => ref.read(cartProvider.notifier).addItem(CartItem(
            productId: p.id,
            name: p.name,
            price: p.price,
            stockQty: p.stockEnabled ? p.stock.toDouble() : null,
          )),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        decoration: BoxDecoration(
          color: KasiraDS.surfaceCard,
          borderRadius: KasiraDS.brPill,
          border: Border.all(color: KasiraDS.borderDefault, width: 1.5),
        ),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          const Icon(LucideIcons.plus, size: 14, color: KasiraDS.brandPrimary),
          const SizedBox(width: 5),
          ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 140),
            child: Text(p.name,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: KasiraDS.sans(size: 12.5, weight: FontWeight.w600, color: KasiraDS.textBody)),
          ),
        ]),
      ),
    );
  }

  /// Promo/diskon cepat — set discountAmount via cart notifier (clamp di provider).
  Widget _promoSection(WidgetRef ref, CartState cart, NumberFormat currency) {
    final subtotal = cart.subtotal;
    if (subtotal <= 0) return const SizedBox.shrink();
    final options = <({String label, double amount})>[
      (label: 'Diskon 10%', amount: (subtotal * 0.10).roundToDouble()),
      (label: 'Rp 5rb', amount: 5000),
      (label: 'Rp 10rb', amount: 10000),
    ];
    return Padding(
      padding: const EdgeInsets.only(top: 16, bottom: 4),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [
            const Icon(LucideIcons.tag, size: 14, color: KasiraDS.brandPrimary),
            const SizedBox(width: 6),
            Text('Diskon / promo',
                style: KasiraDS.sans(size: 12, weight: FontWeight.w700, color: KasiraDS.textBody)),
          ]),
          const SizedBox(height: 9),
          Wrap(spacing: 8, runSpacing: 8, children: [
            for (final o in options)
              _promoChip(ref, o.label, o.amount, cart.discountAmount),
            if (cart.discountAmount > 0)
              GestureDetector(
                onTap: () => ref.read(cartProvider.notifier).setDiscount(0),
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  decoration: BoxDecoration(
                    color: KasiraDS.surfaceSunken,
                    borderRadius: KasiraDS.brPill,
                  ),
                  child: Text('Tanpa diskon',
                      style: KasiraDS.sans(size: 12.5, weight: FontWeight.w700, color: KasiraDS.textMuted)),
                ),
              ),
          ]),
        ],
      ),
    );
  }

  Widget _promoChip(WidgetRef ref, String label, double amount, double current) {
    final sel = (current - amount).abs() < 0.5 && current > 0;
    return GestureDetector(
      onTap: () => ref.read(cartProvider.notifier).setDiscount(sel ? 0 : amount),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        decoration: BoxDecoration(
          gradient: sel ? KasiraDS.gradientFrekuensi : null,
          color: sel ? null : KasiraDS.surfaceCard,
          borderRadius: KasiraDS.brPill,
          border: Border.all(color: sel ? Colors.transparent : KasiraDS.borderDefault, width: 1.5),
        ),
        child: Text(label,
            style: KasiraDS.sans(
                size: 12.5, weight: FontWeight.w700, color: sel ? Colors.white : KasiraDS.textStrong)),
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
        shape: RoundedRectangleBorder(borderRadius: KasiraDS.brLg),
        title: const Text('Kosongkan Pesanan?'),
        content: const Text('Semua item akan dihapus dari keranjang.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Batal')),
          ElevatedButton(
            onPressed: () {
              ref.read(cartProvider.notifier).clearCart();
              Navigator.pop(ctx);
            },
            style: ElevatedButton.styleFrom(backgroundColor: KasiraDS.danger),
            child: const Text('Hapus'),
          ),
        ],
      ),
    );
  }
}

/// Cart item row — icon tile + name/price + gradient stepper pill (design 522-535).
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
    return Row(
      children: [
        // icon tile
        Container(
          width: 42,
          height: 42,
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: KasiraDS.brandTint,
            borderRadius: KasiraDS.brMd,
          ),
          child: const Icon(LucideIcons.coffee, size: 20, color: KasiraDS.brandPrimary),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(item.name,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: KasiraDS.sans(size: 14, weight: FontWeight.w700, color: KasiraDS.textStrong)),
              const SizedBox(height: 2),
              Text(currency.format(item.subtotal),
                  style: KasiraDS.sans(size: 12, color: KasiraDS.textMuted)),
            ],
          ),
        ),
        const SizedBox(width: 10),
        // stepper pill
        Container(
          padding: const EdgeInsets.all(3),
          decoration: BoxDecoration(
            color: KasiraDS.surfaceSunken,
            borderRadius: KasiraDS.brPill,
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              _stepBtn(
                onTap: onDecrement,
                filled: false,
                child: const Text('−',
                    style: TextStyle(
                        fontSize: 18, fontWeight: FontWeight.w700, color: KasiraDS.textStrong, height: 1)),
              ),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 8),
                child: Text('${item.qty}',
                    style: KasiraDS.sans(size: 14, weight: FontWeight.w800, color: KasiraDS.textStrong)),
              ),
              _stepBtn(
                onTap: onIncrement,
                filled: true,
                child: const Icon(LucideIcons.plus, size: 15, color: Colors.white),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _stepBtn({required VoidCallback onTap, required bool filled, required Widget child}) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: 28,
        height: 28,
        alignment: Alignment.center,
        decoration: BoxDecoration(
          gradient: filled ? KasiraDS.gradientFrekuensi : null,
          color: filled ? null : KasiraDS.surfaceCard,
          shape: BoxShape.circle,
          boxShadow: filled ? null : KasiraDS.shadowSm,
        ),
        child: child,
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

    final accent = isDineIn ? KasiraDS.brandPrimary : KasiraDS.brandSecondary;
    final tint = isDineIn ? KasiraDS.brandTint : KasiraDS.brandTint2;

    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 14, 20, 0),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 11),
        decoration: BoxDecoration(
          color: tint,
          border: Border.all(color: accent.withOpacity(0.4)),
          borderRadius: KasiraDS.brMd,
        ),
        child: Row(
          children: [
            Icon(
              isDineIn ? LucideIcons.utensils : LucideIcons.shoppingBag,
              color: accent,
              size: 16,
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    isTakeaway ? 'Takeaway' : 'Dine In',
                    style: KasiraDS.sans(size: 13, weight: FontWeight.w700, color: accent),
                  ),
                  if (isDineIn && cart.tableName != null)
                    Text(
                      cart.tableName!,
                      style: KasiraDS.sans(size: 11, color: KasiraDS.textMuted),
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
                child: Text('Ganti',
                    style: KasiraDS.sans(size: 12, weight: FontWeight.w700, color: KasiraDS.brandPrimary)),
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
        height: 54,
        child: Center(child: CircularProgressIndicator()),
      );
    }

    // Pro Dine-In: soft "simpan ke meja" + gradient "bayar sekarang" (design 568-571)
    if (isDineInPro) {
      return Column(
        children: [
          _SoftButton(
            label: 'Simpan ke meja (bayar nanti)',
            icon: LucideIcons.utensils,
            onTap: onPayLater,
          ),
          const SizedBox(height: 10),
          _GradientButton(
            label: 'Bayar sekarang',
            icon: LucideIcons.creditCard,
            onTap: onPayNow,
          ),
        ],
      );
    }

    // Takeaway or Starter dine-in: single gradient pay button
    return _GradientButton(
      label: 'BAYAR SEKARANG',
      icon: LucideIcons.creditCard,
      onTap: onPayNow,
    );
  }
}

/// Primary CTA — gradient-frekuensi pill with brand glow (design Button primary).
class _GradientButton extends StatelessWidget {
  final String label;
  final IconData icon;
  final VoidCallback onTap;
  const _GradientButton({required this.label, required this.icon, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: double.infinity,
      height: 54,
      child: DecoratedBox(
        decoration: BoxDecoration(
          gradient: KasiraDS.gradientFrekuensi,
          borderRadius: KasiraDS.brMd,
          boxShadow: KasiraDS.glowBrand,
        ),
        child: Material(
          color: Colors.transparent,
          child: InkWell(
            onTap: onTap,
            borderRadius: KasiraDS.brMd,
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(icon, size: 18, color: Colors.white),
                const SizedBox(width: 8),
                Text(label,
                    style: KasiraDS.sans(size: 15, weight: FontWeight.w800, color: Colors.white)),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

/// Soft secondary — brand-tinted fill, brand text (design Button variant="soft").
class _SoftButton extends StatelessWidget {
  final String label;
  final IconData icon;
  final VoidCallback onTap;
  const _SoftButton({required this.label, required this.icon, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: double.infinity,
      height: 50,
      child: Material(
        color: KasiraDS.brandTint,
        borderRadius: KasiraDS.brMd,
        child: InkWell(
          onTap: onTap,
          borderRadius: KasiraDS.brMd,
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(icon, size: 17, color: KasiraDS.brandPrimary),
              const SizedBox(width: 8),
              Text(label,
                  style: KasiraDS.sans(size: 14, weight: FontWeight.w700, color: KasiraDS.brandPrimary)),
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
  final bool isDiscount;

  const _SummaryRow({required this.label, required this.value, this.isDiscount = false});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: KasiraDS.sans(size: 13.5, color: KasiraDS.textBody)),
          Text(
            value,
            style: KasiraDS.sans(
              size: 13.5,
              weight: FontWeight.w700,
              color: isDiscount ? KasiraDS.success : KasiraDS.textStrong,
            ),
          ),
        ],
      ),
    );
  }
}
