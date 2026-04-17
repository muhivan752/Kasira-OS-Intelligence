import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:dio/dio.dart';
import '../../../core/config/app_config.dart';
import '../../../core/services/session_cache.dart';

// ─── Models ──────────────────────────────────────────────────────────────────

class DapurOrderItem {
  final String productName;
  final int qty;
  final String? notes;

  const DapurOrderItem({
    required this.productName,
    required this.qty,
    this.notes,
  });

  factory DapurOrderItem.fromJson(Map<String, dynamic> json) => DapurOrderItem(
        productName: json['product_name'] as String? ?? json['name'] as String? ?? '?',
        qty: (json['qty'] as num?)?.toInt() ?? 1,
        notes: json['notes'] as String?,
      );
}

class DapurOrder {
  final String id;
  final String displayNumber;
  final String status; // pending | preparing | ready | done
  final String orderType; // Dine In | Takeaway
  final String? tableNumber;
  final List<DapurOrderItem> items;
  final DateTime createdAt;
  final int rowVersion;

  const DapurOrder({
    required this.id,
    required this.displayNumber,
    required this.status,
    required this.orderType,
    this.tableNumber,
    required this.items,
    required this.createdAt,
    required this.rowVersion,
  });

  factory DapurOrder.fromJson(Map<String, dynamic> json) {
    final rawItems = json['items'] as List? ?? [];
    return DapurOrder(
      id: json['id'] as String,
      displayNumber: json['display_number'] as String? ??
          (json['id'] as String).substring(0, 8).toUpperCase(),
      status: json['status'] as String? ?? 'pending',
      orderType: json['order_type'] as String? ?? 'Dine In',
      tableNumber: json['table_number'] as String?,
      items: rawItems
          .map((e) => DapurOrderItem.fromJson(e as Map<String, dynamic>))
          .toList(),
      createdAt: DateTime.tryParse(json['created_at'] as String? ?? '') ??
          DateTime.now(),
      rowVersion: (json['row_version'] as num?)?.toInt() ?? 0,
    );
  }

  /// Minutes elapsed since order was created
  int get elapsedMinutes =>
      DateTime.now().difference(createdAt).inMinutes;

  bool get isUrgent => elapsedMinutes >= 15;
  bool get isWarning => elapsedMinutes >= 10 && elapsedMinutes < 15;

  DapurOrder copyWith({String? status, int? rowVersion}) => DapurOrder(
        id: id,
        displayNumber: displayNumber,
        status: status ?? this.status,
        orderType: orderType,
        tableNumber: tableNumber,
        items: items,
        createdAt: createdAt,
        rowVersion: rowVersion ?? this.rowVersion,
      );
}

// ─── State ───────────────────────────────────────────────────────────────────

class DapurState {
  final List<DapurOrder> activeOrders; // pending + preparing + ready
  final List<DapurOrder> completedOrders; // done (today)
  final bool isLoading;
  final String? error;
  final DateTime? lastRefreshed;

  const DapurState({
    this.activeOrders = const [],
    this.completedOrders = const [],
    this.isLoading = false,
    this.error,
    this.lastRefreshed,
  });

  DapurState copyWith({
    List<DapurOrder>? activeOrders,
    List<DapurOrder>? completedOrders,
    bool? isLoading,
    String? error,
    DateTime? lastRefreshed,
  }) =>
      DapurState(
        activeOrders: activeOrders ?? this.activeOrders,
        completedOrders: completedOrders ?? this.completedOrders,
        isLoading: isLoading ?? this.isLoading,
        error: error,
        lastRefreshed: lastRefreshed ?? this.lastRefreshed,
      );
}

// ─── Notifier ────────────────────────────────────────────────────────────────

class DapurNotifier extends StateNotifier<DapurState> {
  Timer? _pollTimer;
  final _cache = SessionCache.instance;

  DapurNotifier() : super(const DapurState());

  Dio get _dio => Dio(BaseOptions(
        baseUrl: AppConfig.apiV1,
        connectTimeout: const Duration(seconds: 8),
        receiveTimeout: const Duration(seconds: 8),
      ));

  Map<String, String> get _headers => {
    ..._cache.authHeaders,
    if (_cache.outletId != null) 'X-Outlet-ID': _cache.outletId!,
  };

