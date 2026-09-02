import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:dio/dio.dart';
import 'package:connectivity_plus/connectivity_plus.dart';
import '../../../core/config/app_config.dart';
import '../../../core/offline/local_reads.dart';
import '../../../core/services/session_cache.dart';
import '../../../core/sync/sync_provider.dart';

class DashboardStats {
  final double revenueToday;
  final int orderCount;
  final double avgOrderValue;
  final String shiftStatus;
  // Shift otomatis (gelombang 2): siapa yang buka, sejak kapan, siapa saja
  // yang jaga, dan sesi yang kasnya belum dihitung.
  final String? shiftOpenedBy;
  final DateTime? shiftStartedAt;
  final List<String> shiftParticipants;
  final int uncountedShifts;
  final DateTime? uncountedSince;
  final List<Map<String, dynamic>> topProducts;
  final Map<String, double> paymentBreakdown;
  /// Angka dari data lokal karena server nggak kejangkau.
  final bool isOffline;
  /// Transaksi yang masih ngantre di HP, belum sampai server.
  final int pendingSync;

  const DashboardStats({
    required this.revenueToday,
    required this.orderCount,
    required this.avgOrderValue,
    required this.shiftStatus,
    this.shiftOpenedBy,
    this.shiftStartedAt,
    this.shiftParticipants = const [],
    this.uncountedShifts = 0,
    this.uncountedSince,
    required this.topProducts,
    required this.paymentBreakdown,
    this.isOffline = false,
    this.pendingSync = 0,
  });

  DashboardStats copyWith({double? revenueToday, int? orderCount, double? avgOrderValue,
      List<Map<String, dynamic>>? topProducts, bool? isOffline, int? pendingSync}) =>
      DashboardStats(
        revenueToday: revenueToday ?? this.revenueToday,
        orderCount: orderCount ?? this.orderCount,
        avgOrderValue: avgOrderValue ?? this.avgOrderValue,
        shiftStatus: shiftStatus,
        shiftOpenedBy: shiftOpenedBy,
        shiftStartedAt: shiftStartedAt,
        shiftParticipants: shiftParticipants,
        uncountedShifts: uncountedShifts,
        uncountedSince: uncountedSince,
        topProducts: topProducts ?? this.topProducts,
        paymentBreakdown: paymentBreakdown,
        isOffline: isOffline ?? this.isOffline,
        pendingSync: pendingSync ?? this.pendingSync,
      );

  factory DashboardStats.fromJson(Map<String, dynamic> json) {
    final breakdown = <String, double>{};
    final raw = json['payment_breakdown'] as Map<String, dynamic>? ?? {};
    raw.forEach((k, v) => breakdown[k] = (v as num).toDouble());

    return DashboardStats(
      revenueToday: (json['revenue_today'] as num? ?? 0).toDouble(),
      orderCount: (json['order_count'] as num? ?? 0).toInt(),
      avgOrderValue: (json['avg_order_value'] as num? ?? 0).toDouble(),
      shiftStatus: json['shift_status'] as String? ?? 'closed',
      shiftOpenedBy: json['shift_opened_by'] as String?,
      shiftStartedAt: DateTime.tryParse(json['shift_started_at']?.toString() ?? '')?.toLocal(),
      shiftParticipants: (json['shift_participants'] as List? ?? []).map((e) => e.toString()).toList(),
      uncountedShifts: (json['uncounted_shifts'] as num? ?? 0).toInt(),
      uncountedSince: DateTime.tryParse(json['uncounted_since']?.toString() ?? '')?.toLocal(),
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

  /// Offline-first (2 Sep 2026): server nggak kejangkau → angka dihitung dari
  /// Drift, jadi transaksi offline langsung kehitung di Beranda. Online →
  /// angka server DITAMBAH transaksi yang masih ngantre di HP (belum ada di
  /// server, jadi nggak dobel; begitu tersinkron dia pindah ke angka server).
  Future<DashboardStats> _fetch() async {
    final c = SessionCache.instance;
    final token = c.accessToken;
    final tenantId = c.tenantId;
    final outletId = c.outletId;
    final local = LocalReads(ref.read(databaseProvider));

    Future<DashboardStats> fromLocal() async {
      if (outletId == null) throw StateError('outlet');
      final json = await local.todayStats(outletId);
      final pending = await local.pendingSyncCount(outletId);
      return DashboardStats.fromJson(json).copyWith(isOffline: true, pendingSync: pending);
    }

    final conn = await Connectivity().checkConnectivity();
    if (conn.isEmpty || conn.contains(ConnectivityResult.none)) return fromLocal();

    final dio = Dio(BaseOptions(
      baseUrl: AppConfig.apiV1,
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 10),
    ));

    try {
      final resp = await dio.get(
        '/reports/daily',
        queryParameters: {'outlet_id': outletId},
        options: Options(headers: {
          if (token != null) 'Authorization': 'Bearer $token',
          if (tenantId != null) 'X-Tenant-ID': tenantId,
        }),
      );
      var stats = DashboardStats.fromJson(resp.data['data'] as Map<String, dynamic>);
      if (outletId != null) {
        final pending = await local.pendingSyncCount(outletId);
        if (pending > 0) {
          final extra = await local.todayStats(outletId, onlyUnsynced: true);
          final extraRevenue = (extra['revenue_today'] as num).toDouble();
          final extraCount = (extra['order_count'] as num).toInt();
          final revenue = stats.revenueToday + extraRevenue;
          final count = stats.orderCount + extraCount;
          stats = stats.copyWith(
            revenueToday: revenue,
            orderCount: count,
            avgOrderValue: count == 0 ? 0 : revenue / count,
            pendingSync: pending,
          );
        }
      }
      return stats;
    } on DioException catch (e) {
      if (e.response == null && outletId != null) return fromLocal();
      rethrow;
    }
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
/// jatuh ke teks cadangan "Toko Anda" — dan gak pernah berubah karena gak ada
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
