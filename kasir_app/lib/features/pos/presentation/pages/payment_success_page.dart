import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:lucide_icons/lucide_icons.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../../../../core/services/session_cache.dart';
import '../../../../core/theme/app_colors.dart';
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
            backgroundColor: AppColors.error,
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
          AppColors.success,
          2,
        ),
      PrintOutcome.busy => (
          'Printer masih sibuk, tunggu sebentar lalu coba lagi.',
          AppColors.error,
          3,
        ),
      PrintOutcome.notConnected => (
          'Printer belum terhubung. Hubungkan di Pengaturan > Printer.',
          AppColors.error,
          5,
        ),
      PrintOutcome.failed => (
          isAutoPrint
              ? 'Auto-print gagal. Tap "CETAK STRUK" untuk coba ulang.'
              : 'Gagal mencetak, coba lagi',
          AppColors.error,
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
      backgroundColor: AppColors.surfaceVariant,
      body: Center(
        child: FadeTransition(
          opacity: _fadeAnim,
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(vertical: 24),
            child: Container(
              width: 480,
              padding: const EdgeInsets.all(40),
              decoration: BoxDecoration(
                color: AppColors.surface,
                borderRadius: BorderRadius.circular(28),
                boxShadow: [
                  BoxShadow(
                    color: AppColors.success.withOpacity(0.15),
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
                      decoration: const BoxDecoration(
                        color: AppColors.success,
                        shape: BoxShape.circle,
                      ),
                      child: const Icon(LucideIcons.check, color: Colors.white, size: 48),
                    ),
                  ),
                  const SizedBox(height: 24),
                  Text(
                    'Pembayaran Berhasil!',
                    style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                          fontWeight: FontWeight.bold,
                          color: AppColors.success,
                        ),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    'Order #${widget.displayNumber}',
                    style: const TextStyle(color: AppColors.textSecondary, fontSize: 15),
                  ),
                  const SizedBox(height: 24),

                  // Payment details card
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(20),
                    decoration: BoxDecoration(
                      color: AppColors.surfaceVariant,
                      borderRadius: BorderRadius.circular(16),
                    ),
                    child: Column(
                      children: [
                        _buildRow('Total Tagihan', _currency.format(widget.totalAmount),
                            isBold: true, valueColor: AppColors.textPrimary),
                        const SizedBox(height: 10),
                        _buildRow(
                          'Metode Pembayaran',
                          widget.paymentMethod,
                          valueColor: AppColors.primary,
                        ),
                        if (widget.paymentMethod == 'Cash') ...[
                          const SizedBox(height: 10),
                          _buildRow('Uang Diterima', _currency.format(widget.amountPaid)),
                          const Divider(height: 20, color: AppColors.border),
                          _buildRow(
                            'Kembalian',
                            _currency.format(_change > 0 ? _change : 0),
                            isBold: true,
                            valueColor: AppColors.success,
                          ),
                        ],
                      ],
                    ),
                  ),
                  const SizedBox(height: 24),

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
                        backgroundColor: AppColors.primary,
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
            color: AppColors.textSecondary,
            fontWeight: isBold ? FontWeight.bold : FontWeight.normal,
          ),
        ),
        Text(
          value,
          style: TextStyle(
            color: valueColor ?? AppColors.textPrimary,
            fontWeight: isBold ? FontWeight.bold : FontWeight.w600,
            fontSize: isBold ? 18 : 14,
          ),
        ),
      ],
    );
  }
}
