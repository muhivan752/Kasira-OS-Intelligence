import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:lucide_icons/lucide_icons.dart';
import 'package:intl/intl.dart';
import 'package:dio/dio.dart';
import '../../../../core/config/app_config.dart';
import '../../../../core/services/session_cache.dart';
import '../../../../core/theme/app_colors.dart';
import '../../providers/orders_provider.dart';

final _currencyFmt = NumberFormat.currency(locale: 'id_ID', symbol: 'Rp ', decimalDigits: 0);

class OrderDetailModal extends ConsumerStatefulWidget {
  final String orderId;

  const OrderDetailModal({super.key, required this.orderId});

  @override
  ConsumerState<OrderDetailModal> createState() => _OrderDetailModalState();
}

class _OrderDetailModalState extends ConsumerState<OrderDetailModal> {
  bool _updating = false;

  Future<void> _updateStatus(String orderId, String newStatus, int rowVersion) async {
    setState(() => _updating = true);
    final notifier = ref.read(ordersProvider.notifier);
    final ok = await notifier.updateStatus(orderId, newStatus, rowVersion);
    if (mounted) {
      setState(() => _updating = false);
      if (ok) {
        ref.invalidate(orderDetailProvider(orderId));
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Status diubah ke ${_statusLabel(newStatus)}'),
            backgroundColor: AppColors.success,
            behavior: SnackBarBehavior.floating,
          ),
        );
      }
    }
  }

  String _statusLabel(String status) {
    switch (status) {
      case 'pending': return 'Menunggu';
      case 'preparing': return 'Diproses';
      case 'ready': return 'Siap';
      case 'served': return 'Disajikan';
      case 'completed': return 'Selesai';
      case 'cancelled': return 'Dibatalkan';
      default: return status;
    }
  }

  @override
  Widget build(BuildContext context) {
    final orderAsync = ref.watch(orderDetailProvider(widget.orderId));

    return Dialog(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24)),
      child: Container(
        width: 500,
        constraints: const BoxConstraints(maxHeight: 700),
        padding: const EdgeInsets.all(32),
        child: orderAsync.when(
          loading: () => const SizedBox(
            height: 200,
            child: Center(child: CircularProgressIndicator()),
          ),
          error: (err, _) => SizedBox(
            height: 200,
            child: Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Icon(LucideIcons.alertCircle, color: AppColors.error, size: 32),
                  const SizedBox(height: 12),
                  const Text('Gagal memuat detail pesanan'),
                  const SizedBox(height: 8),
                  TextButton(
                    onPressed: () => ref.invalidate(orderDetailProvider(widget.orderId)),
                    child: const Text('Coba lagi'),
                  ),
                ],
              ),
            ),
          ),
          data: (order) => _buildContent(context, order),
        ),
      ),
    );
  }

  Widget _buildContent(BuildContext context, OrderModel order) {
    final statusColor = switch (order.status) {
      'completed' => AppColors.success,
      'cancelled' => AppColors.error,
      'ready' => AppColors.info,
      _ => AppColors.warning,
    };

    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Detail Pesanan',
                    style: Theme.of(context).textTheme.headlineSmall),
                const SizedBox(height: 4),
                Text(order.orderNumber,
                    style: const TextStyle(
                        color: AppColors.textSecondary,
                        fontWeight: FontWeight.bold)),
              ],
            ),
            IconButton(
              onPressed: () => Navigator.pop(context),
              icon: const Icon(LucideIcons.x),
            ),
          ],
        ),
        const SizedBox(height: 16),
        Row(
          children: [
            _buildBadge('Status', order.statusLabel, statusColor),
            const SizedBox(width: 12),
            _buildBadge('Tipe', order.orderTypeLabel, AppColors.info),
          ],
        ),
        const Padding(
          padding: EdgeInsets.symmetric(vertical: 16),
          child: Divider(height: 1, color: AppColors.border),
        ),
        const Text('Daftar Item',
            style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
        const SizedBox(height: 12),
        Flexible(
          child: ListView.builder(
            shrinkWrap: true,
            itemCount: order.items.length,
            itemBuilder: (_, i) {
              final item = order.items[i];
              return Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: Row(
                  children: [
                    Text('${item.quantity}x',
                        style: const TextStyle(fontWeight: FontWeight.bold)),
                    const SizedBox(width: 12),
                    Expanded(child: Text(item.productName)),
                    Text(_currencyFmt.format(item.totalPrice),
                        style: const TextStyle(fontWeight: FontWeight.w600)),
                  ],
                ),
              );
            },
          ),
        ),
        const Padding(
          padding: EdgeInsets.symmetric(vertical: 12),
          child: Divider(height: 1, color: AppColors.border),
        ),
        _buildSummaryRow('Subtotal', _currencyFmt.format(order.subtotal)),
        if (order.discountAmount > 0) ...[
          const SizedBox(height: 6),
          _buildSummaryRow('Diskon', '- ${_currencyFmt.format(order.discountAmount)}',
              valueColor: AppColors.error),
        ],
        if (order.serviceChargeAmount > 0) ...[
          const SizedBox(height: 6),
          _buildSummaryRow('Service Charge', _currencyFmt.format(order.serviceChargeAmount)),
        ],
        if (order.taxAmount > 0) ...[
          const SizedBox(height: 6),
          _buildSummaryRow('Pajak', _currencyFmt.format(order.taxAmount)),
        ],
        const SizedBox(height: 12),
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            const Text('Total',
                style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
            Text(
              _currencyFmt.format(order.totalAmount),
              style: Theme.of(context)
                  .textTheme
                  .titleLarge
                  ?.copyWith(color: AppColors.primary, fontWeight: FontWeight.bold),
            ),
          ],
        ),

        // ── Action Buttons ──
        if (order.status != 'cancelled') ...[
          const SizedBox(height: 20),
          const Divider(height: 1, color: AppColors.border),
          const SizedBox(height: 16),
          if (_updating)
            const Center(child: CircularProgressIndicator())
          else if (order.status == 'completed')
            _buildRefundButton(order)
          else
            _buildActionButtons(order),
        ],
      ],
    );
  }

  Widget _buildActionButtons(OrderModel order) {
    final rv = 0; // row_version - server will validate

    switch (order.status) {
      case 'pending':
        return Row(
          children: [
            Expanded(
              child: OutlinedButton.icon(
                onPressed: () => _updateStatus(order.id, 'cancelled', rv),
                icon: const Icon(LucideIcons.x, size: 18),
                label: const Text('Tolak'),
                style: OutlinedButton.styleFrom(
                  foregroundColor: AppColors.error,
                  side: const BorderSide(color: AppColors.error),
                  padding: const EdgeInsets.symmetric(vertical: 14),
                ),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              flex: 2,
              child: ElevatedButton.icon(
                onPressed: () => _updateStatus(order.id, 'preparing', rv),
                icon: const Icon(LucideIcons.chefHat, size: 18),
                label: const Text('Terima & Proses'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppColors.primary,
                  padding: const EdgeInsets.symmetric(vertical: 14),
                ),
              ),
            ),
          ],
        );
      case 'preparing':
        return SizedBox(
          width: double.infinity,
          child: ElevatedButton.icon(
            onPressed: () => _updateStatus(order.id, 'ready', rv),
            icon: const Icon(LucideIcons.check, size: 18),
            label: const Text('Tandai Siap'),
            style: ElevatedButton.styleFrom(
              backgroundColor: AppColors.info,
              padding: const EdgeInsets.symmetric(vertical: 14),
            ),
          ),
        );
      case 'ready':
        return SizedBox(
          width: double.infinity,
          child: ElevatedButton.icon(
            onPressed: () => _updateStatus(order.id, 'completed', rv),
            icon: const Icon(LucideIcons.checkCircle, size: 18),
            label: const Text('Selesai'),
            style: ElevatedButton.styleFrom(
              backgroundColor: AppColors.success,
              padding: const EdgeInsets.symmetric(vertical: 14),
            ),
          ),
        );
      case 'served':
        return SizedBox(
          width: double.infinity,
          child: ElevatedButton.icon(
            onPressed: () => _updateStatus(order.id, 'completed', rv),
            icon: const Icon(LucideIcons.checkCircle, size: 18),
            label: const Text('Selesai'),
            style: ElevatedButton.styleFrom(
              backgroundColor: AppColors.success,
              padding: const EdgeInsets.symmetric(vertical: 14),
            ),
          ),
        );
      default:
        return const SizedBox.shrink();
    }
  }

  Widget _buildRefundButton(OrderModel order) {
    return SizedBox(
      width: double.infinity,
      child: OutlinedButton.icon(
        onPressed: () => _showRefundDialog(order),
        icon: const Icon(LucideIcons.rotateCcw, size: 18),
        label: const Text('Ajukan Refund'),
        style: OutlinedButton.styleFrom(
          foregroundColor: AppColors.warning,
          side: const BorderSide(color: AppColors.warning),
          padding: const EdgeInsets.symmetric(vertical: 14),
        ),
      ),
    );
  }

  void _showRefundDialog(OrderModel order) {
    final amountCtrl = TextEditingController(text: order.totalAmount.toStringAsFixed(0));
    final reasonCtrl = TextEditingController();
    bool isSubmitting = false;

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setDialogState) => AlertDialog(
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
          title: const Text('Ajukan Refund'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text('Order ${order.orderNumber}', style: const TextStyle(color: AppColors.textSecondary)),
              const SizedBox(height: 16),
              TextField(
                controller: amountCtrl,
                keyboardType: TextInputType.number,
                decoration: InputDecoration(
                  labelText: 'Jumlah Refund',
                  prefixText: 'Rp ',
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: reasonCtrl,
                maxLines: 2,
                decoration: InputDecoration(
                  labelText: 'Alasan Refund *',
                  hintText: 'Contoh: Makanan tidak sesuai pesanan',
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                ),
              ),
            ],
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Batal')),
            ElevatedButton(
              onPressed: isSubmitting ? null : () async {
                final reason = reasonCtrl.text.trim();
                if (reason.length < 3) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('Alasan refund wajib diisi (min 3 karakter)'), backgroundColor: AppColors.error),
                  );
                  return;
                }
                setDialogState(() => isSubmitting = true);
                try {
                  // Get payment_id for this order
                  final cache = SessionCache.instance;
                  final dio = Dio(BaseOptions(baseUrl: AppConfig.apiV1, connectTimeout: const Duration(seconds: 15)));
                  final payRes = await dio.get(
                    '/payments/',
                    queryParameters: {'outlet_id': cache.outletId, 'order_id': order.id},
                    options: Options(headers: cache.authHeaders),
                  );
                  final payments = payRes.data['data'] as List? ?? [];
                  if (payments.isEmpty) {
                    if (ctx.mounted) Navigator.pop(ctx);
                    if (mounted) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(content: Text('Payment tidak ditemukan'), backgroundColor: AppColors.error),
                      );
                    }
                    return;
                  }
                  final paymentId = payments.first['id'];
                  final amount = double.tryParse(amountCtrl.text.trim()) ?? order.totalAmount;

                  final refundRes = await dio.post(
                    '/payments/refunds',
                    options: Options(headers: cache.authHeaders),
                    data: {'payment_id': paymentId, 'amount': amount, 'reason': reason},
                  );

                  if (ctx.mounted) Navigator.pop(ctx);
                  if (mounted) {
                    final msg = refundRes.data['message'] ?? 'Refund diajukan';
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(content: Text(msg), backgroundColor: AppColors.success, behavior: SnackBarBehavior.floating),
                    );
                  }
                } on DioException catch (e) {
                  setDialogState(() => isSubmitting = false);
                  final detail = e.response?.data?['detail'] ?? 'Gagal mengajukan refund';
                  if (mounted) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(content: Text(detail.toString()), backgroundColor: AppColors.error),
                    );
                  }
                }
              },
              style: ElevatedButton.styleFrom(backgroundColor: AppColors.warning),
              child: isSubmitting
                  ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                  : const Text('Ajukan Refund'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildBadge(String label, String value, Color color) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label,
            style: const TextStyle(color: AppColors.textSecondary, fontSize: 12)),
        const SizedBox(height: 4),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
          decoration: BoxDecoration(
            color: color.withOpacity(0.1),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Text(value,
              style: TextStyle(
                  color: color, fontWeight: FontWeight.bold, fontSize: 12)),
        ),
      ],
    );
  }

  Widget _buildSummaryRow(String label, String value, {Color? valueColor}) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(label, style: const TextStyle(color: AppColors.textSecondary)),
        Text(value, style: TextStyle(fontWeight: FontWeight.w600, color: valueColor)),
      ],
    );
  }
}
