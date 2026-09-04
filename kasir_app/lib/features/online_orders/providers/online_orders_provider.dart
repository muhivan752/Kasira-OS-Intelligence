import 'dart:async';
import 'dart:convert';

import 'package:audioplayers/audioplayers.dart';
import 'package:dio/dio.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

import '../../../core/config/app_config.dart';
import '../../../core/services/session_cache.dart';

/// Pesanan online (storefront) di app kasir.
///
/// Sumber kebenaran: `GET /orders/online` (daftar) + `GET /orders/stream`
/// (SSE, kabar real-time). SSE cuma pemicu: tiap event kita tarik ulang
/// daftarnya, jadi kalau koneksi putus dan nyambung lagi nggak ada pesanan
/// yang tertinggal. Polling 30 detik jalan terus sebagai jaring pengaman.
///
/// Bel: bunyi 3x waktu pesanan baru masuk, lalu pengingat tiap 45 detik
/// selama masih ada yang menunggu konfirmasi dan app di depan. Kafe ramai,
/// satu bunyi gampang kelewat.

double _toDouble(dynamic v) {
  if (v == null) return 0;
  if (v is num) return v.toDouble();
  return double.tryParse(v.toString()) ?? 0;
}

DateTime? _toDate(dynamic v) {
  if (v == null) return null;
  return DateTime.tryParse(v.toString())?.toLocal();
}

class OnlineOrderItem {
  final String productName;
  final int quantity;
  final double unitPrice;
  final double totalPrice;
  final String? notes;
  const OnlineOrderItem({required this.productName, required this.quantity, required this.unitPrice, required this.totalPrice, this.notes});

  factory OnlineOrderItem.fromJson(Map<String, dynamic> j) => OnlineOrderItem(
        productName: j['product_name'] as String? ?? 'Item',
        quantity: (j['quantity'] as num?)?.toInt() ?? 0,
        unitPrice: _toDouble(j['unit_price']),
        totalPrice: _toDouble(j['total_price']),
        notes: (j['notes'] as String?)?.trim().isEmpty ?? true ? null : (j['notes'] as String).trim(),
      );
}

class OnlineOrder {
  final String id;
  final int displayNumber;
  final String status; // pending | preparing | ready | served | completed | cancelled
  final String orderType; // takeaway | delivery | dine_in
  final double totalAmount;
  final String? customerName;
  final String? customerPhone;
  final String? notes;
  final String? deliveryAddress;
  final String? tableId;
  final String? tabId;
  final String? paymentMethod; // qris | cash | null (tagihan meja)
  final String? paymentStatus;
  /// 'xendit' (lunas otomatis) | 'manual' (QRIS statis toko, kasir yang memastikan).
  final String? paymentChannel;
  /// Bukti bayar yang pelanggan unggah dari halaman lacak (mig 104).
  final String? paymentProofUrl;
  final double? deliveryLat;
  final double? deliveryLng;
  final double? deliveryDistanceKm;
  final DateTime createdAt;
  final DateTime? acceptedAt;
  final int? etaMinutes;
  final DateTime? readyAt;
  final String? cancelReason;
  final int rowVersion;
  final List<OnlineOrderItem> items;

  const OnlineOrder({
    required this.id,
    required this.displayNumber,
    required this.status,
    required this.orderType,
    required this.totalAmount,
    this.customerName,
    this.customerPhone,
    this.notes,
    this.deliveryAddress,
    this.tableId,
    this.tabId,
    this.paymentMethod,
    this.paymentStatus,
    this.paymentChannel,
    this.paymentProofUrl,
    this.deliveryLat,
    this.deliveryLng,
    this.deliveryDistanceKm,
    required this.createdAt,
    this.acceptedAt,
    this.etaMinutes,
    this.readyAt,
    this.cancelReason,
    required this.rowVersion,
    required this.items,
  });

