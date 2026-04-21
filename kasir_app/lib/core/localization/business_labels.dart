import '../services/session_cache.dart';

/// Adaptive UI label mapper — Batch #26.
///
/// Reads `SessionCache.instance.businessDomain` (set at register-time via
/// `POST /ai/classify-domain` suggestion). Null domain → default F&B labels
/// untuk backward compat (existing user zero regression).
///
/// Usage:
///   Text(BusinessLabels.getLabel('table'))  // "Meja" | "Rak/Etalase" | "Area Servis"
///   Text(BusinessLabels.getLabel('order'))  // "Pesanan" | "Penjualan" | "Layanan"
///
/// Domain values: 'fnb' | 'retail' | 'service'. Single source of truth
/// match-in bucket mapping di backend `ai.py:_BUCKET_TO_SUPER_GROUP`.
class BusinessLabels {
  BusinessLabels._();

  static const Map<String, Map<String, String>> _labels = {
    'fnb': {
      'table': 'Meja',
      'kitchen': 'Dapur',
      'order': 'Pesanan',
      'table_plural': 'Meja',
      'kitchen_team': 'Tim Dapur',
      'select_table': 'Pilih Meja',
      'active_tables': 'Meja Aktif',
    },
    'retail': {
      'table': 'Rak/Etalase',
      'kitchen': 'Gudang',
      'order': 'Penjualan',
      'table_plural': 'Rak',
      'kitchen_team': 'Staf Gudang',
      'select_table': 'Pilih Rak',
      'active_tables': 'Etalase Aktif',
    },
    'service': {
      'table': 'Area Servis',
      'kitchen': 'Teknisi',
      'order': 'Layanan',
      'table_plural': 'Kursi',
      'kitchen_team': 'Tim Teknisi',
      'select_table': 'Pilih Area',
      'active_tables': 'Servis Aktif',
    },
  };

  /// Returns label for [key] in current business domain.
  /// Falls back to F&B if domain not set or key not found.
  /// Pass [overrideDomain] to force a specific group (useful for tests).
  static String getLabel(String key, {String? overrideDomain}) {
    final domain = overrideDomain ?? SessionCache.instance.businessDomain ?? 'fnb';
    final group = _labels[domain] ?? _labels['fnb']!;
    return group[key] ?? _labels['fnb']![key] ?? key;
  }

  /// True kalau current domain adalah F&B (default). Useful untuk conditional
  /// UI — misal hide menu "Dapur mode" kalau retail/service.
  static bool get isFnB =>
      (SessionCache.instance.businessDomain ?? 'fnb') == 'fnb';
}
