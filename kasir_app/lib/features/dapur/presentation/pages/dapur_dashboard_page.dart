import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:lucide_icons/lucide_icons.dart';
import '../../../../core/theme/app_colors.dart';
import '../../providers/dapur_provider.dart';
import '../widgets/order_queue_card.dart';

class DapurDashboardPage extends ConsumerStatefulWidget {
  const DapurDashboardPage({super.key});

  @override
  ConsumerState<DapurDashboardPage> createState() => _DapurDashboardPageState();
}

class _DapurDashboardPageState extends ConsumerState<DapurDashboardPage>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;
  Timer? _clockTimer;
  DateTime _now = DateTime.now();
  int _prevActiveCount = 0;
  bool _hasNewOrder = false;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(dapurProvider.notifier).startPolling(intervalSeconds: 8);
    });
    _clockTimer = Timer.periodic(const Duration(seconds: 30), (_) {
      if (mounted) setState(() => _now = DateTime.now());
    });
  }

  @override
  void dispose() {
    _tabController.dispose();
    _clockTimer?.cancel();
    ref.read(dapurProvider.notifier).stopPolling();
    super.dispose();
  }

  void _checkNewOrders(int current) {
    if (current > _prevActiveCount && _prevActiveCount != 0) {
      setState(() => _hasNewOrder = true);
      Future.delayed(const Duration(seconds: 4), () {
        if (mounted) setState(() => _hasNewOrder = false);
      });
    }
    _prevActiveCount = current;
  }

  Future<void> _handleStatusChange(DapurOrder order, String newStatus) async {
    final ok =
        await ref.read(dapurProvider.notifier).updateStatus(order, newStatus);
    if (!ok && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Gagal update status. Data di-refresh.'),
          backgroundColor: AppColors.error,
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    // P2 Quick Win #3: pakai ref.listen biar _checkNewOrders fired ONLY on
    // state change (bukan tiap rebuild via addPostFrameCallback). Pre-fix:
    // schedule callback baru tiap polling tick (8s) → potensi infinite
    // rebuild loop kalau setState trigger callback chain.
    ref.listen<DapurState>(dapurProvider, (prev, next) {
      _checkNewOrders(next.activeOrders.length);
    });
    final state = ref.watch(dapurProvider);

    final pendingOrders =
        state.activeOrders.where((o) => o.status == 'pending').toList();
    final preparingOrders =
        state.activeOrders.where((o) => o.status == 'preparing').toList();
    final readyOrders =
        state.activeOrders.where((o) => o.status == 'ready').toList();

    return Scaffold(
      backgroundColor: const Color(0xFF0F0F1A),
      appBar: AppBar(
        backgroundColor: const Color(0xFF1A1A2E),
        elevation: 0,
        titleSpacing: 16,
        title: Row(
          children: [
            const Icon(Icons.kitchen_rounded, color: AppColors.warning, size: 22),
            const SizedBox(width: 8),
            const Text(
              'DAPUR',
              style: TextStyle(
                color: Colors.white,
                fontWeight: FontWeight.w800,
                fontSize: 18,
                letterSpacing: 2,
              ),
            ),
            const Spacer(),
            if (_hasNewOrder)
              Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: AppColors.error,
                  borderRadius: BorderRadius.circular(20),
                ),
                child: const Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(LucideIcons.bellRing, size: 12, color: Colors.white),
                    SizedBox(width: 4),
                    Text(
                      'PESANAN BARU!',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 11,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ],
                ),
              ),
            const SizedBox(width: 8),
            if (state.isLoading)
              const SizedBox(
                width: 16,
                height: 16,
                child: CircularProgressIndicator(
                    color: AppColors.warning, strokeWidth: 2),
              )
            else
              IconButton(
                icon: const Icon(LucideIcons.refreshCw,
                    size: 18, color: Colors.white60),
                onPressed: () =>
                    ref.read(dapurProvider.notifier).fetchOrders(),
              ),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(LucideIcons.clipboardCheck,
                color: Colors.white60, size: 20),
            tooltip: 'Selesai Hari Ini',
            onPressed: () => context.push('/dapur/completed'),
          ),
          IconButton(
            icon: const Icon(LucideIcons.barChart2,
                color: Colors.white60, size: 20),
            tooltip: 'Statistik',
            onPressed: () => context.push('/dapur/statistik'),
          ),
          IconButton(
            icon: const Icon(LucideIcons.settings,
                color: Colors.white60, size: 20),
            tooltip: 'Pengaturan',
            onPressed: () => context.push('/dapur/settings'),
          ),
        ],
        bottom: TabBar(
          controller: _tabController,
          indicatorColor: AppColors.warning,
          labelColor: AppColors.warning,
          unselectedLabelColor: Colors.white38,
          labelStyle:
              const TextStyle(fontWeight: FontWeight.bold, fontSize: 12),
          tabs: [
            Tab(text: 'ANTRIAN (${pendingOrders.length})'),
            Tab(text: 'DIMASAK (${preparingOrders.length})'),
            Tab(text: 'SIAP SAJI (${readyOrders.length})'),
          ],
        ),
      ),
      body: state.error != null
          ? _buildError(state.error!)
          : TabBarView(
              controller: _tabController,
              children: [
                _buildOrderGrid(pendingOrders),
                _buildOrderGrid(preparingOrders),
                _buildOrderGrid(readyOrders),
              ],
            ),
    );
  }

  Widget _buildOrderGrid(List<DapurOrder> orders) {
    if (orders.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(LucideIcons.checkCircle,
                size: 48, color: Colors.white.withOpacity(0.1)),
            const SizedBox(height: 16),
            Text(
              'Tidak ada pesanan',
              style: TextStyle(
                  color: Colors.white.withOpacity(0.3), fontSize: 16),
            ),
          ],
        ),
      );
    }

    return GridView.builder(
      padding: const EdgeInsets.all(16),
      gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
        maxCrossAxisExtent: 320,
        childAspectRatio: 0.72,
        crossAxisSpacing: 12,
        mainAxisSpacing: 12,
      ),
      itemCount: orders.length,
      itemBuilder: (_, i) {
        final order = orders[i];
        return OrderQueueCard(
          order: order,
          onTap: () => _showDetail(context, order),
          onStatusChange: (newStatus) => _handleStatusChange(order, newStatus),
        );
      },
    );
  }

  Widget _buildError(String msg) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(LucideIcons.wifiOff, size: 48, color: AppColors.error),
          const SizedBox(height: 16),
          Text(msg,
              style: const TextStyle(color: Colors.white60, fontSize: 14)),
          const SizedBox(height: 24),
          ElevatedButton(
            onPressed: () =>
                ref.read(dapurProvider.notifier).fetchOrders(),
            style:
                ElevatedButton.styleFrom(backgroundColor: AppColors.warning),
            child: const Text('Coba Lagi'),
          ),
        ],
      ),
    );
  }

  void _showDetail(BuildContext context, DapurOrder order) {
    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      isScrollControlled: true,
      builder: (_) => DapurOrderDetailSheet(
        order: order,
        onStatusChange: (newStatus) => _handleStatusChange(order, newStatus),
      ),
    );
  }
}

