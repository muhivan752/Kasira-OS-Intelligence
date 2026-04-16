import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:dio/dio.dart';
import '../../../core/config/app_config.dart';
import '../../../core/services/session_cache.dart';

class TaxConfig {
  final bool pb1Enabled;
  final double taxPct;
  final bool serviceChargeEnabled;
  final double serviceChargePct;
  final bool taxInclusive;

  const TaxConfig({
    this.pb1Enabled = false,
    this.taxPct = 10.0,
    this.serviceChargeEnabled = false,
    this.serviceChargePct = 0.0,
    this.taxInclusive = false,
  });

  factory TaxConfig.fromJson(Map<String, dynamic> json) => TaxConfig(
        pb1Enabled: json['pb1_enabled'] as bool? ?? false,
        taxPct: (json['tax_pct'] as num? ?? 10.0).toDouble(),
        serviceChargeEnabled: json['service_charge_enabled'] as bool? ?? false,
        serviceChargePct: (json['service_charge_pct'] as num? ?? 0.0).toDouble(),
        taxInclusive: json['tax_inclusive'] as bool? ?? false,
      );

  /// Calculate tax amount from subtotal (after discount)
  double calcTax(double taxableAmount) {
    if (!pb1Enabled || taxPct <= 0) return 0;
    if (taxInclusive) {
      // Extract tax from price (price already includes tax)
      return taxableAmount - (taxableAmount / (1 + taxPct / 100));
    }
    return taxableAmount * taxPct / 100;
  }

  /// Calculate service charge from subtotal (after discount)
  double calcServiceCharge(double taxableAmount) {
    if (!serviceChargeEnabled || serviceChargePct <= 0) return 0;
    return taxableAmount * serviceChargePct / 100;
  }
}

/// Cached tax config — survives provider rebuilds within same session.
/// Invalidate explicitly when settings change.
TaxConfig? _cachedTaxConfig;

final taxConfigProvider = FutureProvider<TaxConfig>((ref) async {
  // Return cache if available — avoids redundant API call
  if (_cachedTaxConfig != null) return _cachedTaxConfig!;

  final c = SessionCache.instance;
  final token = c.accessToken;
  final outletId = c.outletId;
  final tenantId = c.tenantId;

  if (outletId == null || outletId.isEmpty) return const TaxConfig();

  try {
    final dio = Dio(BaseOptions(
      baseUrl: AppConfig.apiV1,
      connectTimeout: const Duration(seconds: 5),
      receiveTimeout: const Duration(seconds: 5),
    ));

    final response = await dio.get(
      '/outlets/$outletId/tax-config',
      options: Options(headers: {
        if (token != null) 'Authorization': 'Bearer $token',
        if (tenantId != null) 'X-Tenant-ID': tenantId,
      }),
    );

    final data = response.data['data'] as Map<String, dynamic>?;
    if (data == null) return const TaxConfig();
    _cachedTaxConfig = TaxConfig.fromJson(data);
    return _cachedTaxConfig!;
  } catch (_) {
    // Graceful degrade — no tax config = no charges
    return const TaxConfig();
  }
});

/// Call this to force re-fetch tax config (e.g. after settings change)
void invalidateTaxConfigCache() {
  _cachedTaxConfig = null;
}
