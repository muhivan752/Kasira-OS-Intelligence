import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:connectivity_plus/connectivity_plus.dart';
import '../../../core/config/app_config.dart';
import '../../../core/database/app_database.dart';
import '../../../core/sync/sync_provider.dart';

class ProductModel {
  final String id;
  final String name;
  final double price;
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

  ProductModel copyWith({bool? isBestSeller}) {
    return ProductModel(
      id: id,
      name: name,
      price: price,
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
}

class ProductsNotifier extends AsyncNotifier<List<ProductModel>> {
  final _storage = const FlutterSecureStorage();

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
    return rows
        .map((p) => ProductModel(
              id: p.id,
              name: p.name,
              price: p.basePrice,
              stock: p.stockQty.toInt(),
              stockEnabled: p.stockEnabled,
              imageUrl: p.imageUrl,
              categoryId: p.categoryId,
              isAvailable: p.isActive,
              rowVersion: p.rowVersion,
            ))
        .toList();
  }

  Future<List<ProductModel>> _fetchProducts({String? categoryId}) async {
    final online = await _isOnline();
    if (!online) {
      return _fetchFromLocal(categoryId: categoryId);
    }

    try {
      final token = await _storage.read(key: 'access_token');
      final tenantId = await _storage.read(key: 'tenant_id');

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
    final token = await _storage.read(key: 'access_token');
    final tenantId = await _storage.read(key: 'tenant_id');

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
