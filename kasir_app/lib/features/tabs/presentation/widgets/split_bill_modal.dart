import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:lucide_icons/lucide_icons.dart';
import '../../../../core/theme/app_colors.dart';
import '../../providers/tab_provider.dart';

class SplitBillModal extends ConsumerStatefulWidget {
  final TabModel tab;
  final void Function(TabModel updatedTab) onSplitDone;

  const SplitBillModal({super.key, required this.tab, required this.onSplitDone});

  @override
  ConsumerState<SplitBillModal> createState() => _SplitBillModalState();
}

class _SplitBillModalState extends ConsumerState<SplitBillModal> {
  final _currency = NumberFormat.currency(locale: 'id_ID', symbol: 'Rp ', decimalDigits: 0);
  String _selectedMethod = 'equal'; // equal, per_item, custom
  int _numPeople = 2;
  bool _isLoading = false;
  String? _error;

  // Custom split
  final List<_CustomSplitEntry> _customEntries = [];

  // Per-item split
  List<TabItemModel> _items = [];
  bool _loadingItems = false;
  final List<TextEditingController> _guestNameControllers = [];
  // _itemAssignments[itemId] = guest index (0..N-1); -1 = unassigned
  final Map<String, int> _itemAssignments = {};

  @override
  void initState() {
    super.initState();
    _numPeople = widget.tab.guestCount > 1 ? widget.tab.guestCount : 2;
    _initCustomEntries();
    _initGuestControllers();
  }

  void _initGuestControllers() {
    for (final c in _guestNameControllers) { c.dispose(); }
    _guestNameControllers.clear();
    for (int i = 0; i < _numPeople; i++) {
      _guestNameControllers.add(TextEditingController(text: 'Tamu ${i + 1}'));
    }
  }

