import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../../../core/config/app_config.dart';

double _toDouble(dynamic v) {
  if (v is num) return v.toDouble();
  return double.tryParse(v.toString()) ?? 0.0;
}

class OrderItemModel {
  final String id;
  final String productId;
  final String productName;
  final int quantity;
  final double unitPrice;
  final double totalPrice;
  final String? notes;

  const OrderItemModel({
    required this.id,
    required this.productId,
    required this.productName,
    required this.quantity,
    required this.unitPrice,
    required this.totalPrice,
    this.notes,
  });

  factory OrderItemModel.fromJson(Map<String, dynamic> json) {
    return OrderItemModel(
      id: json['id'] as String,
      productId: json['product_id'] as String,
      productName: json['product_name'] as String? ?? '',
      quantity: (json['quantity'] as num).toInt(),
      unitPrice: _toDouble(json['unit_price']),
      totalPrice: _toDouble(json['total_price']),
      notes: json['notes'] as String?,
    );
  }
}

class OrderModel {
  final String id;
  final String orderNumber;
  final int displayNumber;
  final String status;
  final String orderType;
  final double totalAmount;
  final double subtotal;
  final double taxAmount;
  final double serviceChargeAmount;
  final double discountAmount;
  final String? tableId;
  final List<OrderItemModel> items;
  final DateTime createdAt;

  const OrderModel({
    required this.id,
    required this.orderNumber,
    required this.displayNumber,
    required this.status,
    required this.orderType,
    required this.totalAmount,
    required this.subtotal,
    required this.taxAmount,
    required this.serviceChargeAmount,
    required this.discountAmount,
    this.tableId,
    required this.items,
    required this.createdAt,
  });

  factory OrderModel.fromJson(Map<String, dynamic> json) {
    return OrderModel(
      id: json['id'] as String,
      orderNumber: json['order_number'] as String? ?? '',
      displayNumber: (json['display_number'] as num?)?.toInt() ?? 0,
      status: json['status'] as String,
      orderType: json['order_type'] as String,
      totalAmount: _toDouble(json['total_amount']),
      subtotal: _toDouble(json['subtotal']),
      taxAmount: _toDouble(json['tax_amount'] ?? 0),
      serviceChargeAmount: _toDouble(json['service_charge_amount'] ?? 0),
      discountAmount: _toDouble(json['discount_amount'] ?? 0),
      tableId: json['table_id'] as String?,
      items: (json['items'] as List? ?? [])
          .map((e) => OrderItemModel.fromJson(e as Map<String, dynamic>))
          .toList(),
      createdAt: DateTime.parse(json['created_at'] as String),
    );
  }

  String get statusLabel {
    switch (status) {
      case 'pending': return 'Diproses';
      case 'preparing': return 'Diproses';
      case 'ready': return 'Siap';
      case 'served': return 'Disajikan';
      case 'completed': return 'Selesai';
      case 'cancelled': return 'Dibatalkan';
      default: return status;
    }
  }

  String get orderTypeLabel {
    switch (orderType) {
      case 'dine_in': return 'Dine In';
      case 'takeaway': return 'Takeaway';
      case 'delivery': return 'Delivery';
      default: return orderType;
    }
  }
}

// ── State ────────────────────────────────────────────────────────────────────

class OrdersState {
  final List<OrderModel> orders;
  final bool isLoading;
  final String? error;
  final String? statusFilter; // null = semua

  const OrdersState({
    this.orders = const [],
    this.isLoading = false,
    this.error,
    this.statusFilter,
  });

  OrdersState copyWith({
    List<OrderModel>? orders,
    bool? isLoading,
    String? error,
    bool clearError = false,
    String? statusFilter,
    bool clearFilter = false,
  }) =>
      OrdersState(
        orders: orders ?? this.orders,
        isLoading: isLoading ?? this.isLoading,
        error: clearError ? null : (error ?? this.error),
        statusFilter: clearFilter ? null : (statusFilter ?? this.statusFilter),
      );
}

