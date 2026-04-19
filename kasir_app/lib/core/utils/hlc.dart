/// Hybrid Logical Clock (HLC) untuk offline-first CRDT sync.
///
/// Format serialize: `{timestamp_ms}:{counter}:{node_id}`
/// Contoh: `1729331234567:3:device_abc`
///         `1729331234567:3:server:fbc68df5-5613-4197-929d-395ddb903a9e`
///
/// **node_id boleh mengandung `:`** (server emit `server:{outlet_uuid}`),
/// jadi parse() pakai `indexOf` untuk 2 colon pertama, sisanya jadi nodeId.
/// Analog dengan Python `split(':', 2)`.
///
/// **Wiring requirement:** Setelah menerima HLC dari server response,
/// sync_service.dart WAJIB panggil `HLC.fromServer(localHlc, serverHlcString)`
/// sebelum persist ke SharedPreferences. Kalau skip → client HLC bisa regress
/// saat device clock mundur → offline order HLC < previous → gagal menang
/// saat CRDT merge.
class HLC {
  final int timestamp;
  final int counter;
  final String nodeId;

  HLC(this.timestamp, this.counter, this.nodeId);

  /// Fresh HLC dari physical clock. Gunakan HANYA untuk init pertama —
  /// subsequent write pakai [increment] atau [receive] biar monotonic.
  static HLC now(String nodeId) {
    return HLC(DateTime.now().millisecondsSinceEpoch, 0, nodeId);
  }

  /// Parse HLC string dari wire format.
  ///
  /// Tolerant terhadap node_id yang contains `:` (misal `server:outlet-uuid`).
  /// Throw [FormatException] kalau format invalid (< 2 colon, non-numeric
  /// timestamp/counter).
  static HLC parse(String hlcString) {
    final firstColon = hlcString.indexOf(':');
    final secondColon = firstColon < 0 ? -1 : hlcString.indexOf(':', firstColon + 1);
    if (firstColon < 0 || secondColon < 0) {
      throw FormatException('Invalid HLC format: $hlcString');
    }
    final ts = int.tryParse(hlcString.substring(0, firstColon));
    final cnt = int.tryParse(hlcString.substring(firstColon + 1, secondColon));
    final nid = hlcString.substring(secondColon + 1);
    if (ts == null || cnt == null || nid.isEmpty) {
      throw FormatException('Invalid HLC format: $hlcString');
    }
    return HLC(ts, cnt, nid);
  }

  @override
  String toString() => '$timestamp:$counter:$nodeId';

  /// Total ordering: timestamp > counter > nodeId lexical.
  int compareTo(HLC other) {
    if (timestamp != other.timestamp) {
      return timestamp.compareTo(other.timestamp);
    }
    if (counter != other.counter) {
      return counter.compareTo(other.counter);
    }
    return nodeId.compareTo(other.nodeId);
  }

  /// Local event — clock tick tanpa remote merge.
  HLC increment() {
    final now = DateTime.now().millisecondsSinceEpoch;
    if (now > timestamp) {
      return HLC(now, 0, nodeId);
    }
    return HLC(timestamp, counter + 1, nodeId);
  }

  /// Merge remote HLC — dipakai setelah terima message dari device lain
  /// atau server. Guarantee: return HLC >= max(local, remote, physical_now).
  HLC receive(HLC remote) {
    final now = DateTime.now().millisecondsSinceEpoch;
    final maxTime = timestamp > remote.timestamp ? timestamp : remote.timestamp;

    if (now > maxTime) {
      return HLC(now, 0, nodeId);
    } else if (timestamp == remote.timestamp) {
      final maxCounter = counter > remote.counter ? counter : remote.counter;
      return HLC(maxTime, maxCounter + 1, nodeId);
    } else {
      return HLC(
        maxTime,
        (maxTime == timestamp ? counter : remote.counter) + 1,
        nodeId,
      );
    }
  }

  /// Convenience wrapper — parse server HLC string + merge dengan local.
  /// Gunakan ini di sync_service setelah dapat `last_sync_hlc` dari response:
  ///
  /// ```dart
  /// final localHlc = HLC.parse(prefs.getString('last_sync_hlc') ?? '0:0:$nodeId');
  /// final newHlc = HLC.fromServer(localHlc, response.lastSyncHlc);
  /// await prefs.setString('last_sync_hlc', newHlc.toString());
  /// ```
  static HLC fromServer(HLC local, String serverHlcString) {
    final remote = HLC.parse(serverHlcString);
    return local.receive(remote);
  }
}
