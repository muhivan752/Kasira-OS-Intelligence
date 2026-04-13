import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:intl/intl.dart';
import 'package:lucide_icons/lucide_icons.dart';
import 'package:go_router/go_router.dart';
import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../../../../core/config/app_config.dart';
import '../../../../core/theme/app_colors.dart';

class ShiftOpenPage extends StatefulWidget {
  const ShiftOpenPage({super.key});

  @override
  State<ShiftOpenPage> createState() => _ShiftOpenPageState();
}

class _ShiftOpenPageState extends State<ShiftOpenPage> {
  final _cashController = TextEditingController();
  final _notesController = TextEditingController();
  bool _isLoading = false;
  double _openingCash = 0;

  final _currency = NumberFormat.currency(locale: 'id_ID', symbol: 'Rp ', decimalDigits: 0);
  final _dateFormat = DateFormat('EEEE, d MMMM yyyy', 'id_ID');
  final _timeFormat = DateFormat('HH:mm', 'id_ID');

  final List<double> _quickAmounts = [100000, 200000, 500000, 1000000];

  @override
  void dispose() {
    _cashController.dispose();
    _notesController.dispose();
    super.dispose();
  }

  Future<void> _openShift() async {
    if (_openingCash <= 0) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Masukkan jumlah uang modal awal'),
          behavior: SnackBarBehavior.floating,
          backgroundColor: AppColors.error,
        ),
      );
      return;
    }

    setState(() => _isLoading = true);

    try {
      const storage = FlutterSecureStorage();
      final token = await storage.read(key: 'access_token');
      final tenantId = await storage.read(key: 'tenant_id');
      final outletId = await storage.read(key: 'outlet_id');

      if (outletId == null || outletId.isEmpty) {
        throw Exception('Outlet tidak ditemukan, silakan login ulang.');
      }

      final dio = Dio(BaseOptions(
        baseUrl: AppConfig.apiV1,
        connectTimeout: const Duration(seconds: 15),
        receiveTimeout: const Duration(seconds: 15),
      ));

      final response = await dio.post(
        '/shifts/open',
        queryParameters: {'outlet_id': outletId},
        options: Options(headers: {
          if (token != null) 'Authorization': 'Bearer $token',
          if (tenantId != null) 'X-Tenant-ID': tenantId,
        }),
        data: {
          'starting_cash': _openingCash,
          if (_notesController.text.trim().isNotEmpty) 'notes': _notesController.text.trim(),
        },
      );

      final shiftId = response.data['data']['id'] as String;
      await storage.write(key: 'shift_session_id', value: shiftId);

      if (mounted) {
        context.go('/dashboard');
      }
    } on DioException catch (e) {
      final detail = e.response?.data?['detail'] ?? 'Gagal membuka shift';
      if (mounted) {
        setState(() => _isLoading = false);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(detail.toString()),
            behavior: SnackBarBehavior.floating,
            backgroundColor: AppColors.error,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        setState(() => _isLoading = false);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Gagal membuka shift: $e'),
            behavior: SnackBarBehavior.floating,
            backgroundColor: AppColors.error,
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final now = DateTime.now();

    return Scaffold(
      backgroundColor: AppColors.primary,
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Container(
            width: 480,
            padding: const EdgeInsets.all(40),
            decoration: BoxDecoration(
              color: AppColors.surface,
              borderRadius: BorderRadius.circular(28),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withOpacity(0.15),
                  blurRadius: 40,
                  offset: const Offset(0, 10),
                ),
              ],
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                // Logo
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Container(
                      padding: const EdgeInsets.all(10),
                      decoration: BoxDecoration(
                        color: AppColors.primary.withOpacity(0.1),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: const Icon(Icons.point_of_sale_rounded, color: AppColors.primary, size: 28),
                    ),
                    const SizedBox(width: 12),
                    const Text(
                      'KASIRA',
                      style: TextStyle(
                        color: AppColors.primary,
                        fontSize: 24,
                        fontWeight: FontWeight.w800,
                        letterSpacing: -0.5,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 32),

                // Date & time
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
                  decoration: BoxDecoration(
                    color: AppColors.surfaceVariant,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Row(
                    children: [
                      const Icon(LucideIcons.calendar, color: AppColors.primary, size: 20),
                      const SizedBox(width: 12),
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            _dateFormat.format(now),
                            style: const TextStyle(fontWeight: FontWeight.w600),
                          ),
                          Text(
                            'Shift dimulai pukul ${_timeFormat.format(now)}',
                            style: const TextStyle(color: AppColors.textSecondary, fontSize: 12),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 28),

                Text(
                  'Buka Shift Kasir',
                  style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 6),
                const Text(
                  'Masukkan jumlah uang modal awal di laci kasir',
                  textAlign: TextAlign.center,
                  style: TextStyle(color: AppColors.textSecondary),
                ),
                const SizedBox(height: 28),

                // Cash input
                TextField(
                  controller: _cashController,
                  keyboardType: TextInputType.number,
                  inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                  style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold),
                  decoration: InputDecoration(
                    labelText: 'Modal Awal',
                    prefixText: 'Rp ',
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                    focusedBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(12),
                      borderSide: const BorderSide(color: AppColors.primary, width: 2),
                    ),
                  ),
                  onChanged: (val) {
                    setState(() {
                      _openingCash = double.tryParse(val) ?? 0;
                    });
                  },
                ),
                const SizedBox(height: 16),

                // Quick amount buttons
                Row(
                  children: _quickAmounts.map((amount) {
                    return Expanded(
                      child: Padding(
                        padding: EdgeInsets.only(
                          right: amount == _quickAmounts.last ? 0 : 8,
                        ),
                        child: OutlinedButton(
                          onPressed: () {
                            setState(() {
                              _openingCash = amount;
                              _cashController.text = amount.toInt().toString();
                            });
                          },
                          style: OutlinedButton.styleFrom(
                            padding: const EdgeInsets.symmetric(vertical: 10),
                            side: BorderSide(
                              color: _openingCash == amount ? AppColors.primary : AppColors.border,
                            ),
                            backgroundColor: _openingCash == amount
                                ? AppColors.primary.withOpacity(0.05)
                                : null,
                          ),
                          child: Text(
                            _formatShort(amount),
                            style: TextStyle(
                              fontSize: 12,
                              color: _openingCash == amount ? AppColors.primary : AppColors.textSecondary,
                              fontWeight: _openingCash == amount ? FontWeight.bold : FontWeight.normal,
                            ),
                          ),
                        ),
                      ),
                    );
                  }).toList(),
                ),
                const SizedBox(height: 20),

                // Notes
                TextField(
                  controller: _notesController,
                  maxLines: 2,
                  decoration: InputDecoration(
                    labelText: 'Catatan (opsional)',
                    hintText: 'mis: ada koin kembalian...',
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                    focusedBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(12),
                      borderSide: const BorderSide(color: AppColors.primary, width: 2),
                    ),
                  ),
                ),
                const SizedBox(height: 28),

                // Summary
                if (_openingCash > 0)
                  Container(
                    padding: const EdgeInsets.all(16),
                    margin: const EdgeInsets.only(bottom: 20),
                    decoration: BoxDecoration(
                      color: AppColors.success.withOpacity(0.05),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: AppColors.success.withOpacity(0.3)),
                    ),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text('Modal awal shift', style: TextStyle(color: AppColors.textSecondary)),
                        Text(
                          _currency.format(_openingCash),
                          style: const TextStyle(
                            fontWeight: FontWeight.bold,
                            fontSize: 18,
                            color: AppColors.success,
                          ),
                        ),
                      ],
                    ),
                  ),

                SizedBox(
                  width: double.infinity,
                  height: 52,
                  child: ElevatedButton.icon(
                    onPressed: _isLoading ? null : _openShift,
                    icon: _isLoading
                        ? const SizedBox(
                            width: 20,
                            height: 20,
                            child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2),
                          )
                        : const Icon(LucideIcons.playCircle, size: 20),
                    label: Text(_isLoading ? 'Membuka shift...' : 'BUKA SHIFT SEKARANG'),
                    style: ElevatedButton.styleFrom(
                      textStyle: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  String _formatShort(double amount) {
    if (amount >= 1000000) {
      return '${(amount / 1000000).toStringAsFixed(amount % 1000000 == 0 ? 0 : 1)}jt';
    } else if (amount >= 1000) {
      return '${(amount / 1000).toStringAsFixed(0)}rb';
    }
    return amount.toInt().toString();
  }
}
