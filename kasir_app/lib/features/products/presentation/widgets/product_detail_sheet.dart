import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import '../../../../core/theme/kasira_ds.dart';
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

  static void show(
    BuildContext context, {
    required String productId,
    required String productName,
    required double sellingPrice,
  }) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
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
    final currency =
        NumberFormat.currency(locale: 'id_ID', symbol: 'Rp ', decimalDigits: 2);
    final theme = Theme.of(context);
    final ink = theme.colorScheme.onSurface;
    final muted = theme.colorScheme.onSurfaceVariant;
    final accent = theme.brightness == Brightness.dark
        ? KasiraDS.coral400
        : KasiraDS.brandPrimary;

    return SafeArea(
      top: false,
      child: ConstrainedBox(
        constraints: BoxConstraints(
          maxHeight: MediaQuery.sizeOf(context).height * 0.85,
        ),
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Row(
                children: [
                  Expanded(
                      child:
                          Text(productName, style: theme.textTheme.titleLarge)),
                  IconButton(
                    tooltip: 'Tutup rincian HPP',
                    constraints:
                        const BoxConstraints(minWidth: 48, minHeight: 48),
                    onPressed: () => Navigator.pop(context),
                    icon: const Icon(Icons.close),
                  ),
                ],
              ),
              Text(
                  'Harga jual: ${currency.format(recipeAsync.valueOrNull?.sellingPrice ?? sellingPrice)}',
                  style: TextStyle(color: muted)),
              const SizedBox(height: 24),
              recipeAsync.when(
                loading: () => const Padding(
                  padding: EdgeInsets.all(24),
                  child: Column(children: [
                    CircularProgressIndicator(),
                    SizedBox(height: 12),
                    Text('Memuat rincian HPP…'),
                  ]),
                ),
                error: (_, __) => Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('Rincian HPP belum bisa dimuat.'),
                    const SizedBox(height: 12),
                    TextButton(
                      onPressed: () =>
                          ref.invalidate(recipeDetailProvider(productId)),
                      child: const Text('Muat ulang rincian'),
                    ),
                  ],
                ),
                data: (recipe) {
                  if (recipe == null) {
                    return const Text(
                      'Belum ada resep. Tambah resep di dashboard, lalu sinkronkan data.',
                    );
                  }
                  final total = recipe.totalHpp;
                  return Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                          recipe.isEstimated || recipe.needsReview
                              ? 'HPP bahan per porsi (estimasi)'
                              : 'HPP bahan per porsi',
                          style: TextStyle(color: muted)),
                      const SizedBox(height: 8),
                      if (total != null) ...[
                        Text(currency.format(total),
                            style: theme.textTheme.headlineMedium?.copyWith(
                                color: accent, fontWeight: FontWeight.w600)),
                        const SizedBox(height: 12),
                        Text(
                            'Selisih harga jual: ${currency.format(recipe.marginAmount)} '
                            '(${recipe.marginPercent!.toStringAsFixed(1)}%)',
                            style: TextStyle(color: ink)),
                        const SizedBox(height: 8),
                        Text(
                            'Belum termasuk gas, gaji, sewa dan biaya operasional.',
                            style: TextStyle(color: muted)),
                      ] else
                        Text(
                            recipe.needsSync
                                ? 'Sinkronkan data untuk mengambil HPP dari server.'
                                : 'HPP belum lengkap. Periksa satuan bahan di dashboard.',
                            style: TextStyle(color: ink)),
                      if (recipe.isEstimated || recipe.needsReview) ...[
                        const SizedBox(height: 12),
                        const Text(
                            'Ada takaran atau harga perkiraan. Periksa dengan data pembelian nyata.'),
                      ],
                      if (recipe.ingredients.isNotEmpty) ...[
                        const SizedBox(height: 24),
                        Text('Bahan baku', style: theme.textTheme.titleMedium),
                        const SizedBox(height: 12),
                        for (final ing in recipe.ingredients)
                          Padding(
                            padding: const EdgeInsets.only(bottom: 16),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(ing.name,
                                    style: TextStyle(
                                        color: ink,
                                        fontWeight: FontWeight.w600)),
                                const SizedBox(height: 4),
                                Text(
                                    '${NumberFormat('0.########', 'id_ID').format(ing.quantity)} ${ing.unit}',
                                    style: TextStyle(color: muted)),
                                const SizedBox(height: 4),
                                Text(
                                    ing.isOptional
                                        ? 'Opsional, tidak masuk HPP'
                                        : ing.lineCost == null
                                            ? 'Satuan perlu diperiksa'
                                            : currency.format(ing.lineCost),
                                    style: TextStyle(color: ink)),
                                if (ing.needsReview)
                                  Text('Harga perkiraan',
                                      style: TextStyle(color: muted)),
                              ],
                            ),
                          ),
                      ],
                    ],
                  );
                },
              ),
            ],
          ),
        ),
      ),
    );
  }
}
