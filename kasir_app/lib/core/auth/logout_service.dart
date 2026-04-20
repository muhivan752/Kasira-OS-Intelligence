import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../services/session_cache.dart';
import '../sync/sync_provider.dart';

/// Centralized logout flow — Batch #17 Rule #10/#11 + Batch #18 Rule #4b.
///
/// Kontrak:
/// 1. **Cancel in-flight sync** (Batch #18) — via Dio CancelToken biar
///    request POST /sync yang sedang menunggu response gak complete dengan
///    auth header yang udah gak berhak, dan gak nyampah `_markAsSynced`
///    setelah SessionCache.clear() jalan.
/// 2. **Reset in-memory sync state** — flag status + lastError + stock
///    mode change ke default biar gak leak ke session user baru.
/// 3. **Clear SessionCache** — wipe semua credential di RAM, SecureStorage,
///    dan SharedPreferences mirror (tenant/outlet/stock_mode/tier).
/// 4. **Invalidate Riverpod providers** yang hold stale session refs
///    (syncServiceProvider) — force re-create saat user berikut login,
///    biar nodeId getter eval ulang dengan userId baru.
/// 5. **JANGAN drop SQLite** — data offline (orders, payments, products,
///    ingredients) tetap hidup. User yang sama login lagi → lanjut dari
///    mana berhenti. User lain di device yang sama → nodeId beda (Rule #9),
///    jadi CRDT tetap konsisten walaupun pake DB yang sama.
/// 6. **JANGAN hapus `device_node_id`** di SharedPreferences — itu identitas
///    fisik device, harus survive logout. `SessionCache.clear()` cuma hapus
///    key `c_*` prefix, jadi aman.
Future<void> performLogout(WidgetRef ref) async {
  // 1 & 2. Cancel in-flight request + reset state — dipanggil SEBELUM
  //        SessionCache.clear() biar kalau request udah terkirim tapi belum
  //        ke-cancel, header-nya masih valid (graceful). Token lama aman
  //        karena logout adalah intent user sendiri.
  try {
    final syncService = ref.read(syncServiceProvider);
    syncService.cancelInFlight();
    syncService.resetState();
  } catch (e) {
    // Provider belum pernah di-initialize — abaikan
    debugPrint('performLogout: sync cleanup skip — $e');
  }

  // 3. Clear credential di RAM + SecureStorage + SharedPreferences mirror
  await SessionCache.instance.clear();

  // 4. Invalidate providers yang hold stale refs
  //    syncServiceProvider akan re-create next read → nodeId re-eval dengan
  //    userId baru (atau null kalau pre-login).
  ref.invalidate(syncServiceProvider);
}
