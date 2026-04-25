import 'dart:io';
import 'package:drift/drift.dart';
import 'package:drift/native.dart';
import 'package:path_provider/path_provider.dart';
import 'package:path/path.dart' as p;

import 'tables.dart';

part 'app_database.g.dart';

@DriftDatabase(tables: [Products, Orders, OrderItems, Payments, Shifts, CashActivities, Ingredients, Recipes, RecipeIngredients, OutletStocks])
class AppDatabase extends _$AppDatabase {
  AppDatabase() : super(_openConnection());

  @override
  int get schemaVersion => 6;

  @override
  MigrationStrategy get migration => MigrationStrategy(
        onUpgrade: (m, from, to) async {
          if (from < 2) {
            await m.addColumn(products, products.crdtPositive);
            await m.addColumn(products, products.crdtNegative);
          }
          if (from < 3) {
            await m.createTable(ingredients);
            await m.createTable(recipes);
            await m.createTable(recipeIngredients);
          }
          if (from < 4) {
            await m.createTable(outletStocks);
          }
          if (from < 5) {
            // Fase 3 Starter Margin Tracking — products.buyPrice nullable.
            // Additive: existing rows get NULL by default (=belum diisi).
            await m.addColumn(products, products.buyPrice);
          }
          if (from < 6) {
            // Migration 085 — per-item ad-hoc payment (warkop pattern).
            // Additive: existing items NULL = unpaid (atau historical paid via order.status='completed').
            await m.addColumn(orderItems, orderItems.paidAt);
            await m.addColumn(orderItems, orderItems.paidPaymentId);
          }
        },
      );

  // Helper method to get unsynced records
  // NOTE: Products = tenant-level (no outletId column) — tidak di-scope per outlet.
  // Rule #50: Orders/Payments/Shifts/OrderItems/CashActivities WAJIB scope ke
  // SessionCache.outletId biar data belum-sync gak bocor antar-outlet saat
  // multi-outlet switch di same device.
  //
  // Batch #18 Rule #4: optional `brandId` filter untuk cegah tenant bleed.
  // Kalau User A (tenant X) offline edit produk lalu User B (tenant Y) login
  // di device sama, tanpa filter ini SyncService-nya B bakal push produk
  // milik A. Dengan filter brandId → B cuma push produk tenant-nya sendiri.
  // brandId null = no filter (first-install atau tenant belum ke-determine).
  Future<List<ProductLocal>> getUnsyncedProducts({String? brandId}) {
    final query = select(products)..where((t) => t.isSynced.equals(false));
    if (brandId != null && brandId.isNotEmpty) {
      query.where((t) => t.brandId.equals(brandId));
    }
    return query.get();
  }

  /// Derive brandId tenant-aktif dari salah satu produk yang sudah synced
  /// (mereka semua share brand_id karena datang dari server yg sudah
  /// scope by tenant). Return null kalau DB belum ada produk synced sama
  /// sekali (first-install scenario).
  Future<String?> getCurrentBrandId() async {
    final row = await (select(products)
          ..where((t) => t.isSynced.equals(true))
          ..limit(1))
        .getSingleOrNull();
    return row?.brandId;
  }

  Future<List<OrderLocal>> getUnsyncedOrders(String outletId) => (select(orders)
        ..where((t) => t.isSynced.equals(false))
        ..where((t) => t.outletId.equals(outletId)))
      .get();

  /// OrderItems tidak punya outletId column langsung — scope via parent Order.
  Future<List<OrderItemLocal>> getUnsyncedOrderItems(String outletId) {
    final scopedOrderIds = selectOnly(orders)
      ..addColumns([orders.id])
      ..where(orders.outletId.equals(outletId));
    return (select(orderItems)
          ..where((t) => t.isSynced.equals(false))
          ..where((t) => t.orderId.isInQuery(scopedOrderIds)))
        .get();
  }

  Future<List<PaymentLocal>> getUnsyncedPayments(String outletId) =>
      (select(payments)
            ..where((t) => t.isSynced.equals(false))
            ..where((t) => t.outletId.equals(outletId)))
          .get();

  Future<List<ShiftLocal>> getUnsyncedShifts(String outletId) =>
      (select(shifts)
            ..where((t) => t.isSynced.equals(false))
            ..where((t) => t.outletId.equals(outletId)))
          .get();

  /// CashActivities tidak punya outletId column — scope via parent Shift.
  Future<List<CashActivityLocal>> getUnsyncedCashActivities(String outletId) {
    final scopedShiftIds = selectOnly(shifts)
      ..addColumns([shifts.id])
      ..where(shifts.outletId.equals(outletId));
    return (select(cashActivities)
          ..where((t) => t.isSynced.equals(false))
          ..where((t) => t.shiftId.isInQuery(scopedShiftIds)))
        .get();
  }
}

LazyDatabase _openConnection() {
  return LazyDatabase(() async {
    final dbFolder = await getApplicationDocumentsDirectory();
    final file = File(p.join(dbFolder.path, 'kasira_pos.sqlite'));
    final db = NativeDatabase.createInBackground(file);
    return db;
  });
}

/// Call once at app start to enable WAL mode for better concurrent read/write
Future<void> enableWalMode(AppDatabase db) async {
  await db.customStatement('PRAGMA journal_mode=WAL');
  await db.customStatement('PRAGMA synchronous=NORMAL');
}