  factory OnlineOrder.fromJson(Map<String, dynamic> j) => OnlineOrder(
        id: j['id'] as String,
        displayNumber: (j['display_number'] as num?)?.toInt() ?? 0,
        status: j['status'] as String? ?? 'pending',
        orderType: j['order_type'] as String? ?? 'takeaway',
        totalAmount: _toDouble(j['total_amount']),
        customerName: j['customer_name'] as String?,
        customerPhone: j['customer_phone'] as String?,
        notes: (j['notes'] as String?)?.trim().isEmpty ?? true ? null : (j['notes'] as String).trim(),
        deliveryAddress: j['delivery_address'] as String?,
        tableId: j['table_id'] as String?,
        tabId: j['tab_id'] as String?,
        paymentMethod: j['payment_method'] as String?,
        paymentStatus: j['payment_status'] as String?,
        paymentChannel: j['payment_channel'] as String?,
        paymentProofUrl: j['payment_proof_url'] as String?,
        deliveryLat: j['delivery_lat'] == null ? null : _toDouble(j['delivery_lat']),
        deliveryLng: j['delivery_lng'] == null ? null : _toDouble(j['delivery_lng']),
        deliveryDistanceKm: j['delivery_distance_km'] == null ? null : _toDouble(j['delivery_distance_km']),
        createdAt: _toDate(j['created_at']) ?? DateTime.now(),
        acceptedAt: _toDate(j['accepted_at']),
        etaMinutes: (j['eta_minutes'] as num?)?.toInt(),
        readyAt: _toDate(j['ready_at']),
        cancelReason: j['cancel_reason'] as String?,
        rowVersion: (j['row_version'] as num?)?.toInt() ?? 0,
        items: (j['items'] as List? ?? []).map((e) => OnlineOrderItem.fromJson(e as Map<String, dynamic>)).toList(),
      );

  bool get isPending => status == 'pending';
  bool get isActive => status == 'pending' || status == 'preparing' || status == 'ready' || status == 'served';
  bool get isPaid => paymentStatus == 'paid' && paymentMethod == 'qris';
  /// Pesanan meja: bayarnya lewat tagihan meja (tab), bukan dari layar ini.
  bool get isTableTab => orderType == 'dine_in' && tabId != null;

  /// Label yang SAMA dengan halaman lacak pelanggan (app/[slug]/_ui.tsx).
  String get typeLabel => switch (orderType) {
        'delivery' => 'Antar ke alamat',
        'dine_in' => 'Makan di tempat',
        _ => 'Ambil sendiri',
      };

  String get paymentLabel {
    if (paymentMethod == 'qris') {
      if (isPaid) return 'Lunas QRIS';
      if (paymentChannel == 'manual') return paymentProofUrl != null ? 'QRIS toko, bukti masuk' : 'QRIS toko, cek bukti';
      return 'QRIS belum dibayar';
    }
    if (paymentMethod == 'cash') return orderType == 'delivery' ? 'Bayar saat diterima' : 'Bayar di kasir';
    return isTableTab ? 'Tagihan meja' : 'Belum ada pembayaran';
  }

  String get statusLabel => switch (status) {
        'pending' => 'Menunggu konfirmasi',
        'preparing' => 'Disiapkan',
        'ready' => orderType == 'delivery' ? 'Sedang diantar' : 'Siap diambil',
        'served' => 'Sudah diantar',
        'completed' => 'Selesai',
        'cancelled' => 'Dibatalkan',
        _ => status,
      };

  /// Nomor WA 62xxx untuk tombol chat, null kalau nggak ada.
  String? get waNumber {
    final raw = customerPhone;
    if (raw == null) return null;
    final d = raw.replaceAll(RegExp(r'\D'), '');
    if (d.isEmpty) return null;
    return d.startsWith('0') ? '62${d.substring(1)}' : d;
  }
}

class OnlineOrdersState {
  final List<OnlineOrder> orders;
  final bool loading;
  final String? error;
  final bool streamConnected;
  final bool soundEnabled;
  final DateTime? lastFetchAt;
  const OnlineOrdersState({
    this.orders = const [],
    this.loading = false,
    this.error,
    this.streamConnected = false,
    this.soundEnabled = true,
    this.lastFetchAt,
  });

  List<OnlineOrder> get pending => orders.where((o) => o.isPending).toList();
  List<OnlineOrder> get inProgress => orders.where((o) => o.status == 'preparing' || o.status == 'ready' || o.status == 'served').toList();
  List<OnlineOrder> get done => orders.where((o) => !o.isActive).toList();
  int get pendingCount => pending.length;

