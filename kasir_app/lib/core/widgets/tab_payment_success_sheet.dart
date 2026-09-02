import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../services/tab_receipt_service.dart';
import '../theme/kasira_ds.dart';
import 'send_wa_receipt_dialog.dart';

/// Layar sukses sesudah bayar tab / split / sebagian item.
///
/// Menggantikan pola lama: snackbar hijau "1 item dibayar. Sisa: Rp x — STRUK"
/// yang nongol di pojok bawah, nimpa baris tombol Bayar Lunas / Split Bill,
/// dan nyelipin urusan struk ke tombol kecil di snackbar yang hilang sendiri
/// dalam 4 detik. Kasir yang lagi ngeladenin 4 orang di satu meja butuh yang
/// kebalikannya: berhenti sebentar, lihat angkanya, cetak/kirim struk, baru
/// lanjut ke orang berikutnya. Itu persis pola `PaymentSuccessPage` di POS
/// reguler, cuma di sini bentuknya sheet biar halaman tab-nya tetap di bawah.
///
/// Auto-print jalan DI SINI dengan status yang kelihatan ("Mencetak…",
/// "Struk dicetak", "Printer belum terhubung"), bukan diam-diam di background
/// lalu ngasih tau lewat snackbar kuning kalau gagal.
enum _PrintStatus { idle, printing, success, notConnected, failed }

Future<void> showTabPaymentSuccessSheet(
  BuildContext context, {
  required String title,
  required String subtitle,

  /// Nominal yang ditagih ke orang ini (porsi split / total item dipilih /
  /// sisa tab).
  required double amountDue,
  required double amountPaid,
  required double remaining,
  required bool isTabPaid,
  required Future<TabPrintResult> Function() onPrint,

  /// Cash = true (langsung cetak). QRIS = false: struknya udah dicetak lewat
  /// claim-print di modal tunggu, jangan dobel.
  required bool autoPrint,
  String? waOrderId,
  String? waPaymentId,
}) {
  return showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    backgroundColor: KasiraDS.surfaceCard,
    shape: const RoundedRectangleBorder(
      borderRadius: BorderRadius.vertical(top: Radius.circular(28)),
    ),
    builder: (_) => _TabPaymentSuccessSheet(
      title: title,
      subtitle: subtitle,
      amountDue: amountDue,
      amountPaid: amountPaid,
      remaining: remaining,
      isTabPaid: isTabPaid,
      onPrint: onPrint,
      autoPrint: autoPrint,
      waOrderId: waOrderId,
      waPaymentId: waPaymentId,
    ),
  );
}

class _TabPaymentSuccessSheet extends StatefulWidget {
  final String title;
  final String subtitle;
  final double amountDue;
  final double amountPaid;
  final double remaining;
  final bool isTabPaid;
  final Future<TabPrintResult> Function() onPrint;
  final bool autoPrint;
  final String? waOrderId;
  final String? waPaymentId;

  const _TabPaymentSuccessSheet({
    required this.title,
    required this.subtitle,
    required this.amountDue,
    required this.amountPaid,
    required this.remaining,
    required this.isTabPaid,
    required this.onPrint,
    required this.autoPrint,
    this.waOrderId,
    this.waPaymentId,
  });

  @override
  State<_TabPaymentSuccessSheet> createState() => _TabPaymentSuccessSheetState();
}

class _TabPaymentSuccessSheetState extends State<_TabPaymentSuccessSheet> {
  final _rp = NumberFormat.currency(locale: 'id_ID', symbol: 'Rp ', decimalDigits: 0);
  _PrintStatus _status = _PrintStatus.idle;

  /// true begitu struk pernah sukses kecetak — label tombol jadi "Cetak Ulang".
  bool _printedOnce = false;

  @override
  void initState() {
    super.initState();
    if (widget.autoPrint) {
      // Kasih sheet-nya sempat kebuka dulu, baru nembak printer — kalau
      // printer mati, pesannya muncul di sheet yang udah kelihatan, bukan
      // di sheet yang masih animasi naik.
      Future.delayed(const Duration(milliseconds: 350), () {
        if (mounted) _print();
      });
    }
  }

