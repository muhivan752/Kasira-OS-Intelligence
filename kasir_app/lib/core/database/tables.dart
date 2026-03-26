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
  TextColumn get sku => text().nullable()();
  TextColumn get barcode => text().nullable()();
  TextColumn get imageUrl => text().nullable()();
  BoolColumn get stockEnabled => boolean().withDefault(const Constant(false))();
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
