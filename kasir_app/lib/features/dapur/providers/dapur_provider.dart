import 'dart:async';
import 'package:audioplayers/audioplayers.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:dio/dio.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../../../core/config/app_config.dart';
import '../../../core/services/session_cache.dart';

/// Papan dapur. Sumber: `GET /orders/kitchen` (backend, mig 102) yang
/// mengembalikan {active, done} berdasarkan `orders.kitchen_status`, BUKAN
/// status order. Dulu provider ini nembak `GET /orders/?status=pending,preparing,ready`
/// dan `status=done` yang ditolak server 422 sejak lahir, jadi app Dapur
/// nggak pernah nampilin satu pesanan pun.
///
/// Status di app: pending (= antrean, `queued` di server), preparing, ready, done.

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
        qty: (json['quantity'] as num?)?.toInt() ?? (json['qty'] as num?)?.toInt() ?? 1,
        notes: (json['notes'] as String?)?.trim().isEmpty ?? true ? null : (json['notes'] as String).trim(),
      );
}

class DapurOrder {
  final String id;
  final String displayNumber;
  final String status; // pending | preparing | ready | done
  final String orderType; // Makan di tempat | Ambil sendiri | Antar
  final String? tableNumber;
  final String? customerName;
  final String? notes;
  final bool isOnline;
  final List<DapurOrderItem> items;
  final DateTime createdAt;
  final int rowVersion;

  const DapurOrder({
    required this.id,
    required this.displayNumber,
    required this.status,
    required this.orderType,
    this.tableNumber,
    this.customerName,
    this.notes,
    this.isOnline = false,
    required this.items,
    required this.createdAt,
    required this.rowVersion,
  });

  static String _typeLabel(String? t) => switch (t) {
        'dine_in' => 'Makan di tempat',
        'delivery' => 'Antar',
        'takeaway' => 'Ambil sendiri',
        _ => t ?? '',
      };

  factory DapurOrder.fromJson(Map<String, dynamic> json) {
    final rawItems = json['items'] as List? ?? [];
    final ks = json['kitchen_status'] as String? ?? 'queued';
    return DapurOrder(
      id: json['id'] as String,
      displayNumber: json['display_number']?.toString() ??
          (json['id'] as String).substring(0, 8).toUpperCase(),
      status: ks == 'queued' ? 'pending' : ks,
      orderType: _typeLabel(json['order_type'] as String?),
      tableNumber: json['table_name'] as String?,
      customerName: json['customer_name'] as String?,
      notes: (json['notes'] as String?)?.trim().isEmpty ?? true ? null : (json['notes'] as String).trim(),
      isOnline: json['source'] == 'storefront',
      items: rawItems
          .map((e) => DapurOrderItem.fromJson(e as Map<String, dynamic>))
          .toList(),
      createdAt: (DateTime.tryParse(json['created_at'] as String? ?? '') ?? DateTime.now()).toLocal(),
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
        customerName: customerName,
        notes: notes,
        isOnline: isOnline,
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
  final AudioPlayer _player = AudioPlayer();
  Set<String> _knownIds = {};
  bool _primed = false;

  static const prefSound = 'dapur_sound';
  static const prefInterval = 'dapur_poll_interval';

  DapurNotifier() : super(const DapurState());

  /// Pengaturan tersimpan (dulu toggle di halaman Pengaturan cuma setState).
  static Future<(bool, int)> loadPrefs() async {
    try {
      final p = await SharedPreferences.getInstance();
      return (p.getBool(prefSound) ?? true, (p.getInt(prefInterval) ?? 8).clamp(5, 30));
    } catch (_) {
      return (true, 8);
    }
  }

  static Future<void> savePrefs({bool? sound, int? interval}) async {
    try {
      final p = await SharedPreferences.getInstance();
      if (sound != null) await p.setBool(prefSound, sound);
      if (interval != null) await p.setInt(prefInterval, interval);
    } catch (_) {}
  }

  Future<void> _ring() async {
    final (sound, _) = await loadPrefs();
    if (!sound) return;
    try {
      HapticFeedback.heavyImpact();
      await _player.stop();
      await _player.play(AssetSource('sounds/order_bell.wav'), volume: 1.0);
    } catch (_) {}
  }

  Future<void> testRing() => _ring();

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
      final outletId = _cache.outletId;
      final res = await _dio.get(
        '/orders/kitchen',
        queryParameters: {if (outletId != null) 'outlet_id': outletId},
        options: Options(headers: _headers),
      );
      final data = res.data['data'] as Map<String, dynamic>;
      final activeList = (data['active'] as List? ?? [])
          .map((e) => DapurOrder.fromJson(e as Map<String, dynamic>))
          .toList();
      activeList.sort((a, b) {
        const priority = {'pending': 0, 'preparing': 1, 'ready': 2};
        final p = (priority[a.status] ?? 3).compareTo(priority[b.status] ?? 3);
        if (p != 0) return p;
        return a.createdAt.compareTo(b.createdAt);
      });
      final doneList = (data['done'] as List? ?? [])
          .map((e) => DapurOrder.fromJson(e as Map<String, dynamic>))
          .toList();

      // Bel cuma untuk pesanan yang BARU muncul sesudah tarikan pertama.
      final fresh = activeList.where((o) => !_knownIds.contains(o.id)).toList();
      _knownIds = {...activeList.map((o) => o.id), ...doneList.map((o) => o.id)};
      if (_primed && fresh.isNotEmpty) _ring();
      _primed = true;

      state = state.copyWith(
        activeOrders: activeList,
        completedOrders: doneList,
        isLoading: false,
        lastRefreshed: DateTime.now(),
      );
    } on DioException catch (e) {
      final detail = e.response?.data is Map ? (e.response!.data['detail']?.toString()) : null;
      state = state.copyWith(
        isLoading: false,
        error: e.response?.statusCode == 401
            ? 'Sesi habis, login ulang'
            : e.response?.statusCode == 403
                ? (detail ?? 'Layar dapur belum diaktifkan')
                : e.response == null
                    ? 'Tidak ada koneksi'
                    : 'Gagal memuat pesanan',
      );
    } catch (_) {
      state = state.copyWith(isLoading: false, error: 'Gagal memuat pesanan');
    }
  }

  /// Update status of a single order, returns true on success
  Future<bool> updateStatus(DapurOrder order, String newStatus) async {
    try {
      await _dio.post(
        '/orders/${order.id}/kitchen-status',
        data: {'status': newStatus},
        options: Options(headers: _headers),
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
    _player.dispose();
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
