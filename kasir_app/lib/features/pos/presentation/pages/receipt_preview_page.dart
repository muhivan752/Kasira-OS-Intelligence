import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter/services.dart';
import 'package:intl/intl.dart';
import 'package:lucide_icons/lucide_icons.dart';
import 'package:go_router/go_router.dart';
import 'package:dio/dio.dart';
import '../../../../core/config/app_config.dart';
import '../../../../core/services/session_cache.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/services/printer_service.dart';
import '../../../../core/utils/phone_normalize.dart';
import '../../providers/tax_config_provider.dart';

class ReceiptItem {
  final String name;
  final int qty;
  final double price;
  final String? notes;

  const ReceiptItem({
    required this.name,
    required this.qty,
    required this.price,
    this.notes,
  });

  double get subtotal => qty * price;
}

class ReceiptPreviewPage extends ConsumerWidget {
  final String orderId;
  final String displayNumber;
  final double totalAmount;
  final double amountPaid;
  final double changeAmount;
  final String paymentMethod;
  final List<ReceiptItem> items;
  final String outletName;
  final String outletAddress;
  final double? tax;
  final double? serviceCharge;
  final double? discount;
  final bool taxInclusive;
  final String? customerId;
  final String? customerName;

  const ReceiptPreviewPage({
    super.key,
    required this.orderId,
    required this.displayNumber,
    required this.totalAmount,
    required this.amountPaid,
    required this.changeAmount,
    required this.paymentMethod,
    required this.items,
    this.outletName = 'Kasira Outlet',
    this.outletAddress = 'Jl. Sudirman No.1, Jakarta',
    this.tax,
    this.serviceCharge,
    this.discount,
    this.taxInclusive = false,
    this.customerId,
    this.customerName,
  });

