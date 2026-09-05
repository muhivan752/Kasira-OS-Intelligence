import 'dart:async';

import 'package:dio/dio.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../api/api_client.dart' show navigatorKey;
import '../config/app_config.dart';
import 'session_cache.dart';

/// Handler pesan saat app MATI atau di belakang.
///
/// WAJIB fungsi tingkat atas (bukan method, bukan closure): Android
/// menjalankannya di isolate Dart terpisah yang nggak punya widget tree,
/// provider, atau SessionCache milik isolate utama. Jadi jangan taruh
/// apa pun di sini selain hal yang aman berdiri sendiri.
///
/// Notifikasinya sendiri sudah ditampilkan sistem (server ngirim blok
/// `notification`), jadi di sini nggak ada yang perlu dikerjakan. Fungsinya
/// tetap harus ada supaya Firebase nggak protes.
@pragma('vm:entry-point')
Future<void> pushBackgroundHandler(RemoteMessage message) async {}

/// Notifikasi push ke app kasir (5 Sep 2026).
///
/// Lubang yang ditutup: SSE `orders:{outlet_id}` dan polling 30 detik
/// dua-duanya cuma hidup selama app dibuka. Begitu HP dikunci atau app
/// ditutup, kasir buta dan cuma pemilik yang tahu (lewat WA). Push bikin HP
/// bunyi tanpa app harus jalan.
///
/// **Semuanya opsional dan boleh gagal.** HP tanpa Google Play Services,
/// izin notifikasi yang ditolak, atau proyek Firebase yang belum dipasang
/// semuanya berakhir di `_aktif = false`, dan app jalan persis seperti
/// sebelum fitur ini ada. Nggak ada satu pun jalur transaksi yang nunggu
/// push (Rule #49 semangatnya sama: perangkat tambahan nggak boleh nyandera
/// kasir).
class PushService {
  PushService._();
  static final instance = PushService._();

  static const _prefsTokenKey = 'fcm_token_terdaftar';

  /// HARUS sama persis dengan `CHANNEL_ID` di `backend/services/fcm.py` dan
  /// dengan meta-data `default_notification_channel_id` di AndroidManifest.
  /// Beda satu huruf = Android pakai channel cadangan yang senyap.
  static const _channelId = 'pesanan_online';

  final _lokal = FlutterLocalNotificationsPlugin();

  bool _aktif = false;
  bool _mulai = false;
  String? _token;
  String? _tujuanTertunda;

  bool get aktif => _aktif;

  /// Dipanggil sekali dari `main()`, SEBELUM runApp. Nggak pernah throw.
  Future<void> init() async {
    if (_mulai) return;
    _mulai = true;
    try {
      await Firebase.initializeApp();
    } catch (e) {
      // Paling sering: google-services.json belum ada di APK ini. Bukan
      // kondisi darurat, cuma berarti push mati.
      debugPrint('[push] Firebase nggak tersedia: $e');
      return;
    }
    try {
      FirebaseMessaging.onBackgroundMessage(pushBackgroundHandler);
      final messaging = FirebaseMessaging.instance;

      // Android 13+ butuh izin runtime. Ditolak = push mati, app tetap jalan.
      final izin = await messaging.requestPermission(alert: true, badge: true, sound: true);
      if (izin.authorizationStatus == AuthorizationStatus.denied) {
        debugPrint('[push] izin notifikasi ditolak');
        return;
      }

      await _siapkanChannel();

      _aktif = true;

      // Pesan yang datang saat app LAGI DIBUKA nggak ditampilkan Android
      // sendiri — FCM cuma nyerahin datanya ke app. Jadi kita yang nampilin.
      // Tetap perlu walau ada SSE: SSE bisa putus, dan kasir yang lagi buka
      // layar lain harus tetap lihat.
      FirebaseMessaging.onMessage.listen(_tampilkanDiForeground);

      // App dibuka DARI notifikasi saat masih di belakang.
      // Langganan nggak disimpan: PushService itu singleton yang hidup
      // selama app hidup, jadi nggak ada titik di mana dia dibatalkan.
      FirebaseMessaging.onMessageOpenedApp.listen(_tangkapKetukan);
      // App dibuka dari notifikasi saat sebelumnya MATI total.
      final awal = await messaging.getInitialMessage();
      if (awal != null) _tangkapKetukan(awal);

      // Firebase boleh ganti token kapan saja. Kalau nggak didaftar ulang,
      // HP-nya diam selamanya dan nggak ada yang sadar.
      messaging.onTokenRefresh.listen((t) {
        _token = t;
        unawaited(_kirimKeServer(t));
      });

      _token = await messaging.getToken();
      debugPrint('[push] siap, token ${_token == null ? "kosong" : "ada"}');
    } catch (e) {
      debugPrint('[push] gagal disiapkan: $e');
      _aktif = false;
    }
  }

  /// Daftarkan HP ini ke backend. Dipanggil sesudah login dan tiap app
  /// dibuka dengan sesi yang masih hidup. Aman diulang.
  Future<void> daftar() async {
    if (!_aktif) return;
    final cache = SessionCache.instance;
    if (cache.accessToken == null || cache.outletId == null) return;
    _token ??= await _ambilToken();
    final t = _token;
    if (t == null || t.isEmpty) return;
    await _kirimKeServer(t);
  }

