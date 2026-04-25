import 'package:drift/drift.dart';

// Mixin for CRDT fields
mixin CrdtTable on Table {
  TextColumn get id => text()();
  IntColumn get rowVersion => integer().withDefault(const Constant(0))();
  BoolColumn get isDeleted => boolean().withDefault(const Constant(false))();
  TextColumn get lastModifiedHlc => text().nullable()();
  BoolColumn get isSynced => boolean().withDefault(const Constant(true))();
  
  @override
  Set<Column> get primaryKey => {id};
}

@DataClassName('ProductLocal')
class Products extends Table with CrdtTable {
  TextColumn get brandId => text()();
  TextColumn get categoryId => text().nullable()();
  TextColumn get name => text()();
  TextColumn get description => text().nullable()();
  RealColumn get basePrice => real()();
  // Harga beli (modal) — Starter margin tracking. Nullable agar bisa
  // bedakan "belum diisi" vs "diisi 0". Beda dari Ingredient.buyPrice
  // yang default 0 (Pro recipe selalu butuh angka).
  RealColumn get buyPrice => real().nullable()();
  TextColumn get sku => text().nullable()();
  TextColumn get barcode => text().nullable()();
  TextColumn get imageUrl => text().nullable()();
  BoolColumn get stockEnabled => boolean().withDefault(const Constant(false))();
  // CRDT PNCounter untuk stock — pure CRDT, tidak pernah overwrite
  // Format JSON: {"deviceNodeId": count}
  TextColumn get crdtPositive => text().withDefault(const Constant('{}'))(); // restock
  TextColumn get crdtNegative => text().withDefault(const Constant('{}'))(); // sale
  // Cache computed dari CRDT — bisa direcompute kapanpun
  RealColumn get stockQty => real().withDefault(const Constant(0.0))();
  BoolColumn get isActive => boolean().withDefault(const Constant(true))();
}

@DataClassName('OrderLocal')
class Orders extends Table with CrdtTable {
  TextColumn get outletId => text()();
  TextColumn get shiftSessionId => text().nullable()();
  TextColumn get customerId => text().nullable()();
  TextColumn get tableId => text().nullable()();
  TextColumn get userId => text().nullable()();
  TextColumn get orderNumber => text()();
  IntColumn get displayNumber => integer()();
  TextColumn get status => text().withDefault(const Constant('pending'))();
  TextColumn get orderType => text().withDefault(const Constant('dine_in'))();
  RealColumn get subtotal => real().withDefault(const Constant(0.0))();
  RealColumn get serviceChargeAmount => real().withDefault(const Constant(0.0))();
  RealColumn get taxAmount => real().withDefault(const Constant(0.0))();
  RealColumn get discountAmount => real().withDefault(const Constant(0.0))();
  RealColumn get totalAmount => real().withDefault(const Constant(0.0))();
  TextColumn get notes => text().nullable()();
  DateTimeColumn get createdAt => dateTime().nullable()();
  DateTimeColumn get updatedAt => dateTime().nullable()();
}

@DataClassName('OrderItemLocal')
class OrderItems extends Table with CrdtTable {
  TextColumn get orderId => text()();
  TextColumn get productId => text()();
  TextColumn get productVariantId => text().nullable()();
  IntColumn get quantity => integer()();
  RealColumn get unitPrice => real()();
  RealColumn get discountAmount => real().withDefault(const Constant(0.0))();
  RealColumn get totalPrice => real()();
  TextColumn get modifiers => text().nullable()(); // JSON string
  TextColumn get notes => text().nullable()();
  // Migration 085 — per-item ad-hoc payment (warkop pattern)
  // null = unpaid, set = item dibayar via /tabs/{id}/pay-items.
  // Server source of truth — Flutter cuma READ (push gak include).
  DateTimeColumn get paidAt => dateTime().nullable()();
  TextColumn get paidPaymentId => text().nullable()();
}

@DataClassName('PaymentLocal')
class Payments extends Table with CrdtTable {
  TextColumn get orderId => text()();
  TextColumn get outletId => text()();
  TextColumn get shiftSessionId => text().nullable()();
  RealColumn get amountDue => real()();
  RealColumn get amountPaid => real()();
  TextColumn get paymentMethod => text()();
  TextColumn get status => text().withDefault(const Constant('pending'))();
  TextColumn get referenceNumber => text().nullable()();
  DateTimeColumn get paidAt => dateTime().nullable()();
}

@DataClassName('ShiftLocal')
class Shifts extends Table with CrdtTable {
  TextColumn get outletId => text()();
  TextColumn get userId => text()();
  TextColumn get status => text().withDefault(const Constant('open'))();
  DateTimeColumn get startTime => dateTime()();
  DateTimeColumn get endTime => dateTime().nullable()();
  RealColumn get startingCash => real().withDefault(const Constant(0.0))();
  RealColumn get endingCash => real().nullable()();
  RealColumn get expectedEndingCash => real().nullable()();
  TextColumn get notes => text().nullable()();
}

@DataClassName('CashActivityLocal')
class CashActivities extends Table with CrdtTable {
  TextColumn get shiftId => text()();
  TextColumn get activityType => text()(); // income, expense
  RealColumn get amount => real()();
  TextColumn get description => text()();
}

@DataClassName('IngredientLocal')
class Ingredients extends Table with CrdtTable {
  TextColumn get brandId => text()();
  TextColumn get name => text()();
  TextColumn get trackingMode => text()(); // simple, detail
  TextColumn get baseUnit => text()(); // gram, ml, pcs
  TextColumn get unitType => text()(); // WEIGHT, VOLUME, COUNT, CUSTOM
  RealColumn get buyPrice => real().withDefault(const Constant(0.0))();
  RealColumn get buyQty => real().withDefault(const Constant(1.0))();
  RealColumn get costPerBaseUnit => real().withDefault(const Constant(0.0))();
  TextColumn get ingredientType => text().withDefault(const Constant('recipe'))();
}

@DataClassName('RecipeLocal')
class Recipes extends Table with CrdtTable {
  TextColumn get productId => text()();
  IntColumn get version => integer().withDefault(const Constant(1))();
  BoolColumn get isActive => boolean().withDefault(const Constant(true))();
  TextColumn get notes => text().nullable()();
}

@DataClassName('RecipeIngredientLocal')
class RecipeIngredients extends Table with CrdtTable {
  TextColumn get recipeId => text()();
  TextColumn get ingredientId => text()();
  RealColumn get quantity => real()();
  TextColumn get quantityUnit => text()();
  TextColumn get notes => text().nullable()();
  BoolColumn get isOptional => boolean().withDefault(const Constant(false))();
}

@DataClassName('OutletStockLocal')
class OutletStocks extends Table with CrdtTable {
  TextColumn get outletId => text()();
  TextColumn get ingredientId => text()();
  RealColumn get computedStock => real().withDefault(const Constant(0.0))();
  RealColumn get minStockBase => real().withDefault(const Constant(0.0))();
}
