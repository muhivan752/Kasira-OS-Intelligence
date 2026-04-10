import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../config/app_config.dart';
import '../sync/sync_provider.dart';

/// Global navigator key — digunakan untuk redirect ke login dari interceptor
final navigatorKey = GlobalKey<NavigatorState>();

final apiClientProvider = Provider<Dio>((ref) {
  // rebuild provider saat prefs berubah (base URL update)
  ref.watch(sharedPreferencesProvider);

  final dio = Dio(BaseOptions(
    baseUrl: AppConfig.apiV1,
    connectTimeout: const Duration(seconds: 10),
    receiveTimeout: const Duration(seconds: 10),
    headers: {'Content-Type': 'application/json'},
  ));

  dio.interceptors.add(InterceptorsWrapper(
    onRequest: (options, handler) async {
      final storage = const FlutterSecureStorage();
      final token = await storage.read(key: 'access_token');
      final tenantId = await storage.read(key: 'tenant_id');
      if (token != null) {
        options.headers['Authorization'] = 'Bearer $token';
      }
      if (tenantId != null) {
        options.headers['X-Tenant-ID'] = tenantId;
      }
      return handler.next(options);
    },
    onError: (error, handler) async {
      if (error.response?.statusCode == 401) {
        // Token expired/revoked — clear storage & redirect to login
        const storage = FlutterSecureStorage();
        await storage.deleteAll();
        navigatorKey.currentState?.pushNamedAndRemoveUntil(
          '/login',
          (route) => false,
        );
      }
      return handler.next(error);
    },
  ));

  return dio;
});
