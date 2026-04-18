import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:dio/dio.dart';
import '../../../core/config/app_config.dart';
import '../../../core/services/session_cache.dart';

// ── Models ──

class TabSplitModel {
  final String id;
  final String tabId;
  final String? paymentId;
  final String label;
  final double amount;
  final String status; // unpaid, pending, paid
  final List<String> itemIds;
  final int rowVersion;

  const TabSplitModel({
    required this.id,
    required this.tabId,
    this.paymentId,
    required this.label,
    required this.amount,
    required this.status,
    this.itemIds = const [],
    required this.rowVersion,
  });

  factory TabSplitModel.fromJson(Map<String, dynamic> json) => TabSplitModel(
        id: json['id'] as String,
        tabId: json['tab_id'] as String,
        paymentId: json['payment_id'] as String?,
        label: json['label'] as String,
        amount: json['amount'] is num ? (json['amount'] as num).toDouble() : double.tryParse(json['amount']?.toString() ?? '') ?? 0,
        status: json['status'] as String? ?? 'unpaid',
        itemIds: (json['item_ids'] as List?)?.map((e) => e.toString()).toList() ?? [],
        rowVersion: (json['row_version'] as num?)?.toInt() ?? 0,
      );

  bool get isPaid => status == 'paid';
  bool get isUnpaid => status == 'unpaid';
}

class TabModel {
  final String id;
  final String outletId;
  final String? tableId;
  final String? tableName;
  final String tabNumber;
  final String? customerName;
  final int guestCount;
  final double subtotal;
  final double taxAmount;
  final double serviceChargeAmount;
  final double discountAmount;
  final double totalAmount;
  final double paidAmount;
  final double remainingAmount;
  final String? splitMethod;
  final String status; // open, asking_bill, splitting, paid, cancelled
  final String? notes;
  final int rowVersion;
  final List<TabSplitModel> splits;
  final List<String> orderIds;
  final DateTime createdAt;

  const TabModel({
    required this.id,
    required this.outletId,
    this.tableId,
    this.tableName,
    required this.tabNumber,
    this.customerName,
    required this.guestCount,
    required this.subtotal,
    required this.taxAmount,
    required this.serviceChargeAmount,
    required this.discountAmount,
    required this.totalAmount,
    required this.paidAmount,
    required this.remainingAmount,
    this.splitMethod,
    required this.status,
    this.notes,
    required this.rowVersion,
    this.splits = const [],
    this.orderIds = const [],
    required this.createdAt,
  });

  static double _toDouble(dynamic v) =>
      v is num ? v.toDouble() : double.tryParse(v?.toString() ?? '') ?? 0;

  factory TabModel.fromJson(Map<String, dynamic> json) => TabModel(
        id: json['id'] as String,
        outletId: json['outlet_id'] as String,
        tableId: json['table_id'] as String?,
        tableName: json['table_name'] as String?,
        tabNumber: json['tab_number'] as String,
        customerName: json['customer_name'] as String?,
        guestCount: (json['guest_count'] as num?)?.toInt() ?? 1,
        subtotal: _toDouble(json['subtotal']),
        taxAmount: _toDouble(json['tax_amount']),
        serviceChargeAmount: _toDouble(json['service_charge_amount']),
        discountAmount: _toDouble(json['discount_amount']),
        totalAmount: _toDouble(json['total_amount']),
        paidAmount: _toDouble(json['paid_amount']),
        remainingAmount: _toDouble(json['remaining_amount']),
        splitMethod: json['split_method'] as String?,
        status: json['status'] as String? ?? 'open',
        notes: json['notes'] as String?,
        rowVersion: (json['row_version'] as num?)?.toInt() ?? 0,
        splits: (json['splits'] as List?)
                ?.map((s) => TabSplitModel.fromJson(s as Map<String, dynamic>))
                .toList() ??
            [],
        orderIds: (json['order_ids'] as List?)?.map((e) => e.toString()).toList() ?? [],
        createdAt: DateTime.tryParse(json['created_at'] as String? ?? '') ?? DateTime.now(),
      );

