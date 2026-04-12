import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:lucide_icons/lucide_icons.dart';
import '../../../../core/theme/app_colors.dart';
import '../../providers/recipe_provider.dart';

class ProductDetailSheet extends ConsumerWidget {
  final String productId;
  final String productName;
  final double sellingPrice;

  const ProductDetailSheet({
    super.key,
    required this.productId,
    required this.productName,
    required this.sellingPrice,
  });

  static void show(BuildContext context, {
    required String productId,
    required String productName,
    required double sellingPrice,
  }) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => ProductDetailSheet(
        productId: productId,
        productName: productName,
        sellingPrice: sellingPrice,
      ),
    );
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final recipeAsync = ref.watch(recipeDetailProvider(productId));
    final currency = NumberFormat.currency(locale: 'id_ID', symbol: 'Rp ', decimalDigits: 0);

    return Container(
      constraints: BoxConstraints(
        maxHeight: MediaQuery.of(context).size.height * 0.7,
      ),
      decoration: const BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Handle bar
          Container(
            margin: const EdgeInsets.only(top: 12),
            width: 40,
            height: 4,
            decoration: BoxDecoration(
              color: AppColors.border,
              borderRadius: BorderRadius.circular(2),
            ),
          ),

          // Header
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 16, 20, 0),
            child: Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        productName,
                        style: const TextStyle(
                          fontWeight: FontWeight.bold,
                          fontSize: 18,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        'Harga jual: ${currency.format(sellingPrice)}',
                        style: const TextStyle(
                          color: AppColors.textSecondary,
                          fontSize: 14,
                        ),
                      ),
                    ],
                  ),
                ),
                IconButton(
                  onPressed: () => Navigator.pop(context),
                  icon: const Icon(LucideIcons.x, size: 20),
                ),
              ],
            ),
          ),

          const Divider(height: 24),

          // Content
          Flexible(
            child: recipeAsync.when(
              loading: () => const Padding(
                padding: EdgeInsets.all(40),
                child: Center(child: CircularProgressIndicator()),
              ),
              error: (err, _) => Padding(
                padding: const EdgeInsets.all(40),
                child: Center(
                  child: Text('Error: $err',
                      style: const TextStyle(color: AppColors.error)),
                ),
              ),
              data: (recipe) {
                if (recipe == null) {
                  return Padding(
                    padding: const EdgeInsets.all(40),
                    child: Center(
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(LucideIcons.chefHat,
                              size: 48, color: AppColors.textTertiary),
                          const SizedBox(height: 12),
                          const Text(
                            'Belum ada resep',
                            style: TextStyle(
                              color: AppColors.textSecondary,
                              fontSize: 15,
                            ),
                          ),
                          const SizedBox(height: 4),
                          const Text(
                            'Tambah resep di dashboard untuk melihat HPP',
                            style: TextStyle(
                              color: AppColors.textTertiary,
                              fontSize: 12,
                            ),
                          ),
                        ],
                      ),
                    ),
                  );
                }

                return SingleChildScrollView(
                  padding: const EdgeInsets.fromLTRB(20, 0, 20, 24),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // HPP Summary Cards
                      Row(
                        children: [
                          _SummaryCard(
                            label: 'HPP',
                            value: currency.format(recipe.totalHpp),
                            icon: LucideIcons.calculator,
                            color: AppColors.primary,
                          ),
                          const SizedBox(width: 12),
                          _SummaryCard(
                            label: 'Margin',
                            value: currency.format(recipe.marginAmount),
                            icon: LucideIcons.trendingUp,
                            color: recipe.marginPercent >= 30
                                ? AppColors.success
                                : recipe.marginPercent >= 15
                                    ? const Color(0xFFF59E0B)
                                    : AppColors.error,
                          ),
                          const SizedBox(width: 12),
                          _SummaryCard(
                            label: 'Margin %',
                            value: '${recipe.marginPercent.toStringAsFixed(1)}%',
                            icon: LucideIcons.percent,
                            color: recipe.marginPercent >= 30
                                ? AppColors.success
                                : recipe.marginPercent >= 15
                                    ? const Color(0xFFF59E0B)
                                    : AppColors.error,
                          ),
                        ],
                      ),

                      const SizedBox(height: 20),

                      // Ingredient breakdown
                      const Text(
                        'Bahan Baku',
                        style: TextStyle(
                          fontWeight: FontWeight.bold,
                          fontSize: 15,
                        ),
                      ),
                      const SizedBox(height: 12),

                      ...recipe.ingredients.map((ing) => _IngredientRow(
                            name: ing.name,
                            quantity: ing.quantity,
                            unit: ing.unit,
                            lineCost: ing.lineCost,
                            currency: currency,
                          )),

                      // Total row
                      Container(
                        margin: const EdgeInsets.only(top: 8),
                        padding: const EdgeInsets.symmetric(
                            horizontal: 12, vertical: 10),
                        decoration: BoxDecoration(
                          color: AppColors.primary.withOpacity(0.06),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            const Text(
                              'Total HPP',
                              style: TextStyle(
                                fontWeight: FontWeight.bold,
                                fontSize: 14,
                              ),
                            ),
                            Text(
                              currency.format(recipe.totalHpp),
                              style: const TextStyle(
                                fontWeight: FontWeight.bold,
                                fontSize: 14,
                                color: AppColors.primary,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

class _SummaryCard extends StatelessWidget {
  final String label;
  final String value;
  final IconData icon;
  final Color color;

  const _SummaryCard({
    required this.label,
    required this.value,
    required this.icon,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: color.withOpacity(0.06),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: color.withOpacity(0.15)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(icon, size: 18, color: color),
            const SizedBox(height: 8),
            Text(
              value,
              style: TextStyle(
                fontWeight: FontWeight.bold,
                fontSize: 15,
                color: color,
              ),
            ),
            const SizedBox(height: 2),
            Text(
              label,
              style: const TextStyle(
                color: AppColors.textSecondary,
                fontSize: 11,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _IngredientRow extends StatelessWidget {
  final String name;
  final double quantity;
  final String unit;
  final double lineCost;
  final NumberFormat currency;

  const _IngredientRow({
    required this.name,
    required this.quantity,
    required this.unit,
    required this.lineCost,
    required this.currency,
  });

  @override
  Widget build(BuildContext context) {
    final qtyStr = quantity % 1 == 0
        ? quantity.toInt().toString()
        : quantity.toStringAsFixed(1);

    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        children: [
          Container(
            width: 6,
            height: 6,
            decoration: BoxDecoration(
              color: AppColors.primary.withOpacity(0.4),
              shape: BoxShape.circle,
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              name,
              style: const TextStyle(fontSize: 13),
            ),
          ),
          Text(
            '$qtyStr $unit',
            style: const TextStyle(
              color: AppColors.textSecondary,
              fontSize: 12,
            ),
          ),
          const SizedBox(width: 16),
          SizedBox(
            width: 80,
            child: Text(
              currency.format(lineCost),
              textAlign: TextAlign.right,
              style: const TextStyle(
                fontWeight: FontWeight.w600,
                fontSize: 13,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
