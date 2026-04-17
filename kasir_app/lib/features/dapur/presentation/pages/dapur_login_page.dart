import 'package:flutter/material.dart';
import 'package:dio/dio.dart';
import 'package:go_router/go_router.dart';
import '../../../../core/services/session_cache.dart';
import 'package:lucide_icons/lucide_icons.dart';
import '../../../../core/config/app_config.dart';
import '../../../../core/theme/app_colors.dart';

/// PIN-only login for kitchen staff.
/// Reuses the same /auth/login endpoint but with role check (kasir or manager).
class DapurLoginPage extends StatefulWidget {
  const DapurLoginPage({super.key});

  @override
  State<DapurLoginPage> createState() => _DapurLoginPageState();
}

class _DapurLoginPageState extends State<DapurLoginPage> {
  String _pin = '';
  bool _isLoading = false;
  String? _error;

  Dio get _dio => Dio(BaseOptions(
        baseUrl: AppConfig.apiV1,
        connectTimeout: const Duration(seconds: 8),
        receiveTimeout: const Duration(seconds: 8),
      ));

  void _appendDigit(String digit) {
    if (_pin.length >= 6) return;
    setState(() {
      _pin += digit;
      _error = null;
    });
    if (_pin.length == 6) _submit();
  }

  void _deleteDigit() {
    if (_pin.isEmpty) return;
    setState(() => _pin = _pin.substring(0, _pin.length - 1));
  }

  Future<void> _submit() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final cache = SessionCache.instance;
      final phone = cache.phone ?? '';
      if (phone.isEmpty) {
        setState(() {
          _pin = '';
          _error = 'Nomor HP tidak ditemukan. Login via aplikasi utama dulu.';
          _isLoading = false;
        });
        return;
      }
      final res = await _dio.post('/auth/pin/verify', data: {
        'phone': phone,
        'pin': _pin,
      });

      final data = res.data['data'];
      await cache.setAccessToken(data['access_token'] as String);
      await cache.setTenantId(data['tenant_id'] as String);
      await cache.setOutletId(data['outlet_id'] as String);

      if (mounted) context.go('/dapur/dashboard');
    } on DioException catch (e) {
      setState(() {
        _pin = '';
        _error = e.response?.statusCode == 401
            ? 'PIN salah, coba lagi'
            : 'Gagal login, coba lagi';
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF1A1A2E),
      body: SafeArea(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.kitchen_rounded, color: AppColors.warning, size: 48),
            const SizedBox(height: 16),
            const Text(
              'Masuk sebagai Tim Dapur',
              style: TextStyle(
                color: Colors.white,
                fontSize: 18,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              'Masukkan PIN 6 digit',
              style: TextStyle(color: Colors.white.withOpacity(0.5), fontSize: 14),
            ),
            const SizedBox(height: 40),

            // PIN dots
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: List.generate(6, (i) {
                final filled = i < _pin.length;
                return Container(
                  margin: const EdgeInsets.symmetric(horizontal: 8),
                  width: 16,
                  height: 16,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: filled ? AppColors.warning : Colors.transparent,
                    border: Border.all(
                      color: filled ? AppColors.warning : Colors.white38,
                      width: 2,
                    ),
                  ),
                );
              }),
            ),

            if (_error != null) ...[
              const SizedBox(height: 16),
              Text(
                _error!,
                style: const TextStyle(color: AppColors.error, fontSize: 13),
              ),
            ],

            const SizedBox(height: 40),

            // Numpad
            if (_isLoading)
              const CircularProgressIndicator(color: AppColors.warning)
            else
              _buildNumpad(),

            const SizedBox(height: 32),
            TextButton(
              onPressed: () => context.go('/setup'),
              child: Text(
                'Ubah Server',
                style: TextStyle(color: Colors.white.withOpacity(0.4), fontSize: 12),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildNumpad() {
    final digits = [
      ['1', '2', '3'],
      ['4', '5', '6'],
      ['7', '8', '9'],
      ['', '0', '⌫'],
    ];

    return Column(
      children: digits.map((row) {
        return Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: row.map((d) {
            if (d.isEmpty) return const SizedBox(width: 80, height: 68);
            return GestureDetector(
              onTap: () => d == '⌫' ? _deleteDigit() : _appendDigit(d),
              child: Container(
                width: 80,
                height: 68,
                margin: const EdgeInsets.all(6),
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.07),
                  borderRadius: BorderRadius.circular(16),
                ),
                alignment: Alignment.center,
                child: d == '⌫'
                    ? const Icon(LucideIcons.delete, color: Colors.white60, size: 22)
                    : Text(
                        d,
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 26,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
              ),
            );
          }).toList(),
        );
      }).toList(),
    );
  }
}
