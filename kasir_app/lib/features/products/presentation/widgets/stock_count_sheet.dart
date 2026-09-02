import 'package:dio/dio.dart';
import 'package:flutter/material.dart';

import '../../../../core/config/app_config.dart';
import '../../../../core/services/session_cache.dart';
import '../../../../core/theme/kasira_ds.dart';

/// Stok opname satu produk: ketik angka fisik → POST /products/{id}/stock-count.
///
/// Dipakai dari tab Produk (tile produk) dan tab Stok (daftar restok), supaya
/// tanda "terjual lebih dari tercatat" bisa dibereskan dari tempat mana pun
/// kasir kebetulan melihatnya.
Future<void> showStockCountSheet(
  BuildContext context, {
  required String productId,
  required String name,
  required int stock,
  required int oversellQty,
  VoidCallback? onDone,
}) async {
  final messenger = ScaffoldMessenger.of(context);
  final ctrl = TextEditingController(text: '$stock');
  final ok = await showModalBottomSheet<bool>(
    context: context,
    isScrollControlled: true,
    backgroundColor: Colors.transparent,
    builder: (ctx) => Padding(
      padding: EdgeInsets.only(bottom: MediaQuery.of(ctx).viewInsets.bottom),
      child: Container(
        padding: const EdgeInsets.fromLTRB(20, 16, 20, 28),
        decoration: const BoxDecoration(
          color: KasiraDS.surfaceCard,
          borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Hitung fisik $name', style: KasiraDS.display(size: 20)),
            const SizedBox(height: 6),
            Text(
              oversellQty > 0
                  ? 'Tercatat $stock, tapi terjual $oversellQty lebih dari itu. Hitung yang ada di rak sekarang, lalu masukkan angkanya. Kalau lebih kecil dari tercatat, selisihnya masuk Keuangan sebagai selisih stok.'
                  : 'Tercatat $stock. Hitung yang ada di rak, lalu masukkan angkanya.',
              style: KasiraDS.sans(size: 13, color: KasiraDS.textMuted),
            ),
            const SizedBox(height: 16),
            TextField(
              controller: ctrl,
              autofocus: true,
              keyboardType: TextInputType.number,
              decoration: InputDecoration(
                labelText: 'Jumlah fisik',
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
              ),
            ),
            const SizedBox(height: 16),
            SizedBox(
              width: double.infinity,
              height: 52,
              child: ElevatedButton(
                onPressed: () => Navigator.pop(ctx, true),
                child: const Text('Catat hasil hitung', style: TextStyle(fontWeight: FontWeight.bold)),
              ),
            ),
          ],
        ),
      ),
    ),
  );
  if (ok != true) return;
  final counted = int.tryParse(ctrl.text.trim());
  if (counted == null || counted < 0) return;
  try {
    final cache = SessionCache.instance;
    final dio = Dio(BaseOptions(
      baseUrl: AppConfig.apiV1,
      connectTimeout: const Duration(seconds: 15),
      receiveTimeout: const Duration(seconds: 15),
    ));
    final res = await dio.post(
      '/products/$productId/stock-count',
      options: Options(headers: cache.authHeaders),
      data: {'outlet_id': cache.outletId, 'counted_qty': counted},
    );
    messenger.showSnackBar(SnackBar(
      content: Text(res.data['message']?.toString() ?? 'Hasil hitung dicatat'),
      behavior: SnackBarBehavior.floating,
      duration: const Duration(seconds: 4),
    ));
    onDone?.call();
  } on DioException catch (e) {
    messenger.showSnackBar(SnackBar(
      content: Text((e.response?.data?['detail'] ?? 'Gagal mencatat hasil hitung. Butuh koneksi.').toString()),
      backgroundColor: KasiraDS.danger,
      behavior: SnackBarBehavior.floating,
    ));
  }
}
