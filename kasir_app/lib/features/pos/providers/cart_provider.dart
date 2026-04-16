import 'package:drift/drift.dart' as drift;
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:dio/dio.dart';
import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:uuid/uuid.dart';
import '../../../core/config/app_config.dart';
import '../../../core/database/app_database.dart';
import '../../../core/sync/sync_provider.dart';
import '../../../core/utils/pn_counter.dart';
import '../../../core/services/session_cache.dart';
import 'tax_config_provider.dart';

// ─── Model ───────────────────────────────────────────────────────────────────

class CartItem {
  final String productId;
  final String name;
  final double price;
  final double? stockQty; // null = stok tidak diaktifkan
  int qty;
  String? notes;

  CartItem({
    required this.productId,
    required this.name,
    required this.price,
    this.stockQty,
    this.qty = 1,
    this.notes,
  });

  double get subtotal => price * qty;

  CartItem copyWith({int? qty, String? notes}) => CartItem(
        productId: productId,
        name: name,
        price: price,
        stockQty: stockQty,
        qty: qty ?? this.qty,
        notes: notes ?? this.notes,
      );
}

class CartState {
  final List<CartItem> items;
  final String orderType;
  final String? customerId;
  final String? customerName;
  final String? tableId;
  final String? tableName;
  final bool isSubmitting;
  final String? error;
  final String? submittedOrderId;
  final bool wasOffline;
  final double discountAmount;
  final double taxAmount;
  final double serviceChargeAmount;
  final bool taxInclusive;

  const CartState({
    this.items = const [],
    this.orderType = 'Dine In',
    this.customerId,
    this.customerName,
    this.tableId,
    this.tableName,
    this.isSubmitting = false,
    this.error,
    this.submittedOrderId,
    this.wasOffline = false,
    this.discountAmount = 0,
    this.taxAmount = 0,
    this.serviceChargeAmount = 0,
    this.taxInclusive = false,
  });

  double get subtotal => items.fold(0, (s, i) => s + i.subtotal);

  double get total {
    if (taxInclusive) {
      // Price already includes tax — add service charge, subtract discount
      return subtotal + serviceChargeAmount - discountAmount;
    }
    return subtotal + taxAmount + serviceChargeAmount - discountAmount;
  }

  CartState copyWith({
    List<CartItem>? items,
    String? orderType,
    String? customerId,
    String? customerName,
    bool clearCustomer = false,
    String? tableId,
    String? tableName,
    bool clearTable = false,
    bool? isSubmitting,
    String? error,
    bool clearError = false,
    String? submittedOrderId,
    bool? wasOffline,
    double? discountAmount,
    double? taxAmount,
    double? serviceChargeAmount,
    bool? taxInclusive,
  }) =>
      CartState(
        items: items ?? this.items,
        orderType: orderType ?? this.orderType,
        customerId: clearCustomer ? null : (customerId ?? this.customerId),
        customerName: clearCustomer ? null : (customerName ?? this.customerName),
        tableId: clearTable ? null : (tableId ?? this.tableId),
        tableName: clearTable ? null : (tableName ?? this.tableName),
        isSubmitting: isSubmitting ?? this.isSubmitting,
        error: clearError ? null : (error ?? this.error),
        submittedOrderId: submittedOrderId ?? this.submittedOrderId,
        wasOffline: wasOffline ?? this.wasOffline,
        discountAmount: discountAmount ?? this.discountAmount,
        taxAmount: taxAmount ?? this.taxAmount,
        serviceChargeAmount: serviceChargeAmount ?? this.serviceChargeAmount,
        taxInclusive: taxInclusive ?? this.taxInclusive,
      );
}

// ─── Notifier ────────────────────────────────────────────────────────────────

class CartNotifier extends StateNotifier<CartState> {
  final AppDatabase _db;
  TaxConfig? _taxConfig;
  CartNotifier(this._db) : super(const CartState());

  void setTaxConfig(TaxConfig config) {
    _taxConfig = config;
    _recalcCharges();
  }

