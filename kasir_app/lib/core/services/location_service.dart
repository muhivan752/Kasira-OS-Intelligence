import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:geolocator/geolocator.dart';
import '../config/app_config.dart';

/// Silent location service — fire once after login, never blocks UI.
class LocationService {
  static const _storage = FlutterSecureStorage();
  static const _flagKey = 'location_sent';

  /// Send outlet location to backend. Call once after login.
  /// Returns silently on any failure — never throws.
  static Future<void> sendLocationSilent() async {
    try {
      // Only send once
      final alreadySent = await _storage.read(key: _flagKey);
      if (alreadySent == 'true') return;

      // Check permission — request if not determined, skip if denied
      LocationPermission permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied) {
        permission = await Geolocator.requestPermission();
      }
      if (permission == LocationPermission.denied ||
          permission == LocationPermission.deniedForever) {
        return; // User said no — respect it, don't ask again
      }

      // Check if location services are enabled
      if (!await Geolocator.isLocationServiceEnabled()) return;

      // Get position (timeout 10s)
      final position = await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(
          accuracy: LocationAccuracy.low, // coarse is enough
          timeLimit: Duration(seconds: 10),
        ),
      );

      // Send to backend
      final token = await _storage.read(key: 'access_token');
      final tenantId = await _storage.read(key: 'tenant_id');
      final outletId = await _storage.read(key: 'outlet_id');
      if (token == null || outletId == null) return;

      final dio = Dio(BaseOptions(
        baseUrl: AppConfig.apiV1,
        connectTimeout: const Duration(seconds: 10),
        receiveTimeout: const Duration(seconds: 10),
      ));

      await dio.post(
        '/outlets/$outletId/location',
        data: {
          'latitude': position.latitude,
          'longitude': position.longitude,
        },
        options: Options(headers: {
          'Authorization': 'Bearer $token',
          if (tenantId != null) 'X-Tenant-ID': tenantId,
        }),
      );

      // Mark as sent — won't ask again
      await _storage.write(key: _flagKey, value: 'true');
    } catch (_) {
      // Silent — never crash the app for location
    }
  }
}
