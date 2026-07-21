import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
import 'package:go_router/go_router.dart';
import 'package:dio/dio.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../../../../core/config/app_config.dart';
import '../../../../core/services/session_cache.dart';
import '../../../../core/theme/kasira_ds.dart';
import '../../../../core/services/printer_service.dart';
import '../../providers/tax_config_provider.dart';
import '../../utils/post_payment_refresh.dart';
import 'receipt_preview_page.dart';

class PaymentSuccessPage extends ConsumerStatefulWidget {
  final double totalAmount;
  final double amountPaid;
  final String paymentMethod;
  final String orderId;
  final String displayNumber;
  final List<ReceiptItem> items;
  final double? tax;
  final double? serviceCharge;
  final double? discount;
  final bool taxInclusive;
  final String? customerId;
  final String? customerName;

  const PaymentSuccessPage({
    super.key,
    required this.totalAmount,
    required this.amountPaid,
    required this.paymentMethod,
    required this.orderId,
    required this.displayNumber,
    this.items = const [],
    this.tax,
    this.serviceCharge,
    this.discount,
    this.taxInclusive = false,
    this.customerId,
    this.customerName,
  });

  @override
  ConsumerState<PaymentSuccessPage> createState() => _PaymentSuccessPageState();
}

class _PaymentSuccessPageState extends ConsumerState<PaymentSuccessPage>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _scaleAnim;
  late Animation<double> _fadeAnim;

  final _currency = NumberFormat.currency(locale: 'id_ID', symbol: 'Rp ', decimalDigits: 0);

  String _outletName = 'Kasira Outlet';
  String _outletAddress = '';
  bool _autoPrintAttempted = false;

  // Tangkap nomor pelanggan di sini, bukan di keranjang. Di keranjang tombolnya
  // ketulis "(opsional)" dan alurnya 6 langkah — kasir nggak akan pakai pas
  // rame, dan buktinya cuma 0,4% transaksi yang nyambung ke pelanggan.
  // Di layar ini kasir udah selesai, orangnya masih di depan, dan alasannya
  // jelas buat customer: "struknya dikirim ke WA ya".
  final _waPhoneController = TextEditingController();
  bool _waSending = false;
  bool _waSent = false;
  /// Izin kirim promo. Default MATI — kasir harus nanya dulu ke customer.
  /// Izin nggak boleh disimpulkan dari "dia mau dikirimi struk": struk itu
  /// bukti transaksi, promo itu iklan. Dan izin nggak bisa dikumpulin surut —
  /// nomor yang masuk tanpa centang ini selamanya nggak boleh dikirimi promo.
  bool _waConsent = false;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 500),
    );
    _scaleAnim = Tween<double>(begin: 0.5, end: 1.0).animate(
      CurvedAnimation(parent: _controller, curve: Curves.elasticOut),
    );
    _fadeAnim = CurvedAnimation(parent: _controller, curve: Curves.easeIn);
    _controller.forward();
    _loadOutletInfoAndMaybeAutoPrint();
  }

  Future<void> _loadOutletInfoAndMaybeAutoPrint() async {
    // Fallback chain: SessionCache (in-memory) → SharedPreferences → 'Kasira Outlet'
    final cache = SessionCache.instance;
    final prefs = await SharedPreferences.getInstance();
    if (!mounted) return;
    setState(() {
      _outletName = cache.outletName
          ?? prefs.getString('c_outlet_name')
          ?? 'Kasira Outlet';
      _outletAddress = cache.outletAddress
          ?? prefs.getString('c_outlet_address')
          ?? '';
    });

    // Kalau outlet name masih default → trigger fetch background biar
    // transaksi berikutnya (atau reprint) pake nama outlet yang bener.
    if (cache.outletName == null || cache.outletName!.isEmpty) {
      cache.fetchAndCacheOutletInfo();
    }

    // Auto-print setelah animasi selesai, kalau printer connected
    await Future.delayed(const Duration(milliseconds: 600));
    if (!mounted || _autoPrintAttempted) return;
    _autoPrintAttempted = true;

    final printerState = ref.read(printerProvider);
    if (printerState.isConnected) {
      // Auto-print: SELALU show snackbar hasil (sukses/gagal) biar user gak
      // mikir struk kecetak padahal gagal. Prefix "(otomatis)" di success message.
      _printReceipt(isAutoPrint: true);
    }
  }

  @override
  void dispose() {
    _waPhoneController.dispose();
    _controller.dispose();
    super.dispose();
  }

  double get _change => widget.amountPaid - widget.totalAmount;

  Future<void> _printReceipt({bool isAutoPrint = false}) async {
    final notifier = ref.read(printerProvider.notifier);
    final state = ref.read(printerProvider);

    if (!state.isConnected) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(isAutoPrint
                ? 'Auto-print batal: printer belum terhubung. Hubungkan di Pengaturan > Printer.'
                : 'Printer belum terhubung. Hubungkan di Pengaturan > Printer.'),
            backgroundColor: KasiraDS.danger,
            behavior: SnackBarBehavior.floating,
            duration: const Duration(seconds: 4),
          ),
        );
      }
      return;
    }

    final taxConfig = ref.read(taxConfigProvider).valueOrNull;
    final prefs = await SharedPreferences.getInstance();
    final now = DateTime.now();
    final dateFormat = DateFormat('dd/MM/yy HH:mm', 'id_ID');
    final subtotal = widget.items.fold(0.0, (s, i) => s + i.subtotal);

    final data = ReceiptData(
      outletName: _outletName,
      outletAddress: _outletAddress,
      orderNumber: widget.displayNumber,
      dateTime: dateFormat.format(now),
      items: widget.items
          .map((i) => ReceiptLineItem(
                name: i.name,
                qty: i.qty,
                price: i.price,
                notes: i.notes,
              ))
          .toList(),
      subtotal: subtotal,
      tax: widget.tax,
      serviceCharge: widget.serviceCharge,
      total: widget.totalAmount,
      paymentMethod: widget.paymentMethod,
      amountPaid: widget.amountPaid,
      changeAmount: widget.amountPaid - widget.totalAmount,
      taxNumber: taxConfig?.taxNumber ?? prefs.getString('c_outlet_tax_number'),
      customFooter: taxConfig?.receiptFooter ?? prefs.getString('c_outlet_custom_footer'),
    );

    final bytes = buildReceipt(data);
    final outcome = await notifier.printBytesWithOutcome(bytes);

    if (!mounted) return;
    final (msg, color, seconds) = switch (outcome) {
      PrintOutcome.success => (
          isAutoPrint ? 'Struk otomatis dicetak' : 'Struk dikirim ke printer',
          KasiraDS.success,
          2,
        ),
      PrintOutcome.busy => (
          'Printer masih sibuk, tunggu sebentar lalu coba lagi.',
          KasiraDS.danger,
          3,
        ),
      PrintOutcome.notConnected => (
          'Printer belum terhubung. Hubungkan di Pengaturan > Printer.',
          KasiraDS.danger,
          5,
        ),
      PrintOutcome.failed => (
          isAutoPrint
              ? 'Auto-print gagal. Tap "CETAK STRUK" untuk coba ulang.'
              : 'Gagal mencetak, coba lagi',
          KasiraDS.danger,
          5,
        ),
    };
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(msg),
        backgroundColor: color,
        behavior: SnackBarBehavior.floating,
        duration: Duration(seconds: seconds),
      ),
    );
  }

  void _snack(String msg, Color color) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(msg),
        backgroundColor: color,
        behavior: SnackBarBehavior.floating,
        duration: const Duration(seconds: 3),
      ),
    );
  }

  /// Kirim struk + otomatis simpan pelanggan + sambungkan ke order.
  /// Endpoint /payments/send-receipt udah ngerjain ketiganya sekaligus.
  Future<void> _quickSendWa() async {
    final raw = _waPhoneController.text.trim();
    if (raw.length < 8 || _waSending) return;
    setState(() => _waSending = true);
    try {
      final cache = SessionCache.instance;
      final dio = Dio(BaseOptions(
        baseUrl: AppConfig.apiV1,
        connectTimeout: const Duration(seconds: 12),
        receiveTimeout: const Duration(seconds: 12),
      ));
      final res = await dio.post(
        '/payments/send-receipt',
        options: Options(headers: cache.authHeaders),
        data: {
          'order_id': widget.orderId,
          'phone': raw,
          'marketing_consent': _waConsent,
        },
      );
      final sent = res.data['data']?['sent'] == true;
      if (!mounted) return;
      setState(() {
        _waSending = false;
        _waSent = sent;
      });
      _snack(
        sent ? 'Struk dikirim & pelanggan tersimpan' : 'Nomor tersimpan, struk gagal terkirim',
        sent ? KasiraDS.success : KasiraDS.warning,
      );
    } catch (_) {
      if (!mounted) return;
      setState(() => _waSending = false);
      // Gagal kirim struk nggak boleh kelihatan kayak transaksinya bermasalah —
      // uangnya udah masuk, ini cuma layanan tambahan.
      _snack('Gagal kirim struk. Transaksi tetap aman.', KasiraDS.warning);
    }
  }

  void _sendWa() {
    showDialog(
      context: context,
      builder: (_) => SendReceiptWaDialog(
        orderId: widget.orderId,
        customerId: widget.customerId,
        customerName: widget.customerName,
      ),
    );
  }

  void _viewReceipt() {
    context.push('/receipt', extra: {
      'orderId': widget.orderId,
      'displayNumber': widget.displayNumber,
      'totalAmount': widget.totalAmount,
      'amountPaid': widget.amountPaid,
      'changeAmount': widget.amountPaid - widget.totalAmount,
      'paymentMethod': widget.paymentMethod,
      'items': widget.items,
      'tax': widget.tax,
      'serviceCharge': widget.serviceCharge,
      'discount': widget.discount,
      'taxInclusive': widget.taxInclusive,
      'outletName': _outletName,
      'outletAddress': _outletAddress,
      'customerId': widget.customerId,
      'customerName': widget.customerName,
    });
  }

  void _newTransaction() {
    // P3 Quick Win #1: defer cascade ke microtask via shared helper
    schedulePostPaymentRefresh(ref);
    context.go('/dashboard');
  }

  @override
  Widget build(BuildContext context) {
    final printerState = ref.watch(printerProvider);

    return Scaffold(
      backgroundColor: KasiraDS.surfaceSunken,
      body: Center(
        child: FadeTransition(
          opacity: _fadeAnim,
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(vertical: 24),
            child: Container(
              width: 480,
              padding: const EdgeInsets.all(40),
              decoration: BoxDecoration(
                color: KasiraDS.surfaceCard,
                borderRadius: BorderRadius.circular(28),
                boxShadow: [
                  BoxShadow(
                    color: KasiraDS.success.withOpacity(0.15),
                    blurRadius: 40,
                    offset: const Offset(0, 10),
                  ),
                ],
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  // Success icon
                  ScaleTransition(
                    scale: _scaleAnim,
                    child: Container(
                      width: 96,
                      height: 96,
                      decoration: BoxDecoration(
                        gradient: KasiraDS.gradientFrekuensi,
                        shape: BoxShape.circle,
                        boxShadow: KasiraDS.glowBrand,
                      ),
                      child: const Icon(LucideIcons.check, color: Colors.white, size: 48),
                    ),
                  ),
                  const SizedBox(height: 24),
                  Text(
                    'Pembayaran Berhasil!',
                    style: KasiraDS.display(size: 26, color: KasiraDS.textStrong),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    'Order #${widget.displayNumber}',
                    style: const TextStyle(color: KasiraDS.textMuted, fontSize: 15),
                  ),
                  const SizedBox(height: 24),

                  // Payment details card
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(20),
                    decoration: BoxDecoration(
                      color: KasiraDS.surfaceSunken,
                      borderRadius: BorderRadius.circular(16),
                    ),
                    child: Column(
                      children: [
                        _buildRow('Total Tagihan', _currency.format(widget.totalAmount),
                            isBold: true, valueColor: KasiraDS.textStrong),
                        const SizedBox(height: 10),
                        _buildRow(
                          'Metode Pembayaran',
                          widget.paymentMethod,
                          valueColor: KasiraDS.brandPrimary,
                        ),
                        if (widget.paymentMethod == 'Cash') ...[
                          const SizedBox(height: 10),
                          _buildRow('Uang Diterima', _currency.format(widget.amountPaid)),
                          const Divider(height: 20, color: KasiraDS.borderSubtle),
                          _buildRow(
                            'Kembalian',
                            _currency.format(_change > 0 ? _change : 0),
                            isBold: true,
                            valueColor: KasiraDS.success,
                          ),
                        ],
                      ],
                    ),
                  ),
                  const SizedBox(height: 20),

                  // TANGKAP NOMOR PELANGGAN — inline, bukan popup.
                  // Cuma muncul kalau transaksinya belum kepaut pelanggan.
                  // Boleh dilewat: kasir tinggal lanjut ke tombol di bawah.
                  if (widget.customerId == null && !_waSent)
                    Container(
                      margin: const EdgeInsets.only(bottom: 16),
                      padding: const EdgeInsets.all(14),
                      decoration: BoxDecoration(
                        color: KasiraDS.surfaceSunken,
                        borderRadius: KasiraDS.brMd,
                        border: Border.all(color: KasiraDS.borderSubtle),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('Kirim struk ke WhatsApp customer?',
                              style: KasiraDS.sans(
                                  size: 13.5,
                                  weight: FontWeight.w700,
                                  color: KasiraDS.textStrong)),
                          const SizedBox(height: 2),
                          Text('Nomornya tersimpan jadi data pelanggan. Boleh dilewat.',
                              style: KasiraDS.sans(size: 11.5, color: KasiraDS.textMuted)),
                          const SizedBox(height: 10),
                          Row(
                            children: [
                              Expanded(
                                child: TextField(
                                  controller: _waPhoneController,
                                  keyboardType: TextInputType.phone,
                                  onChanged: (_) => setState(() {}),
                                  decoration: InputDecoration(
                                    hintText: '08xxxxxxxxxx',
                                    isDense: true,
                                    filled: true,
                                    fillColor: KasiraDS.surfaceCard,
                                    contentPadding: const EdgeInsets.symmetric(
                                        horizontal: 12, vertical: 12),
                                    border: OutlineInputBorder(
                                      borderRadius: KasiraDS.brSm,
                                      borderSide: const BorderSide(
                                          color: KasiraDS.borderSubtle),
                                    ),
                                  ),
                                ),
                              ),
                              const SizedBox(width: 8),
                              SizedBox(
                                height: 44,
                                child: FilledButton(
                                  onPressed: (_waPhoneController.text.trim().length >= 8 &&
                                          !_waSending)
                                      ? _quickSendWa
                                      : null,
                                  style: FilledButton.styleFrom(
                                    backgroundColor: const Color(0xFF25D366),
                                    padding: const EdgeInsets.symmetric(horizontal: 16),
                                  ),
                                  child: _waSending
                                      ? const SizedBox(
                                          width: 16,
                                          height: 16,
                                          child: CircularProgressIndicator(
                                              strokeWidth: 2, color: Colors.white))
                                      : const Text('Kirim'),
                                ),
                              ),
                            ],
                          ),
                          InkWell(
                            onTap: () => setState(() => _waConsent = !_waConsent),
                            child: Padding(
                              padding: const EdgeInsets.only(top: 4),
                              child: Row(
                                children: [
                                  SizedBox(
                                    width: 34,
                                    height: 34,
                                    child: Checkbox(
                                      value: _waConsent,
                                      onChanged: (v) =>
                                          setState(() => _waConsent = v ?? false),
                                      activeColor: KasiraDS.brandPrimary,
                                    ),
                                  ),
                                  Expanded(
                                    child: Text(
                                      'Customer setuju dikirimi info promo',
                                      style: KasiraDS.sans(
                                          size: 12, color: KasiraDS.textMuted),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),

                  // PRIMARY ACTION — Cetak Struk
                  SizedBox(
                    width: double.infinity,
                    height: 56,
                    child: ElevatedButton.icon(
                      onPressed: () => _printReceipt(),
                      icon: const Icon(LucideIcons.printer, size: 20),
                      label: Text(
                        printerState.isConnected ? 'CETAK STRUK' : 'CETAK STRUK (Printer Offline)',
                        style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15),
                      ),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: KasiraDS.brandPrimary,
                        foregroundColor: Colors.white,
                        elevation: 2,
                      ),
                    ),
                  ),
                  const SizedBox(height: 10),

                  // SECONDARY ACTIONS — WA + Preview
                  Row(
                    children: [
                      Expanded(
                        child: OutlinedButton.icon(
                          onPressed: _sendWa,
                          icon: const Icon(LucideIcons.messageCircle, size: 18, color: Color(0xFF25D366)),
                          label: const Text('Kirim WA'),
                          style: OutlinedButton.styleFrom(
                            padding: const EdgeInsets.symmetric(vertical: 14),
                            side: const BorderSide(color: Color(0xFF25D366)),
                            foregroundColor: const Color(0xFF25D366),
                          ),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: OutlinedButton.icon(
                          onPressed: _viewReceipt,
                          icon: const Icon(LucideIcons.receipt, size: 18),
                          label: const Text('Lihat Struk'),
                          style: OutlinedButton.styleFrom(
                            padding: const EdgeInsets.symmetric(vertical: 14),
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),

                  // TERTIARY — Transaksi Baru
                  TextButton.icon(
                    onPressed: _newTransaction,
                    icon: const Icon(LucideIcons.arrowRight, size: 16),
                    label: const Text('Selesai — Transaksi Baru'),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildRow(String label, String value,
      {bool isBold = false, Color? valueColor}) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(
          label,
          style: TextStyle(
            color: KasiraDS.textMuted,
            fontWeight: isBold ? FontWeight.bold : FontWeight.normal,
          ),
        ),
        Text(
          value,
          style: TextStyle(
            color: valueColor ?? KasiraDS.textStrong,
            fontWeight: isBold ? FontWeight.bold : FontWeight.w600,
            fontSize: isBold ? 18 : 14,
          ),
        ),
      ],
    );
  }
}
