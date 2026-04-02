import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:lucide_icons/lucide_icons.dart';
import '../../../../core/theme/app_colors.dart';
import '../../providers/dapur_provider.dart';

class DapurStatistikPage extends ConsumerWidget {
  const DapurStatistikPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final stats = ref.watch(dapurStatsProvider);
    final state = ref.watch(dapurProvider);

    final preparingCount =
        state.activeOrders.where((o) => o.status == 'preparing').length;
    final readyCount =
        state.activeOrders.where((o) => o.status == 'ready').length;

    return Scaffold(
      backgroundColor: const Color(0xFF0F0F1A),
      appBar: AppBar(
        backgroundColor: const Color(0xFF1A1A2E),
        elevation: 0,
        leading: IconButton(
          icon: const Icon(LucideIcons.arrowLeft, color: Colors.white70),
          onPressed: () => context.pop(),
        ),
        title: const Text(
          'Statistik Shift',
          style: TextStyle(
              color: Colors.white, fontWeight: FontWeight.bold, fontSize: 16),
        ),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Summary cards
            Row(
              children: [
                Expanded(
                  child: _StatCard(
                    icon: LucideIcons.clipboardList,
                    label: 'Total Pesanan',
                    value: '${stats.totalOrders}',
                    color: AppColors.info,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: _StatCard(
                    icon: LucideIcons.checkCircle,
                    label: 'Selesai',
                    value: '${stats.completedOrders}',
                    color: AppColors.success,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: _StatCard(
                    icon: LucideIcons.clock,
                    label: 'Rata-rata Waktu',
                    value: '${stats.avgMinutes.toStringAsFixed(1)} mnt',
                    color: AppColors.warning,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: _StatCard(
                    icon: LucideIcons.alertCircle,
                    label: 'Antrian Aktif',
                    value: '${stats.pendingOrders}',
                    color: AppColors.error,
                  ),
                ),
              ],
            ),

            const SizedBox(height: 24),

            // Status breakdown
            const Text(
              'STATUS SAAT INI',
              style: TextStyle(
                color: Colors.white38,
                fontSize: 11,
                fontWeight: FontWeight.bold,
                letterSpacing: 1,
              ),
            ),
            const SizedBox(height: 12),
            _StatusBar(
              label: 'Antrian',
              count: stats.pendingOrders,
              total: stats.totalOrders,
              color: AppColors.info,
            ),
            const SizedBox(height: 8),
            _StatusBar(
              label: 'Sedang Dimasak',
              count: preparingCount,
              total: stats.totalOrders,
              color: AppColors.warning,
            ),
            const SizedBox(height: 8),
            _StatusBar(
              label: 'Siap Saji',
              count: readyCount,
              total: stats.totalOrders,
              color: AppColors.success,
            ),
            const SizedBox(height: 8),
            _StatusBar(
              label: 'Selesai',
              count: stats.completedOrders,
              total: stats.totalOrders,
              color: AppColors.textSecondary,
            ),

            const SizedBox(height: 24),

            // Urgent orders
            if (state.activeOrders.any((o) => o.isUrgent)) ...[
              const Text(
                'PERLU PERHATIAN (>15 MENIT)',
                style: TextStyle(
                  color: AppColors.error,
                  fontSize: 11,
                  fontWeight: FontWeight.bold,
                  letterSpacing: 1,
                ),
              ),
              const SizedBox(height: 12),
              ...state.activeOrders
                  .where((o) => o.isUrgent)
                  .map((o) => Container(
                        margin: const EdgeInsets.only(bottom: 8),
                        padding: const EdgeInsets.all(14),
                        decoration: BoxDecoration(
                          color: AppColors.error.withOpacity(0.08),
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(
                              color: AppColors.error.withOpacity(0.3)),
                        ),
                        child: Row(
                          children: [
                            const Icon(LucideIcons.alertTriangle,
                                size: 16, color: AppColors.error),
                            const SizedBox(width: 10),
                            Text(
                              '#${o.displayNumber}',
                              style: const TextStyle(
                                color: Colors.white,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                            const Spacer(),
                            Text(
                              '${o.elapsedMinutes} menit',
                              style: const TextStyle(
                                  color: AppColors.error,
                                  fontWeight: FontWeight.bold),
                            ),
                          ],
                        ),
                      )),
            ],
          ],
        ),
      ),
    );
  }
}

class _StatCard extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;
  final Color color;

  const _StatCard({
    required this.icon,
    required this.label,
    required this.value,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: color.withOpacity(0.08),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: color.withOpacity(0.2)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, size: 20, color: color),
          const SizedBox(height: 12),
          Text(
            value,
            style: TextStyle(
              color: color,
              fontSize: 28,
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            label,
            style: TextStyle(
              color: Colors.white.withOpacity(0.5),
              fontSize: 12,
            ),
          ),
        ],
      ),
    );
  }
}

class _StatusBar extends StatelessWidget {
  final String label;
  final int count;
  final int total;
  final Color color;

  const _StatusBar({
    required this.label,
    required this.count,
    required this.total,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    final pct = total > 0 ? count / total : 0.0;

    return Row(
      children: [
        SizedBox(
          width: 110,
          child: Text(
            label,
            style: const TextStyle(color: Colors.white60, fontSize: 13),
          ),
        ),
        Expanded(
          child: ClipRRect(
            borderRadius: BorderRadius.circular(4),
            child: LinearProgressIndicator(
              value: pct,
              backgroundColor: Colors.white.withOpacity(0.06),
              valueColor: AlwaysStoppedAnimation(color),
              minHeight: 8,
            ),
          ),
        ),
        const SizedBox(width: 10),
        SizedBox(
          width: 24,
          child: Text(
            '$count',
            style: TextStyle(
              color: color,
              fontSize: 13,
              fontWeight: FontWeight.bold,
            ),
            textAlign: TextAlign.right,
          ),
        ),
      ],
    );
  }
}
