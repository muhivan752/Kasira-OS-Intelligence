import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
import '../../../../core/theme/kasira_ds.dart';
import '../../../../core/sync/sync_provider.dart';

class SyncSettingsPage extends ConsumerStatefulWidget {
  const SyncSettingsPage({super.key});

  @override
  ConsumerState<SyncSettingsPage> createState() => _SyncSettingsPageState();
}

class _SyncSettingsPageState extends ConsumerState<SyncSettingsPage> {
  bool _isAutoSyncEnabled = true;
  bool _isSyncing = false;
  String _lastSyncTime = 'Belum pernah';

  @override
  void initState() {
    super.initState();
    _loadLastSyncTime();
  }

  void _loadLastSyncTime() {
    final prefs = ref.read(sharedPreferencesProvider);
    final lastSync = prefs.getString('last_sync_hlc');
    if (lastSync != null) {
      setState(() {
        _lastSyncTime = 'Tersinkronisasi';
      });
    }
  }

  void _performManualSync() async {
    setState(() {
      _isSyncing = true;
    });

    final syncService = ref.read(syncServiceProvider);
    try {
      await syncService.sync();
      // Network error sekarang di-handle silent di SyncService (set status,
      // debugPrint, gak rethrow). Check status buat show snackbar yang tepat.
    } catch (e) {
      if (mounted) {
        setState(() { _isSyncing = false; });
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Gagal sinkronisasi: ${syncService.lastError ?? e}'),
            backgroundColor: KasiraDS.danger,
          ),
        );
      }
      return;
    }

    if (!mounted) return;
    setState(() {
      _isSyncing = false;
      if (syncService.status == SyncStatus.success) {
        _lastSyncTime = 'Baru saja';
      }
    });

    final (msg, color) = switch (syncService.status) {
      SyncStatus.success => ('Sinkronisasi data berhasil.', KasiraDS.success),
      SyncStatus.networkError => (
          'Offline / jaringan bermasalah. Data akan sync otomatis saat online.',
          KasiraDS.danger,
        ),
      SyncStatus.serverError => (
          'Server error: ${syncService.lastError ?? "tidak diketahui"}',
          KasiraDS.danger,
        ),
      _ => (
          'Status: ${syncService.status.name}${syncService.lastError != null ? " — ${syncService.lastError}" : ""}',
          KasiraDS.danger,
        ),
    };
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(msg), backgroundColor: color),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: KasiraDS.bgBase,
      appBar: AppBar(
        backgroundColor: KasiraDS.surfaceCard,
        title: const Text('Sinkronisasi Data', style: TextStyle(color: KasiraDS.textStrong)),
        iconTheme: const IconThemeData(color: KasiraDS.textStrong),
        elevation: 0,
      ),
      body: ListView(
        padding: const EdgeInsets.all(24),
        children: [
          // Status Card
          Container(
            padding: const EdgeInsets.all(24),
            decoration: BoxDecoration(
              color: KasiraDS.surfaceCard,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: KasiraDS.borderSubtle),
            ),
            child: Column(
              children: [
                Icon(
                  _isSyncing ? LucideIcons.refreshCw : LucideIcons.checkCircle,
                  size: 48,
                  color: _isSyncing ? KasiraDS.brandPrimary : KasiraDS.success,
                ),
                const SizedBox(height: 16),
                Text(
                  _isSyncing ? 'Sedang Menyinkronkan...' : 'Data Tersinkronisasi',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
                const SizedBox(height: 8),
                Text(
                  'Terakhir sinkron: $_lastSyncTime',
                  style: const TextStyle(color: KasiraDS.textMuted),
                ),
                const SizedBox(height: 24),
                SizedBox(
                  width: double.infinity,
                  height: 50,
                  child: ElevatedButton.icon(
                    onPressed: _isSyncing ? null : _performManualSync,
                    icon: _isSyncing 
                        ? const SizedBox(
                            width: 20, 
                            height: 20, 
                            child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2)
                          )
                        : const Icon(LucideIcons.refreshCw, size: 20),
                    label: Text(_isSyncing ? 'Menyinkronkan...' : 'Sinkronisasi Sekarang'),
                  ),
                ),
              ],
            ),
          ),
          
          const SizedBox(height: 32),
          
          // Settings Options
          const Padding(
            padding: EdgeInsets.only(left: 8, bottom: 16),
            child: Text(
              'PENGATURAN SINKRONISASI',
              style: const TextStyle(
                color: KasiraDS.textMuted,
                fontWeight: FontWeight.bold,
                fontSize: 12,
                letterSpacing: 1.2,
              ),
            ),
          ),
          
          Card(
            margin: EdgeInsets.zero,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            child: Column(
              children: [
                SwitchListTile(
                  title: const Text('Sinkronisasi Otomatis', style: TextStyle(fontWeight: FontWeight.bold)),
                  subtitle: const Text('Sinkronisasi data di latar belakang saat terhubung ke internet', style: TextStyle(color: KasiraDS.textMuted, fontSize: 12)),
                  value: _isAutoSyncEnabled,
                  activeColor: KasiraDS.brandPrimary,
                  onChanged: (value) {
                    setState(() {
                      _isAutoSyncEnabled = value;
                    });
                  },
                ),
                const Divider(height: 1),
                ListTile(
                  title: const Text('Interval Sinkronisasi', style: TextStyle(fontWeight: FontWeight.bold)),
                  subtitle: const Text('Setiap 5 menit', style: TextStyle(color: KasiraDS.textMuted, fontSize: 12)),
                  trailing: const Icon(LucideIcons.chevronRight, color: KasiraDS.textMuted),
                  onTap: () {
                    // Show interval picker
                  },
                ),
                const Divider(height: 1),
                ListTile(
                  title: const Text('Sinkronisasi Hanya via Wi-Fi', style: TextStyle(fontWeight: FontWeight.bold)),
                  subtitle: const Text('Menghemat kuota data seluler', style: TextStyle(color: KasiraDS.textMuted, fontSize: 12)),
                  trailing: Switch(
                    value: false,
                    activeColor: KasiraDS.brandPrimary,
                    onChanged: (value) {},
                  ),
                ),
              ],
            ),
          ),
          
          const SizedBox(height: 32),
          
          // Diagnostic
          const Padding(
            padding: EdgeInsets.only(left: 8, bottom: 16),
            child: Text(
              'DIAGNOSTIK',
              style: const TextStyle(
                color: KasiraDS.textMuted,
                fontWeight: FontWeight.bold,
                fontSize: 12,
                letterSpacing: 1.2,
              ),
            ),
          ),
          
          Card(
            margin: EdgeInsets.zero,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            child: Column(
              children: [
                ListTile(
                  leading: const Icon(LucideIcons.database, color: KasiraDS.textMuted),
                  title: const Text('Data Belum Tersinkronisasi', style: TextStyle(fontWeight: FontWeight.bold)),
                  trailing: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                    decoration: BoxDecoration(
                      color: KasiraDS.surfaceSunken,
                      borderRadius: BorderRadius.circular(16),
                    ),
                    child: const Text('0 Item', style: TextStyle(fontWeight: FontWeight.bold, color: KasiraDS.textMuted)),
                  ),
                ),
                const Divider(height: 1),
                ListTile(
                  leading: const Icon(LucideIcons.fileText, color: KasiraDS.textMuted),
                  title: const Text('Log Sinkronisasi', style: TextStyle(fontWeight: FontWeight.bold)),
                  trailing: const Icon(LucideIcons.chevronRight, color: KasiraDS.textMuted),
                  onTap: () {},
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