  /// Start auto-polling every [intervalSeconds] seconds
  void startPolling({int intervalSeconds = 8}) {
    _pollTimer?.cancel();
    fetchOrders(); // immediate first fetch
    _pollTimer = Timer.periodic(
      Duration(seconds: intervalSeconds),
      (_) => fetchOrders(silent: true),
    );
  }

  void stopPolling() {
    _pollTimer?.cancel();
    _pollTimer = null;
  }

  Future<void> fetchOrders({bool silent = false}) async {
    if (!silent) state = state.copyWith(isLoading: true, error: null);

    try {
      final headers = _headers;
      final outletId = _cache.outletId;

      // Active orders: pending + preparing + ready
      final activeRes = await _dio.get(
        '/orders/',
        queryParameters: {
          if (outletId != null) 'outlet_id': outletId,
          'status': 'pending,preparing,ready',
          'limit': 50,
        },
        options: Options(headers: headers),
      );

      // Completed today
      final doneRes = await _dio.get(
        '/orders/',
        queryParameters: {
          if (outletId != null) 'outlet_id': outletId,
          'status': 'done',
          'limit': 30,
          'today': true,
        },
        options: Options(headers: headers),
      );

      final activeList = (activeRes.data['data'] as List? ?? [])
          .map((e) => DapurOrder.fromJson(e as Map<String, dynamic>))
          .toList();

      // Sort: pending first, then preparing, then ready; within same status by time asc
      activeList.sort((a, b) {
        const priority = {'pending': 0, 'preparing': 1, 'ready': 2};
        final p = (priority[a.status] ?? 3).compareTo(priority[b.status] ?? 3);
        if (p != 0) return p;
        return a.createdAt.compareTo(b.createdAt);
      });

      final doneList = (doneRes.data['data'] as List? ?? [])
          .map((e) => DapurOrder.fromJson(e as Map<String, dynamic>))
          .toList();

      state = state.copyWith(
        activeOrders: activeList,
        completedOrders: doneList,
        isLoading: false,
        lastRefreshed: DateTime.now(),
      );
    } on DioException catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.response?.statusCode == 401
            ? 'Sesi habis, login ulang'
            : 'Gagal memuat pesanan',
      );
    } catch (_) {
      state = state.copyWith(isLoading: false, error: 'Gagal memuat pesanan');
    }
  }

  /// Update status of a single order, returns true on success
  Future<bool> updateStatus(DapurOrder order, String newStatus) async {
    try {
      final headers = _headers;
      await _dio.put(
        '/orders/${order.id}/status',
        data: {
          'status': newStatus,
          'row_version': order.rowVersion,
        },
        options: Options(headers: headers),
      );

      // Optimistically update local state
      final updatedActive = state.activeOrders
          .map((o) => o.id == order.id
              ? o.copyWith(status: newStatus, rowVersion: order.rowVersion + 1)
              : o)
          .where((o) => o.status != 'done')
          .toList();

      state = state.copyWith(activeOrders: updatedActive);

      // Refresh to sync with server
      await fetchOrders(silent: true);
      return true;
    } on DioException catch (e) {
      if (e.response?.statusCode == 409) {
        // Optimistic lock conflict → force refresh
        await fetchOrders(silent: true);
      }
      return false;
    }
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    super.dispose();
  }
}

final dapurProvider = StateNotifierProvider<DapurNotifier, DapurState>(
  (ref) => DapurNotifier(),
);

// ─── Shift stats (today) ─────────────────────────────────────────────────────

class DapurStats {
  final int totalOrders;
  final int completedOrders;
  final int pendingOrders;
  final double avgMinutes; // avg time pending→done

  const DapurStats({
    required this.totalOrders,
    required this.completedOrders,
    required this.pendingOrders,
    required this.avgMinutes,
  });
}

final dapurStatsProvider = Provider<DapurStats>((ref) {
  final state = ref.watch(dapurProvider);
  final total = state.activeOrders.length + state.completedOrders.length;
  final done = state.completedOrders.length;
  final pending = state.activeOrders.where((o) => o.status == 'pending').length;

  // Avg elapsed of completed orders (approximate — we don't store completion time locally)
  final avgMins = done > 0
      ? state.completedOrders
              .map((o) => o.elapsedMinutes.toDouble())
              .reduce((a, b) => a + b) /
          done
      : 0.0;

  return DapurStats(
    totalOrders: total,
    completedOrders: done,
    pendingOrders: pending,
    avgMinutes: avgMins,
  );
});
