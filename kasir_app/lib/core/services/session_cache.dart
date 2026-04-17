import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:shared_preferences/shared_preferences.dart';

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
  String? stockMode;
  String? subscriptionTier;
  String? shiftSessionId;
  String? phone;
  String? userId;

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

    _initialized = true;
  }

  /// Fast init from SharedPreferences cache (for cold start before login)
  Future<void> initFromPrefsCache() async {
    if (_initialized) return;
    final prefs = await SharedPreferences.getInstance();
    tenantId = prefs.getString('c_tenant_id');
    outletId = prefs.getString('c_outlet_id');
    stockMode = prefs.getString('c_stock_mode');
    subscriptionTier = prefs.getString('c_subscription_tier');
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
    outletId = value;
    Future.wait([
      const FlutterSecureStorage().write(key: 'outlet_id', value: value),
      SharedPreferences.getInstance().then((p) => p.setString('c_outlet_id', value)),
    ]);
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

  // ── Auth headers (convenience) ─────────────────────────────────────────────
  Map<String, String> get authHeaders => {
    if (accessToken != null) 'Authorization': 'Bearer $accessToken',
    if (tenantId != null) 'X-Tenant-ID': tenantId!,
  };

  // ── Tier check (convenience) ───────────────────────────────────────────────
  bool get isPro => const {'pro', 'business', 'enterprise'}
      .contains((subscriptionTier ?? 'starter').toLowerCase());

  // ── Logout / clear ─────────────────────────────────────────────────────────
  Future<void> clear() async {
    accessToken = null;
    tenantId = null;
    outletId = null;
    stockMode = null;
    subscriptionTier = null;
    shiftSessionId = null;
    phone = null;
    userId = null;
    _initialized = false;
    await const FlutterSecureStorage().deleteAll();
    final prefs = await SharedPreferences.getInstance();
    for (final key in ['c_tenant_id', 'c_outlet_id', 'c_stock_mode', 'c_subscription_tier']) {
      prefs.remove(key);
    }
  }
}
