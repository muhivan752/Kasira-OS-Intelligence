import 'dart:io';
import 'package:drift/drift.dart';
import 'package:drift/native.dart';
import 'package:path_provider/path_provider.dart';
import 'package:path/path.dart' as p;

import 'tables.dart';

part 'app_database.g.dart';

@DriftDatabase(tables: [Products, Orders, OrderItems, Payments, Shifts, CashActivities, Ingredients, Recipes, RecipeIngredients])
class AppDatabase extends _$AppDatabase {
  AppDatabase() : super(_openConnection());

  @override
  int get schemaVersion => 3;

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
        },
      );

  // Helper method to get unsynced records
  Future<List<ProductLocal>> getUnsyncedProducts() => 
      (select(products)..where((t) => t.isSynced.equals(false))).get();
      
  Future<List<OrderLocal>> getUnsyncedOrders() => 
      (select(orders)..where((t) => t.isSynced.equals(false))).get();
      
  Future<List<OrderItemLocal>> getUnsyncedOrderItems() => 
      (select(orderItems)..where((t) => t.isSynced.equals(false))).get();
      
  Future<List<PaymentLocal>> getUnsyncedPayments() => 
      (select(payments)..where((t) => t.isSynced.equals(false))).get();
      
  Future<List<ShiftLocal>> getUnsyncedShifts() => 
      (select(shifts)..where((t) => t.isSynced.equals(false))).get();
      
  Future<List<CashActivityLocal>> getUnsyncedCashActivities() => 
      (select(cashActivities)..where((t) => t.isSynced.equals(false))).get();
}

LazyDatabase _openConnection() {
  return LazyDatabase(() async {
    final dbFolder = await getApplicationDocumentsDirectory();
    final file = File(p.join(dbFolder.path, 'kasira_pos.sqlite'));
    return NativeDatabase.createInBackground(file);
  });
}