class DapurOrderDetailSheet extends StatelessWidget {
  final DapurOrder order;
  final Future<void> Function(String newStatus) onStatusChange;

  const DapurOrderDetailSheet({
    super.key,
    required this.order,
    required this.onStatusChange,
  });

  Color _statusColor(String status) {
    switch (status) {
      case 'preparing':
        return AppColors.warning;
      case 'ready':
        return AppColors.success;
      case 'done':
        return AppColors.textSecondary;
      default:
        return AppColors.info;
    }
  }

  String _statusLabel(String status) {
    switch (status) {
      case 'preparing':
        return 'DIMASAK';
      case 'ready':
        return 'SIAP SAJI';
      case 'done':
        return 'SELESAI';
      default:
        return 'ANTRIAN';
    }
  }

  @override
  Widget build(BuildContext context) {
    final color = _statusColor(order.status);
    final label = _statusLabel(order.status);

    return Container(
      margin: const EdgeInsets.fromLTRB(12, 0, 12, 12),
      decoration: const BoxDecoration(
        color: Color(0xFF1E1E30),
        borderRadius: BorderRadius.all(Radius.circular(24)),
      ),
      child: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            // Handle bar
            Container(
              margin: const EdgeInsets.only(top: 12),
              width: 40,
              height: 4,
              decoration: BoxDecoration(
                color: Colors.white24,
                borderRadius: BorderRadius.circular(2),
              ),
            ),

            Padding(
              padding: const EdgeInsets.all(20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Header
                  Row(
                    children: [
                      Text(
                        '#${order.displayNumber}',
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 24,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                      const SizedBox(width: 12),
                      Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 10, vertical: 4),
                        decoration: BoxDecoration(
                          color: color,
                          borderRadius: BorderRadius.circular(20),
                        ),
                        child: Text(
                          label,
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 11,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ),
                      const Spacer(),
                      Text(
                        '${order.elapsedMinutes} menit lalu',
                        style: TextStyle(
                          color: order.isUrgent
                              ? AppColors.error
                              : Colors.white38,
                          fontSize: 13,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      Icon(
                        order.orderType == 'Dine In'
                            ? LucideIcons.utensils
                            : LucideIcons.shoppingBag,
                        size: 14,
                        color: Colors.white38,
                      ),
                      const SizedBox(width: 6),
                      Text(
                        order.orderType,
                        style: const TextStyle(
                            color: Colors.white38, fontSize: 13),
                      ),
                      if (order.tableNumber != null) ...[
                        const SizedBox(width: 8),
                        Text(
                          '· Meja ${order.tableNumber}',
                          style: const TextStyle(
                            color: AppColors.info,
                            fontSize: 13,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ],
                    ],
                  ),
                  const SizedBox(height: 20),
                  const Text(
                    'ITEM PESANAN',
                    style: TextStyle(
                      color: Colors.white38,
                      fontSize: 11,
                      fontWeight: FontWeight.bold,
                      letterSpacing: 1,
                    ),
                  ),
                  const SizedBox(height: 12),
                  ...order.items.map(
                    (item) => Container(
                      margin: const EdgeInsets.only(bottom: 10),
                      padding: const EdgeInsets.all(14),
                      decoration: BoxDecoration(
                        color: Colors.white.withOpacity(0.05),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Container(
                            width: 32,
                            height: 32,
                            decoration: BoxDecoration(
                              color: AppColors.primary.withOpacity(0.15),
                              borderRadius: BorderRadius.circular(8),
                            ),
                            alignment: Alignment.center,
                            child: Text(
                              '${item.qty}',
                              style: const TextStyle(
                                color: AppColors.primary,
                                fontWeight: FontWeight.bold,
                                fontSize: 16,
                              ),
                            ),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  item.productName,
                                  style: const TextStyle(
                                    color: Colors.white,
                                    fontWeight: FontWeight.w600,
                                    fontSize: 15,
                                  ),
                                ),
                                if (item.notes != null &&
                                    item.notes!.isNotEmpty) ...[
                                  const SizedBox(height: 4),
                                  Row(
                                    children: [
                                      const Icon(LucideIcons.messageSquare,
                                          size: 12, color: AppColors.warning),
                                      const SizedBox(width: 4),
                                      Expanded(
                                        child: Text(
                                          item.notes!,
                                          style: const TextStyle(
                                            color: AppColors.warning,
                                            fontSize: 13,
                                            fontStyle: FontStyle.italic,
                                          ),
                                        ),
                                      ),
                                    ],
                                  ),
                                ],
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),

                  const SizedBox(height: 8),
                  if (order.status != 'done')
                    _buildActionButton(context),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildActionButton(BuildContext context) {
    switch (order.status) {
      case 'pending':
        return SizedBox(
          width: double.infinity,
          height: 50,
          child: ElevatedButton.icon(
            onPressed: () async {
              Navigator.pop(context);
              await onStatusChange('preparing');
            },
            icon: const Icon(LucideIcons.chefHat, size: 18),
            label: const Text('MULAI MASAK',
                style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
            style: ElevatedButton.styleFrom(
              backgroundColor: AppColors.warning,
              foregroundColor: Colors.white,
              shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12)),
            ),
          ),
        );
      case 'preparing':
        return SizedBox(
          width: double.infinity,
          height: 50,
          child: ElevatedButton.icon(
            onPressed: () async {
              Navigator.pop(context);
              await onStatusChange('ready');
            },
            icon: const Icon(LucideIcons.bellRing, size: 18),
            label: const Text('SIAP SAJI',
                style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
            style: ElevatedButton.styleFrom(
              backgroundColor: AppColors.success,
              foregroundColor: Colors.white,
              shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12)),
            ),
          ),
        );
      case 'ready':
        return SizedBox(
          width: double.infinity,
          height: 50,
          child: OutlinedButton.icon(
            onPressed: () async {
              Navigator.pop(context);
              await onStatusChange('done');
            },
            icon: const Icon(LucideIcons.checkCircle, size: 18),
            label: const Text('TANDAI SELESAI',
                style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
            style: OutlinedButton.styleFrom(
              foregroundColor: AppColors.success,
              side: const BorderSide(color: AppColors.success, width: 2),
              shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12)),
            ),
          ),
        );
      default:
        return const SizedBox.shrink();
    }
  }
}
