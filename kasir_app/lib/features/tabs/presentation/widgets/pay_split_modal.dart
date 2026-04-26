import 'dart:async';
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:lucide_icons/lucide_icons.dart';
import '../../../../core/config/app_config.dart';
import '../../../../core/services/printer_service.dart';
import '../../../../core/services/session_cache.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/widgets/send_wa_receipt_dialog.dart';
import '../../providers/tab_provider.dart';

/// Pay a single split or pay full remaining tab.
/// If [split] is null, pays the full remaining amount.
class PaySplitModal extends ConsumerStatefulWidget {
  final TabModel tab;
  final TabSplitModel? split;
  final void Function(TabModel updatedTab) onPaid;

  const PaySplitModal({super.key, required this.tab, this.split, required this.onPaid});

  @override
  ConsumerState<PaySplitModal> createState() => _PaySplitModalState();
}

class _PaySplitModalState extends ConsumerState<PaySplitModal> {
  final _currency = NumberFormat.currency(locale: 'id_ID', symbol: 'Rp ', decimalDigits: 0);
  String _paymentMethod = 'cash';
  final _amountController = TextEditingController();
  double _amountReceived = 0;
  bool _isLoading = false;
  String? _error;

  double get _amountDue => widget.split?.amount ?? widget.tab.remainingAmount;
  String get _label => widget.split?.label ?? 'Sisa Tagihan';

  @override
  void initState() {
    super.initState();
    _amountReceived = _amountDue;
    _amountController.text = _amountDue.toStringAsFixed(0);
  }

  @override
  void dispose() {
    _amountController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final change = _amountReceived - _amountDue;

    return Padding(
      padding: EdgeInsets.only(
        left: 20, right: 20, top: 20,
        bottom: MediaQuery.of(context).viewInsets.bottom + 20,
      ),
      child: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header
            Row(
              children: [
                const Icon(LucideIcons.banknote, color: AppColors.primary),
                const SizedBox(width: 12),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Bayar $_label', style: Theme.of(context).textTheme.titleLarge),
                    Text(widget.tab.tabNumber, style: TextStyle(color: AppColors.textSecondary, fontSize: 13)),
                  ],
                ),
                const Spacer(),
                IconButton(onPressed: () => Navigator.pop(context), icon: const Icon(LucideIcons.x)),
              ],
            ),
            const SizedBox(height: 16),

