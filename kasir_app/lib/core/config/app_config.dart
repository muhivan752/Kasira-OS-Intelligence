import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Satu-satunya sumber kebenaran untuk konfigurasi app.
/// URL backend bisa diubah dari settings tanpa rebuild APK.
class AppConfig {
  static const String _keyBaseUrl = 'app_base_url';

  /// Default URL — ganti saat deploy ke VPS
  static const String defaultBaseUrl = 'http://127.0.0.1:8000';

  static String _baseUrl = defaultBaseUrl;

  static String get baseUrl => _baseUrl;
  static String get apiV1 => '$_baseUrl/api/v1';

  /// Load URL tersimpan dari SharedPreferences
  static Future<void> init(SharedPreferences prefs) async {
    final saved = prefs.getString(_keyBaseUrl);
    if (saved != null && saved.isNotEmpty) {
      _baseUrl = saved;
    }
    if (kDebugMode) {
      debugPrint('[AppConfig] baseUrl = $_baseUrl');
    }
  }

  /// Simpan URL baru (dari halaman Settings)
  static Future<void> setBaseUrl(String url, SharedPreferences prefs) async {
    final cleaned = url.trimRight().replaceAll(RegExp(r'/$'), '');
    _baseUrl = cleaned;
    await prefs.setString(_keyBaseUrl, cleaned);
  }
}
