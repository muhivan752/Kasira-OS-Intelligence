import 'dart:async';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:lucide_icons/lucide_icons.dart';
import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:qr_flutter/qr_flutter.dart';
import '../../../../core/config/app_config.dart';
import '../../../../core/theme/app_colors.dart';

class PaymentModal extends StatefulWidget {
  final double totalAmount;
  final String orderId;
  final void Function(String paymentMethod, double amountPaid) onPaymentSuccess;

  const PaymentModal({
    super.key,
    required this.totalAmount,
    required this.orderId,
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

  // QRIS State
  bool _isLoadingQris = false;
  String? _qrisUrl;
  String? _qrisPaymentId;
  String? _qrisError;
  bool _isQrisPaid = false;
  int _qrisTimerSeconds = 15 * 60;
  Timer? _qrisTimer;
  Timer? _qrisPollingTimer;

  Dio get _dio => Dio(BaseOptions(
    baseUrl: AppConfig.apiV1,
    connectTimeout: const Duration(seconds: 10),
    receiveTimeout: const Duration(seconds: 10),
  ));
  final _storage = const FlutterSecureStorage();

  Future<void> _submitCashPayment(double amountPaid) async {
    try {
      final token = await _storage.read(key: 'access_token');
      final tenantId = await _storage.read(key: 'tenant_id');
      final outletId = await _storage.read(key: 'outlet_id') ?? '';
      final change = amountPaid - widget.totalAmount;

      await _dio.post(
        '/payments/',
        options: Options(headers: {
          if (token != null) 'Authorization': 'Bearer $token',
          if (tenantId != null) 'X-Tenant-ID': tenantId,
        }),
        data: {
          'order_id': widget.orderId,
          'outlet_id': outletId,
          'payment_method': 'cash',
          'amount_due': widget.totalAmount,
          'amount_paid': amountPaid,
          'change_amount': change < 0 ? 0 : change,
        },
      );
    } catch (_) {
      // Payment tetap lanjut meski gagal catat (offline fallback)
    }
    if (mounted) {
      widget.onPaymentSuccess(_paymentMethod, amountPaid);
      Navigator.pop(context);
    }
  }

  @override
  void initState() {
    super.initState();
    _amountReceived = widget.totalAmount;
    _amountController.text = widget.totalAmount.toInt().toString();
  }

  @override
  void dispose() {
    _amountController.dispose();
    _qrisTimer?.cancel();
    _qrisPollingTimer?.cancel();
    super.dispose();
  }

  void _startQrisTimer() {
    _qrisTimer?.cancel();
    _qrisTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (_qrisTimerSeconds > 0) {
        setState(() {
          _qrisTimerSeconds--;
        });
      } else {
        timer.cancel();
        _qrisPollingTimer?.cancel();
      }
    });
  }

  void _startQrisPolling() {
    _qrisPollingTimer?.cancel();
    _qrisPollingTimer = Timer.periodic(const Duration(seconds: 3), (timer) async {
      if (_qrisPaymentId == null) return;

      try {
        final token = await _storage.read(key: 'access_token');
        final tenantId = await _storage.read(key: 'tenant_id');
        final response = await _dio.get(
          '/payments/$_qrisPaymentId/status',
          options: Options(
            headers: {
              if (token != null) 'Authorization': 'Bearer $token',
              if (tenantId != null) 'X-Tenant-ID': tenantId,
            },
          ),
        );

        final data = response.data['data'];
        if (data['status'] == 'paid') {
          timer.cancel();
          _qrisTimer?.cancel();
          setState(() {
            _isQrisPaid = true;
          });
          
          Future.delayed(const Duration(seconds: 2), () {
            if (mounted) {
              widget.onPaymentSuccess('QRIS', widget.totalAmount);
              Navigator.pop(context);
            }
          });
        }
      } catch (e) {
        // Ignore polling errors
      }
    });
  }

