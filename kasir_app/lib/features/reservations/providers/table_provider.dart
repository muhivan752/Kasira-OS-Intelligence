import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../../../core/config/app_config.dart';

// ── Model ──

class TableInfo {
  final String id;
  final String name;
  final int capacity;
  final String floorSection;
  final String status;
  final bool isActive;

  const TableInfo({
    required this.id,
    required this.name,
    required this.capacity,
    required this.floorSection,
    required this.status,
    required this.isActive,
  });

  factory TableInfo.fromJson(Map<String, dynamic> json) => TableInfo(
        id: json['id'] as String,
        name: json['name'] as String? ?? '',
        capacity: (json['capacity'] as num?)?.toInt() ?? 2,
        floorSection: json['floor_section'] as String? ?? '',
        status: json['status'] as String? ?? 'available',
        isActive: json['is_active'] as bool? ?? true,
      );
}

// ── State ──

class TableListState {
  final List<TableInfo> tables;
  final bool isLoading;
  final String? error;

  const TableListState({this.tables = const [], this.isLoading = false, this.error});

  TableListState copyWith({List<TableInfo>? tables, bool? isLoading, String? error, bool clearError = false}) =>
      TableListState(
        tables: tables ?? this.tables,
        isLoading: isLoading ?? this.isLoading,
        error: clearError ? null : (error ?? this.error),
      );
}

// ── Notifier ──

class TableListNotifier extends StateNotifier<TableListState> {
  TableListNotifier() : super(const TableListState());

  final _storage = const FlutterSecureStorage();

  Dio get _dio => Dio(BaseOptions(
        baseUrl: AppConfig.apiV1,
        connectTimeout: const Duration(seconds: 10),
        receiveTimeout: const Duration(seconds: 10),
      ));

  Future<Map<String, String>> _headers() async {
    final token = await _storage.read(key: 'access_token');
    final tenantId = await _storage.read(key: 'tenant_id');
    return {
      if (token != null) 'Authorization': 'Bearer $token',
      if (tenantId != null) 'X-Tenant-ID': tenantId,
    };
  }

  Future<void> fetchTables() async {
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      final outletId = await _storage.read(key: 'outlet_id');
      final res = await _dio.get(
        '/tables/',
        queryParameters: {'outlet_id': outletId},
        options: Options(headers: await _headers()),
      );
      final list = (res.data['data'] as List)
          .map((t) => TableInfo.fromJson(t as Map<String, dynamic>))
          .toList();
      state = state.copyWith(tables: list, isLoading: false);
    } on DioException catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.response?.data?['detail']?.toString() ?? 'Gagal memuat meja',
      );
    }
  }
}

// ── Provider ──

final tableListProvider = StateNotifierProvider<TableListNotifier, TableListState>(
  (_) => TableListNotifier(),
);
