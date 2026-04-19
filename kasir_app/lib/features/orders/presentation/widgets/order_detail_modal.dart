import 'dart:async';
import 'package:drift/drift.dart' as drift;
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:lucide_icons/lucide_icons.dart';
import 'package:intl/intl.dart';
import 'package:dio/dio.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../../../../core/config/app_config.dart';
import '../../../../core/database/app_database.dart';
import '../../../../core/services/session_cache.dart';
import '../../../../core/services/printer_service.dart';
import '../../../../core/sync/sync_provider.dart';
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
            _buildCompletedActions(order)
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

  Widget _buildCompletedActions(OrderModel order) {
    return Column(
      children: [
        Row(
          children: [
            Expanded(
              child: OutlinedButton.icon(
                onPressed: () => _reprintReceipt(order),
                icon: const Icon(LucideIcons.printer, size: 18),
                label: const Text('Cetak Ulang'),
                style: OutlinedButton.styleFrom(
                  foregroundColor: AppColors.primary,
                  side: const BorderSide(color: AppColors.primary),
                  padding: const EdgeInsets.symmetric(vertical: 14),
                ),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: OutlinedButton.icon(
                onPressed: () => _showRefundDialog(order),
                icon: const Icon(LucideIcons.rotateCcw, size: 18),
                label: const Text('Refund'),
                style: OutlinedButton.styleFrom(
                  foregroundColor: AppColors.warning,
                  side: const BorderSide(color: AppColors.warning),
                  padding: const EdgeInsets.symmetric(vertical: 14),
                ),
              ),
            ),
          ],
        ),
      ],
    );
  }

  Future<void> _reprintReceipt(OrderModel order) async {
    final messenger = ScaffoldMessenger.of(context);
    ReceiptData? receiptData;
    bool offline = false;

    try {
      final cache = SessionCache.instance;
      final dio = Dio(BaseOptions(baseUrl: AppConfig.apiV1, connectTimeout: const Duration(seconds: 5)));
      final resp = await dio.get(
        '/orders/${order.id}/receipt',
        options: Options(headers: cache.authHeaders),
      );
      final data = resp.data['data'] as Map<String, dynamic>;
      receiptData = ReceiptDataJson.fromJson(data);
      // Cache outlet info untuk offline fallback next time
      await _cacheOutletInfo(
        name: receiptData.outletName,
        address: receiptData.outletAddress,
        taxNumber: receiptData.taxNumber,
        customFooter: receiptData.customFooter,
      );
    } on DioException catch (_) {
      // Offline / backend unreachable → fallback ke drift DB
      offline = true;
      try {
        receiptData = await _buildReceiptFromDrift(order);
      } catch (dbErr) {
        if (!mounted) return;
        messenger.showSnackBar(
          SnackBar(content: Text('Offline + data lokal tidak lengkap: $dbErr'), backgroundColor: AppColors.error),
        );
        return;
      }
    } catch (e) {
      if (!mounted) return;
      messenger.showSnackBar(
        SnackBar(content: Text('Gagal ambil data struk: $e'), backgroundColor: AppColors.error),
      );
      return;
    }

    if (receiptData == null) return;

    final bytes = buildReprintReceipt(receiptData);
    final ok = await ref.read(printerProvider.notifier).printBytes(bytes);
    if (!mounted) return;
    messenger.showSnackBar(
      SnackBar(
        content: Text(ok
            ? (offline ? 'Struk dicetak ulang (offline)' : 'Struk dicetak ulang')
            : 'Gagal cetak — cek printer'),
        backgroundColor: ok ? AppColors.success : AppColors.error,
        behavior: SnackBarBehavior.floating,
      ),
    );
  }

  Future<ReceiptData> _buildReceiptFromDrift(OrderModel order) async {
    final db = ref.read(databaseProvider);
    final currentOutletId = SessionCache.instance.outletId;

    // Outlet scoping — verify order milik outlet aktif. Defense-in-depth
    // seandainya drift masih nyimpen data outlet lama setelah user switch.
    final orderRow = await (db.select(db.orders)..where((t) => t.id.equals(order.id))).getSingleOrNull();
    if (orderRow == null) {
      throw Exception('Order tidak ditemukan di DB lokal');
    }
    if (currentOutletId != null && orderRow.outletId != currentOutletId) {
      throw Exception('Order ini bukan milik outlet aktif');
    }

    final orderItemRows = await (db.select(db.orderItems)..where((t) => t.orderId.equals(order.id))).get();
    if (orderItemRows.isEmpty) {
      throw Exception('Item pesanan tidak ada di DB lokal');
    }

    // Ambil nama produk dari Products table (drift gak simpan product_name di OrderItemLocal)
    final productIds = orderItemRows.map((e) => e.productId).toSet().toList();
    final productRows = await (db.select(db.products)..where((t) => t.id.isIn(productIds))).get();
    final productNameById = {for (final p in productRows) p.id: p.name};

    final items = orderItemRows.map((oi) {
      return ReceiptLineItem(
        name: productNameById[oi.productId] ?? 'Item',
        qty: oi.quantity,
        price: oi.unitPrice,
        notes: oi.notes,
      );
    }).toList();

    // Payment terakhir
    final paymentRows = await (db.select(db.payments)
          ..where((t) => t.orderId.equals(order.id))
          ..orderBy([(t) => drift.OrderingTerm.desc(t.paidAt)]))
        .get();
    final payment = paymentRows.isNotEmpty ? paymentRows.first : null;
    final methodLabel = switch (payment?.paymentMethod ?? 'cash') {
      'cash' => 'Tunai',
      'qris' => 'QRIS',
      'card' => 'Kartu',
      'transfer' => 'Transfer',
      final x => x.toUpperCase(),
    };
    final amountPaid = payment?.amountPaid ?? order.totalAmount;
    // Change: amountPaid - totalAmount (kalau cash overpay)
    final changeAmount = amountPaid > order.totalAmount ? amountPaid - order.totalAmount : 0.0;

    // Outlet info dari SharedPreferences cache (terisi pas online)
    final prefs = await SharedPreferences.getInstance();
    final outletName = prefs.getString('c_outlet_name') ?? 'Kasira';
    final outletAddress = prefs.getString('c_outlet_address') ?? '';
    final taxNumber = prefs.getString('c_outlet_tax_number');
    final customFooter = prefs.getString('c_outlet_custom_footer');

    final dt = order.createdAt.toLocal();
    final dateStr = DateFormat('dd/MM/yyyy HH:mm').format(dt);

    return ReceiptData(
      outletName: outletName,
      outletAddress: outletAddress,
      orderNumber: order.displayNumber.toString(),
      dateTime: dateStr,
      items: items,
      subtotal: order.subtotal,
      serviceCharge: order.serviceChargeAmount > 0 ? order.serviceChargeAmount : null,
      tax: order.taxAmount > 0 ? order.taxAmount : null,
      total: order.totalAmount,
      paymentMethod: methodLabel,
      amountPaid: amountPaid,
      changeAmount: changeAmount,
      taxNumber: (taxNumber != null && taxNumber.isNotEmpty) ? taxNumber : null,
      customFooter: (customFooter != null && customFooter.isNotEmpty) ? customFooter : null,
    );
  }

  Future<void> _cacheOutletInfo({
    required String name,
    required String address,
    String? taxNumber,
    String? customFooter,
  }) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('c_outlet_name', name);
    await prefs.setString('c_outlet_address', address);
    if (taxNumber != null) {
      await prefs.setString('c_outlet_tax_number', taxNumber);
    } else {
      await prefs.remove('c_outlet_tax_number');
    }
    if (customFooter != null) {
      await prefs.setString('c_outlet_custom_footer', customFooter);
    } else {
      await prefs.remove('c_outlet_custom_footer');
    }
  }

  Future<void> _printRefundReceipt(OrderModel order, double amount, String reason) async {
    try {
      // Ambil outlet info dari cache (diisi saat reprint/receipt online) — offline-first
      final prefs = await SharedPreferences.getInstance();
      String outletName = prefs.getString('c_outlet_name') ?? 'Kasira';
      String outletAddress = prefs.getString('c_outlet_address') ?? '';
      String? taxNumber = prefs.getString('c_outlet_tax_number');
      String? customFooter = prefs.getString('c_outlet_custom_footer');

      // Best-effort refresh outlet info kalau online (non-blocking pada offline)
      try {
        final cache = SessionCache.instance;
        final dio = Dio(BaseOptions(baseUrl: AppConfig.apiV1, connectTimeout: const Duration(seconds: 3)));
        final recRes = await dio.get(
          '/orders/${order.id}/receipt',
          options: Options(headers: cache.authHeaders),
        );
        final d = recRes.data['data'] as Map<String, dynamic>;
        outletName = (d['outlet_name'] ?? outletName).toString();
        outletAddress = (d['outlet_address'] ?? outletAddress).toString();
        taxNumber = d['tax_number']?.toString() ?? taxNumber;
        customFooter = d['custom_footer']?.toString() ?? customFooter;
        await _cacheOutletInfo(
          name: outletName, address: outletAddress,
          taxNumber: taxNumber, customFooter: customFooter,
        );
      } catch (_) {
        // offline — pakai cache yang udah di-set di atas
      }

      final now = DateTime.now();
      final dt = DateFormat('dd/MM/yyyy HH:mm').format(now);
      final refundData = RefundReceiptData(
        outletName: outletName,
        outletAddress: outletAddress,
        originalOrderNumber: order.displayNumber.toString(),
        dateTime: dt,
        refundAmount: amount,
        reason: reason,
        taxNumber: taxNumber,
        customFooter: customFooter,
      );
      final bytes = buildRefundReceipt(refundData);
      await ref.read(printerProvider.notifier).printBytes(bytes);
    } catch (_) {
      // print failure jangan block flow refund — sudah ada snackbar success refund
    }
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
                    // Auto-print struk refund (best-effort, jangan block)
                    unawaited(_printRefundReceipt(order, amount, reason));
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
