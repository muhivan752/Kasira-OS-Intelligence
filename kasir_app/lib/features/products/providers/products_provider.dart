import 'dart:math' as math;
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:dio/dio.dart';
import 'package:connectivity_plus/connectivity_plus.dart';
import '../../../core/config/app_config.dart';
import '../../../core/database/app_database.dart';
import '../../../core/sync/sync_provider.dart';
import '../../../core/services/session_cache.dart';

class ProductModel {
  final String id;
  final String name;
  final double price;
  final double? buyPrice;
  final int stock;
  final bool stockEnabled;
  final String? imageUrl;
  final String? categoryId;
  final String? categoryName;
  final bool isAvailable;
  final int rowVersion;
  final int soldTotal;
  final bool isBestSeller;

  const ProductModel({
    required this.id,
    required this.name,
    required this.price,
    this.buyPrice,
    required this.stock,
    this.stockEnabled = false,
    this.imageUrl,
    this.categoryId,
    this.categoryName,
    this.isAvailable = true,
    this.rowVersion = 0,
    this.soldTotal = 0,
    this.isBestSeller = false,
  });

  /// Margin per unit (Rp). Null kalau buyPrice belum diisi.
  double? get margin => buyPrice == null ? null : price - buyPrice!;

  /// Margin percentage (0-100). Null kalau buyPrice belum diisi atau price=0.
  double? get marginPct =>
      (buyPrice == null || price <= 0) ? null : ((price - buyPrice!) / price) * 100;

  ProductModel copyWith({bool? isBestSeller}) {
    return ProductModel(
      id: id,
      name: name,
      price: price,
      buyPrice: buyPrice,
      stock: stock,
      stockEnabled: stockEnabled,
      imageUrl: imageUrl,
      categoryId: categoryId,
      categoryName: categoryName,
      isAvailable: isAvailable,
      rowVersion: rowVersion,
      soldTotal: soldTotal,
      isBestSeller: isBestSeller ?? this.isBestSeller,
    );
  }

  factory ProductModel.fromJson(Map<String, dynamic> json) {
    return ProductModel(
      id: json['id'] as String,
      name: json['name'] as String,
      price: _toDouble(json['price']),
      // buy_price bisa null (kebanyakan produk legacy belum diisi),
      // bisa string Decimal "8500.00", atau num.
      buyPrice: _toDoubleOrNull(json['buy_price']),
      stock: (json['stock_qty'] as num?)?.toInt() ?? 0,
      stockEnabled: (json['stock_enabled'] as bool?) ?? false,
      imageUrl: json['image_url'] as String?,
      categoryId: json['category_id'] as String?,
      categoryName: json['category_name'] as String?,
      isAvailable: (json['is_active'] as bool?) ?? true,
      rowVersion: (json['row_version'] as num?)?.toInt() ?? 0,
      soldTotal: (json['sold_total'] as num?)?.toInt() ?? 0,
    );
  }

  static double _toDouble(dynamic v) {
    if (v is num) return v.toDouble();
    return double.tryParse(v.toString()) ?? 0.0;
  }

  /// Parse num/string ke double, return null kalau v null atau gagal parse.
  /// Beda dari _toDouble yang fallback ke 0.0 — disini kita perlu bedakan
  /// "belum diisi" (null) vs "0" (free product / loss leader).
  static double? _toDoubleOrNull(dynamic v) {
    if (v == null) return null;
    if (v is num) return v.toDouble();
    final s = v.toString();
    if (s.isEmpty) return null;
    return double.tryParse(s);
  }
}

class ProductsNotifier extends AsyncNotifier<List<ProductModel>> {

  @override
  Future<List<ProductModel>> build() async {
    return _fetchProducts();
  }

  Future<bool> _isOnline() async {
    final result = await Connectivity().checkConnectivity();
    return result.isNotEmpty && !result.contains(ConnectivityResult.none);
  }

  /// Load products dari lokal Drift DB (fallback offline)
  Future<List<ProductModel>> _fetchFromLocal({String? categoryId}) async {
    final db = ref.read(databaseProvider);
    var query = db.select(db.products)
      ..where((p) => p.isDeleted.equals(false));
    if (categoryId != null && categoryId != 'all') {
      query = query..where((p) => p.categoryId.equals(categoryId));
    }
    final rows = await query.get();

    // Check stock_mode — if recipe, compute stock from ingredients
    final stockMode = SessionCache.instance.stockMode ?? 'simple';
    Map<String, int> recipeStocks = {};

    if (stockMode == 'recipe') {
      recipeStocks = await _computeRecipeStockLocal(db, rows);
    }

    return rows
        .map((p) {
          final stock = (stockMode == 'recipe' && p.stockEnabled)
              ? recipeStocks[p.id] ?? 0
              : p.stockQty.toInt();
          return ProductModel(
              id: p.id,
              name: p.name,
              price: p.basePrice,
              buyPrice: p.buyPrice,
              stock: stock,
              stockEnabled: p.stockEnabled,
              imageUrl: p.imageUrl,
              categoryId: p.categoryId,
              isAvailable: p.isActive,
              rowVersion: p.rowVersion,
            );
        })
        .toList();
  }

