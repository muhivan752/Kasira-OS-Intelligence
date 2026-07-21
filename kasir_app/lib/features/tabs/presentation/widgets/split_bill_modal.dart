import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
import '../../../../core/theme/kasira_ds.dart';
import '../../providers/tab_provider.dart';
import 'pay_items_modal.dart';

class SplitBillModal extends ConsumerStatefulWidget {
  final TabModel tab;
  final void Function(TabModel updatedTab) onSplitDone;

  const SplitBillModal({super.key, required this.tab, required this.onSplitDone});

  @override
  ConsumerState<SplitBillModal> createState() => _SplitBillModalState();
}

class _SplitBillModalState extends ConsumerState<SplitBillModal> {
  final _currency = NumberFormat.currency(locale: 'id_ID', symbol: 'Rp ', decimalDigits: 0);
  // Tiga mode saja: bayar sebagian menu (default, pola warkop), bagi rata,
  // dan nominal custom. Mode "per tamu" — assign tiap item ke orang tertentu —
  // dibuang: alurnya panjang (atur jumlah tamu, kasih nama, tap tiap item satu
  // per satu) sementara "bayar sebagian" nutup kebutuhan yang sama jauh lebih
  // cepat. Endpoint /split/per-item di backend masih ada kalau suatu saat balik.
  String _selectedMethod = 'pay_items';
  int _numPeople = 2;
  bool _isLoading = false;
  String? _error;

  // Custom split
  final List<_CustomSplitEntry> _customEntries = [];


  @override
  void initState() {
    super.initState();
    _numPeople = widget.tab.guestCount > 1 ? widget.tab.guestCount : 2;
    _initCustomEntries();
  }

  void _initCustomEntries() {
    _customEntries.clear();
    final perPerson = widget.tab.totalAmount / _numPeople;
    for (int i = 0; i < _numPeople; i++) {
      _customEntries.add(_CustomSplitEntry(
        nameController: TextEditingController(text: 'Tamu ${i + 1}'),
        amountController: TextEditingController(text: perPerson.toStringAsFixed(0)),
      ));
    }
  }

