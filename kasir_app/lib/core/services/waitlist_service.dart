import 'package:dio/dio.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../config/app_config.dart';
import 'session_cache.dart';

/// Waitlist service — Batch #27.
///
/// Non-F&B user klik "Daftar Waitlist" → record interest locally (dedup via
/// SharedPreferences flag) + POST ke backend `/waitlist/join` (non-blocking).
/// Backend log ke Event table untuk early-access outreach nanti.
///
/// Idempotent: flag `waitlist_joined_{domain}` dicek dulu, return fast kalau
/// sudah joined. Backend tetep accept duplicate (append-only audit), tapi
/// Flutter hemat network call.
class WaitlistService {
  WaitlistService._();

  static Future<bool> hasJoined(String domain) async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getBool('waitlist_joined_$domain') ?? false;
  }

  /// Join waitlist untuk [domain] ('retail' | 'service'). Idempotent.
  /// Returns true kalau ini first-time join (UI can show celebration).
  /// Fail-open: network error = tetep mark local flag (biar user gak spam
  /// coba lagi) + log silent.
  static Future<bool> join({
    required String domain,
    String? displayName,
    String source = 'upgrade_sheet',
  }) async {
    final prefs = await SharedPreferences.getInstance();
    final key = 'waitlist_joined_$domain';
    if (prefs.getBool(key) == true) return false; // already joined

    // Mark local dulu — cegah double-tap saat network lambat
    await prefs.setBool(key, true);

    // Fire network call (best-effort). Fail silent — local flag tetep set,
    // next session manual retry lewat Settings kalau mau (future).
    final cache = SessionCache.instance;
    final token = cache.accessToken;
    if (token == null) return true; // pre-login user, skip backend post

    try {
      final dio = Dio(BaseOptions(
        baseUrl: AppConfig.apiV1,
        connectTimeout: const Duration(seconds: 8),
        receiveTimeout: const Duration(seconds: 8),
      ));
      await dio.post(
        '/waitlist/join',
        data: {
          'domain': domain,
          if (displayName != null) 'display_name': displayName,
          'source': source,
        },
        options: Options(headers: cache.authHeaders),
      );
    } catch (_) {
      // Silent — local flag sudah set, jangan block UX
    }

    return true;
  }
}