  void _recalcCharges() {
    final cfg = _taxConfig;
    if (cfg == null) return;
    final taxable = state.subtotal - state.discountAmount;
    state = state.copyWith(
      taxAmount: cfg.calcTax(taxable),
      serviceChargeAmount: cfg.calcServiceCharge(taxable),
      taxInclusive: cfg.taxInclusive,
    );
  }

  SessionCache get _cache => SessionCache.instance;
  static const _uuid = Uuid();

  String _generateUuid() => _uuid.v4();

  void addItem(CartItem item) {
    final existing = state.items.indexWhere((i) => i.productId == item.productId);
    if (existing >= 0) {
      final updated = List<CartItem>.from(state.items);
      updated[existing] = updated[existing].copyWith(qty: updated[existing].qty + 1);
      state = state.copyWith(items: updated, clearError: true);
    } else {
      state = state.copyWith(items: [...state.items, item], clearError: true);
    }
    _recalcCharges();
  }

  void incrementItem(String productId) {
    final updated = state.items.map((i) {
      if (i.productId == productId) return i.copyWith(qty: i.qty + 1);
      return i;
    }).toList();
    state = state.copyWith(items: updated);
    _recalcCharges();
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
    _recalcCharges();
  }

  void removeItem(String productId) {
    state = state.copyWith(
        items: state.items.where((i) => i.productId != productId).toList());
    _recalcCharges();
  }

  void setOrderType(String type) {
    state = state.copyWith(orderType: type);
    // Clear table when switching to takeaway
    if (type == 'Takeaway') {
      state = state.copyWith(clearTable: true);
    }
  }
  void setCustomer(String? id, {String? name}) {
    if (id == null) {
      state = state.copyWith(clearCustomer: true);
    } else {
      state = state.copyWith(customerId: id, customerName: name);
    }
  }
  void setTable(String? id, {String? name}) {
    if (id == null) {
      state = state.copyWith(clearTable: true);
    } else {
      state = state.copyWith(tableId: id, tableName: name);
    }
  }
  void clearCart() => state = const CartState();

