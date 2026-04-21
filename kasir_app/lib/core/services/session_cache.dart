import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../config/app_config.dart';
import '../../features/pos/providers/tax_config_provider.dart';

/// In-memory credential cache — read storage ONCE at login, then 0ms everywhere.
///
/// Sensitive keys (access_token, user_pin) stay in SecureStorage.
/// Non-sensitive keys (tenant_id, outlet_id, stock_mode, subscription_tier)
/// are also mirrored to SharedPreferences for 10-50x faster cold reads.
class SessionCache {
  SessionCache._();
  static final instance = SessionCache._();

  // ── Cached values ─────────────────────────────────────────────────────────
  String? accessToken;
  String? tenantId;
  String? outletId;
  String? outletName;
  String? outletAddress;
  String? stockMode;
  String? subscriptionTier;
  String? shiftSessionId;
  String? phone;
  String? userId;
  // Business domain untuk Adaptive UI labels (Batch #26).
  // Values: 'fnb' (default) | 'retail' | 'service'. Null = belum di-detect,
  // treat as 'fnb' via BusinessLabels.getLabel fallback.
  String? businessDomain;

  bool _initialized = false;
  bool get isInitialized => _initialized;

  // ── Load from storage (call once at login/app start) ───────────────────────
  Future<void> init() async {
    if (_initialized) return;

    const secure = FlutterSecureStorage();
    final prefs = await SharedPreferences.getInstance();

    // Read all keys in parallel from SecureStorage
    final results = await Future.wait([
      secure.read(key: 'access_token'),
      secure.read(key: 'tenant_id'),
      secure.read(key: 'outlet_id'),
      secure.read(key: 'stock_mode'),
      secure.read(key: 'subscription_tier'),
      secure.read(key: 'shift_session_id'),
      secure.read(key: 'phone'),
      secure.read(key: 'user_id'),
    ]);

    accessToken = results[0];
    tenantId = results[1];
    outletId = results[2];
    stockMode = results[3];
    subscriptionTier = results[4];
    shiftSessionId = results[5];
    phone = results[6];
    userId = results[7];

    // Mirror non-sensitive to SharedPreferences for faster cold reads
    if (tenantId != null) prefs.setString('c_tenant_id', tenantId!);
    if (outletId != null) prefs.setString('c_outlet_id', outletId!);
    if (stockMode != null) prefs.setString('c_stock_mode', stockMode!);
    if (subscriptionTier != null) prefs.setString('c_subscription_tier', subscriptionTier!);

    // Prime outlet name/address dari SharedPreferences cache (populated via
    // order_detail_modal saat user buka receipt, atau via fetchOutletInfo).
    outletName = prefs.getString('c_outlet_name');
    outletAddress = prefs.getString('c_outlet_address');
    businessDomain = prefs.getString('c_business_domain');

    _initialized = true;

    // Fire-and-forget fetch outlet info kalau belum ada cached name.
    // Saat pertama login → prime cache biar receipt next transaksi bener.
    if (outletName == null && outletId != null && accessToken != null) {
      fetchAndCacheOutletInfo();
    }
  }

  /// Fast init from SharedPreferences cache (for cold start before login)
  Future<void> initFromPrefsCache() async {
    if (_initialized) return;
    final prefs = await SharedPreferences.getInstance();
    tenantId = prefs.getString('c_tenant_id');
    outletId = prefs.getString('c_outlet_id');
    outletName = prefs.getString('c_outlet_name');
    outletAddress = prefs.getString('c_outlet_address');
    stockMode = prefs.getString('c_stock_mode');
    subscriptionTier = prefs.getString('c_subscription_tier');
    businessDomain = prefs.getString('c_business_domain');
    // Token still needs SecureStorage — read in parallel
    const secure = FlutterSecureStorage();
    final results = await Future.wait([
      secure.read(key: 'access_token'),
      secure.read(key: 'shift_session_id'),
    ]);
    accessToken = results[0];
    shiftSessionId = results[1];
    _initialized = true;
  }

  // ── Update individual keys (keeps cache + storage in sync) ─────────────────
  Future<void> setAccessToken(String value) async {
    accessToken = value;
    const FlutterSecureStorage().write(key: 'access_token', value: value);
  }

  Future<void> setTenantId(String value) async {
    tenantId = value;
    Future.wait([
      const FlutterSecureStorage().write(key: 'tenant_id', value: value),
      SharedPreferences.getInstance().then((p) => p.setString('c_tenant_id', value)),
    ]);
  }

  Future<void> setOutletId(String value) async {
    final changed = outletId != null && outletId != value;
    outletId = value;
    Future.wait([
      const FlutterSecureStorage().write(key: 'outlet_id', value: value),
      SharedPreferences.getInstance().then((p) => p.setString('c_outlet_id', value)),
    ]);
    // Rule #50: saat outlet ganti, tax config outlet lama gak valid lagi.
    // Clear cache → fetch ulang saat provider dibaca di context outlet baru.
    if (changed) {
      invalidateTaxConfigCache();
      outletName = null; // force re-fetch dari /outlets/{id}
    }
  }

