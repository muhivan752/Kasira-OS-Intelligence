import 'package:drift/drift.dart' as drift;

import '../database/app_database.dart';
import '../../features/orders/providers/orders_provider.dart';

/// Sisi BACA offline-first.
///
/// CRDT sync selama ini cuma ngurus sisi TULIS (transaksi disimpan lokal,
/// dikirim belakangan). Sisi bacanya nggak pernah dikerjakan: Beranda,
/// Riwayat, dan stok kritis nembak server, jadi begitu sinyal hilang semua
/// halaman di luar Kasir jadi "Coba lagi" (kegigit tes offline Ivan, 2 Sep
/// 2026). Semua fungsi di sini baca dari Drift saja, tanpa jaringan, supaya:
///  - transaksi offline tetap kehitung di Beranda detik itu juga,
///  - Riwayat tetap tampil, yang belum sync cuma dikasih tanda,
///  - stok kritis tetap bisa dilihat dari angka lokal.
///
/// Rule #50: semua query di-scope ke outletId aktif.
class LocalReads {
  LocalReads(this.db);
  final AppDatabase db;

  static DateTime _startOfToday() {
    final n = DateTime.now();
    return DateTime(n.year, n.month, n.day);
  }

  /// Order hari ini (waktu lokal) di outlet ini, kecuali yang dibatalkan.
  /// `onlyUnsynced` = cuma yang belum sampai ke server (buat digabung ke
  /// angka server waktu online, tanpa dobel).
  Future<List<OrderLocal>> _todayOrders(String outletId, {bool onlyUnsynced = false}) {
    final q = db.select(db.orders)
      ..where((o) => o.outletId.equals(outletId))
      ..where((o) => o.isDeleted.equals(false))
      ..where((o) => o.status.equals('cancelled').not())
      ..where((o) => o.createdAt.isBiggerOrEqualValue(_startOfToday()));
    if (onlyUnsynced) q.where((o) => o.isSynced.equals(false));
    return q.get();
  }

  /// Angka Beranda dari data lokal. Bentuknya sama dengan `reports/daily`
  /// supaya `DashboardStats.fromJson` bisa dipakai apa adanya.
  Future<Map<String, dynamic>> todayStats(String outletId, {bool onlyUnsynced = false}) async {
    final orders = await _todayOrders(outletId, onlyUnsynced: onlyUnsynced);
    if (orders.isEmpty) {
      return {'revenue_today': 0, 'order_count': 0, 'avg_order_value': 0,
              'top_products': const [], 'payment_breakdown': const {}, 'shift_status': 'closed'};
    }
    final ids = orders.map((o) => o.id).toList();

    // Omzet = total order yang lunas. Order offline ditutup `completed` waktu
    // bayar tunai (cart_provider.savePaymentOffline), jadi status jadi acuan.
    final paidOrders = orders.where((o) => o.status == 'completed').toList();
    final revenue = paidOrders.fold<double>(0, (s, o) => s + o.totalAmount);

    final payments = await (db.select(db.payments)
          ..where((p) => p.orderId.isIn(ids))
          ..where((p) => p.status.equals('paid')))
        .get();
    final breakdown = <String, double>{};
    for (final p in payments) {
      breakdown[p.paymentMethod] = (breakdown[p.paymentMethod] ?? 0) + p.amountDue;
    }

    final items = await (db.select(db.orderItems)..where((i) => i.orderId.isIn(ids))).get();
    final byProduct = <String, ({int sold, double revenue})>{};
    for (final it in items) {
      final cur = byProduct[it.productId] ?? (sold: 0, revenue: 0.0);
      byProduct[it.productId] = (sold: cur.sold + it.quantity, revenue: cur.revenue + it.totalPrice);
    }
    final products = byProduct.isEmpty
        ? const <ProductLocal>[]
        : await (db.select(db.products)..where((p) => p.id.isIn(byProduct.keys.toList()))).get();
    final names = {for (final p in products) p.id: p.name};
    final top = byProduct.entries
        .map((e) => {'name': names[e.key] ?? 'Produk', 'sold': e.value.sold, 'revenue': e.value.revenue})
        .toList()
      ..sort((a, b) => (b['sold'] as int).compareTo(a['sold'] as int));

    return {
      'revenue_today': revenue,
      'order_count': paidOrders.length,
      'avg_order_value': paidOrders.isEmpty ? 0 : revenue / paidOrders.length,
      'top_products': top.take(5).toList(),
      'payment_breakdown': breakdown,
      'shift_status': 'closed',
    };
  }

