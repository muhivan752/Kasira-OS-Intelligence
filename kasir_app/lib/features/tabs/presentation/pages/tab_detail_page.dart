import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
import '../../../../core/services/printer_service.dart';
import '../../../../core/services/tab_receipt_service.dart';
import '../../../../core/theme/kasira_ds.dart';
import '../../../../core/widgets/tab_receipt_sheet.dart';
import '../../providers/tab_provider.dart';
import '../../../tables/presentation/pages/table_grid_page.dart';
import '../../../pos/providers/cart_provider.dart';
import '../../../pos/providers/pos_mode_provider.dart';
import '../widgets/split_bill_modal.dart';
import '../widgets/pay_split_modal.dart';
import '../widgets/tab_header.dart';
import '../widgets/tab_info_card.dart';
import '../widgets/tab_split_card.dart';
import '../widgets/tab_bottom_actions.dart';
import '../widgets/guest_count_sheet.dart';

class TabDetailPage extends ConsumerStatefulWidget {
  final String tabId;
  const TabDetailPage({super.key, required this.tabId});

  @override
  ConsumerState<TabDetailPage> createState() => _TabDetailPageState();
}

class _TabDetailPageState extends ConsumerState<TabDetailPage> {
  final _currency = NumberFormat.currency(locale: 'id_ID', symbol: 'Rp ', decimalDigits: 0);
  TabModel? _tab;
  bool _isLoading = true;

  /// Item pesanan satu meja beserta status bayarnya. Dulu halaman ini cuma
  /// nampilin kartu ringkasan + kartu split, dan area di tengah kosong
  /// melompong — kasir gak bisa lihat meja ini pesan apa, apalagi mana yang
  /// udah dibayar orang pertama waktu pola warkop (bayar sebagian). Daftar
  /// ini yang ngisi ruang itu.
  List<TabItemModel> _items = const [];
  bool _itemsLoading = false;

  @override
  void initState() {
    super.initState();
    _loadTab();
  }

  Future<void> _loadTab() async {
    setState(() => _isLoading = true);
    final notifier = ref.read(tabProvider.notifier);
    final tab = await notifier.getTab(widget.tabId);
    if (mounted) setState(() { _tab = tab; _isLoading = false; });
    await _loadItems();
  }

  Future<void> _loadItems() async {
    if (!mounted) return;
    setState(() => _itemsLoading = true);
    final items = await ref.read(tabProvider.notifier).getTabItems(widget.tabId);
    if (mounted) setState(() { _items = items; _itemsLoading = false; });
  }

  /// Dipanggil tiap tab berubah karena pembayaran / tambah pesanan —
  /// `paid_at` item cuma bisa dibaca ulang dari server.
  void _applyTab(TabModel updated) {
    setState(() => _tab = updated);
    _loadItems();
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return Scaffold(
        backgroundColor: KasiraDS.bgBase,
        appBar: AppBar(title: const Text('Tab Detail')),
        body: const Center(child: CircularProgressIndicator()),
      );
    }

    if (_tab == null) {
      return Scaffold(
        backgroundColor: KasiraDS.bgBase,
        appBar: AppBar(title: const Text('Tab Detail')),
        body: const Center(child: Text('Tab tidak ditemukan')),
      );
    }

    final tab = _tab!;