  Future<void> _loadItems() async {
    if (_items.isNotEmpty || _loadingItems) return;
    setState(() => _loadingItems = true);
    final items = await ref.read(tabProvider.notifier).getTabItems(widget.tab.id);
    if (!mounted) return;
    setState(() {
      _items = items;
      for (final it in items) {
        _itemAssignments[it.id] = -1;
      }
      _loadingItems = false;
    });
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
    for (final c in _guestNameControllers) { c.dispose(); }
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
                const Icon(LucideIcons.split, color: AppColors.primary),
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
                color: AppColors.primary.withOpacity(0.05),
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
            Text('Metode Split', style: TextStyle(color: AppColors.textSecondary, fontSize: 13)),
            const SizedBox(height: 8),
            Row(
              children: [
                _buildMethodChip('equal', 'Bagi Rata', LucideIcons.divide),
                const SizedBox(width: 6),
                _buildMethodChip('per_item', 'Per Item', LucideIcons.listChecks),
                const SizedBox(width: 6),
                _buildMethodChip('custom', 'Custom', LucideIcons.penTool),
              ],
            ),
            const SizedBox(height: 20),

            if (_selectedMethod == 'equal') ...[
              // Equal split
              Text('Jumlah Orang', style: TextStyle(color: AppColors.textSecondary, fontSize: 13)),
              const SizedBox(height: 8),
              Row(
                children: [
                  IconButton.filled(
                    onPressed: _numPeople > 2 ? () => setState(() => _numPeople--) : null,
                    icon: const Icon(LucideIcons.minus, size: 18),
                    style: IconButton.styleFrom(
                      backgroundColor: AppColors.surfaceVariant,
                      foregroundColor: AppColors.textPrimary,
                    ),
                  ),
                  const SizedBox(width: 16),
                  Text('$_numPeople', style: const TextStyle(fontSize: 28, fontWeight: FontWeight.bold)),
                  const SizedBox(width: 16),
                  IconButton.filled(
                    onPressed: _numPeople < 20 ? () => setState(() => _numPeople++) : null,
                    icon: const Icon(LucideIcons.plus, size: 18),
                    style: IconButton.styleFrom(
                      backgroundColor: AppColors.primary.withOpacity(0.1),
                      foregroundColor: AppColors.primary,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: AppColors.surfaceVariant,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Text('Per orang', style: TextStyle(fontSize: 15)),
                    Text(
                      _currency.format(perPerson),
                      style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 20, color: AppColors.primary),
                    ),
                  ],
                ),
              ),
            ] else if (_selectedMethod == 'per_item') ...[
              // Per-item split
              _buildPerItemSection(),
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
                          icon: const Icon(LucideIcons.trash2, size: 18, color: AppColors.error),
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
                    color: diff.abs() < 1 ? AppColors.success.withOpacity(0.1) : AppColors.error.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(diff.abs() < 1 ? 'Total cocok' : 'Selisih: ${_currency.format(diff.abs())}'),
                      Icon(
                        diff.abs() < 1 ? LucideIcons.checkCircle2 : LucideIcons.alertCircle,
                        color: diff.abs() < 1 ? AppColors.success : AppColors.error,
                        size: 20,
                      ),
                    ],
                  ),
                );
              }),
            ],

            if (_error != null) ...[
              const SizedBox(height: 12),
              Text(_error!, style: const TextStyle(color: AppColors.error, fontSize: 13)),
            ],

            const SizedBox(height: 20),
            SizedBox(
              width: double.infinity,
              height: 50,
              child: FilledButton.icon(
                onPressed: _isLoading ? null : _submitSplit,
                icon: _isLoading
                    ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                    : const Icon(LucideIcons.check, size: 18),
                label: const Text('Konfirmasi Split'),
                style: FilledButton.styleFrom(backgroundColor: AppColors.primary),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildMethodChip(String method, String label, IconData icon) {
    final isSelected = _selectedMethod == method;
    return Expanded(
      child: GestureDetector(
        onTap: () {
          setState(() => _selectedMethod = method);
          if (method == 'per_item') _loadItems();
        },
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 12),
          decoration: BoxDecoration(
            color: isSelected ? AppColors.primary.withOpacity(0.1) : AppColors.surface,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: isSelected ? AppColors.primary : AppColors.border, width: 2),
          ),
          child: Column(
            children: [
              Icon(icon, color: isSelected ? AppColors.primary : AppColors.textSecondary),
              const SizedBox(height: 4),
              Text(label, style: TextStyle(
                fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                color: isSelected ? AppColors.primary : AppColors.textSecondary,
                fontSize: 13,
              )),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildPerItemSection() {
    if (_loadingItems) {
      return const Padding(
        padding: EdgeInsets.symmetric(vertical: 20),
        child: Center(child: CircularProgressIndicator()),
      );
    }
    if (_items.isEmpty) {
      return const Padding(
        padding: EdgeInsets.symmetric(vertical: 20),
        child: Center(
          child: Text('Belum ada item di tab ini',
              style: TextStyle(color: AppColors.textSecondary)),
        ),
      );
    }

    // Count per guest (for header chips)
    final perGuestTotal = <int, double>{};
    _items.forEach((item) {
      final g = _itemAssignments[item.id] ?? -1;
      if (g >= 0) {
        perGuestTotal[g] = (perGuestTotal[g] ?? 0) + item.totalPrice;
      }
    });
    final unassignedCount = _items.where((i) => (_itemAssignments[i.id] ?? -1) < 0).length;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Guest count control
        Row(
          children: [
            const Text('Jumlah Orang:', style: TextStyle(fontSize: 13, color: AppColors.textSecondary)),
            const SizedBox(width: 12),
            IconButton.filled(
              onPressed: _numPeople > 2
                  ? () {
                      setState(() {
                        // reassign items using guest >= newCount → unassigned
                        _numPeople--;
                        _initGuestControllers();
                        _itemAssignments.updateAll((_, v) => v >= _numPeople ? -1 : v);
                      });
                    }
                  : null,
              icon: const Icon(LucideIcons.minus, size: 16),
              style: IconButton.styleFrom(
                backgroundColor: AppColors.surfaceVariant,
                foregroundColor: AppColors.textPrimary,
                padding: EdgeInsets.zero,
                minimumSize: const Size(32, 32),
              ),
            ),
            const SizedBox(width: 8),
            Text('$_numPeople', style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            const SizedBox(width: 8),
            IconButton.filled(
              onPressed: _numPeople < 10
                  ? () {
                      setState(() {
                        _numPeople++;
                        _initGuestControllers();
                      });
                    }
                  : null,
              icon: const Icon(LucideIcons.plus, size: 16),
              style: IconButton.styleFrom(
                backgroundColor: AppColors.primary.withOpacity(0.1),
                foregroundColor: AppColors.primary,
                padding: EdgeInsets.zero,
                minimumSize: const Size(32, 32),
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),
        // Guest name editor chips
        Wrap(
          spacing: 6,
          runSpacing: 6,
          children: List.generate(_numPeople, (i) {
            final total = perGuestTotal[i] ?? 0;
            return Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
              decoration: BoxDecoration(
                color: _guestColor(i).withOpacity(0.12),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: _guestColor(i).withOpacity(0.3), width: 1),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Container(
                    width: 8, height: 8,
                    decoration: BoxDecoration(color: _guestColor(i), shape: BoxShape.circle),
                  ),
                  const SizedBox(width: 6),
                  IntrinsicWidth(
                    child: TextField(
                      controller: _guestNameControllers[i],
                      style: TextStyle(fontSize: 12, color: _guestColor(i), fontWeight: FontWeight.w600),
                      decoration: const InputDecoration(
                        isDense: true,
                        border: InputBorder.none,
                        enabledBorder: InputBorder.none,
                        focusedBorder: InputBorder.none,
                        contentPadding: EdgeInsets.zero,
                      ),
                    ),
                  ),
                  if (total > 0) ...[
                    const SizedBox(width: 6),
                    Text('(${_currency.format(total)})',
                        style: TextStyle(fontSize: 11, color: _guestColor(i))),
                  ],
                ],
              ),
            );
          }),
        ),
        const SizedBox(height: 12),
        // Instruction
        Container(
          padding: const EdgeInsets.all(10),
          decoration: BoxDecoration(
            color: AppColors.info.withOpacity(0.08),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Row(
            children: [
              const Icon(LucideIcons.info, size: 14, color: AppColors.info),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  'Tap item → pilih siapa yang bayar. '
                  '${unassignedCount > 0 ? "Sisa $unassignedCount item belum di-assign." : "Semua item sudah di-assign ✓"}',
                  style: const TextStyle(fontSize: 11, color: AppColors.textSecondary),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 10),
        // Item list
        ..._items.map((item) => _buildItemRow(item)),
      ],
    );
  }

  Widget _buildItemRow(TabItemModel item) {
    final guestIdx = _itemAssignments[item.id] ?? -1;
    final assigned = guestIdx >= 0;
    final color = assigned ? _guestColor(guestIdx) : AppColors.textTertiary;

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: InkWell(
        borderRadius: BorderRadius.circular(8),
        onTap: () => _showAssignSheet(item),
        child: Container(
          padding: const EdgeInsets.all(10),
          decoration: BoxDecoration(
            color: assigned ? color.withOpacity(0.06) : AppColors.surfaceVariant,
            borderRadius: BorderRadius.circular(8),
            border: Border.all(
              color: assigned ? color.withOpacity(0.4) : AppColors.border.withOpacity(0.5),
              width: 1,
            ),
          ),
          child: Row(
            children: [
              Container(
                width: 28, height: 28,
                decoration: BoxDecoration(
                  color: color.withOpacity(0.15),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Center(
                  child: assigned
                      ? Text(_guestNameControllers[guestIdx].text.trim().isNotEmpty
                              ? _guestNameControllers[guestIdx].text[0].toUpperCase()
                              : '${guestIdx + 1}',
                          style: TextStyle(color: color, fontSize: 12, fontWeight: FontWeight.bold))
                      : const Icon(LucideIcons.user, size: 14, color: AppColors.textTertiary),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '${item.quantity}× ${item.productName}',
                      style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600),
                    ),
                    if (assigned)
                      Text(
                        _guestNameControllers[guestIdx].text.trim().isNotEmpty
                            ? _guestNameControllers[guestIdx].text
                            : 'Tamu ${guestIdx + 1}',
                        style: TextStyle(fontSize: 11, color: color, fontWeight: FontWeight.w600),
                      )
                    else
                      const Text(
                        'Belum di-assign',
                        style: TextStyle(fontSize: 11, color: AppColors.textTertiary),
                      ),
                  ],
                ),
              ),
              Text(
                _currency.format(item.totalPrice),
                style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600),
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _showAssignSheet(TabItemModel item) {
    showModalBottomSheet(
      context: context,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Siapa yang bayar?',
                style: Theme.of(context).textTheme.titleMedium,
              ),
              const SizedBox(height: 4),
              Text(
                '${item.quantity}× ${item.productName} · ${_currency.format(item.totalPrice)}',
                style: const TextStyle(fontSize: 12, color: AppColors.textSecondary),
              ),
              const SizedBox(height: 16),
              ...List.generate(_numPeople, (i) {
                final name = _guestNameControllers[i].text.trim().isNotEmpty
                    ? _guestNameControllers[i].text
                    : 'Tamu ${i + 1}';
                return ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: CircleAvatar(
                    backgroundColor: _guestColor(i).withOpacity(0.15),
                    radius: 14,
                    child: Text(name[0].toUpperCase(),
                        style: TextStyle(color: _guestColor(i), fontSize: 12, fontWeight: FontWeight.bold)),
                  ),
                  title: Text(name, style: const TextStyle(fontSize: 14)),
                  trailing: (_itemAssignments[item.id] ?? -1) == i
                      ? const Icon(LucideIcons.check, color: AppColors.success, size: 16)
                      : null,
                  onTap: () {
                    setState(() => _itemAssignments[item.id] = i);
                    Navigator.pop(ctx);
                  },
                );
              }),
              if ((_itemAssignments[item.id] ?? -1) >= 0) ...[
                const Divider(height: 20),
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: const Icon(LucideIcons.xCircle, color: AppColors.error, size: 18),
                  title: const Text('Lepas assignment',
                      style: TextStyle(fontSize: 13, color: AppColors.error)),
                  onTap: () {
                    setState(() => _itemAssignments[item.id] = -1);
                    Navigator.pop(ctx);
                  },
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }

  Color _guestColor(int i) {
    const palette = [
      Color(0xFF00D68F), // green
      Color(0xFF3B82F6), // blue
      Color(0xFFF59E0B), // amber
      Color(0xFFEC4899), // pink
      Color(0xFF8B5CF6), // purple
      Color(0xFF06B6D4), // cyan
      Color(0xFFEF4444), // red
      Color(0xFF10B981), // emerald
      Color(0xFFF97316), // orange
      Color(0xFF6366F1), // indigo
    ];
    return palette[i % palette.length];
  }

  Future<void> _submitSplit() async {
    setState(() { _isLoading = true; _error = null; });

    TabModel? result;
    final notifier = ref.read(tabProvider.notifier);

    if (_selectedMethod == 'equal') {
      result = await notifier.splitEqual(widget.tab.id, _numPeople, widget.tab.rowVersion);
    } else if (_selectedMethod == 'per_item') {
      // Validate: every item must be assigned
      final unassigned = _items.where((i) => (_itemAssignments[i.id] ?? -1) < 0).toList();
      if (unassigned.isNotEmpty) {
        setState(() {
          _isLoading = false;
          _error = '${unassigned.length} item belum di-assign ke siapapun';
        });
        return;
      }
      // Group by guest
      final byGuest = <int, List<String>>{};
      for (final item in _items) {
        final g = _itemAssignments[item.id]!;
        byGuest.putIfAbsent(g, () => []).add(item.id);
      }
      final assignments = byGuest.entries.map((e) {
        final name = _guestNameControllers[e.key].text.trim();
        return {
          'label': name.isNotEmpty ? name : 'Tamu ${e.key + 1}',
          'item_ids': e.value,
        };
      }).toList();
      result = await notifier.splitPerItem(widget.tab.id, assignments, widget.tab.rowVersion);
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