            // Amount due
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: AppColors.primary.withOpacity(0.05),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text('Tagihan', style: TextStyle(fontSize: 15)),
                  Text(
                    _currency.format(_amountDue),
                    style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 22, color: AppColors.primary),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20),

            // Payment method (cash-only — QRIS untuk tab belum support)
            Text('Metode Pembayaran', style: TextStyle(color: AppColors.textSecondary, fontSize: 13)),
            const SizedBox(height: 8),
            Row(
              children: [
                _buildMethodChip('cash', 'Cash', LucideIcons.banknote),
              ],
            ),
            const SizedBox(height: 8),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              decoration: BoxDecoration(
                color: AppColors.warning.withOpacity(0.1),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: AppColors.warning.withOpacity(0.3)),
              ),
              child: Row(
                children: [
                  const Icon(LucideIcons.info, size: 14, color: AppColors.warning),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      'QRIS untuk tab belum tersedia. Pakai POS reguler kalau customer mau bayar QRIS.',
                      style: TextStyle(fontSize: 11, color: AppColors.textSecondary),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20),

            if (_paymentMethod == 'cash') ...[
              // Cash input
              Text('Uang Diterima', style: TextStyle(color: AppColors.textSecondary, fontSize: 13)),
              const SizedBox(height: 8),
              TextField(
                controller: _amountController,
                keyboardType: TextInputType.number,
                style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold),
                decoration: InputDecoration(
                  prefixText: 'Rp ',
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                ),
                onChanged: (val) {
                  setState(() {
                    _amountReceived = double.tryParse(val) ?? 0;
                    _error = null;
                  });
                },
              ),
              const SizedBox(height: 12),
              Row(
                children: [
                  _buildQuickBtn(_amountDue, 'Pas'),
                  const SizedBox(width: 8),
                  _buildQuickBtn(50000, _currency.format(50000)),
                  const SizedBox(width: 8),
                  _buildQuickBtn(100000, _currency.format(100000)),
                ],
              ),
              const SizedBox(height: 16),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text('Kembalian', style: Theme.of(context).textTheme.titleMedium),
                  Text(
                    _currency.format(change > 0 ? change : 0),
                    style: TextStyle(
                      fontWeight: FontWeight.bold,
                      fontSize: 18,
                      color: change >= 0 ? AppColors.success : AppColors.error,
                    ),
                  ),
                ],
              ),
            ] else ...[
              Container(
                padding: const EdgeInsets.all(20),
                decoration: BoxDecoration(
                  color: AppColors.surfaceVariant,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Column(
                  children: [
                    Icon(LucideIcons.qrCode, size: 48, color: AppColors.textSecondary),
                    const SizedBox(height: 12),
                    Text(
                      'QRIS akan diproses setelah konfirmasi',
                      style: TextStyle(color: AppColors.textSecondary),
                      textAlign: TextAlign.center,
                    ),
                  ],
                ),
              ),
            ],

            if (_error != null) ...[
              const SizedBox(height: 12),
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: AppColors.error.withOpacity(0.08),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Row(
                  children: [
                    const Icon(LucideIcons.alertCircle, color: AppColors.error, size: 16),
                    const SizedBox(width: 8),
                    Expanded(child: Text(_error!, style: const TextStyle(color: AppColors.error, fontSize: 13))),
                  ],
                ),
              ),
            ],

            const SizedBox(height: 24),
            SizedBox(
              width: double.infinity,
              height: 52,
              child: FilledButton.icon(
                onPressed: _isLoading || (_paymentMethod == 'cash' && change < 0) ? null : _submitPayment,
                icon: _isLoading
                    ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                    : const Icon(LucideIcons.check, size: 18),
                label: Text('Bayar ${_currency.format(_amountDue)}'),
                style: FilledButton.styleFrom(
                  backgroundColor: (_paymentMethod == 'cash' && change < 0)
                      ? AppColors.border
                      : AppColors.success,
                  padding: const EdgeInsets.symmetric(vertical: 14),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildMethodChip(String method, String label, IconData icon) {
    final isSelected = _paymentMethod == method;
    return Expanded(
      child: GestureDetector(
        onTap: () => setState(() { _paymentMethod = method; _error = null; }),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 12),
          decoration: BoxDecoration(
            color: isSelected ? AppColors.primary.withOpacity(0.1) : AppColors.surface,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: isSelected ? AppColors.primary : AppColors.border, width: 2),
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(icon, size: 18, color: isSelected ? AppColors.primary : AppColors.textSecondary),
              const SizedBox(width: 8),
              Text(label, style: TextStyle(
                fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                color: isSelected ? AppColors.primary : AppColors.textSecondary,
              )),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildQuickBtn(double amount, String label) {
    return Expanded(
      child: OutlinedButton(
        onPressed: () {
          setState(() {
            _amountReceived = amount;
            _amountController.text = amount.toStringAsFixed(0);
            _error = null;
          });
        },
        style: OutlinedButton.styleFrom(padding: const EdgeInsets.symmetric(vertical: 10)),
        child: Text(label, style: const TextStyle(fontSize: 12), overflow: TextOverflow.ellipsis),
      ),
    );
  }

  Future<void> _submitPayment() async {
    setState(() { _isLoading = true; _error = null; });

    final notifier = ref.read(tabProvider.notifier);
    final idempKey = 'split_${widget.tab.id}_${widget.split?.id ?? "full"}_${DateTime.now().millisecondsSinceEpoch}';

    TabModel? result;

    if (widget.split != null) {
      // Pay single split
      result = await notifier.paySplit(
        widget.tab.id,
        widget.split!.id,
        _paymentMethod,
        _amountReceived,
        widget.split!.rowVersion,
        idempotencyKey: idempKey,
      );
    } else {
      // Pay full remaining
      result = await notifier.payFull(
        widget.tab.id,
        _paymentMethod,
        _amountReceived,
        widget.tab.rowVersion,
        idempotencyKey: idempKey,
      );
    }

    if (mounted) {
      setState(() => _isLoading = false);
      if (result != null) {
        // Capture stable refs SEBELUM Navigator.pop — context modal ke-deactivate
        // setelah pop, navigator + messenger tetap alive (parent page masih ada).
        final messenger = ScaffoldMessenger.of(context);
        final rootNav = Navigator.of(context, rootNavigator: true);

        // Auto-print struk untuk pembayaran yg udah confirmed (cash only — QRIS pending poll).
        // Fail-silent (Rule #54) — print error gak boleh block snackbar success.
        if (_paymentMethod == 'cash') {
          if (widget.split != null) {
            unawaited(_autoPrintSplitReceipt(widget.tab.id, widget.split!.id));
          } else {
            unawaited(_autoPrintFullReceipt(widget.tab.orderIds));
          }
        }

        Navigator.pop(context);
        widget.onPaid(result);

        // Tab lunas snackbar
        if (result.isPaid) {
          messenger.showSnackBar(
            const SnackBar(
              content: Text('Tab lunas! Semua pembayaran selesai.'),
              backgroundColor: AppColors.success,
            ),
          );
        }

        // Snackbar action "Kirim WA" — only for cash success (QRIS pending = jangan kirim)
        if (_paymentMethod == 'cash' && widget.tab.orderIds.isNotEmpty) {
          // Defer 700ms biar gak overlap sama snackbar "lunas" di atas
          Future.delayed(const Duration(milliseconds: 700), () {
            messenger.showSnackBar(
              SnackBar(
                content: const Text('Mau kirim struk via WA ke customer?'),
                backgroundColor: AppColors.surfaceElevated,
                duration: const Duration(seconds: 6),
                action: SnackBarAction(
                  label: '📱 Kirim WA',
                  textColor: AppColors.primary,
                  onPressed: () {
                    showDialog<void>(
                      context: rootNav.context,
                      builder: (_) => SendWaReceiptDialog(
                        orderId: widget.tab.orderIds.first,
                        // pay-split + pay-full = full order receipt (subset gak supported
                        // untuk pay_split — backend gak link items.paid_payment_id ke split)
                      ),
                    );
                  },
                ),
              ),
            );
          });
        }
      } else {
        setState(() => _error = ref.read(tabProvider).error ?? 'Gagal memproses pembayaran');
      }
    }
  }

  Future<void> _autoPrintSplitReceipt(String tabId, String splitId) async {
    try {
      final cache = SessionCache.instance;
      final dio = Dio(BaseOptions(
        baseUrl: AppConfig.apiV1,
        connectTimeout: const Duration(seconds: 6),
        receiveTimeout: const Duration(seconds: 6),
      ));
      final res = await dio.get(
        '/tabs/$tabId/splits/$splitId/receipt',
        options: Options(headers: cache.authHeaders),
      );
      final data = res.data['data'] as Map<String, dynamic>?;
      if (data == null) return;
      final receiptData = SplitReceiptData.fromJson(data);
      final bytes = buildSplitReceipt(receiptData);
      await ref.read(printerProvider.notifier).printBytes(bytes);
    } catch (_) {
      // silent fail — print issue jangan block payment flow
    }
  }

  /// Pay-full path: cetak 1 struk per order di tab.
  /// Pakai endpoint reguler /orders/{id}/receipt + buildReceipt — orders udah
  /// fully paid via pay-full settle items + tab close.
  /// Fail-silent (Rule #54) — print issue jangan block payment flow.
  Future<void> _autoPrintFullReceipt(List<String> orderIds) async {
    if (orderIds.isEmpty) return;
    try {
      final cache = SessionCache.instance;
      final dio = Dio(BaseOptions(
        baseUrl: AppConfig.apiV1,
        connectTimeout: const Duration(seconds: 6),
        receiveTimeout: const Duration(seconds: 6),
      ));
      final notifier = ref.read(printerProvider.notifier);
      for (final orderId in orderIds) {
        try {
          final res = await dio.get(
            '/orders/$orderId/receipt',
            options: Options(headers: cache.authHeaders),
          );
          final data = res.data['data'] as Map<String, dynamic>?;
          if (data == null) continue;
          final receiptData = ReceiptData.fromJson(data);
          final bytes = buildReceipt(receiptData);
          await notifier.printBytes(bytes);
        } catch (_) {
          // skip order ini, lanjut ke berikutnya
        }
      }
    } catch (_) {
      // silent fail outer
    }
  }
}
