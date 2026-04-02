import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../../../core/config/app_config.dart';

class LoyaltyBalance {
  final String customerId;
  final String customerName;
  final double balance;
  final double lifetimeEarned;
  final double lifetimeRedeemed;
  final double redeemValueRp;

  const LoyaltyBalance({
    required this.customerId,
    required this.customerName,
    required this.balance,
    required this.lifetimeEarned,
    required this.lifetimeRedeemed,
    required this.redeemValueRp,
  });

  factory LoyaltyBalance.fromJson(Map<String, dynamic> json) => LoyaltyBalance(
        customerId: json['customer_id'] as String,
        customerName: json['customer_name'] as String,
        balance: (json['balance'] as num).toDouble(),
        lifetimeEarned: (json['lifetime_earned'] as num).toDouble(),
        lifetimeRedeemed: (json['lifetime_redeemed'] as num).toDouble(),
        redeemValueRp: (json['redeem_value_rp'] as num).toDouble(),
      );
}

class PointTxn {
  final String id;
  final String type; // earn | redeem | adjustment | refund
  final double amount;
  final double balanceAfter;
  final String? description;
  final String createdAt;

  const PointTxn({
    required this.id,
    required this.type,
    required this.amount,
    required this.balanceAfter,
    this.description,
    required this.createdAt,
  });

  factory PointTxn.fromJson(Map<String, dynamic> json) => PointTxn(
        id: json['id'] as String,
        type: json['type'] as String,
        amount: (json['amount'] as num).toDouble(),
        balanceAfter: (json['balance_after'] as num).toDouble(),
        description: json['description'] as String?,
        createdAt: json['created_at'] as String,
      );
}

// ─── Providers ───────────────────────────────────────────────────────────────

final loyaltyBalanceProvider = FutureProvider.family<LoyaltyBalance?, String>(
  (ref, customerId) async {
    if (customerId.isEmpty) return null;
    final storage = const FlutterSecureStorage();
    final token = await storage.read(key: 'access_token');
    final tenantId = await storage.read(key: 'tenant_id');

    final dio = Dio(BaseOptions(
      baseUrl: AppConfig.apiV1,
      connectTimeout: const Duration(seconds: 8),
      receiveTimeout: const Duration(seconds: 8),
    ));

    final res = await dio.get(
      '/loyalty/$customerId/balance',
      options: Options(headers: {
        if (token != null) 'Authorization': 'Bearer $token',
        if (tenantId != null) 'X-Tenant-ID': tenantId,
      }),
    );
    return LoyaltyBalance.fromJson(res.data['data'] as Map<String, dynamic>);
  },
);

final loyaltyHistoryProvider = FutureProvider.family<List<PointTxn>, String>(
  (ref, customerId) async {
    if (customerId.isEmpty) return [];
    final storage = const FlutterSecureStorage();
    final token = await storage.read(key: 'access_token');
    final tenantId = await storage.read(key: 'tenant_id');

    final dio = Dio(BaseOptions(
      baseUrl: AppConfig.apiV1,
      connectTimeout: const Duration(seconds: 8),
      receiveTimeout: const Duration(seconds: 8),
    ));

    final res = await dio.get(
      '/loyalty/$customerId/history',
      options: Options(headers: {
        if (token != null) 'Authorization': 'Bearer $token',
        if (tenantId != null) 'X-Tenant-ID': tenantId,
      }),
    );
    return (res.data['data'] as List)
        .map((e) => PointTxn.fromJson(e as Map<String, dynamic>))
        .toList();
  },
);
