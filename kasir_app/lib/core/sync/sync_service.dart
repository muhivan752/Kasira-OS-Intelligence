import 'package:dio/dio.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../database/app_database.dart';
import '../utils/hlc.dart';
import '../utils/pn_counter.dart';
import 'package:flutter/foundation.dart';

class SyncService {
  final AppDatabase db;
  final Dio dio;
  final SharedPreferences prefs;
  
  static const String _lastSyncKey = 'last_sync_hlc';
  static const String _nodeIdKey = 'device_node_id';

  SyncService(this.db, this.dio, this.prefs);

  String get nodeId {
    String? id = prefs.getString(_nodeIdKey);
    if (id == null) {
      id = 'device_${DateTime.now().millisecondsSinceEpoch}';
      prefs.setString(_nodeIdKey, id);
    }
    return id;
  }

  Future<void> sync() async {
    try {
      debugPrint('Starting sync process...');
      
      // 1. Gather unsynced local changes
      final unsyncedProducts = await db.getUnsyncedProducts();
      final unsyncedOrders = await db.getUnsyncedOrders();
      final unsyncedOrderItems = await db.getUnsyncedOrderItems();
      final unsyncedPayments = await db.getUnsyncedPayments();
      final unsyncedShifts = await db.getUnsyncedShifts();
      final unsyncedCashActivities = await db.getUnsyncedCashActivities();

      final changes = {
        'categories': [], // We don't create categories from POS
        'products': unsyncedProducts.map(_productToJson).toList(),
        'orders': unsyncedOrders.map(_orderToJson).toList(),
        'order_items': unsyncedOrderItems.map(_orderItemToJson).toList(),
        'payments': unsyncedPayments.map(_paymentToJson).toList(),
        'outlet_stock': [], // Handled via products/orders usually
        'shifts': unsyncedShifts.map(_shiftToJson).toList(),
        'cash_activities': unsyncedCashActivities.map(_cashActivityToJson).toList(),
      };

      final lastSyncHlc = prefs.getString(_lastSyncKey);

      final payload = {
        'node_id': nodeId,
        'last_sync_hlc': lastSyncHlc,
        'changes': changes,
      };

      // 2. Send to server
      final response = await dio.post('/sync/', data: payload);

      if (response.statusCode == 200) {
        final data = response.data;
        final serverHlc = data['last_sync_hlc'];
        final serverChanges = data['changes'];

        // 3. Apply server changes to local DB
        await _applyServerChanges(serverChanges);

        // 3b. Persist stock_mode from server
        final stockMode = data['stock_mode']?.toString();
        if (stockMode != null) {
          const storage = FlutterSecureStorage();
          await storage.write(key: 'stock_mode', value: stockMode);
        }

        // 4. Mark local changes as synced
        await _markAsSynced(
          products: unsyncedProducts,
          orders: unsyncedOrders,
          orderItems: unsyncedOrderItems,
          payments: unsyncedPayments,
          shifts: unsyncedShifts,
          cashActivities: unsyncedCashActivities,
        );

        // 5. Update last sync HLC
        await prefs.setString(_lastSyncKey, serverHlc);
        debugPrint('Sync completed successfully. New HLC: $serverHlc');
      } else {
        debugPrint('Sync failed with status: ${response.statusCode}');
      }
    } catch (e) {
      debugPrint('Sync error: $e');
      rethrow;
    }
  }

