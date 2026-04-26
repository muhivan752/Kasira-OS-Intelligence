import 'dart:async';
import 'package:flutter/material.dart';
import 'package:dio/dio.dart';
import 'package:go_router/go_router.dart';
import 'package:package_info_plus/package_info_plus.dart';
import 'package:url_launcher/url_launcher.dart';
import '../../../../core/config/app_config.dart';
import '../../../../core/theme/app_colors.dart';

class SplashPage extends StatefulWidget {
  const SplashPage({super.key});

  @override
  State<SplashPage> createState() => _SplashPageState();
}

class _SplashPageState extends State<SplashPage> with SingleTickerProviderStateMixin {
  late AnimationController _animController;
  late Animation<double> _fadeAnim;
  String _statusText = 'Memuat...';
  bool _isMandatoryUpdate = false;
  String? _updateUrl;

  static const _versionJsonUrl =
      'https://raw.githubusercontent.com/muhivan752/Kasira-OS-Intelligence/main/version.json';

  // P4 Quick Win #5: timeout 5s → 2s (conservative variant). raw.githubusercontent
  // CDN umumnya <1s, 2s cukup generous untuk worst case. Pre-fix: kalau GitHub
  // flaky/down, splash block 5s × 2 timeout (connect+receive) = 10s. Post-fix:
  // max 2s blocking, fallback ke navigasi normal (try-catch silent).
  Dio get _dio => Dio(BaseOptions(
    connectTimeout: const Duration(seconds: 2),
    receiveTimeout: const Duration(seconds: 2),
  ));

  @override
  void initState() {
    super.initState();
    _animController = AnimationController(vsync: this, duration: const Duration(milliseconds: 600));
    _fadeAnim = CurvedAnimation(parent: _animController, curve: Curves.easeIn);
    _animController.forward();
    _init();
  }

  @override
  void dispose() {
    _animController.dispose();
    super.dispose();
  }

  Future<void> _init() async {
    // P1 Quick Win #4: hapus 800ms artificial delay — animation controller
    // 600ms udah jalan parallel via initState. Boot saves 800ms.
    await _checkVersion();
  }

  Future<void> _checkVersion() async {
    try {
      setState(() => _statusText = 'Memeriksa versi...');
      final info = await PackageInfo.fromPlatform();
      final currentVersion = info.version;

      final response = await _dio.get(_versionJsonUrl);
      final appKey = info.packageName.contains('dapur') ? 'dapur' : 'pos';
      final data = response.data[appKey] as Map<String, dynamic>;

      final latestVersion = data['version'] as String;
      final isMandatory = data['is_mandatory'] as bool;
      final downloadUrl = data['download_url'] as String?;

      if (_isOutdated(currentVersion, latestVersion)) {
        if (isMandatory) {
          setState(() {
            _isMandatoryUpdate = true;
            _updateUrl = downloadUrl;
            _statusText = 'Update tersedia';
          });
          return;
        }
        // Non-mandatory: show banner then continue
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('Versi baru tersedia ($latestVersion). Silakan update.'),
              action: SnackBarAction(label: 'Update', onPressed: () => _openUpdate(downloadUrl)),
              duration: const Duration(seconds: 6),
            ),
          );
        }
      }
    } catch (_) {
      // Version check gagal = lanjut saja, tidak block app
    }

    await _navigate();
  }

  bool _isOutdated(String current, String latest) {
    final c = current.split('.').map(int.tryParse).toList();
    final l = latest.split('.').map(int.tryParse).toList();
    for (var i = 0; i < 3; i++) {
      final ci = (i < c.length ? c[i] : null) ?? 0;
      final li = (i < l.length ? l[i] : null) ?? 0;
      if (ci < li) return true;
      if (ci > li) return false;
    }
    return false;
  }

  Future<void> _openUpdate(String? url) async {
    // P1 Quick Win #9: was no-op pre-fix — force update tombol gak jalan.
    // url_launcher dep udah ada di pubspec.
    if (url == null || url.isEmpty) return;
    final uri = Uri.tryParse(url);
    if (uri == null) return;
    try {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    } catch (_) {
      // Silent fail — kalau browser gak bisa buka, user manual download
    }
  }

  Future<void> _navigate() async {
    if (!mounted) return;
    setState(() => _statusText = 'Menyiapkan...');

    // Pertama kali install → minta URL server
    if (!AppConfig.isConfigured) {
      if (mounted) context.go('/setup');
      return;
    }

    if (mounted) context.go('/login');
  }

  @override
  Widget build(BuildContext context) {
    if (_isMandatoryUpdate) {
      return _buildForceUpdateScreen();
    }

    return Scaffold(
      backgroundColor: AppColors.primary,
      body: FadeTransition(
        opacity: _fadeAnim,
        child: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Container(
                width: 100,
                height: 100,
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.15),
                  borderRadius: BorderRadius.circular(28),
                ),
                child: const Icon(Icons.point_of_sale_rounded, color: Colors.white, size: 56),
              ),
              const SizedBox(height: 24),
              const Text(
                'KASIRA',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 40,
                  fontWeight: FontWeight.w800,
                  letterSpacing: -1,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                'Smart POS untuk Cafe Indonesia',
                style: TextStyle(color: Colors.white.withOpacity(0.7), fontSize: 14),
              ),
              const SizedBox(height: 64),
              SizedBox(
                width: 24,
                height: 24,
                child: CircularProgressIndicator(
                  color: Colors.white.withOpacity(0.7),
                  strokeWidth: 2,
                ),
              ),
              const SizedBox(height: 16),
              Text(
                _statusText,
                style: TextStyle(color: Colors.white.withOpacity(0.6), fontSize: 13),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildForceUpdateScreen() {
    return Scaffold(
      backgroundColor: AppColors.primary,
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 400),
          child: Container(
            padding: const EdgeInsets.all(40),
            decoration: BoxDecoration(
              color: AppColors.surface,
              borderRadius: BorderRadius.circular(24),
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.system_update_alt_rounded, size: 64, color: AppColors.primary),
                const SizedBox(height: 24),
                Text(
                  'Update Wajib',
                  style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 12),
                const Text(
                  'Versi baru Kasira tersedia. Silakan update untuk melanjutkan.',
                  textAlign: TextAlign.center,
                  style: TextStyle(color: AppColors.textSecondary),
                ),
                const SizedBox(height: 32),
                SizedBox(
                  width: double.infinity,
                  height: 50,
                  child: ElevatedButton(
                    onPressed: () => _openUpdate(_updateUrl),
                    child: const Text('Download Update'),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
