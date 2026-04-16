import 'dart:async';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:lucide_icons/lucide_icons.dart';
import 'package:dio/dio.dart';
import 'package:qr_flutter/qr_flutter.dart';
import '../../../../core/config/app_config.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/services/session_cache.dart';

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

  // Inline error untuk cash payment
  String? _cashError;

  Dio get _dio => Dio(BaseOptions(
    baseUrl: AppConfig.apiV1,
    connectTimeout: const Duration(seconds: 10),
    receiveTimeout: const Duration(seconds: 10),
  ));
  SessionCache get _cache => SessionCache.instance;

  Future<void> _submitCashPayment(double amountPaid) async {
    setState(() {
      _isLoadingQris = true;
      _cashError = null;
    });
    try {
      final outletId = _cache.outletId ?? '';
      final shiftId = _cache.shiftSessionId;
      final change = amountPaid - widget.totalAmount;

      await _dio.post(
        '/payments/',
        options: Options(headers: _cache.authHeaders),
        data: {
          'order_id': widget.orderId,
          'outlet_id': outletId,
          'payment_method': 'cash',
          'amount_due': widget.totalAmount,
          'amount_paid': amountPaid,
          'change_amount': change < 0 ? 0 : change,
          if (shiftId != null) 'shift_session_id': shiftId,
        },
      );

      if (mounted) {
        setState(() => _isLoadingQris = false);
        widget.onPaymentSuccess(_paymentMethod, amountPaid);
        Navigator.pop(context);
      }
    } on DioException catch (e) {
      final detail = e.response?.data?['detail'] ?? 'Gagal memproses pembayaran';
      if (mounted) {
        setState(() {
          _isLoadingQris = false;
          _cashError = detail.toString();
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _isLoadingQris = false;
          _cashError = 'Terjadi kesalahan: $e';
        });
      }
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
        setState(() => _qrisTimerSeconds--);
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
        final response = await _dio.get(
          '/payments/$_qrisPaymentId/status',
          options: Options(headers: _cache.authHeaders),
        );
        final data = response.data['data'];
        if (data != null && data['status'] == 'paid') {
          timer.cancel();
          _qrisTimer?.cancel();
          if (mounted) setState(() => _isQrisPaid = true);
          Future.delayed(const Duration(seconds: 2), () {
            if (mounted) {
              widget.onPaymentSuccess('QRIS', widget.totalAmount);
              Navigator.pop(context);
            }
          });
        }
      } catch (_) {}
    });
  }

  Future<void> _generateQris() async {
    setState(() {
      _isLoadingQris = true;
      _qrisError = null;
    });
    try {
      final outletId = _cache.outletId ?? '';
      final shiftId = _cache.shiftSessionId;

      final response = await _dio.post(
        '/payments/',
        options: Options(headers: _cache.authHeaders),
        data: {
          'order_id': widget.orderId,
          'outlet_id': outletId,
          'payment_method': 'qris',
          'amount_due': widget.totalAmount,
          'amount_paid': widget.totalAmount,
          'change_amount': 0,
          if (shiftId != null) 'shift_session_id': shiftId,
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
    } on DioException catch (e) {
      final detail = e.response?.data?['detail'] ?? 'QRIS tidak tersedia';
      setState(() {
        _qrisError = detail.toString();
        _isLoadingQris = false;
      });
    } catch (_) {
      setState(() {
        _qrisError = 'QRIS tidak tersedia';
        _isLoadingQris = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final screenWidth = MediaQuery.of(context).size.width;
    final isNarrow = screenWidth < 600;

    return Dialog(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24)),
      insetPadding: isNarrow
          ? const EdgeInsets.symmetric(horizontal: 12, vertical: 24)
          : const EdgeInsets.symmetric(horizontal: 40, vertical: 24),
      child: isNarrow ? _buildNarrowLayout(context) : _buildWideLayout(context),
    );
  }

  // ─── Wide layout (tablet/desktop) ──────────────────────────────────────────
  Widget _buildWideLayout(BuildContext context) {
    final change = _amountReceived - widget.totalAmount;
    final isCash = _paymentMethod == 'Cash';

    return SizedBox(
      width: 760,
      height: 580,
      child: Row(
        children: [
          // Left: Payment Methods
          Expanded(
            flex: 4,
            child: Container(
              padding: const EdgeInsets.all(28),
              decoration: const BoxDecoration(
                color: AppColors.surfaceVariant,
                borderRadius: BorderRadius.horizontal(left: Radius.circular(24)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Pilih Metode', style: Theme.of(context).textTheme.headlineMedium),
                  const SizedBox(height: 24),
                  _buildMethodBtn('Cash', LucideIcons.banknote),
                  const SizedBox(height: 12),
                  _buildMethodBtn('QRIS', LucideIcons.qrCode),
                  const SizedBox(height: 12),
                  _buildMethodBtn('Kartu Debit/Kredit', LucideIcons.creditCard),
                ],
              ),
            ),
          ),
          // Right: Details
          Expanded(
            flex: 6,
            child: Container(
              padding: const EdgeInsets.all(28),
              decoration: const BoxDecoration(
                color: AppColors.surface,
                borderRadius: BorderRadius.horizontal(right: Radius.circular(24)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text('Total Tagihan',
                          style: Theme.of(context).textTheme.titleLarge?.copyWith(color: AppColors.textSecondary)),
                      IconButton(
                          onPressed: () => Navigator.pop(context),
                          icon: const Icon(LucideIcons.x)),
                    ],
                  ),
                  const SizedBox(height: 4),
                  Text(
                    currencyFormatter.format(widget.totalAmount),
                    style: Theme.of(context).textTheme.displayMedium?.copyWith(
                          color: AppColors.primary,
                          fontWeight: FontWeight.bold,
                        ),
                  ),
                  const Divider(height: 40, color: AppColors.border),
                  if (isCash) ..._buildCashDetails(context, change)
                  else if (_paymentMethod == 'QRIS')
                    Expanded(child: _buildQrisDetails(context))
                  else
                    const Expanded(child: Center(child: Text('Metode pembayaran belum tersedia'))),
                  if (_paymentMethod != 'QRIS') ...[
                    const Spacer(),
                    _buildPayButton(context, change),
                  ],
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  // ─── Narrow layout (phone) ──────────────────────────────────────────────────
  Widget _buildNarrowLayout(BuildContext context) {
    final change = _amountReceived - widget.totalAmount;
    final isCash = _paymentMethod == 'Cash';
    final screenHeight = MediaQuery.of(context).size.height;

    return SizedBox(
      height: screenHeight * 0.88,
      child: Column(
        children: [
          // Header
          Container(
            padding: const EdgeInsets.fromLTRB(20, 20, 8, 16),
            decoration: const BoxDecoration(
              border: Border(bottom: BorderSide(color: AppColors.border)),
            ),
            child: Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Total Tagihan',
                          style: TextStyle(color: AppColors.textSecondary, fontSize: 12)),
                      Text(
                        currencyFormatter.format(widget.totalAmount),
                        style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                              color: AppColors.primary,
                              fontWeight: FontWeight.bold,
                            ),
                      ),
                    ],
                  ),
                ),
                IconButton(
                  onPressed: () => Navigator.pop(context),
                  icon: const Icon(LucideIcons.x),
                ),
              ],
            ),
          ),
          // Method selector chips
          Container(
            color: AppColors.surfaceVariant,
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
            child: Row(
              children: [
                _buildMethodChip('Cash', LucideIcons.banknote),
                const SizedBox(width: 8),
                _buildMethodChip('QRIS', LucideIcons.qrCode),
                const SizedBox(width: 8),
                _buildMethodChip('Kartu', LucideIcons.creditCard),
              ],
            ),
          ),
          // Details (scrollable)
          Expanded(
            child: isCash
                ? SingleChildScrollView(
                    padding: const EdgeInsets.all(20),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: _buildCashDetails(context, change),
                    ),
                  )
                : _paymentMethod == 'QRIS'
                    ? Padding(
                        padding: const EdgeInsets.all(16),
                        child: _buildQrisDetails(context),
                      )
                    : const Center(child: Text('Metode belum tersedia')),
          ),
          // Button
          if (_paymentMethod != 'QRIS')
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
              child: _buildPayButton(context, change),
            ),
        ],
      ),
    );
  }

  List<Widget> _buildCashDetails(BuildContext context, double change) {
    return [
      Text('Uang Diterima', style: Theme.of(context).textTheme.titleMedium),
      const SizedBox(height: 12),
      TextField(
        controller: _amountController,
        keyboardType: TextInputType.number,
        style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold),
        decoration: const InputDecoration(prefixText: 'Rp '),
        onChanged: (val) {
          setState(() {
            _amountReceived = double.tryParse(val) ?? 0.0;
            _cashError = null;
          });
        },
      ),
      const SizedBox(height: 12),
      Row(
        children: [
          _buildQuickCashBtn(widget.totalAmount),
          const SizedBox(width: 8),
          _buildQuickCashBtn(100000),
          const SizedBox(width: 8),
          _buildQuickCashBtn(50000),
        ],
      ),
      const SizedBox(height: 20),
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
      if (_cashError != null) ...[
        const SizedBox(height: 12),
        Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: AppColors.error.withOpacity(0.08),
            borderRadius: BorderRadius.circular(10),
            border: Border.all(color: AppColors.error.withOpacity(0.3)),
          ),
          child: Row(
            children: [
              const Icon(LucideIcons.alertCircle, color: AppColors.error, size: 16),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  _cashError!,
                  style: const TextStyle(color: AppColors.error, fontSize: 13),
                ),
              ),
            ],
          ),
        ),
      ],
    ];
  }

  Widget _buildQrisDetails(BuildContext context) {
    return Center(
      child: _isLoadingQris
          ? const CircularProgressIndicator()
          : _qrisError != null
              ? Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const Icon(LucideIcons.alertCircle, size: 48, color: AppColors.error),
                    const SizedBox(height: 16),
                    Text(_qrisError!,
                        style: Theme.of(context).textTheme.titleMedium,
                        textAlign: TextAlign.center),
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
                        Text('Pembayaran Berhasil',
                            style: Theme.of(context)
                                .textTheme
                                .titleLarge
                                ?.copyWith(color: AppColors.success)),
                      ],
                    )
                  : Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        if (_qrisUrl != null)
                          Container(
                            padding: const EdgeInsets.all(12),
                            decoration: BoxDecoration(
                              color: AppColors.surface,
                              borderRadius: BorderRadius.circular(16),
                              border: Border.all(color: AppColors.border),
                            ),
                            child: QrImageView(
                              data: _qrisUrl!,
                              version: QrVersions.auto,
                              size: 180,
                            ),
                          ),
                        const SizedBox(height: 16),
                        if (_qrisTimerSeconds > 0) ...[
                          Text('Selesaikan dalam',
                              style: Theme.of(context).textTheme.bodyLarge),
                          const SizedBox(height: 4),
                          Text(
                            '${(_qrisTimerSeconds ~/ 60).toString().padLeft(2, '0')}:${(_qrisTimerSeconds % 60).toString().padLeft(2, '0')}',
                            style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                                  color: AppColors.error,
                                  fontWeight: FontWeight.bold,
                                ),
                          ),
                        ] else ...[
                          const Text('Waktu habis', style: TextStyle(color: AppColors.error)),
                          const SizedBox(height: 16),
                          ElevatedButton(
                            onPressed: () => setState(() => _paymentMethod = 'Cash'),
                            child: const Text('Ganti ke Cash'),
                          ),
                        ],
                      ],
                    ),
    );
  }

  Widget _buildPayButton(BuildContext context, double change) {
    final isCash = _paymentMethod == 'Cash';
    final isDisabled = (isCash && change < 0) || _isLoadingQris;
    return SizedBox(
      width: double.infinity,
      height: 52,
      child: ElevatedButton(
        onPressed: isDisabled ? null : () async => _submitCashPayment(_amountReceived),
        style: ElevatedButton.styleFrom(
          backgroundColor: isDisabled ? AppColors.border : AppColors.primary,
        ),
        child: _isLoadingQris
            ? const SizedBox(
                height: 20,
                width: 20,
                child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
            : const Text('SELESAIKAN PEMBAYARAN',
                style: TextStyle(fontWeight: FontWeight.bold)),
      ),
    );
  }

  Widget _buildMethodBtn(String label, IconData icon) {
    final isSelected = _paymentMethod == label;
    return InkWell(
      onTap: () {
        setState(() {
          _paymentMethod = label;
          _cashError = null;
        });
        if (label == 'QRIS' && (_qrisUrl == null || _qrisError != null) && !_isLoadingQris) {
          _generateQris();
        }
      },
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: isSelected ? AppColors.primary.withOpacity(0.1) : AppColors.surface,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(
            color: isSelected ? AppColors.primary : AppColors.border,
            width: 2,
          ),
        ),
        child: Row(
          children: [
            Icon(icon, color: isSelected ? AppColors.primary : AppColors.textSecondary),
            const SizedBox(width: 12),
            Text(
              label,
              style: TextStyle(
                fontSize: 16,
                fontWeight: isSelected ? FontWeight.bold : FontWeight.w500,
                color: isSelected ? AppColors.primary : AppColors.textPrimary,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildMethodChip(String label, IconData icon) {
    final isSelected = _paymentMethod == label ||
        (label == 'Kartu' && _paymentMethod == 'Kartu Debit/Kredit');
    return Expanded(
      child: GestureDetector(
        onTap: () {
          final fullLabel = label == 'Kartu' ? 'Kartu Debit/Kredit' : label;
          setState(() {
            _paymentMethod = fullLabel;
            _cashError = null;
          });
          if (fullLabel == 'QRIS' && (_qrisUrl == null || _qrisError != null) && !_isLoadingQris) {
            _generateQris();
          }
        },
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 8),
          decoration: BoxDecoration(
            color: isSelected ? AppColors.primary : AppColors.surface,
            borderRadius: BorderRadius.circular(10),
            border: Border.all(color: isSelected ? AppColors.primary : AppColors.border),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(icon, size: 18,
                  color: isSelected ? Colors.white : AppColors.textSecondary),
              const SizedBox(height: 2),
              Text(
                label,
                style: TextStyle(
                  fontSize: 11,
                  fontWeight: FontWeight.w600,
                  color: isSelected ? Colors.white : AppColors.textSecondary,
                ),
              ),
            ],
          ),
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
            _cashError = null;
          });
        },
        style: OutlinedButton.styleFrom(
          padding: const EdgeInsets.symmetric(vertical: 10),
        ),
        child: Text(
          amount == widget.totalAmount ? 'Pas' : currencyFormatter.format(amount),
          style: const TextStyle(fontSize: 12),
          overflow: TextOverflow.ellipsis,
        ),
      ),
    );
  }
}
