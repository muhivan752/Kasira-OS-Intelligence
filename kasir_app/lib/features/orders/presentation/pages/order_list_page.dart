import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
import 'package:intl/intl.dart';
import '../../../../core/theme/kasira_ds.dart';
import '../../providers/orders_provider.dart';
import '../widgets/order_detail_modal.dart';

final _currencyFmt = NumberFormat.currency(locale: 'id_ID', symbol: 'Rp ', decimalDigits: 0);

class OrderListPage extends ConsumerStatefulWidget {
  const OrderListPage({super.key});

  @override
  ConsumerState<OrderListPage> createState() => _OrderListPageState();
}

class _OrderListPageState extends ConsumerState<OrderListPage>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;
  String _searchQuery = '';

  static const _tabs = [
    (label: 'Semua', status: null),
    (label: 'Diproses', status: 'pending'),
    (label: 'Selesai', status: 'completed'),
    (label: 'Dibatalkan', status: 'cancelled'),
  ];

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: _tabs.length, vsync: this)
      ..addListener(() {
        if (!_tabController.indexIsChanging) {
          final status = _tabs[_tabController.index].status;
          ref.read(ordersProvider.notifier).fetch(status: status);
        }
      });
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(ordersProvider);
    final isWide = MediaQuery.of(context).size.width >= 600;

    final filtered = _searchQuery.isEmpty
        ? state.orders
        : state.orders
            .where((o) =>
                o.orderNumber.toLowerCase().contains(_searchQuery.toLowerCase()))
            .toList();

    return Scaffold(
      backgroundColor: KasiraDS.bgBase,
      body: Column(
        children: [
          Container(
            padding: EdgeInsets.all(isWide ? 24 : 16),
            color: KasiraDS.surfaceCard,
            child: SafeArea(
              bottom: false,
              child: Row(
                children: [
                  Text('Daftar Pesanan',
                      style: isWide
                          ? Theme.of(context).textTheme.headlineMedium
                          : Theme.of(context).textTheme.titleLarge),
                  const Spacer(),
                  SizedBox(
                    width: isWide ? 300 : 160,
                    child: Container(
                      decoration: BoxDecoration(
                        color: KasiraDS.surfaceSunken,
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: TextField(
                        decoration: const InputDecoration(
                          hintText: 'Cari nomor pesanan...',
                          prefixIcon: Icon(LucideIcons.search,
                              color: KasiraDS.textMuted, size: 18),
                          border: InputBorder.none,
                          contentPadding: EdgeInsets.symmetric(vertical: 10),
                        ),
                        onChanged: (v) => setState(() => _searchQuery = v),
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  IconButton(
                    onPressed: () {
                      final status = _tabs[_tabController.index].status;
                      ref.read(ordersProvider.notifier).fetch(status: status);
                    },
                    icon: const Icon(LucideIcons.refreshCw,
                        color: KasiraDS.textMuted),
                    tooltip: 'Refresh',
                  ),
                ],
              ),
            ),
          ),
          Container(
            color: KasiraDS.surfaceCard,
            child: TabBar(
              controller: _tabController,
              labelColor: KasiraDS.brandPrimary,
              unselectedLabelColor: KasiraDS.textMuted,
              indicatorColor: KasiraDS.brandPrimary,
              tabs: _tabs
                  .map((t) => Tab(text: t.label))
                  .toList(),
            ),
          ),
          Expanded(
            child: state.isLoading
                ? const Center(child: CircularProgressIndicator())
                : state.error != null
                    ? _buildError(state.error!)
                    : filtered.isEmpty
                        ? _buildEmpty()
                        : _buildList(filtered, isWide),
          ),
        ],
      ),
    );
  }

  Widget _buildError(String msg) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(LucideIcons.wifiOff, size: 40, color: KasiraDS.textMuted),
          const SizedBox(height: 12),
          Text(msg, style: const TextStyle(color: KasiraDS.textMuted)),
          const SizedBox(height: 8),
          TextButton(
            onPressed: () {
              final status = _tabs[_tabController.index].status;
              ref.read(ordersProvider.notifier).fetch(status: status);
            },
            child: const Text('Coba lagi'),
          ),
        ],
      ),
    );
  }

  Widget _buildEmpty() {
    return const Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(LucideIcons.clipboardList, size: 40, color: KasiraDS.textMuted),
          SizedBox(height: 12),
          Text('Tidak ada pesanan', style: TextStyle(color: KasiraDS.textMuted)),
        ],
      ),
    );
  }

  Widget _buildList(List<OrderModel> orders, bool isWide) {
    return ListView.builder(
      padding: EdgeInsets.all(isWide ? 24 : 12),
      itemCount: orders.length,
      itemBuilder: (context, index) => _buildOrderCard(orders[index], isWide),
    );
  }

  Widget _buildOrderCard(OrderModel order, bool isWide) {
    final statusColor = switch (order.status) {
      'completed' => KasiraDS.success,
      'cancelled' => KasiraDS.danger,
      'ready' => KasiraDS.info,
      _ => KasiraDS.warning,
    };

    return Container(
      margin: EdgeInsets.only(bottom: isWide ? 16 : 10),
      decoration: BoxDecoration(
        color: KasiraDS.surfaceCard,
        borderRadius: KasiraDS.brLg,
        border: Border.all(color: KasiraDS.borderSubtle),
        boxShadow: KasiraDS.shadowSm,
      ),
      child: Padding(
        padding: EdgeInsets.all(isWide ? 20 : 13),
        child: Row(
          children: [
            Container(
              width: 40,
              height: 40,
              alignment: Alignment.center,
              decoration: BoxDecoration(
                color: KasiraDS.surfaceSunken,
                borderRadius: KasiraDS.brMd,
              ),
              child: const Icon(LucideIcons.receipt, color: KasiraDS.textBody, size: 19),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(order.orderNumber,
                      style: KasiraDS.display(size: isWide ? 16 : 14.5, color: KasiraDS.textStrong)),
                  const SizedBox(height: 3),
                  Text(
                    '${order.orderTypeLabel} · ${order.items.length} item',
                    style: KasiraDS.sans(size: 11.5, color: KasiraDS.textMuted),
                  ),
                ],
              ),
            ),
            Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Text(_currencyFmt.format(order.totalAmount),
                    style: KasiraDS.display(size: isWide ? 16 : 15, color: KasiraDS.textStrong)),
                const SizedBox(height: 4),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(
                    color: statusColor.withOpacity(0.12),
                    borderRadius: KasiraDS.brSm,
                  ),
                  child: Text(order.statusLabel,
                      style: KasiraDS.sans(
                          size: 10.5, weight: FontWeight.w700, color: statusColor)),
                ),
              ],
            ),
            if (isWide) ...[
              const SizedBox(width: 16),
              OutlinedButton(
                onPressed: () => _showDetail(order.id),
                child: const Text('Detail'),
              ),
            ] else ...[
              const SizedBox(width: 8),
              IconButton(
                onPressed: () => _showDetail(order.id),
                icon: const Icon(LucideIcons.eye, size: 18, color: KasiraDS.brandPrimary),
              ),
            ],
          ],
        ),
      ),
    );
  }

  void _showDetail(String orderId) {
    showDialog(
      context: context,
      builder: (_) => OrderDetailModal(orderId: orderId),
    );
  }
}
