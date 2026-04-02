import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../../../core/config/app_config.dart';

// ─── Model ───────────────────────────────────────────────────────────────────

class CartItem {
  final String productId;
  final String name;
  final double price;
  int qty;
  String? notes;

  CartItem({
    required this.productId,
    required this.name,
    required this.price,
    this.qty = 1,
    this.notes,
  });

  double get subtotal => price * qty;

  CartItem copyWith({int? qty, String? notes}) => CartItem(
        productId: productId,
        name: name,
        price: price,
        qty: qty ?? this.qty,
        notes: notes ?? this.notes,
      );
}

class CartState {
  final List<CartItem> items;
  final String orderType; // 'Dine In' | 'Takeaway'
  final String? customerId;
  final String? tableId;
  final bool isSubmitting;
  final String? error;
  final String? submittedOrderId;

  const CartState({
    this.items = const [],
    this.orderType = 'Dine In',
    this.customerId,
    this.tableId,
    this.isSubmitting = false,
    this.error,
    this.submittedOrderId,
  });

  double get subtotal => items.fold(0, (s, i) => s + i.subtotal);

  CartState copyWith({
    List<CartItem>? items,
    String? orderType,
    String? customerId,
    String? tableId,
    bool? isSubmitting,
    String? error,
    bool clearError = false,
    String? submittedOrderId,
  }) =>
      CartState(
        items: items ?? this.items,
        orderType: orderType ?? this.orderType,
        customerId: customerId ?? this.customerId,
        tableId: tableId ?? this.tableId,
        isSubmitting: isSubmitting ?? this.isSubmitting,
        error: clearError ? null : (error ?? this.error),
        submittedOrderId: submittedOrderId ?? this.submittedOrderId,
      );
}

// ─── Notifier ────────────────────────────────────────────────────────────────

class CartNotifier extends StateNotifier<CartState> {
  CartNotifier() : super(const CartState());

  final _storage = const FlutterSecureStorage();

  void addItem(CartItem item) {
    final existing = state.items.indexWhere((i) => i.productId == item.productId);
    if (existing >= 0) {
      final updated = List<CartItem>.from(state.items);
      updated[existing] = updated[existing].copyWith(qty: updated[existing].qty + 1);
      state = state.copyWith(items: updated, clearError: true);
    } else {
      state = state.copyWith(items: [...state.items, item], clearError: true);
    }
  }

  void incrementItem(String productId) {
    final updated = state.items.map((i) {
      if (i.productId == productId) return i.copyWith(qty: i.qty + 1);
      return i;
    }).toList();
    state = state.copyWith(items: updated);
  }

  void decrementItem(String productId) {
    final updated = state.items
        .map((i) {
          if (i.productId == productId) return i.copyWith(qty: i.qty - 1);
          return i;
        })
        .where((i) => i.qty > 0)
        .toList();
    state = state.copyWith(items: updated);
  }

  void removeItem(String productId) {
    state = state.copyWith(items: state.items.where((i) => i.productId != productId).toList());
  }

  void setOrderType(String type) => state = state.copyWith(orderType: type);

  void setCustomer(String? customerId) => state = state.copyWith(customerId: customerId);

  void setTable(String? tableId) => state = state.copyWith(tableId: tableId);

  void clearCart() => state = const CartState();

  Future<String?> submitOrder() async {
    if (state.items.isEmpty) return null;
    state = state.copyWith(isSubmitting: true, clearError: true);

    try {
      final token = await _storage.read(key: 'access_token');
      final tenantId = await _storage.read(key: 'tenant_id');
      final outletId = await _storage.read(key: 'outlet_id');

      if (outletId == null || outletId.isEmpty) {
        state = state.copyWith(isSubmitting: false, error: 'Outlet tidak ditemukan. Silakan login ulang.');
        return null;
      }

      final dio = Dio(BaseOptions(
        baseUrl: AppConfig.apiV1,
        connectTimeout: const Duration(seconds: 15),
        receiveTimeout: const Duration(seconds: 15),
      ));

      final response = await dio.post(
        '/orders/',
        options: Options(headers: {
          if (token != null) 'Authorization': 'Bearer $token',
          if (tenantId != null) 'X-Tenant-ID': tenantId,
        }),
        data: {
          'outlet_id': outletId,
          'order_type': state.orderType.toLowerCase().replaceAll(' ', '_'),
          if (state.customerId != null) 'customer_id': state.customerId,
          if (state.tableId != null) 'table_id': state.tableId,
          'items': state.items.map((i) => {
            'product_id': i.productId,
            'quantity': i.qty,
            'unit_price': i.price,
            if (i.notes != null && i.notes!.isNotEmpty) 'notes': i.notes,
          }).toList(),
        },
      );

      final orderId = response.data['data']['id'] as String;
      state = state.copyWith(isSubmitting: false, submittedOrderId: orderId);
      return orderId;
    } on DioException catch (e) {
      final msg = e.response?.data['detail'] ?? 'Gagal membuat pesanan';
      state = state.copyWith(isSubmitting: false, error: msg.toString());
      return null;
    } catch (e) {
      state = state.copyWith(isSubmitting: false, error: 'Terjadi kesalahan sistem');
      return null;
    }
  }
}

final cartProvider = StateNotifierProvider<CartNotifier, CartState>((ref) {
  return CartNotifier();
});
