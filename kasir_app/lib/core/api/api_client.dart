import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../config/app_config.dart';
import '../sync/sync_provider.dart';
import '../services/session_cache.dart';

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
    onRequest: (options, handler) {
      // Read from in-memory cache — 0ms, no async
      final cache = SessionCache.instance;
      if (cache.accessToken != null) {
        options.headers['Authorization'] = 'Bearer ${cache.accessToken}';
      }
      if (cache.tenantId != null) {
        options.headers['X-Tenant-ID'] = cache.tenantId;
      }
      return handler.next(options);
    },
    onError: (error, handler) async {
      if (error.response?.statusCode == 401) {
        // Token expired/revoked — clear cache + storage & redirect to login
        await SessionCache.instance.clear();
        final ctx = navigatorKey.currentContext;
        if (ctx != null) {
          GoRouter.of(ctx).go('/login');
        }
      }
      return handler.next(error);
    },
  ));

  return dio;
});