// ── Notifier ─────────────────────────────────────────────────────────────────

class OrdersNotifier extends StateNotifier<OrdersState> {
  OrdersNotifier() : super(const OrdersState()) {
    fetch();
  }

  final _storage = const FlutterSecureStorage();

  Future<void> fetch({String? status}) async {
    state = state.copyWith(
      isLoading: true,
      clearError: true,
      statusFilter: status,
      clearFilter: status == null,
    );
    try {
      final results = await Future.wait([
        _storage.read(key: 'access_token'),
        _storage.read(key: 'tenant_id'),
        _storage.read(key: 'outlet_id'),
      ]);
      final token = results[0];
      final tenantId = results[1];
      final outletId = results[2];

      if (outletId == null) {
        state = state.copyWith(isLoading: false, error: 'Outlet tidak ditemukan');
        return;
      }

      final dio = Dio(BaseOptions(
        baseUrl: AppConfig.apiV1,
        connectTimeout: const Duration(seconds: 10),
        receiveTimeout: const Duration(seconds: 10),
      ));

      final params = <String, dynamic>{'outlet_id': outletId, 'limit': 20};
      if (status != null) params['status'] = status;

      final resp = await dio.get(
        '/orders/',
        queryParameters: params,
        options: Options(headers: {
          if (token != null) 'Authorization': 'Bearer $token',
          if (tenantId != null) 'X-Tenant-ID': tenantId,
        }),
      );

      final list = (resp.data['data'] as List)
          .map((e) => OrderModel.fromJson(e as Map<String, dynamic>))
          .toList();
      state = state.copyWith(orders: list, isLoading: false);
    } on DioException catch (e) {
      final msg = e.response?.data?['detail'] ?? 'Gagal memuat pesanan';
      state = state.copyWith(isLoading: false, error: msg.toString());
    } catch (_) {
      state = state.copyWith(isLoading: false, error: 'Terjadi kesalahan');
    }
  }

  Future<bool> updateStatus(String orderId, String newStatus, int rowVersion) async {
    try {
      final results = await Future.wait([
        _storage.read(key: 'access_token'),
        _storage.read(key: 'tenant_id'),
      ]);
      final token = results[0];
      final tenantId = results[1];

      final dio = Dio(BaseOptions(
        baseUrl: AppConfig.apiV1,
        connectTimeout: const Duration(seconds: 10),
        receiveTimeout: const Duration(seconds: 10),
      ));

      await dio.put(
        '/orders/$orderId/status',
        data: {'status': newStatus, 'row_version': rowVersion},
        options: Options(headers: {
          if (token != null) 'Authorization': 'Bearer $token',
          if (tenantId != null) 'X-Tenant-ID': tenantId,
        }),
      );

      // Refresh list
      await fetch(status: state.statusFilter);
      return true;
    } catch (e) {
      final msg = e is DioException
          ? (e.response?.data?['detail'] ?? 'Gagal update status')
          : 'Terjadi kesalahan';
      state = state.copyWith(error: msg.toString());
      return false;
    }
  }
}

final ordersProvider = StateNotifierProvider<OrdersNotifier, OrdersState>(
  (_) => OrdersNotifier(),
);

// ── Detail: FutureProvider.family ────────────────────────────────────────────

final orderDetailProvider = FutureProvider.family<OrderModel, String>((ref, orderId) async {
  const storage = FlutterSecureStorage();
  final token = await storage.read(key: 'access_token');
  final tenantId = await storage.read(key: 'tenant_id');

  final dio = Dio(BaseOptions(
    baseUrl: AppConfig.apiV1,
    connectTimeout: const Duration(seconds: 10),
    receiveTimeout: const Duration(seconds: 10),
  ));

  final resp = await dio.get(
    '/orders/$orderId',
    options: Options(headers: {
      if (token != null) 'Authorization': 'Bearer $token',
      if (tenantId != null) 'X-Tenant-ID': tenantId,
    }),
  );

  return OrderModel.fromJson(resp.data['data'] as Map<String, dynamic>);
});
