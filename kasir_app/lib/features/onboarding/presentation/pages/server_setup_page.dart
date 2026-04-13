import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:dio/dio.dart';
import '../../../../core/config/app_config.dart';
import '../../../../core/theme/app_colors.dart';

/// Muncul HANYA saat pertama kali install atau URL belum dikonfigurasi.
/// Kasir cukup masukkan IP VPS — tidak perlu rebuild APK.
class ServerSetupPage extends StatefulWidget {
  const ServerSetupPage({super.key});

  @override
  State<ServerSetupPage> createState() => _ServerSetupPageState();
}

class _ServerSetupPageState extends State<ServerSetupPage> {
  final _urlController = TextEditingController();
  bool _isLoading = false;
  bool _isSuccess = false;
  String? _error;
  String? _serverVersion;

  @override
  void initState() {
    super.initState();
    // Pre-fill dengan current value kalau ada
    _urlController.text = AppConfig.baseUrl == AppConfig.defaultBaseUrl
        ? ''
        : AppConfig.baseUrl;
  }

  @override
  void dispose() {
    _urlController.dispose();
    super.dispose();
  }

  Future<void> _testAndSave() async {
    final input = _urlController.text.trim();
    if (input.isEmpty) {
      setState(() => _error = 'Masukkan URL server');
      return;
    }

    // Auto-add http:// jika tidak ada
    String url = input;
    if (!url.startsWith('http://') && !url.startsWith('https://')) {
      url = 'http://$url';
    }
    // Hapus trailing slash
    url = url.replaceAll(RegExp(r'/$'), '');

    setState(() {
      _isLoading = true;
      _error = null;
      _isSuccess = false;
    });

    try {
      final dio = Dio(BaseOptions(
        baseUrl: '$url/api/v1',
        connectTimeout: const Duration(seconds: 8),
        receiveTimeout: const Duration(seconds: 8),
      ));

      final response = await dio.get('/auth/app/version');
      final version = response.data['data']['latest_version'] as String? ?? '-';

      // Simpan ke AppConfig
      final prefs = await SharedPreferences.getInstance();
      await AppConfig.setBaseUrl(url, prefs);

      setState(() {
        _isLoading = false;
        _isSuccess = true;
        _serverVersion = version;
      });

      // Navigasi ke login setelah 1.5 detik
      await Future.delayed(const Duration(milliseconds: 1500));
      if (mounted) context.go('/login');
    } on DioException catch (e) {
      String msg;
      if (e.type == DioExceptionType.connectionTimeout ||
          e.type == DioExceptionType.receiveTimeout) {
        msg = 'Server tidak merespons. Pastikan VPS aktif dan port 8000 terbuka.';
      } else if (e.type == DioExceptionType.connectionError) {
        msg = 'Tidak bisa terhubung ke $url\nPastikan IP dan port benar.';
      } else {
        msg = 'Gagal terhubung (${e.response?.statusCode ?? e.type.name})';
      }
      setState(() {
        _isLoading = false;
        _error = msg;
      });
    } catch (e) {
      setState(() {
        _isLoading = false;
        _error = 'Error: $e';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.primary,
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: Container(
              width: 420,
              padding: const EdgeInsets.all(40),
              decoration: BoxDecoration(
                color: AppColors.surface,
                borderRadius: BorderRadius.circular(28),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withOpacity(0.2),
                    blurRadius: 40,
                    offset: const Offset(0, 12),
                  ),
                ],
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  // Logo
                  Container(
                    padding: const EdgeInsets.all(14),
                    decoration: BoxDecoration(
                      color: AppColors.primary.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(18),
                    ),
                    child: const Icon(Icons.point_of_sale_rounded,
                        color: AppColors.primary, size: 36),
                  ),
                  const SizedBox(height: 16),
                  const Text(
                    'KASIRA',
                    style: TextStyle(
                      color: AppColors.primary,
                      fontSize: 28,
                      fontWeight: FontWeight.w800,
                      letterSpacing: -0.5,
                    ),
                  ),
                  const SizedBox(height: 8),
                  const Text(
                    'Konfigurasi Server',
                    style: TextStyle(
                      color: AppColors.textSecondary,
                      fontSize: 15,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  const SizedBox(height: 32),

                  // Info box
                  Container(
                    padding: const EdgeInsets.all(14),
                    decoration: BoxDecoration(
                      color: AppColors.info.withOpacity(0.08),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: AppColors.info.withOpacity(0.3)),
                    ),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Icon(Icons.info_outline, color: AppColors.info, size: 18),
                        const SizedBox(width: 10),
                        const Expanded(
                          child: Text(
                            'Masukkan alamat IP server dari pemilik cafe.\n'
                            'Contoh: 103.123.45.67:8000',
                            style: TextStyle(color: AppColors.textSecondary, fontSize: 13),
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 24),

                  // URL Input
                  TextField(
                    controller: _urlController,
                    keyboardType: TextInputType.url,
                    autocorrect: false,
                    inputFormatters: [
                      FilteringTextInputFormatter.deny(RegExp(r'\s')),
                    ],
                    style: const TextStyle(fontFamily: 'monospace', fontSize: 16),
                    decoration: InputDecoration(
                      labelText: 'URL Server',
                      hintText: '103.123.45.67:8000',
                      prefixIcon: const Icon(Icons.dns_outlined),
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                      focusedBorder: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(12),
                        borderSide: const BorderSide(color: AppColors.primary, width: 2),
                      ),
                      errorText: _error,
                      errorMaxLines: 3,
                    ),
                    onSubmitted: (_) => _testAndSave(),
                  ),
                  const SizedBox(height: 20),

                  // Success state
                  if (_isSuccess)
                    Container(
                      padding: const EdgeInsets.all(14),
                      decoration: BoxDecoration(
                        color: AppColors.success.withOpacity(0.1),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Row(
                        children: [
                          const Icon(Icons.check_circle_rounded,
                              color: AppColors.success, size: 20),
                          const SizedBox(width: 10),
                          Expanded(
                            child: Text(
                              'Terhubung! Kasira v$_serverVersion\nMasuk ke halaman login...',
                              style: const TextStyle(
                                  color: AppColors.success,
                                  fontWeight: FontWeight.w600),
                            ),
                          ),
                        ],
                      ),
                    ),

                  if (!_isSuccess) ...[
                    SizedBox(
                      width: double.infinity,
                      height: 52,
                      child: ElevatedButton.icon(
                        onPressed: _isLoading ? null : _testAndSave,
                        icon: _isLoading
                            ? const SizedBox(
                                width: 18,
                                height: 18,
                                child: CircularProgressIndicator(
                                    color: Colors.white, strokeWidth: 2),
                              )
                            : const Icon(Icons.wifi_tethering_rounded, size: 20),
                        label: Text(
                          _isLoading ? 'Menghubungkan...' : 'Hubungkan ke Server',
                          style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                        ),
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
