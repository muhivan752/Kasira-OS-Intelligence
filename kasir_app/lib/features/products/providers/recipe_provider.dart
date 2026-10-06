import 'dart:convert';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:drift/drift.dart';
import '../../../core/sync/sync_provider.dart';

class RecipeDetail {
  final String recipeName;
  final double? totalHpp;
  final double sellingPrice;
  final double? marginAmount;
  final double? marginPercent;
  final bool isEstimated;
  final bool needsReview;
  final bool needsSync;
  final List<RecipeIngredientDetail> ingredients;

  const RecipeDetail({
    required this.recipeName,
    required this.totalHpp,
    required this.sellingPrice,
    required this.marginAmount,
    required this.marginPercent,
    required this.ingredients,
    this.isEstimated = false,
    this.needsReview = false,
    this.needsSync = false,
  });
}

class RecipeIngredientDetail {
  final String name;
  final double quantity;
  final String unit;
  final double costPerUnit;
  final double? lineCost;
  final bool isOptional;
  final bool needsReview;

  const RecipeIngredientDetail({
    required this.name,
    required this.quantity,
    required this.unit,
    required this.costPerUnit,
    required this.lineCost,
    this.isOptional = false,
    this.needsReview = false,
  });
}

double _number(Object value) => double.parse(value.toString());

final recipeDetailProvider =
    StreamProvider.autoDispose.family<RecipeDetail?, String>((ref, productId) {
  final db = ref.watch(databaseProvider);
  final query = db.select(db.recipes).join([
    innerJoin(db.products, db.products.id.equalsExp(db.recipes.productId)),
    leftOuterJoin(db.recipeHppSnapshots,
        db.recipeHppSnapshots.recipeId.equalsExp(db.recipes.id)),
  ])
    ..where(db.recipes.productId.equals(productId))
    ..where(db.recipes.isActive.equals(true))
    ..where(db.recipes.isDeleted.equals(false))
    ..where(db.products.isDeleted.equals(false))
    ..orderBy([OrderingTerm.desc(db.recipes.version)])
    ..limit(1);

  // Drift emits after each transaction, including ingredient-only HPP pulls.
  // An open sheet and a previously empty recipe both follow the local cache.
  return query.watch().map((rows) {
    if (rows.isEmpty) return null;
    final row = rows.single;
    final recipe = row.readTable(db.recipes);
    final product = row.readTable(db.products);
    final cached = row.readTableOrNull(db.recipeHppSnapshots);
    final snapshot = cached == null
        ? null
        : jsonDecode(cached.snapshot) as Map<String, dynamic>;
    if (snapshot != null && snapshot['product_id'] != productId) {
      throw const FormatException('Rincian HPP tidak cocok dengan produk');
    }
    final rawTotal = snapshot?['total_cost'];
    final total = rawTotal == null ? null : _number(rawTotal);
    final margin = total == null ? null : product.basePrice - total;
    final details = <RecipeIngredientDetail>[
      for (final ing in snapshot?['ingredients'] ?? [])
        RecipeIngredientDetail(
          name: ing['name'],
          quantity: _number(ing['quantity']),
          unit: ing['unit'],
          costPerUnit: _number(ing['cost_per_unit']),
          lineCost: ing['line_cost'] == null ? null : _number(ing['line_cost']),
          isOptional: ing['is_optional'] ?? false,
          needsReview: ing['needs_review'] ?? false,
        ),
    ];
    return RecipeDetail(
      recipeName: recipe.notes ?? 'Resep v${recipe.version}',
      totalHpp: total,
      sellingPrice: product.basePrice,
      marginAmount: margin,
      marginPercent: margin == null
          ? null
          : product.basePrice > 0
              ? margin / product.basePrice * 100
              : 0,
      isEstimated: recipe.isEstimated || (snapshot?['is_estimated'] ?? false),
      needsReview: snapshot?['needs_review'] ?? false,
      needsSync: cached == null,
      ingredients: details,
    );
  });
});