  Future<int> pendingSyncCount(String outletId) async {
    final rows = await (db.select(db.orders)
          ..where((o) => o.outletId.equals(outletId))
          ..where((o) => o.isSynced.equals(false)))
        .get();
    return rows.length;
  }

  /// Riwayat dari lokal. `onlyUnsynced` buat digabung ke daftar server.
  Future<List<OrderModel>> recentOrders(String outletId, {int limit = 50, String? status, bool onlyUnsynced = false}) async {
    final q = db.select(db.orders)
      ..where((o) => o.outletId.equals(outletId))
      ..where((o) => o.isDeleted.equals(false))
      ..orderBy([(o) => drift.OrderingTerm.desc(o.createdAt)])
      ..limit(limit);
    if (status != null) q.where((o) => o.status.equals(status));
    if (onlyUnsynced) q.where((o) => o.isSynced.equals(false));
    final rows = await q.get();
    if (rows.isEmpty) return const [];
    final items = await (db.select(db.orderItems)..where((i) => i.orderId.isIn(rows.map((o) => o.id).toList()))).get();
    final productIds = items.map((i) => i.productId).toSet().toList();
    final products = productIds.isEmpty
        ? const <ProductLocal>[]
        : await (db.select(db.products)..where((p) => p.id.isIn(productIds))).get();
    final names = {for (final p in products) p.id: p.name};
    return rows.map((o) => _toModel(o, items.where((i) => i.orderId == o.id).toList(), names)).toList();
  }

  Future<OrderModel?> orderById(String orderId) async {
    final o = await (db.select(db.orders)..where((t) => t.id.equals(orderId))).getSingleOrNull();
    if (o == null) return null;
    final items = await (db.select(db.orderItems)..where((i) => i.orderId.equals(orderId))).get();
    final productIds = items.map((i) => i.productId).toSet().toList();
    final products = productIds.isEmpty
        ? const <ProductLocal>[]
        : await (db.select(db.products)..where((p) => p.id.isIn(productIds))).get();
    return _toModel(o, items, {for (final p in products) p.id: p.name});
  }

  OrderModel _toModel(OrderLocal o, List<OrderItemLocal> items, Map<String, String> names) => OrderModel(
        id: o.id,
        orderNumber: o.orderNumber,
        displayNumber: o.displayNumber,
        status: o.status,
        orderType: o.orderType,
        totalAmount: o.totalAmount,
        subtotal: o.subtotal,
        taxAmount: o.taxAmount,
        serviceChargeAmount: o.serviceChargeAmount,
        discountAmount: o.discountAmount,
        tableId: o.tableId,
        items: items
            .map((i) => OrderItemModel(
                  id: i.id,
                  productId: i.productId,
                  productName: names[i.productId] ?? 'Produk',
                  quantity: i.quantity,
                  unitPrice: i.unitPrice,
                  totalPrice: i.totalPrice,
                  notes: i.notes,
                ))
            .toList(),
        createdAt: o.createdAt ?? DateTime.now(),
        isSynced: o.isSynced,
      );

  /// Stok kritis dari angka lokal (mode sederhana). Produk tanpa stok
  /// diaktifkan nggak ikut.
  Future<List<ProductLocal>> lowStockProducts({int threshold = 10}) => (db.select(db.products)
        ..where((p) => p.stockEnabled.equals(true))
        ..where((p) => p.isActive.equals(true))
        ..where((p) => p.isDeleted.equals(false))
        ..where((p) => p.stockQty.isSmallerOrEqualValue(threshold.toDouble()))
        ..orderBy([(p) => drift.OrderingTerm.asc(p.stockQty)]))
      .get();
}