  Future<void> _generateQris() async {
    setState(() {
      _isLoadingQris = true;
      _qrisError = null;
    });

    try {
      final token = await _storage.read(key: 'access_token');
      final tenantId = await _storage.read(key: 'tenant_id');
      final outletId = await _storage.read(key: 'outlet_id') ?? '';

      final response = await _dio.post(
        '/payments/',
        options: Options(
          headers: {
            if (token != null) 'Authorization': 'Bearer $token',
            if (tenantId != null) 'X-Tenant-ID': tenantId,
          },
        ),
        data: {
          'order_id': widget.orderId,
          'outlet_id': outletId,
          'payment_method': 'qris',
          'amount_due': widget.totalAmount,
          'amount_paid': widget.totalAmount,
          'change_amount': 0,
        },
      );

      final data = response.data['data'];
      if (data['status'] == 'failed') {
        setState(() {
          _qrisError = 'QRIS tidak tersedia';
          _isLoadingQris = false;
        });
        return;
      }

      final qrisUrl = data['qris_url'];
      final paymentId = data['id'];

      if (qrisUrl != null && paymentId != null) {
        setState(() {
          _qrisUrl = qrisUrl;
          _qrisPaymentId = paymentId;
          _isLoadingQris = false;
          _qrisTimerSeconds = 15 * 60;
        });
        _startQrisTimer();
        _startQrisPolling();
      } else {
        setState(() {
          _qrisError = 'QRIS tidak tersedia';
          _isLoadingQris = false;
        });
      }
    } catch (e) {
      setState(() {
        _qrisError = 'QRIS tidak tersedia';
        _isLoadingQris = false;
      });
    }
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
                    ] else if (_paymentMethod == 'QRIS') ...[
                      Expanded(
                        child: Center(
                          child: _isLoadingQris
                              ? const CircularProgressIndicator()
                              : _qrisError != null
                                  ? Column(
                                      mainAxisAlignment: MainAxisAlignment.center,
                                      children: [
                                        const Icon(LucideIcons.alertCircle, size: 48, color: AppColors.error),
                                        const SizedBox(height: 16),
                                        Text(_qrisError!, style: Theme.of(context).textTheme.titleMedium),
                                        const SizedBox(height: 24),
                                        ElevatedButton(
                                          onPressed: () => setState(() => _paymentMethod = 'Cash'),
                                          child: const Text('Bayar Cash'),
                                        ),
                                      ],
                                    )
                                  : _isQrisPaid
                                      ? Column(
                                          mainAxisAlignment: MainAxisAlignment.center,
                                          children: [
                                            const Icon(LucideIcons.checkCircle2, size: 64, color: AppColors.success),
                                            const SizedBox(height: 16),
                                            Text('Pembayaran Berhasil', style: Theme.of(context).textTheme.titleLarge?.copyWith(color: AppColors.success)),
                                          ],
                                        )
                                      : Column(
                                          mainAxisAlignment: MainAxisAlignment.center,
                                          children: [
                                            if (_qrisUrl != null)
                                              Container(
                                                padding: const EdgeInsets.all(16),
                                                decoration: BoxDecoration(
                                                  color: Colors.white,
                                                  borderRadius: BorderRadius.circular(16),
                                                  border: Border.all(color: AppColors.border),
                                                ),
                                                child: QrImageView(
                                                  data: _qrisUrl!,
                                                  version: QrVersions.auto,
                                                  size: 200.0,
                                                ),
                                              ),
                                            const SizedBox(height: 24),
                                            if (_qrisTimerSeconds > 0) ...[
                                              Text(
                                                'Selesaikan pembayaran dalam',
                                                style: Theme.of(context).textTheme.bodyLarge,
                                              ),
                                              const SizedBox(height: 8),
                                              Text(
                                                '${(_qrisTimerSeconds ~/ 60).toString().padLeft(2, '0')}:${(_qrisTimerSeconds % 60).toString().padLeft(2, '0')}',
                                                style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                                                      color: AppColors.error,
                                                      fontWeight: FontWeight.bold,
                                                    ),
                                              ),
                                            ] else ...[
                                              const Text('Waktu pembayaran habis', style: TextStyle(color: AppColors.error)),
                                              const SizedBox(height: 16),
                                              ElevatedButton(
                                                onPressed: () => setState(() => _paymentMethod = 'Cash'),
                                                child: const Text('Ganti ke Cash'),
                                              ),
                                            ],
                                          ],
                                        ),
                        ),
                      ),
                    ] else ...[
                      const Expanded(
                        child: Center(
                          child: Text('Metode pembayaran belum tersedia'),
                        ),
                      ),
                    ],
                    
                    if (_paymentMethod != 'QRIS') ...[
                      const Spacer(),
                      SizedBox(
                        width: double.infinity,
                        height: 56,
                        child: ElevatedButton(
                          onPressed: (isCash && change < 0) ? null : () async {
                            await _submitCashPayment(_amountReceived);
                          },
                          style: ElevatedButton.styleFrom(
                            backgroundColor: (isCash && change < 0) ? AppColors.border : AppColors.primary,
                          ),
                          child: const Text('SELESAIKAN PEMBAYARAN'),
                        ),
                      ),
                    ],
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
      onTap: () {
        setState(() => _paymentMethod = label);
        if (label == 'QRIS' && (_qrisUrl == null || _qrisError != null) && !_isLoadingQris) {
          _generateQris();
        }
      },
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
