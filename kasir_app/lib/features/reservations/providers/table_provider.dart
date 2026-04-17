import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:dio/dio.dart';
import '../../../core/config/app_config.dart';
import '../../../core/services/session_cache.dart';

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

  final _cache = SessionCache.instance;

  Dio get _dio => Dio(BaseOptions(
        baseUrl: AppConfig.apiV1,
        connectTimeout: const Duration(seconds: 10),
        receiveTimeout: const Duration(seconds: 10),
      ));

  Map<String, String> get _headers => _cache.authHeaders;

  Future<void> fetchTables() async {
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      final res = await _dio.get(
        '/tables/',
        queryParameters: {'outlet_id': _cache.outletId},
        options: Options(headers: _headers),
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
