import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:lucide_icons/lucide_icons.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/services/session_cache.dart';
import '../../providers/cart_provider.dart';
import '../../providers/pos_mode_provider.dart';

class PosModeSelector extends ConsumerWidget {
  const PosModeSelector({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                color: AppColors.primary.withOpacity(0.1),
                shape: BoxShape.circle,
              ),
              child: const Icon(LucideIcons.store, size: 40, color: AppColors.primary),
            ),
            const SizedBox(height: 24),
            const Text(
              'Pilih Tipe Pesanan',
              style: TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.bold,
                color: AppColors.textPrimary,
              ),
            ),
            const SizedBox(height: 8),
            const Text(
              'Tentukan tipe pesanan untuk memulai',
              style: TextStyle(fontSize: 13, color: AppColors.textSecondary),
            ),
            const SizedBox(height: 32),
            Row(
              children: [
                Expanded(
                  child: _ModeCard(
                    icon: LucideIcons.shoppingBag,
                    label: 'Takeaway',
                    subtitle: 'Bawa pulang',
                    color: AppColors.accent,
                    onTap: () {
                      ref.read(cartProvider.notifier).setOrderType('Takeaway');
                      ref.read(posModeProvider.notifier).state = PosMode.takeaway;
                    },
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: _ModeCard(
                    icon: LucideIcons.utensils,
                    label: 'Dine In',
                    subtitle: 'Makan di tempat',
                    color: AppColors.primary,
                    onTap: () {
                      ref.read(cartProvider.notifier).setOrderType('Dine In');
                      final isPro = SessionCache.instance.isPro;
                      if (isPro) {
                        ref.read(posModeProvider.notifier).state = PosMode.dineInTableSelect;
                      } else {
                        // Starter: no table management, go straight to ordering
                        ref.read(posModeProvider.notifier).state = PosMode.dineInOrdering;
                      }
                    },
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _ModeCard extends StatelessWidget {
  final IconData icon;
  final String label;
  final String subtitle;
  final Color color;
  final VoidCallback onTap;

  const _ModeCard({
    required this.icon,
    required this.label,
    required this.subtitle,
    required this.color,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(16),
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 32, horizontal: 16),
        decoration: BoxDecoration(
          color: color.withOpacity(0.08),
          border: Border.all(color: color.withOpacity(0.3)),
          borderRadius: BorderRadius.circular(16),
        ),
        child: Column(
          children: [
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: color.withOpacity(0.15),
                shape: BoxShape.circle,
              ),
              child: Icon(icon, size: 32, color: color),
            ),
            const SizedBox(height: 16),
            Text(
              label,
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
                color: color,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              subtitle,
              style: const TextStyle(fontSize: 12, color: AppColors.textSecondary),
            ),
          ],
        ),
      ),
    );
  }
}
