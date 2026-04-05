import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../../../core/config/app_config.dart';

class ProductModel {
  final String id;
  final String name;
  final double price;
  final int stock;
  final String? imageUrl;
  final String? categoryId;
  final String? categoryName;
  final bool isAvailable;
  final int rowVersion;

  const ProductModel({
    required this.id,
    required this.name,
    required this.price,
    required this.stock,
    this.imageUrl,
    this.categoryId,
    this.categoryName,
    this.isAvailable = true,
    this.rowVersion = 0,
  });

  factory ProductModel.fromJson(Map<String, dynamic> json) {
    return ProductModel(
      id: json['id'] as String,
      name: json['name'] as String,
      price: _toDouble(json['price']),
      stock: (json['stock_qty'] as num?)?.toInt() ?? 0,
      imageUrl: json['image_url'] as String?,
      categoryId: json['category_id'] as String?,
      categoryName: json['category_name'] as String?,
      isAvailable: (json['is_active'] as bool?) ?? true,
      rowVersion: (json['row_version'] as num?)?.toInt() ?? 0,
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

  Future<List<ProductModel>> _fetchProducts({String? categoryId}) async {
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

    final items = (response.data['data'] as List)
        .map((e) => ProductModel.fromJson(e as Map<String, dynamic>))
        .toList();
    return items;
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