  bool get isOpen => status == 'open' || status == 'asking_bill';
  bool get isSplitting => status == 'splitting';
  bool get isPaid => status == 'paid';
  bool get isCancelled => status == 'cancelled';
  bool get hasOrders => orderIds.isNotEmpty;
}

class TabItemModel {
  final String id;
  final String orderId;
  final String? productId;
  final String productName;
  final int quantity;
  final double unitPrice;
  final double totalPrice;

  const TabItemModel({
    required this.id,
    required this.orderId,
    this.productId,
    required this.productName,
    required this.quantity,
    required this.unitPrice,
    required this.totalPrice,
  });

  factory TabItemModel.fromJson(Map<String, dynamic> j) => TabItemModel(
        id: j['id'] as String,
        orderId: j['order_id'] as String,
        productId: j['product_id'] as String?,
        productName: j['product_name'] as String? ?? 'Item',
        quantity: (j['quantity'] as num?)?.toInt() ?? 1,
        unitPrice: (j['unit_price'] as num?)?.toDouble() ?? 0,
        totalPrice: (j['total_price'] as num?)?.toDouble() ?? 0,
      );
}

// ── Active Tabs Count (for dashboard badge) ──

final activeTabsCountProvider = FutureProvider.autoDispose<int>((ref) async {
  final cache = SessionCache.instance;
  final outletId = cache.outletId;
  if (outletId == null) return 0;
  final dio = Dio(BaseOptions(
    baseUrl: AppConfig.apiV1,
    connectTimeout: const Duration(seconds: 8),
    receiveTimeout: const Duration(seconds: 8),
  ));
  try {
    final res = await dio.get(
      '/tabs/',
      queryParameters: {'outlet_id': outletId, 'status': 'open'},
      options: Options(headers: cache.authHeaders),
    );
    final list = (res.data['data'] as List?) ?? [];
    int count = list.length;
    try {
      final res2 = await dio.get(
        '/tabs/',
        queryParameters: {'outlet_id': outletId, 'status': 'asking_bill'},
        options: Options(headers: cache.authHeaders),
      );
      count += ((res2.data['data'] as List?) ?? []).length;
    } catch (_) {}
    return count;
  } catch (_) {
    return 0;
  }
});

// ── Add Order Context (state for "tambah pesanan" flow) ──

class AddOrderContext {
  final String tabId;
  final String tabNumber;
  final String? tableName;
  const AddOrderContext({required this.tabId, required this.tabNumber, this.tableName});
}

final addOrderContextProvider = StateProvider<AddOrderContext?>((ref) => null);

// ── State ──

class TabListState {
  final List<TabModel> tabs;
  final bool isLoading;
  final String? error;

  const TabListState({this.tabs = const [], this.isLoading = false, this.error});

  TabListState copyWith({List<TabModel>? tabs, bool? isLoading, String? error, bool clearError = false}) =>
      TabListState(
        tabs: tabs ?? this.tabs,
        isLoading: isLoading ?? this.isLoading,
        error: clearError ? null : (error ?? this.error),
      );
}

// ── Notifier ──

class TabNotifier extends StateNotifier<TabListState> {
  TabNotifier() : super(const TabListState());

  final _cache = SessionCache.instance;

  Dio get _dio => Dio(BaseOptions(
        baseUrl: AppConfig.apiV1,
        connectTimeout: const Duration(seconds: 10),
        receiveTimeout: const Duration(seconds: 10),
      ));

  Map<String, String> get _headers => _cache.authHeaders;

