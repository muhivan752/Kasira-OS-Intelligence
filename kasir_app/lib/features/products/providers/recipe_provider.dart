import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:drift/drift.dart';
import '../../../core/database/app_database.dart';
import '../../../core/sync/sync_provider.dart';

class RecipeDetail {
  final String recipeName;
  final double totalHpp;
  final double sellingPrice;
  final double marginAmount;
  final double marginPercent;
  final List<RecipeIngredientDetail> ingredients;

  const RecipeDetail({
    required this.recipeName,
    required this.totalHpp,
    required this.sellingPrice,
    required this.marginAmount,
    required this.marginPercent,
    required this.ingredients,
  });
}

class RecipeIngredientDetail {
  final String name;
  final double quantity;
  final String unit;
  final double costPerUnit;
  final double lineCost;

  const RecipeIngredientDetail({
    required this.name,
    required this.quantity,
    required this.unit,
    required this.costPerUnit,
    required this.lineCost,
  });
}

final recipeDetailProvider =
    FutureProvider.family<RecipeDetail?, String>((ref, productId) async {
  final db = ref.read(databaseProvider);

  // Get active recipe for this product
  final recipe = await (db.select(db.recipes)
        ..where((r) =>
            r.productId.equals(productId) &
            r.isActive.equals(true) &
            r.isDeleted.equals(false)))
      .getSingleOrNull();

  if (recipe == null) return null;

  // Get recipe ingredients
  final riList = await (db.select(db.recipeIngredients)
        ..where((ri) =>
            ri.recipeId.equals(recipe.id) & ri.isDeleted.equals(false)))
      .get();

  if (riList.isEmpty) return null;

  // Get all ingredient IDs
  final ingredientIds = riList.map((ri) => ri.ingredientId).toList();

  // Fetch ingredients
  final ingredientRows = await (db.select(db.ingredients)
        ..where((i) => i.id.isIn(ingredientIds) & i.isDeleted.equals(false)))
      .get();

  final ingredientMap = {for (var i in ingredientRows) i.id: i};

  // Calculate HPP
  double totalHpp = 0;
  final details = <RecipeIngredientDetail>[];

  for (final ri in riList) {
    final ing = ingredientMap[ri.ingredientId];
    if (ing == null) continue;

    final lineCost = ri.quantity * ing.costPerBaseUnit;
    totalHpp += lineCost;

    details.add(RecipeIngredientDetail(
      name: ing.name,
      quantity: ri.quantity,
      unit: ri.quantityUnit,
      costPerUnit: ing.costPerBaseUnit,
      lineCost: lineCost,
    ));
  }

  // Get selling price from product
  final product = await (db.select(db.products)
        ..where((p) => p.id.equals(productId)))
      .getSingleOrNull();

  final sellingPrice = product?.basePrice ?? 0;
  final marginAmount = sellingPrice - totalHpp;
  final marginPercent = sellingPrice > 0 ? (marginAmount / sellingPrice) * 100 : 0;

  return RecipeDetail(
    recipeName: recipe.notes ?? 'Resep v${recipe.version}',
    totalHpp: totalHpp,
    sellingPrice: sellingPrice,
    marginAmount: marginAmount,
    marginPercent: marginPercent.toDouble(),
    ingredients: details,
  );
});