  // Demo constructor for preview
  factory ReceiptPreviewPage.demo() {
    return ReceiptPreviewPage(
      orderId: 'uuid-demo',
      displayNumber: '20260402-0042',
      totalAmount: 75000,
      amountPaid: 100000,
      changeAmount: 25000,
      paymentMethod: 'Cash',
      outletName: 'Kasira Coffee',
      outletAddress: 'Jl. Sudirman No. 88, Jakarta',
      tax: 7500,
      serviceCharge: 3750,
      items: const [
        ReceiptItem(name: 'Kopi Susu Gula Aren', qty: 2, price: 25000),
        ReceiptItem(name: 'Matcha Latte', qty: 1, price: 28000, notes: 'Less sugar'),
        ReceiptItem(name: 'Croissant', qty: 1, price: 18000),
      ],
    );
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final printerState = ref.watch(printerProvider);
    final taxConfig = ref.watch(taxConfigProvider).valueOrNull;
    final taxNumber = taxConfig?.taxNumber;
    final customFooter = taxConfig?.receiptFooter;
    final currency = NumberFormat.currency(locale: 'id_ID', symbol: 'Rp ', decimalDigits: 0);
    final dateFormat = DateFormat('dd MMM yyyy, HH:mm', 'id_ID');
    final now = DateTime.now();
    final subtotal = items.fold(0.0, (sum, item) => sum + item.subtotal);

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: AppColors.surface,
        title: const Text('Preview Struk', style: TextStyle(color: AppColors.textPrimary)),
        iconTheme: const IconThemeData(color: AppColors.textPrimary),
        elevation: 0,
        actions: [
          IconButton(
            onPressed: () => _printReceipt(context, ref, now),
            icon: Icon(
              LucideIcons.printer,
              color: printerState.isConnected ? AppColors.primary : AppColors.textSecondary,
            ),
            tooltip: printerState.isConnected ? 'Cetak' : 'Printer belum terhubung',
          ),
          IconButton(
            onPressed: () => _shareViaWa(context),
            icon: const Icon(LucideIcons.messageCircle, color: AppColors.primary),
            tooltip: 'Kirim WA',
          ),
          const SizedBox(width: 8),
        ],
      ),
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Column(
            children: [
              // Receipt card
              Container(
                width: 380,
                decoration: BoxDecoration(
                  color: AppColors.surface,
                  borderRadius: BorderRadius.circular(8),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withOpacity(0.08),
                      blurRadius: 20,
                      offset: const Offset(0, 4),
                    ),
                  ],
                ),
                child: Column(
                  children: [
                    // Header
                    Container(
                      width: double.infinity,
                      padding: const EdgeInsets.all(24),
                      decoration: const BoxDecoration(
                        color: AppColors.primary,
                        borderRadius: BorderRadius.vertical(top: Radius.circular(8)),
                      ),
                      child: Column(
                        children: [
                          const Icon(Icons.point_of_sale_rounded, color: Colors.white, size: 32),
                          const SizedBox(height: 8),
                          Text(
                            outletName,
                            style: const TextStyle(
                              color: Colors.white,
                              fontSize: 20,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            outletAddress,
                            style: TextStyle(color: Colors.white.withOpacity(0.8), fontSize: 12),
                            textAlign: TextAlign.center,
                          ),
                          if (taxNumber != null && taxNumber.isNotEmpty) ...[
                            const SizedBox(height: 2),
                            Text(
                              'NPWP: $taxNumber',
                              style: TextStyle(color: Colors.white.withOpacity(0.75), fontSize: 11),
                              textAlign: TextAlign.center,
                            ),
                          ],
                        ],
                      ),
                    ),

                    Padding(
                      padding: const EdgeInsets.all(20),
                      child: Column(
                        children: [
                          // Order info
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              const Text('No. Order', style: TextStyle(color: AppColors.textSecondary, fontSize: 12)),
                              Text('#$displayNumber', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                            ],
                          ),
                          const SizedBox(height: 4),
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              const Text('Tanggal', style: TextStyle(color: AppColors.textSecondary, fontSize: 12)),
                              Text(dateFormat.format(now), style: const TextStyle(fontSize: 12)),
                            ],
                          ),

                          const Padding(
                            padding: EdgeInsets.symmetric(vertical: 16),
                            child: _DashedDivider(),
                          ),

                          // Items
                          ...items.map((item) => Padding(
                                padding: const EdgeInsets.only(bottom: 10),
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Row(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        Expanded(
                                          child: Text(
                                            item.name,
                                            style: const TextStyle(fontWeight: FontWeight.w500),
                                          ),
                                        ),
                                        Text(
                                          currency.format(item.subtotal),
                                          style: const TextStyle(fontWeight: FontWeight.w600),
                                        ),
                                      ],
                                    ),
                                    Row(
                                      children: [
                                        Text(
                                          '${item.qty} x ${currency.format(item.price)}',
                                          style: const TextStyle(color: AppColors.textSecondary, fontSize: 12),
                                        ),
                                      ],
                                    ),
                                    if (item.notes != null)
                                      Text(
                                        '* ${item.notes}',
                                        style: const TextStyle(
                                          color: AppColors.textTertiary,
                                          fontSize: 11,
                                          fontStyle: FontStyle.italic,
                                        ),
                                      ),
                                  ],
                                ),
                              )),

                          const Padding(
                            padding: EdgeInsets.symmetric(vertical: 12),
                            child: _DashedDivider(),
                          ),

                          // Subtotal
                          _buildReceiptRow('Subtotal', currency.format(subtotal)),
                          if (discount != null && discount! > 0) ...[
                            const SizedBox(height: 4),
                            _buildReceiptRow('Diskon', '-${currency.format(discount)}', valueColor: AppColors.error),
                          ],
                          if (serviceCharge != null && serviceCharge! > 0) ...[
                            const SizedBox(height: 4),
                            _buildReceiptRow('Service Charge', currency.format(serviceCharge)),
                          ],
                          if (tax != null && tax! > 0) ...[
                            const SizedBox(height: 4),
                            _buildReceiptRow(
                              taxInclusive ? 'Pajak (inklusif)' : 'Pajak',
                              currency.format(tax),
                            ),
                          ],

                          const Divider(height: 24, color: AppColors.border),

                          _buildReceiptRow(
                            'TOTAL',
                            currency.format(totalAmount),
                            isBold: true,
                            fontSize: 18,
                          ),
                          const SizedBox(height: 8),
                          _buildReceiptRow('Metode Bayar', paymentMethod),
                          const SizedBox(height: 4),
                          _buildReceiptRow('Bayar', currency.format(amountPaid)),
                          const SizedBox(height: 4),
                          _buildReceiptRow(
                            'Kembali',
                            currency.format(changeAmount > 0 ? changeAmount : 0),
                            valueColor: AppColors.success,
                          ),

                          const SizedBox(height: 24),
                          Text(
                            (customFooter != null && customFooter.isNotEmpty)
                                ? 'Terima kasih atas kunjungan Anda!\n$customFooter'
                                : 'Terima kasih atas kunjungan Anda!\nPowered by Kasira',
                            textAlign: TextAlign.center,
                            style: const TextStyle(
                              color: AppColors.textTertiary,
                              fontSize: 12,
                            ),
                          ),
                          const SizedBox(height: 8),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 32),