  Future<void> fetchTabs({String? status}) async {
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      final outletId = _cache.outletId;
      final res = await _dio.get(
        '/tabs/',
        queryParameters: {
          'outlet_id': outletId,
          if (status != null) 'status': status,
        },
        options: Options(headers: _headers),
      );
      final list = (res.data['data'] as List)
          .map((t) => TabModel.fromJson(t as Map<String, dynamic>))
          .toList();
      state = state.copyWith(tabs: list, isLoading: false);
    } on DioException catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.response?.data?['detail']?.toString() ?? 'Gagal memuat tab',
      );
    }
  }

  Future<TabModel?> openTab({
    String? tableId,
    String? customerName,
    int guestCount = 1,
  }) async {
    try {
      final outletId = _cache.outletId;
      final res = await _dio.post(
        '/tabs/',
        options: Options(headers: _headers),
        data: {
          'outlet_id': outletId,
          if (tableId != null) 'table_id': tableId,
          if (customerName != null) 'customer_name': customerName,
          'guest_count': guestCount,
        },
      );
      final tab = TabModel.fromJson(res.data['data'] as Map<String, dynamic>);
      await fetchTabs();
      return tab;
    } on DioException catch (e) {
      state = state.copyWith(error: e.response?.data?['detail']?.toString() ?? 'Gagal membuka tab');
      return null;
    }
  }

  Future<TabModel?> getTab(String tabId) async {
    try {
      final res = await _dio.get(
        '/tabs/$tabId',
        options: Options(headers: _headers),
      );
      return TabModel.fromJson(res.data['data'] as Map<String, dynamic>);
    } catch (_) {
      return null;
    }
  }

  Future<List<TabItemModel>> getTabItems(String tabId) async {
    try {
      final res = await _dio.get(
        '/tabs/$tabId/items',
        options: Options(headers: _headers),
      );
      final list = (res.data['data'] as List)
          .map((i) => TabItemModel.fromJson(i as Map<String, dynamic>))
          .toList();
      return list;
    } catch (_) {
      return [];
    }
  }

  Future<TabModel?> addOrderToTab(String tabId, String orderId) async {
    try {
      final res = await _dio.post(
        '/tabs/$tabId/orders',
        options: Options(headers: _headers),
        data: {'order_id': orderId},
      );
      final tab = TabModel.fromJson(res.data['data'] as Map<String, dynamic>);
      await fetchTabs();
      return tab;
    } on DioException catch (e) {
      state = state.copyWith(error: e.response?.data?['detail']?.toString() ?? 'Gagal menambah order');
      return null;
    }
  }

  Future<TabModel?> splitEqual(String tabId, int numPeople, int rowVersion) async {
    try {
      final res = await _dio.post(
        '/tabs/$tabId/split/equal',
        options: Options(headers: _headers),
        data: {'num_people': numPeople, 'row_version': rowVersion},
      );
      return TabModel.fromJson(res.data['data'] as Map<String, dynamic>);
    } on DioException catch (e) {
      state = state.copyWith(error: e.response?.data?['detail']?.toString() ?? 'Gagal split');
      return null;
    }
  }

  Future<TabModel?> splitPerItem(
      String tabId, List<Map<String, dynamic>> assignments, int rowVersion) async {
    try {
      final res = await _dio.post(
        '/tabs/$tabId/split/per-item',
        options: Options(headers: _headers),
        data: {'assignments': assignments, 'row_version': rowVersion},
      );
      return TabModel.fromJson(res.data['data'] as Map<String, dynamic>);
    } on DioException catch (e) {
      state = state.copyWith(error: e.response?.data?['detail']?.toString() ?? 'Gagal split');
      return null;
    }
  }

  Future<TabModel?> splitCustom(
      String tabId, List<Map<String, dynamic>> splits, int rowVersion) async {
    try {
      final res = await _dio.post(
        '/tabs/$tabId/split/custom',
        options: Options(headers: _headers),
        data: {'splits': splits, 'row_version': rowVersion},
      );
      return TabModel.fromJson(res.data['data'] as Map<String, dynamic>);
    } on DioException catch (e) {
      state = state.copyWith(error: e.response?.data?['detail']?.toString() ?? 'Gagal split');
      return null;
    }
  }

  Future<TabModel?> payFull(
      String tabId, String paymentMethod, double amountPaid, int rowVersion,
      {String? idempotencyKey}) async {
    try {
      final res = await _dio.post(
        '/tabs/$tabId/pay-full',
        options: Options(headers: _headers),
        data: {
          'payment_method': paymentMethod,
          'amount_paid': amountPaid,
          'row_version': rowVersion,
          if (idempotencyKey != null) 'idempotency_key': idempotencyKey,
        },
      );
      final tab = TabModel.fromJson(res.data['data'] as Map<String, dynamic>);
      await fetchTabs();
      return tab;
    } on DioException catch (e) {
      state = state.copyWith(error: e.response?.data?['detail']?.toString() ?? 'Gagal bayar');
      return null;
    }
  }

  Future<TabModel?> paySplit(
      String tabId, String splitId, String paymentMethod, double amountPaid, int rowVersion,
      {String? idempotencyKey}) async {
    try {
      final res = await _dio.post(
        '/tabs/$tabId/splits/$splitId/pay',
        options: Options(headers: _headers),
        data: {
          'payment_method': paymentMethod,
          'amount_paid': amountPaid,
          'row_version': rowVersion,
          if (idempotencyKey != null) 'idempotency_key': idempotencyKey,
        },
      );
      return TabModel.fromJson(res.data['data'] as Map<String, dynamic>);
    } on DioException catch (e) {
      state = state.copyWith(error: e.response?.data?['detail']?.toString() ?? 'Gagal bayar split');
      return null;
    }
  }

  Future<TabModel?> moveTable(String tabId, String newTableId, int rowVersion) async {
    try {
      final res = await _dio.post(
        '/tabs/$tabId/move-table',
        options: Options(headers: _headers),
        data: {'new_table_id': newTableId, 'row_version': rowVersion},
      );
      final tab = TabModel.fromJson(res.data['data'] as Map<String, dynamic>);
      await fetchTabs();
      return tab;
    } on DioException catch (e) {
      state = state.copyWith(error: e.response?.data?['detail']?.toString() ?? 'Gagal pindah meja');
      return null;
    }
  }

  Future<TabModel?> mergeTab(String targetTabId, String sourceTabId, int rowVersion) async {
    try {
      final res = await _dio.post(
        '/tabs/$targetTabId/merge',
        options: Options(headers: _headers),
        data: {'source_tab_id': sourceTabId, 'row_version': rowVersion},
      );
      final tab = TabModel.fromJson(res.data['data'] as Map<String, dynamic>);
      await fetchTabs();
      return tab;
    } on DioException catch (e) {
      state = state.copyWith(error: e.response?.data?['detail']?.toString() ?? 'Gagal gabung tab');
      return null;
    }
  }

  Future<TabModel?> requestBill(String tabId) async {
    try {
      final res = await _dio.post(
        '/tabs/$tabId/request-bill',
        options: Options(headers: _headers),
      );
      final tab = TabModel.fromJson(res.data['data'] as Map<String, dynamic>);
      await fetchTabs();
      return tab;
    } on DioException catch (e) {
      state = state.copyWith(error: e.response?.data?['detail']?.toString() ?? 'Gagal minta bill');
      return null;
    }
  }

  Future<TabModel?> cancelTab(String tabId) async {
    try {
      final res = await _dio.post(
        '/tabs/$tabId/cancel',
        options: Options(headers: _headers),
      );
      final tab = TabModel.fromJson(res.data['data'] as Map<String, dynamic>);
      await fetchTabs();
      return tab;
    } on DioException catch (e) {
      state = state.copyWith(error: e.response?.data?['detail']?.toString() ?? 'Gagal membatalkan tab');
      return null;
    }
  }
}

// ── Providers ──

final tabProvider = StateNotifierProvider<TabNotifier, TabListState>((ref) {
  return TabNotifier();
});