  /// Dipanggil saat logout, SEBELUM token dibuang dari SessionCache —
  /// endpointnya butuh Authorization. Tanpa ini, HP yang sudah logout tetap
  /// dapat notifikasi pesanan toko lamanya.
  Future<void> lupakan() async {
    final t = _token ?? await _tokenTersimpan();
    if (t == null || t.isEmpty) return;
    try {
      await _dio().post('/devices/unregister', data: {'fcm_token': t});
    } catch (_) {
      // Offline saat logout: token bakal kecabut sendiri di server begitu
      // notifikasi berikutnya ditolak Firebase.
    }
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.remove(_prefsTokenKey);
    } catch (_) {}
  }

  /// Ketukan notifikasi yang datang sebelum ada layar buat dituju.
  ///
  /// Waktu app dibuka dari kondisi mati, rutenya masih di splash dan
  /// `push()` bakal ketimpa perpindahan ke dashboard. Jadi tujuannya
  /// disimpan dulu, lalu dipakai Dashboard begitu dia terpasang.
  void bukaTertunda() {
    final tujuan = _tujuanTertunda;
    if (tujuan == null) return;
    _tujuanTertunda = null;
    _pindah(tujuan);
  }

  // ── Dalaman ──────────────────────────────────────────────────────────────

  /// Android 8+ nolak notifikasi yang channel-nya nggak ada, dan importance
  /// nempel PERMANEN ke channel begitu dibikin: ganti nilainya di kode nggak
  /// ngaruh sampai app di-uninstall. Makanya sekali bikin harus langsung
  /// `high` (nongol di layar + bunyi).
  Future<void> _siapkanChannel() async {
    try {
      await _lokal.initialize(
        settings: const InitializationSettings(
          android: AndroidInitializationSettings('@mipmap/ic_launcher'),
        ),
        onDidReceiveNotificationResponse: (resp) {
          final tujuan = resp.payload ?? '';
          if (tujuan.startsWith('/')) {
            _tujuanTertunda = tujuan;
            bukaTertunda();
          }
        },
      );
      final android = _lokal.resolvePlatformSpecificImplementation<
          AndroidFlutterLocalNotificationsPlugin>();
      await android?.createNotificationChannel(const AndroidNotificationChannel(
        _channelId,
        'Pesanan online',
        description: 'Pesanan masuk, reservasi, dan bukti bayar dari pelanggan.',
        importance: Importance.high,
      ));
    } catch (e) {
      debugPrint('[push] channel gagal dibikin: $e');
    }
  }

  Future<void> _tampilkanDiForeground(RemoteMessage m) async {
    final n = m.notification;
    if (n == null) return;
    try {
      await _lokal.show(
        id: m.hashCode,
        title: n.title ?? 'Selaris',
        body: n.body ?? '',
        notificationDetails: const NotificationDetails(
          android: AndroidNotificationDetails(
            _channelId,
            'Pesanan online',
            importance: Importance.high,
            priority: Priority.high,
          ),
        ),
        payload: (m.data['route'] ?? '').toString(),
      );
    } catch (e) {
      debugPrint('[push] gagal nampilin di foreground: $e');
    }
  }

  void _tangkapKetukan(RemoteMessage m) {
    final tujuan = (m.data['route'] ?? '').toString();
    if (tujuan.isEmpty || !tujuan.startsWith('/')) return;
    _tujuanTertunda = tujuan;
    // Kalau layarnya sudah ada, langsung. Kalau belum, Dashboard yang manggil
    // `bukaTertunda()` sesudah terpasang.
    final ctx = navigatorKey.currentContext;
    if (ctx != null) bukaTertunda();
  }

  void _pindah(String tujuan) {
    final ctx = navigatorKey.currentContext;
    if (ctx == null) {
      _tujuanTertunda = tujuan;
      return;
    }
    try {
      // `push`, BUKAN `go`: `go` ngeganti seluruh tumpukan, jadi tombol
      // kembali dari layar ini mendarat di layar hitam.
      GoRouter.of(ctx).push(tujuan);
    } catch (e) {
      debugPrint('[push] gagal buka $tujuan: $e');
    }
  }

  Future<String?> _ambilToken() async {
    try {
      return await FirebaseMessaging.instance.getToken();
    } catch (_) {
      return null;
    }
  }

  Future<String?> _tokenTersimpan() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      return prefs.getString(_prefsTokenKey);
    } catch (_) {
      return null;
    }
  }

  Dio _dio() {
    final cache = SessionCache.instance;
    return Dio(BaseOptions(
      baseUrl: AppConfig.apiV1,
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 10),
      headers: {
        'Content-Type': 'application/json',
        if (cache.accessToken != null) 'Authorization': 'Bearer ${cache.accessToken}',
        if (cache.tenantId != null) 'X-Tenant-ID': cache.tenantId,
      },
    ));
  }

  Future<void> _kirimKeServer(String token) async {
    final cache = SessionCache.instance;
    if (cache.accessToken == null || cache.outletId == null) return;
    try {
      await _dio().post('/devices/register', data: {
        'fcm_token': token,
        'outlet_id': cache.outletId,
        'device_name': cache.outletName ?? 'Perangkat kasir',
        'device_type': 'kasir',
      });
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(_prefsTokenKey, token);
      debugPrint('[push] terdaftar di server');
    } catch (e) {
      // Offline waktu app dibuka itu wajar. Percobaan berikutnya jalan di
      // pembukaan app selanjutnya, jadi nggak perlu antrean sendiri.
      debugPrint('[push] daftar ke server gagal: $e');
    }
  }
}
