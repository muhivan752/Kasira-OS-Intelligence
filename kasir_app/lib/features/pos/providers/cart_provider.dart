import 'package:drift/drift.dart' as drift;
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:dio/dio.dart';
import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:uuid/uuid.dart';
import '../../../core/config/app_config.dart';
import '../../../core/database/app_database.dart';
import '../../../core/sync/sync_provider.dart';
import '../../../core/sync/sync_service.dart';
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
  final int guestCount;
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
    this.guestCount = 1,
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
    int? guestCount,
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
        guestCount: clearTable ? 1 : (guestCount ?? this.guestCount),
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

// ─── Helper: parse structured error detail dari backend ─────────────────────
// Backend stock_service & ingredient_stock_service return detail dalam format:
//   {code, mode, message, items: [{name, product_name, available, needed, unit}]}
// Fungsi ini fallback ke plain string kalau detail bukan Map.
String parseStockErrorDetail(dynamic detail, {String fallback = 'Gagal membuat pesanan'}) {
  if (detail == null) return fallback;
  if (detail is String) return detail;
  if (detail is! Map) return detail.toString();

  final code = detail['code']?.toString();
  final mode = detail['mode']?.toString();
  final message = detail['message']?.toString();
  final items = (detail['items'] as List?) ?? const [];

  if ((code == 'STOCK_INSUFFICIENT' || code == 'STOCK_RACE_CONDITION' || code == 'STOCK_NOT_INITIALIZED')
      && items.isNotEmpty) {
    final buf = StringBuffer();
    buf.writeln(mode == 'recipe' ? 'Stok bahan tidak cukup:' : 'Stok produk tidak cukup:');
    for (final it in items.take(5)) {
      if (it is! Map) continue;
      final name = it['name']?.toString() ?? '-';
      final avail = it['available'];
      final need = it['needed'];
      final unit = it['unit']?.toString() ?? '';
      final productName = it['product_name']?.toString();
      final line = mode == 'recipe' && productName != null && productName.isNotEmpty
          ? '• $name (untuk $productName): butuh $need $unit, sisa $avail'
          : '• $name: butuh $need $unit, sisa $avail';
      buf.writeln(line);
    }
    if (items.length > 5) buf.writeln('... dan ${items.length - 5} lainnya');
    return buf.toString().trim();
  }

  return message ?? fallback;
}

// ─── Notifier ────────────────────────────────────────────────────────────────

class CartNotifier extends StateNotifier<CartState> {
  final AppDatabase _db;
  final SyncService _syncService;
  TaxConfig? _taxConfig;
  // Batch #18 Rule #1: CartNotifier dapet injection SyncService biar offline
  // PNCounter increment pake composite nodeId (sha256(device|user)) — bukan
  // raw device_node_id yang bikin collision kalau user shift-switch cepat di
  // device yang sama.
  CartNotifier(this._db, this._syncService) : super(const CartState());

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
  void setTable(String? id, {String? name, int? guestCount}) {
    if (id == null) {
      state = state.copyWith(clearTable: true);
    } else {
      state = state.copyWith(
        tableId: id,
        tableName: name,
        guestCount: guestCount ?? state.guestCount,
      );
    }
  }

