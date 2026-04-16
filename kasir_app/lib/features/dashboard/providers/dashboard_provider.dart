import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../../../core/config/app_config.dart';

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
    const storage = FlutterSecureStorage();
    final results = await Future.wait([
      storage.read(key: 'access_token'),
      storage.read(key: 'tenant_id'),
      storage.read(key: 'outlet_id'),
    ]);
    final token = results[0];
    final tenantId = results[1];
    final outletId = results[2];

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
