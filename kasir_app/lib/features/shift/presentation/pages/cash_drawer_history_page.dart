import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:lucide_icons/lucide_icons.dart';
import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../../../../core/config/app_config.dart';
import '../../../../core/theme/app_colors.dart';

class CashDrawerHistoryPage extends StatefulWidget {
  const CashDrawerHistoryPage({super.key});

  @override
  State<CashDrawerHistoryPage> createState() => _CashDrawerHistoryPageState();
}

class _CashDrawerHistoryPageState extends State<CashDrawerHistoryPage> {
  List<Map<String, dynamic>> _activities = [];
  bool _isLoading = true;
  String? _error;
  double _totalIn = 0, _totalOut = 0;

  final _currency = NumberFormat.currency(locale: 'id_ID', symbol: 'Rp ', decimalDigits: 0);
  final _dateFormat = DateFormat('dd MMM yyyy • HH:mm', 'id_ID');

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() { _isLoading = true; _error = null; });
    try {
      const storage = FlutterSecureStorage();
      final token = await storage.read(key: 'access_token');
      final tenantId = await storage.read(key: 'tenant_id');
      final outletId = await storage.read(key: 'outlet_id');
      final shiftId = await storage.read(key: 'shift_session_id');

      if (shiftId == null) {
        setState(() { _activities = []; _isLoading = false; });
        return;
      }

      final dio = Dio(BaseOptions(baseUrl: AppConfig.apiV1, connectTimeout: const Duration(seconds: 15), receiveTimeout: const Duration(seconds: 15)));
      final headers = {
        if (token != null) 'Authorization': 'Bearer $token',
        if (tenantId != null) 'X-Tenant-ID': tenantId,
      };

      final res = await dio.get(
        '/shifts/$shiftId/activities',
        queryParameters: {'outlet_id': outletId},
        options: Options(headers: headers),
      );

      final data = res.data['data'];
      // Backend sekarang return {activities: [...], cash_payments: [...]}
      final List<Map<String, dynamic>> activityList;
      final List<Map<String, dynamic>> paymentList;
      if (data is Map) {
        activityList = ((data['activities'] as List?) ?? []).cast<Map<String, dynamic>>();
        paymentList = ((data['cash_payments'] as List?) ?? []).cast<Map<String, dynamic>>();
      } else {
        // Fallback: old format (list only)
        activityList = (data as List? ?? []).cast<Map<String, dynamic>>();
        paymentList = [];
      }

      double totalIn = 0, totalOut = 0;
      final allItems = <Map<String, dynamic>>[];

      for (final a in activityList) {
        final amount = (a['amount'] as num?)?.toDouble() ?? 0;
        if (a['activity_type'] == 'income') totalIn += amount;
        if (a['activity_type'] == 'expense') totalOut += amount;
        allItems.add(a);
      }

      // Tambahkan payment transactions sebagai "income" items
      for (final p in paymentList) {
        final net = (p['net_amount'] as num?)?.toDouble() ?? 0;
        final method = p['payment_method'] ?? 'cash';
        final displayNum = p['display_number'];
        totalIn += net;
        allItems.add({
          'activity_type': 'income',
          'amount': net,
          'description': 'Order #${displayNum ?? '-'} (${method == 'qris' ? 'QRIS' : 'Cash'})',
          'created_at': p['paid_at'] ?? p['created_at'],
        });
      }

      // Sort by created_at descending
      allItems.sort((a, b) {
        final aTime = DateTime.tryParse(a['created_at']?.toString() ?? '') ?? DateTime(2000);
        final bTime = DateTime.tryParse(b['created_at']?.toString() ?? '') ?? DateTime(2000);
        return bTime.compareTo(aTime);
      });

      if (mounted) setState(() { _activities = allItems; _totalIn = totalIn; _totalOut = totalOut; _isLoading = false; });
    } on DioException catch (e) {
      final msg = e.response?.data?['detail'] ?? 'Gagal memuat riwayat kas';
      if (mounted) setState(() { _error = msg.toString(); _isLoading = false; });
    } catch (_) {
      if (mounted) setState(() { _error = 'Gagal memuat riwayat kas'; _isLoading = false; });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: AppColors.surface,
        title: const Text('Riwayat Laci Kasir', style: TextStyle(color: AppColors.textPrimary)),
        iconTheme: const IconThemeData(color: AppColors.textPrimary),
        elevation: 0,
        actions: [
          IconButton(icon: const Icon(LucideIcons.refreshCw, color: AppColors.primary), onPressed: _load),
          const SizedBox(width: 8),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? _buildError()
              : Column(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(24),
                      color: AppColors.surface,
                      child: Row(
                        children: [
                          Expanded(child: _buildSummaryCard('Total Penerimaan', _currency.format(_totalIn), LucideIcons.arrowDownLeft, AppColors.success)),
                          const SizedBox(width: 16),
                          Expanded(child: _buildSummaryCard('Total Pengeluaran', _currency.format(_totalOut), LucideIcons.arrowUpRight, AppColors.error)),
                        ],
                      ),
                    ),
                    Expanded(
                      child: _activities.isEmpty
                          ? const Center(child: Text('Belum ada aktivitas kas shift ini', style: TextStyle(color: AppColors.textSecondary)))
                          : ListView.builder(
                              padding: const EdgeInsets.all(24),
                              itemCount: _activities.length,
                              itemBuilder: (_, i) => _buildTile(_activities[i]),
                            ),
                    ),
                  ],
                ),
    );
  }

  Widget _buildError() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Text(_error!, style: const TextStyle(color: AppColors.textSecondary)),
          const SizedBox(height: 16),
          ElevatedButton.icon(onPressed: _load, icon: const Icon(LucideIcons.refreshCw, size: 16), label: const Text('Coba Lagi')),
        ],
      ),
    );
  }

  Widget _buildTile(Map<String, dynamic> a) {
    final isIncome = a['activity_type'] == 'income';
    final amount = (a['amount'] as num?)?.toDouble() ?? 0;
    final color = isIncome ? AppColors.success : AppColors.error;
    final icon = isIncome ? LucideIcons.arrowDownLeft : LucideIcons.arrowUpRight;
    final description = a['description'] as String? ?? '-';
    DateTime? createdAt;
    try {
      createdAt = DateTime.parse(a['created_at'] as String);
    } catch (_) {}

    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: ListTile(
        contentPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
        leading: Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(color: color.withOpacity(0.1), borderRadius: BorderRadius.circular(12)),
          child: Icon(icon, color: color),
        ),
        title: Text(description, style: const TextStyle(fontWeight: FontWeight.bold)),
        subtitle: createdAt != null
            ? Padding(
                padding: const EdgeInsets.only(top: 4),
                child: Text(_dateFormat.format(createdAt.toLocal()), style: const TextStyle(color: AppColors.textSecondary, fontSize: 12)),
              )
            : null,
        trailing: Text(
          _currency.format(amount),
          style: TextStyle(color: color, fontWeight: FontWeight.bold, fontSize: 16),
        ),
      ),
    );
  }

  Widget _buildSummaryCard(String title, String amount, IconData icon, Color color) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: color.withOpacity(0.05),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: color.withOpacity(0.2)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [Icon(icon, color: color, size: 20), const SizedBox(width: 8), Text(title, style: TextStyle(color: color, fontWeight: FontWeight.bold, fontSize: 12))]),
          const SizedBox(height: 16),
          Text(amount, style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.bold, color: color)),
        ],
      ),
    );
  }
}