  void setGuestCount(int n) {
    if (n < 1) n = 1;
    if (n > 50) n = 50;
    state = state.copyWith(guestCount: n);
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
              'guest_count': state.guestCount,
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
              : parseStockErrorDetail(e.response?.data?['detail'], fallback: 'Gagal membuka tab');
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
        final msg = parseStockErrorDetail(e.response?.data?['detail']);
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
      final msg = parseStockErrorDetail(e.response?.data?['detail']);
      state = state.copyWith(isSubmitting: false, error: msg);
      return null;
    }
  }

  // ── Offline: simpan ke Drift SQLite, deduct stok lokal ──────────────────
  Future<String?> _submitOffline() async {
    try {
      // Pre-check stock (mirror backend guard agar gak oversell offline)
      final stockError = await _validateOfflineStock();
      if (stockError != null) {
        state = state.copyWith(isSubmitting: false, error: stockError);
        return null;
      }
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
              // Simple mode: Pure CRDT stock deduct — PNCounter.
              // Batch #18: pake composite nodeId dari SyncService (sha256 per
              // user-device pair). Gak lagi baca raw 'device_node_id' key —
              // biar shift-switch User A → User B di device sama jatuh di
              // slot PNCounter yang beda, merge server penjumlahan bukan max.
              final nodeId = _syncService.nodeId;

              final product = await (_db.select(_db.products)
                    ..where((p) => p.id.equals(item.productId)))
                  .getSingleOrNull();

              if (product != null && product.stockEnabled) {
                final negMap = PNCounter.fromJson(product.crdtNegative);
                final posMap = PNCounter.fromJson(product.crdtPositive);
                final newNeg = PNCounter.increment(negMap, nodeId, amount: item.qty);
                final newStock = PNCounter.getValue(posMap, newNeg);

                // Rule #20: produk stock=0 tetap muncul (is_available dikomputasi dari stockQty),
                // jangan paksa isActive=false karena itu flag on/off manual dari owner.
                await (_db.update(_db.products)
                      ..where((p) => p.id.equals(item.productId)))
                    .write(ProductsCompanion(
                  crdtNegative: drift.Value(PNCounter.toJson(newNeg)),
                  stockQty: drift.Value(newStock),
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
    final rawRiList = await (_db.select(_db.recipeIngredients)
          ..where((ri) => ri.recipeId.equals(recipe.id))
          ..where((ri) => ri.isDeleted.equals(false))
          ..where((ri) => ri.isOptional.equals(false)))
        .get();

    // Filter ingredients yang sudah soft-deleted (ghost stock guard)
    final ingIds = rawRiList.map((ri) => ri.ingredientId).toSet().toList();
    if (ingIds.isEmpty) return;
    final activeIngs = await (_db.select(_db.ingredients)
          ..where((i) => i.id.isIn(ingIds))
          ..where((i) => i.isDeleted.equals(false)))
        .get();
    final activeSet = activeIngs.map((i) => i.id).toSet();
    final riList = rawRiList.where((ri) => activeSet.contains(ri.ingredientId)).toList();

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

  /// Pre-check: pastikan stok cukup sebelum insert order offline.
  /// Return null kalau cukup, atau pesan error siap tampil ke user.
  Future<String?> _validateOfflineStock() async {
    final stockMode = _cache.stockMode ?? 'simple';
    final outletId = _cache.outletId ?? '';

    // Aggregate qty per product (item bisa muncul lebih dari sekali di cart)
    final qtyByProduct = <String, int>{};
    for (final item in state.items) {
      if (item.stockQty == null) continue;
      qtyByProduct[item.productId] = (qtyByProduct[item.productId] ?? 0) + item.qty;
    }
    if (qtyByProduct.isEmpty) return null;

    if (stockMode == 'recipe') {
      // Aggregate ingredient requirements across all items
      final required = <String, double>{};
      for (final entry in qtyByProduct.entries) {
        final recipe = await (_db.select(_db.recipes)
              ..where((r) => r.productId.equals(entry.key))
              ..where((r) => r.isActive.equals(true))
              ..where((r) => r.isDeleted.equals(false)))
            .getSingleOrNull();
        if (recipe == null) continue;
        final rawRi = await (_db.select(_db.recipeIngredients)
              ..where((ri) => ri.recipeId.equals(recipe.id))
              ..where((ri) => ri.isDeleted.equals(false))
              ..where((ri) => ri.isOptional.equals(false)))
            .get();
        final ingIds = rawRi.map((ri) => ri.ingredientId).toSet().toList();
        if (ingIds.isEmpty) continue;
        final activeIngs = await (_db.select(_db.ingredients)
              ..where((i) => i.id.isIn(ingIds))
              ..where((i) => i.isDeleted.equals(false)))
            .get();
        final activeSet = activeIngs.map((i) => i.id).toSet();
        for (final ri in rawRi) {
          if (!activeSet.contains(ri.ingredientId)) continue;
          if (ri.quantity <= 0) continue;
          required[ri.ingredientId] =
              (required[ri.ingredientId] ?? 0) + ri.quantity * entry.value;
        }
      }
      if (required.isEmpty) return null;

      final stocks = await (_db.select(_db.outletStocks)
            ..where((os) => os.outletId.equals(outletId))
            ..where((os) => os.ingredientId.isIn(required.keys.toList()))
            ..where((os) => os.isDeleted.equals(false)))
          .get();
      final stockMap = {for (final s in stocks) s.ingredientId: s.computedStock};

      for (final entry in required.entries) {
        final available = stockMap[entry.key] ?? 0.0;
        if (available < entry.value) {
          final ing = await (_db.select(_db.ingredients)
                ..where((i) => i.id.equals(entry.key)))
              .getSingleOrNull();
          final unit = ing?.baseUnit ?? '';
          final name = ing?.name ?? 'bahan';
          final needStr = entry.value % 1 == 0 ? entry.value.toInt().toString() : entry.value.toStringAsFixed(1);
          final availStr = available % 1 == 0 ? available.toInt().toString() : available.toStringAsFixed(1);
          return 'Stok $name tidak cukup — butuh $needStr $unit, sisa $availStr $unit';
        }
      }
    } else {
      // Simple mode
      for (final entry in qtyByProduct.entries) {
        final product = await (_db.select(_db.products)
              ..where((p) => p.id.equals(entry.key)))
            .getSingleOrNull();
        if (product == null || !product.stockEnabled) continue;
        if (product.stockQty < entry.value) {
          return 'Stok ${product.name} tidak cukup (tersedia: ${product.stockQty.toInt()})';
        }
      }
    }
    return null;
  }

  Future<bool> _checkOnline() async {
    final result = await Connectivity().checkConnectivity();
    return result.isNotEmpty && !result.contains(ConnectivityResult.none);
  }
}

// ─── Provider ─────────────────────────────────────────────────────────────────

final cartProvider = StateNotifierProvider<CartNotifier, CartState>((ref) {
  final db = ref.watch(databaseProvider);
  final syncService = ref.watch(syncServiceProvider);
  final notifier = CartNotifier(db, syncService);

  // Inject tax config when available
  ref.listen(taxConfigProvider, (_, next) {
    next.whenData((config) => notifier.setTaxConfig(config));
  });

  // Also set immediately if already loaded
  final taxAsync = ref.read(taxConfigProvider);
  taxAsync.whenData((config) => notifier.setTaxConfig(config));

  return notifier;
});
