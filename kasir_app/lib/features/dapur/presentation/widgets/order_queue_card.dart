import 'package:flutter/material.dart';
import 'package:lucide_icons/lucide_icons.dart';
import '../../../../core/theme/app_colors.dart';
import '../../providers/dapur_provider.dart';

class OrderQueueCard extends StatelessWidget {
  final DapurOrder order;
  final VoidCallback? onTap;
  final Future<void> Function(String newStatus)? onStatusChange;

  const OrderQueueCard({
    super.key,
    required this.order,
    this.onTap,
    this.onStatusChange,
  });

  @override
  Widget build(BuildContext context) {
    final (statusColor, statusLabel, statusIcon) = _statusMeta(order.status);
    final elapsed = order.elapsedMinutes;
    final timerColor = order.isUrgent
        ? AppColors.error
        : order.isWarning
            ? AppColors.warning
            : AppColors.textSecondary;

    return GestureDetector(
      onTap: onTap,
      child: Container(
        decoration: BoxDecoration(
          color: AppColors.surface,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: order.isUrgent
                ? AppColors.error.withOpacity(0.5)
                : order.isWarning
                    ? AppColors.warning.withOpacity(0.4)
                    : AppColors.border,
            width: order.isUrgent ? 2 : 1,
          ),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.05),
              blurRadius: 8,
              offset: const Offset(0, 2),
            ),
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Header
            Container(
              padding: const EdgeInsets.fromLTRB(16, 12, 12, 12),
              decoration: BoxDecoration(
                color: statusColor.withOpacity(0.08),
                borderRadius: const BorderRadius.vertical(top: Radius.circular(16)),
              ),
              child: Row(
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                    decoration: BoxDecoration(
                      color: statusColor,
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(statusIcon, size: 12, color: Colors.white),
                        const SizedBox(width: 4),
                        Text(
                          statusLabel,
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 11,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      '#${order.displayNumber}',
                      style: const TextStyle(
                        fontWeight: FontWeight.w800,
                        fontSize: 18,
                        letterSpacing: -0.5,
                      ),
                    ),
                  ),
                  // Timer
                  Row(
                    children: [
                      Icon(LucideIcons.clock, size: 13, color: timerColor),
                      const SizedBox(width: 3),
                      Text(
                        '${elapsed}m',
                        style: TextStyle(
                          color: timerColor,
                          fontSize: 13,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),

            // Order type + table
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 10, 16, 4),
              child: Row(
                children: [
                  Icon(
                    order.orderType == 'Dine In'
                        ? LucideIcons.utensils
                        : LucideIcons.shoppingBag,
                    size: 13,
                    color: AppColors.textSecondary,
                  ),
                  const SizedBox(width: 5),
                  Text(
                    order.orderType,
                    style: const TextStyle(
                      color: AppColors.textSecondary,
                      fontSize: 12,
                    ),
                  ),
                  if (order.tableNumber != null) ...[
                    const SizedBox(width: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(
                        color: AppColors.info.withOpacity(0.1),
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: Text(
                        'Meja ${order.tableNumber}',
                        style: const TextStyle(
                          color: AppColors.info,
                          fontSize: 11,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
                  ],
                ],
              ),
            ),

            // Items
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 4, 16, 8),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: order.items
                    .map((item) => Padding(
                          padding: const EdgeInsets.only(bottom: 3),
                          child: Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                '${item.qty}×',
                                style: const TextStyle(
                                  color: AppColors.primary,
                                  fontWeight: FontWeight.bold,
                                  fontSize: 13,
                                ),
                              ),
                              const SizedBox(width: 6),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      item.productName,
                                      style: const TextStyle(
                                          fontSize: 13, fontWeight: FontWeight.w500),
                                    ),
                                    if (item.notes != null && item.notes!.isNotEmpty)
                                      Text(
                                        item.notes!,
                                        style: const TextStyle(
                                          color: AppColors.warning,
                                          fontSize: 11,
                                          fontStyle: FontStyle.italic,
                                        ),
                                      ),
                                  ],
                                ),
                              ),
                            ],
                          ),
                        ))
                    .toList(),
              ),
            ),

            // Action button
            if (onStatusChange != null)
              Padding(
                padding: const EdgeInsets.fromLTRB(12, 0, 12, 12),
                child: _buildActionButton(context),
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
          height: 40,
          child: ElevatedButton.icon(
            onPressed: () => onStatusChange!('preparing'),
            icon: const Icon(LucideIcons.chefHat, size: 16),
            label: const Text('MULAI MASAK', style: TextStyle(fontWeight: FontWeight.bold)),
            style: ElevatedButton.styleFrom(
              backgroundColor: AppColors.warning,
              foregroundColor: Colors.white,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
            ),
          ),
        );
      case 'preparing':
        return SizedBox(
          height: 40,
          child: ElevatedButton.icon(
            onPressed: () => onStatusChange!('ready'),
            icon: const Icon(LucideIcons.bellRing, size: 16),
            label: const Text('SIAP SAJI', style: TextStyle(fontWeight: FontWeight.bold)),
            style: ElevatedButton.styleFrom(
              backgroundColor: AppColors.success,
              foregroundColor: Colors.white,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
            ),
          ),
        );
      case 'ready':
        return SizedBox(
          height: 40,
          child: OutlinedButton.icon(
            onPressed: () => onStatusChange!('done'),
            icon: const Icon(LucideIcons.checkCircle, size: 16),
            label: const Text('SELESAI', style: TextStyle(fontWeight: FontWeight.bold)),
            style: OutlinedButton.styleFrom(
              foregroundColor: AppColors.success,
              side: const BorderSide(color: AppColors.success),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
            ),
          ),
        );
      default:
        return const SizedBox.shrink();
    }
  }

  static (Color, String, IconData) _statusMeta(String status) {
    switch (status) {
      case 'preparing':
        return (AppColors.warning, 'DIMASAK', LucideIcons.chefHat);
      case 'ready':
        return (AppColors.success, 'SIAP SAJI', LucideIcons.bellRing);
      case 'done':
        return (AppColors.textSecondary, 'SELESAI', LucideIcons.checkCircle);
      default:
        return (AppColors.info, 'ANTRIAN', LucideIcons.listOrdered);
    }
  }
}