  /// Compute available portions from local ingredient stock + recipes
  Future<Map<String, int>> _computeRecipeStockLocal(
      AppDatabase db, List<ProductLocal> products) async {
    final outletId = SessionCache.instance.outletId ?? '';
    final stockEnabledIds = products.where((p) => p.stockEnabled).map((p) => p.id).toList();
    if (stockEnabledIds.isEmpty) return {};

    // Load active recipes for these products
    final recipes = await (db.select(db.recipes)
          ..where((r) => r.productId.isIn(stockEnabledIds))
          ..where((r) => r.isActive.equals(true))
          ..where((r) => r.isDeleted.equals(false)))
        .get();
    final recipeMap = <String, RecipeLocal>{};
    for (final r in recipes) {
      recipeMap[r.productId] = r;
    }

    // Load recipe ingredients
    final recipeIds = recipes.map((r) => r.id).toList();
    if (recipeIds.isEmpty) return {};
    final rawRiList = await (db.select(db.recipeIngredients)
          ..where((ri) => ri.recipeId.isIn(recipeIds))
          ..where((ri) => ri.isDeleted.equals(false))
          ..where((ri) => ri.isOptional.equals(false)))
        .get();

    // Filter out recipe_ingredients that reference deleted ingredients (ghost stock guard)
    final allIngIds = rawRiList.map((ri) => ri.ingredientId).toSet().toList();
    if (allIngIds.isEmpty) return {};
    final activeIngs = await (db.select(db.ingredients)
          ..where((i) => i.id.isIn(allIngIds))
          ..where((i) => i.isDeleted.equals(false)))
        .get();
    final activeIngIds = activeIngs.map((i) => i.id).toSet();
    final riList = rawRiList.where((ri) => activeIngIds.contains(ri.ingredientId)).toList();

    // Collect ingredient IDs and load outlet stocks
    final ingredientIds = riList.map((ri) => ri.ingredientId).toSet().toList();
    if (ingredientIds.isEmpty) return {};
    final stocks = await (db.select(db.outletStocks)
          ..where((os) => os.outletId.equals(outletId))
          ..where((os) => os.ingredientId.isIn(ingredientIds))
          ..where((os) => os.isDeleted.equals(false)))
        .get();
    final stockMap = <String, double>{};
    for (final s in stocks) {
      stockMap[s.ingredientId] = s.computedStock;
    }

    // Group recipe ingredients by recipe
    final riByRecipe = <String, List<RecipeIngredientLocal>>{};
    for (final ri in riList) {
      riByRecipe.putIfAbsent(ri.recipeId, () => []).add(ri);
    }

    // Compute min portions per product
    final result = <String, int>{};
    for (final pid in stockEnabledIds) {
      final recipe = recipeMap[pid];
      if (recipe == null) {
        result[pid] = 0;
        continue;
      }
      final ingredients = riByRecipe[recipe.id];
      if (ingredients == null || ingredients.isEmpty) {
        result[pid] = 0;
        continue;
      }
      double minPortions = double.infinity;
      for (final ri in ingredients) {
        if (ri.quantity <= 0) continue;
        final available = stockMap[ri.ingredientId] ?? 0.0;
        minPortions = math.min(minPortions, available / ri.quantity);
      }
      result[pid] = minPortions == double.infinity ? 0 : math.max(0, minPortions.floor());
    }
    return result;
  }

  Future<List<ProductModel>> _fetchProducts({String? categoryId}) async {
    final online = await _isOnline();
    if (!online) {
      return _fetchFromLocal(categoryId: categoryId);
    }

    try {
      final c = SessionCache.instance;
      final token = c.accessToken;
      final tenantId = c.tenantId;

      final dio = Dio(BaseOptions(
        baseUrl: AppConfig.apiV1,
        connectTimeout: const Duration(seconds: 10),
        receiveTimeout: const Duration(seconds: 10),
      ));

      final queryParams = <String, dynamic>{
        if (categoryId != null && categoryId != 'all') 'category_id': categoryId,
      };

      final response = await dio.get(
        '/products/',
        queryParameters: queryParams,
        options: Options(headers: {
          if (token != null) 'Authorization': 'Bearer $token',
          if (tenantId != null) 'X-Tenant-ID': tenantId,
        }),
      );

      var items = (response.data['data'] as List)
          .map((e) => ProductModel.fromJson(e as Map<String, dynamic>))
          .toList();

      // Mark top 3 by sold_total as best sellers
      final sorted = [...items]..sort((a, b) => b.soldTotal.compareTo(a.soldTotal));
      final bestSellerIds = sorted
          .where((p) => p.soldTotal > 0)
          .take(3)
          .map((p) => p.id)
          .toSet();
      items = items.map((p) =>
          bestSellerIds.contains(p.id) ? p.copyWith(isBestSeller: true) : p
      ).toList();

      return items;
    } catch (_) {
      // Network error — fallback ke lokal
      return _fetchFromLocal(categoryId: categoryId);
    }
  }

  Future<void> refresh({String? categoryId}) async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(() => _fetchProducts(categoryId: categoryId));
  }

  Future<void> toggleAvailability(String productId, bool newIsActive, int rowVersion) async {
    final c = SessionCache.instance;
    final token = c.accessToken;
    final tenantId = c.tenantId;

    final dio = Dio(BaseOptions(
      baseUrl: AppConfig.apiV1,
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 10),
    ));

    await dio.put(
      '/products/$productId',
      options: Options(headers: {
        if (token != null) 'Authorization': 'Bearer $token',
        if (tenantId != null) 'X-Tenant-ID': tenantId,
      }),
      data: {'is_active': newIsActive, 'row_version': rowVersion},
    );

    await refresh();
  }
}

final productsProvider = AsyncNotifierProvider<ProductsNotifier, List<ProductModel>>(
  ProductsNotifier.new,
);
