import 'dart:async';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
import 'package:dio/dio.dart';
import 'package:qr_flutter/qr_flutter.dart';
import '../../../../core/config/app_config.dart';
import '../../../../core/theme/kasira_ds.dart';
import '../../../../core/services/session_cache.dart';

class PaymentModal extends StatefulWidget {
  final double totalAmount;
  // Cara A (optimistic): orderId di-resolve async — submitOrder jalan di
  // background pas modal dibuka. Modal await pas benar-benar butuh.
  final Future<String?> orderIdFuture;
  final String? Function()? orderErrorGetter;
  final void Function(String paymentMethod, double amountPaid, String orderId) onPaymentSuccess;

  const PaymentModal({
    super.key,
    required this.totalAmount,
    required this.orderIdFuture,
    required this.onPaymentSuccess,
    this.orderErrorGetter,
  });

  @override
  State<PaymentModal> createState() => _PaymentModalState();
}

class _PaymentModalState extends State<PaymentModal> {
  String _paymentMethod = 'Cash';
  double _amountReceived = 0.0;
  final _amountController = TextEditingController();
  final currencyFormatter = NumberFormat.currency(locale: 'id_ID', symbol: 'Rp ', decimalDigits: 0);

  // Cara A: orderId di-resolve dari future (submitOrder background).
  String? _orderId;
  String? _orderError;
  bool _orderResolved = false;

  /// Tunggu orderId siap (biasanya udah kelar duluan karena user butuh waktu
  /// milih metode + ketik uang). Return null kalau order gagal dibuat.
  Future<String?> _ensureOrderId() async {
    if (_orderId != null) return _orderId;
    if (_orderResolved) return null; // resolved tapi null = gagal
    try {
      final id = await widget.orderIdFuture;
      return id;
    } catch (_) {
      return null;
    }
  }

  // QRIS State
  bool _isLoadingQris = false;
  String? _qrisUrl;
  String? _qrisPaymentId;
  String? _qrisError;
  bool _isQrisPaid = false;
  int _qrisTimerSeconds = 15 * 60;
  Timer? _qrisTimer;
  Timer? _qrisPollingTimer;
  // Tracker untuk polling health — terakhir kali response dari backend
  // sukses diterima (response != null, terlepas status). Dipakai untuk
  // cancel polling + show retry dialog kalau >= 30s tanpa sukses.
  DateTime? _lastPollSuccessAt;
  bool _pollingErrorDialogShown = false;

  // Inline error untuk cash payment
  String? _cashError;

  Dio get _dio => Dio(BaseOptions(
    baseUrl: AppConfig.apiV1,
    connectTimeout: const Duration(seconds: 10),
    receiveTimeout: const Duration(seconds: 10),
  ));
  SessionCache get _cache => SessionCache.instance;