  @override
  void dispose() {
    for (final e in _customEntries) {
      e.nameController.dispose();
      e.amountController.dispose();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final total = widget.tab.totalAmount;
    final perPerson = total / _numPeople;

    return Padding(
      padding: EdgeInsets.only(
        left: 20, right: 20, top: 20,
        bottom: MediaQuery.of(context).viewInsets.bottom + 20,
      ),
      child: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header
            Row(
              children: [
                const Icon(LucideIcons.split, color: KasiraDS.brandPrimary),
                const SizedBox(width: 12),
                Text('Split Bill', style: Theme.of(context).textTheme.titleLarge),
                const Spacer(),
                IconButton(onPressed: () => Navigator.pop(context), icon: const Icon(LucideIcons.x)),
              ],
            ),
            const SizedBox(height: 8),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: KasiraDS.brandPrimary.withOpacity(0.05),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text('Total Tagihan', style: TextStyle(fontSize: 14)),
                  Text(_currency.format(total), style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
                ],
              ),
            ),
            const SizedBox(height: 20),

            // Method selector
            Text('Metode Split', style: KasiraDS.sans(size: 13, color: KasiraDS.textMuted)),
            const SizedBox(height: 8),
            Row(
              children: [
                _buildMethodChip('pay_items', 'Sebagian', LucideIcons.checkSquare),
                const SizedBox(width: KasiraDS.space2),
                _buildMethodChip('equal', 'Bagi Rata', LucideIcons.divide),
                const SizedBox(width: KasiraDS.space2),
                _buildMethodChip('custom', 'Custom', LucideIcons.penTool),
              ],
            ),
            const SizedBox(height: 20),

            if (_selectedMethod == 'pay_items') ...[
              _buildPayItemsIntro(),
            ] else if (_selectedMethod == 'equal') ...[
              // Equal split
              Text('Jumlah Orang', style: TextStyle(color: KasiraDS.textMuted, fontSize: 13)),
              const SizedBox(height: 8),
              Row(
                children: [
                  IconButton.filled(
                    onPressed: _numPeople > 2 ? () => setState(() => _numPeople--) : null,
                    icon: const Icon(LucideIcons.minus, size: 18),
                    style: IconButton.styleFrom(
                      backgroundColor: KasiraDS.surfaceSunken,
                      foregroundColor: KasiraDS.textStrong,
                    ),
                  ),
                  const SizedBox(width: 16),
                  Text('$_numPeople', style: const TextStyle(fontSize: 28, fontWeight: FontWeight.bold)),
                  const SizedBox(width: 16),
                  IconButton.filled(
                    onPressed: _numPeople < 20 ? () => setState(() => _numPeople++) : null,
                    icon: const Icon(LucideIcons.plus, size: 18),
                    style: IconButton.styleFrom(
                      backgroundColor: KasiraDS.brandPrimary.withOpacity(0.1),
                      foregroundColor: KasiraDS.brandPrimary,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: KasiraDS.surfaceSunken,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Text('Per orang', style: TextStyle(fontSize: 15)),
                    Text(
                      _currency.format(perPerson),
                      style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 20, color: KasiraDS.brandPrimary),
                    ),
                  ],
                ),
              ),
            ] else ...[
              // Custom split
              ..._customEntries.asMap().entries.map((entry) {
                final i = entry.key;
                final e = entry.value;
                return Padding(
                  padding: const EdgeInsets.only(bottom: 10),
                  child: Row(
                    children: [
                      Expanded(
                        flex: 3,
                        child: TextField(
                          controller: e.nameController,
                          decoration: InputDecoration(
                            isDense: true,
                            labelText: 'Nama',
                            border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        flex: 3,
                        child: TextField(
                          controller: e.amountController,
                          keyboardType: TextInputType.number,
                          decoration: InputDecoration(
                            isDense: true,
                            prefixText: 'Rp ',
                            border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
                          ),
                        ),
                      ),
                      if (_customEntries.length > 2)
                        IconButton(
                          icon: const Icon(LucideIcons.trash2, size: 18, color: KasiraDS.danger),
                          onPressed: () {
                            setState(() {
                              _customEntries[i].nameController.dispose();
                              _customEntries[i].amountController.dispose();
                              _customEntries.removeAt(i);
                            });
                          },
                        ),
                    ],
                  ),
                );
              }),
              TextButton.icon(
                onPressed: () {
                  setState(() {
                    _customEntries.add(_CustomSplitEntry(
                      nameController: TextEditingController(text: 'Tamu ${_customEntries.length + 1}'),
                      amountController: TextEditingController(text: '0'),
                    ));
                  });
                },
                icon: const Icon(LucideIcons.plus, size: 16),
                label: const Text('Tambah Orang'),
              ),
              // Show total check
              Builder(builder: (context) {
                final customTotal = _customEntries.fold<double>(
                    0, (s, e) => s + (double.tryParse(e.amountController.text) ?? 0));
                final diff = total - customTotal;
                return Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: diff.abs() < 1 ? KasiraDS.success.withOpacity(0.1) : KasiraDS.danger.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(diff.abs() < 1 ? 'Total cocok' : 'Selisih: ${_currency.format(diff.abs())}'),
                      Icon(
                        diff.abs() < 1 ? LucideIcons.checkCircle2 : LucideIcons.alertCircle,
                        color: diff.abs() < 1 ? KasiraDS.success : KasiraDS.danger,
                        size: 20,
                      ),
                    ],
                  ),
                );
              }),
            ],

            if (_error != null) ...[
              const SizedBox(height: 12),
              Text(_error!, style: const TextStyle(color: KasiraDS.danger, fontSize: 13)),
            ],

