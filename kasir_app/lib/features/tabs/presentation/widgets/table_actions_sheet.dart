import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
import '../../../../core/config/app_config.dart';
import '../../../../core/services/session_cache.dart';
import '../../../../core/theme/kasira_ds.dart';
import '../../../pos/providers/cart_provider.dart';
import '../../../pos/providers/pos_mode_provider.dart';
import '../../providers/tab_provider.dart';
import 'pay_items_modal.dart';

/// Bottom sheet untuk meja occupied — show items pool + 3 actions.
/// Pattern warkop: kasir tap meja → liat list pesanan + akses cepat ke
/// (1) Tambah Pesanan, (2) Bayar Sebagian (per-item), (3) Lihat Tab Detail.
class TableActionsSheet extends ConsumerStatefulWidget {
  final String tabId;
  final String tableName;
  final String? tableId;

  const TableActionsSheet({
    super.key,
    required this.tabId,
    required this.tableName,
    this.tableId,
  });

  @override
  ConsumerState<TableActionsSheet> createState() => _TableActionsSheetState();
}

class _TableActionsSheetState extends ConsumerState<TableActionsSheet> {
  final _currency = NumberFormat.currency(locale: 'id_ID', symbol: 'Rp ', decimalDigits: 0);
  TabModel? _tab;
  List<TabItemModel> _items = [];
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final cache = SessionCache.instance;
      final dio = Dio(BaseOptions(
        baseUrl: AppConfig.apiV1,
        connectTimeout: const Duration(seconds: 8),
        receiveTimeout: const Duration(seconds: 8),
      ));

      final results = await Future.wait([
        dio.get('/tabs/${widget.tabId}', options: Options(headers: cache.authHeaders)),
        dio.get('/tabs/${widget.tabId}/items', options: Options(headers: cache.authHeaders)),
      ]);

      final tabData = results[0].data['data'] as Map<String, dynamic>?;
      final itemsData = (results[1].data['data'] as List?) ?? [];

