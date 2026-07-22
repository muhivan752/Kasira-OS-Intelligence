import 'package:drift/drift.dart' show OrderingTerm;
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/database/app_database.dart';
import '../../../core/sync/sync_provider.dart';

/// Varian produk (Hot/Ice, size, level gula) — dibaca dari Drift lokal.
///
/// SELALU dari Drift, nggak pernah lewat HTTP. Varian dipakai persis di detik
/// kasir nge-tap produk, dan itu harus jalan waktu sinyal mati — kalau di sini
/// nembak jaringan, warung yang wifinya putus langsung nggak bisa jualan Es
/// Kopi. Datanya masuk lewat sync pull (`sync_service._applyServerChanges`).
class ProductVariantModel {
  final String id;
  final String productId;
  final String name;

  /// SELISIH dari harga produk, bukan harga akhir. Boleh negatif.
  final double priceAdjustment;

  const ProductVariantModel({
    required this.id,
    required this.productId,
    required this.name,
    required this.priceAdjustment,
  });

  /// Harga jual final varian ini untuk produk dengan harga [basePrice].
  ///
  /// SATU-SATUNYA tempat harga varian dihitung di sisi Flutter. Jangan tulis
  /// `product.price + variant.priceAdjustment` di widget — begitu ada dua
  /// tempat, salah satunya bakal ketinggalan pas rumusnya berubah. Cerminan
  /// `variant_price()` di `backend/services/variant_utils.py`.
  ///
  /// Di-clamp ke 0 sama kayak backend: harga jual minus bikin total order minus.
  double priceFor(double basePrice) {
    final p = basePrice + priceAdjustment;
    return p < 0 ? 0 : p;
  }

  /// Label selisih buat ditampilin di tombol varian: "+Rp2.000" / "-Rp3.000".
  /// String kosong kalau nggak ada selisih — nulis "+Rp0" cuma bikin ramai.
  String adjustmentLabel() {
    if (priceAdjustment == 0) return '';
    final sign = priceAdjustment > 0 ? '+' : '-';
    final abs = priceAdjustment.abs();
    return '${sign}Rp${_thousands(abs)}';
  }

  static String _thousands(double v) {
    final s = v.round().toString();
    final buf = StringBuffer();
    for (var i = 0; i < s.length; i++) {
      if (i > 0 && (s.length - i) % 3 == 0) buf.write('.');
      buf.write(s[i]);
    }
    return buf.toString();
  }

  factory ProductVariantModel.fromLocal(ProductVariantLocal v) =>
      ProductVariantModel(
        id: v.id,
        productId: v.productId,
        name: v.name,
        priceAdjustment: v.priceAdjustment,
      );
}

/// Semua varian aktif, dikelompokkan per productId.
///
/// Sengaja satu query untuk seluruh produk, bukan per-produk pas di-tap: grid
/// POS perlu tahu produk mana yang PUNYA varian buat nentuin tap-nya langsung
/// masuk keranjang atau buka pemilih. Query per-tap juga bikin jeda yang
/// kerasa pas antrean panjang.
final productVariantsProvider =
    FutureProvider<Map<String, List<ProductVariantModel>>>((ref) async {
  final db = ref.watch(databaseProvider);

  // Tiga filter, semuanya perlu:
  //   isDeleted  — varian yang dicabut pemilik ikut ketarik sync (server
  //                sengaja nggak nyaring, biar device tahu harus buang).
  //   isActive   — dimatikan sementara (es batu habis), barisnya masih ada.
  //   Urutan     — sortOrder dulu, biar sama persis dengan dashboard & struk.
  final rows = await (db.select(db.productVariants)
        ..where((t) => t.isDeleted.equals(false))
        ..where((t) => t.isActive.equals(true))
        ..orderBy([
          (t) => OrderingTerm(expression: t.sortOrder),
          (t) => OrderingTerm(expression: t.name),
        ]))
      .get();

  final map = <String, List<ProductVariantModel>>{};
  for (final r in rows) {
    map.putIfAbsent(r.productId, () => []).add(ProductVariantModel.fromLocal(r));
  }
  return map;
});