            const SizedBox(height: 20),
            // Pay-items mode punya tombol bayar sendiri di PayItemsModal —
            // sembunyiin "Konfirmasi Split" biar gak ambigu (nge-trigger 2 flow).
            if (_selectedMethod != 'pay_items')
              SizedBox(
                width: double.infinity,
                height: 56,
                child: FilledButton.icon(
                  onPressed: _isLoading ? null : _submitSplit,
                  icon: _isLoading
                      ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                      : const Icon(LucideIcons.check, size: 18),
                  label: const Text('Konfirmasi Split'),
                  style: FilledButton.styleFrom(backgroundColor: KasiraDS.brandPrimary),
                ),
              ),
          ],
        ),
      ),
    );
  }

  /// Intro section untuk mode "Bayar Sebagian" (warkop pattern Indonesia).
  /// Beda dari 3 mode lain: gak butuh assign tamu / input nominal — kasir tinggal
  /// centang item yg customer mau bayar duluan, sisa unpaid nempel di tab.
  Widget _buildPayItemsIntro() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: KasiraDS.success.withOpacity(0.08),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: KasiraDS.success.withOpacity(0.3)),
          ),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Icon(LucideIcons.lightbulb, color: KasiraDS.success, size: 20),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Cara warkop Indonesia',
                      style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'Centang menu yang dia bayar, langsung bayar. Sisa nempel di tab — '
                      'orang berikutnya nyusul tinggal centang punya dia.',
                      style: TextStyle(color: KasiraDS.textMuted, fontSize: 12.5, height: 1.4),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),
        SizedBox(
          width: double.infinity,
          height: 52,
          child: FilledButton.icon(
            onPressed: _isLoading ? null : _launchPayItems,
            icon: _isLoading
                ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                : const Icon(LucideIcons.checkSquare, size: 20),
            label: const Text(
              'Mulai Pilih Item & Bayar',
              style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold),
            ),
            style: FilledButton.styleFrom(
              backgroundColor: KasiraDS.brandPrimary,
            ),
          ),
        ),
      ],
    );
  }

  /// Load tab items, filter unpaid, close current modal & push PayItemsModal
  /// (warkop pattern). Edge case: kalau semua items udah paid → kasih notice +
  /// fallback ke "Bagi Rata" mode (sisa amount dari paid_via_splits/full).
  Future<void> _launchPayItems() async {
    setState(() { _isLoading = true; _error = null; });
    final items = await ref.read(tabProvider.notifier).getTabItems(widget.tab.id);
    if (!mounted) return;

    final unpaid = items.where((i) => i.paidAt == null).toList();

    if (unpaid.isEmpty) {
      setState(() {
        _isLoading = false;
        _selectedMethod = 'equal';
        _error = 'Semua item sudah dibayar. Sisa tab bisa pakai mode lain.';
      });
      return;
    }

    setState(() => _isLoading = false);
    Navigator.of(context).pop(); // close SplitBillModal
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: KasiraDS.surfaceCard,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (_) => PayItemsModal(
        tab: widget.tab,
        unpaidItems: unpaid,
        onPaid: widget.onSplitDone,
      ),
    );
  }

  Widget _buildMethodChip(String method, String label, IconData icon) {
    final isSelected = _selectedMethod == method;
    return Expanded(
      child: GestureDetector(
        onTap: () {
          setState(() => _selectedMethod = method);
        },
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 150),
          padding: const EdgeInsets.symmetric(vertical: KasiraDS.space4),
          decoration: BoxDecoration(
            gradient: isSelected ? KasiraDS.gradientFrekuensi : null,
            color: isSelected ? null : KasiraDS.surfaceCard,
            borderRadius: KasiraDS.brMd,
            border: Border.all(
                color: isSelected ? Colors.transparent : KasiraDS.borderSubtle, width: 1.5),
            boxShadow: isSelected ? KasiraDS.glowPink : null,
          ),
          child: Column(
            children: [
              Icon(icon, size: 24, color: isSelected ? Colors.white : KasiraDS.textMuted),
              const SizedBox(height: KasiraDS.space2),
              Text(label,
                  textAlign: TextAlign.center,
                  style: KasiraDS.sans(
                    size: 13.5,
                    weight: FontWeight.w700,
                    color: isSelected ? Colors.white : KasiraDS.textMuted,
                  )),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _submitSplit() async {
    setState(() { _isLoading = true; _error = null; });

    TabModel? result;
    final notifier = ref.read(tabProvider.notifier);

    if (_selectedMethod == 'equal') {
      result = await notifier.splitEqual(widget.tab.id, _numPeople, widget.tab.rowVersion);
    } else {
      // Custom
      final splits = _customEntries.map((e) => {
            'label': e.nameController.text.trim().isNotEmpty ? e.nameController.text.trim() : 'Tamu',
            'amount': double.tryParse(e.amountController.text) ?? 0,
          }).toList();
      result = await notifier.splitCustom(widget.tab.id, splits, widget.tab.rowVersion);
    }

    if (mounted) {
      setState(() => _isLoading = false);
      if (result != null) {
        Navigator.pop(context);
        widget.onSplitDone(result);
      } else {
        setState(() => _error = ref.read(tabProvider).error ?? 'Gagal split bill');
      }
    }
  }
}

class _CustomSplitEntry {
  final TextEditingController nameController;
  final TextEditingController amountController;
  _CustomSplitEntry({required this.nameController, required this.amountController});
}
