import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../database/app_database.dart';
import '../api/api_client.dart';
import 'sync_service.dart';

// Re-export SyncStatus biar consumer cukup import sync_provider.dart
export 'sync_service.dart' show SyncStatus, SyncService;

final databaseProvider = Provider<AppDatabase>((ref) {
  return AppDatabase();
});

final sharedPreferencesProvider = Provider<SharedPreferences>((ref) {
  throw UnimplementedError('sharedPreferencesProvider must be overridden in main.dart');
});

final syncServiceProvider = Provider<SyncService>((ref) {
  final db = ref.watch(databaseProvider);
  final dio = ref.watch(apiClientProvider);
  final prefs = ref.watch(sharedPreferencesProvider);
  
  return SyncService(db, dio, prefs);
});
