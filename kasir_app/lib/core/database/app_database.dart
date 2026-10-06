import 'dart:io';
import 'package:drift/drift.dart';
import 'package:drift/native.dart';
import 'package:path_provider/path_provider.dart';
import 'package:path/path.dart' as p;

import 'tables.dart';

part 'app_database.g.dart';

@DriftDatabase(tables: [
  Products,
  ProductVariants,
  Orders,
  OrderItems,
  Payments,
  Shifts,
  CashActivities,
  Ingredients,
  Recipes,
  RecipeIngredients,
  OutletStocks,
  RecipeHppSnapshots
])
class AppDatabase extends _$AppDatabase {
  AppDatabase() : super(_openConnection());

  AppDatabase.withExecutor(QueryExecutor executor) : super(executor);

  Future<Set<String>> protectedSyncIds(String table) async {
    final queries = <String, String>{
      'order_items':
          'SELECT id FROM order_items WHERE is_synced = 0 OR order_id IN (SELECT id FROM orders WHERE is_synced = 0)',
      'payments':
          'SELECT id FROM payments WHERE is_synced = 0 OR order_id IN (SELECT id FROM orders WHERE is_synced = 0)',
      'cash_activities':
          'SELECT id FROM cash_activities WHERE is_synced = 0 OR shift_id IN (SELECT id FROM shifts WHERE is_synced = 0)',
      'orders':
          'SELECT id FROM orders WHERE is_synced = 0 UNION SELECT order_id FROM order_items WHERE is_synced = 0 UNION SELECT order_id FROM payments WHERE is_synced = 0',
      'shifts':
          'SELECT id FROM shifts WHERE is_synced = 0 UNION SELECT shift_id FROM cash_activities WHERE is_synced = 0 UNION SELECT shift_session_id FROM orders WHERE is_synced = 0 UNION SELECT shift_session_id FROM payments WHERE is_synced = 0',
      'products':
          'SELECT id FROM products WHERE is_synced = 0 UNION SELECT product_id FROM order_items WHERE is_synced = 0',
      'product_variants':
          'SELECT id FROM product_variants WHERE is_synced = 0 UNION SELECT product_variant_id FROM order_items WHERE is_synced = 0',
    };
    final query =
        queries[table] ?? 'SELECT id FROM "$table" WHERE is_synced = 0';
    return (await customSelect(query).get())
        .map((r) => r.readNullable<String>('id'))
        .whereType<String>()
        .toSet();
  }

  Future<void> clearAccessCaches() async {
    await transaction(() async {
      for (final table in [
        'order_items',
        'payments',
        'cash_activities',
        'orders',
        'shifts',
        'products',
        'product_variants',
        'ingredients',
        'recipes',
        'recipe_ingredients',
        'outlet_stocks'
      ]) {
        final protected = await protectedSyncIds(table);
        final ids =
            (await customSelect('SELECT id FROM "$table" WHERE is_synced = 1')
                    .get())
                .map((r) => r.read<String>('id'))
                .where((id) => !protected.contains(id));
        for (final id in ids) {
          await customStatement('DELETE FROM "$table" WHERE id = ?', [id]);
        }
      }
      await delete(recipeHppSnapshots).go();
    });
  }

  @override
  int get schemaVersion => 8;

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
          if (from < 7) {
            // Migration 090 — varian produk (Hot/Ice, size, level gula).
            // Tabel baru, pull-only. Device yang upgrade mulai kosong lalu
            // keisi di sync berikutnya: `last_sync_hlc` device lama nunjuk ke
            // masa lalu, dan varian yang udah ada `updated_at`-nya lebih baru
            // dari situ, jadi semuanya ketarik tanpa perlu reset sync.
            await m.createTable(productVariants);
          }
          if (from < 8) {
            await m.addColumn(ingredients, ingredients.needsReview);
            await m.addColumn(recipes, recipes.isEstimated);
            await m.createTable(recipeHppSnapshots);
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

  Future<List<ShiftLocal>> getUnsyncedShifts(String outletId) => (select(shifts)
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
