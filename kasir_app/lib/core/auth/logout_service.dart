import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../services/session_cache.dart';
import '../sync/sync_provider.dart';

/// Centralized logout flow — Batch #17 Rule #10 (orphan cleanup) & Rule #11
/// (hardened logout).
///
/// Kontrak:
/// 1. **Reset in-memory sync state** — biar sync cycle yang sedang/barusan
///    jalan gak leak status stale ke session user baru. Tidak cancel future
///    yang sedang in-flight (Dart gak ngasih cancellation token), tapi flag
///    status + lastError di-reset.
/// 2. **Clear SessionCache** — wipe semua credential di RAM, SecureStorage,
///    dan SharedPreferences mirror (tenant/outlet/stock_mode/tier).
/// 3. **Invalidate Riverpod providers** yang hold stale session refs
///    (syncServiceProvider) — force re-create saat user berikut login,
///    biar nodeId getter eval ulang dengan userId baru.
/// 4. **JANGAN drop SQLite** — data offline (orders, payments, products,
///    ingredients) tetap hidup. User yang sama login lagi → lanjut dari
///    mana berhenti. User lain di device yang sama → nodeId beda (Rule #9),
///    jadi CRDT tetap konsisten walaupun pake DB yang sama.
/// 5. **JANGAN hapus `device_node_id`** di SharedPreferences — itu identitas
///    fisik device, harus survive logout. `SessionCache.clear()` cuma hapus
///    key `c_*` prefix, jadi aman.
Future<void> performLogout(WidgetRef ref) async {
  // 1. Reset sync in-memory state (orphan cleanup)
  try {
    ref.read(syncServiceProvider).resetState();
  } catch (e) {
    // Provider belum pernah di-initialize — abaikan
    debugPrint('performLogout: resetState skip — $e');
  }

  // 2. Clear credential di RAM + SecureStorage + SharedPreferences mirror
  await SessionCache.instance.clear();

  // 3. Invalidate providers yang hold stale refs
  //    syncServiceProvider akan re-create next read → nodeId re-eval dengan
  //    userId baru (atau null kalau pre-login).
  ref.invalidate(syncServiceProvider);
}