  /// For dine-in Pro: open or reuse tab, create order, link to tab — NO payment yet.
  /// ONLINE ONLY — Tab is a server-side feature, cannot work offline.
  Future<Map<String, dynamic>?> submitDineInOrder() async {
    if (state.items.isEmpty) return null;
    if (state.tableId == null) {
      state = state.copyWith(error: 'Pilih meja terlebih dahulu untuk Dine In');
      return null;
    }

    // Tab flow requires network — check connectivity first
    final isOnline = await _checkOnline();
    if (!isOnline) {
      state = state.copyWith(error: 'Tab/Bon membutuhkan koneksi internet. Gunakan mode Takeaway untuk offline.');
      return null;
    }

    state = state.copyWith(isSubmitting: true, clearError: true);

    try {
      final token = _cache.accessToken;
      final tenantId = _cache.tenantId;
      final outletId = _cache.outletId;
      final shiftId = _cache.shiftSessionId;

      if (outletId == null || outletId.isEmpty) {
        state = state.copyWith(isSubmitting: false, error: 'Outlet tidak ditemukan. Login ulang.');
        return null;
      }

      final dio = Dio(BaseOptions(
        baseUrl: AppConfig.apiV1,
        connectTimeout: const Duration(seconds: 15),
        receiveTimeout: const Duration(seconds: 15),
      ));
      final headers = _cache.authHeaders;

      // 1. Check if table already has an open tab
      String? tabId;
      String? tabNumber;
      try {
        final tabRes = await dio.get(
          '/tabs/by-table/${state.tableId}',
          queryParameters: {'outlet_id': outletId},
          options: Options(headers: headers),
        );
        final tabData = tabRes.data['data'];
        if (tabData != null) {
          tabId = tabData['id'] as String;
          tabNumber = tabData['tab_number'] as String?;
        }
      } catch (_) {
        // No open tab or endpoint error — will create new tab
      }

      // 2. If no open tab, create one
      bool tabWasCreated = false;
      if (tabId == null) {
        try {
          final createRes = await dio.post(
            '/tabs/',
            options: Options(headers: headers),
            data: {
              'outlet_id': outletId,
              'table_id': state.tableId,
              'customer_name': state.customerName,
              'guest_count': 1,
            },
          );
          final tabData = createRes.data?['data'];
          if (tabData is Map) {
            tabId = tabData['id']?.toString();
            tabNumber = tabData['tab_number']?.toString();
            tabWasCreated = true;
          }
        } on DioException catch (e) {
          final code = e.response?.statusCode;
          final msg = code == 403
              ? 'Fitur Tab memerlukan paket Pro'
              : (e.response?.data?['detail']?.toString() ?? 'Gagal membuka tab');
          state = state.copyWith(isSubmitting: false, error: msg);
          return null;
        }
      }
      if (tabId == null) {
        state = state.copyWith(isSubmitting: false, error: 'Gagal membuka tab');
        return null;
      }

      // 3. Create the order
      final subtotal = state.subtotal;
      String? orderId;
      try {
        final orderRes = await dio.post(
          '/orders/',
          options: Options(headers: headers),
          data: {
            'outlet_id': outletId,
            if (shiftId != null) 'shift_session_id': shiftId,
            'order_type': 'dine_in',
            if (state.customerId != null) 'customer_id': state.customerId,
            if (state.tableId != null) 'table_id': state.tableId,
            'subtotal': subtotal,
            'service_charge_amount': state.serviceChargeAmount,
            'tax_amount': state.taxAmount,
            'discount_amount': state.discountAmount,
            'total_amount': state.total,
            'items': state.items
                .map((i) => {
                      'product_id': i.productId,
                      'quantity': i.qty,
                      'unit_price': i.price,
                      'total_price': i.price * i.qty,
                      'discount_amount': 0,
                      if (i.notes != null && i.notes!.isNotEmpty) 'notes': i.notes,
                    })
                .toList(),
          },
        );
        orderId = orderRes.data?['data']?['id']?.toString();
      } on DioException catch (e) {
        // Order failed — cancel tab if we just created it (prevent orphan)
        if (tabWasCreated) {
          try { await dio.post('/tabs/$tabId/cancel', options: Options(headers: headers)); } catch (_) {}
        }
        final msg = e.response?.data?['detail']?.toString() ?? 'Gagal membuat pesanan';
        state = state.copyWith(isSubmitting: false, error: msg);
        return null;
      }
      if (orderId == null) {
        if (tabWasCreated) {
          try { await dio.post('/tabs/$tabId/cancel', options: Options(headers: headers)); } catch (_) {}
        }
        state = state.copyWith(isSubmitting: false, error: 'Gagal membuat pesanan');
        return null;
      }

      // 4. Link order to tab + set to preparing (best-effort, non-blocking)
      try {
        await dio.post('/tabs/$tabId/orders', options: Options(headers: headers),
            data: {'order_id': orderId});
      } catch (_) {}

      try {
        await dio.put('/orders/$orderId/status', options: Options(headers: headers),
            data: {'status': 'preparing', 'row_version': 0});
      } catch (_) {}

      state = state.copyWith(
        isSubmitting: false,
        submittedOrderId: orderId,
        wasOffline: false,
      );
      return {
        'orderId': orderId,
        'tabId': tabId,
        'tabNumber': tabNumber,
      };
    } catch (_) {
      state = state.copyWith(isSubmitting: false, error: 'Terjadi kesalahan sistem');
      return null;
    }
  }

  Future<String?> submitOrder() async {
    if (state.items.isEmpty) return null;
    // Dine-in wajib pilih meja
    if (state.orderType == 'Dine In' && state.tableId == null) {
      state = state.copyWith(error: 'Pilih meja terlebih dahulu untuk Dine In');
      return null;
    }
    state = state.copyWith(isSubmitting: true, clearError: true);

    final isOnline = await _checkOnline();
    try {
      return isOnline ? await _submitOnline() : await _submitOffline();
    } catch (_) {
      state = state.copyWith(isSubmitting: false, error: 'Terjadi kesalahan sistem');
      return null;
    }
  }