  Future<void> _print() async {
    if (_status == _PrintStatus.printing) return;
    setState(() => _status = _PrintStatus.printing);
    final r = await widget.onPrint();
    if (!mounted) return;
    setState(() {
      _status = switch (r) {
        TabPrintResult.success => _PrintStatus.success,
        TabPrintResult.notConnected => _PrintStatus.notConnected,
        TabPrintResult.failed => _PrintStatus.failed,
      };
      if (r == TabPrintResult.success) _printedOnce = true;
    });
  }

  void _sendWa() {
    final orderId = widget.waOrderId;
    if (orderId == null) return;
    final rootContext = Navigator.of(context, rootNavigator: true).context;
    Navigator.of(context).pop();
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
    final change = widget.amountPaid - widget.amountDue;
    final printing = _status == _PrintStatus.printing;

    return Padding(
      padding: EdgeInsets.fromLTRB(
        KasiraDS.space5,
        KasiraDS.space3,
        KasiraDS.space5,
        MediaQuery.of(context).padding.bottom + KasiraDS.space5,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
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
          const SizedBox(height: KasiraDS.space5),

          // ── Ikon + judul ──
          Center(
            child: Container(
              width: 64,
              height: 64,
              alignment: Alignment.center,
              decoration: BoxDecoration(
                color: KasiraDS.success.withOpacity(0.12),
                shape: BoxShape.circle,
              ),
              child: const Icon(LucideIcons.check, size: 32, color: KasiraDS.success),
            ),
          ),
          const SizedBox(height: KasiraDS.space3),
          Text(
            widget.title,
            textAlign: TextAlign.center,
            style: KasiraDS.display(size: 22, color: KasiraDS.textStrong),
          ),
          const SizedBox(height: 2),
          Text(
            widget.subtitle,
            textAlign: TextAlign.center,
            style: KasiraDS.sans(size: 13, color: KasiraDS.textMuted),
          ),
          const SizedBox(height: KasiraDS.space5),

          // ── Angka ──
          Container(
            padding: const EdgeInsets.all(KasiraDS.space4),
            decoration: BoxDecoration(
              color: KasiraDS.surfaceSunken,
              borderRadius: KasiraDS.brLg,
            ),
            child: Column(
              children: [
                Text('DIBAYAR', style: KasiraDS.eyebrow()),
                const SizedBox(height: 4),
                Text(
                  _rp.format(widget.amountDue),
                  style: KasiraDS.display(size: 32, color: KasiraDS.textStrong),
                ),
                if (change > 0) ...[
                  const SizedBox(height: KasiraDS.space3),
                  const Divider(height: 1, color: KasiraDS.borderSubtle),
                  const SizedBox(height: KasiraDS.space3),
                  _row('Uang diterima', _rp.format(widget.amountPaid)),
                  const SizedBox(height: 6),
                  _row(
                    'Kembalian',
                    _rp.format(change),
                    valueColor: KasiraDS.success,
                    bold: true,
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(height: KasiraDS.space3),

          // ── Status meja ──
          _Banner(
            icon: widget.isTabPaid ? LucideIcons.checkCheck : LucideIcons.clock,
            color: widget.isTabPaid ? KasiraDS.success : KasiraDS.warning,
            text: widget.isTabPaid
                ? 'Meja lunas — semua sudah bayar'
                : 'Sisa tagihan meja ${_rp.format(widget.remaining)}',
          ),
          const SizedBox(height: KasiraDS.space2),

          // ── Status cetak ──
          _printStatusRow(),
          const SizedBox(height: KasiraDS.space4),

          // ── Aksi ──
          SizedBox(
            height: 54,
            child: FilledButton.icon(
              onPressed: printing ? null : _print,
              style: FilledButton.styleFrom(
                backgroundColor: KasiraDS.brandPrimary,
                shape: RoundedRectangleBorder(borderRadius: KasiraDS.brMd),
              ),
              icon: printing
                  ? const SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                    )
                  : const Icon(LucideIcons.printer, size: 18),
              label: Text(
                printing
                    ? 'Mencetak…'
                    : (_printedOnce ? 'Cetak Ulang' : 'Cetak Struk'),
                style: KasiraDS.sans(
                  size: 15,
                  weight: FontWeight.w700,
                  color: KasiraDS.textOnBrand,
                ),
              ),
            ),
          ),
          const SizedBox(height: KasiraDS.space2),
          Row(
            children: [
              if (widget.waOrderId != null) ...[
                Expanded(
                  child: SizedBox(
                    height: 50,
                    child: OutlinedButton.icon(
                      onPressed: printing ? null : _sendWa,
                      style: OutlinedButton.styleFrom(
                        foregroundColor: const Color(0xFF25D366),
                        side: const BorderSide(color: Color(0xFF25D366)),
                        shape: RoundedRectangleBorder(borderRadius: KasiraDS.brMd),
                      ),
                      icon: const Icon(LucideIcons.messageCircle, size: 18),
                      label: Text('Kirim WA',
                          style: KasiraDS.sans(size: 14, weight: FontWeight.w700)),
                    ),
                  ),
                ),
                const SizedBox(width: KasiraDS.space2),
              ],
              Expanded(
                child: SizedBox(
                  height: 50,
                  child: OutlinedButton.icon(
                    onPressed: () => Navigator.of(context).pop(),
                    style: OutlinedButton.styleFrom(
                      foregroundColor: KasiraDS.textStrong,
                      side: const BorderSide(color: KasiraDS.borderDefault),
                      shape: RoundedRectangleBorder(borderRadius: KasiraDS.brMd),
                    ),
                    icon: const Icon(LucideIcons.arrowRight, size: 18),
                    label: Text('Selesai',
                        style: KasiraDS.sans(size: 14, weight: FontWeight.w700)),
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _printStatusRow() {
    final (icon, color, text) = switch (_status) {
      _PrintStatus.idle => (
          LucideIcons.printer,
          KasiraDS.textMuted,
          widget.autoPrint ? 'Menyiapkan struk…' : 'Struk siap dicetak',
        ),
      _PrintStatus.printing => (
          LucideIcons.printer,
          KasiraDS.brandSecondary,
          'Mencetak struk…',
        ),
      _PrintStatus.success => (
          LucideIcons.checkCircle2,
          KasiraDS.success,
          'Struk sudah dicetak',
        ),
      _PrintStatus.notConnected => (
          LucideIcons.unplug,
          KasiraDS.warning,
          'Printer belum terhubung — kirim WA atau hubungkan di Pengaturan',
        ),
      _PrintStatus.failed => (
          LucideIcons.alertCircle,
          KasiraDS.danger,
          'Struk gagal dicetak — cek kertas & koneksi, lalu coba lagi',
        ),
    };
    return Row(
      children: [
        Icon(icon, size: 16, color: color),
        const SizedBox(width: KasiraDS.space2),
        Expanded(
          child: Text(text, style: KasiraDS.sans(size: 12.5, color: color)),
        ),
      ],
    );
  }

  Widget _row(String label, String value, {Color? valueColor, bool bold = false}) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(label, style: KasiraDS.sans(size: 13.5, color: KasiraDS.textMuted)),
        Text(
          value,
          style: KasiraDS.sans(
            size: 15,
            weight: bold ? FontWeight.w800 : FontWeight.w600,
            color: valueColor ?? KasiraDS.textStrong,
          ),
        ),
      ],
    );
  }
}

class _Banner extends StatelessWidget {
  final IconData icon;
  final Color color;
  final String text;

  const _Banner({required this.icon, required this.color, required this.text});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: KasiraDS.space3,
        vertical: 10,
      ),
      decoration: BoxDecoration(
        color: color.withOpacity(0.10),
        borderRadius: KasiraDS.brMd,
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Row(
        children: [
          Icon(icon, size: 18, color: color),
          const SizedBox(width: KasiraDS.space2),
          Expanded(
            child: Text(
              text,
              style: KasiraDS.sans(size: 13.5, weight: FontWeight.w700, color: color),
            ),
          ),
        ],
      ),
    );
  }
}
