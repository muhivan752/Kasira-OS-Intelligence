import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'sync_provider.dart';

final apiClientProvider = Provider<Dio>((ref) {
  final prefs = ref.watch(sharedPreferencesProvider);
  final token = prefs.getString('access_token');
  
  final dio = Dio(BaseOptions(
    baseUrl: 'http://127.0.0.1:8000/api/v1', // Should be configurable
    connectTimeout: const Duration(seconds: 10),
    receiveTimeout: const Duration(seconds: 10),
    headers: {
      'Content-Type': 'application/json',
      if (token != null) 'Authorization': 'Bearer $token',
    },
  ));

  dio.interceptors.add(InterceptorsWrapper(
    onRequest: (options, handler) {
      // Refresh token logic can be added here
      return handler.next(options);
    },
  ));

  return dio;
});