  Future<void> _submitCashPayment(double amountPaid, {String apiMethod = 'cash'}) async {
    setState(() {
      _isLoadingQris = true;
      _cashError = null;
    });
    // Cara A: pastiin order udah kebuat di server sebelum POST payment.
    final oid = await _ensureOrderId();
    if (oid == null) {
      if (mounted) {
        setState(() {
          _isLoadingQris = false;
          _cashError = _orderError ?? 'Pesanan gagal dibuat. Tutup & coba lagi.';
        });
      }
      return;
    }
    try {
      final outletId = _cache.outletId ?? '';
      final shiftId = _cache.shiftSessionId;
      // Non-cash (kartu) gak ada kembalian — amount_paid = tagihan.
      final isCashApi = apiMethod == 'cash';
      final paid = isCashApi ? amountPaid : widget.totalAmount;
      final change = paid - widget.totalAmount;

      await _dio.post(
        '/payments/',
        options: Options(headers: _cache.authHeaders),
        data: {
          'order_id': oid,
          'outlet_id': outletId,
          'payment_method': apiMethod,
          'amount_due': widget.totalAmount,
          'amount_paid': paid,
          'change_amount': change < 0 ? 0 : change,
          if (shiftId != null) 'shift_session_id': shiftId,
        },
      );

      if (mounted) {
        setState(() => _isLoadingQris = false);
        widget.onPaymentSuccess(_paymentMethod, amountPaid, oid);
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
    // Cara A: resolve orderId di background (submitOrder yg dikick dari cart).
    widget.orderIdFuture.then((id) {
      if (!mounted) return;
      setState(() {
        _orderResolved = true;
        _orderId = id;
        if (id == null) {
          _orderError = widget.orderErrorGetter?.call() ??
              'Gagal membuat pesanan. Tutup & coba lagi.';
        }
      });
    }).catchError((e) {
      if (!mounted) return;
      setState(() {
        _orderResolved = true;
        _orderError = 'Gagal membuat pesanan. Tutup & coba lagi.';
      });
    });
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
    // Reset health tracker tiap kali polling start (termasuk retry dari dialog).
    _lastPollSuccessAt = DateTime.now();
    _pollingErrorDialogShown = false;
    _qrisPollingTimer = Timer.periodic(const Duration(seconds: 3), (timer) async {
      if (_qrisPaymentId == null) return;
      try {
        final response = await _dio.get(
          '/payments/$_qrisPaymentId/status',
          options: Options(headers: _cache.authHeaders),
        );
        // Tandai polling sehat — response sampai (backend reachable),
        // terlepas status payment-nya pending/paid.
        _lastPollSuccessAt = DateTime.now();
        final data = response.data['data'];
        if (data != null && data['status'] == 'paid') {
          timer.cancel();
          _qrisTimer?.cancel();
          if (mounted) setState(() => _isQrisPaid = true);
          Future.delayed(const Duration(seconds: 2), () {
            if (mounted) {
              widget.onPaymentSuccess('QRIS', widget.totalAmount, _orderId ?? '');
              Navigator.pop(context);
            }
          });
        }
      } catch (_) {
        // Polling gagal (network/timeout/server error). Cek elapsed sejak
        // terakhir sukses — kalau >= 30s, stop polling + show retry dialog.
        // Tidak crash app: error tetap silent, user dapet feedback via UI.
        final lastSuccess = _lastPollSuccessAt;
        if (lastSuccess != null &&
            DateTime.now().difference(lastSuccess).inSeconds >= 30 &&
            !_pollingErrorDialogShown) {
          timer.cancel();
          _pollingErrorDialogShown = true;
          if (mounted) _showPollingErrorDialog();
        }
      }
    });
  }

  /// Dialog retry saat QRIS polling >= 30s tanpa response sukses.
  /// Tap "Coba Lagi" → restart polling dari awal (reset health tracker).
  /// Tap "Tutup" → polling tetap stop; user bisa cancel via tombol X di
  /// header modal atau biarkan QR timer 15-menit habis.
  void _showPollingErrorDialog() {
    if (!mounted) return;
    showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (dialogCtx) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: const Row(
          children: [
            Icon(LucideIcons.wifiOff, color: KasiraDS.danger, size: 22),
            SizedBox(width: 10),
            Expanded(child: Text('Koneksi Bermasalah', style: TextStyle(fontSize: 16))),
          ],
        ),
        content: const Text(
          'Status pembayaran QRIS tidak bisa diperiksa selama 30 detik. '
          'Mungkin koneksi internet bermasalah.\n\n'
          'Kalau customer sudah scan QR & bayar, tap "Coba Lagi" untuk '
          'cek ulang. Atau tutup dialog ini dan tap X di pojok atas '
          'modal kalau mau batalkan.',
          style: TextStyle(fontSize: 13, height: 1.4),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogCtx).pop(),
            child: const Text('Tutup', style: TextStyle(color: KasiraDS.textMuted)),
          ),
          ElevatedButton.icon(
            onPressed: () {
              Navigator.of(dialogCtx).pop();
              // Restart polling dari awal — reset _lastPollSuccessAt + flag.
              _startQrisPolling();
            },
            icon: const Icon(LucideIcons.refreshCw, size: 16),
            label: const Text('Coba Lagi'),
            style: ElevatedButton.styleFrom(
              backgroundColor: KasiraDS.brandPrimary,
              foregroundColor: Colors.white,
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _generateQris() async {
    setState(() {
      _isLoadingQris = true;
      _qrisError = null;
    });
    // Cara A: QRIS butuh order ADA di server (buat generate QR Xendit) — tunggu
    // order kelar dulu. Biasanya udah beres pas user tap QRIS.
    final oid = await _ensureOrderId();
    if (oid == null) {
      if (mounted) {
        setState(() {
          _isLoadingQris = false;
          _qrisError = _orderError ?? 'Pesanan gagal dibuat. Coba lagi.';
        });
      }
      return;
    }
    _orderId = oid; // pastiin ke-set buat polling success
    try {
      final outletId = _cache.outletId ?? '';
      final shiftId = _cache.shiftSessionId;

      final response = await _dio.post(
        '/payments/',
        options: Options(headers: _cache.authHeaders),
        data: {
          'order_id': oid,
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

    // Rule #43: payment immutable. Block device back button biar user gak
    // tidak sengaja batalin pembayaran yang sedang in-flight (cash typed,
    // QRIS polling, dll). Cancel resmi via tombol X di header atau ganti
    // metode pembayaran di chip.
    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, _) {
        if (didPop) return;
        // QRIS in-flight? Peringatkan user — jangan dismiss diam-diam.
        if (_isLoadingQris || (_qrisPaymentId != null && !_isQrisPaid)) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text(
                'Pembayaran sedang diproses. Tap tombol X di atas kalau mau batal.',
              ),
              backgroundColor: KasiraDS.danger,
              behavior: SnackBarBehavior.floating,
              duration: Duration(seconds: 3),
            ),
          );
        }
      },
      child: Dialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24)),
        insetPadding: isNarrow
            ? const EdgeInsets.symmetric(horizontal: 12, vertical: 24)
            : const EdgeInsets.symmetric(horizontal: 40, vertical: 24),
        child: isNarrow ? _buildNarrowLayout(context) : _buildWideLayout(context),
      ),
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
                color: KasiraDS.surfaceSunken,
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
                color: KasiraDS.surfaceCard,
                borderRadius: BorderRadius.horizontal(right: Radius.circular(24)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text('Total Tagihan',
                          style: Theme.of(context).textTheme.titleLarge?.copyWith(color: KasiraDS.textMuted)),
                      IconButton(
                          onPressed: () => Navigator.pop(context),
                          icon: const Icon(LucideIcons.x)),
                    ],
                  ),
                  const SizedBox(height: 4),
                  Text(
                    currencyFormatter.format(widget.totalAmount),
                    style: Theme.of(context).textTheme.displayMedium?.copyWith(
                          color: KasiraDS.brandPrimary,
                          fontWeight: FontWeight.bold,
                        ),
                  ),
                  const Divider(height: 40, color: KasiraDS.borderSubtle),
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

