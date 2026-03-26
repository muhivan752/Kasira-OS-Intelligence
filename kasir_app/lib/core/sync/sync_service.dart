import 'package:dio/dio.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../database/app_database.dart';
import '../utils/hlc.dart';
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
        'products': unsyncedProducts.map((p) => p.toJson()).toList(),
        'orders': unsyncedOrders.map((o) => o.toJson()).toList(),
        'order_items': unsyncedOrderItems.map((oi) => oi.toJson()).toList(),
        'payments': unsyncedPayments.map((p) => p.toJson()).toList(),
        'outlet_stock': [], // Handled via products/orders usually
        'shifts': unsyncedShifts.map((s) => s.toJson()).toList(),
        'cash_activities': unsyncedCashActivities.map((ca) => ca.toJson()).toList(),
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
      // Apply Products
      if (changes['products'] != null) {
        for (var p in changes['products']) {
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
              stockQty: (p['stock_qty'] as num?)?.toDouble() ?? 0.0,
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
}
