import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
import '../../../../core/services/printer_service.dart';
import '../../../../core/services/tab_receipt_service.dart';
import '../../../../core/theme/kasira_ds.dart';
import '../../../../core/widgets/tab_receipt_sheet.dart';
import '../../providers/tab_provider.dart';
import 'qris_waiting_modal.dart';

/// Pay-items modal — warkop pattern: kasir centang items yg customer sebut → bayar.
/// Items kepay individu, sisa unpaid masih nempel di tab. Auto-print struk pasca
/// cash payment success (Rule #54 fail-silent).
class PayItemsModal extends ConsumerStatefulWidget {
  final TabModel tab;
  final List<TabItemModel> unpaidItems;
  final void Function(TabModel updatedTab) onPaid;
  /// true = semua item ke-select duluan (= "Bayar Semua" 1 tap).
  final bool preselectAll;

  const PayItemsModal({
    super.key,
    required this.tab,
    required this.unpaidItems,
    required this.onPaid,
    this.preselectAll = false,
  });

  @override
  ConsumerState<PayItemsModal> createState() => _PayItemsModalState();
}

class _PayItemsModalState extends ConsumerState<PayItemsModal> {
  final _currency = NumberFormat.currency(locale: 'id_ID', symbol: 'Rp ', decimalDigits: 0);
  final Set<String> _selected = {};
  String _paymentMethod = 'cash';
  final _amountController = TextEditingController();
  double _amountReceived = 0;
  /// Begitu kasir ngetik nominal sendiri, field berhenti ngikutin total centangan.
  /// Tanpa ini, ngetik manual bakal ketimpa tiap kali item di-centang/uncentang.
  bool _amountEdited = false;
  bool _isLoading = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    // "Bayar Semua" → semua item unpaid ke-select duluan, kasir tinggal konfirmasi.
    if (widget.preselectAll) {
      _selected.addAll(widget.unpaidItems.map((i) => i.id));
    }
  }

  @override
  void dispose() {
    _amountController.dispose();
    super.dispose();
  }

  /// Round half-away-from-zero ke 2 desimal — mirror Python `Decimal.quantize(0.01)`
  /// yg dipake backend `items_proportional_due()`.
  double _q2(double x) => (x * 100).roundToDouble() / 100;

  /// Total yg DI-CHARGE ke customer = subtotal items + proportional tax + service share.
  /// Mirror backend `items_proportional_due()` di tab_service.py — WAJIB konsisten
  /// supaya kasir nampilin nominal yg same dgn yg backend hitung saat submit.
  ///
  /// Quantize per-share (bukan per-total) WAJIB match backend. Tanpa quantize,
  /// double float drift bikin total < Decimal backend by ~Rp 0.0045 → backend
  /// reject "Nominal pembayaran kurang" walau display match. Bug discovered
  /// 2026-04-26 di tab cappucino real merchant (tax-inclusive 5K/55K = 0.0909..).
  double get _selectedTotal {
    final selectedSubtotal = widget.unpaidItems
        .where((i) => _selected.contains(i.id))
        .fold(0.0, (sum, i) => sum + i.totalPrice);
    if (selectedSubtotal == 0) return 0;
    final tabSubtotal = widget.tab.subtotal;
    if (tabSubtotal == 0) return selectedSubtotal;
    final taxRate = widget.tab.taxAmount / tabSubtotal;
    final serviceRate = widget.tab.serviceChargeAmount / tabSubtotal;
    final shareTax = _q2(selectedSubtotal * taxRate);
    final shareService = _q2(selectedSubtotal * serviceRate);
    return selectedSubtotal + shareTax + shareService;
  }

  void _toggle(String itemId) {
    setState(() {
      if (_selected.contains(itemId)) {
        _selected.remove(itemId);
      } else {
        _selected.add(itemId);
      }
      // Syarat lama `_amountController.text.isEmpty` bikin nominal cuma ke-isi
      // SEKALI — pas item pertama dicentang. Centang item berikutnya, total naik
      // tapi "Uang Diterima" nyangkut di harga item pertama, jadi kasir liat
      // 10rb padahal tagihannya lebih. Sekarang ngikut terus, kecuali kasir
      // udah ngetik nominal sendiri.
      if (_paymentMethod == 'cash' && !_amountEdited) {
        _amountReceived = _selectedTotal;
        _amountController.text = _selectedTotal.toStringAsFixed(0);
      }
    });
  }

  void _selectAll() {
    setState(() {
      if (_selected.length == widget.unpaidItems.length) {
        _selected.clear();
      } else {
        _selected.addAll(widget.unpaidItems.map((i) => i.id));
      }
      if (!_amountEdited) {
        _amountReceived = _selectedTotal;
        _amountController.text = _selectedTotal.toStringAsFixed(0);
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final selectedTotal = _selectedTotal;
    final change = _amountReceived - selectedTotal;
    final allSelected = _selected.length == widget.unpaidItems.length && widget.unpaidItems.isNotEmpty;

    return DraggableScrollableSheet(
      initialChildSize: 0.85,
      minChildSize: 0.5,
      maxChildSize: 0.95,
      expand: false,
      builder: (_, scrollCtrl) {
        return Padding(
          padding: EdgeInsets.only(
            left: 16, right: 16, top: 16,
            bottom: MediaQuery.of(context).viewInsets.bottom + 16,
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header
              Row(
                children: [
                  const Icon(LucideIcons.checkSquare, color: KasiraDS.brandPrimary),
                  const SizedBox(width: 8),
                  Text('Bayar Sebagian', style: Theme.of(context).textTheme.titleLarge),
                  const Spacer(),
                  IconButton(onPressed: () => Navigator.pop(context), icon: const Icon(LucideIcons.x)),
                ],
              ),
              Text(
                'Centang items yang dibayar customer',
                style: TextStyle(color: KasiraDS.textMuted, fontSize: 13),
              ),
              const SizedBox(height: 12),

              // Select all toggle
              InkWell(
                onTap: _selectAll,
                child: Padding(
                  padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 4),
                  child: Row(
                    children: [
                      Icon(
                        allSelected ? LucideIcons.checkSquare : LucideIcons.square,
                        size: 18, color: KasiraDS.brandPrimary,
                      ),
                      const SizedBox(width: 8),
                      Text(
                        allSelected ? 'Batal pilih semua' : 'Pilih semua (${widget.unpaidItems.length})',
                        style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600),
                      ),
                    ],
                  ),
                ),
              ),
              const Divider(),

              // Items checklist
              Expanded(
                child: ListView.builder(
                  controller: scrollCtrl,
                  itemCount: widget.unpaidItems.length,
                  itemBuilder: (_, i) {
                    final item = widget.unpaidItems[i];
                    final selected = _selected.contains(item.id);
                    return InkWell(
                      onTap: () => _toggle(item.id),
                      child: Container(
                        padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 4),
                        decoration: BoxDecoration(
                          border: Border(
                            bottom: BorderSide(color: KasiraDS.borderSubtle.withOpacity(0.3)),
                          ),
                        ),
                        child: Row(
                          children: [
                            Icon(
                              selected ? LucideIcons.checkSquare : LucideIcons.square,
                              size: 20,
                              color: selected ? KasiraDS.brandPrimary : KasiraDS.textMuted,
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    item.productName,
                                    style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14),
                                  ),
                                  Text(
                                    '${item.quantity} x ${_currency.format(item.unitPrice)}',
                                    style: TextStyle(color: KasiraDS.textMuted, fontSize: 12),
                                  ),
                                ],
                              ),
                            ),
                            Text(
                              _currency.format(item.totalPrice),
                              style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14),
                            ),
                          ],
                        ),
                      ),
                    );
                  },
                ),
              ),

              // Realtime total + payment
              if (_selected.isNotEmpty) ...[
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: KasiraDS.brandPrimary.withOpacity(0.05),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text('${_selected.length} item dipilih',
                          style: const TextStyle(fontSize: 13, color: KasiraDS.textMuted)),
                      Text(
                        _currency.format(selectedTotal),
                        style: const TextStyle(
                          fontWeight: FontWeight.bold,
                          fontSize: 20,
                          color: KasiraDS.brandPrimary,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 12),

                // Payment method
                Row(
                  children: [
                    _buildMethodChip('cash', 'Cash', LucideIcons.banknote),
                    const SizedBox(width: 8),
                    _buildMethodChip('qris', 'QRIS', LucideIcons.qrCode),
                  ],
                ),
                const SizedBox(height: 12),

                if (_paymentMethod == 'cash') ...[
                  TextField(
                    controller: _amountController,
                    keyboardType: TextInputType.number,
                    style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                    decoration: InputDecoration(
                      labelText: 'Uang Diterima',
                      prefixText: 'Rp ',
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
                      contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
                    ),
                    onChanged: (v) {
                      setState(() {
                        _amountEdited = true;
                        _amountReceived = double.tryParse(v) ?? 0;
                      });
                    },
                  ),
                  if (change > 0)
                    Padding(
                      padding: const EdgeInsets.only(top: 6),
                      child: Text(
                        'Kembalian: ${_currency.format(change)}',
                        style: const TextStyle(color: KasiraDS.success, fontWeight: FontWeight.w600),
                      ),
                    ),
                  const SizedBox(height: 8),
                ],

                if (_error != null)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: Text(_error!, style: const TextStyle(color: KasiraDS.danger, fontSize: 12)),
                  ),

                SizedBox(
                  width: double.infinity,
                  child: FilledButton.icon(
                    onPressed: _isLoading || _selected.isEmpty ? null : _submitPayment,
                    icon: _isLoading
                        ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                        : const Icon(LucideIcons.check),
                    label: Text(_isLoading
                        ? 'Memproses...'
                        : 'Bayar ${_currency.format(selectedTotal)}'),
                    style: FilledButton.styleFrom(
                      backgroundColor: KasiraDS.brandPrimary,
                      padding: const EdgeInsets.symmetric(vertical: 14),
                    ),
                  ),
                ),
              ],
            ],
          ),
        );
      },
    );
  }

  Widget _buildMethodChip(String value, String label, IconData icon) {
    final selected = _paymentMethod == value;
    return Expanded(
      child: InkWell(
        onTap: () => setState(() => _paymentMethod = value),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 10),
          decoration: BoxDecoration(
            color: selected ? KasiraDS.brandPrimary.withOpacity(0.08) : null,
            border: Border.all(color: selected ? KasiraDS.brandPrimary : KasiraDS.borderSubtle),
            borderRadius: BorderRadius.circular(10),
          ),
          child: Column(
            children: [
              Icon(icon, color: selected ? KasiraDS.brandPrimary : KasiraDS.textMuted, size: 18),
              const SizedBox(height: 2),
              Text(label,
                  style: TextStyle(
                    color: selected ? KasiraDS.brandPrimary : KasiraDS.textMuted,
                    fontWeight: FontWeight.w600,
                    fontSize: 12,
                  )),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _submitPayment() async {
    setState(() { _isLoading = true; _error = null; });

    final notifier = ref.read(tabProvider.notifier);
    final idempKey = 'pay_items_${widget.tab.id}_${DateTime.now().millisecondsSinceEpoch}';

    final result = await notifier.payItems(
      widget.tab.id,
      _selected.toList(),
      _paymentMethod,
      _amountReceived,
      idempotencyKey: idempKey,
    );

    if (mounted) {
      setState(() => _isLoading = false);
      if (result != null) {
        // Capture stable refs SEBELUM Navigator.pop
        final messenger = ScaffoldMessenger.of(context);
        final rootNav = Navigator.of(context, rootNavigator: true);
        final selectedItemIds = _selected.toList();

        // ⚠️ `ref` HARAM disentuh sesudah pop — flutter_riverpod throw
        // StateError('Cannot use "ref" after the widget was disposed').
        // Lihat catatan lengkapnya di `pay_split_modal.dart`: gara-gara ini
        // auto-print struk tab gak pernah jalan sama sekali. Notifier-nya milik
        // provider container, jadi aman dipegang lintas await.
        final printer = ref.read(printerProvider.notifier);
        final tabNotifier = ref.read(tabProvider.notifier);

        final tabIdSnap = widget.tab.id;
        final tabNumberSnap = widget.tab.tabNumber;
        final isCash = _paymentMethod == 'cash';
        final paidCountSnap = selectedItemIds.length;
        final tabSnap = result;
        // Dihitung SEKARANG, bukan di dalam closure: `widget` dibaca sesudah
        // State-nya ke-dispose itu jebakan yang sama kayak `ref`.
        final unpaidLeftSnap = widget.unpaidItems
            .where((i) => !selectedItemIds.contains(i.id))
            .length;

        // Target struk subset di-resolve sekali, lalu dipakai ulang buat cetak
        // maupun kirim WA. Di-cache biar tombol STRUK yang dipencet belakangan
        // gak nembak `/tabs/{id}/items` lagi tiap kali.
        ({String orderId, String paymentId})? target;
        var targetResolved = false;
        Future<({String orderId, String paymentId})?> resolveTarget() async {
          if (targetResolved) return target;
          target = await resolveTabItemsReceiptTarget(
            tabId: tabIdSnap,
            itemIds: selectedItemIds,
          );
          targetResolved = true;
          return target;
        }

        Future<TabPrintResult> printReceipt() async {
          final t = await resolveTarget();
          if (t == null) return TabPrintResult.failed;
          return printTabItemsReceipt(
            printer,
            orderId: t.orderId,
            paymentId: t.paymentId,
            tabNumber: tabNumberSnap,
            isTabPaid: tabSnap.status == 'paid',
            outstandingAmount: tabSnap.remainingAmount,
            outstandingItemCount: unpaidLeftSnap,
          );
        }

        Future<void> openReceiptSheet() async {
          final t = await resolveTarget();
          await showTabReceiptSheet(
            rootNav.context,
            title: 'Struk $paidCountSnap item',
            subtitle: tabNumberSnap,
            onPrint: printReceipt,
            waOrderId: t?.orderId,
            waPaymentId: t?.paymentId,
          );
        }

        SnackBarAction receiptAction() => SnackBarAction(
              label: 'STRUK',
              textColor: Colors.white,
              onPressed: () => unawaited(openReceiptSheet()),
            );

        // Auto-print gak nge-block flow (Rule #54) tapi juga gak diam total —
        // kasir wajib tau kalau struknya gagal keluar.
        void autoPrintThenReport() {
          unawaited(printReceipt().then((r) {
            if (r == TabPrintResult.success) return;
            messenger.showSnackBar(SnackBar(
              content: Text(r == TabPrintResult.notConnected
                  ? 'Struk belum kecetak — printer belum terhubung.'
                  : 'Struk gagal dicetak.'),
              backgroundColor: KasiraDS.warning,
              duration: const Duration(seconds: 6),
              action: receiptAction(),
            ));
          }));
        }

        // QRIS branch — switch to waiting modal, autoprint via claim-print on webhook settle
        if (_paymentMethod == 'qris' && result.pendingQris != null) {
          final qris = result.pendingQris!;
          Navigator.pop(context);
          widget.onPaid(result);
          await showModalBottomSheet<bool>(
            context: rootNav.context,
            isScrollControlled: true,
            isDismissible: false,
            enableDrag: false,
            builder: (_) => QrisWaitingModal(
              tabId: tabIdSnap,
              pendingQris: qris,
              onPaidAndClaimedPrint: (paymentId) async {
                autoPrintThenReport();
              },
            ),
          );
          // Refresh tab post-webhook (paid → tab maybe closed; cancel/expired → items unlocked)
          final refreshed = await tabNotifier.getTab(tabIdSnap);
          if (refreshed != null) widget.onPaid(refreshed);
          return;
        }

        Navigator.pop(context);
        widget.onPaid(result);

        // Auto-print struk per items dipay (cash only — QRIS lewat claim-print)
        if (isCash) autoPrintThenReport();

        // Konfirmasi pembayaran doang — TANPA ajakan kirim WA yang nyembul
        // sendiri. Yang nempel di sini tombol STRUK: kasir yang mencet waktu
        // customer-nya yang minta, dan di dalam sheet baru ada pilihan cetak
        // atau kirim WA. Lihat catatan lengkap di `pay_split_modal.dart`.
        messenger.showSnackBar(
          SnackBar(
            content: Text(result.isPaid
                ? 'Tab lunas! Semua sudah dibayar.'
                : '$paidCountSnap item dibayar. Sisa: ${_currency.format(result.remainingAmount)}'),
            backgroundColor: KasiraDS.success,
            action: receiptAction(),
          ),
        );
      } else {
        setState(() => _error = ref.read(tabProvider).error ?? 'Gagal memproses pembayaran');
      }
    }
  }
}