  // ── Online: langsung ke backend ─────────────────────────────────────────
  Future<String?> _submitOnline() async {
    try {
      final outletId = _cache.outletId;
      final shiftId = _cache.shiftSessionId;

      if (outletId == null || outletId.isEmpty) {
        state = state.copyWith(
            isSubmitting: false, error: 'Outlet tidak ditemukan. Silakan login ulang.');
        return null;
      }

      final dio = Dio(BaseOptions(
        baseUrl: AppConfig.apiV1,
        connectTimeout: const Duration(seconds: 15),
        receiveTimeout: const Duration(seconds: 15),
      ));

      final subtotal = state.subtotal;
      final response = await dio.post(
        '/orders/',
        options: Options(headers: _cache.authHeaders),
        data: {
          'outlet_id': outletId,
          if (shiftId != null) 'shift_session_id': shiftId,
          'order_type': state.orderType.toLowerCase().replaceAll(' ', '_'),
          if (state.customerId != null) 'customer_id': state.customerId,
          if (state.tableId != null) 'table_id': state.tableId,
          'subtotal': subtotal,
          'service_charge_amount': state.serviceChargeAmount,
          'tax_amount': state.taxAmount,
          'discount_amount': state.discountAmount,
          'total_amount': state.total,
          'items': state.items
              .map((i) => {
                    'product_id': i.productId,
                    'quantity': i.qty,
                    'unit_price': i.price,
                    'total_price': i.price * i.qty,
                    'discount_amount': 0,
                    if (i.notes != null && i.notes!.isNotEmpty) 'notes': i.notes,
                  })
              .toList(),
        },
      );

      final orderId = response.data?['data']?['id']?.toString();
      if (orderId == null) {
        state = state.copyWith(isSubmitting: false, error: 'Response pesanan tidak valid');
        return null;
      }
      state = state.copyWith(
          isSubmitting: false, submittedOrderId: orderId, wasOffline: false);
      return orderId;
    } on DioException catch (e) {
      final msg = e.response?.data['detail'] ?? 'Gagal membuat pesanan';
      state = state.copyWith(isSubmitting: false, error: msg.toString());
      return null;
    }
  }

  // ── Offline: simpan ke Drift SQLite, deduct stok lokal ──────────────────
  Future<String?> _submitOffline() async {
    try {
      final outletId = _cache.outletId ?? '';
      final userId = _cache.userId ?? '';
      final shiftId = _cache.shiftSessionId;
      final orderId = _generateUuid();
      final now = DateTime.now();
      final subtotal = state.subtotal;
      final displayNumber = now.millisecondsSinceEpoch % 100000;

      await _db.transaction(() async {
        // 1. Simpan order lokal (isSynced: false → queue for sync)
        await _db.into(_db.orders).insert(OrdersCompanion(
          id: drift.Value(orderId),
          outletId: drift.Value(outletId),
          shiftSessionId: drift.Value(shiftId),
          userId: drift.Value(userId),
          customerId: drift.Value(state.customerId),
          tableId: drift.Value(state.tableId),
          orderNumber: drift.Value('OFFLINE-$displayNumber'),
          displayNumber: drift.Value(displayNumber),
          status: const drift.Value('pending'),
          orderType: drift.Value(state.orderType.toLowerCase().replaceAll(' ', '_')),
          subtotal: drift.Value(subtotal),
          serviceChargeAmount: drift.Value(state.serviceChargeAmount),
          taxAmount: drift.Value(state.taxAmount),
          discountAmount: drift.Value(state.discountAmount),
          totalAmount: drift.Value(state.total),
          createdAt: drift.Value(now),
          updatedAt: drift.Value(now),
          rowVersion: const drift.Value(0),
          isDeleted: const drift.Value(false),
          isSynced: const drift.Value(false),
        ));

        // 2. Simpan order items + deduct stok lokal
        final stockMode = _cache.stockMode ?? 'simple';

        for (final item in state.items) {
          await _db.into(_db.orderItems).insert(OrderItemsCompanion(
            id: drift.Value(_generateUuid()),
            orderId: drift.Value(orderId),
            productId: drift.Value(item.productId),
            quantity: drift.Value(item.qty),
            unitPrice: drift.Value(item.price),
            discountAmount: const drift.Value(0),
            totalPrice: drift.Value(item.price * item.qty),
            notes: drift.Value(item.notes),
            rowVersion: const drift.Value(0),
            isDeleted: const drift.Value(false),
            isSynced: const drift.Value(false),
          ));

          if (item.stockQty != null) {
            if (stockMode == 'recipe') {
              // Recipe mode: deduct ingredient stocks
              await _deductIngredientStockOffline(item.productId, item.qty, outletId);
            } else {
              // Simple mode: Pure CRDT stock deduct — PNCounter
              final prefs = await SharedPreferences.getInstance();
              final nodeId = prefs.getString('device_node_id') ??
                  'device_${DateTime.now().millisecondsSinceEpoch}';

              final product = await (_db.select(_db.products)
                    ..where((p) => p.id.equals(item.productId)))
                  .getSingleOrNull();

              if (product != null && product.stockEnabled) {
                final negMap = PNCounter.fromJson(product.crdtNegative);
                final posMap = PNCounter.fromJson(product.crdtPositive);
                final newNeg = PNCounter.increment(negMap, nodeId, amount: item.qty);
                final newStock = PNCounter.getValue(posMap, newNeg);

                await (_db.update(_db.products)
                      ..where((p) => p.id.equals(item.productId)))
                    .write(ProductsCompanion(
                  crdtNegative: drift.Value(PNCounter.toJson(newNeg)),
                  stockQty: drift.Value(newStock),
                  isActive: drift.Value(newStock > 0),
                  isSynced: const drift.Value(false),
                ));
              }
            }
          }
        }
      });

      state = state.copyWith(
          isSubmitting: false, submittedOrderId: orderId, wasOffline: true);
      return orderId;
    } catch (e) {
      state = state.copyWith(isSubmitting: false, error: 'Gagal menyimpan pesanan offline');
      return null;
    }
  }

