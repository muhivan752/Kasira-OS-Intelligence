import 'dart:convert';

/// PNCounter — Positive-Negative CRDT Counter
/// Mirror dari backend/services/crdt.py::PNCounter
///
/// - `positive` = G-Counter untuk restock (increment only)
/// - `negative` = G-Counter untuk sale/consume (increment only)
/// - `value`    = sum(positive) - sum(negative), min 0
///
/// Merge rule: max per nodeId — commutative, associative, idempoten.
/// Tidak ada LWW, tidak ada conflict.
class PNCounter {
  /// Increment counter untuk nodeId sebesar [amount].
  static Map<String, int> increment(
    Map<String, int> state,
    String nodeId, {
    int amount = 1,
  }) {
    final next = Map<String, int>.from(state);
    next[nodeId] = (next[nodeId] ?? 0) + amount;
    return next;
  }

  /// Merge dua G-Counter: ambil max per nodeId.
  static Map<String, int> merge(
    Map<String, int> local,
    Map<String, int> remote,
  ) {
    final result = Map<String, int>.from(local);
    for (final entry in remote.entries) {
      result[entry.key] = entry.value > (result[entry.key] ?? 0)
          ? entry.value
          : (result[entry.key] ?? 0);
    }
    return result;
  }

  /// Computed value = sum(positive) - sum(negative), min 0.
  static double getValue(
    Map<String, int> positive,
    Map<String, int> negative,
  ) {
    final p = positive.values.fold(0, (a, b) => a + b);
    final n = negative.values.fold(0, (a, b) => a + b);
    return (p - n).clamp(0, double.infinity).toDouble();
  }

  // ── JSON helpers ──────────────────────────────────────────────────────────

  static Map<String, int> fromJson(String json) {
    if (json.isEmpty || json == '{}') return {};
    final decoded = jsonDecode(json) as Map<String, dynamic>;
    return decoded.map((k, v) => MapEntry(k, (v as num).toInt()));
  }

  static String toJson(Map<String, int> state) => jsonEncode(state);
}
