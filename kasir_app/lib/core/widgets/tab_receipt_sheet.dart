import 'package:flutter/material.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../services/tab_receipt_service.dart';
import '../theme/kasira_ds.dart';
import 'send_wa_receipt_dialog.dart';

/// Sheet "Struk" untuk pembayaran tab / split bill.
///
/// Sengaja HANYA muncul kalau kasir yang mencet. Versi sebelumnya nawarin kirim
/// WA sendiri lewat tombol aksi di snackbar sukses — nagih nomor sesudah duit
/// masuk bikin kasir kudu ngejar customer yang udah beranjak pergi. Di sini
/// urutannya kebalik: kasir buka sheet ini waktu customer-nya yang minta struk.
///
/// [onPrint] dibungkus caller supaya sheet ini gak perlu tau bentuk struknya —
/// split, subset item, atau order penuh sama aja dari sisi sini.
Future<void> showTabReceiptSheet(
  BuildContext context, {
  required String title,
  required String subtitle,
  required Future<TabPrintResult> Function() onPrint,

  /// Target kirim WA. `null` = tombol WA disembunyiin (misal struk pay-full yang
  /// nyangkut di banyak order sekaligus, atau payment_id-nya belum ke-resolve).
  String? waOrderId,
  String? waPaymentId,
}) {
  return showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    backgroundColor: KasiraDS.surfaceCard,
    shape: const RoundedRectangleBorder(
      borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
    ),
    builder: (_) => _TabReceiptSheet(
      title: title,
      subtitle: subtitle,
      onPrint: onPrint,
      waOrderId: waOrderId,
      waPaymentId: waPaymentId,
    ),
  );
}

class _TabReceiptSheet extends StatefulWidget {
  final String title;
  final String subtitle;
  final Future<TabPrintResult> Function() onPrint;
  final String? waOrderId;
  final String? waPaymentId;

  const _TabReceiptSheet({
    required this.title,
    required this.subtitle,
    required this.onPrint,
    this.waOrderId,
    this.waPaymentId,
  });

  @override
  State<_TabReceiptSheet> createState() => _TabReceiptSheetState();
}

class _TabReceiptSheetState extends State<_TabReceiptSheet> {
  bool _printing = false;

  Future<void> _print() async {
    if (_printing) return;
    setState(() => _printing = true);

    // Messenger + navigator di-capture SEBELUM await — sheet-nya ketutup di
    // bawah, context-nya ikut mati.
    final messenger = ScaffoldMessenger.of(context);
    final result = await widget.onPrint();
    if (!mounted) return;
    setState(() => _printing = false);

    final (msg, color) = switch (result) {
      TabPrintResult.success => ('Struk dicetak', KasiraDS.success),
      TabPrintResult.notConnected => (
          'Printer belum terhubung. Hubungkan di Pengaturan > Printer.',
          KasiraDS.danger,
        ),
      TabPrintResult.failed => (
          'Gagal cetak struk — cek kertas & koneksi printer.',
          KasiraDS.danger,
        ),
    };

    // Sukses = urusan kelar, tutup sheet. Gagal = biarin kebuka biar kasir bisa
    // langsung coba lagi atau banting setir ke WA tanpa navigasi ulang.
    if (result == TabPrintResult.success) Navigator.pop(context);
    messenger.showSnackBar(SnackBar(
      content: Text(msg),
      backgroundColor: color,
      behavior: SnackBarBehavior.floating,
      duration: const Duration(seconds: 3),
    ));
  }

  void _sendWa() {
    final orderId = widget.waOrderId;
    if (orderId == null) return;
    final navigator = Navigator.of(context);
    final rootContext = Navigator.of(context, rootNavigator: true).context;
    navigator.pop();
    showDialog<void>(
      context: rootContext,
      builder: (_) => SendWaReceiptDialog(
        orderId: orderId,
        paymentId: widget.waPaymentId,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.fromLTRB(
        20,
        16,
        20,
        MediaQuery.of(context).padding.bottom + 20,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Center(
            child: Container(
              width: 42,
              height: 4,
              decoration: BoxDecoration(
                color: KasiraDS.borderSubtle,
                borderRadius: KasiraDS.brPill,
              ),
            ),
          ),
          const SizedBox(height: 18),
          Row(
            children: [
              const Icon(LucideIcons.receipt,
                  color: KasiraDS.brandPrimary, size: 22),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(widget.title,
                        style: KasiraDS.display(
                            size: 18, color: KasiraDS.textStrong)),
                    const SizedBox(height: 2),
                    Text(widget.subtitle,
                        style: KasiraDS.sans(
                            size: 12.5, color: KasiraDS.textMuted)),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 20),
          SizedBox(
            width: double.infinity,
            height: 50,
            child: FilledButton.icon(
              onPressed: _printing ? null : _print,
              style: FilledButton.styleFrom(
                backgroundColor: KasiraDS.brandPrimary,
                shape: RoundedRectangleBorder(borderRadius: KasiraDS.brMd),
              ),
              icon: _printing
                  ? const SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(
                          strokeWidth: 2, color: Colors.white))
                  : const Icon(LucideIcons.printer, size: 18),
              label: Text(_printing ? 'Mencetak...' : 'Cetak Struk',
                  style: KasiraDS.sans(
                      size: 15,
                      weight: FontWeight.w700,
                      color: KasiraDS.textOnBrand)),
            ),
          ),
          if (widget.waOrderId != null) ...[
            const SizedBox(height: 10),
            SizedBox(
              width: double.infinity,
              height: 50,
              child: OutlinedButton.icon(
                onPressed: _printing ? null : _sendWa,
                style: OutlinedButton.styleFrom(
                  foregroundColor: const Color(0xFF25D366),
                  side: const BorderSide(color: Color(0xFF25D366)),
                  shape: RoundedRectangleBorder(borderRadius: KasiraDS.brMd),
                ),
                icon: const Icon(LucideIcons.messageCircle, size: 18),
                label: Text('Kirim ke WhatsApp',
                    style: KasiraDS.sans(size: 15, weight: FontWeight.w700)),
              ),
            ),
            const SizedBox(height: 6),
            Text('Nomornya diminta di langkah berikutnya.',
                style: KasiraDS.sans(size: 11.5, color: KasiraDS.textMuted)),
          ],
        ],
      ),
    );
  }
}