      if (mounted) {
        setState(() {
          _tab = tabData != null ? TabModel.fromJson(tabData) : null;
          _items = itemsData.map((e) => TabItemModel.fromJson(e as Map<String, dynamic>)).toList();
          _isLoading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = 'Gagal memuat tab: ${e.toString()}';
          _isLoading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const SizedBox(
        height: 200,
        child: Center(child: CircularProgressIndicator()),
      );
    }
    if (_error != null || _tab == null) {
      return Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(LucideIcons.alertCircle, color: KasiraDS.danger, size: 48),
            const SizedBox(height: 12),
            Text(_error ?? 'Tab tidak ditemukan', style: const TextStyle(color: KasiraDS.danger)),
            const SizedBox(height: 12),
            FilledButton(onPressed: () => Navigator.pop(context), child: const Text('Tutup')),
          ],
        ),
      );
    }

    final tab = _tab!;
    final unpaidItems = _items.where((i) => !i.isPaid).toList();
    final paidCount = _items.length - unpaidItems.length;

    return Padding(
      padding: EdgeInsets.only(
        left: 16, right: 16, top: 16,
        bottom: MediaQuery.of(context).viewInsets.bottom + 16,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header — meja + tab number + status
          Row(
            children: [
              const Icon(LucideIcons.armchair, color: KasiraDS.brandPrimary),
              const SizedBox(width: 8),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(widget.tableName, style: Theme.of(context).textTheme.titleLarge),
                    Text(
                      tab.tabNumber,
                      style: TextStyle(color: KasiraDS.textMuted, fontSize: 12),
                    ),
                  ],
                ),
              ),
              IconButton(onPressed: () => Navigator.pop(context), icon: const Icon(LucideIcons.x)),
            ],
          ),
          const Divider(),

          // Summary status
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: KasiraDS.brandPrimary.withOpacity(0.05),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text('Total bill', style: TextStyle(color: KasiraDS.textMuted, fontSize: 12)),
                    Text(_currency.format(tab.totalAmount),
                        style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
                  ],
                ),
                const SizedBox(height: 4),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text('Sisa belum dibayar', style: TextStyle(color: KasiraDS.textMuted, fontSize: 12)),
                    Text(
                      _currency.format(tab.remainingAmount),
                      style: const TextStyle(
                        fontWeight: FontWeight.bold,
                        fontSize: 16,
                        color: KasiraDS.warning,
                      ),
                    ),
                  ],
                ),
                if (paidCount > 0)
                  Padding(
                    padding: const EdgeInsets.only(top: 4),
                    child: Text(
                      '$paidCount dari ${_items.length} item sudah dibayar',
                      style: TextStyle(color: KasiraDS.success, fontSize: 11),
                    ),
                  ),
              ],
            ),
          ),
          const SizedBox(height: 12),

          // Items list (compact)
          if (_items.isNotEmpty) ...[
            const Text('Pesanan di meja:', style: TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
            const SizedBox(height: 6),
            ConstrainedBox(
              constraints: const BoxConstraints(maxHeight: 180),
              child: ListView.builder(
                shrinkWrap: true,
                itemCount: _items.length,
                itemBuilder: (_, i) {
                  final it = _items[i];
                  return Container(
                    padding: const EdgeInsets.symmetric(vertical: 6, horizontal: 4),
                    decoration: BoxDecoration(
                      border: Border(bottom: BorderSide(color: KasiraDS.borderSubtle.withOpacity(0.3))),
                    ),
                    child: Row(
                      children: [
                        Icon(
                          it.isPaid ? LucideIcons.checkCircle2 : LucideIcons.circleDot,
                          size: 16,
                          color: it.isPaid ? KasiraDS.success : KasiraDS.textMuted,
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            '${it.quantity}x ${it.productName}',
                            style: TextStyle(
                              fontSize: 13,
                              decoration: it.isPaid ? TextDecoration.lineThrough : null,
                              color: it.isPaid ? KasiraDS.textMuted : KasiraDS.textStrong,
                            ),
                          ),
                        ),
                        Text(
                          _currency.format(it.totalPrice),
                          style: TextStyle(
                            fontSize: 13,
                            fontWeight: FontWeight.w600,
                            decoration: it.isPaid ? TextDecoration.lineThrough : null,
                            color: it.isPaid ? KasiraDS.textMuted : KasiraDS.textStrong,
                          ),
                        ),
                      ],
                    ),
                  );
                },
              ),
            ),
            const SizedBox(height: 12),
          ],

          // Action buttons — simplified: "Bayar Semua" jadi aksi utama (1 tap).
          if (unpaidItems.isNotEmpty) ...[
            SizedBox(
              width: double.infinity,
              child: FilledButton.icon(
                onPressed: () => _onPayItems(unpaidItems, preselectAll: true),
                icon: const Icon(LucideIcons.creditCard, size: 18),
                label: Text('Bayar Semua · ${_currency.format(tab.remainingAmount)}'),
                style: FilledButton.styleFrom(
                  backgroundColor: KasiraDS.brandPrimary,
                  padding: const EdgeInsets.symmetric(vertical: 15),
                  textStyle: const TextStyle(fontSize: 15, fontWeight: FontWeight.w800),
                ),
              ),
            ),
            const SizedBox(height: 8),
            // Bayar sebagian (pilih item) — buat split / bayar sebagian aja
            SizedBox(
              width: double.infinity,
              child: OutlinedButton.icon(
                onPressed: () => _onPayItems(unpaidItems, preselectAll: false),
                icon: const Icon(LucideIcons.checkSquare, size: 16),
                label: Text('Bayar sebagian (pilih item · ${unpaidItems.length})'),
                style: OutlinedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 12),
                ),
              ),
            ),
            const SizedBox(height: 8),
          ],
          Row(
            children: [
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: tab.isOpen ? _onAddOrder : null,
                  icon: const Icon(LucideIcons.plus, size: 16),
                  label: const Text('Tambah'),
                  style: OutlinedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(vertical: 12),
                  ),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: _onViewDetail,
                  icon: const Icon(LucideIcons.fileText, size: 16),
                  label: const Text('Detail'),
                  style: OutlinedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(vertical: 12),
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  void _onPayItems(List<TabItemModel> unpaid, {bool preselectAll = false}) {
    Navigator.pop(context); // close sheet
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: KasiraDS.surfaceCard,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (_) => PayItemsModal(
        tab: _tab!,
        unpaidItems: unpaid,
        preselectAll: preselectAll,
        onPaid: (updated) async {
          // Refresh tab provider so other screens reflect change
          await ref.read(tabProvider.notifier).fetchTabs();
        },
      ),
    );
  }

  void _onAddOrder() {
    final tab = _tab!;
    Navigator.pop(context);
    ref.read(cartProvider.notifier).setOrderType('Dine In');
    if (tab.tableId != null) {
      ref.read(cartProvider.notifier).setTable(tab.tableId!, name: tab.tableName);
    }
    ref.read(posModeProvider.notifier).state = PosMode.dineInOrdering;
    ref.read(addOrderContextProvider.notifier).state = AddOrderContext(
      tabId: tab.id,
      tabNumber: tab.tabNumber,
      tableName: tab.tableName,
    );
    ref.read(pendingNavigateToPosProvider.notifier).state = true;
    context.go('/dashboard');
  }

  void _onViewDetail() {
    Navigator.pop(context);
    context.push('/tabs/${widget.tabId}');
  }
}
