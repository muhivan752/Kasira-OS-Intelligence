import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:dio/dio.dart';
import '../../../core/config/app_config.dart';
import '../../../core/services/session_cache.dart';

class DashboardStats {
  final double revenueToday;
  final int orderCount;
  final double avgOrderValue;
  final String shiftStatus;
  final List<Map<String, dynamic>> topProducts;
  final Map<String, double> paymentBreakdown;

  const DashboardStats({
    required this.revenueToday,
    required this.orderCount,
    required this.avgOrderValue,
    required this.shiftStatus,
    required this.topProducts,
    required this.paymentBreakdown,
  });

  factory DashboardStats.fromJson(Map<String, dynamic> json) {
    final breakdown = <String, double>{};
    final raw = json['payment_breakdown'] as Map<String, dynamic>? ?? {};
    raw.forEach((k, v) => breakdown[k] = (v as num).toDouble());

    return DashboardStats(
      revenueToday: (json['revenue_today'] as num? ?? 0).toDouble(),
      orderCount: (json['order_count'] as num? ?? 0).toInt(),
      avgOrderValue: (json['avg_order_value'] as num? ?? 0).toDouble(),
      shiftStatus: json['shift_status'] as String? ?? 'closed',
      topProducts: (json['top_products'] as List? ?? [])
          .map((e) => e as Map<String, dynamic>)
          .toList(),
      paymentBreakdown: breakdown,
    );
  }
}

class DashboardNotifier extends AsyncNotifier<DashboardStats> {
  @override
  Future<DashboardStats> build() => _fetch();

  Future<DashboardStats> _fetch() async {
    final c = SessionCache.instance;
    final token = c.accessToken;
    final tenantId = c.tenantId;
    final outletId = c.outletId;

    final dio = Dio(BaseOptions(
      baseUrl: AppConfig.apiV1,
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 10),
    ));

    final resp = await dio.get(
      '/reports/daily',
      queryParameters: {'outlet_id': outletId},
      options: Options(headers: {
        if (token != null) 'Authorization': 'Bearer $token',
        if (tenantId != null) 'X-Tenant-ID': tenantId,
      }),
    );

    return DashboardStats.fromJson(resp.data['data'] as Map<String, dynamic>);
  }

  Future<void> refresh() async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(_fetch);
  }
}

final dashboardProvider = AsyncNotifierProvider<DashboardNotifier, DashboardStats>(
  DashboardNotifier.new,
);

/// Nama outlet buat sapaan Beranda.
///
/// SessionCache.outletName diisi lewat fetch fire-and-forget pas init, jadi
/// pas Beranda pertama kali dirender nilainya sering masih null dan sapaannya
/// jatuh ke teks cadangan "Toko kamu" — dan gak pernah berubah karena gak ada
/// yang nyuruh rebuild waktu fetch-nya kelar. Provider ini yang nungguin
/// fetch-nya, jadi begitu nama aslinya dapet, sapaannya ikut ke-update.
final outletNameProvider = FutureProvider<String?>((ref) async {
  final cache = SessionCache.instance;
  if (cache.outletName != null && cache.outletName!.isNotEmpty) {
    return cache.outletName;
  }
  await cache.fetchAndCacheOutletInfo();
  return cache.outletName;
});

/// Insight AI singkat buat Beranda (Pro). Fetch dari POST /ai/insight (Haiku,
/// cached server-side per jam). Return "" kalau gagal / non-Pro → card fallback
/// ke insight lokal dari data (biar tetap ada isi).
final aiInsightProvider = FutureProvider<String>((ref) async {
  if (!SessionCache.instance.isPro) return '';
  final stats = await ref.watch(dashboardProvider.future);
  final c = SessionCache.instance;
  final outletId = c.outletId;
  if (outletId == null) return '';
  try {
    final dio = Dio(BaseOptions(
      baseUrl: AppConfig.apiV1,
      connectTimeout: const Duration(seconds: 12),
      receiveTimeout: const Duration(seconds: 20),
    ));
    final resp = await dio.post(
      '/ai/insight',
      data: {
        'outlet_id': outletId,
        'revenue_today': stats.revenueToday,
        'order_count': stats.orderCount,
        'avg_order': stats.avgOrderValue,
        'top_products': stats.topProducts,
      },
      options: Options(headers: {
        if (c.accessToken != null) 'Authorization': 'Bearer ${c.accessToken}',
        if (c.tenantId != null) 'X-Tenant-ID': c.tenantId,
      }),
    );
    final data = resp.data is Map ? resp.data['data'] : null;
    return (data?['insight'] as String?)?.trim() ?? '';
  } catch (_) {
    return '';
  }
});
