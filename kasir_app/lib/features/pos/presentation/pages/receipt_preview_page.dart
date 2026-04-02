import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:lucide_icons/lucide_icons.dart';
import 'package:go_router/go_router.dart';
import '../../../../core/theme/app_colors.dart';

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

class ReceiptPreviewPage extends StatelessWidget {
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
  Widget build(BuildContext context) {
    final currency = NumberFormat.currency(locale: 'id_ID', symbol: 'Rp ', decimalDigits: 0);
    final dateFormat = DateFormat('dd MMM yyyy, HH:mm', 'id_ID');
    final now = DateTime.now();
    final subtotal = items.fold(0.0, (sum, item) => sum + item.subtotal);

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: Colors.white,
        title: const Text('Preview Struk', style: TextStyle(color: AppColors.textPrimary)),
        iconTheme: const IconThemeData(color: AppColors.textPrimary),
        elevation: 0,
        actions: [
          IconButton(
            onPressed: () => _printReceipt(context),
            icon: const Icon(LucideIcons.printer, color: AppColors.primary),
            tooltip: 'Cetak',
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
                  color: Colors.white,
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
                          if (serviceCharge != null && serviceCharge! > 0) ...[
                            const SizedBox(height: 4),
                            _buildReceiptRow('Service Charge', currency.format(serviceCharge)),
                          ],
                          if (tax != null && tax! > 0) ...[
                            const SizedBox(height: 4),
                            _buildReceiptRow('Pajak', currency.format(tax)),
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
                          const Text(
                            'Terima kasih atas kunjungan Anda!\nPowered by Kasira',
                            textAlign: TextAlign.center,
                            style: TextStyle(
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
                        onPressed: () => _printReceipt(context),
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

  void _printReceipt(BuildContext context) {
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Mengirim ke printer...'),
        behavior: SnackBarBehavior.floating,
      ),
    );
  }

  void _shareViaWa(BuildContext context) {
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Mengirim struk via WhatsApp...'),
        behavior: SnackBarBehavior.floating,
      ),
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
