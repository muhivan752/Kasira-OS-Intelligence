import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:intl/intl.dart';
import 'package:lucide_icons/lucide_icons.dart';
import 'package:dio/dio.dart';
import 'package:go_router/go_router.dart';
import '../../../../core/config/app_config.dart';
import '../../../../core/services/session_cache.dart';
import '../../../../core/theme/app_colors.dart';
import 'cash_drawer_history_page.dart';

class ShiftPage extends StatefulWidget {
  const ShiftPage({super.key});

  @override
  State<ShiftPage> createState() => _ShiftPageState();
}

class _ShiftPageState extends State<ShiftPage> {
  final _cashController = TextEditingController();
  final _currency = NumberFormat.currency(locale: 'id_ID', symbol: 'Rp ', decimalDigits: 0);

  Map<String, dynamic>? _shift;
  bool _isLoading = true;
  bool _isClosing = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadShift();
  }

  @override
  void dispose() {
    _cashController.dispose();
    super.dispose();
  }

  Map<String, String> get _headers => SessionCache.instance.authHeaders;

  Dio get _dio => Dio(BaseOptions(
        baseUrl: AppConfig.apiV1,
        connectTimeout: const Duration(seconds: 15),
        receiveTimeout: const Duration(seconds: 15),
      ));

  Future<void> _loadShift() async {
    setState(() { _isLoading = true; _error = null; });
    try {
      final outletId = SessionCache.instance.outletId;

      final res = await _dio.get(
        '/shifts/current',
        queryParameters: {'outlet_id': outletId},
        options: Options(headers: _headers),
      );
      setState(() { _shift = res.data['data']; _isLoading = false; });
    } catch (_) {
      setState(() { _error = 'Gagal memuat data shift'; _isLoading = false; });
    }
  }

  Future<void> _closeShift() async {
    final actualCash = double.tryParse(_cashController.text.trim()) ?? 0;
    if (actualCash <= 0) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Masukkan jumlah uang aktual di laci'), backgroundColor: AppColors.error, behavior: SnackBarBehavior.floating),
      );
      return;
    }

    setState(() => _isClosing = true);
    try {
      final shiftId = _shift!['id'];
      final closeRes = await _dio.post(
        '/shifts/$shiftId/close',
        options: Options(headers: _headers),
        data: {'ending_cash': actualCash},
      );

      await SessionCache.instance.setShiftSessionId(null);

      // Show variance result before navigating
      if (mounted) {
        final data = closeRes.data['data'];
        final variance = (data?['variance'] as num?)?.toDouble() ?? 0;
        final varianceStatus = data?['variance_status'] as String? ?? 'balanced';
        final message = closeRes.data['message'] as String? ?? 'Shift ditutup';

        await showDialog(
          context: context,
          barrierDismissible: false,
          builder: (ctx) => AlertDialog(
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
            icon: Icon(
              varianceStatus == 'balanced' ? LucideIcons.checkCircle2 : LucideIcons.alertTriangle,
              color: varianceStatus == 'balanced' ? AppColors.success : AppColors.warning,
              size: 48,
            ),
            title: Text(varianceStatus == 'balanced' ? 'Shift Ditutup' : 'Shift Ditutup — Ada Selisih'),
            content: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(message, textAlign: TextAlign.center, style: const TextStyle(color: AppColors.textSecondary)),
                if (varianceStatus != 'balanced') ...[
                  const SizedBox(height: 16),
                  Container(
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: (varianceStatus == 'surplus' ? AppColors.success : AppColors.error).withOpacity(0.1),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(
                          varianceStatus == 'surplus' ? LucideIcons.trendingUp : LucideIcons.trendingDown,
                          color: varianceStatus == 'surplus' ? AppColors.success : AppColors.error,
                        ),
                        const SizedBox(width: 8),
                        Text(
                          '${varianceStatus == 'surplus' ? '+' : '-'} ${_currency.format(variance.abs())}',
                          style: TextStyle(
                            fontSize: 20,
                            fontWeight: FontWeight.bold,
                            color: varianceStatus == 'surplus' ? AppColors.success : AppColors.error,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ],
            ),
            actions: [
              ElevatedButton(
                onPressed: () {
                  Navigator.pop(ctx);
                  context.go('/shift/open');
                },
                child: const Text('OK'),
              ),
            ],
          ),
        );
        return; // already navigated in dialog
      }
    } on DioException catch (e) {
      final msg = e.response?.data?['detail'] ?? 'Gagal tutup shift';
      if (mounted) {
        setState(() => _isClosing = false);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(msg.toString()), backgroundColor: AppColors.error, behavior: SnackBarBehavior.floating),
        );
      }
    } catch (_) {
      if (mounted) setState(() => _isClosing = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: AppColors.surface,
        title: const Text('Manajemen Shift', style: TextStyle(color: AppColors.textPrimary)),
        iconTheme: const IconThemeData(color: AppColors.textPrimary),
        elevation: 0,
        actions: [
          TextButton.icon(
            onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const CashDrawerHistoryPage())),
            icon: const Icon(LucideIcons.history, color: AppColors.primary),
            label: const Text('Riwayat Kas', style: TextStyle(color: AppColors.primary)),
          ),
          const SizedBox(width: 16),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? _buildError()
              : _buildContent(),
    );
  }

  Widget _buildError() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Text(_error!, style: const TextStyle(color: AppColors.textSecondary)),
          const SizedBox(height: 16),
          ElevatedButton.icon(onPressed: _loadShift, icon: const Icon(LucideIcons.refreshCw, size: 16), label: const Text('Coba Lagi')),
        ],
      ),
    );
  }

  Widget _buildContent() {
    if (_shift == null) {
      return const Center(child: Text('Tidak ada shift aktif', style: TextStyle(color: AppColors.textSecondary)));
    }

    final startingCash = (_shift!['starting_cash'] as num?)?.toDouble() ?? 0;
    final expectedCash = (_shift!['expected_ending_cash'] as num?)?.toDouble();
    final activities = (_shift!['activities'] as List?) ?? [];
    final totalCashSales = (_shift!['total_cash_sales'] as num?)?.toDouble() ?? 0;
    final totalQrisSales = (_shift!['total_qris_sales'] as num?)?.toDouble() ?? 0;

    double cashIn = 0, cashOut = 0;
    for (final a in activities) {
      final amount = (a['amount'] as num?)?.toDouble() ?? 0;
      if (a['activity_type'] == 'income') cashIn += amount;
      if (a['activity_type'] == 'expense') cashOut += amount;
    }

    final systemTotal = expectedCash ?? (startingCash + cashIn - cashOut + totalCashSales);

    return Center(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 500),
          child: Container(
          padding: const EdgeInsets.all(32),
          decoration: BoxDecoration(
            color: AppColors.surface,
            borderRadius: BorderRadius.circular(24),
            boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.05), blurRadius: 20, offset: const Offset(0, 10))],
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(LucideIcons.clock, size: 48, color: AppColors.primary),
              const SizedBox(height: 24),
              Text('Tutup Shift Saat Ini', style: Theme.of(context).textTheme.headlineMedium),
              const SizedBox(height: 8),
              const Text('Pastikan jumlah uang di laci kasir sesuai dengan sistem.', textAlign: TextAlign.center, style: TextStyle(color: AppColors.textSecondary)),
              const SizedBox(height: 32),
              _buildRow('Uang Modal Awal', _currency.format(startingCash)),
              const SizedBox(height: 12),
              _buildRow('Penjualan Cash', _currency.format(totalCashSales)),
              const SizedBox(height: 12),
              _buildRow('Penjualan QRIS', _currency.format(totalQrisSales)),
              const SizedBox(height: 12),
              _buildRow('Penerimaan Kas Lainnya', _currency.format(cashIn)),
              const SizedBox(height: 12),
              _buildRow('Pengeluaran Kas', _currency.format(cashOut), isNegative: true),
              const Divider(height: 32),
              _buildRow('Total Uang di Laci (Sistem)', _currency.format(systemTotal), isBold: true),
              const SizedBox(height: 32),
              TextField(
                controller: _cashController,
                keyboardType: TextInputType.number,
                inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                decoration: InputDecoration(
                  labelText: 'Uang Aktual di Laci',
                  prefixText: 'Rp ',
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                  focusedBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                    borderSide: const BorderSide(color: AppColors.primary, width: 2),
                  ),
                ),
              ),
              const SizedBox(height: 32),
              SizedBox(
                width: double.infinity,
                height: 56,
                child: ElevatedButton(
                  onPressed: _isClosing ? null : _closeShift,
                  style: ElevatedButton.styleFrom(backgroundColor: AppColors.error),
                  child: _isClosing
                      ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                      : const Text('TUTUP SHIFT & CETAK REKAP', style: TextStyle(fontWeight: FontWeight.bold)),
                ),
              ),
            ],
          ),
        ),
      ),
      ),
    );
  }

  Widget _buildRow(String label, String value, {bool isNegative = false, bool isBold = false}) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(label, style: TextStyle(color: isBold ? AppColors.textPrimary : AppColors.textSecondary, fontWeight: isBold ? FontWeight.bold : FontWeight.normal, fontSize: isBold ? 18 : 14)),
        Text(value, style: TextStyle(color: isNegative ? AppColors.error : AppColors.textPrimary, fontWeight: isBold ? FontWeight.bold : FontWeight.w600, fontSize: isBold ? 18 : 14)),
      ],
    );
  }
}
