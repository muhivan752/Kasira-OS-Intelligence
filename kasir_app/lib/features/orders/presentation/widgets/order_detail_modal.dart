import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:lucide_icons/lucide_icons.dart';
import 'package:intl/intl.dart';
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
        if (order.taxAmount > 0) ...[
          const SizedBox(height: 6),
          _buildSummaryRow('Pajak', _currencyFmt.format(order.taxAmount)),
        ],
        if (order.discountAmount > 0) ...[
          const SizedBox(height: 6),
          _buildSummaryRow('Diskon', '- ${_currencyFmt.format(order.discountAmount)}'),
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
        if (order.status != 'completed' && order.status != 'cancelled') ...[
          const SizedBox(height: 20),
          const Divider(height: 1, color: AppColors.border),
          const SizedBox(height: 16),
          if (_updating)
            const Center(child: CircularProgressIndicator())
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

  Widget _buildSummaryRow(String label, String value) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(label, style: const TextStyle(color: AppColors.textSecondary)),
        Text(value, style: const TextStyle(fontWeight: FontWeight.w600)),
      ],
    );
  }
}