  OnlineOrdersState copyWith({
    List<OnlineOrder>? orders,
    bool? loading,
    String? error,
    bool clearError = false,
    bool? streamConnected,
    bool? soundEnabled,
    DateTime? lastFetchAt,
  }) =>
      OnlineOrdersState(
        orders: orders ?? this.orders,
        loading: loading ?? this.loading,
        error: clearError ? null : (error ?? this.error),
        streamConnected: streamConnected ?? this.streamConnected,
        soundEnabled: soundEnabled ?? this.soundEnabled,
        lastFetchAt: lastFetchAt ?? this.lastFetchAt,
      );
}

class OnlineOrdersNotifier extends StateNotifier<OnlineOrdersState> {
  OnlineOrdersNotifier() : super(const OnlineOrdersState()) {
    _loadSoundPref();
  }

  static const _prefSound = 'online_orders_sound';
  static const _pollEvery = Duration(seconds: 30);
  static const _remindEvery = Duration(seconds: 45);

  http.Client? _client;
  StreamSubscription<String>? _sub;
  Timer? _poll;
  Timer? _reconnect;
  Timer? _remind;
  int _backoffSec = 2;
  bool _running = false;
  bool _foreground = true;
  Set<String> _knownIds = {};
  final AudioPlayer _player = AudioPlayer();

  Dio get _dio => Dio(BaseOptions(
        baseUrl: AppConfig.apiV1,
        headers: SessionCache.instance.authHeaders,
        connectTimeout: const Duration(seconds: 10),
        receiveTimeout: const Duration(seconds: 15),
      ));

  Future<void> _loadSoundPref() async {
    try {
      final p = await SharedPreferences.getInstance();
      state = state.copyWith(soundEnabled: p.getBool(_prefSound) ?? true);
    } catch (_) {}
  }

  Future<void> setSoundEnabled(bool v) async {
    state = state.copyWith(soundEnabled: v);
    try {
      (await SharedPreferences.getInstance()).setBool(_prefSound, v);
    } catch (_) {}
  }

  // ── Siklus hidup ──────────────────────────────────────────────────────

  /// Dipanggil sekali dari Beranda (dashboard). Aman dipanggil ulang.
  Future<void> start() async {
    if (_running) return;
    _running = true;
    await fetch(silent: true);
    _knownIds = state.orders.map((o) => o.id).toSet();
    _connect();
    _poll?.cancel();
    _poll = Timer.periodic(_pollEvery, (_) => fetch(silent: true));
    _remind?.cancel();
    _remind = Timer.periodic(_remindEvery, (_) {
      if (_foreground && state.pendingCount > 0) _ring(times: 1);
    });
  }

  void stop() {
    _running = false;
    _poll?.cancel();
    _remind?.cancel();
    _reconnect?.cancel();
    _closeStream();
  }

  /// App ke belakang: putus stream (hemat baterai), polling tetap.
  void onBackground() {
    _foreground = false;
    _reconnect?.cancel();
    _closeStream();
  }

  /// App kembali ke depan: tarik ulang + sambung lagi.
  void onForeground() {
    _foreground = true;
    if (!_running) return;
    fetch(silent: true);
    if (_sub == null) _connect();
  }

  @override
  void dispose() {
    stop();
    _player.dispose();
    super.dispose();
  }

  // ── Data ──────────────────────────────────────────────────────────────

  Future<void> fetch({bool silent = false}) async {
    final outletId = SessionCache.instance.outletId;
    if (outletId == null || outletId.isEmpty) return;
    if (!silent) state = state.copyWith(loading: true, clearError: true);
    try {
      final res = await _dio.get('/orders/online', queryParameters: {'outlet_id': outletId, 'include_done': true, 'limit': 60});
      final list = (res.data['data'] as List? ?? [])
          .map((e) => OnlineOrder.fromJson(e as Map<String, dynamic>))
          .toList()
        ..sort((a, b) => b.createdAt.compareTo(a.createdAt));
      final fresh = list.where((o) => o.isPending && !_knownIds.contains(o.id)).toList();
      _knownIds.addAll(list.map((o) => o.id));
      state = state.copyWith(orders: list, loading: false, clearError: true, lastFetchAt: DateTime.now());
      if (fresh.isNotEmpty && _running && _foreground) _ring(times: 3);
    } on DioException catch (e) {
      state = state.copyWith(loading: false, error: e.response == null ? 'Tidak ada koneksi' : 'Gagal memuat pesanan online');
    } catch (_) {
      state = state.copyWith(loading: false, error: 'Gagal memuat pesanan online');
    }
  }