  // ─── Narrow layout (phone) — ports "Kasira POS.dc.html" CHECKOUT screen ──────
  Widget _buildNarrowLayout(BuildContext context) {
    final change = _amountReceived - widget.totalAmount;
    final isCash = _paymentMethod == 'Cash';
    final isKartu = _paymentMethod == 'Kartu Debit/Kredit';
    final screenHeight = MediaQuery.of(context).size.height;

    return SizedBox(
      height: screenHeight * 0.9,
      child: Column(
        children: [
          // Header: back + "Pembayaran"
          Padding(
            padding: const EdgeInsets.fromLTRB(12, 12, 12, 6),
            child: Row(
              children: [
                _circleBtn(LucideIcons.x, () => Navigator.pop(context)),
                const SizedBox(width: 12),
                Text('Pembayaran',
                    style: KasiraDS.display(size: 19, color: KasiraDS.textStrong)),
              ],
            ),
          ),
          Expanded(
            child: SingleChildScrollView(
              padding: const EdgeInsets.fromLTRB(20, 4, 20, 16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Total hero
                  Center(
                    child: Column(
                      children: [
                        const SizedBox(height: 8),
                        Text('// TOTAL TAGIHAN',
                            style: KasiraDS.eyebrow(color: KasiraDS.textMuted)),
                        const SizedBox(height: 6),
                        Text(currencyFormatter.format(widget.totalAmount),
                            style: KasiraDS.display(size: 38, color: KasiraDS.textStrong)),
                        const SizedBox(height: 18),
                      ],
                    ),
                  ),
                  Text('Metode pembayaran',
                      style: KasiraDS.sans(size: 12.5, weight: FontWeight.w700, color: KasiraDS.textBody)),
                  const SizedBox(height: 10),
                  // Method grid 2col
                  Row(children: [
                    Expanded(child: _methodTile('Cash', 'Tunai', LucideIcons.banknote)),
                    const SizedBox(width: 11),
                    Expanded(child: _methodTile('QRIS', 'QRIS', LucideIcons.qrCode)),
                  ]),
                  const SizedBox(height: 11),
                  Row(children: [
                    Expanded(child: _methodTile('Kartu Debit/Kredit', 'Kartu', LucideIcons.creditCard)),
                    const SizedBox(width: 11),
                    const Expanded(child: SizedBox()),
                  ]),
                  const SizedBox(height: 18),
                  if (isCash)
                    ..._buildCashDetails(context, change)
                  else if (_paymentMethod == 'QRIS')
                    _buildQrisDetails(context)
                  else if (isKartu)
                    _buildKartuInfo(),
                ],
              ),
            ),
          ),
          // Confirm button (QRIS auto-confirms via polling → hide)
          if (_paymentMethod != 'QRIS')
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 12, 20, 24),
              child: _buildPayButton(context, change),
            ),
        ],
      ),
    );
  }

  Widget _circleBtn(IconData icon, VoidCallback onTap) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(999),
      child: Container(
        width: 40,
        height: 40,
        alignment: Alignment.center,
        decoration: BoxDecoration(
          color: KasiraDS.surfaceCard,
          shape: BoxShape.circle,
          border: Border.all(color: KasiraDS.borderSubtle),
          boxShadow: KasiraDS.shadowSm,
        ),
        child: Icon(icon, size: 19, color: KasiraDS.textStrong),
      ),
    );
  }

  /// Method grid tile (design 591-596): icon tile + label, selected = brand border + tint + glow.
  Widget _methodTile(String value, String label, IconData icon) {
    final isSelected = _paymentMethod == value;
    return GestureDetector(
      onTap: () {
        setState(() {
          _paymentMethod = value;
          _cashError = null;
        });
        if (value == 'QRIS' && (_qrisUrl == null || _qrisError != null) && !_isLoadingQris) {
          _generateQris();
        }
      },
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 150),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 15),
        decoration: BoxDecoration(
          color: isSelected ? KasiraDS.brandTint : KasiraDS.surfaceCard,
          borderRadius: KasiraDS.brMd,
          border: Border.all(
            color: isSelected ? KasiraDS.brandPrimary : KasiraDS.borderSubtle,
            width: isSelected ? 2 : 1.5,
          ),
          boxShadow: isSelected ? KasiraDS.shadowSm : null,
        ),
        child: Row(
          children: [
            Container(
              width: 38,
              height: 38,
              alignment: Alignment.center,
              decoration: BoxDecoration(
                gradient: isSelected ? KasiraDS.gradientFrekuensi : null,
                color: isSelected ? null : KasiraDS.surfaceSunken,
                borderRadius: KasiraDS.brSm,
              ),
              child: Icon(icon, size: 19,
                  color: isSelected ? Colors.white : KasiraDS.textMuted),
            ),
            const SizedBox(width: 11),
            Flexible(
              child: Text(label,
                  overflow: TextOverflow.ellipsis,
                  style: KasiraDS.sans(
                      size: 14,
                      weight: FontWeight.w700,
                      color: isSelected ? KasiraDS.brandPrimary : KasiraDS.textStrong)),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildKartuInfo() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: KasiraDS.surfaceSunken,
        borderRadius: KasiraDS.brLg,
      ),
      child: Column(
        children: [
          const Icon(LucideIcons.creditCard, size: 30, color: KasiraDS.textMuted),
          const SizedBox(height: 10),
          Text('Gesek/tap di mesin EDC, lalu tekan Konfirmasi pembayaran.',
              textAlign: TextAlign.center,
              style: KasiraDS.sans(size: 13, color: KasiraDS.textMuted)),
        ],
      ),
    );
  }

  /// Denominasi cash: uang pas + pembulatan + pecahan umum di atas total.
  List<double> _cashOptions() {
    final total = widget.totalAmount;
    final opts = <double>{total};
    for (final n in [1000, 5000, 10000, 20000, 50000, 100000]) {
      final up = (total / n).ceil() * n.toDouble();
      if (up > total) opts.add(up);
    }
    for (final note in [20000.0, 50000.0, 100000.0]) {
      if (note > total) opts.add(note);
    }
    final list = opts.toList()..sort();
    return list.take(6).toList();
  }

  List<Widget> _buildCashDetails(BuildContext context, double change) {
    final hasCash = _amountReceived > 0;
    return [
      Text('Uang diterima',
          style: KasiraDS.sans(size: 12.5, weight: FontWeight.w700, color: KasiraDS.textBody)),
      const SizedBox(height: 11),
      Wrap(
        spacing: 9,
        runSpacing: 9,
        children: _cashOptions().map((a) => _cashChip(a)).toList(),
      ),
      const SizedBox(height: 12),
      TextField(
        controller: _amountController,
        keyboardType: TextInputType.number,
        style: KasiraDS.sans(size: 15, weight: FontWeight.w700, color: KasiraDS.textStrong),
        decoration: const InputDecoration(prefixText: 'Rp ', hintText: 'Nominal lain', isDense: true),
        onChanged: (val) {
          setState(() {
            _amountReceived = double.tryParse(val) ?? 0.0;
            _cashError = null;
          });
        },
      ),
      const SizedBox(height: 14),
      if (hasCash)
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
          decoration: BoxDecoration(
            color: KasiraDS.success.withOpacity(0.12),
            borderRadius: KasiraDS.brMd,
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text('Kembalian',
                  style: KasiraDS.sans(size: 14, weight: FontWeight.w700, color: KasiraDS.textStrong)),
              Text(currencyFormatter.format(change > 0 ? change : 0),
                  style: KasiraDS.display(size: 20, color: change >= 0 ? KasiraDS.success : KasiraDS.danger)),
            ],
          ),
        ),
      if (_cashError != null) ...[
        const SizedBox(height: 12),
        Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: KasiraDS.danger.withOpacity(0.08),
            borderRadius: KasiraDS.brSm,
            border: Border.all(color: KasiraDS.danger.withOpacity(0.3)),
          ),
          child: Row(
            children: [
              const Icon(LucideIcons.alertCircle, color: KasiraDS.danger, size: 16),
              const SizedBox(width: 8),
              Expanded(
                child: Text(_cashError!, style: KasiraDS.sans(size: 13, color: KasiraDS.danger)),
              ),
            ],
          ),
        ),
      ],
    ];
  }

  Widget _cashChip(double amount) {
    final isSelected = _amountReceived == amount;
    final isPas = amount == widget.totalAmount;
    return GestureDetector(
      onTap: () {
        setState(() {
          _amountReceived = amount;
          _amountController.text = amount.toInt().toString();
          _cashError = null;
        });
      },
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 11),
        decoration: BoxDecoration(
          gradient: isSelected ? KasiraDS.gradientFrekuensi : null,
          color: isSelected ? null : KasiraDS.surfaceCard,
          borderRadius: KasiraDS.brMd,
          border: Border.all(
            color: isSelected ? Colors.transparent : KasiraDS.borderDefault,
            width: 1.5,
          ),
        ),
        child: Text(
          isPas ? 'Uang pas' : currencyFormatter.format(amount),
          style: KasiraDS.sans(
              size: 13.5,
              weight: FontWeight.w800,
              color: isSelected ? Colors.white : KasiraDS.textStrong),
        ),
      ),
    );
  }

  Widget _buildQrisDetails(BuildContext context) {
    return Center(
      child: _isLoadingQris
          ? const CircularProgressIndicator()
          : _qrisError != null
              ? Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const Icon(LucideIcons.alertCircle, size: 48, color: KasiraDS.danger),
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
                        const Icon(LucideIcons.checkCircle2, size: 64, color: KasiraDS.success),
                        const SizedBox(height: 16),
                        Text('Pembayaran Berhasil',
                            style: Theme.of(context)
                                .textTheme
                                .titleLarge
                                ?.copyWith(color: KasiraDS.success)),
                      ],
                    )
                  : Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        if (_qrisUrl != null)
                          Container(
                            padding: const EdgeInsets.all(12),
                            decoration: BoxDecoration(
                              color: KasiraDS.surfaceCard,
                              borderRadius: BorderRadius.circular(16),
                              border: Border.all(color: KasiraDS.borderSubtle),
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
                                  color: KasiraDS.danger,
                                  fontWeight: FontWeight.bold,
                                ),
                          ),
                        ] else ...[
                          const Text('Waktu habis', style: TextStyle(color: KasiraDS.danger)),
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
    final isKartu = _paymentMethod == 'Kartu Debit/Kredit';
    final isDisabled = (isCash && change < 0) || _isLoadingQris;
    void submit() {
      if (isKartu) {
        _submitCashPayment(widget.totalAmount, apiMethod: 'card');
      } else {
        _submitCashPayment(_amountReceived);
      }
    }

    return SizedBox(
      width: double.infinity,
      height: 54,
      child: DecoratedBox(
        decoration: BoxDecoration(
          gradient: isDisabled ? null : KasiraDS.gradientFrekuensi,
          color: isDisabled ? KasiraDS.surfaceSunken : null,
          borderRadius: KasiraDS.brMd,
          boxShadow: isDisabled ? null : KasiraDS.glowBrand,
        ),
        child: Material(
          color: Colors.transparent,
          child: InkWell(
            onTap: isDisabled ? null : submit,
            borderRadius: KasiraDS.brMd,
            child: Center(
              child: _isLoadingQris
                  ? const SizedBox(
                      height: 20,
                      width: 20,
                      child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                  : Text('Konfirmasi pembayaran',
                      style: KasiraDS.sans(
                          size: 15,
                          weight: FontWeight.w800,
                          color: isDisabled ? KasiraDS.textMuted : Colors.white)),
            ),
          ),
        ),
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
          color: isSelected ? KasiraDS.brandPrimary.withOpacity(0.1) : KasiraDS.surfaceCard,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(
            color: isSelected ? KasiraDS.brandPrimary : KasiraDS.borderSubtle,
            width: 2,
          ),
        ),
        child: Row(
          children: [
            Icon(icon, color: isSelected ? KasiraDS.brandPrimary : KasiraDS.textMuted),
            const SizedBox(width: 12),
            Text(
              label,
              style: TextStyle(
                fontSize: 16,
                fontWeight: isSelected ? FontWeight.bold : FontWeight.w500,
                color: isSelected ? KasiraDS.brandPrimary : KasiraDS.textStrong,
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
            color: isSelected ? KasiraDS.brandPrimary : KasiraDS.surfaceCard,
            borderRadius: BorderRadius.circular(10),
            border: Border.all(color: isSelected ? KasiraDS.brandPrimary : KasiraDS.borderSubtle),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(icon, size: 18,
                  color: isSelected ? Colors.white : KasiraDS.textMuted),
              const SizedBox(height: 2),
              Text(
                label,
                style: TextStyle(
                  fontSize: 11,
                  fontWeight: FontWeight.w600,
                  color: isSelected ? Colors.white : KasiraDS.textMuted,
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
