import 'package:dio/dio.dart';

import '../config/app_config.dart';
import 'printer_service.dart';
import 'session_cache.dart';

/// Jalur struk untuk pembayaran tab / split bill.
///
/// Dulu semua logika ini kekunci di dalam `_autoPrint*` milik `pay_split_modal`
/// dan `pay_items_modal` — jadi struk cuma bisa keluar SEKALI, di detik
/// pembayaran, dan cuma kalau printer kebetulan nyala. Begitu modal-nya ketutup,
/// gak ada lagi cara nyetak ulang struk split per-orang: Riwayat cuma nyimpen
/// struk order penuh (`buildReprintReceipt`), bukan porsi per orang.
///
/// Sekarang dipisah ke sini biar bisa dipanggil ulang dari mana aja — snackbar
/// sesudah bayar, tombol Struk permanen di halaman Tab, dan retry waktu printer
/// ternyata mati.
enum TabPrintResult {
  success,

  /// Printer belum tersambung. Dibedain dari [failed] biar pesan ke kasir bisa
  /// spesifik — "hubungkan printer" beda tindakan sama "coba lagi".
  notConnected,

  /// Gagal ambil data struk dari server, atau printer nolak byte-nya.
  failed,
}

Dio _dio() => Dio(BaseOptions(
      baseUrl: AppConfig.apiV1,
      connectTimeout: const Duration(seconds: 8),
      receiveTimeout: const Duration(seconds: 8),
    ));

TabPrintResult _mapOutcome(PrintOutcome o) => switch (o) {
      PrintOutcome.success => TabPrintResult.success,
      PrintOutcome.notConnected => TabPrintResult.notConnected,
      PrintOutcome.busy => TabPrintResult.failed,
      PrintOutcome.failed => TabPrintResult.failed,
    };

/// Struk satu porsi split bill (`/tabs/{id}/splits/{split_id}/receipt`).
Future<TabPrintResult> printTabSplitReceipt(
  PrinterNotifier printer, {
  required String tabId,
  required String splitId,
}) async {
  try {
    final res = await _dio().get(
      '/tabs/$tabId/splits/$splitId/receipt',
      options: Options(headers: SessionCache.instance.authHeaders),
    );
    final data = res.data['data'] as Map<String, dynamic>?;
    if (data == null) return TabPrintResult.failed;
    final bytes = buildSplitReceipt(SplitReceiptData.fromJson(data));
    final outcome = await printer.printBytesWithOutcome(bytes);
    return _mapOutcome(outcome);
  } catch (_) {
    return TabPrintResult.failed;
  }
}

/// Pay-full: satu struk per order di tab.
///
/// Sukses kalau MINIMAL satu order kecetak — tab bisa punya order yang datanya
/// gak lengkap, dan itu gak boleh bikin seluruh cetakan dianggap gagal.
Future<TabPrintResult> printTabFullReceipt(
  PrinterNotifier printer, {
  required List<String> orderIds,
}) async {
  if (orderIds.isEmpty) return TabPrintResult.failed;
  final dio = _dio();
  var anySuccess = false;
  var sawNotConnected = false;

  for (final orderId in orderIds) {
    try {
      final res = await dio.get(
        '/orders/$orderId/receipt',
        options: Options(headers: SessionCache.instance.authHeaders),
      );
      final data = res.data['data'] as Map<String, dynamic>?;
      if (data == null) continue;
      final bytes = buildReceipt(ReceiptData.fromJson(data));
      final outcome = await printer.printBytesWithOutcome(bytes);
      if (outcome == PrintOutcome.success) {
        anySuccess = true;
      } else if (outcome == PrintOutcome.notConnected) {
        // Printer mati — order berikutnya pasti kena nasib sama, stop di sini
        // daripada nembak endpoint sisanya percuma.
        sawNotConnected = true;
        break;
      }
    } catch (_) {
      // Skip order ini, lanjut ke berikutnya.
    }
  }

  if (anySuccess) return TabPrintResult.success;
  return sawNotConnected ? TabPrintResult.notConnected : TabPrintResult.failed;
}

/// Struk subset item (warkop pattern / pay-items) — `?payment_id=` bikin backend
/// motong strukna cuma ke item yang dibayar di transaksi itu.
Future<TabPrintResult> printTabItemsReceipt(
  PrinterNotifier printer, {
  required String orderId,
  required String paymentId,
  required String tabNumber,
  required bool isTabPaid,
  required double outstandingAmount,
  required int outstandingItemCount,
}) async {
  try {
    final res = await _dio().get(
      '/orders/$orderId/receipt',
      queryParameters: {'payment_id': paymentId},
      options: Options(headers: SessionCache.instance.authHeaders),
    );
    final data = res.data['data'] as Map<String, dynamic>?;
    if (data == null) return TabPrintResult.failed;
    final bytes = buildItemsReceipt(ItemsReceiptData.fromJson(
      data,
      tabNumber: tabNumber,
      isTabPaid: isTabPaid,
      outstandingAmount: outstandingAmount,
      outstandingItemCount: outstandingItemCount,
    ));
    final outcome = await printer.printBytesWithOutcome(bytes);
    return _mapOutcome(outcome);
  } catch (_) {
    return TabPrintResult.failed;
  }
}

/// Cari (orderId, paymentId) dari item-item yang barusan dibayar.
///
/// Dipakai dua-duanya: nyetak struk subset dan ngirimnya via WA. Balik `null`
/// kalau backend belum sempat nempelin `paid_payment_id` — caller wajib nangani,
/// jangan diasumsikan selalu ada.
Future<({String orderId, String paymentId})?> resolveTabItemsReceiptTarget({
  required String tabId,
  required List<String> itemIds,
}) async {
  if (itemIds.isEmpty) return null;
  try {
    final res = await _dio().get(
      '/tabs/$tabId/items',
      options: Options(headers: SessionCache.instance.authHeaders),
    );
    for (final it in (res.data['data'] as List?) ?? const []) {
      if (itemIds.contains(it['id']?.toString()) &&
          it['paid_payment_id'] != null) {
        final orderId = it['order_id']?.toString();
        if (orderId == null) continue;
        return (
          orderId: orderId,
          paymentId: it['paid_payment_id'].toString(),
        );
      }
    }
    return null;
  } catch (_) {
    return null;
  }
}