  Future<void> _applyServerChanges(Map<String, dynamic> changes) async {
    await db.transaction(() async {
      // Apply Products — CRDT merge: gabungkan counter lokal & server
      if (changes['products'] != null) {
        for (var p in changes['products']) {
          final serverPos = p['crdt_positive'] ?? '{}';
          final serverNeg = p['crdt_negative'] ?? '{}';

          // Cek apakah produk sudah ada di lokal
          final existing = await (db.select(db.products)
                ..where((t) => t.id.equals(p['id'])))
              .getSingleOrNull();

          String mergedPos = serverPos;
          String mergedNeg = serverNeg;
          double mergedStock = (p['stock_qty'] as num?)?.toDouble() ?? 0.0;

          if (existing != null && existing.stockEnabled) {
            // Merge CRDT: ambil max dari setiap node
            final localPosMap = PNCounter.fromJson(existing.crdtPositive);
            final localNegMap = PNCounter.fromJson(existing.crdtNegative);
            final serverPosMap = PNCounter.fromJson(serverPos);
            final serverNegMap = PNCounter.fromJson(serverNeg);

            final mPos = PNCounter.merge(localPosMap, serverPosMap);
            final mNeg = PNCounter.merge(localNegMap, serverNegMap);

            mergedPos = PNCounter.toJson(mPos);
            mergedNeg = PNCounter.toJson(mNeg);
            mergedStock = PNCounter.getValue(mPos, mNeg);
          }

          await db.into(db.products).insertOnConflictUpdate(
            ProductLocal(
              id: p['id'],
              brandId: p['brand_id'],
              categoryId: p['category_id'],
              name: p['name'],
              description: p['description'],
              basePrice: (p['base_price'] as num).toDouble(),
              sku: p['sku'],
              barcode: p['barcode'],
              imageUrl: p['image_url'],
              stockEnabled: p['stock_enabled'] ?? false,
              crdtPositive: mergedPos,
              crdtNegative: mergedNeg,
              stockQty: mergedStock,
              isActive: p['is_active'] ?? true,
              rowVersion: p['row_version'] ?? 0,
              isDeleted: p['is_deleted'] ?? false,
              lastModifiedHlc: p['hlc'],
              isSynced: true,
            ),
          );
        }
      }

      // Apply Orders
      if (changes['orders'] != null) {
        for (var o in changes['orders']) {
          await db.into(db.orders).insertOnConflictUpdate(
            OrderLocal(
              id: o['id'],
              outletId: o['outlet_id'],
              shiftSessionId: o['shift_session_id'],
              customerId: o['customer_id'],
              tableId: o['table_id'],
              userId: o['user_id'],
              orderNumber: o['order_number'],
              displayNumber: o['display_number'],
              status: o['status'],
              orderType: o['order_type'],
              subtotal: (o['subtotal'] as num).toDouble(),
              serviceChargeAmount: (o['service_charge_amount'] as num).toDouble(),
              taxAmount: (o['tax_amount'] as num).toDouble(),
              discountAmount: (o['discount_amount'] as num).toDouble(),
              totalAmount: (o['total_amount'] as num).toDouble(),
              notes: o['notes'],
              createdAt: o['created_at'] != null ? DateTime.parse(o['created_at']) : null,
              updatedAt: o['updated_at'] != null ? DateTime.parse(o['updated_at']) : null,
              rowVersion: o['row_version'] ?? 0,
              isDeleted: o['is_deleted'] ?? false,
              lastModifiedHlc: o['hlc'],
              isSynced: true,
            ),
          );
        }
      }
      
      // Apply Order Items
      if (changes['order_items'] != null) {
        for (var oi in changes['order_items']) {
          await db.into(db.orderItems).insertOnConflictUpdate(
            OrderItemLocal(
              id: oi['id'],
              orderId: oi['order_id'],
              productId: oi['product_id'],
              productVariantId: oi['product_variant_id'],
              quantity: oi['quantity'],
              unitPrice: (oi['unit_price'] as num).toDouble(),
              discountAmount: (oi['discount_amount'] as num).toDouble(),
              totalPrice: (oi['total_price'] as num).toDouble(),
              modifiers: oi['modifiers']?.toString(),
              notes: oi['notes'],
              rowVersion: oi['row_version'] ?? 0,
              isDeleted: oi['is_deleted'] ?? false,
              lastModifiedHlc: oi['hlc'],
              isSynced: true,
            ),
          );
        }
      }

      // Apply Payments
      if (changes['payments'] != null) {
        for (var p in changes['payments']) {
          await db.into(db.payments).insertOnConflictUpdate(
            PaymentLocal(
              id: p['id'],
              orderId: p['order_id'],
              outletId: p['outlet_id'],
              shiftSessionId: p['shift_session_id'],
              amountDue: (p['amount_due'] as num).toDouble(),
              amountPaid: (p['amount_paid'] as num).toDouble(),
              paymentMethod: p['payment_method'],
              status: p['status'],
              referenceNumber: p['reference_number'],
              paidAt: p['paid_at'] != null ? DateTime.parse(p['paid_at']) : null,
              rowVersion: p['row_version'] ?? 0,
              isDeleted: p['is_deleted'] ?? false,
              lastModifiedHlc: p['hlc'],
              isSynced: true,
            ),
          );
        }
      }

      // Apply Shifts
      if (changes['shifts'] != null) {
        for (var s in changes['shifts']) {
          await db.into(db.shifts).insertOnConflictUpdate(
            ShiftLocal(
              id: s['id'],
              outletId: s['outlet_id'],
              userId: s['user_id'],
              status: s['status'],
              startTime: DateTime.parse(s['start_time']),
              endTime: s['end_time'] != null ? DateTime.parse(s['end_time']) : null,
              startingCash: (s['starting_cash'] as num).toDouble(),
              endingCash: (s['ending_cash'] as num?)?.toDouble(),
              expectedEndingCash: (s['expected_ending_cash'] as num?)?.toDouble(),
              notes: s['notes'],
              rowVersion: s['row_version'] ?? 0,
              isDeleted: s['is_deleted'] ?? false,
              lastModifiedHlc: s['hlc'],
              isSynced: true,
            ),
          );
        }
      }
      
      // Apply Cash Activities
      if (changes['cash_activities'] != null) {
        for (var ca in changes['cash_activities']) {
          await db.into(db.cashActivities).insertOnConflictUpdate(
            CashActivityLocal(
              id: ca['id'],
              shiftId: ca['shift_id'],
              activityType: ca['activity_type'],
              amount: (ca['amount'] as num).toDouble(),
              description: ca['description'],
              rowVersion: ca['row_version'] ?? 0,
              isDeleted: ca['is_deleted'] ?? false,
              lastModifiedHlc: ca['hlc'],
              isSynced: true,
            ),
          );
        }
      }

      // Apply Ingredients (read-only from server)
      if (changes['ingredients'] != null) {
        for (var ing in changes['ingredients']) {
          await db.into(db.ingredients).insertOnConflictUpdate(
            IngredientLocal(
              id: ing['id'],
              brandId: ing['brand_id'],
              name: ing['name'],
              trackingMode: ing['tracking_mode'] ?? 'simple',
              baseUnit: ing['base_unit'] ?? 'pcs',
              unitType: ing['unit_type'] ?? 'COUNT',
              buyPrice: _toDouble(ing['buy_price']),
              buyQty: _toDouble(ing['buy_qty'], fallback: 1.0),
              costPerBaseUnit: _toDouble(ing['cost_per_base_unit']),
              ingredientType: ing['ingredient_type'] ?? 'recipe',
              rowVersion: ing['row_version'] ?? 0,
              isDeleted: ing['is_deleted'] ?? false,
              lastModifiedHlc: ing['hlc'],
              isSynced: true,
            ),
          );
        }
      }

      // Apply Recipes (read-only from server)
      if (changes['recipes'] != null) {
        for (var r in changes['recipes']) {
          await db.into(db.recipes).insertOnConflictUpdate(
            RecipeLocal(
              id: r['id'],
              productId: r['product_id'],
              version: r['version'] ?? 1,
              isActive: r['is_active'] ?? true,
              notes: r['notes'],
              rowVersion: 0,
              isDeleted: r['is_deleted'] ?? false,
              lastModifiedHlc: r['hlc'],
              isSynced: true,
            ),
          );
        }
      }

      // Apply Recipe Ingredients (read-only from server)
      if (changes['recipe_ingredients'] != null) {
        for (var ri in changes['recipe_ingredients']) {
          await db.into(db.recipeIngredients).insertOnConflictUpdate(
            RecipeIngredientLocal(
              id: ri['id'],
              recipeId: ri['recipe_id'],
              ingredientId: ri['ingredient_id'],
              quantity: _toDouble(ri['quantity']),
              quantityUnit: ri['quantity_unit'],
              notes: ri['notes'],
              isOptional: ri['is_optional'] ?? false,
              rowVersion: 0,
              isDeleted: ri['is_deleted'] ?? false,
              lastModifiedHlc: ri['hlc'],
              isSynced: true,
            ),
          );
        }
      }

      // Apply Outlet Stock (ingredient stock per outlet, read-only from server)
      if (changes['outlet_stock'] != null) {
        for (var os in changes['outlet_stock']) {
          await db.into(db.outletStocks).insertOnConflictUpdate(
            OutletStockLocal(
              id: os['id'],
              outletId: os['outlet_id'],
              ingredientId: os['ingredient_id'],
              computedStock: _toDouble(os['computed_stock']),
              minStockBase: _toDouble(os['min_stock_base']),
              rowVersion: os['row_version'] ?? 0,
              isDeleted: os['is_deleted'] ?? false,
              lastModifiedHlc: os['hlc'],
              isSynced: true,
            ),
          );
        }
      }
    });
  }