    return Scaffold(
      backgroundColor: KasiraDS.bgBase,
      body: Column(
        children: [
          TabHeader(
            tab: tab,
            currency: _currency,
            onMoveTable: tab.isOpen ? () => _showMoveTableModal(tab) : null,
          ),
          Expanded(
            child: RefreshIndicator(
              onRefresh: _loadTab,
              child: ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  TabInfoCard(tab: tab),
                  const SizedBox(height: 16),
                  _TabItemsSection(
                    items: _items,
                    loading: _itemsLoading,
                    currency: _currency,
                  ),
                  const SizedBox(height: 16),
                  if (tab.splits.isNotEmpty) ...[
                    Row(
                      children: [
                        const Icon(LucideIcons.split, size: 18, color: KasiraDS.brandPrimary),
                        const SizedBox(width: 8),
                        const Text('Split Bill', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                      ],
                    ),
                    const SizedBox(height: 8),
                    ...tab.splits.map((s) => TabSplitCard(
                      split: s,
                      currency: _currency,
                      onPay: () => _showPaySplitModal(tab, s),
                      onReceipt: s.isPaid ? () => _showSplitReceipt(tab, s) : null,
                    )),
                    const SizedBox(height: 16),
                  ],
                ],
              ),
            ),
          ),
          // `paidAmount > 0` ikut masuk syarat: tab yang udah lunas dulu bikin
          // bar ini ilang total, jadi gak ada lagi pintu ke struk.
          if (tab.isOpen || tab.isSplitting || tab.paidAmount > 0)
            TabBottomActions(
              tab: tab,
              currency: _currency,
              onAddOrder: () {
                // Pre-set POS to dine-in ordering with this table + set context banner
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
                // One-shot signal — dashboard akan switch ke POS tab sekali, lalu clear.
                // Beda dari watch posModeProvider persistent yg bikin user stuck di POS tab.
                ref.read(pendingNavigateToPosProvider.notifier).state = true;

                // POP, bukan go(). `go()` ngeganti SELURUH tumpukan navigasi —
                // halaman ini di-push di atas /dashboard, jadi go('/dashboard')
                // bikin tumpukan tinggal satu route. Pencet back sesudahnya =
                // pop route terakhir = LAYAR HITAM. Pop balik ke /dashboard yang
                // udah ada di bawah, tumpukannya tetap utuh.
                if (context.canPop()) {
                  context.pop();
                } else {
                  context.go('/dashboard');
                }
              },
              onAddGuests: () => _showGuestCountModal(tab),
              onMergeTab: () => _showMergeTabModal(tab),
              onCancel: () => _confirmCancel(tab),
              onPayFull: () => _showPayFullModal(tab),
              onSplitBill: () => _showSplitBillModal(tab),
              onReceipt: () => _showTabReceipt(tab),
            ),
        ],
      ),
    );
  }

  /// Struk satu porsi split — pintu satu-satunya buat orang yang bayar splitnya
  /// sendiri. Riwayat cuma nyimpen struk order penuh, bukan porsi per orang.
  void _showSplitReceipt(TabModel tab, TabSplitModel split) {
    final printer = ref.read(printerProvider.notifier);
    showTabReceiptSheet(
      context,
      title: split.label,
      subtitle: '${tab.tabNumber} · ${_currency.format(split.amount)}',
      onPrint: () => printTabSplitReceipt(printer,
          tabId: tab.id, splitId: split.id),
      waOrderId: tab.orderIds.isEmpty ? null : tab.orderIds.first,
      waPaymentId: split.paymentId,
    );
  }

  /// Struk seluruh tab — satu lembar per order di dalamnya.
  void _showTabReceipt(TabModel tab) {
    final printer = ref.read(printerProvider.notifier);
    showTabReceiptSheet(
      context,
      title: 'Struk ${tab.tabNumber}',
      subtitle: tab.tableName ?? 'Total ${_currency.format(tab.totalAmount)}',
      onPrint: () => printTabFullReceipt(printer, orderIds: tab.orderIds),
      waOrderId: tab.orderIds.isEmpty ? null : tab.orderIds.first,
    );
  }

  void _showSplitBillModal(TabModel tab) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (_) => SplitBillModal(
        tab: tab,
        onSplitDone: _applyTab,
      ),
    );
  }

  void _showPaySplitModal(TabModel tab, TabSplitModel split) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (_) => PaySplitModal(
        tab: tab,
        split: split,
        onPaid: _applyTab,
      ),
    );
  }

  void _showPayFullModal(TabModel tab) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (_) => PaySplitModal(
        tab: tab,
        split: null,
        onPaid: _applyTab,
      ),
    );
  }

  /// Ubah jumlah tamu di tab berjalan (temen nyusul / rombongan pecah).
  /// Angka ini yang dipakai "bagi rata" sebagai default jumlah orang.
  Future<void> _showGuestCountModal(TabModel tab) async {
    final newCount = await showGuestCountSheet(
      context,
      tableName: tab.tableName ?? tab.tabNumber,
      initial: tab.guestCount,
      title: 'Ubah jumlah tamu',
      confirmLabel: 'Simpan',
      confirmIcon: LucideIcons.check,
    );
    if (newCount == null || !mounted) return;
    if (newCount == tab.guestCount) return;

    final updated = await ref
        .read(tabProvider.notifier)
        .updateGuests(tab.id, newCount, tab.rowVersion);
    if (!mounted) return;

    if (updated == null) {
      final err = ref.read(tabProvider).error ?? 'Gagal ubah jumlah tamu';
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(err), backgroundColor: KasiraDS.danger),
      );
      // Backend nolak (mis. split udah kebentuk / row_version basi) — tarik
      // ulang biar layar gak nampilin angka yang gak jadi kesimpan.
      await _loadTab();
      return;
    }

    setState(() => _tab = updated);
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('Jumlah tamu jadi $newCount orang'),
        backgroundColor: KasiraDS.success,
      ),
    );
  }

  void _showMoveTableModal(TabModel tab) {
    showDialog(
      context: context,
      builder: (ctx) => Dialog(
        insetPadding: const EdgeInsets.all(16),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        child: SizedBox(
          width: double.maxFinite,
          height: MediaQuery.of(context).size.height * 0.7,
          child: Column(
            children: [
              Padding(
                padding: const EdgeInsets.all(16),
                child: Row(
                  children: [
                    const Icon(LucideIcons.arrowRightLeft, size: 20),
                    const SizedBox(width: 8),
                    const Text('Pilih Meja Tujuan', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                    const Spacer(),
                    IconButton(icon: const Icon(LucideIcons.x), onPressed: () => Navigator.pop(ctx)),
                  ],
                ),
              ),
              Expanded(
                child: ClipRRect(
                  borderRadius: const BorderRadius.vertical(bottom: Radius.circular(16)),
                  child: TableGridPage(
                    onTableSelected: (table) async {
                      if (table.id == tab.tableId) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(content: Text('Sudah di meja ini'), backgroundColor: KasiraDS.warning),
                        );
                        return;
                      }
                      if (table.status != TableStatus.available) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(
                            content: Text('Meja ${table.name} sedang ${table.status.name}'),
                            backgroundColor: KasiraDS.danger,
                          ),
                        );
                        return;
                      }
                      Navigator.pop(ctx);
                      final result = await ref.read(tabProvider.notifier).moveTable(
                        tab.id, table.id, tab.rowVersion,
                      );
                      if (result != null && mounted) {
                        setState(() => _tab = result);
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(
                            content: Text('Pindah ke Meja ${table.name}'),
                            backgroundColor: KasiraDS.success,
                          ),
                        );
                      }
                    },
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _showMergeTabModal(TabModel tab) async {
    await ref.read(tabProvider.notifier).fetchTabs(status: 'open');
    final allTabs = ref.read(tabProvider).tabs;
    final otherTabs = allTabs.where((t) => t.id != tab.id && t.isOpen).toList();

    if (!mounted) return;
    if (otherTabs.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Tidak ada tab aktif lain untuk digabung'), backgroundColor: KasiraDS.warning),
      );
      return;
    }

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (ctx) => Padding(
        padding: EdgeInsets.only(bottom: MediaQuery.of(ctx).viewInsets.bottom),
        child: Container(
          constraints: BoxConstraints(maxHeight: MediaQuery.of(context).size.height * 0.5),
          padding: const EdgeInsets.all(20),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  const Icon(LucideIcons.merge, color: KasiraDS.warning),
                  const SizedBox(width: 8),
                  const Text('Gabung Tab', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
                  const Spacer(),
                  IconButton(icon: const Icon(LucideIcons.x), onPressed: () => Navigator.pop(ctx)),
                ],
              ),
              const SizedBox(height: 4),
              Text(
                'Pilih tab yang mau digabung ke ${tab.tabNumber}:',
                style: const TextStyle(color: KasiraDS.textMuted, fontSize: 13),
              ),
              const SizedBox(height: 16),
              Flexible(
                child: ListView.builder(
                  shrinkWrap: true,
                  itemCount: otherTabs.length,
                  itemBuilder: (_, i) {
                    final src = otherTabs[i];
                    return Card(
                      elevation: 0,
                      margin: const EdgeInsets.only(bottom: 8),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12),
                        side: BorderSide(color: KasiraDS.borderSubtle),
                      ),
                      child: ListTile(
                        leading: CircleAvatar(
                          backgroundColor: KasiraDS.brandPrimary.withOpacity(0.1),
                          child: const Icon(LucideIcons.receipt, color: KasiraDS.brandPrimary, size: 20),
                        ),
                        title: Text(src.tabNumber, style: const TextStyle(fontWeight: FontWeight.bold)),
                        subtitle: Text(
                          '${src.tableName ?? "Tanpa meja"} — ${_currency.format(src.totalAmount)} — ${src.guestCount} tamu',
                          style: const TextStyle(fontSize: 12),
                        ),
                        trailing: FilledButton(
                          onPressed: () async {
                            Navigator.pop(ctx);
                            final result = await ref.read(tabProvider.notifier).mergeTab(
                              tab.id, src.id, tab.rowVersion,
                            );
                            if (result != null && mounted) {
                              setState(() => _tab = result);
                              ScaffoldMessenger.of(context).showSnackBar(
                                SnackBar(
                                  content: Text('${src.tabNumber} digabung'),
                                  backgroundColor: KasiraDS.success,
                                ),
                              );
                            }
                          },
                          style: FilledButton.styleFrom(
                            backgroundColor: KasiraDS.warning,
                            padding: const EdgeInsets.symmetric(horizontal: 16),
                          ),
                          child: const Text('Gabung', style: TextStyle(fontSize: 13)),
                        ),
                      ),
                    );
                  },
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _confirmCancel(TabModel tab) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: const Text('Batalkan Tab?'),
        content: Text('Tab ${tab.tabNumber} akan dibatalkan. Lanjutkan?'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Tidak')),
          FilledButton(
            onPressed: () async {
              Navigator.pop(ctx);
              final result = await ref.read(tabProvider.notifier).cancelTab(tab.id);
              if (result != null && mounted) {
                setState(() => _tab = result);
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Tab dibatalkan'), backgroundColor: KasiraDS.danger),
                );
              }
            },
            style: FilledButton.styleFrom(backgroundColor: KasiraDS.danger),
            child: const Text('Batalkan'),
          ),
        ],
      ),
    );
  }
}


/// Daftar pesanan meja, dikelompokkan: yang belum dibayar di atas (itu yang
/// masih jadi urusan kasir), yang udah lunas di bawah dengan tanda centang.
class _TabItemsSection extends StatelessWidget {
  final List<TabItemModel> items;
  final bool loading;
  final NumberFormat currency;

  const _TabItemsSection({
    required this.items,
    required this.loading,
    required this.currency,
  });

  @override
  Widget build(BuildContext context) {
    final unpaid = items.where((i) => !i.isPaid).toList();
    final paid = items.where((i) => i.isPaid).toList();
    final totalQty = items.fold<int>(0, (sum, i) => sum + i.quantity);

    return Container(
      padding: const EdgeInsets.all(KasiraDS.space4),
      decoration: BoxDecoration(
        color: KasiraDS.surfaceCard,
        borderRadius: KasiraDS.brLg,
        border: Border.all(color: KasiraDS.borderSubtle),
        boxShadow: KasiraDS.shadowXs,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(LucideIcons.utensils, size: 18, color: KasiraDS.brandPrimary),
              const SizedBox(width: KasiraDS.space2),
              Text('Pesanan Meja',
                  style: KasiraDS.sans(
                      size: 15, weight: FontWeight.w700, color: KasiraDS.textStrong)),
              const Spacer(),
              if (items.isNotEmpty)
                Text('$totalQty item',
                    style: KasiraDS.sans(size: 12.5, color: KasiraDS.textMuted)),
            ],
          ),
          const SizedBox(height: KasiraDS.space3),
          if (loading && items.isEmpty)
            const Padding(
              padding: EdgeInsets.symmetric(vertical: KasiraDS.space4),
              child: Center(
                child: SizedBox(
                  width: 20,
                  height: 20,
                  child: CircularProgressIndicator(strokeWidth: 2),
                ),
              ),
            )
          else if (items.isEmpty)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: KasiraDS.space3),
              child: Text(
                'Belum ada pesanan. Tap "Tambah Pesanan" di bawah.',
                style: KasiraDS.sans(size: 13, color: KasiraDS.textMuted),
              ),
            )
          else ...[
            ...unpaid.map((i) => _ItemRow(item: i, currency: currency)),
            if (paid.isNotEmpty) ...[
              if (unpaid.isNotEmpty) ...[
                const SizedBox(height: KasiraDS.space2),
                Row(
                  children: [
                    const Icon(LucideIcons.checkCheck, size: 14, color: KasiraDS.success),
                    const SizedBox(width: 6),
                    Text('Sudah dibayar',
                        style: KasiraDS.sans(
                            size: 12, weight: FontWeight.w700, color: KasiraDS.success)),
                  ],
                ),
                const SizedBox(height: KasiraDS.space1),
              ],
              ...paid.map((i) => _ItemRow(item: i, currency: currency)),
            ],
          ],
        ],
      ),
    );
  }
}

