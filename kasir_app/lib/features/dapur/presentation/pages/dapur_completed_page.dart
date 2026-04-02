import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:lucide_icons/lucide_icons.dart';
import '../../../../core/theme/app_colors.dart';
import '../../providers/dapur_provider.dart';

class DapurCompletedPage extends ConsumerWidget {
  const DapurCompletedPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(dapurProvider);
    final completed = state.completedOrders;

    return Scaffold(
      backgroundColor: const Color(0xFF0F0F1A),
      appBar: AppBar(
        backgroundColor: const Color(0xFF1A1A2E),
        elevation: 0,
        leading: IconButton(
          icon: const Icon(LucideIcons.arrowLeft, color: Colors.white70),
          onPressed: () => context.pop(),
        ),
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Selesai Hari Ini',
              style: TextStyle(
                  color: Colors.white,
                  fontWeight: FontWeight.bold,
                  fontSize: 16),
            ),
            Text(
              '${completed.length} pesanan',
              style: const TextStyle(color: Colors.white38, fontSize: 12),
            ),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(LucideIcons.refreshCw,
                color: Colors.white38, size: 18),
            onPressed: () => ref.read(dapurProvider.notifier).fetchOrders(),
          ),
          const SizedBox(width: 8),
        ],
      ),
      body: completed.isEmpty
          ? _buildEmpty()
          : ListView.builder(
              padding: const EdgeInsets.all(16),
              itemCount: completed.length,
              itemBuilder: (_, i) => _CompletedTile(order: completed[i]),
            ),
    );
  }

  Widget _buildEmpty() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(LucideIcons.clipboardCheck,
              size: 48, color: Colors.white.withOpacity(0.1)),
          const SizedBox(height: 16),
          Text(
            'Belum ada pesanan selesai',
            style:
                TextStyle(color: Colors.white.withOpacity(0.3), fontSize: 16),
          ),
        ],
      ),
    );
  }
}

class _CompletedTile extends StatelessWidget {
  final DapurOrder order;

  const _CompletedTile({required this.order});

  @override
  Widget build(BuildContext context) {
    final timeStr = DateFormat('HH:mm', 'id_ID')
        .format(order.createdAt.toLocal());
    final itemCount = order.items.fold<int>(0, (sum, item) => sum + item.qty);

    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.04),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: Colors.white.withOpacity(0.08)),
      ),
      child: Row(
        children: [
          Container(
            width: 44,
            height: 44,
            decoration: BoxDecoration(
              color: AppColors.success.withOpacity(0.12),
              borderRadius: BorderRadius.circular(12),
            ),
            alignment: Alignment.center,
            child: const Icon(LucideIcons.checkCircle,
                size: 20, color: AppColors.success),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '#${order.displayNumber}',
                  style: const TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.bold,
                    fontSize: 15,
                  ),
                ),
                const SizedBox(height: 4),
                Row(
                  children: [
                    Icon(
                      order.orderType == 'Dine In'
                          ? LucideIcons.utensils
                          : LucideIcons.shoppingBag,
                      size: 12,
                      color: Colors.white38,
                    ),
                    const SizedBox(width: 4),
                    Text(
                      order.orderType,
                      style: const TextStyle(
                          color: Colors.white38, fontSize: 12),
                    ),
                    if (order.tableNumber != null) ...[
                      Text(
                        '  ·  Meja ${order.tableNumber}',
                        style: const TextStyle(
                            color: AppColors.info, fontSize: 12),
                      ),
                    ],
                  ],
                ),
                const SizedBox(height: 2),
                Text(
                  order.items
                      .map((e) => '${e.qty}× ${e.productName}')
                      .join(', '),
                  style: const TextStyle(
                      color: Colors.white38, fontSize: 11),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ),
          ),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(
                timeStr,
                style: const TextStyle(
                    color: Colors.white60,
                    fontSize: 13,
                    fontWeight: FontWeight.w600),
              ),
              const SizedBox(height: 4),
              Text(
                '$itemCount item',
                style: const TextStyle(
                    color: Colors.white38, fontSize: 11),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