  /// Deduct ingredient stock offline based on active recipe
  Future<void> _deductIngredientStockOffline(
      String productId, int orderQty, String outletId) async {
    // Load active recipe for product
    final recipe = await (_db.select(_db.recipes)
          ..where((r) => r.productId.equals(productId))
          ..where((r) => r.isActive.equals(true))
          ..where((r) => r.isDeleted.equals(false)))
        .getSingleOrNull();
    if (recipe == null) return;

    // Load non-optional recipe ingredients
    final riList = await (_db.select(_db.recipeIngredients)
          ..where((ri) => ri.recipeId.equals(recipe.id))
          ..where((ri) => ri.isDeleted.equals(false))
          ..where((ri) => ri.isOptional.equals(false)))
        .get();

    // Deduct each ingredient from outlet_stock
    for (final ri in riList) {
      if (ri.quantity <= 0) continue;
      final deductQty = ri.quantity * orderQty;

      final stock = await (_db.select(_db.outletStocks)
            ..where((os) => os.outletId.equals(outletId))
            ..where((os) => os.ingredientId.equals(ri.ingredientId))
            ..where((os) => os.isDeleted.equals(false)))
          .getSingleOrNull();

      if (stock != null) {
        final newStock = (stock.computedStock - deductQty).clamp(0.0, double.infinity);
        await (_db.update(_db.outletStocks)
              ..where((os) => os.id.equals(stock.id)))
            .write(OutletStocksCompanion(
          computedStock: drift.Value(newStock),
          isSynced: const drift.Value(false),
        ));
      }
    }
  }

  Future<bool> _checkOnline() async {
    final result = await Connectivity().checkConnectivity();
    return result.isNotEmpty && !result.contains(ConnectivityResult.none);
  }
}

// ─── Provider ─────────────────────────────────────────────────────────────────

final cartProvider = StateNotifierProvider<CartNotifier, CartState>((ref) {
  final db = ref.watch(databaseProvider);
  final notifier = CartNotifier(db);

  // Inject tax config when available
  ref.listen(taxConfigProvider, (_, next) {
    next.whenData((config) => notifier.setTaxConfig(config));
  });

  // Also set immediately if already loaded
  final taxAsync = ref.read(taxConfigProvider);
  taxAsync.whenData((config) => notifier.setTaxConfig(config));

  return notifier;
});