class _ItemRow extends StatelessWidget {
  final TabItemModel item;
  final NumberFormat currency;

  const _ItemRow({required this.item, required this.currency});

  @override
  Widget build(BuildContext context) {
    final paid = item.isPaid;
    final textColor = paid ? KasiraDS.textMuted : KasiraDS.textStrong;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 30,
            height: 30,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              color: paid
                  ? KasiraDS.success.withOpacity(0.12)
                  : KasiraDS.brandPrimary.withOpacity(0.08),
              borderRadius: KasiraDS.brSm,
            ),
            child: paid
                ? const Icon(LucideIcons.check, size: 15, color: KasiraDS.success)
                : Text('${item.quantity}×',
                    style: KasiraDS.sans(
                        size: 12.5,
                        weight: FontWeight.w800,
                        color: KasiraDS.brandPrimary)),
          ),
          const SizedBox(width: KasiraDS.space3),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  item.productName,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: KasiraDS.sans(
                    size: 14,
                    weight: FontWeight.w600,
                    color: textColor,
                  ).copyWith(
                    decoration: paid ? TextDecoration.lineThrough : null,
                    decorationColor: KasiraDS.textMuted,
                  ),
                ),
                if (paid || (item.notes != null && item.notes!.trim().isNotEmpty))
                  Text(
                    paid
                        ? '${item.quantity} × ${currency.format(item.unitPrice)}'
                        : item.notes!.trim(),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: KasiraDS.sans(size: 12, color: KasiraDS.textMuted),
                  ),
              ],
            ),
          ),
          const SizedBox(width: KasiraDS.space2),
          Text(
            currency.format(item.totalPrice),
            style: KasiraDS.sans(size: 14, weight: FontWeight.w700, color: textColor),
          ),
        ],
      ),
    );
  }
}
