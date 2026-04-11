import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../../../core/config/app_config.dart';

// ── Model ──

class ReservationModel {
  final String id;
  final String outletId;
  final String? tableId;
  final String? tableName;
  final String? tableFloorSection;
  final String reservationDate;
  final String startTime;
  final String? endTime;
  final int guestCount;
  final String customerName;
  final String? customerPhone;
  final String status;
  final String? source;
  final String? notes;
  final String? confirmedAt;
  final int? rowVersion;
  final DateTime createdAt;

  const ReservationModel({
    required this.id,
    required this.outletId,
    this.tableId,
    this.tableName,
    this.tableFloorSection,
    required this.reservationDate,
    required this.startTime,
    this.endTime,
    required this.guestCount,
    required this.customerName,
    this.customerPhone,
    required this.status,
    this.source,
    this.notes,
    this.confirmedAt,
    this.rowVersion,
    required this.createdAt,
  });

  factory ReservationModel.fromJson(Map<String, dynamic> json) => ReservationModel(
        id: json['id'] as String,
        outletId: json['outlet_id'] as String,
        tableId: json['table_id'] as String?,
        tableName: json['table_name'] as String?,
        tableFloorSection: json['table_floor_section'] as String?,
        reservationDate: json['reservation_date'] as String,
        startTime: json['start_time'] as String,
        endTime: json['end_time'] as String?,
        guestCount: (json['guest_count'] as num?)?.toInt() ?? 1,
        customerName: json['customer_name'] as String? ?? '',
        customerPhone: json['customer_phone'] as String?,
        status: json['status'] as String? ?? 'pending',
        source: json['source'] as String?,
        notes: json['notes'] as String?,
        confirmedAt: json['confirmed_at'] as String?,
        rowVersion: (json['row_version'] as num?)?.toInt(),
        createdAt: DateTime.tryParse(json['created_at'] as String? ?? '') ?? DateTime.now(),
      );

  String get statusLabel {
    switch (status) {
      case 'pending':
        return 'Menunggu';
      case 'confirmed':
        return 'Dikonfirmasi';
      case 'seated':
        return 'Duduk';
      case 'completed':
        return 'Selesai';
      case 'cancelled':
        return 'Dibatalkan';
      case 'no_show':
        return 'Tidak Hadir';
      default:
        return status;
    }
  }

  /// Formatted time display e.g. "14:00 - 16:00"
  String get timeDisplay {
    final start = startTime.length >= 5 ? startTime.substring(0, 5) : startTime;
    if (endTime != null && endTime!.isNotEmpty) {
      final end = endTime!.length >= 5 ? endTime!.substring(0, 5) : endTime!;
      return '$start - $end';
    }
    return start;
  }
}

// ── State ──

class ReservationState {
  final List<ReservationModel> reservations;
  final bool isLoading;
  final String? error;
  final DateTime selectedDate;

  ReservationState({
    this.reservations = const [],
    this.isLoading = false,
    this.error,
    DateTime? selectedDate,
  }) : selectedDate = selectedDate ?? DateTime.now();

  ReservationState copyWith({
    List<ReservationModel>? reservations,
    bool? isLoading,
    String? error,
    bool clearError = false,
    DateTime? selectedDate,
  }) =>
      ReservationState(
        reservations: reservations ?? this.reservations,
        isLoading: isLoading ?? this.isLoading,
        error: clearError ? null : (error ?? this.error),
        selectedDate: selectedDate ?? this.selectedDate,
      );
}

// ── Notifier ──

class ReservationNotifier extends StateNotifier<ReservationState> {
  ReservationNotifier() : super(ReservationState());

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

  static String _formatDate(DateTime d) =>
      '${d.year}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';

  Future<void> fetchReservations({DateTime? date, String? status}) async {
    final targetDate = date ?? state.selectedDate;
    state = state.copyWith(isLoading: true, clearError: true, selectedDate: targetDate);
    try {
      final outletId = await _storage.read(key: 'outlet_id');
      final params = <String, dynamic>{
        'outlet_id': outletId,
        'reservation_date': _formatDate(targetDate),
      };
      if (status != null) params['status'] = status;

      final res = await _dio.get(
        '/reservations/',
        queryParameters: params,
        options: Options(headers: await _headers()),
      );
      final list = (res.data['data'] as List)
          .map((r) => ReservationModel.fromJson(r as Map<String, dynamic>))
          .toList();
      state = state.copyWith(reservations: list, isLoading: false);
    } on DioException catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.response?.data?['detail']?.toString() ?? 'Gagal memuat reservasi',
      );
    }
  }

  Future<ReservationModel?> createReservation({
    required String reservationDate,
    required String startTime,
    required int guestCount,
    required String customerName,
    required String customerPhone,
    String? tableId,
    String? notes,
    String? source,
  }) async {
    try {
      final outletId = await _storage.read(key: 'outlet_id');
      final data = <String, dynamic>{
        'reservation_date': reservationDate,
        'start_time': startTime,
        'guest_count': guestCount,
        'customer_name': customerName,
        'customer_phone': customerPhone,
      };
      if (tableId != null) data['table_id'] = tableId;
      if (notes != null && notes.isNotEmpty) data['notes'] = notes;
      if (source != null) data['source'] = source;

      final res = await _dio.post(
        '/reservations/',
        queryParameters: {'outlet_id': outletId},
        data: data,
        options: Options(headers: await _headers()),
      );
      final reservation = ReservationModel.fromJson(res.data['data'] as Map<String, dynamic>);
      await fetchReservations();
      return reservation;
    } on DioException catch (e) {
      state = state.copyWith(error: e.response?.data?['detail']?.toString() ?? 'Gagal membuat reservasi');
      return null;
    }
  }

  Future<bool> confirmReservation(String id) async => _updateStatus(id, 'confirm');
  Future<bool> seatReservation(String id) async => _updateStatus(id, 'seat');
  Future<bool> completeReservation(String id) async => _updateStatus(id, 'complete');
  Future<bool> cancelReservation(String id) async => _updateStatus(id, 'cancel');
  Future<bool> noShowReservation(String id) async => _updateStatus(id, 'no-show');

  Future<bool> _updateStatus(String id, String action) async {
    try {
      await _dio.put(
        '/reservations/$id/$action',
        options: Options(headers: await _headers()),
      );
      await fetchReservations();
      return true;
    } on DioException catch (e) {
      state = state.copyWith(error: e.response?.data?['detail']?.toString() ?? 'Gagal mengubah status');
      return false;
    }
  }

  void changeDate(DateTime newDate) {
    fetchReservations(date: newDate);
  }
}

// ── Provider ──

final reservationProvider = StateNotifierProvider<ReservationNotifier, ReservationState>(
  (_) => ReservationNotifier(),
);