  Future<void> _markAsSynced({
    required List<ProductLocal> products,
    required List<OrderLocal> orders,
    required List<OrderItemLocal> orderItems,
    required List<PaymentLocal> payments,
    required List<ShiftLocal> shifts,
    required List<CashActivityLocal> cashActivities,
  }) async {
    await db.transaction(() async {
      for (var p in products) {
        await db.update(db.products).replace(p.copyWith(isSynced: true));
      }
      for (var o in orders) {
        await db.update(db.orders).replace(o.copyWith(isSynced: true));
      }
      for (var oi in orderItems) {
        await db.update(db.orderItems).replace(oi.copyWith(isSynced: true));
      }
      for (var p in payments) {
        await db.update(db.payments).replace(p.copyWith(isSynced: true));
      }
      for (var s in shifts) {
        await db.update(db.shifts).replace(s.copyWith(isSynced: true));
      }
      for (var ca in cashActivities) {
        await db.update(db.cashActivities).replace(ca.copyWith(isSynced: true));
      }
    });
  }

  Map<String, dynamic> _productToJson(ProductLocal p) => {
    'id': p.id,
    'brand_id': p.brandId,
    'category_id': p.categoryId,
    'name': p.name,
    'description': p.description,
    'base_price': p.basePrice,
    'sku': p.sku,
    'barcode': p.barcode,
    'image_url': p.imageUrl,
    'stock_enabled': p.stockEnabled,
    'stock_qty': p.stockQty,
    // Pure CRDT: kirim kedua G-Counter agar backend bisa merge dengan benar
    'crdt_positive': p.crdtPositive,
    'crdt_negative': p.crdtNegative,
    'is_active': p.isActive,
    'row_version': p.rowVersion,
    'is_deleted': p.isDeleted,
    'hlc': p.lastModifiedHlc,
  };