  Future<String?> accept(String orderId, int etaMinutes) async {
    try {
      await _dio.post('/orders/$orderId/accept', data: {'eta_minutes': etaMinutes});
      await fetch(silent: true);
      return null;
    } on DioException catch (e) {
      return _msg(e, 'Gagal menerima pesanan');
    }
  }

  Future<String?> reject(String orderId, String reason) async {
    try {
      await _dio.post('/orders/$orderId/reject', data: {'reason': reason});
      await fetch(silent: true);
      return null;
    } on DioException catch (e) {
      return _msg(e, 'Gagal menolak pesanan');
    }
  }

  Future<String?> setStatus(String orderId, String status) async {
    try {
      await _dio.put('/orders/$orderId/status', data: {'status': status, 'row_version': 0});
      await fetch(silent: true);
      return null;
    } on DioException catch (e) {
      return _msg(e, 'Gagal memperbarui status');
    }
  }

  String _msg(DioException e, String fallback) {
    final d = e.response?.data;
    if (d is Map && d['detail'] is String) return d['detail'] as String;
    return e.response == null ? 'Tidak ada koneksi' : fallback;
  }

  // ── SSE ───────────────────────────────────────────────────────────────

  Future<void> _connect() async {
    final outletId = SessionCache.instance.outletId;
    if (!_running || outletId == null || outletId.isEmpty) return;
    _closeStream();
    final client = http.Client();
    _client = client;
    try {
      final req = http.Request('GET', Uri.parse('${AppConfig.apiV1}/orders/stream?outlet_id=$outletId'));
      req.headers.addAll(SessionCache.instance.authHeaders);
      req.headers['Accept'] = 'text/event-stream';
      final resp = await client.send(req);
      if (resp.statusCode != 200) throw Exception('stream ${resp.statusCode}');
      _backoffSec = 2;
      state = state.copyWith(streamConnected: true);
      var buf = '';
      _sub = resp.stream.transform(utf8.decoder).listen((chunk) {
        buf += chunk;
        while (true) {
          final idx = buf.indexOf('\n\n');
          if (idx < 0) break;
          _handleFrame(buf.substring(0, idx));
          buf = buf.substring(idx + 2);
        }
      }, onDone: _onStreamLost, onError: (_) => _onStreamLost(), cancelOnError: true);
    } catch (_) {
      _onStreamLost();
    }
  }

  void _handleFrame(String frame) {
    String? event;
    for (final line in frame.split('\n')) {
      if (line.startsWith('event:')) event = line.substring(6).trim();
      // `data:` nggak dipakai: semua event = tarik ulang daftar.
    }
    if (event == null || event == 'hello') return;
    fetch(silent: true);
  }

  void _onStreamLost() {
    if (!mounted) return;
    state = state.copyWith(streamConnected: false);
    _sub = null;
    if (!_running || !_foreground) return;
    _reconnect?.cancel();
    _reconnect = Timer(Duration(seconds: _backoffSec), _connect);
    _backoffSec = (_backoffSec * 2).clamp(2, 60);
  }

  void _closeStream() {
    _sub?.cancel();
    _sub = null;
    _client?.close();
    _client = null;
    if (mounted && state.streamConnected) state = state.copyWith(streamConnected: false);
  }

  // ── Bel ───────────────────────────────────────────────────────────────

  Future<void> _ring({int times = 1}) async {
    if (!state.soundEnabled) return;
    for (var i = 0; i < times; i++) {
      try {
        HapticFeedback.heavyImpact();
        await _player.stop();
        await _player.play(AssetSource('sounds/order_bell.wav'), volume: 1.0);
      } catch (_) {}
      if (i < times - 1) await Future.delayed(const Duration(milliseconds: 1400));
    }
  }

  /// Tes bunyi dari halaman (tombol speaker).
  Future<void> testRing() => _ring(times: 1);
}

final onlineOrdersProvider = StateNotifierProvider<OnlineOrdersNotifier, OnlineOrdersState>((ref) => OnlineOrdersNotifier());