  Future<void> setStockMode(String value) async {
    final previous = stockMode;
    stockMode = value;
    Future.wait([
      const FlutterSecureStorage().write(key: 'stock_mode', value: value),
      SharedPreferences.getInstance().then((p) => p.setString('c_stock_mode', value)),
    ]);
    _stockModeChanged = previous != null && previous != value;
    _previousStockMode = previous;
  }

  // Track stock mode changes for sync notification
  bool _stockModeChanged = false;
  String? _previousStockMode;
  bool get stockModeChanged => _stockModeChanged;
  void clearStockModeChanged() => _stockModeChanged = false;

  Future<void> setSubscriptionTier(String value) async {
    subscriptionTier = value;
    Future.wait([
      const FlutterSecureStorage().write(key: 'subscription_tier', value: value),
      SharedPreferences.getInstance().then((p) => p.setString('c_subscription_tier', value)),
    ]);
  }

  Future<void> setShiftSessionId(String? value) async {
    shiftSessionId = value;
    if (value != null) {
      const FlutterSecureStorage().write(key: 'shift_session_id', value: value);
    }
  }

  Future<void> setPhone(String value) async {
    phone = value;
    const FlutterSecureStorage().write(key: 'phone', value: value);
  }

  Future<void> setUserId(String value) async {
    userId = value;
    const FlutterSecureStorage().write(key: 'user_id', value: value);
  }

  /// Set business domain untuk Adaptive UI (Batch #26).
  /// Value: 'fnb' | 'retail' | 'service'. Pass null untuk clear (revert ke default F&B).
  /// Persist ke SharedPreferences only (non-sensitive, gak butuh SecureStorage).
  Future<void> setBusinessDomain(String? value) async {
    businessDomain = value;
    final prefs = await SharedPreferences.getInstance();
    if (value == null) {
      await prefs.remove('c_business_domain');
    } else {
      await prefs.setString('c_business_domain', value);
    }
  }

  // ── Auth headers (convenience) ─────────────────────────────────────────────
  Map<String, String> get authHeaders => {
    if (accessToken != null) 'Authorization': 'Bearer $accessToken',
    if (tenantId != null) 'X-Tenant-ID': tenantId!,
  };

  /// Fetch outlet info dari GET /outlets/{outletId} — prime cache biar
  /// receipt/print gak pake fallback 'Kasira Outlet' di first transaction.
  /// Fire-and-forget, silent on error (graceful degrade).
  Future<void> fetchAndCacheOutletInfo() async {
    if (outletId == null || accessToken == null) return;
    try {
      final dio = Dio(BaseOptions(
        baseUrl: AppConfig.apiV1,
        connectTimeout: const Duration(seconds: 5),
        receiveTimeout: const Duration(seconds: 5),
      ));
      final response = await dio.get(
        '/outlets/$outletId',
        options: Options(headers: authHeaders),
      );
      final data = response.data['data'] as Map<String, dynamic>?;
      if (data == null) return;
      final name = data['name'] as String?;
      final address = data['address'] as String?;
      if (name != null && name.isNotEmpty) {
        outletName = name;
        final prefs = await SharedPreferences.getInstance();
        prefs.setString('c_outlet_name', name);
      }
      if (address != null && address.isNotEmpty) {
        outletAddress = address;
        final prefs = await SharedPreferences.getInstance();
        prefs.setString('c_outlet_address', address);
      }
    } catch (_) {
      // Silent — fallback chain (SessionCache → SharedPreferences → 'Kasira Outlet') tetap works
    }
  }

  // ── Tier check (convenience) ───────────────────────────────────────────────
  bool get isPro => const {'pro', 'business', 'enterprise'}
      .contains((subscriptionTier ?? 'starter').toLowerCase());

  // ── Logout / clear ─────────────────────────────────────────────────────────
  Future<void> clear() async {
    accessToken = null;
    tenantId = null;
    outletId = null;
    outletName = null;
    outletAddress = null;
    stockMode = null;
    subscriptionTier = null;
    shiftSessionId = null;
    phone = null;
    userId = null;
    businessDomain = null;
    _initialized = false;
    invalidateTaxConfigCache();
    await const FlutterSecureStorage().deleteAll();
    final prefs = await SharedPreferences.getInstance();
    for (final key in [
      'c_tenant_id',
      'c_outlet_id',
      'c_outlet_name',
      'c_outlet_address',
      'c_stock_mode',
      'c_subscription_tier',
      'c_business_domain',
    ]) {
      prefs.remove(key);
    }
  }
}