  Map<String, dynamic> _orderToJson(OrderLocal o) => {
    'id': o.id,
    'outlet_id': o.outletId,
    'shift_session_id': o.shiftSessionId,
    'customer_id': o.customerId,
    'table_id': o.tableId,
    'user_id': o.userId,
    'order_number': o.orderNumber,
    'display_number': o.displayNumber,
    'status': o.status,
    'order_type': o.orderType,
    'subtotal': o.subtotal,
    'service_charge_amount': o.serviceChargeAmount,
    'tax_amount': o.taxAmount,
    'discount_amount': o.discountAmount,
    'total_amount': o.totalAmount,
    'notes': o.notes,
    'created_at': o.createdAt?.toIso8601String(),
    'updated_at': o.updatedAt?.toIso8601String(),
    'row_version': o.rowVersion,
    'is_deleted': o.isDeleted,
    'hlc': o.lastModifiedHlc,
  };

  Map<String, dynamic> _orderItemToJson(OrderItemLocal oi) => {
    'id': oi.id,
    'order_id': oi.orderId,
    'product_id': oi.productId,
    'product_variant_id': oi.productVariantId,
    'quantity': oi.quantity,
    'unit_price': oi.unitPrice,
    'discount_amount': oi.discountAmount,
    'total_price': oi.totalPrice,
    'modifiers': oi.modifiers,
    'notes': oi.notes,
    'row_version': oi.rowVersion,
    'is_deleted': oi.isDeleted,
    'hlc': oi.lastModifiedHlc,
  };

  Map<String, dynamic> _paymentToJson(PaymentLocal p) => {
    'id': p.id,
    'order_id': p.orderId,
    'outlet_id': p.outletId,
    'shift_session_id': p.shiftSessionId,
    'amount_due': p.amountDue,
    'amount_paid': p.amountPaid,
    'payment_method': p.paymentMethod,
    'status': p.status,
    'reference_number': p.referenceNumber,
    'paid_at': p.paidAt?.toIso8601String(),
    'row_version': p.rowVersion,
    'is_deleted': p.isDeleted,
    'hlc': p.lastModifiedHlc,
  };

  Map<String, dynamic> _shiftToJson(ShiftLocal s) => {
    'id': s.id,
    'outlet_id': s.outletId,
    'user_id': s.userId,
    'status': s.status,
    'start_time': s.startTime.toIso8601String(),
    'end_time': s.endTime?.toIso8601String(),
    'starting_cash': s.startingCash,
    'ending_cash': s.endingCash,
    'expected_ending_cash': s.expectedEndingCash,
    'notes': s.notes,
    'row_version': s.rowVersion,
    'is_deleted': s.isDeleted,
    'hlc': s.lastModifiedHlc,
  };

  static double _toDouble(dynamic v, {double fallback = 0.0}) {
    if (v == null) return fallback;
    if (v is num) return v.toDouble();
    return double.tryParse(v.toString()) ?? fallback;
  }

  Map<String, dynamic> _cashActivityToJson(CashActivityLocal ca) => {
    'id': ca.id,
    'shift_id': ca.shiftId,
    'activity_type': ca.activityType,
    'amount': ca.amount,
    'description': ca.description,
    'row_version': ca.rowVersion,
    'is_deleted': ca.isDeleted,
    'hlc': ca.lastModifiedHlc,
  };
}