              // Action buttons
              SizedBox(
                width: 380,
                child: Row(
                  children: [
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: () => _printReceipt(context, ref, now),
                        icon: const Icon(LucideIcons.printer, size: 18),
                        label: const Text('Cetak Struk'),
                        style: OutlinedButton.styleFrom(
                          padding: const EdgeInsets.symmetric(vertical: 14),
                        ),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: ElevatedButton.icon(
                        onPressed: () => _shareViaWa(context),
                        icon: const Icon(LucideIcons.messageCircle, size: 18),
                        label: const Text('Kirim WA'),
                        style: ElevatedButton.styleFrom(
                          padding: const EdgeInsets.symmetric(vertical: 14),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 12),
              SizedBox(
                width: 380,
                child: TextButton(
                  onPressed: () => context.go('/dashboard'),
                  child: const Text('Kembali ke Dashboard'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildReceiptRow(String label, String value,
      {bool isBold = false, double fontSize = 14, Color? valueColor}) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(
          label,
          style: TextStyle(
            color: isBold ? AppColors.textPrimary : AppColors.textSecondary,
            fontWeight: isBold ? FontWeight.bold : FontWeight.normal,
            fontSize: fontSize,
          ),
        ),
        Text(
          value,
          style: TextStyle(
            color: valueColor ?? AppColors.textPrimary,
            fontWeight: isBold ? FontWeight.bold : FontWeight.w600,
            fontSize: fontSize,
          ),
        ),
      ],
    );
  }

  Future<void> _printReceipt(BuildContext context, WidgetRef ref, DateTime now) async {
    final notifier = ref.read(printerProvider.notifier);
    final state = ref.read(printerProvider);

    if (!state.isConnected) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Printer belum terhubung. Hubungkan di Pengaturan > Printer.'),
          backgroundColor: AppColors.error,
          behavior: SnackBarBehavior.floating,
        ),
      );
      return;
    }

    final taxConfig = ref.read(taxConfigProvider).valueOrNull;
    final dateFormat = DateFormat('dd/MM/yy HH:mm', 'id_ID');
    final data = ReceiptData(
      outletName: outletName,
      outletAddress: outletAddress,
      orderNumber: displayNumber,
      dateTime: dateFormat.format(now),
      items: items.map((i) => ReceiptLineItem(
        name: i.name,
        qty: i.qty,
        price: i.price,
        notes: i.notes,
      )).toList(),
      subtotal: items.fold(0.0, (s, i) => s + i.subtotal),
      tax: tax,
      serviceCharge: serviceCharge,
      total: totalAmount,
      paymentMethod: paymentMethod,
      amountPaid: amountPaid,
      changeAmount: changeAmount,
      taxNumber: taxConfig?.taxNumber,
      customFooter: taxConfig?.receiptFooter,
    );

    final bytes = buildReceipt(data);
    final ok = await notifier.printBytes(bytes);

    if (context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(ok ? 'Struk dikirim ke printer' : 'Gagal mencetak, coba lagi'),
          backgroundColor: ok ? AppColors.success : AppColors.error,
          behavior: SnackBarBehavior.floating,
        ),
      );
    }
  }

  void _shareViaWa(BuildContext context) {
    showDialog(
      context: context,
      builder: (_) => SendReceiptWaDialog(
        orderId: orderId,
        customerId: customerId,
        customerName: customerName,
      ),
    );
  }
}

