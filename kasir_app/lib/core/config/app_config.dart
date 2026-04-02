import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Satu-satunya sumber kebenaran untuk konfigurasi app.
/// URL backend bisa diubah dari settings tanpa rebuild APK.
class AppConfig {
  static const String _keyBaseUrl = 'app_base_url';
  static const String _keyIsConfigured = 'app_server_configured';

  /// Default URL — hanya dipakai di emulator/dev. Di HP asli selalu minta setup.
  static const String defaultBaseUrl = 'http://127.0.0.1:8000';

  static String _baseUrl = defaultBaseUrl;
  static bool _isConfigured = false;

  static String get baseUrl => _baseUrl;
  static String get apiV1 => '$_baseUrl/api/v1';

  /// Sudah dikonfigurasi user (bukan default pertama kali)?
  static bool get isConfigured => _isConfigured;

  /// Load URL tersimpan dari SharedPreferences
  static Future<void> init(SharedPreferences prefs) async {
    final saved = prefs.getString(_keyBaseUrl);
    _isConfigured = prefs.getBool(_keyIsConfigured) ?? false;
    if (saved != null && saved.isNotEmpty) {
      _baseUrl = saved;
    }
    if (kDebugMode) {
      debugPrint('[AppConfig] baseUrl=$_baseUrl  configured=$_isConfigured');
    }
  }

  /// Simpan URL baru (dipanggil dari ServerSetupPage atau Settings)
  static Future<void> setBaseUrl(String url, SharedPreferences prefs) async {
    final cleaned = url.trim().replaceAll(RegExp(r'/$'), '');
    _baseUrl = cleaned;
    _isConfigured = true;
    await prefs.setString(_keyBaseUrl, cleaned);
    await prefs.setBool(_keyIsConfigured, true);
  }
}