/// Dialog untuk kirim struk via WhatsApp.
/// Kalau `customerId` null DAN phone berhasil kirim → auto-create customer record
/// (best-effort, silent on duplicate). Biar nomor WA ke-save untuk transaksi berikutnya.
class SendReceiptWaDialog extends StatefulWidget {
  final String orderId;
  final String? customerId;
  final String? customerName;

  const SendReceiptWaDialog({
    super.key,
    required this.orderId,
    this.customerId,
    this.customerName,
  });

  @override
  State<SendReceiptWaDialog> createState() => _SendReceiptWaDialogState();
}

class _SendReceiptWaDialogState extends State<SendReceiptWaDialog> {
  final _phoneController = TextEditingController();
  final _nameController = TextEditingController();
  bool _isLoading = false;
  bool _saveAsCustomer = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    if (widget.customerName != null) {
      _nameController.text = widget.customerName!;
    }
    // Kalau customer udah kepilih di cart, gak perlu save lagi (sudah di DB)
    _saveAsCustomer = widget.customerId == null;
  }

  @override
  void dispose() {
    _phoneController.dispose();
    _nameController.dispose();
    super.dispose();
  }

  Future<void> _send() async {
    final rawPhone = _phoneController.text.trim();
    if (rawPhone.isEmpty) {
      setState(() => _error = 'Masukkan nomor HP');
      return;
    }
    // Normalize ke 628xxx sebelum kirim — prevent duplicate customer record
    // kalau user next time ketik format beda (08xxx vs 628xxx).
    final phone = normalizeIndoPhone(rawPhone);
    if (phone == null) {
      setState(() => _error = 'Nomor HP tidak valid (minimal 8 digit)');
      return;
    }
    setState(() { _isLoading = true; _error = null; });

    try {
      final dio = Dio(BaseOptions(
        baseUrl: AppConfig.apiV1,
        connectTimeout: const Duration(seconds: 15),
        receiveTimeout: const Duration(seconds: 15),
      ));
      final headers = SessionCache.instance.authHeaders;

      // 1. Kirim struk via WA (backend juga normalize, tapi kirim sudah
      //    normalized biar konsisten dengan customer record yang di-save)
      final response = await dio.post(
        '/payments/send-receipt',
        options: Options(headers: headers),
        data: {'order_id': widget.orderId, 'phone': phone},
      );

      final sent = response.data['data']?['sent'] == true;

      // 2. Best-effort: save as customer kalau user opt-in & belum linked
      bool customerSaved = false;
      if (sent && _saveAsCustomer && widget.customerId == null) {
        final name = _nameController.text.trim().isNotEmpty
            ? _nameController.text.trim()
            : 'Pelanggan $phone';
        try {
          await dio.post(
            '/customers/',
            options: Options(headers: headers),
            data: {'name': name, 'phone': phone},
          );
          customerSaved = true;
        } on DioException catch (e) {
          // 400 = phone sudah terdaftar — anggap "saved" karena tujuan tercapai
          if (e.response?.statusCode == 400) customerSaved = true;
          // error lain: silent, jangan block success flow
        } catch (_) {}
      }

      if (mounted) {
        Navigator.pop(context);
        final msg = sent
            ? (customerSaved
                ? 'Struk dikirim ke $phone & pelanggan tersimpan'
                : 'Struk dikirim ke $phone')
            : 'Gagal mengirim struk';
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(msg),
            backgroundColor: sent ? AppColors.success : AppColors.error,
            behavior: SnackBarBehavior.floating,
          ),
        );
      }
    } on DioException catch (e) {
      final detail = e.response?.data?['detail'] ?? 'Gagal mengirim';
      if (mounted) setState(() { _isLoading = false; _error = detail.toString(); });
    } catch (e) {
      if (mounted) setState(() { _isLoading = false; _error = 'Terjadi kesalahan'; });
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      title: const Row(
        children: [
          Icon(LucideIcons.messageCircle, color: AppColors.primary, size: 20),
          SizedBox(width: 8),
          Text('Kirim Struk via WA'),
        ],
      ),
      content: SizedBox(
        width: 360,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Masukkan nomor WhatsApp customer',
              style: TextStyle(color: AppColors.textSecondary, fontSize: 13),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _phoneController,
              keyboardType: TextInputType.phone,
              inputFormatters: [FilteringTextInputFormatter.digitsOnly],
              autofocus: true,
              decoration: InputDecoration(
                hintText: '08xxxxxxxxxx',
                prefixIcon: const Icon(LucideIcons.smartphone, size: 18),
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
                focusedBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(10),
                  borderSide: const BorderSide(color: AppColors.primary, width: 2),
                ),
                errorText: _error,
              ),
              onSubmitted: (_) => _send(),
            ),
            const SizedBox(height: 6),
            const Text(
              'Format: 08xxx atau 628xxx',
              style: TextStyle(color: AppColors.textTertiary, fontSize: 11),
            ),
            // Save as customer opt-in — hanya kalau cart belum link ke customer
            if (widget.customerId == null) ...[
              const SizedBox(height: 16),
              const Divider(height: 1),
              const SizedBox(height: 12),
              CheckboxListTile(
                value: _saveAsCustomer,
                onChanged: (v) => setState(() => _saveAsCustomer = v ?? false),
                controlAffinity: ListTileControlAffinity.leading,
                contentPadding: EdgeInsets.zero,
                dense: true,
                title: const Text(
                  'Simpan sebagai pelanggan',
                  style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600),
                ),
                subtitle: const Text(
                  'Nomor WA disimpan biar gak perlu input ulang next order',
                  style: TextStyle(fontSize: 11, color: AppColors.textTertiary),
                ),
              ),
              if (_saveAsCustomer) ...[
                const SizedBox(height: 8),
                TextField(
                  controller: _nameController,
                  decoration: InputDecoration(
                    hintText: 'Nama pelanggan (opsional)',
                    prefixIcon: const Icon(LucideIcons.user, size: 18),
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
                    isDense: true,
                  ),
                ),
              ],
            ],
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: _isLoading ? null : () => Navigator.pop(context),
          child: const Text('Batal'),
        ),
        ElevatedButton(
          onPressed: _isLoading ? null : _send,
          child: _isLoading
              ? const SizedBox(
                  width: 18,
                  height: 18,
                  child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                )
              : const Text('Kirim'),
        ),
      ],
    );
  }
}

class _DashedDivider extends StatelessWidget {
  const _DashedDivider();

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(builder: (context, constraints) {
      const dashWidth = 6.0;
      const dashSpace = 4.0;
      final dashCount = (constraints.constrainWidth() / (dashWidth + dashSpace)).floor();
      return Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: List.generate(dashCount, (_) {
          return Container(width: dashWidth, height: 1, color: AppColors.border);
        }),
      );
    });
  }
}
